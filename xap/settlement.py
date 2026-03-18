"""SettlementIntent implementation for XAP v0.2."""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, ClassVar

from ._common import (
    deep_copy,
    generate_prefixed_id,
    parse_utc,
    utc_now_iso,
    validate_against_schema,
)
from .crypto import canonical_json_bytes, generate_keypair, sign_payload
from .errors import XAPExpiredError, XAPSplitError, XAPStateError
from .receipt import ExecutionReceipt

_PLATFORM_PRIVATE_KEY, PLATFORM_PUBLIC_KEY = generate_keypair()

_TERMINAL_STATES = {"SETTLED", "REFUNDED", "PARTIAL", "TIMEOUT", "FAILED_LOCK", "RELEASE_FAILED", "DISPUTED"}


def _generate_settlement_id() -> str:
    return f"stl_{secrets.token_hex(4)}"


def _generate_idempotency_key() -> str:
    return f"idem_{secrets.token_hex(8)}"


def _generate_condition_id() -> str:
    return f"cond_{secrets.token_hex(2)}"


@dataclass
class SettlementIntent:
    _data: dict[str, Any]
    event_chain: list[dict[str, Any]] = field(default_factory=list)

    SCHEMA: ClassVar[str] = "settlement-intent.json"
    _idempotency_registry: ClassVar[dict[str, "SettlementIntent"]] = {}

    @property
    def settlement_id(self) -> str:
        return self._data["settlement_id"]

    @property
    def execution_receipt(self) -> ExecutionReceipt | None:
        return getattr(self, "_execution_receipt", None)

    @classmethod
    def create(cls, negotiation: Any, idempotency_key: str | None = None) -> "SettlementIntent":
        if idempotency_key and idempotency_key in cls._idempotency_registry:
            return cls._idempotency_registry[idempotency_key]

        negotiation_data = negotiation.to_dict() if hasattr(negotiation, "to_dict") else deep_copy(negotiation)

        if negotiation_data.get("state") != "ACCEPT":
            raise XAPStateError("SettlementIntent can only be created from an ACCEPT negotiation")
        if parse_utc(utc_now_iso()) > parse_utc(negotiation_data["expires_at"]):
            raise XAPExpiredError("Cannot create settlement from an expired negotiation")

        # Read negotiation fields (v0.2)
        payer = negotiation_data.get("from_agent") or negotiation_data.get("initiator_agent_id", "")
        payee = negotiation_data.get("to_agent") or negotiation_data.get("counterparty_agent_id", "")
        sla_data = negotiation_data.get("sla") or negotiation_data.get("sla_declaration", {})

        # Amount from pricing (v0.2) or offer (v0.1)
        if "pricing" in negotiation_data:
            total_amount = negotiation_data["pricing"]["amount_minor_units"]
            currency = negotiation_data["pricing"]["currency"]
        else:
            total_amount = round(negotiation_data["offer"]["offered_rate"] * 100)
            currency = negotiation_data["offer"].get("settlement_unit", "USD")

        # Build conditions from SLA
        conditions = []
        min_quality_bps = sla_data.get("min_quality_score_bps")
        if min_quality_bps is not None:
            conditions.append({
                "condition_id": _generate_condition_id(),
                "type": "probabilistic",
                "check": "quality_score",
                "operator": "gte",
                "threshold": min_quality_bps,
                "verifier": "engine",
                "required": True,
            })
        if not conditions:
            conditions.append({
                "condition_id": _generate_condition_id(),
                "type": "deterministic",
                "check": "execution_completed",
                "verifier": "engine",
                "required": True,
            })

        idem_key = idempotency_key or _generate_idempotency_key()
        timeout_ms = sla_data.get("max_latency_ms", 60000)

        data: dict[str, Any] = {
            "settlement_id": _generate_settlement_id(),
            "negotiation_id": negotiation_data["negotiation_id"],
            "state": "FUNDS_LOCKED",
            "payer_agent": payer,
            "payee_agents": [
                {"agent_id": payee, "share_bps": 10000, "role": "primary_executor"},
            ],
            "total_amount_minor_units": total_amount,
            "currency": currency,
            "adapter": "test",
            "conditions": conditions,
            "timeout_seconds": max(1, (timeout_ms * 2) // 1000),
            "on_timeout": "full_refund",
            "on_partial_completion": "pro_rata",
            "on_failure": "full_refund",
            "chargeback_policy": "proportional",
            "idempotency_key": idem_key,
            "finality_class": "reversible",
            "xap_version": "0.2.0",
            "created_at": utc_now_iso(),
            "signature": "",
        }

        validate_against_schema(cls.SCHEMA, data)
        obj = cls(data)
        obj.event_chain = _build_initial_event_chain(negotiation_data, data["settlement_id"])
        cls._idempotency_registry[idem_key] = obj
        return obj

    def start_execution(self) -> "SettlementIntent":
        self._transition("FUNDS_LOCKED", "EXECUTING")
        self._append_event("EXECUTION_STARTED", self._primary_payee(), {"state": "EXECUTING"})
        return self

    def submit_result(
        self,
        output: dict[str, Any],
        quality_score: float,
        latency_ms: int,
        agent_private_key: str,
    ) -> "SettlementIntent":
        self._transition("EXECUTING", "PENDING_VERIFICATION")

        result = {
            "submitted_by": self._primary_payee(),
            "submitted_at": utc_now_iso(),
            "output": output,
            "quality_score": quality_score,
            "latency_ms": latency_ms,
            "completion_percentage": output.get("completion_percentage", 100),
        }
        result["execution_signature"] = sign_payload(result, agent_private_key, exclude_fields=["execution_signature"])
        self._data["execution_result"] = result
        self._append_event("EXECUTION_COMPLETED", self._primary_payee(), result, signer_key=agent_private_key)
        validate_against_schema(self.SCHEMA, self._data)
        return self

    def verify_condition(self) -> bool:
        if self._data["state"] != "PENDING_VERIFICATION":
            raise XAPStateError("Condition verification requires PENDING_VERIFICATION state")

        result = self._data.get("execution_result", {})
        conditions = self._data["conditions"]
        all_required_met = True
        evaluations = []

        for cond in conditions:
            met = self._evaluate_condition(cond, result)
            evaluations.append({
                "condition_id": cond["condition_id"],
                "type": cond["type"],
                "met": met,
                "required": cond["required"],
            })
            if cond["required"] and not met:
                all_required_met = False

        if all_required_met:
            resulting_state = "SETTLED"
        else:
            completion = result.get("completion_percentage", 100)
            resulting_state = "REFUNDED" if completion >= 100 else "PARTIAL"

        self._data["verification_result"] = {
            "verified_at": utc_now_iso(),
            "conditions_evaluated": evaluations,
            "all_required_met": all_required_met,
            "resulting_state": resulting_state,
            "verification_detail": f"required_met={all_required_met} conditions={len(evaluations)}",
        }

        self._append_event(
            "CONDITION_VERIFIED" if all_required_met else "CONDITION_FAILED",
            self._data["payer_agent"],
            {"all_required_met": all_required_met},
        )
        validate_against_schema(self.SCHEMA, self._data)
        return all_required_met

    def release(self) -> "SettlementIntent":
        if self._data["state"] != "PENDING_VERIFICATION":
            raise XAPStateError("Release requires PENDING_VERIFICATION state")

        if "verification_result" not in self._data:
            self.verify_condition()
        if not self._data["verification_result"]["all_required_met"]:
            raise XAPStateError("Cannot release settlement when required conditions are not met")

        distributions = self.apply_splits()
        completion = self._data.get("execution_result", {}).get("completion_percentage", 100)
        target_state = "PARTIAL" if completion < 100 else "SETTLED"

        self._data["state"] = target_state
        self._data["settled_at"] = utc_now_iso()
        self._data["split_distributions"] = distributions

        self._append_event("FUNDS_RELEASED", self._data["payer_agent"], {"state": target_state})
        self._issue_receipt()
        validate_against_schema(self.SCHEMA, self._data)
        return self

    def refund(self) -> "SettlementIntent":
        if self._data["state"] != "PENDING_VERIFICATION":
            raise XAPStateError("Refund requires PENDING_VERIFICATION state")

        self._data["state"] = "REFUNDED"
        self._data["settled_at"] = utc_now_iso()
        if "verification_result" not in self._data:
            self._data["verification_result"] = {
                "verified_at": utc_now_iso(),
                "conditions_evaluated": [],
                "all_required_met": False,
                "resulting_state": "REFUNDED",
                "verification_detail": "refund requested",
            }

        self._append_event("FUNDS_ROLLED_BACK", self._data["payer_agent"], {"state": "REFUNDED"})
        self._issue_receipt()
        validate_against_schema(self.SCHEMA, self._data)
        return self

    def apply_splits(self) -> list[dict[str, Any]]:
        payee_agents = self._data.get("payee_agents", [])
        total_bps = sum(p["share_bps"] for p in payee_agents)
        if total_bps != 10000:
            raise XAPSplitError(f"payee share_bps must sum to exactly 10000, got {total_bps}")

        total_amount = self._data["total_amount_minor_units"]
        now = utc_now_iso()
        distributions: list[dict[str, Any]] = []
        distributed = 0

        for i, payee in enumerate(payee_agents):
            if i == len(payee_agents) - 1:
                amount = total_amount - distributed
            else:
                amount = (total_amount * payee["share_bps"]) // 10000
                distributed += amount

            record = {
                "agent_id": payee["agent_id"],
                "amount_minor_units": amount,
                "share_bps": payee["share_bps"],
                "role": payee["role"],
                "distribution_timestamp": now,
            }
            record["distribution_signature"] = sign_payload(
                record,
                _PLATFORM_PRIVATE_KEY,
                exclude_fields=["distribution_signature"],
            )
            distributions.append(record)

        return distributions

    def to_dict(self) -> dict[str, Any]:
        data = deep_copy(self._data)
        data["event_chain"] = deep_copy(self.event_chain)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SettlementIntent":
        event_chain = deep_copy(data.get("event_chain", []))
        payload = deep_copy(data)
        payload.pop("event_chain", None)
        validate_against_schema(cls.SCHEMA, payload)
        return cls(payload, event_chain=event_chain)

    def _transition(self, expected_state: str, next_state: str) -> None:
        current = self._data["state"]
        if current != expected_state:
            raise XAPStateError(f"Invalid state transition from {current} to {next_state}")
        self._data["state"] = next_state

    def _primary_payee(self) -> str:
        return self._data["payee_agents"][0]["agent_id"]

    def _evaluate_condition(self, cond: dict[str, Any], result: dict[str, Any]) -> bool:
        cond_type = cond["type"]
        if cond_type == "deterministic":
            output = result.get("output", {})
            return bool(output)
        elif cond_type == "probabilistic":
            operator = cond.get("operator", "gte")
            threshold = cond.get("threshold", 0)
            # Map check to result field
            check = cond.get("check", "")
            if check == "quality_score":
                actual = round(result.get("quality_score", 0) * 10000)
            elif check == "latency_ms":
                actual = result.get("latency_ms", 0)
            else:
                actual = 0

            ops = {"gte": actual >= threshold, "lte": actual <= threshold, "gt": actual > threshold, "lt": actual < threshold, "eq": actual == threshold}
            return ops.get(operator, False)
        elif cond_type == "human_approval":
            return bool(result.get("output", {}).get("human_approved"))
        return False

    def _append_event(
        self,
        event_type: str,
        agent_id: str,
        event_data: dict[str, Any],
        signer_key: str | None = None,
    ) -> None:
        previous_hash = _event_hash(self.event_chain[-1]) if self.event_chain else ""
        event = {
            "event_id": generate_prefixed_id("evt_"),
            "event_type": event_type,
            "timestamp": utc_now_iso(),
            "agent_id": agent_id,
            "event_data": event_data,
            "previous_event_hash": previous_hash,
        }
        event["signature"] = sign_payload(event, signer_key or _PLATFORM_PRIVATE_KEY, exclude_fields=["signature"])
        self.event_chain.append(event)

    def _issue_receipt(self) -> None:
        if self._data["state"] not in _TERMINAL_STATES:
            return
        self._execution_receipt = ExecutionReceipt.issue(self, _PLATFORM_PRIVATE_KEY)
        self._data["execution_receipt_id"] = self._execution_receipt.receipt_id


def _event_hash(event: dict[str, Any]) -> str:
    return sha256(canonical_json_bytes(event, exclude_fields=["signature"])).hexdigest()


def _build_initial_event_chain(negotiation_data: dict[str, Any], settlement_id: str) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    initiator = negotiation_data.get("from_agent") or negotiation_data.get("initiator_agent_id", "")

    first_event = {
        "event_id": generate_prefixed_id("evt_"),
        "event_type": "NEGOTIATION_INITIATED",
        "timestamp": negotiation_data["created_at"],
        "agent_id": initiator,
        "event_data": {"negotiation_id": negotiation_data["negotiation_id"]},
        "previous_event_hash": "",
    }
    first_event["signature"] = sign_payload(first_event, _PLATFORM_PRIVATE_KEY, exclude_fields=["signature"])
    chain.append(first_event)

    lock_event = {
        "event_id": generate_prefixed_id("evt_"),
        "event_type": "FUNDS_LOCKED",
        "timestamp": utc_now_iso(),
        "agent_id": initiator,
        "event_data": {"settlement_id": settlement_id},
        "previous_event_hash": _event_hash(chain[-1]),
    }
    lock_event["signature"] = sign_payload(lock_event, _PLATFORM_PRIVATE_KEY, exclude_fields=["signature"])
    chain.append(lock_event)
    return chain

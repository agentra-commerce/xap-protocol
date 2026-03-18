"""ExecutionReceipt implementation for XAP v0.2."""

from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, ClassVar

from ._common import deep_copy, utc_now_iso, validate_against_schema
from .crypto import canonical_json_bytes, sign_payload, verify_payload


def _generate_receipt_id() -> str:
    return f"rcpt_{secrets.token_hex(4)}"


class ReceiptChain:
    """Thread-safe receipt chain state.

    Each instance tracks its own chain position counter and last receipt hash,
    eliminating the previous global mutable state that was unsafe in
    multi-worker environments.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._chain_position_counter: int = 0
        self._last_receipt_hash: str = ""

    def advance(self) -> tuple[int, str]:
        """Atomically increment chain position and return (position, previous_hash)."""
        with self._lock:
            self._chain_position_counter += 1
            position = self._chain_position_counter
            previous_hash = self._last_receipt_hash
            return position, previous_hash

    def set_last_hash(self, receipt_hash: str) -> None:
        """Update the last receipt hash after computing it."""
        with self._lock:
            self._last_receipt_hash = receipt_hash


# Default chain instance (per-process). For multi-worker deployments,
# each worker gets its own ReceiptChain instance automatically.
_default_chain = ReceiptChain()


@dataclass
class ExecutionReceipt:
    _data: dict[str, Any]

    SCHEMA: ClassVar[str] = "execution-receipt.json"
    _registry: ClassVar[dict[str, "ExecutionReceipt"]] = {}

    @property
    def receipt_id(self) -> str:
        return self._data["receipt_id"]

    @classmethod
    def issue(
        cls,
        settlement: Any,
        platform_private_key: str,
        chain: ReceiptChain | None = None,
    ) -> "ExecutionReceipt":
        if chain is None:
            chain = _default_chain

        settlement_data = settlement.to_dict() if hasattr(settlement, "to_dict") else deep_copy(settlement)

        payer = settlement_data.get("payer_agent", "")
        payee_agents = settlement_data.get("payee_agents", [])
        conditions = settlement_data.get("conditions", [])
        verification = settlement_data.get("verification_result", {})
        exec_result = settlement_data.get("execution_result", {})
        distributions = settlement_data.get("split_distributions", [])
        state = settlement_data["state"]

        # Build conditions_results from settlement conditions + verification
        evaluated = {e["condition_id"]: e for e in verification.get("conditions_evaluated", [])}
        now = utc_now_iso()
        conditions_results = []
        for cond in conditions:
            cond_id = cond["condition_id"]
            ev = evaluated.get(cond_id, {})
            cr: dict[str, Any] = {
                "condition_id": cond_id,
                "type": cond["type"],
                "check": cond["check"],
                "passed": ev.get("met", False),
                "verified_by": cond.get("verifier", "engine"),
                "verified_at": verification.get("verified_at", now),
            }
            if cond.get("operator"):
                cr["operator"] = cond["operator"]
            if cond.get("threshold") is not None:
                cr["threshold"] = cond["threshold"]
            if cond.get("verifier_agent_id"):
                cr["verified_by_agent_id"] = cond["verifier_agent_id"]
            conditions_results.append(cr)

        if not conditions_results:
            conditions_results = [{
                "condition_id": "cond_0000",
                "type": "deterministic",
                "check": "execution_completed",
                "passed": state in {"SETTLED", "PARTIAL"},
                "verified_by": "engine",
                "verified_at": now,
            }]

        # Build payouts from distributions + payee_agents
        currency = settlement_data.get("currency", "USD")
        total_amount = settlement_data.get("total_amount_minor_units", 0)
        payouts = []
        payee_map = {p["agent_id"]: p for p in payee_agents}
        for dist in distributions:
            agent_id = dist.get("agent_id", "")
            payee_info = payee_map.get(agent_id, {})
            share_bps = payee_info.get("share_bps", 10000)
            base_amount = (total_amount * share_bps) // 10000
            final_amount = dist.get("amount_minor_units", 0)
            payouts.append({
                "agent_id": agent_id,
                "role": payee_info.get("role", "primary_executor"),
                "declared_share_bps": share_bps,
                "base_amount_minor_units": base_amount,
                "final_amount_minor_units": final_amount,
                "currency": currency,
                "status": "paid",
            })

        if not payouts and payee_agents:
            for p in payee_agents:
                payouts.append({
                    "agent_id": p["agent_id"],
                    "role": p.get("role", "primary_executor"),
                    "declared_share_bps": p.get("share_bps", 10000),
                    "base_amount_minor_units": 0,
                    "final_amount_minor_units": 0,
                    "currency": currency,
                    "status": "refunded" if state == "REFUNDED" else "failed",
                })

        # Execution metrics
        quality_score = exec_result.get("quality_score", 0)
        latency_ms = exec_result.get("latency_ms", 0)
        metrics = {
            "execution_started_at": exec_result.get("submitted_at", now),
            "execution_completed_at": exec_result.get("submitted_at", now),
            "execution_duration_ms": latency_ms,
            "verification_duration_ms": 0,
            "total_duration_ms": latency_ms,
            "timeout_triggered": state == "TIMEOUT",
            "retries_attempted": 0,
        }

        # Reputation impacts
        all_met = verification.get("all_required_met", False)
        outcome_label = "positive" if all_met else ("negative" if state == "REFUNDED" else "neutral")
        delta = 1 if all_met else (-1 if state == "REFUNDED" else 0)

        reputation_impacts = []
        for p in payee_agents:
            impact: dict[str, Any] = {
                "agent_id": p["agent_id"],
                "role_in_settlement": "payee",
                "outcome_for_agent": outcome_label,
                "success_rate_delta_bps": delta,
                "dispute_filed": state == "DISPUTED",
            }
            if quality_score:
                impact["quality_score_recorded_bps"] = round(quality_score * 10000)
            reputation_impacts.append(impact)

        reputation_impacts.append({
            "agent_id": payer,
            "role_in_settlement": "payer",
            "outcome_for_agent": "positive" if all_met else "neutral",
            "success_rate_delta_bps": 1 if all_met else 0,
            "dispute_filed": state == "DISPUTED",
        })

        # Verity hash (placeholder — real implementation links to Verity engine)
        verity_hash = f"sha256:{sha256(canonical_json_bytes(settlement_data)).hexdigest()}"

        # Chain (thread-safe via ReceiptChain instance)
        chain_position, previous_hash = chain.advance()

        receipt_data: dict[str, Any] = {
            "receipt_id": _generate_receipt_id(),
            "settlement_id": settlement_data["settlement_id"],
            "negotiation_id": settlement_data["negotiation_id"],
            "payer_agent": payer,
            "outcome": state,
            "conditions_results": conditions_results,
            "payouts": payouts,
            "execution_metrics": metrics,
            "reputation_impacts": reputation_impacts,
            "verity_hash": verity_hash,
            "chain_position": chain_position,
            "adapter_used": settlement_data.get("adapter", "test"),
            "finality_status": "final",
            "xap_version": "0.2.0",
            "issued_at": now,
            "signatures": {
                "settlement_engine": sign_payload({"receipt": "engine_attestation"}, platform_private_key),
                "payer": "",
                "payees": [
                    {"agent_id": p["agent_id"], "signature": ""}
                    for p in payee_agents
                ],
            },
        }

        if previous_hash:
            receipt_data["chain_previous_hash"] = f"sha256:{previous_hash}"

        # Compute receipt hash for chain continuity
        receipt_hash = sha256(canonical_json_bytes(receipt_data)).hexdigest()
        chain.set_last_hash(receipt_hash)

        validate_against_schema(cls.SCHEMA, receipt_data)
        obj = cls(receipt_data)
        cls._registry[obj.receipt_id] = obj
        return obj

    def verify(self, platform_public_key: str) -> bool:
        sig = self._data.get("signatures", {}).get("settlement_engine", "")
        if not sig:
            return False
        return verify_payload(
            {"receipt": "engine_attestation"},
            sig,
            platform_public_key,
        )

    def to_dict(self) -> dict[str, Any]:
        return deep_copy(self._data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionReceipt":
        validate_against_schema(cls.SCHEMA, data)
        obj = cls(deep_copy(data))
        cls._registry[obj.receipt_id] = obj
        return obj

    @classmethod
    def query(
        cls,
        settlement_id: str | None = None,
        negotiation_id: str | None = None,
    ) -> list["ExecutionReceipt"]:
        results = list(cls._registry.values())
        if settlement_id is not None:
            results = [item for item in results if item._data.get("settlement_id") == settlement_id]
        if negotiation_id is not None:
            results = [item for item in results if item._data.get("negotiation_id") == negotiation_id]
        return results

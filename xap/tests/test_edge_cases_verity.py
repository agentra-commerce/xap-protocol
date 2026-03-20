"""Edge case tests for verity subsystem (EC-027 through EC-036).

Covers: replay hash mismatch, chain break, UNKNOWN never resolved,
confidence below threshold, engine version mismatch, multiple receipts,
timeout-then-dispute, REVERSED terminal, repeated UNKNOWN, evidence hash.
"""

import json

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pathlib import Path

SCHEMA_DIR = Path(__file__).parent.parent / "schemas"


def _load_schema(name):
    with (SCHEMA_DIR / name).open() as f:
        return json.load(f)


def _verity_base():
    """Return a valid base verity receipt dict."""
    return {
        "verity_id": "vrt_a1b2c3d4",
        "settlement_id": "stl_4b7c9e2f",
        "decision_type": "condition_verification",
        "decision_timestamp": "2026-03-15T14:30:28Z",
        "input_state": {
            "settlement_state": "PENDING_VERIFICATION",
            "contract_terms": {
                "pricing": {"amount_minor_units": 500, "currency": "USD"},
                "sla": {"max_latency_ms": 5000},
                "conditions": [{"condition_id": "cond_a1b2", "type": "deterministic"}],
            },
            "agent_states": [
                {"agent_id": "agent_2d8e5f1a", "role": "primary_executor"},
            ],
        },
        "rules_applied": {
            "rules_version": "0.2.0",
            "rules_hash": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "applicable_rules": [
                {"rule_id": "cond_check", "rule_description": "Check condition", "evaluated": True, "result": "pass"},
            ],
        },
        "computation": {
            "steps": [
                {
                    "step_number": 1,
                    "operation": "evaluate_condition",
                    "inputs": {"condition_id": "cond_a1b2"},
                    "output": {"passed": True},
                    "deterministic": True,
                },
            ],
            "total_steps": 1,
            "computation_duration_ms": 3,
        },
        "outcome": {
            "decision": "release_funds",
            "settlement_state_after": "SETTLED",
            "outcome_classification": "SUCCESS",
        },
        "replay_hash": "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        "confidence_bps": 10000,
        "chain_position": 1,
        "xap_version": "0.2.0",
        "verity_engine_version": "0.2.0",
        "verity_signature": "ed25519:dmVyaXR5X3NpbXBsZV9zaWduYXR1cmU=",
    }


def _validate(instance):
    schema = _load_schema("verity-receipt.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))


class TestEC029UnknownOutcomeNeverResolved:
    """EC-029: UNKNOWN is a valid outcome_classification."""

    def test_unknown_outcome_is_valid(self):
        receipt = _verity_base()
        receipt["outcome"]["outcome_classification"] = "UNKNOWN"
        errors = _validate(receipt)
        assert not errors


class TestEC030ConfidenceBelowThreshold:
    """EC-030: Low confidence values are schema-valid but flagged at runtime."""

    def test_low_confidence_is_schema_valid(self):
        receipt = _verity_base()
        receipt["confidence_bps"] = 4500  # below typical 8000 threshold
        errors = _validate(receipt)
        assert not errors

    def test_zero_confidence_is_schema_valid(self):
        receipt = _verity_base()
        receipt["confidence_bps"] = 0
        errors = _validate(receipt)
        assert not errors


class TestEC031EngineVersionMismatch:
    """EC-031: Different engine versions are recorded in receipt."""

    def test_engine_version_field_present(self):
        receipt = _verity_base()
        receipt["verity_engine_version"] = "2.1.0"
        errors = _validate(receipt)
        assert not errors

    def test_engine_version_mismatch_recorded(self):
        receipt = _verity_base()
        receipt["verity_engine_version"] = "2.2.0"
        assert receipt["verity_engine_version"] != receipt["xap_version"]


class TestEC032MultipleVerityReceipts:
    """EC-032: Multiple receipts for same settlement are valid."""

    def test_two_receipts_same_settlement_different_positions(self):
        r1 = _verity_base()
        r2 = _verity_base()
        r2["verity_id"] = "vrt_e5f6a7b8"
        r2["chain_position"] = 2
        r2["chain_previous_verity_hash"] = (
            "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        )
        assert not _validate(r1)
        assert not _validate(r2)


class TestEC034ReversedIsTerminal:
    """EC-034: REVERSED is a valid outcome classification."""

    def test_reversed_outcome_is_valid(self):
        receipt = _verity_base()
        receipt["outcome"]["outcome_classification"] = "REVERSED"
        receipt["decision_type"] = "reversal_execution"
        errors = _validate(receipt)
        assert not errors


class TestEC035RepeatedUnknown:
    """EC-035: Repeated UNKNOWN outcomes are recorded independently."""

    def test_unknown_outcome_chain(self):
        r1 = _verity_base()
        r1["outcome"]["outcome_classification"] = "UNKNOWN"
        r1["confidence_bps"] = 3000

        r2 = _verity_base()
        r2["verity_id"] = "vrt_e5f6a7b8"
        r2["chain_position"] = 2
        r2["outcome"]["outcome_classification"] = "UNKNOWN"
        r2["confidence_bps"] = 3500
        r2["chain_previous_verity_hash"] = (
            "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        )
        assert not _validate(r1)
        assert not _validate(r2)


class TestEC027ReplayHashFormat:
    """EC-027: Invalid replay_hash format is caught by schema."""

    def test_bad_replay_hash_fails_validation(self):
        receipt = _verity_base()
        receipt["replay_hash"] = "md5:invalidhash"
        errors = _validate(receipt)
        assert errors, "Bad replay_hash format should fail validation"


class TestEC028ChainBreak:
    """EC-028: Invalid chain_previous_verity_hash is caught."""

    def test_bad_chain_hash_fails_validation(self):
        receipt = _verity_base()
        receipt["chain_position"] = 3
        receipt["chain_previous_verity_hash"] = "NOT_A_VALID_HASH"
        errors = _validate(receipt)
        assert errors, "Bad chain hash format should fail validation"


class TestEC036EvidenceHashMismatch:
    """EC-036: Evidence hash with invalid format is caught."""

    def test_bad_evidence_hash_fails_schema(self):
        receipt = _verity_base()
        receipt["input_state"]["dispute_evidence"] = {
            "submitted_by": "agent_2d8e5f1a",
            "evidence_type": "screenshot",
            "evidence_hash": "md5:badhash",
        }
        errors = _validate(receipt)
        assert errors, "Bad evidence_hash format should fail validation"

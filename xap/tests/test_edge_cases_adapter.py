"""Edge case tests for adapter subsystem (EC-047 through EC-052).

These edge cases are adapter-implementation-dependent.
Tests validate that the protocol schema and state machine
accommodate the necessary states and fields for adapter error handling.
"""

import json

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pathlib import Path

from xap.settlement import _TERMINAL_STATES

SCHEMA_DIR = Path(__file__).parent.parent / "schemas"


def _load_schema(name):
    with (SCHEMA_DIR / name).open() as f:
        return json.load(f)


def _validate_settlement(instance):
    schema = _load_schema("settlement-intent.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))


def _settlement_base():
    return {
        "settlement_id": "stl_4b7c9e2f",
        "negotiation_id": "neg_8a2f4c1d",
        "state": "PENDING_LOCK",
        "payer_agent": "agent_7f3a9b2c",
        "payee_agents": [
            {"agent_id": "agent_2d8e5f1a", "share_bps": 10000, "role": "primary_executor"},
        ],
        "total_amount_minor_units": 500,
        "currency": "USD",
        "adapter": "stripe",
        "conditions": [
            {
                "condition_id": "cond_a1b2",
                "type": "deterministic",
                "check": "http_status_200",
                "verifier": "engine",
                "required": True,
            },
        ],
        "timeout_seconds": 30,
        "on_timeout": "full_refund",
        "on_partial_completion": "pro_rata",
        "on_failure": "full_refund",
        "chargeback_policy": "proportional",
        "idempotency_key": "idem_9c3f2a1b",
        "finality_class": "reversible",
        "xap_version": "0.2.0",
        "created_at": "2026-03-15T14:30:00Z",
        "signature": "ed25519:c2V0dGxlbWVudF9zaW1wbGVfc2ln",
    }


class TestEC047StripeWebhookTimeout:
    """EC-047: Settlement state machine supports FAILED_LOCK state."""

    def test_failed_lock_is_valid_state(self):
        settlement = _settlement_base()
        settlement["state"] = "FAILED_LOCK"
        errors = _validate_settlement(settlement)
        assert not errors

    def test_failed_lock_is_terminal(self):
        assert "FAILED_LOCK" in _TERMINAL_STATES


class TestEC048USDCConfirmationDelay:
    """EC-048: USDC adapter is a valid adapter type."""

    def test_usdc_base_adapter_valid(self):
        settlement = _settlement_base()
        settlement["adapter"] = "usdc_base"
        errors = _validate_settlement(settlement)
        assert not errors

    def test_usdc_ethereum_adapter_valid(self):
        settlement = _settlement_base()
        settlement["adapter"] = "usdc_ethereum"
        errors = _validate_settlement(settlement)
        assert not errors


class TestEC049AdapterPartialSuccess:
    """EC-049: RELEASE_FAILED state exists for partial adapter failures."""

    def test_release_failed_is_valid_state(self):
        settlement = _settlement_base()
        settlement["state"] = "RELEASE_FAILED"
        errors = _validate_settlement(settlement)
        assert not errors

    def test_release_failed_is_terminal(self):
        assert "RELEASE_FAILED" in _TERMINAL_STATES


class TestEC050TestAdapterOutOfFunds:
    """EC-050: Test adapter is a valid adapter type."""

    def test_test_adapter_valid(self):
        settlement = _settlement_base()
        settlement["adapter"] = "test"
        errors = _validate_settlement(settlement)
        assert not errors


class TestEC051AdapterTypeMismatch:
    """EC-051: Invalid adapter types are rejected by schema."""

    def test_invalid_adapter_type_fails(self):
        settlement = _settlement_base()
        settlement["adapter"] = "paypal"
        errors = _validate_settlement(settlement)
        assert errors, "Unsupported adapter type should fail schema validation"

    def test_valid_adapter_types(self):
        for adapter in ["stripe", "usdc_base", "usdc_ethereum", "test"]:
            settlement = _settlement_base()
            settlement["adapter"] = adapter
            errors = _validate_settlement(settlement)
            assert not errors, f"Adapter '{adapter}' should be valid"


class TestEC052NetworkPartitionDuringLock:
    """EC-052: Settlement has idempotency_key for safe retries."""

    def test_idempotency_key_required(self):
        settlement = _settlement_base()
        del settlement["idempotency_key"]
        errors = _validate_settlement(settlement)
        assert errors, "Missing idempotency_key should fail"

    def test_idempotency_key_format_enforced(self):
        settlement = _settlement_base()
        settlement["idempotency_key"] = "bad_key_format"
        errors = _validate_settlement(settlement)
        assert errors, "Bad idempotency_key format should fail"

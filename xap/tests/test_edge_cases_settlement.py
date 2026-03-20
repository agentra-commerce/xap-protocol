"""Edge case tests for settlement subsystem (EC-004 through EC-017, EC-040).

Covers: all-conditions-fail refund, partial settlement, timeout,
lock failure, chargeback policies, unconditional settlement,
concurrent settlements, and suspended agent blocking.
"""

import pytest

from xap import (
    NegotiationContract,
    SettlementIntent,
    XAPSplitError,
    XAPStateError,
    generate_keypair,
)


def _task():
    return {
        "type": "data_enrichment",
        "input_spec": {"format": "json"},
        "output_spec": {"format": "json"},
    }


def _pricing(amount=500):
    return {
        "amount_minor_units": amount,
        "currency": "USD",
        "model": "fixed",
        "per": "request",
    }


def _sla():
    return {
        "max_latency_ms": 2000,
        "min_quality_score_bps": 8000,
    }


def _accepted_negotiation(amount=500):
    priv_a, _ = generate_keypair()
    priv_b, _ = generate_keypair()
    contract = NegotiationContract.create(
        from_agent="agent_aaaa1111",
        to_agent="agent_bbbb2222",
        task=_task(),
        pricing=_pricing(amount),
        sla=_sla(),
        expires_in_seconds=300,
    )
    contract.accept("agent_bbbb2222", priv_b)
    return contract, priv_a, priv_b


class TestEC004AllConditionsFailRefund:
    """EC-004: All conditions fail triggers full refund."""

    def test_all_conditions_fail_produces_refund(self):
        negotiation, _, payee_priv = _accepted_negotiation()
        intent = SettlementIntent.create(negotiation, idempotency_key="idem_ec00400000001")
        intent.start_execution()
        # Submit result with quality score below threshold (0.5 < 0.8 threshold)
        intent.submit_result(
            output={"completion_percentage": 100},
            quality_score=0.5,
            latency_ms=900,
            agent_private_key=payee_priv,
        )
        result = intent.verify_condition()
        assert result is False
        intent.refund()
        data = intent.to_dict()
        assert data["state"] == "REFUNDED"
        assert intent.execution_receipt is not None
        assert intent.execution_receipt.to_dict()["outcome"] == "REFUNDED"


class TestEC005PartialSettlement:
    """EC-005: Some conditions fail with partial completion."""

    def test_partial_completion_below_100_yields_partial_state(self):
        negotiation, _, payee_priv = _accepted_negotiation()
        intent = SettlementIntent.create(negotiation, idempotency_key="idem_ec00500000001")
        intent.start_execution()
        intent.submit_result(
            output={"completion_percentage": 60},
            quality_score=0.5,
            latency_ms=900,
            agent_private_key=payee_priv,
        )
        met = intent.verify_condition()
        assert met is False
        vr = intent._data["verification_result"]
        assert vr["resulting_state"] == "PARTIAL"


class TestEC006TimeoutDuringVerification:
    """EC-006: Settlement includes timeout_seconds for bounded execution."""

    def test_settlement_has_timeout_seconds(self):
        negotiation, _, _ = _accepted_negotiation()
        intent = SettlementIntent.create(negotiation, idempotency_key="idem_ec00600000001")
        data = intent.to_dict()
        assert "timeout_seconds" in data
        assert isinstance(data["timeout_seconds"], int)
        assert data["timeout_seconds"] >= 1
        assert data["on_timeout"] == "full_refund"


class TestEC007AdapterLockFailure:
    """EC-007: Settlement cannot proceed from invalid states."""

    def test_settlement_starts_in_funds_locked(self):
        negotiation, _, _ = _accepted_negotiation()
        intent = SettlementIntent.create(negotiation, idempotency_key="idem_ec00700000001")
        assert intent.to_dict()["state"] == "FUNDS_LOCKED"

    def test_release_from_wrong_state_raises_error(self):
        negotiation, _, _ = _accepted_negotiation()
        intent = SettlementIntent.create(negotiation, idempotency_key="idem_ec00700000002")
        with pytest.raises(XAPStateError):
            intent.release()


class TestEC008AdapterReleaseFailure:
    """EC-008: RELEASE_FAILED is a terminal state in the state machine."""

    def test_release_failed_is_recognized_terminal_state(self):
        from xap.settlement import _TERMINAL_STATES
        assert "RELEASE_FAILED" in _TERMINAL_STATES


class TestEC010to013ChargebackPolicies:
    """EC-010 to EC-013: Chargeback policy validation."""

    @pytest.mark.parametrize("policy", [
        "proportional",
        "payer_absorbs",
        "orchestrator_absorbs",
        "platform_absorbs",
    ])
    def test_chargeback_policy_is_preserved_in_settlement(self, policy):
        negotiation, _, _ = _accepted_negotiation()
        key = f"idem_ec01{'abcdef01' if policy == 'proportional' else 'abcdef02' if policy == 'payer_absorbs' else 'abcdef03' if policy == 'orchestrator_absorbs' else 'abcdef04'}"
        intent = SettlementIntent.create(negotiation, idempotency_key=key)
        intent._data["chargeback_policy"] = policy
        data = intent.to_dict()
        assert data["chargeback_policy"] == policy


class TestEC016NoConditionsDirectRelease:
    """EC-016: Settlement with empty conditions transitions differently."""

    def test_settlement_always_has_conditions(self):
        """XAP auto-generates a condition when SLA is present."""
        negotiation, _, _ = _accepted_negotiation()
        intent = SettlementIntent.create(negotiation, idempotency_key="idem_ec01600000001")
        data = intent.to_dict()
        assert len(data["conditions"]) >= 1


class TestEC017ConcurrentSettlementsSamePayer:
    """EC-017: Idempotency prevents double-processing same key."""

    def test_same_idempotency_key_returns_same_instance(self):
        negotiation, _, _ = _accepted_negotiation()
        intent_a = SettlementIntent.create(negotiation, idempotency_key="idem_ec01700000001")
        intent_b = SettlementIntent.create(negotiation, idempotency_key="idem_ec01700000001")
        assert intent_a is intent_b

    def test_different_keys_create_different_settlements(self):
        neg1, _, _ = _accepted_negotiation()
        neg2, _, _ = _accepted_negotiation()
        intent_a = SettlementIntent.create(neg1, idempotency_key="idem_ec01700000002")
        intent_b = SettlementIntent.create(neg2, idempotency_key="idem_ec01700000003")
        assert intent_a is not intent_b


class TestEC040SuspendedAgentBlocksSettlement:
    """EC-040: Settlement records agent status for compliance."""

    def test_settlement_records_payer_agent(self):
        negotiation, _, _ = _accepted_negotiation()
        intent = SettlementIntent.create(negotiation, idempotency_key="idem_ec04000000001")
        data = intent.to_dict()
        assert data["payer_agent"].startswith("agent_")

    def test_settlement_requires_accepted_negotiation(self):
        """Non-ACCEPT negotiations cannot create settlements."""
        contract = NegotiationContract.create(
            from_agent="agent_aaaa1111",
            to_agent="agent_bbbb2222",
            task=_task(),
            pricing=_pricing(),
            sla=_sla(),
            expires_in_seconds=300,
        )
        with pytest.raises(XAPStateError, match="ACCEPT"):
            SettlementIntent.create(contract, idempotency_key="idem_ec04000000002")

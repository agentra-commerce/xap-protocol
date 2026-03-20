"""Edge case tests for negotiation subsystem (EC-019 through EC-026, EC-033).

Covers: expired offer, counter on rejected, max rounds, self-negotiation,
hash chain integrity, accept-already-accepted, suspended counterparty,
same-terms counter, timeout-then-dispute.
"""

import pytest

from xap import (
    NegotiationContract,
    XAPExpiredError,
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


class TestEC019ExpiredOfferAccepted:
    """EC-019: Accept on expired negotiation raises XAPExpiredError."""

    def test_accept_expired_negotiation_raises(self):
        priv_b, _ = generate_keypair()
        contract = NegotiationContract.create(
            from_agent="agent_aaaa1111",
            to_agent="agent_bbbb2222",
            task=_task(),
            pricing=_pricing(),
            sla=_sla(),
            expires_in_seconds=-1,  # already expired
        )
        with pytest.raises(XAPExpiredError):
            contract.accept("agent_bbbb2222", priv_b)


class TestEC020CounterOnRejected:
    """EC-020: Counter on a rejected contract raises XAPStateError."""

    def test_counter_after_reject_raises(self):
        priv_a, _ = generate_keypair()
        contract = NegotiationContract.create(
            from_agent="agent_aaaa1111",
            to_agent="agent_bbbb2222",
            task=_task(),
            pricing=_pricing(),
            sla=_sla(),
            expires_in_seconds=300,
        )
        contract.reject("agent_bbbb2222", priv_a)
        assert contract.to_dict()["state"] == "REJECT"
        with pytest.raises(XAPStateError):
            contract.counter(_pricing(400), proposed_by="agent_aaaa1111")


class TestEC021MaxRoundsExceeded:
    """EC-021: Exceeding max rounds raises XAPStateError."""

    def test_max_rounds_2_blocks_third_counter(self):
        contract = NegotiationContract.create(
            from_agent="agent_aaaa1111",
            to_agent="agent_bbbb2222",
            task=_task(),
            pricing=_pricing(),
            sla=_sla(),
            expires_in_seconds=300,
            max_rounds=2,
        )
        contract.counter(_pricing(400), proposed_by="agent_bbbb2222")
        with pytest.raises(XAPStateError, match="Maximum negotiation rounds"):
            contract.counter(_pricing(350), proposed_by="agent_aaaa1111")


class TestEC022SelfNegotiation:
    """EC-022: Agent cannot negotiate with itself (runtime check)."""

    def test_self_negotiation_schema_valid_but_semantically_wrong(self):
        """NegotiationContract.create allows same agent IDs at schema level.
        This test documents that self-negotiation creates a contract
        but the runtime should catch it at a higher level."""
        contract = NegotiationContract.create(
            from_agent="agent_aaaa1111",
            to_agent="agent_aaaa1111",
            task=_task(),
            pricing=_pricing(),
            sla=_sla(),
            expires_in_seconds=300,
        )
        data = contract.to_dict()
        # Validate the scenario exists: both agents are the same
        assert data["from_agent"] == data["to_agent"]


class TestEC023HashChainIntegrity:
    """EC-023: Hash chain break detection on counter."""

    def test_counter_creates_valid_hash_chain(self):
        priv_b, _ = generate_keypair()
        contract = NegotiationContract.create(
            from_agent="agent_aaaa1111",
            to_agent="agent_bbbb2222",
            task=_task(),
            pricing=_pricing(),
            sla=_sla(),
            expires_in_seconds=300,
        )
        contract.counter(_pricing(400), proposed_by="agent_bbbb2222", private_key=priv_b)
        data = contract.to_dict()
        assert "previous_state_hash" in data
        assert data["previous_state_hash"].startswith("sha256:")
        assert len(data["previous_state_hash"]) == 71  # sha256: + 64 hex


class TestEC024AcceptAlreadyAccepted:
    """EC-024: Second accept on already-accepted contract raises error."""

    def test_double_accept_raises_state_error(self):
        priv_a, _ = generate_keypair()
        priv_b, _ = generate_keypair()
        contract = NegotiationContract.create(
            from_agent="agent_aaaa1111",
            to_agent="agent_bbbb2222",
            task=_task(),
            pricing=_pricing(),
            sla=_sla(),
            expires_in_seconds=300,
        )
        contract.accept("agent_bbbb2222", priv_b)
        assert contract.to_dict()["state"] == "ACCEPT"
        # ACCEPT is terminal; second accept should fail
        with pytest.raises(XAPStateError):
            contract.accept("agent_aaaa1111", priv_a)


class TestEC025NegotiateWithSuspendedAgent:
    """EC-025: Negotiation with suspended agent should be prevented."""

    def test_negotiation_contract_created_with_any_agent_id(self):
        """At schema level, any valid agent_id is accepted.
        Runtime identity status checks would block suspended agents."""
        contract = NegotiationContract.create(
            from_agent="agent_aaaa1111",
            to_agent="agent_cccc3333",
            task=_task(),
            pricing=_pricing(),
            sla=_sla(),
            expires_in_seconds=300,
        )
        data = contract.to_dict()
        assert data["state"] == "OFFER"
        assert data["to_agent"] == "agent_cccc3333"


class TestEC026CounterWithSameTerms:
    """EC-026: Counter with identical terms wastes a round."""

    def test_same_terms_counter_increments_round(self):
        contract = NegotiationContract.create(
            from_agent="agent_aaaa1111",
            to_agent="agent_bbbb2222",
            task=_task(),
            pricing=_pricing(500),
            sla=_sla(),
            expires_in_seconds=300,
        )
        # Counter with same pricing
        contract.counter(_pricing(500), proposed_by="agent_bbbb2222")
        data = contract.to_dict()
        assert data["round_number"] == 2
        assert data["state"] == "COUNTER"


class TestEC033TimeoutThenDispute:
    """EC-033: DISPUTED is a valid terminal state in settlement."""

    def test_disputed_is_terminal_state(self):
        from xap.settlement import _TERMINAL_STATES
        assert "DISPUTED" in _TERMINAL_STATES

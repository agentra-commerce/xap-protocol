import pytest

from xap import XAPSplitError, XAPStateError, NegotiationContract, SettlementIntent, generate_keypair


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


def _accepted_negotiation():
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
    contract.counter(_pricing(amount=400), proposed_by="agent_bbbb2222", private_key=priv_b)
    contract.accept("agent_aaaa1111", priv_a)
    return contract


def test_settlement_idempotency_and_happy_path_release():
    payee_priv, _ = generate_keypair()
    negotiation = _accepted_negotiation()

    intent_a = SettlementIntent.create(negotiation, idempotency_key="idem_aa001111")
    intent_b = SettlementIntent.create(negotiation, idempotency_key="idem_aa001111")
    assert intent_a is intent_b

    intent_a.start_execution()
    intent_a.submit_result(output={"completion_percentage": 100}, quality_score=0.91, latency_ms=900, agent_private_key=payee_priv)
    assert intent_a.verify_condition()
    intent_a.release()

    data = intent_a.to_dict()
    assert data["state"] == "SETTLED"
    assert data["payer_agent"] == "agent_aaaa1111"
    assert data["total_amount_minor_units"] == 400
    assert data["currency"] == "USD"
    assert intent_a.execution_receipt is not None


def test_settlement_invalid_state_transition_raises_state_error():
    negotiation = _accepted_negotiation()
    intent = SettlementIntent.create(negotiation, idempotency_key="idem_aa002222")

    with pytest.raises(XAPStateError):
        intent.release()


def test_settlement_split_bps_must_sum_to_10000():
    negotiation = _accepted_negotiation()
    intent = SettlementIntent.create(negotiation, idempotency_key="idem_aa003333")

    # Manually modify payee_agents to have bad split
    intent._data["payee_agents"] = [
        {"agent_id": "agent_bbbb2222", "share_bps": 7000, "role": "primary_executor"},
        {"agent_id": "agent_cccc3333", "share_bps": 2000, "role": "platform"},
    ]

    payee_priv, _ = generate_keypair()
    intent.start_execution()
    intent.submit_result(output={"completion_percentage": 100}, quality_score=0.95, latency_ms=500, agent_private_key=payee_priv)
    intent.verify_condition()

    with pytest.raises(XAPSplitError, match="10000"):
        intent.release()


def test_settlement_split_distributions_integer_math():
    """Verify split amounts are integers and sum to total."""
    negotiation = _accepted_negotiation()
    intent = SettlementIntent.create(negotiation, idempotency_key="idem_aa004444")

    # 3-way split with amounts that don't divide evenly
    intent._data["payee_agents"] = [
        {"agent_id": "agent_bbbb2222", "share_bps": 3333, "role": "primary_executor"},
        {"agent_id": "agent_cccc3333", "share_bps": 3334, "role": "data_provider"},
        {"agent_id": "agent_dddd4444", "share_bps": 3333, "role": "platform"},
    ]

    payee_priv, _ = generate_keypair()
    intent.start_execution()
    intent.submit_result(output={"completion_percentage": 100}, quality_score=0.95, latency_ms=500, agent_private_key=payee_priv)
    intent.verify_condition()
    intent.release()

    distributions = intent.to_dict()["split_distributions"]
    total_distributed = sum(d["amount_minor_units"] for d in distributions)
    assert total_distributed == intent._data["total_amount_minor_units"]
    for d in distributions:
        assert isinstance(d["amount_minor_units"], int)


def test_settlement_refund():
    payee_priv, _ = generate_keypair()
    negotiation = _accepted_negotiation()
    intent = SettlementIntent.create(negotiation, idempotency_key="idem_aa005555")

    intent.start_execution()
    intent.submit_result(output={"completion_percentage": 100}, quality_score=0.5, latency_ms=900, agent_private_key=payee_priv)

    assert not intent.verify_condition()
    intent.refund()
    assert intent.to_dict()["state"] == "REFUNDED"
    assert intent.execution_receipt is not None


def test_end_to_end_register_negotiate_lock_execute_verify_release_receipt():
    initiator_priv, initiator_pub = generate_keypair()
    counterparty_priv, counterparty_pub = generate_keypair()

    from xap import AgentIdentity

    initiator = AgentIdentity.create(
        capabilities=[
            {
                "name": "orchestrate",
                "version": "1.0.0",
                "pricing": {"model": "fixed", "amount_minor_units": 500, "currency": "USD", "per": "request"},
                "sla": {"max_latency_ms": 2000, "availability_bps": 9900},
            }
        ],
        risk_profile={"risk_tier": "low"},
        public_key=initiator_pub,
    )
    initiator.sign(initiator_priv)

    counterparty = AgentIdentity.create(
        capabilities=[
            {
                "name": "data_enrichment",
                "version": "1.0.0",
                "pricing": {"model": "fixed", "amount_minor_units": 350, "currency": "USD", "per": "request"},
                "sla": {"max_latency_ms": 1500, "availability_bps": 9950},
            }
        ],
        risk_profile={"risk_tier": "low"},
        public_key=counterparty_pub,
    )
    counterparty.sign(counterparty_priv)

    negotiation = NegotiationContract.create(
        from_agent=initiator.agent_id,
        to_agent=counterparty.agent_id,
        task=_task(),
        pricing=_pricing(amount=350),
        sla=_sla(),
        expires_in_seconds=300,
    )
    negotiation.counter(_pricing(amount=300), proposed_by=counterparty.agent_id, private_key=counterparty_priv)
    negotiation.accept(initiator.agent_id, initiator_priv)

    settlement = SettlementIntent.create(negotiation, idempotency_key="idem_e2e0aabb")
    settlement.start_execution()
    settlement.submit_result(
        output={"completion_percentage": 100, "result": {"ok": True}},
        quality_score=0.92,
        latency_ms=700,
        agent_private_key=counterparty_priv,
    )
    assert settlement.verify_condition()
    settlement.release()

    receipt = settlement.execution_receipt
    assert receipt is not None
    assert receipt.to_dict()["outcome"] == "SETTLED"

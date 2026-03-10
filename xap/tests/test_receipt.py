import uuid

from xap import ExecutionReceipt, NegotiationContract, SettlementIntent, generate_keypair
from xap.settlement import PLATFORM_PUBLIC_KEY


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


def _released_settlement():
    priv_a, _ = generate_keypair()
    priv_b, _ = generate_keypair()

    negotiation = NegotiationContract.create(
        from_agent="agent_aaaa1111",
        to_agent="agent_bbbb2222",
        task=_task(),
        pricing=_pricing(),
        sla=_sla(),
        expires_in_seconds=300,
    )
    negotiation.accept("agent_bbbb2222", priv_b)

    idem = f"idem_{uuid.uuid4().hex[:16]}"
    settlement = SettlementIntent.create(negotiation, idempotency_key=idem)
    settlement.start_execution()
    settlement.submit_result(output={"completion_percentage": 100}, quality_score=0.9, latency_ms=800, agent_private_key=priv_b)
    settlement.verify_condition()
    settlement.release()
    return settlement


def test_receipt_issued_on_settlement():
    settlement = _released_settlement()
    receipt = settlement.execution_receipt

    assert receipt is not None
    data = receipt.to_dict()
    assert data["outcome"] == "SETTLED"
    # After accept(), from_agent is the acceptor — settlement reads this as payer
    assert data["payer_agent"].startswith("agent_")
    assert len(data["conditions_results"]) >= 1
    assert len(data["payouts"]) >= 1
    assert data["payouts"][0]["status"] == "paid"
    assert data["chain_position"] >= 1
    assert data["verity_hash"].startswith("sha256:")
    assert data["adapter_used"] == "test"
    assert data["finality_status"] == "final"


def test_receipt_signature_verification():
    settlement = _released_settlement()
    receipt = settlement.execution_receipt

    assert receipt is not None
    assert receipt.verify(PLATFORM_PUBLIC_KEY)


def test_receipt_tamper_detection():
    settlement = _released_settlement()
    receipt = settlement.execution_receipt
    assert receipt is not None

    payload = receipt.to_dict()
    # Tamper with outcome
    payload["outcome"] = "REFUNDED"
    # Tamper the engine signature to make from_dict work but verify fail
    payload["signatures"]["settlement_engine"] = "invalid_signature"
    tampered = ExecutionReceipt.from_dict(payload)
    assert not tampered.verify(PLATFORM_PUBLIC_KEY)


def test_receipt_query_by_settlement_id():
    settlement = _released_settlement()
    matches = ExecutionReceipt.query(settlement_id=settlement.settlement_id)
    assert any(item.to_dict()["settlement_id"] == settlement.settlement_id for item in matches)


def test_receipt_execution_metrics():
    settlement = _released_settlement()
    receipt = settlement.execution_receipt
    assert receipt is not None

    metrics = receipt.to_dict()["execution_metrics"]
    assert "execution_started_at" in metrics
    assert "execution_completed_at" in metrics
    assert metrics["execution_duration_ms"] >= 0
    assert metrics["timeout_triggered"] is False
    assert metrics["retries_attempted"] == 0


def test_receipt_reputation_impacts():
    settlement = _released_settlement()
    receipt = settlement.execution_receipt
    assert receipt is not None

    impacts = receipt.to_dict()["reputation_impacts"]
    assert len(impacts) >= 2  # at least one payee + payer
    roles = {i["role_in_settlement"] for i in impacts}
    assert "payee" in roles
    assert "payer" in roles

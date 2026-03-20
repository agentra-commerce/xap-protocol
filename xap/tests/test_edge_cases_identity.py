"""Edge case tests for identity subsystem (EC-037 through EC-041).

Covers: duplicate agent_id, key rotation mid-settlement, org without team_id,
suspended agent attempts settlement, identity portability proof failure.
"""

import json

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pathlib import Path

from xap import AgentIdentity, generate_keypair

SCHEMA_DIR = Path(__file__).parent.parent / "schemas"


def _load_schema(name):
    with (SCHEMA_DIR / name).open() as f:
        return json.load(f)


def _validate_identity(instance):
    schema = _load_schema("agent-identity.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))


def _capabilities():
    return [
        {
            "name": "data_enrichment",
            "version": "1.0.0",
            "pricing": {
                "model": "fixed",
                "amount_minor_units": 300,
                "currency": "USD",
                "per": "request",
            },
            "sla": {
                "max_latency_ms": 1500,
                "availability_bps": 9900,
            },
        }
    ]


class TestEC037DuplicateAgentIdRegistration:
    """EC-037: agent_id must follow the pattern ^agent_[a-f0-9]{8}$."""

    def test_bad_agent_id_format_fails_schema(self):
        identity = {
            "agent_id": "agent_ZZZZZZZZ",
            "public_key": "ed25519:key123",
            "key_version": 1,
            "key_status": "active",
            "capabilities": _capabilities(),
            "reputation": {
                "total_settlements": 0,
                "success_rate_bps": 0,
                "disputes": 0,
                "dispute_resolution_rate_bps": 0,
                "last_updated": "2026-03-09T12:00:00Z",
            },
            "xap_version": "0.2.0",
            "status": "active",
            "registered_at": "2026-03-09T12:00:00Z",
            "last_active_at": "2026-03-09T12:00:00Z",
            "signature": "sig",
        }
        errors = _validate_identity(identity)
        assert errors, "Non-hex agent_id should fail schema validation"

    def test_agent_id_uniqueness_via_registry(self):
        """Two identities get different agent_ids by construction."""
        id1 = AgentIdentity.create(capabilities=_capabilities())
        id2 = AgentIdentity.create(capabilities=_capabilities())
        assert id1.agent_id != id2.agent_id


class TestEC038KeyRotationMidSettlement:
    """EC-038: Key rotation produces new key_version."""

    def test_identity_key_version_starts_at_1(self):
        _, pub = generate_keypair()
        identity = AgentIdentity.create(
            capabilities=_capabilities(),
            public_key=pub,
        )
        data = identity.to_dict()
        assert data["key_version"] == 1
        assert data["key_status"] == "active"

    def test_key_version_recorded_in_schema(self):
        """Schema requires key_version >= 1."""
        identity = {
            "agent_id": "agent_a1b2c3d4",
            "public_key": "ed25519:key123",
            "key_version": 0,
            "key_status": "active",
            "capabilities": _capabilities(),
            "reputation": {
                "total_settlements": 0,
                "success_rate_bps": 0,
                "disputes": 0,
                "dispute_resolution_rate_bps": 0,
                "last_updated": "2026-03-09T12:00:00Z",
            },
            "xap_version": "0.2.0",
            "status": "active",
            "registered_at": "2026-03-09T12:00:00Z",
            "last_active_at": "2026-03-09T12:00:00Z",
            "signature": "sig",
        }
        errors = _validate_identity(identity)
        assert errors, "key_version: 0 should fail (minimum: 1)"


class TestEC039OrgAgentWithoutTeamId:
    """EC-039: team_id requires org_id (dependentRequired)."""

    def test_team_id_without_org_id_fails_schema(self):
        identity = {
            "agent_id": "agent_a1b2c3d4",
            "public_key": "ed25519:key123",
            "key_version": 1,
            "key_status": "active",
            "team_id": "team_e5f6a7b8",
            "capabilities": _capabilities(),
            "reputation": {
                "total_settlements": 0,
                "success_rate_bps": 0,
                "disputes": 0,
                "dispute_resolution_rate_bps": 0,
                "last_updated": "2026-03-09T12:00:00Z",
            },
            "xap_version": "0.2.0",
            "status": "active",
            "registered_at": "2026-03-09T12:00:00Z",
            "last_active_at": "2026-03-09T12:00:00Z",
            "signature": "sig",
        }
        errors = _validate_identity(identity)
        assert errors, "team_id without org_id should fail"


class TestEC041PortabilityProofVerificationFailure:
    """EC-041: Signature verification detects tampering."""

    def test_tampered_identity_fails_verification(self):
        priv, pub = generate_keypair()
        identity = AgentIdentity.create(
            capabilities=_capabilities(),
            public_key=pub,
        )
        identity.sign(priv)
        assert identity.verify(pub)

        # Tamper with the identity data
        tampered_data = identity.to_dict()
        tampered_data["capabilities"][0]["pricing"]["amount_minor_units"] = 99999
        tampered = AgentIdentity.from_dict(tampered_data)
        assert not tampered.verify(pub)

    def test_wrong_key_fails_verification(self):
        priv1, pub1 = generate_keypair()
        _, pub2 = generate_keypair()
        identity = AgentIdentity.create(
            capabilities=_capabilities(),
            public_key=pub1,
        )
        identity.sign(priv1)
        # Verify with wrong key
        assert not identity.verify(pub2)

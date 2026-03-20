"""Edge case tests for discovery subsystem (EC-042 through EC-046).

Covers: empty registry query, no matching agents, pagination cursor expired,
query for suspended agents, relevance weight sum validation.
"""

import json

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pathlib import Path

SCHEMA_DIR = Path(__file__).parent.parent / "schemas"


def _load_schema(name):
    with (SCHEMA_DIR / name).open() as f:
        return json.load(f)


def _validate_query(instance):
    schema = _load_schema("registry-query.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))


def _validate_response(instance):
    schema = _load_schema("registry-response.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))


class TestEC042EmptyRegistryQuery:
    """EC-042: Query with empty filters is schema-valid.
    Runtime validation should reject it (EMPTY_QUERY_FORBIDDEN)."""

    def test_empty_filters_passes_schema(self):
        query = {
            "query_id": "qry_a1b2c3d4",
            "querying_agent_id": "agent_7f3a9b2c",
            "filters": {},
            "xap_version": "0.2.0",
        }
        errors = _validate_query(query)
        # Schema allows empty filters; runtime rejects
        assert not errors

    def test_query_with_filter_is_valid(self):
        query = {
            "query_id": "qry_a1b2c3d4",
            "querying_agent_id": "agent_7f3a9b2c",
            "filters": {"capability": {"name": "text_summarization"}},
            "xap_version": "0.2.0",
        }
        assert not _validate_query(query)


class TestEC043NoMatchingAgentsFound:
    """EC-043: Empty results array is valid response."""

    def test_empty_results_is_valid_response(self):
        response = {
            "query_id": "qry_a1b2c3d4",
            "results": [],
            "total_count": 0,
            "pagination": {"has_more": False, "limit": 20},
            "responded_at": "2026-03-10T09:15:32Z",
            "xap_version": "0.2.0",
        }
        errors = _validate_response(response)
        assert not errors


class TestEC044PaginationCursorExpired:
    """EC-044: Pagination with cursor is schema-valid."""

    def test_pagination_with_cursor_is_valid(self):
        query = {
            "query_id": "qry_a1b2c3d4",
            "querying_agent_id": "agent_7f3a9b2c",
            "filters": {"capability": {"name": "text_summarization"}},
            "pagination": {"cursor": "eyJvZmZzZXQiOjV9", "limit": 10},
            "xap_version": "0.2.0",
        }
        assert not _validate_query(query)

    def test_pagination_limit_exceeds_max_fails(self):
        query = {
            "query_id": "qry_a1b2c3d4",
            "querying_agent_id": "agent_7f3a9b2c",
            "filters": {"capability": {"name": "text_summarization"}},
            "pagination": {"limit": 500},
            "xap_version": "0.2.0",
        }
        errors = _validate_query(query)
        assert errors, "Pagination limit > 100 should fail"


class TestEC045QueryForSuspendedAgents:
    """EC-045: Status filter supports 'suspended' value."""

    def test_suspended_status_filter_is_valid(self):
        query = {
            "query_id": "qry_a1b2c3d4",
            "querying_agent_id": "agent_7f3a9b2c",
            "filters": {"status": "suspended"},
            "xap_version": "0.2.0",
        }
        assert not _validate_query(query)

    def test_invalid_status_filter_fails(self):
        query = {
            "query_id": "qry_a1b2c3d4",
            "querying_agent_id": "agent_7f3a9b2c",
            "filters": {"status": "banned"},
            "xap_version": "0.2.0",
        }
        errors = _validate_query(query)
        assert errors, "Invalid status value should fail"


class TestEC046RelevanceWeightSum:
    """EC-046: Weights that don't sum to 10000 are schema-valid
    but must be caught at runtime."""

    def test_weights_within_bounds_are_schema_valid(self):
        query = {
            "query_id": "qry_a1b2c3d4",
            "querying_agent_id": "agent_7f3a9b2c",
            "filters": {"capability": {"name": "text_summarization"}},
            "sort": {
                "field": "relevance",
                "weights": {
                    "reputation_weight_bps": 3000,
                    "price_weight_bps": 2500,
                    "latency_weight_bps": 2500,
                    "availability_weight_bps": 2000,
                },
            },
            "xap_version": "0.2.0",
        }
        assert not _validate_query(query)

    def test_weight_over_10000_fails_schema(self):
        query = {
            "query_id": "qry_a1b2c3d4",
            "querying_agent_id": "agent_7f3a9b2c",
            "filters": {"capability": {"name": "text_summarization"}},
            "sort": {
                "field": "relevance",
                "weights": {
                    "reputation_weight_bps": 15000,
                },
            },
            "xap_version": "0.2.0",
        }
        errors = _validate_query(query)
        assert errors, "Weight > 10000 should fail schema validation"

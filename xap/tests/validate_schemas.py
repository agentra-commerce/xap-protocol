"""Validates XAP example files against their schemas.

Runs both valid examples (must pass) and invalid examples (must fail).
Supports both `python -m xap.tests.validate_schemas` and `pytest`.
"""

import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_DIR = Path(__file__).parent.parent / "schemas"
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
INVALID_DIR = Path(__file__).parent / "invalid"

SCHEMA_EXAMPLE_MAP = {
    "agent-manifest.json": [
        "agent-manifest-simple.json",
        "agent-manifest-production.json",
    ],
    "agent-identity.json": [
        "agent-identity-simple.json",
        "agent-identity-complex.json",
    ],
    "negotiation-contract.json": [
        "negotiation-simple-offer.json",
        "negotiation-simple-accept.json",
        "negotiation-complex-offer.json",
        "negotiation-complex-counter.json",
    ],
    "settlement-intent.json": [
        "settlement-simple.json",
        "settlement-complex-split.json",
        "settlement-usdc-confirmation.json",
    ],
    "execution-receipt.json": [
        "receipt-simple-settled.json",
        "receipt-partial-split.json",
    ],
    "verity-receipt.json": [
        "verity-simple-deterministic.json",
        "verity-complex-partial.json",
    ],
    "registry-query.json": [
        "registry-query-simple.json",
        "registry-query-complex.json",
        "registry-query-org.json",
    ],
    "registry-response.json": [
        "registry-response-simple.json",
        "registry-response-complex.json",
    ],
}

# Maps schema file names to their invalid example directories
SCHEMA_INVALID_DIR_MAP = {
    "agent-manifest.json": "agent-manifest",
    "agent-identity.json": "agent-identity",
    "negotiation-contract.json": "negotiation-contract",
    "settlement-intent.json": "settlement-intent",
    "execution-receipt.json": "execution-receipt",
    "verity-receipt.json": "verity-receipt",
    "registry-query.json": "registry-query",
    "registry-response.json": "registry-response",
}


def _load_schema(schema_path: Path) -> dict:
    with schema_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _get_errors(schema: dict, instance: dict) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
    return [
        f"  {'.'.join(str(p) for p in err.absolute_path) or '<root>'}: {err.message}"
        for err in errors
    ]


# ---------------------------------------------------------------------------
# pytest parametrized tests
# ---------------------------------------------------------------------------

def _collect_valid_cases():
    cases = []
    for schema_name, example_names in SCHEMA_EXAMPLE_MAP.items():
        for example_name in example_names:
            cases.append((schema_name, example_name))
    return cases


def _collect_invalid_cases():
    cases = []
    for schema_name, invalid_dir_name in SCHEMA_INVALID_DIR_MAP.items():
        invalid_dir = INVALID_DIR / invalid_dir_name
        if not invalid_dir.exists():
            continue
        for invalid_file in sorted(invalid_dir.glob("*.json")):
            cases.append((schema_name, invalid_dir_name, invalid_file.name))
    return cases


@pytest.mark.parametrize("schema_name,example_name", _collect_valid_cases(),
                         ids=[f"valid/{c[1]}" for c in _collect_valid_cases()])
def test_valid_example_passes(schema_name, example_name):
    schema = _load_schema(SCHEMA_DIR / schema_name)
    example = _load_json(EXAMPLES_DIR / example_name)
    errors = _get_errors(schema, example)
    assert not errors, f"{example_name} should pass validation:\n" + "\n".join(errors)


@pytest.mark.parametrize("schema_name,invalid_dir_name,invalid_file", _collect_invalid_cases(),
                         ids=[f"invalid/{c[1]}/{c[2]}" for c in _collect_invalid_cases()])
def test_invalid_example_fails(schema_name, invalid_dir_name, invalid_file):
    schema = _load_schema(SCHEMA_DIR / schema_name)
    example = _load_json(INVALID_DIR / invalid_dir_name / invalid_file)
    errors = _get_errors(schema, example)
    assert errors, f"{invalid_dir_name}/{invalid_file} should FAIL validation but passed"


# ---------------------------------------------------------------------------
# Standalone runner (python -m xap.tests.validate_schemas)
# ---------------------------------------------------------------------------

def main() -> int:
    total = 0
    passed = 0
    failed = 0

    print("=" * 60)
    print("VALID EXAMPLES (must pass)")
    print("=" * 60)

    for schema_name, example_names in SCHEMA_EXAMPLE_MAP.items():
        schema_path = SCHEMA_DIR / schema_name
        if not schema_path.exists():
            print(f"SKIP  schema not found: {schema_name}")
            continue
        schema = _load_schema(schema_path)

        for example_name in example_names:
            example_path = EXAMPLES_DIR / example_name
            total += 1
            if not example_path.exists():
                print(f"FAIL  {example_name} — file not found")
                failed += 1
                continue

            errors = _get_errors(schema, _load_json(example_path))
            if errors:
                print(f"FAIL  {example_name} against {schema_name}")
                for err in errors:
                    print(err)
                failed += 1
            else:
                print(f"PASS  valid/{example_name}")
                passed += 1

    print()
    print("=" * 60)
    print("INVALID EXAMPLES (must fail)")
    print("=" * 60)

    for schema_name, invalid_dir_name in SCHEMA_INVALID_DIR_MAP.items():
        schema_path = SCHEMA_DIR / schema_name
        if not schema_path.exists():
            continue
        schema = _load_schema(schema_path)

        invalid_dir = INVALID_DIR / invalid_dir_name
        if not invalid_dir.exists():
            print(f"SKIP  no invalid dir for {schema_name}")
            continue

        for invalid_file in sorted(invalid_dir.glob("*.json")):
            total += 1
            errors = _get_errors(schema, _load_json(invalid_file))
            if errors:
                print(f"PASS  invalid/{invalid_dir_name}/{invalid_file.name} (rejected as expected)")
                passed += 1
            else:
                print(f"FAIL  invalid/{invalid_dir_name}/{invalid_file.name} — should have been rejected but PASSED")
                failed += 1

    print(f"\n{passed}/{total} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

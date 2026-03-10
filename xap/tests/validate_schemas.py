"""Validates XAP example files against their schemas."""

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_DIR = Path(__file__).parent.parent / "schemas"
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"

SCHEMA_EXAMPLE_MAP = {
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
}


def validate_example(schema_path: Path, example_path: Path) -> list[str]:
    with schema_path.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    with example_path.open("r", encoding="utf-8") as f:
        example = json.load(f)

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(example), key=lambda e: list(e.absolute_path))
    return [
        f"  {'.'.join(str(p) for p in err.absolute_path) or '<root>'}: {err.message}"
        for err in errors
    ]


def main() -> int:
    total = 0
    passed = 0
    failed = 0

    for schema_name, example_names in SCHEMA_EXAMPLE_MAP.items():
        schema_path = SCHEMA_DIR / schema_name
        if not schema_path.exists():
            print(f"SKIP  schema not found: {schema_name}")
            continue

        for example_name in example_names:
            example_path = EXAMPLES_DIR / example_name
            total += 1
            if not example_path.exists():
                print(f"FAIL  {example_name} — file not found")
                failed += 1
                continue

            errors = validate_example(schema_path, example_path)
            if errors:
                print(f"FAIL  {example_name} against {schema_name}")
                for err in errors:
                    print(err)
                failed += 1
            else:
                print(f"PASS  {example_name} against {schema_name}")
                passed += 1

    print(f"\n{passed}/{total} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

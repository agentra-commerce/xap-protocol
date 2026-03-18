# Contributing to XAP

Thank you for your interest in contributing to the eXchange Agent Protocol.

XAP is early-stage. The protocol is in draft. The schemas are being hardened. The most impactful contributions right now are feedback and thinking, not code.

## How to Contribute

### 1. Read first

Start with the schemas in `/xap/schemas/`. They are the source of truth. Then read the open issues and discussions to understand what is already being explored.

### 2. Open an issue before writing anything substantial

XAP is a protocol. Changing a field name or adding a required property can break every implementation. All significant changes start as a discussion, not a pull request.

### 3. Use the right label

| Label | Use for |
|---|---|
| `schema-feedback` | Feedback on the five XAP schemas |
| `edge-case` | A scenario the protocol does not handle correctly |
| `vertical-schema` | Domain-specific capability definitions (finance, healthcare, legal, etc.) |
| `implementation-feedback` | Problems encountered while implementing XAP |
| `dispute-resolution` | Ideas for deterministic dispute resolution rules |
| `security` | Security vulnerabilities (see SECURITY.md for responsible disclosure) |

### 4. Edge Case Submissions

Edge cases are tracked in `docs/edge-cases.md` with a formal lifecycle:

1. **DISCOVERED** — identified during development, testing, or community feedback
2. **DOCUMENTED** — added to edge-cases.md with scenario, risk, and proposed resolution
3. **ANALYZED** — resolution validated against protocol invariants
4. **RESOLVED** — resolution implemented in schemas, SDK, or engine
5. **TESTED** — validation test covers this edge case
6. **DEPLOYED** — fix is in a released version

To submit an edge case, open an issue using the Edge Case template.

Severity guide:
- **S1 (Critical):** Could cause financial loss or data corruption
- **S2 (High):** Could cause incorrect settlement or broken invariant
- **S3 (Medium):** Could cause degraded experience or incorrect state
- **S4 (Low):** Cosmetic or unlikely scenario

When submitting, include:
- **Category**: negotiation, settlement, receipt, verity, discovery, identity, adapter, or cross-cutting
- **Scenario**: What happens, step by step
- **Risk**: What goes wrong if unhandled
- **Proposed resolution**: Your suggestion (optional but appreciated)

### What We Are Not Looking For Right Now

- Pull requests that change core protocol objects without a prior discussion
- Implementation code (implementations belong in separate repos)
- Marketing or copy edits

## Code of Conduct

All participants are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

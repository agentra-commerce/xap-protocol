# Changelog

All notable changes to the XAP protocol will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] — March 2026

### Added
- `verity-receipt.json`: Five new optional fields closing institutional-grade
  audit gaps:
  - `timestamp_authority`: RFC 3161 TSA token for independent temporal proof
  - `rules_applied.policy_content_hash`: SHA-256 of governing policy document
  - `rules_applied.policy_url`: Where to retrieve and verify the policy
  - `key_id`: Identifies the specific signing key for historical lookup
  - `causality`: Links receipt to its position in a multi-agent workflow chain
  - `condition_results[].verifier_attestation`: Cryptographic attestation from
    external probabilistic verifiers
- `policy-version.json`: New schema for content-addressed XAP policy documents
- `agent-key-history.json`: New schema for agent Ed25519 key rotation history
- Three new example files

### Migration
All new fields are optional. No existing receipt validation breaks.
Systems that do not implement the new fields produce v0.2-compatible receipts.
Systems that implement all fields produce v0.3-compatible receipts.
v0.2 and v0.3 receipts are accepted by any XAP-compliant verifier.

## [0.2.0] - In Progress

### Added — v0.2 Gap Closure
- **AgentManifest** — sixth primitive (primitive 0). Pre-negotiation trust credential with Ed25519 signature, Verity-backed capability attestations, and economic terms. The first cryptographic proof-of-performance in agent discovery.
- **RegistryQuery** — complete query interface for agent discovery with composite scoring, cursor-based pagination, and AND-combined filters.
- **RegistryQuery response** — ranked agent summaries with relevance scoring and pagination metadata.
- **Federation hints** — `also_registered_at` and `identity_portable_proof` fields in AgentManifest seed v1.1 cross-registry discovery.
- 14 new validation tests for AgentManifest (2 valid examples, 12 invalid edge cases).
- Production and simple manifest examples.

### Changed
- Renamed protocol from ACP to XAP (eXchange Agent Protocol) to differentiate from Stripe/OpenAI Agentic Commerce Protocol
- Renamed schema directory from `/acp/schemas/` to `/xap/schemas/`
- All monetary amounts now use integer minor units (no floating point)
- Split shares now use basis points (integer, 1-10000)
- Primitive count: 5 → 6 (AgentManifest added as primitive 0)

### Added — v0.2 Hardening
- Organizational identity hierarchy (org_id, team_id) in AgentIdentity
- Chargeback policy field in SettlementIntent
- Identity portability mechanism (export/import)
- Verity outcome states: SUCCESS, FAIL, UNKNOWN, DISPUTED, REVERSED
- CONTRIBUTING.md, SECURITY.md, CODE_OF_CONDUCT.md
- Edge case registry with continuous learning system

### Improved
- Schema hardening across all six primitives
- Field-by-field documentation for every schema
- Error codes for every validation failure

## [0.1.0] - 2026-02-25

### Added
- Initial draft of five XAP primitive schemas
  - AgentIdentity
  - NegotiationContract
  - SettlementIntent
  - ExecutionReceipt
  - VerityReceipt (partial)
- README with protocol overview
- MIT License

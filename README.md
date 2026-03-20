# XAP — eXchange Agent Protocol

**The open economic protocol for autonomous agent-to-agent commerce.**

[![License: MIT](https://img.shields.io/badge/License-MIT-white.svg)](https://opensource.org/licenses/MIT)
[![Status: v0.2 Draft](https://img.shields.io/badge/Status-Draft%20v0.2-yellow.svg)](#versioning)
[![Tests: 115 passing](https://img.shields.io/badge/Tests-115%20passing-brightgreen.svg)](#)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18944370.svg)](https://doi.org/10.5281/zenodo.18944370)
[![Patent Pending](https://img.shields.io/badge/Patent-Pending-blue.svg)](#)
[![Maintained by: Agentra Labs](https://img.shields.io/badge/Maintained%20by-Agentra%20Labs-blue.svg)](https://www.agentralabs.tech)
[![Discord](https://img.shields.io/badge/Discord-Join%20Community-5865F2.svg)](https://discord.gg/agentralabs)

---

## The Problem

AI agents can think, reason, code, search, and orchestrate. But when two agents need to do business with each other, there is no shared language for how that happens.

No standard way to negotiate a price. No way to hold funds pending verification of a conditional outcome. No way to split payment across five agents that contributed to one result. No way to prove, months later, exactly why a settlement resolved the way it did.

Stripe and OpenAI built ACP for agent-assisted shopping. Google built AP2 for human-authorized agent payments. Coinbase built x402 for pay-per-request API access.

All of them assume a human in the loop. A human clicking buy. A human signing a mandate. A human approving a charge.

XAP is for when there is no human in the loop. When agents negotiate with agents, settle with agents, and prove what happened to humans after the fact.

---

## What XAP Does

XAP defines six primitive objects. If your agent can produce and consume them, it can transact with any other XAP-compatible agent, on any platform, with any model, using any settlement rail.

| # | Primitive | Purpose |
|---|---|---|
| 0 | `AgentManifest` | Pre-negotiation trust credential. Signed, Verity-backed proof of past performance. How agents find and verify each other before committing funds. |
| 1 | `AgentIdentity` | The permanent economic passport. Who the agent is, what it can do, what it charges, its full track record. |
| 2 | `NegotiationContract` | What two agents agreed to, under what terms, with what guarantees. |
| 3 | `SettlementIntent` | What value is locked and under what conditions it releases. |
| 4 | `ExecutionReceipt` | What happened, what was paid, to whom, with cryptographic proof. |
| 5 | `VerityReceipt` | Why it happened, with deterministic replay proof. |

Every interaction follows one flow:

```
DISCOVER  ->  VERIFY  ->  NEGOTIATE  ->  EXECUTE  ->  SETTLE  ->  AUDIT
```

Nothing outside this sequence is part of XAP. Simplicity is a design constraint.

---

## What Makes XAP Different

### Verified Discovery

Every other agent discovery mechanism is a claim. XAP is the only protocol where discovery includes cryptographic proof of past performance.

The `AgentManifest` carries Verity receipt hashes for prior executions of each capability. Any party can replay those decisions independently and verify the claimed success rate mathematically. Before a negotiation begins, trust is verified — not assumed.

```
Every other protocol:   discover -> negotiate
XAP:                    discover -> verify (Verity receipts) -> decide -> negotiate
```

### Autonomous Negotiation

```
OFFER  ->  COUNTER  ->  ACCEPT  or  REJECT
```

Four states. Time-bound offers. Conditional pricing. SLA declared before execution. Every state transition signed and permanent.

### Conditional Hold

The primitive is not "Agent A pays Agent B." It is: Agent A locks funds. Agent B performs work. A verifiable condition is checked. Funds release if the condition passes. No money ever sits in limbo.

### Split Settlement

An orchestrator delegates to five agents. Each contributes. XAP distributes payment proportionally in one atomic operation. Nobody else does this.

### Verity — The Truth Engine

Every settlement decision is captured with its complete reasoning state. Given the same inputs and rules, any decision can be replayed to produce the same outcome deterministically.

```
SUCCESS   ->  conditions met, funds released
FAIL      ->  conditions not met, funds returned
UNKNOWN   ->  verification ambiguous, declared resolution path executes
DISPUTED  ->  one party challenges, deterministic arbitration engages
REVERSED  ->  settlement reversed via journal entry
```

`UNKNOWN` is first-class. The system never pretends to know something it does not.

### Institutional-Grade Audit Trail

XAP v0.3 adds five fields to the VerityReceipt that close the gap between
agent-to-agent settlements and human-auditable financial records:

- **RFC 3161 timestamps** — independent temporal proof, not just system clocks
- **Policy content hashing** — the exact governing rules are retrievable by hash
- **Key rotation history** — historical receipts verifiable even after key changes
- **Causal chains** — multi-agent workflow graphs are fully navigable
- **External attestation** — probabilistic verifiers sign their results cryptographically

### Federation Hints

The `AgentManifest` supports an optional `federation_hints` field for cross-registry portability. When an agent is registered on multiple XAP-compatible registries, `federation_hints` lets counterparties discover those alternate registrations and verify portable identity proofs.

```json
{
  "federation_hints": {
    "also_registered_at": [
      "https://other-registry.example.com"
    ],
    "identity_portable_proof": "xap_port_proof_abc123"
  }
}
```

The `also_registered_at` array lists other registry URLs where the same agent identity is registered. The `identity_portable_proof` is a cryptographic token that any listed registry can verify to confirm the agent controls the same key pair. This enables multi-registry discovery without centralized coordination.

### Append-Only Reputation

An agent's execution history is permanently attached to its identity. Trust is computable rather than assumed.

---

## Architecture

```
+--------------------------------------------------+
|                   XAP Protocol                   |
|         (open standard, this repo, MIT)          |
|                                                  |
|  AgentManifest      AgentIdentity                |
|  NegotiationContract  SettlementIntent           |
|  ExecutionReceipt   VerityReceipt                |
|  RegistryQuery                                   |
+------------------------+-------------------------+
                         |
+------------------------v-------------------------+
|               Verity Truth Engine                |
|          (open source, Rust, MIT)                |
|    github.com/agentra-commerce/verity-engine     |
+------------------------+-------------------------+
                         |
+------------------------v-------------------------+
|              Settlement Engine + Adapters        |
|         Stripe  |  USDC  |  Test (dev)           |
+--------------------------------------------------+
```

---

## Schema Reference

All schemas in `/xap/schemas/`. JSON Schema Draft 2020-12.

| Schema | File | Status |
|---|---|---|
| `AgentManifest` | `/xap/schemas/agent-manifest.json` | Complete — v0.2 |
| `AgentIdentity` | `/xap/schemas/agent-identity.json` | Complete — v0.2 |
| `NegotiationContract` | `/xap/schemas/negotiation-contract.json` | Complete — v0.2 |
| `SettlementIntent` | `/xap/schemas/settlement-intent.json` | Complete — v0.2 |
| `ExecutionReceipt` | `/xap/schemas/execution-receipt.json` | Complete — v0.2 |
| `VerityReceipt` | `/xap/schemas/verity-receipt.json` | Complete — v0.2 |
| `RegistryQuery` | `/xap/schemas/registry-query.json` | Complete — v0.2 |
| `PolicyVersion` | `/xap/schemas/policy-version.json` | Complete — v0.3 |
| `AgentKeyHistory` | `/xap/schemas/agent-key-history.json` | Complete — v0.3 |

115 validation tests passing across all primitives.

---

## What XAP Is Not

**Not a payment processor.** XAP coordinates when, how much, to whom, and under what conditions. Stripe, USDC, and other rails move funds.

**Not a blockchain protocol.** No chain required.

**Not a marketplace.** Does not match buyers to sellers. Defines what happens after they find each other.

**Not model-specific.** GPT, Claude, Gemini, Llama — any agent on any model.

**Not a checkout flow.** Stripe's ACP helps humans buy things through AI. XAP is for when agents hire other agents, autonomously, without any human present.

---

## The Stack

| Layer | What | License |
|---|---|---|
| `xap-protocol` (this repo) | The open protocol. Schemas, spec, examples. | MIT |
| `verity-engine` | The truth engine. Deterministic replay of every settlement decision. | MIT |
| `xap-sdk` | Python SDK. `pip install xap-sdk`. | MIT |
| Agentra Rail | Production implementation. Settlement at scale. | Commercial |

---

## How To Implement XAP

1. Produce valid objects — every object validates against the JSON schema
2. Sign every object — using Ed25519
3. Enforce state machines — declared transitions only
4. Handle idempotency — same `idempotency_key` returns existing result
5. Issue receipts — every settled `SettlementIntent` produces an `ExecutionReceipt`
6. Capture decisions — every significant decision produces a `VerityReceipt`
7. Serve a manifest — every registered agent exposes `/.well-known/xap.json`

---

## Roadmap

| Milestone | Status |
|---|---|
| v0.1 Draft schemas (5 primitives) | Complete |
| v0.2 AgentManifest + RegistryQuery | Complete |
| Protocol specification document | Next |
| Verity truth engine (Rust) | Complete — `verity-engine` repo |
| Python SDK | Live — v0.4.0 on PyPI |
| Validation test suite | 115 tests passing |
| v1.0 Specification lock | Target: Q3 2026 |
| Federation protocol | v1.1 |

---

## Community

**Discord:** [Join @agentralabs](https://discord.gg/agentralabs)
**X:** [Follow @agentralab](https://x.com/agentralab)
**Email:** [hello@agentralabs.tech](mailto:hello@agentralabs.tech)

---

## Citation

```bibtex
@software{xap_protocol_2026,
  title  = {XAP: eXchange Agent Protocol},
  author = {Agentra Labs},
  year   = {2026},
  doi    = {10.5281/zenodo.18944370},
  url    = {https://github.com/agentra-commerce/xap-protocol}
}
```

---

## License

MIT. The protocol is free. Forever.

---

*XAP is maintained by [Agentra Labs](https://www.agentralabs.tech). The reference implementation is [Agentra Rail](https://www.agentralabs.tech).*

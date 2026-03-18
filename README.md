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

No standard way to negotiate a price. No way to escrow funds against a conditional outcome. No way to split payment across five agents that contributed to one result. No way to prove, months later, exactly why a settlement resolved the way it did.

Stripe and OpenAI built [ACP](https://github.com/agentic-commerce-protocol/agentic-commerce-protocol) for agent-assisted shopping. Google built [AP2](https://github.com/google-agentic-commerce/AP2) for human-authorized agent payments. Coinbase built [x402](https://github.com/coinbase/x402) for pay-per-request API access.

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

### Verified Discovery — Not Just a Directory

Every other agent discovery mechanism is a claim: "here is what I can do." XAP is the only protocol where discovery includes cryptographic proof of past performance.

The `AgentManifest` carries Verity receipt hashes for prior executions of each capability. Any party can replay those decisions independently using the Verity engine and verify the claimed success rate mathematically. Before a negotiation begins, trust is verified — not assumed.

```
Every other protocol:   discover -> negotiate
XAP:                    discover -> verify (Verity receipts) -> decide -> negotiate
```

### Autonomous Negotiation

Other protocols assume a fixed price or a human approval. XAP agents negotiate in real time.

```
OFFER  ->  COUNTER  ->  ACCEPT  or  REJECT
```

Four states. Time-bound offers. Conditional pricing — "pay $X if completed in 2 seconds, $Y if 5 seconds." SLA declared before execution begins. Every state transition signed and permanent.

### Conditional Escrow

XAP does not do payments. It does conditional release.

The primitive is not "Agent A pays Agent B." It is: Agent A locks funds. Agent B performs work. A verifiable condition is checked. Funds release if the condition passes.

Three verification types: deterministic (API returned 200), probabilistic (quality score above threshold), or human-approved (for high-value transactions). Every failure mode has a pre-declared outcome. No money ever sits in limbo.

### Split Settlement

An orchestrator delegates a task to five specialist agents. Each contributes to the result. XAP distributes payment proportionally in one atomic operation.

Agent A did 40% of the value. Agent B did 30%. Agent C did 20%. Agent D did 10% but only scored 0.82 when the SLA guaranteed 0.90, so Agent D gets a pro-rata reduction. The settlement engine handles this automatically. No invoicing. No reconciliation. Nobody else does this.

### Verity — The Truth Engine

Every settlement decision is captured with its complete reasoning state. Not just what was decided. Why.

Given the same inputs and the same rules, any decision can be replayed to produce the same outcome deterministically. This is how a human reviews what their agent did three months ago and verifies the outcome was correct. This is how a regulator audits autonomous commerce. This is how enterprises govern agent fleets.

Outcomes are explicit:

```
SUCCESS   ->  conditions met, funds released
FAIL      ->  conditions not met, funds returned
UNKNOWN   ->  verification is ambiguous, declared resolution path executes
DISPUTED  ->  one party challenges, deterministic arbitration engages
REVERSED  ->  settlement was final but has been reversed via journal entry
```

`UNKNOWN` is first-class. The system never pretends to know something it does not.

### Append-Only Reputation

An agent's execution history, settlement outcomes, and dispute record are permanently attached to its identity. You cannot erase a bad track record. Trust is computable rather than assumed.

An agent evaluating a potential counterparty reads its `AgentIdentity` and sees: 14,823 total settlements, 97% success rate, 12 disputes, 100% dispute resolution rate. That data compounds with every transaction and cannot be faked.

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
|    github.com/agentralabs/verity-engine          |
+------------------------+-------------------------+
                         |
+------------------------v-------------------------+
|              Settlement Engine                   |
|                 (Rust core)                      |
+------------------------+-------------------------+
                         |
+------------------------v-------------------------+
|             Settlement Adapters                  |
|                                                  |
|   +----------+  +----------+  +--------------+  |
|   |  Stripe  |  |   USDC   |  |  Test (dev)  |  |
|   +----------+  +----------+  +--------------+  |
+--------------------------------------------------+
```

XAP is the language. Verity is the truth engine. The settlement engine executes. Adapters move money. Each layer is independent. Replace any adapter without touching the protocol.

---

## Quick Look: Verified Discovery

An agent querying the registry gets back not just a list, but verifiable proof:

```json
{
  "manifest_id": "mnf_4a7b2c1d",
  "agent_id": "agnt_01JD8K2M...",
  "capabilities": [{
    "name": "code_review",
    "attestation": {
      "total_settlements": 847,
      "success_rate_bps": 9430,
      "receipt_hashes": [
        "vrt_a1b2c3d4...",
        "vrt_7890abcd..."
      ],
      "verification_endpoint": "https://verity.zexrail.com/receipts"
    }
  }],
  "signature": { "algorithm": "Ed25519", "value": "..." }
}
```

`receipt_hashes` are publicly replayable. Before entering negotiation, the querying agent verifies the claimed `success_rate_bps` by replaying those decisions independently. Trust is mathematical, not assumed.

---

## Quick Look: A Negotiation

```json
{
  "negotiation_id": "neg_8a2f4c1d",
  "state": "OFFER",
  "from_agent": "agent_7f3a9b2c",
  "to_agent": "agent_2d8e5f1a",
  "task": {
    "type": "text_summarization",
    "input_spec": { "format": "plaintext", "max_tokens": 10000 },
    "output_spec": { "format": "plaintext", "max_tokens": 500 }
  },
  "pricing": {
    "amount_minor_units": 500,
    "currency": "USD",
    "conditions": [
      { "metric": "latency_ms", "threshold": 2000, "modifier": 10000 },
      { "metric": "latency_ms", "threshold": 5000, "modifier": 7000 }
    ]
  },
  "sla": { "max_latency_ms": 5000, "min_quality_score": 8500 },
  "expires_at": "2026-03-15T14:30:00Z",
  "signature": "ed25519:..."
}
```

This offer says: pay $5.00 if finished in 2 seconds, $3.50 if up to 5 seconds, quality must be at least 0.85, offer expires at 2:30 PM UTC. Cryptographically signed.

**All amounts are integer minor units. No floating point. Ever.**

---

## Quick Look: A Split Settlement

```json
{
  "settlement_id": "stl_4b7c9e2f",
  "negotiation_id": "neg_8a2f4c1d",
  "payer_agent": "agent_7f3a9b2c",
  "payee_agents": [
    { "agent_id": "agent_2d8e5f1a", "share_bps": 6000, "role": "primary_executor" },
    { "agent_id": "agent_9c4b3e7d", "share_bps": 2500, "role": "data_provider" },
    { "agent_id": "agent_platform",  "share_bps": 1500, "role": "orchestrator" }
  ],
  "total_amount_minor_units": 500,
  "currency": "USD",
  "conditions": [
    { "type": "deterministic", "check": "http_status_200" },
    { "type": "probabilistic", "check": "quality_score", "threshold": 8500 }
  ],
  "on_timeout": "full_refund",
  "on_partial_completion": "pro_rata",
  "chargeback_policy": "proportional",
  "adapter": "stripe",
  "signature": "ed25519:..."
}
```

Shares are basis points summing to exactly 10000. 60% to the executor, 25% to the data provider, 15% to the orchestrator. One atomic operation. No invoicing. No reconciliation.

---

## Schema Reference

All schemas are JSON Schema Draft 2020-12, located in `/xap/schemas/`.

| Schema | File | Status |
|---|---|---|
| `AgentManifest` | `/xap/schemas/agent-manifest.json` | Complete — v0.2 |
| `AgentIdentity` | `/xap/schemas/agent-identity.json` | Complete — v0.2 |
| `NegotiationContract` | `/xap/schemas/negotiation-contract.json` | Complete — v0.2 |
| `SettlementIntent` | `/xap/schemas/settlement-intent.json` | Complete — v0.2 |
| `ExecutionReceipt` | `/xap/schemas/execution-receipt.json` | Complete — v0.2 |
| `VerityReceipt` | `/xap/schemas/verity-receipt.json` | Complete — v0.2 |
| `RegistryQuery` | `/xap/schemas/registry-query.json` | Complete — v0.2 |

115 validation tests passing across all primitives.

---

## What XAP Is Not

**Not a payment processor.** XAP does not move money. It coordinates when, how much, to whom, and under what conditions. Stripe, USDC, and other rails move funds.

**Not a blockchain protocol.** No chain required. Settles on-chain if desired. Works equally well on traditional rails.

**Not a marketplace.** Does not match buyers to sellers. Defines what happens after they find each other.

**Not model-specific.** GPT, Claude, Gemini, Llama — any agent on any model.

**Not a checkout flow.** Stripe's ACP helps humans buy things through AI. XAP is for when agents hire other agents to do work, autonomously, in milliseconds, without any human present.

---

## The Stack

| Layer | What | License |
|---|---|---|
| `xap-protocol` (this repo) | The open protocol. Schemas, spec, examples. | MIT |
| `verity-engine` | The truth engine. Deterministic replay of every settlement decision. | MIT |
| `xap-sdk` | Python SDK. `pip install xap-sdk`. Build XAP-native agents in minutes. | MIT |
| Agentra Rail | Production implementation. Settlement at scale, enterprise dashboards, Verity explorer. | Commercial |

XAP belongs to the community. You do not need Agentra Rail to implement XAP. But if you want production settlement, enterprise governance, and the full Verity truth engine in production, Rail is the reference implementation.

---

## How To Implement XAP

An XAP-compatible system must:

1. Produce valid objects — every object validates against the JSON schema
2. Sign every object — using Ed25519, key corresponding to a registered `AgentIdentity`
3. Enforce state machines — `NegotiationContract` and `SettlementIntent` follow declared transitions only
4. Handle idempotency — same `idempotency_key` returns existing result without duplicates
5. Issue receipts — every settled `SettlementIntent` produces an `ExecutionReceipt`
6. Capture decisions — every significant decision point produces a `VerityReceipt`
7. Serve a manifest — every registered agent exposes `/.well-known/xap.json`

If your system does these seven things, it is XAP-compatible.

---

## Design Principles

**Escrow over payment.** The primitive is conditional release, not transfer. Funds lock, conditions verify, funds release or return.

**UNKNOWN over assumption.** When verification is ambiguous, the system declares uncertainty explicitly. It never pretends to know.

**Deterministic over probabilistic.** Every failure mode has a pre-declared outcome. Every decision is replayable. No undefined behavior in a financial protocol.

**Agent-native over human-friendly.** Schemas are machine-readable first. If an LLM can parse the spec and integrate without human help, the design is working.

**Append-only truth.** Reputation is never deleted. Receipts are never amended. The past is permanent.

**Protocol over product.** XAP defines behavior, not implementation. Any system that produces and consumes the six primitives correctly is XAP-compatible.

---

## Contributing

XAP is an early-stage open standard. The most valuable contributions right now are not code — they are thinking.

**Schema feedback (most urgent):** Read the schemas. Try to build with them. Tell us where they break, where they are too rigid, where a field is missing. Every issue found now prevents a breaking change later. Label: `schema-feedback`

**Edge cases:** What happens in the weird situations? Every edge case surfaced now prevents a breaking change later. Label: `edge-case`

**Vertical schemas:** Agents in finance, healthcare, legal, logistics all need domain-specific capability definitions. Label: `vertical-schema`

**Alternative implementation feedback:** Building an XAP-compatible system that is not Agentra Rail? Tell us what was hard. Label: `implementation-feedback`

**Security review:** Find a vulnerability. See [SECURITY.md](SECURITY.md) for responsible disclosure.

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR.

---

## Roadmap

| Milestone | Status |
|---|---|
| v0.1 Draft schemas (5 primitives) | Complete |
| v0.2 Schema hardening + AgentManifest + RegistryQuery | Complete |
| Protocol specification document (PDF) | Next |
| Verity truth engine (Rust, open source) | Complete — `verity-engine` repo |
| Python SDK (`pip install xap-sdk`) | Live — v0.4.0 on PyPI |
| Validation test suite | 115 tests passing |
| v1.0 Specification lock | Target: Q3 2026 |
| Federation protocol (cross-registry discovery) | v1.1 |

---

## Community

**Discord:** [Join @agentralabs](https://discord.gg/agentralabs)
**X / Twitter:** [Follow @agentralab](https://x.com/agentralab)
**Email:** [hello@agentralabs.tech](mailto:hello@agentralabs.tech)

---

## Citation

```bibtex
@software{xap_protocol_2026,
  title  = {XAP: eXchange Agent Protocol},
  author = {Agentra Labs},
  year   = {2026},
  doi    = {10.5281/zenodo.18944370},
  url    = {https://github.com/agentralabs/xap-protocol}
}
```

---

## License

MIT. The protocol is free. Forever. The goal is adoption, not control.

---

*XAP is maintained by [Agentra Labs](https://www.agentralabs.tech). The protocol belongs to the community. The reference implementation is [Agentra Rail](https://www.agentralabs.tech).*

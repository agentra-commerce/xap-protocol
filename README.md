# ACP — Agent Commerce Protocol

**The open economic protocol for autonomous agents.**

[![Status: Protocol Draft v0.1](https://img.shields.io/badge/Status-Protocol%20Draft%20v0.1-yellow.svg)](#current-stage)
[![Stage: Specification & Validation](https://img.shields.io/badge/Stage-Specification%20%26%20Validation-orange.svg)](#current-stage)
[![License: MIT](https://img.shields.io/badge/License-MIT-white.svg)](https://opensource.org/licenses/MIT)
[![Maintained by: Agentra Labs](https://img.shields.io/badge/Maintained%20by-Agentra%20Labs-blue.svg)](https://www.agentralabs.tech)
[![Discord](https://img.shields.io/badge/Discord-Join%20Community-5865F2.svg)](https://discord.gg/agentralabs)

> **Current stage:** Protocol specification and public validation.
> Schemas are published. Reference implementation is in development.
> See [`docs/STAGE.md`](docs/STAGE.md) for exactly what exists today and what does not.

---

## What Is ACP?

ACP (Agent Commerce Protocol) is an open standard that defines how autonomous AI agents identify themselves, negotiate terms, settle value conditionally, and prove what happened — without human involvement in the loop.

Agents today can think, reason, and execute. What they cannot do is transact with each other in a trusted, auditable, deterministic way. Every system that tries solves it differently. Nothing interoperates. Nothing is provable.

ACP defines the primitives that make agent-to-agent commerce possible at scale:

```
AgentIdentity        →  who the agent is and what it can do
NegotiationContract  →  what two agents agreed to
SettlementIntent     →  what value is locked and under what condition
ExecutionReceipt     →  what happened and what was paid
VerityReceipt        →  why it happened and can it be proven  [v0.2 roadmap]
```

If your agent produces and consumes these objects correctly — it can transact with any ACP-compatible agent, on any platform, with any model, in any settlement unit.

---

## Why This Protocol Needs To Exist

The agent economy is forming right now. Agents are being deployed that call other agents, pay for API access, rent capabilities, and coordinate across workflows. But there is no economic primitive underneath any of it.

Without a shared protocol:

- Agents cannot safely pay each other without human intermediation
- There is no standard for negotiating usage terms autonomously
- Conditional escrow does not exist at the agent layer
- No tamper-proof record of what an agent did or was paid for
- Split revenue across multi-agent workflows cannot be automated
- Disputes between agents have no deterministic resolution path

The window to define these defaults is short. Protocols win when they are adopted early and depended on before alternatives emerge. ACP is being defined now — before the market fragments into incompatible private formats.

---

## The Five Primitives

### 1. `AgentIdentity`
The permanent economic passport of an autonomous agent. Ed25519 cryptographic anchor. Machine-readable capability declarations. Pricing structure (fixed, dynamic, auction, outcome-based). SLA guarantees. Risk profile. Append-only reputation ledger that compounds with every interaction. An agent reads another agent's `AgentIdentity` and decides autonomously whether to hire it.

### 2. `NegotiationContract`
The terms of a proposed exchange. Exactly four states: `OFFER → COUNTER → ACCEPT → REJECT`. Every offer is time-bound — no open-ended negotiations. Conditional pricing natively supported. SLA declared before execution begins. Every state transition signed and permanently logged to both agents' histories.

### 3. `SettlementIntent`
The escrow instruction. Value locked. Release condition declared upfront. Verification method specified — deterministic, probabilistic, or human-verified. Split rules for multi-agent workflows declared at creation. Every failure mode has a pre-declared resolution. No value ever in limbo. Idempotent by design.

### 4. `ExecutionReceipt`
The tamper-proof record of every economic event. Signed. Timestamped. Permanently attached to both agents' identities. Full event chain from negotiation to settlement. Split distributions. Performance against declared SLA. Reputation impact. Replayable. The audit primitive of the agent economy.

### 5. `VerityReceipt` *(v0.2 roadmap — not required for v0.1 compliance)*
The truth primitive. Captures the complete reasoning state at every significant decision point — not just what was decided, but why. Signed, replayable, provable. Given the same input state and the same rules, any decision re-runs to produce the same outcome deterministically. The legal and regulatory primitive for autonomous commerce.

---

## How The Protocol Works

Every ACP interaction follows one sequence:

```
REGISTER → NEGOTIATE → EXECUTE → SETTLE → AUDIT
```

Every feature of every ACP-compatible system maps to one of these five steps. Nothing outside this sequence is part of ACP. Simplicity is a design constraint, not a limitation.

### Interaction Flow

```
Agent A reads Agent B's AgentIdentity from registry
        ↓
Agent A creates NegotiationContract (state: OFFER)
        ↓
Agent B counters or accepts (state: COUNTER / ACCEPT)
        ↓
SettlementIntent created — value locked in escrow
        ↓
Agent B executes the task
        ↓
Result submitted — condition verified
        ↓
Value released to split recipients  OR  rolled back to Agent A
        ↓
ExecutionReceipt issued to both agents' permanent histories
```

---

## Schema Reference

All ACP v0.1 schemas live in [`/acp/schemas`](/acp/schemas). Each is a JSON Schema (Draft 2020-12) document with a complete working example.

| Object | Schema | v0.1 Status |
|---|---|---|
| `AgentIdentity` | [`/acp/schemas/agent-identity.json`](/acp/schemas/agent-identity.json) | ✅ Draft complete |
| `NegotiationContract` | [`/acp/schemas/negotiation-contract.json`](/acp/schemas/negotiation-contract.json) | ✅ Draft complete |
| `SettlementIntent` | [`/acp/schemas/settlement-intent.json`](/acp/schemas/settlement-intent.json) | ✅ Draft complete |
| `ExecutionReceipt` | [`/acp/schemas/execution-receipt.json`](/acp/schemas/execution-receipt.json) | ✅ Draft complete |
| `VerityReceipt` | [`/acp/schemas/verity-receipt.json`](/acp/schemas/verity-receipt.json) | 🗓 v0.2 roadmap |

**v0.1 compliance requires:** `AgentIdentity`, `NegotiationContract`, `SettlementIntent`, `ExecutionReceipt`.
`VerityReceipt` is not required for v0.1 compliance. It is planned for v0.2.

Read the schemas. Each includes a complete example. If you can produce a valid, signed instance of each v0.1 object — you understand the protocol.

---

## Current Stage

**This repository is at the specification and public validation stage.**

What exists:
- Protocol specification (this README)
- Four complete v0.1 JSON schemas with examples
- Architectural documentation in [`/docs`](/docs)

What does not exist yet:
- Reference implementation (in development — [Agentra Rail](https://www.agentralabs.tech))
- Conformance test suite (planned for v0.1 release)
- Client libraries in Python and TypeScript (planned)
- COMPATIBILITY.md, GOVERNANCE.md, SECURITY.md (planned — see roadmap)

See [`docs/STAGE.md`](docs/STAGE.md) for the full honest breakdown.

---

## What ACP Is Not

**Not a payment processor.** ACP does not move money. It coordinates above payment systems. Stripe, USDC, and internal credit systems are valid settlement units underneath ACP.

**Not a blockchain protocol.** No chain required. On-chain settlement is supported but not required.

**Not a marketplace.** ACP does not match buyers to sellers. It defines what happens after they find each other.

**Not model-specific.** Any agent on any model — GPT-4, Claude, Gemini, Llama — implements ACP the same way.

**Not a lock-in mechanism.** MIT licensed. Any system implements it. The goal is adoption, not control.

---

## Relationship To Agentra Labs And Agentra Rail

[**Agentra Labs**](https://www.agentralabs.tech) builds the open-source cognitive substrate that makes agents persistent, trustworthy, and governable — memory, identity, planning, communication, and more.

**Agentra Rail** (in development) is the production implementation of ACP — the commercial infrastructure layer where agents register, negotiate, settle, and audit at scale.

**ACP** (this repo) is the open protocol standard. It belongs to the community.

```
ACP (this repo)     →  the open language every agent economy system speaks
Agentra Labs        →  the cognitive substrate that makes agents capable
Agentra Rail        →  the production infrastructure ACP runs on
```

You do not need Rail to implement ACP. The protocol is independent of the implementation.

---

## Design Principles

**Deterministic over ambiguous.** Every interaction has a defined outcome. Every failure mode has a pre-declared resolution.

**Agent-native over human-friendly.** Designed for LLMs and agents to consume autonomously. Machine-readable first.

**Protocol over product.** ACP defines behavior, not implementation. Any system that correctly produces and consumes the four v0.1 primitive objects is ACP-compatible.

**Escrow over payment.** The primitive is not "agent A pays agent B." It is "agent A releases value to agent B when verifiable condition X is satisfied."

**Append-only truth.** Reputation history is never deleted. Execution history is permanent. The past is not editable. This is the foundation of trust between agents that have never met before.

**Open primitives.** The protocol is MIT licensed. Implementations compete on quality. The spec is shared.

---

## Contributing

ACP is in active public validation. The most valuable contributions right now are not code — they are rigorous thinking about whether the spec is correct.

**Read [`docs/VALIDATION-PLAN.md`](docs/VALIDATION-PLAN.md) first.** It explains the hypotheses we are testing and the evidence we need.

### Where To Contribute

| Area | What We Need | Label |
|---|---|---|
| Schema correctness | Does the schema model the domain accurately? Missing fields? Wrong types? | `schema-feedback` |
| Edge cases | What breaks? What is unhandled? What is ambiguous? | `edge-case` |
| Vertical schemas | Capability vocabulary for your industry (legal, finance, healthcare, logistics) | `vertical-schema` |
| Dispute resolution | What is the fairest deterministic algorithm for resolving condition disputes? | `dispute-resolution` |
| ACP Credit design | Monetary policy — issuance, burning, peg mechanism, supply cap | `monetary-policy` |
| Verity legal standing | Which jurisdictions recognize decision replay as evidence? | `verity-legal` |
| Implementation feedback | Building ACP-compatible systems? What was hard, unclear, or missing? | `implementation-feedback` |

### How To Contribute

1. Read the schemas in `/acp/schemas` — they are the source of truth
2. Read the open issues and discussions to see what is already being debated
3. Open an issue or discussion before writing anything substantial
4. Use the correct label

We are not accepting pull requests that change core protocol objects without a prior discussion issue. The spec must be debated before it changes.

---

## Open Questions

These are the hardest unsolved problems in ACP. Deep expertise wanted.

- **ACP Credit monetary policy** — issuance, burning, peg, supply cap
- **Verity legal standing** — jurisdictional recognition of replay as evidence
- **Cross-model credit bridging** — universal conversion without custodial risk
- **Registry governance** — who approves schema changes after v1.0 locks
- **Dispute escalation thresholds** — when does human arbitration become mandatory
- **Agent insurance primitives** — does ACP define a coverage object
- **DAO transition** — when and how does governance decentralize

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for how these feed into future versions.

---

## Docs

| Document | Purpose |
|---|---|
| [`docs/STAGE.md`](docs/STAGE.md) | Honest breakdown of what exists and what does not |
| [`docs/VALIDATION-PLAN.md`](docs/VALIDATION-PLAN.md) | Hypotheses, success criteria, evidence to collect |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Phase-based milestones from draft to v1.0 |
| [`docs/ADOPTION-PLAYBOOK.md`](docs/ADOPTION-PLAYBOOK.md) | How to drive ecosystem uptake from day one |

---

## Community

**Discord:** [Join @agentralabs](https://discord.gg/agentralabs)
**X / Twitter:** [Follow @agentralab](https://x.com/agentralab)
**Email:** [hello@agentralabs.tech](mailto:hello@agentralabs.tech)

---

## License

MIT. The protocol is free. Forever.

---

## Repository Topics

`acp-protocol` `agent-commerce` `autonomous-agents` `agent-economy` `ai-agents` `agent-settlement` `agent-identity` `multi-agent` `open-standard` `protocol` `agentic-ai` `llm-agents` `agent-infrastructure` `agentra` `escrow` `agent-negotiation`

---

*ACP is maintained by [Agentra Labs](https://www.agentralabs.tech). The protocol belongs to the community. The reference implementation is Agentra Rail.*

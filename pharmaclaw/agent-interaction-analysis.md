# PharmaClaw Agent Interaction Analysis
**Date:** 2026-03-04  
**Goal:** Assess current inter-agent communication and recommend improvements for maximum productivity.

---

## Current Architecture: What You Have

### Pattern: **Static Sequential Pipeline (with conditional branches)**

```
Chemistry → Pharmacology → Toxicology → [conditional] → Synthesis → Catalyst → Literature → IP → [Market] → Consensus
```

**How agents talk:** They don't, really. Each agent:
1. Runs a Python script via `subprocess`
2. Returns JSON to the LangGraph state dict
3. The next agent reads from the shared state

**Communication is one-directional and passive.** Agent B can read Agent A's output from the state, but:
- Agent A never sees Agent B's results
- Agents can't ask each other questions
- Agents can't request re-runs with different parameters
- No agent can say "wait, I need more info from Chemistry before I proceed"

### Strengths of Current Setup
- Simple, predictable, debuggable
- Fast (no LLM calls in the orchestrator itself — pure script execution)
- Cheap (zero token cost for orchestration logic)
- Works reliably for the "run everything and score" use case

### Weaknesses
1. **No feedback loops** — If Toxicology flags a problem, the only response is routing to Pharmacology. But Pharmacology can't ask Chemistry to generate an analog.
2. **No inter-agent dialogue** — Catalyst Design gets a hardcoded `["suzuki", "buchwald_hartwig"]` instead of actually reading the synthesis route and inferring reaction types.
3. **Agents are stateless scripts** — They don't know they're part of a pipeline. They just process input → output.
4. **Consensus is rule-based** — The scoring is a series of `if` statements, not a synthesized assessment of all data.
5. **No iteration** — The pipeline runs once, linearly. Real drug discovery is iterative — you'd go back and modify the scaffold based on tox results.
6. **Wasted context** — Literature search uses a generic query. It doesn't know what the other agents found (e.g., "search for papers about CYP3A4 inhibition of pyridopyrimidinone scaffolds").

---

## The 5 Multi-Agent Patterns (Industry Standard)

| Pattern | How It Works | Best For |
|---------|-------------|----------|
| **1. Sequential Chain** | A → B → C → D | Simple pipelines, your current setup |
| **2. Supervisor/Router** | Boss agent decides who runs next | Dynamic task routing |
| **3. Collaborative (Shared Scratchpad)** | All agents read/write to shared memory | Agents that need each other's context |
| **4. Hierarchical Teams** | Supervisor → Sub-teams → Agents | Complex multi-domain problems |
| **5. Debate/Critique** | Agent A proposes, Agent B critiques, iterate | Quality-critical decisions |

**Your current setup is Pattern 1 with a tiny bit of Pattern 2** (the conditional route after tox).

---

## Recommended Architecture: Hybrid Supervisor + Shared Memory + Critique

### The Core Change: Add an LLM-Powered Orchestrator

Instead of hardcoded graph edges, **Cheminem (the orchestrator) should be an LLM agent** that:
- Reads all agent outputs as they come in
- Decides what to run next based on actual results
- Can ask agents to re-run with different parameters
- Synthesizes the final consensus with real reasoning

```
                    ┌─────────────┐
                    │  Cheminem   │ ← LLM-powered supervisor
                    │ Orchestrator│
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
     ┌──────┴──────┐ ┌────┴────┐  ┌──────┴──────┐
     │ Tier 1:     │ │ Tier 2: │  │ Tier 3:     │
     │ Foundation  │ │ Safety  │  │ Intelligence│
     │             │ │         │  │             │
     │ • Chemistry │ │ • Pharm │  │ • Literature│
     │ • Chemin.   │ │ • Tox   │  │ • IP        │
     │ • Synthesis │ │         │  │ • Market    │
     │ • Catalyst  │ │         │  │             │
     └─────────────┘ └─────────┘  └─────────────┘
```

### Specific Improvements

#### 1. **Shared Memory / Blackboard** (Biggest Bang for Buck)
Instead of each agent only seeing its direct input, maintain a **shared context object** that accumulates findings:

```python
shared_context = {
    "molecule": {
        "smiles": "...",
        "name": "sotorasib",
        "mw": 560.6,
        "key_features": ["KRAS G12C covalent inhibitor", "acrylamide warhead"]
    },
    "findings": [
        {"agent": "chemistry", "finding": "pyridopyrimidinone core", "severity": "info"},
        {"agent": "tox", "finding": "CYP3A4 inhibition risk", "severity": "warning"},
        {"agent": "pharmacology", "finding": "low aqueous solubility", "severity": "warning"},
    ],
    "open_questions": [
        "Can we reduce CYP3A4 inhibition while maintaining KRAS binding?",
        "Are there salt forms that improve solubility?"
    ],
    "iterations": 0
}
```

Every agent reads AND writes to this context. This means:
- Literature agent searches for "CYP3A4 inhibition pyridopyrimidinone" (not just "novel drug candidate")
- IP agent knows the specific scaffold to check patents against
- Catalyst agent reads the actual retrosynthesis route to recommend appropriate catalysts

#### 2. **Feedback Loops / Iteration** (The Real Game-Changer)

```
Chemistry → Pharm → Tox ──[HIGH risk]──→ Chemistry (generate analog)
                         ──[LOW risk]───→ continue pipeline
```

When Tox flags a structural alert:
1. Supervisor asks Chemistry to generate 3-5 bioisosteric analogs
2. Quick-screen analogs through Pharm + Tox (just the critical checks)
3. Pick the best analog and continue the full pipeline with it

This turns a linear pipe into an **optimization loop**. This is how real med chem works — you don't just score a molecule, you iterate on it.

#### 3. **LLM-Powered Consensus** (Replace Rule-Based Scoring)

Current consensus:
```python
if mw > 500: score -= 1.0  # Arbitrary penalty
if logp > 5: score -= 1.0  # No context
```

Better consensus: Feed ALL agent results to an LLM and ask it to reason:
```python
consensus_prompt = f"""
You are a senior medicinal chemist reviewing a drug candidate.

Chemistry report: {json.dumps(chemistry_result)}
Pharmacology report: {json.dumps(pharm_result)}
Toxicology report: {json.dumps(tox_result)}
Synthesis report: {json.dumps(synth_result)}
Literature report: {json.dumps(lit_result)}
IP report: {json.dumps(ip_result)}
Market report: {json.dumps(market_result)}

Provide:
1. Overall score (0-10) with reasoning
2. Go/No-Go recommendation
3. Top 3 risks with mitigation strategies
4. Recommended next experiments
5. Comparison to similar approved drugs
"""
```

This gives you a nuanced, contextual assessment instead of `score -= 1.0`.

#### 4. **Agent-to-Agent Queries** (Smart Routing)

Let agents request information from each other:

```python
# Catalyst agent realizes it needs the specific bond disconnections
catalyst_request = {
    "to": "synthesis",
    "query": "What are the key bond disconnections in step 2?",
    "context": "Need to match catalyst to reaction type"
}

# Literature agent asks for specifics
lit_request = {
    "to": "tox",
    "query": "What specific structural alerts were flagged?",
    "context": "Searching for papers on mitigation strategies"
}
```

#### 5. **Parallel Execution Where Possible**

Current: Everything is serial (273s for full pipeline).

Better:
```
Phase 1 (parallel): Chemistry + Literature (independent)
Phase 2 (parallel): Pharmacology + Toxicology (both need Chemistry output)
Phase 3 (serial):   Synthesis (needs Pharm/Tox to know what to optimize)
Phase 4 (parallel): Catalyst + IP + Market (all need Synthesis)
Phase 5:            LLM Consensus (needs everything)
```

This could cut pipeline time by 40-50%.

---

## Framework Comparison for Implementation

| Framework | Pros | Cons | Fit for PharmaClaw |
|-----------|------|------|-------------------|
| **LangGraph (current)** | You already use it; typed state; conditional routing | No built-in agent dialogue; manual parallelism | Good base, needs extensions |
| **CrewAI** | Built-in delegation + question-asking; agent roles | Heavier LLM usage; less control over tool execution | Great for the dialogue features |
| **AutoGen** | Strong multi-turn conversations; nested agents | Complex setup; Microsoft ecosystem | Overkill for your use case |
| **Custom (OpenClaw subagents)** | Native to your platform; session-based communication | You'd build the orchestration yourself | Most flexible, most work |

### My Recommendation: **Extend LangGraph + Add LLM Consensus Layer**

Don't switch frameworks. Instead:
1. Add a **shared memory/blackboard** to PipelineState
2. Add **iteration support** (loop counter, analog generation on high-tox)
3. Replace rule-based consensus with **LLM-powered synthesis**
4. Add **parallel execution** for independent agents
5. Make **agent inputs context-aware** (pass relevant findings, not just SMILES)

---

## Priority Implementation Order

| Priority | Change | Effort | Impact |
|----------|--------|--------|--------|
| **P0** | Context-aware agent inputs (pass findings to each agent) | Low | High — immediately better results |
| **P1** | LLM-powered consensus replacing rule-based scoring | Medium | High — much more nuanced assessments |
| **P2** | Tox feedback loop (generate analogs on high risk) | Medium | Very High — turns analysis into optimization |
| **P3** | Parallel execution (Phase 1-4 model above) | Medium | Medium — faster, not smarter |
| **P4** | Agent-to-agent queries | High | Medium — nice for complex cases |
| **P5** | Full supervisor LLM routing | High | Medium — flexibility vs. predictability tradeoff |

---

## Token Cost Impact

| Change | Additional Cost Per Run |
|--------|----------------------|
| Context-aware inputs | $0 (just restructuring JSON) |
| LLM consensus | ~$0.01-0.03 (one LLM call with all results) |
| Tox feedback loop | ~$0.02-0.05 (3-5 extra Chemistry + quick Tox runs) |
| Parallel execution | $0 (same work, different scheduling) |
| Agent queries | ~$0.01-0.02 per query |
| Full supervisor routing | ~$0.03-0.10 per run (LLM decides each step) |

Even with ALL improvements, you're looking at **< $0.20 per full run**. That's still well under the $0.12/run overage pricing.

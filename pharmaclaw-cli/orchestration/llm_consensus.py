#!/usr/bin/env python3
"""
LLM-Powered Consensus — P1 upgrade for Cheminem Orchestrator.

Replaces rule-based if/else scoring with an LLM that reasons like a
senior medicinal chemist over ALL agent findings.

Supports any provider via litellm (Anthropic, OpenAI, Groq, Ollama, etc.).
Falls back to rule-based consensus if no LLM is configured or call fails.

Configuration (checked in order):
  1. PHARMACLAW_LLM_MODEL env var (e.g., "anthropic/claude-sonnet-4-20250514")
  2. PHARMACLAW_LLM_API_KEY env var
  3. ~/.pharmaclaw/config.json → {"llm_model": "...", "llm_api_key": "..."}
  4. Standard provider env vars (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)
"""

import json
import os
import sys
from datetime import datetime, timezone

# Default model — cheap and fast, good enough for structured reasoning
DEFAULT_MODEL = "anthropic/claude-sonnet-4-20250514"

CONSENSUS_SYSTEM_PROMPT = """You are a senior medicinal chemist reviewing a drug candidate.
You will receive structured data from multiple specialized AI agents that analyzed a molecule.
Your job is to synthesize ALL findings into a single expert assessment.

You MUST respond with ONLY valid JSON (no markdown, no commentary) in this exact schema:
{
  "score": <float 0-10>,
  "verdict": "<one-line assessment>",
  "go_no_go": "<GO|CONDITIONAL_GO|NO_GO>",
  "rationale": "<2-3 sentence reasoning connecting key findings>",
  "top_risks": [
    {"risk": "<description>", "severity": "critical|high|moderate|low", "mitigation": "<suggested action>"}
  ],
  "next_experiments": ["<recommended experiment 1>", "<recommended experiment 2>"],
  "comparison_note": "<how this compares to similar approved drugs, if data available>"
}

Scoring guide:
- 9-10: Exceptional candidate, minimal concerns
- 7-8: Strong candidate, manageable issues
- 5-6: Viable with significant modifications needed
- 3-4: Major concerns, likely needs scaffold redesign
- 0-2: Not viable, fundamental problems

Be specific. Reference actual data (MW values, LogP, specific alerts, Tanimoto scores).
Weigh IP risk heavily — a perfect molecule you can't patent is worthless.
PAINS alerts may be false positives for covalent inhibitors (michael acceptors) — note this if relevant."""


def _get_config() -> dict:
    """Load LLM configuration from env vars or config file."""
    config = {}

    # Check env vars first
    config["model"] = os.environ.get("PHARMACLAW_LLM_MODEL", "")
    config["api_key"] = os.environ.get("PHARMACLAW_LLM_API_KEY", "")

    # Fall back to config file
    if not config["model"]:
        config_path = os.path.expanduser("~/.pharmaclaw/config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    file_config = json.load(f)
                config["model"] = file_config.get("llm_model", "")
                config["api_key"] = config["api_key"] or file_config.get("llm_api_key", "")
            except Exception:
                pass

    # Default model if still empty
    if not config["model"]:
        config["model"] = DEFAULT_MODEL

    return config


def _build_prompt(state: dict) -> str:
    """Build the user prompt from pipeline state."""
    smiles = state.get("smiles", "unknown")
    drug_name = state.get("drug_name", "")
    profile = state.get("molecule_profile", {})
    findings = state.get("findings", [])
    open_questions = state.get("open_questions", [])

    sections = []

    # Header
    header = f"## Drug Candidate: {drug_name or smiles}"
    if drug_name:
        header += f"\nSMILES: {smiles}"
    sections.append(header)

    # Molecule profile
    if profile:
        sections.append(f"## Molecule Profile\n```json\n{json.dumps(profile, indent=2, default=str)}\n```")

    # All findings (the accumulated context from every agent)
    if findings:
        sections.append("## Agent Findings")
        for f in findings:
            sev_icon = {"critical": "🔴", "warning": "🟡", "info": "🟢"}.get(f.get("severity", "info"), "⚪")
            sections.append(f"- {sev_icon} **[{f.get('agent', '?')}]** ({f.get('type', '?')}): {f.get('detail', '?')}")

    # Key agent results (summarized)
    for agent_name in ["chemistry", "cheminformatics", "pharmacology", "toxicology",
                       "synthesis", "catalyst", "literature", "ip", "market"]:
        agent_data = state.get(agent_name, {})
        if agent_data and "error" not in str(agent_data.get("error", "")):
            # Truncate large results to save tokens
            summary = json.dumps(agent_data, default=str)
            if len(summary) > 1500:
                summary = summary[:1500] + "... [truncated]"
            sections.append(f"## {agent_name.title()} Agent Output\n```json\n{summary}\n```")

    # Open questions
    if open_questions:
        sections.append("## Open Questions from Agents")
        for q in open_questions:
            sections.append(f"- {q}")

    # Route history
    route = state.get("route_history", [])
    if route:
        sections.append(f"\n**Agents consulted:** {' → '.join(route)}")

    return "\n\n".join(sections)


def llm_consensus(state: dict, verbose: bool = False) -> dict:
    """
    Run LLM-powered consensus on the pipeline state.
    
    Returns a consensus dict compatible with the existing schema,
    enriched with LLM reasoning.
    
    Falls back to None if LLM call fails (caller should use rule-based).
    """
    config = _get_config()
    model = config["model"]
    api_key = config.get("api_key", "")

    # Build the prompt
    user_prompt = _build_prompt(state)

    if verbose:
        print(f"[LLM Consensus] Model: {model}", file=sys.stderr)
        print(f"[LLM Consensus] Prompt length: {len(user_prompt)} chars", file=sys.stderr)

    try:
        import litellm
        litellm.drop_params = True  # Ignore unsupported params gracefully

        # Set API key if provided
        if api_key:
            # litellm reads standard env vars, so set them
            if "anthropic" in model.lower():
                os.environ.setdefault("ANTHROPIC_API_KEY", api_key)
            elif "openai" in model.lower() or "gpt" in model.lower():
                os.environ.setdefault("OPENAI_API_KEY", api_key)
            else:
                os.environ.setdefault("OPENAI_API_KEY", api_key)

        # Build kwargs
        kwargs = dict(
            model=model,
            messages=[
                {"role": "system", "content": CONSENSUS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,  # Low temp for consistent scoring
            max_tokens=1000,
            timeout=120,  # Ollama needs time for first load
        )

        # Ollama needs api_base
        if model.startswith("ollama"):
            api_base = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            kwargs["api_base"] = api_base

        response = litellm.completion(**kwargs)

        content = response.choices[0].message.content.strip()

        # Parse JSON response
        # Handle potential markdown wrapping
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        llm_result = json.loads(content)

        # Build consensus dict from LLM response
        score = float(llm_result.get("score", 5.0))
        score = max(0, min(10, score))

        # Map go_no_go to verdict if verdict not provided
        verdict = llm_result.get("verdict", "")
        if not verdict:
            gng = llm_result.get("go_no_go", "CONDITIONAL_GO")
            if gng == "GO":
                verdict = "Strong candidate — proceed to next stage"
            elif gng == "NO_GO":
                verdict = "Not viable — fundamental issues identified"
            else:
                verdict = "Viable with modifications needed"

        # Build warnings from top_risks
        warnings = []
        for risk in llm_result.get("top_risks", []):
            warnings.append(f"[{risk.get('severity', '?').upper()}] {risk.get('risk', '?')}")

        # Build recommendations from top_risks mitigations + next_experiments
        recommendations = []
        for risk in llm_result.get("top_risks", []):
            if risk.get("mitigation"):
                recommendations.append(risk["mitigation"])
        for exp in llm_result.get("next_experiments", []):
            recommendations.append(f"Next experiment: {exp}")

        findings = state.get("findings", [])

        # Get token usage
        usage = {}
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        consensus = {
            "score": round(score, 1),
            "verdict": verdict,
            "go_no_go": llm_result.get("go_no_go", "CONDITIONAL_GO"),
            "rationale": llm_result.get("rationale", ""),
            "warnings": warnings,
            "recommendations": recommendations,
            "top_risks": llm_result.get("top_risks", []),
            "next_experiments": llm_result.get("next_experiments", []),
            "comparison_note": llm_result.get("comparison_note", ""),
            "agents_consulted": state.get("route_history", []),
            "total_findings": len(findings),
            "critical_count": sum(1 for f in findings if f.get("severity") == "critical"),
            "warning_count": sum(1 for f in findings if f.get("severity") == "warning"),
            "consensus_method": "llm",
            "llm_model": model,
            "llm_usage": usage,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if verbose:
            print(f"[LLM Consensus] Score: {score}/10 — {verdict}", file=sys.stderr)
            if usage:
                print(f"[LLM Consensus] Tokens: {usage.get('total_tokens', '?')}", file=sys.stderr)

        return consensus

    except ImportError:
        if verbose:
            print("[LLM Consensus] litellm not installed — falling back to rule-based", file=sys.stderr)
        return None
    except Exception as e:
        if verbose:
            print(f"[LLM Consensus] Failed: {e} — falling back to rule-based", file=sys.stderr)
        return None

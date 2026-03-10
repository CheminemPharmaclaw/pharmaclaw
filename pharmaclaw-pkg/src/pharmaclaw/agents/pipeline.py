"""
Pipeline — Multi-agent orchestration for end-to-end drug discovery.

Chains all 9 PharmaClaw agents with an AI orchestrator that decides what to run,
interprets results, and produces a unified report.

Usage:
    >>> from pharmaclaw.agents import Pipeline
    >>> pipe = Pipeline(api_key="sk-...")
    >>> report = pipe.run("Analyze sotorasib as a KRAS G12C inhibitor")
    >>> print(report["answer"])
"""

import json
from pharmaclaw.agents.base import BaseAgent, _check_litellm
from pharmaclaw.core import chemistry as chem
from pharmaclaw.core import pharmacology as pharm
from pharmaclaw.core import toxicology as tox
from pharmaclaw.core import synthesis as synth
from pharmaclaw.core import catalyst as cat
from pharmaclaw.core import literature as lit
from pharmaclaw.core import ip_check as ip
from pharmaclaw.core import market as mkt
from pharmaclaw.core import cheminformatics as ci


class Pipeline(BaseAgent):
    """Multi-agent pipeline — chains all 9 PharmaClaw agents with AI orchestration.

    The orchestrator LLM decides which agents to invoke based on your question,
    interprets results across agents, and produces a unified analysis.

    Args:
        api_key: LLM provider API key.
        model: Model name (default 'gpt-4o-mini'). Use 'gpt-4o' or 'claude-sonnet-4-20250514' for best results.
        verbose: Print each tool call to stderr as it runs.

    Example:
        >>> pipe = Pipeline(api_key="sk-...", model="gpt-4o", verbose=True)
        >>> report = pipe.run("Full analysis of CC(=O)Oc1ccccc1C(=O)O")
        >>> print(report["answer"])
    """

    AGENT_NAME = "pipeline"

    SYSTEM_PROMPT = """You are PharmaClaw's Pipeline Orchestrator 🎯 — the lead of a 9-agent drug discovery team.

You have access to ALL PharmaClaw agents as tools. For a comprehensive analysis, use them strategically:

1. **Chemistry** (get_props, get_retro, get_plan, get_similarity, standardize, scaffold_analysis) — Start here. Get molecular properties and structure info.
2. **Pharmacology** (pharmacology_profile) — ADME/PK profiling, drug-likeness rules, risk assessment.
3. **Toxicology** (toxicology_analyze) — Safety screening, PAINS alerts, structural concerns.
4. **Synthesis** (synthesis_plan) — Retrosynthetic route planning with feasibility scoring.
5. **Catalyst** (catalyst_recommend, catalyst_design_ligand) — Catalyst selection for key reactions in the synthesis.
6. **Literature** (literature_search) — Find relevant papers, clinical data, prior art.
7. **IP Check** (ip_fto, ip_bioisosteres) — Freedom-to-Operate analysis, patent risk, novel derivative suggestions.
8. **Market Intel** (market_faers) — FDA adverse event data, safety signal monitoring.
9. **Cheminformatics** (conformers, recap_fragment, stereoisomers, convert_format) — 3D structures, fragments, format conversion.

**Strategy:**
- For a full analysis, run Chemistry → Pharmacology → Toxicology → Synthesis → IP in that order.
- Add Literature and Market Intel when the user asks about a known drug.
- Use Catalyst when synthesis planning reveals key coupling reactions.
- Use Cheminformatics when 3D structure or fragment analysis is needed.
- Interpret results ACROSS agents: e.g., if tox flags high risk but pharmacology looks good, explain the tradeoff.

**Output:** Provide a clear, structured report with:
- Key findings from each agent
- Overall assessment (promising / needs modification / not viable)
- Specific recommendations for next steps
- Any red flags or concerns

Be thorough but concise. Scientists value precision over verbosity.
"""

    TOOLS = [
        # Chemistry tools
        {"type": "function", "function": {
            "name": "get_props", "description": "Compute molecular properties (MW, LogP, TPSA, HBD, HBA, rotatable bonds).",
            "parameters": {"type": "object", "properties": {"smiles": {"type": "string"}}, "required": ["smiles"]}
        }},
        {"type": "function", "function": {
            "name": "get_retro", "description": "BRICS retrosynthesis — find precursor fragments.",
            "parameters": {"type": "object", "properties": {"smiles": {"type": "string"}, "depth": {"type": "integer", "default": 1}}, "required": ["smiles"]}
        }},
        {"type": "function", "function": {
            "name": "get_similarity", "description": "Tanimoto similarity between query and target molecules.",
            "parameters": {"type": "object", "properties": {"query_smiles": {"type": "string"}, "target_smiles": {"type": "string"}}, "required": ["query_smiles", "target_smiles"]}
        }},
        {"type": "function", "function": {
            "name": "standardize", "description": "Standardize molecule and enumerate tautomers.",
            "parameters": {"type": "object", "properties": {"smiles": {"type": "string"}}, "required": ["smiles"]}
        }},
        {"type": "function", "function": {
            "name": "scaffold_analysis", "description": "Compute Murcko scaffolds.",
            "parameters": {"type": "object", "properties": {"smiles": {"type": "string"}}, "required": ["smiles"]}
        }},
        # Pharmacology
        {"type": "function", "function": {
            "name": "pharmacology_profile", "description": "Full ADME/PK profile: Lipinski, Veber, QED, BBB, solubility, CYP3A4, PAINS, risk assessment.",
            "parameters": {"type": "object", "properties": {"smiles": {"type": "string"}}, "required": ["smiles"]}
        }},
        # Toxicology
        {"type": "function", "function": {
            "name": "toxicology_analyze", "description": "Safety profiling: Lipinski/Veber violations, QED, PAINS, risk level.",
            "parameters": {"type": "object", "properties": {"smiles": {"type": "string"}}, "required": ["smiles"]}
        }},
        # Synthesis
        {"type": "function", "function": {
            "name": "synthesis_plan", "description": "Multi-step synthesis route with feasibility scoring.",
            "parameters": {"type": "object", "properties": {"smiles": {"type": "string"}, "steps": {"type": "integer", "default": 3}}, "required": ["smiles"]}
        }},
        # Catalyst
        {"type": "function", "function": {
            "name": "catalyst_recommend", "description": "Recommend catalysts for a reaction type.",
            "parameters": {"type": "object", "properties": {"reaction": {"type": "string"}, "enantioselective": {"type": "boolean", "default": False}}, "required": ["reaction"]}
        }},
        {"type": "function", "function": {
            "name": "catalyst_design_ligand", "description": "Design novel ligand variants.",
            "parameters": {"type": "object", "properties": {"scaffold": {"type": "string"}, "strategy": {"type": "string", "default": "all"}}, "required": ["scaffold"]}
        }},
        # Literature
        {"type": "function", "function": {
            "name": "literature_search", "description": "Search PubMed and Semantic Scholar.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "source": {"type": "string", "default": "both"}, "max_results": {"type": "integer", "default": 5}}, "required": ["query"]}
        }},
        # IP
        {"type": "function", "function": {
            "name": "ip_fto", "description": "Freedom-to-Operate: Tanimoto similarity vs known drugs.",
            "parameters": {"type": "object", "properties": {"smiles": {"type": "string"}, "threshold": {"type": "number", "default": 0.85}}, "required": ["smiles"]}
        }},
        {"type": "function", "function": {
            "name": "ip_bioisosteres", "description": "Suggest bioisosteric replacements for IP differentiation.",
            "parameters": {"type": "object", "properties": {"smiles": {"type": "string"}}, "required": ["smiles"]}
        }},
        # Market
        {"type": "function", "function": {
            "name": "market_faers", "description": "Query FDA FAERS adverse events for a drug.",
            "parameters": {"type": "object", "properties": {"drug": {"type": "string"}, "limit": {"type": "integer", "default": 20}}, "required": ["drug"]}
        }},
        # Cheminformatics
        {"type": "function", "function": {
            "name": "conformers", "description": "Generate 3D conformer ensemble.",
            "parameters": {"type": "object", "properties": {"smiles": {"type": "string"}, "num_confs": {"type": "integer", "default": 5}}, "required": ["smiles"]}
        }},
        {"type": "function", "function": {
            "name": "recap_fragment", "description": "RECAP/BRICS fragmentation for library design.",
            "parameters": {"type": "object", "properties": {"smiles": {"type": "string"}}, "required": ["smiles"]}
        }},
        {"type": "function", "function": {
            "name": "stereoisomers", "description": "Enumerate stereoisomers (R/S, E/Z).",
            "parameters": {"type": "object", "properties": {"smiles": {"type": "string"}}, "required": ["smiles"]}
        }},
    ]

    TOOL_FUNCTIONS = {
        # Chemistry
        "get_props": chem.get_props,
        "get_retro": chem.get_retro,
        "get_similarity": chem.get_similarity,
        "standardize": chem.standardize,
        "scaffold_analysis": chem.scaffold_analysis,
        # Pharmacology
        "pharmacology_profile": pharm.profile,
        # Toxicology
        "toxicology_analyze": tox.analyze,
        # Synthesis
        "synthesis_plan": synth.plan_synthesis,
        # Catalyst
        "catalyst_recommend": cat.recommend,
        "catalyst_design_ligand": cat.design_ligand,
        # Literature
        "literature_search": lit.search,
        # IP
        "ip_fto": ip.fto_analysis,
        "ip_bioisosteres": ip.bioisostere_suggestions,
        # Market
        "market_faers": mkt.query_faers,
        # Cheminformatics
        "conformers": ci.generate_conformers,
        "recap_fragment": ci.recap_fragment,
        "stereoisomers": ci.enumerate_stereoisomers,
    }

    def run(self, query: str) -> dict:
        """Run the full pipeline on a query. Alias for ask().

        Args:
            query: Natural language description of what you want analyzed.
                   Include SMILES, drug names, or specific questions.

        Returns:
            dict with 'answer' (natural language report), 'tool_calls' (what ran),
            and 'data' (raw results from each agent).
        """
        return self.ask(query, reset=True)

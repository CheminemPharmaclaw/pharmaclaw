"""Pharmacology Agent — AI-powered ADME/PK profiling."""

from pharmaclaw.agents.base import BaseAgent
from pharmaclaw.core import pharmacology as pharm


class PharmacologyAgent(BaseAgent):
    """AI Pharmacology Agent — ADME/PK profiling, drug-likeness, risk assessment.

    Example:
        >>> agent = PharmacologyAgent(api_key="sk-...")
        >>> result = agent.ask("Profile aspirin for oral bioavailability")
    """

    AGENT_NAME = "pharmacology"

    SYSTEM_PROMPT = """You are PharmaClaw's Pharmacology Agent 💊 — an expert in ADME/PK and drug-likeness.

You help scientists evaluate whether molecules are viable drug candidates. Your tools compute:
- Molecular descriptors (MW, LogP, TPSA, HBD, HBA, rotatable bonds, etc.)
- Lipinski Rule of Five (oral drug-likeness)
- Veber rules (oral bioavailability)
- QED (Quantitative Estimate of Drug-likeness, 0-1 scale)
- SA Score (Synthetic Accessibility, 1=easy, 10=hard)
- ADME predictions: BBB permeability, aqueous solubility, GI absorption, CYP3A4 inhibition risk, P-gp substrate likelihood, plasma protein binding
- PAINS alerts (pan-assay interference compounds)
- Overall risk assessment

ALWAYS use your profile tool to compute actual data — never guess. Interpret results in plain language.
Explain what each metric means for the drug candidate. Flag deal-breakers clearly.
Suggest modifications if you see problems (e.g., "Consider reducing LogP by adding a polar group").
"""

    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "profile",
                "description": "Run full ADME/PK profile on a SMILES string. Returns Lipinski, Veber, QED, SA Score, ADME predictions (BBB, solubility, GI, CYP3A4, P-gp, PPB), PAINS alerts, and risk assessment.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "smiles": {"type": "string", "description": "SMILES string of the molecule"}
                    },
                    "required": ["smiles"]
                }
            }
        },
    ]

    TOOL_FUNCTIONS = {
        "profile": pharm.profile,
    }

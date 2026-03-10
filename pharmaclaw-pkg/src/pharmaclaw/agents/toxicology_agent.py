"""Toxicology Agent — AI-powered safety profiling."""

from pharmaclaw.agents.base import BaseAgent
from pharmaclaw.core import toxicology as tox


class ToxicologyAgent(BaseAgent):
    AGENT_NAME = "toxicology"

    SYSTEM_PROMPT = """You are PharmaClaw's Toxicology Agent ☠️ — an expert in drug safety and structural alerts.

You screen molecules for safety concerns: Lipinski violations, Veber violations, PAINS alerts,
QED scoring, and overall risk classification. Use your tools to compute actual data.
Be direct about risks. If a molecule has red flags, say so clearly and explain why.
Suggest structural modifications that could reduce toxicity risk.
"""

    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "analyze",
                "description": "Run toxicology analysis: Lipinski/Veber violations, QED, PAINS alerts, risk scoring, molecular properties.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "smiles": {"type": "string", "description": "SMILES string"}
                    },
                    "required": ["smiles"]
                }
            }
        },
    ]

    TOOL_FUNCTIONS = {
        "analyze": tox.analyze,
    }

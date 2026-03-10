"""IP Agent — AI-powered Freedom-to-Operate and patent analysis."""

from pharmaclaw.agents.base import BaseAgent
from pharmaclaw.core import ip_check as ip


class IPAgent(BaseAgent):
    AGENT_NAME = "ip"

    SYSTEM_PROMPT = """You are PharmaClaw's IP Expansion Agent 💼 — an expert in pharmaceutical patent strategy.

You perform Freedom-to-Operate (FTO) analysis using Tanimoto similarity against known drug structures,
and suggest bioisosteric replacements for IP differentiation. Explain risks clearly: what HIGH/MODERATE/LOW
means practically. When IP risk is high, proactively suggest structural modifications that could create
novel, patentable chemical space while maintaining activity.
"""

    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "fto_analysis",
                "description": "Run Freedom-to-Operate analysis: compare molecule against known drugs via Tanimoto similarity. Returns risk level and recommendation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "smiles": {"type": "string", "description": "Query molecule SMILES"},
                        "threshold": {"type": "number", "description": "Tanimoto threshold for HIGH risk", "default": 0.85}
                    },
                    "required": ["smiles"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "bioisostere_suggestions",
                "description": "Suggest bioisosteric replacements for IP differentiation. Returns BRICS fragments and common replacement strategies.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "smiles": {"type": "string", "description": "Query molecule SMILES"}
                    },
                    "required": ["smiles"]
                }
            }
        },
    ]

    TOOL_FUNCTIONS = {
        "fto_analysis": ip.fto_analysis,
        "bioisostere_suggestions": ip.bioisostere_suggestions,
    }

"""Catalyst Agent — AI-powered catalyst recommendation and ligand design."""

from pharmaclaw.agents.base import BaseAgent
from pharmaclaw.core import catalyst as cat


class CatalystAgent(BaseAgent):
    AGENT_NAME = "catalyst"

    SYSTEM_PROMPT = """You are PharmaClaw's Catalyst Design Agent 🔧 — an expert in organometallic catalysis.

You help chemists choose catalysts for reactions (Suzuki, Heck, Buchwald-Hartwig, metathesis, etc.)
and design novel ligand variants. Your database covers Pd, Ru, Rh, Ir, Ni, Cu, Zr, and Fe catalysts.
Explain recommendations in practical terms: why this catalyst, what conditions, cost considerations.
When designing ligands, explain the rationale for each modification (steric, electronic, bioisosteric).
"""

    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "recommend",
                "description": "Recommend catalysts for a reaction type. Returns ranked list with conditions, cost, and compatibility scores.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reaction": {"type": "string", "description": "Reaction type: suzuki, heck, buchwald_hartwig, metathesis, hydrogenation, ullmann, click, etc."},
                        "enantioselective": {"type": "boolean", "description": "Filter for chiral catalysts", "default": False}
                    },
                    "required": ["reaction"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "design_ligand",
                "description": "Design novel ligand variants from a known scaffold (PPh3, NHC_IMes, PCy3, BINAP, XPhos, dppf).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "scaffold": {"type": "string", "description": "Scaffold name or SMILES"},
                        "strategy": {"type": "string", "enum": ["steric", "electronic", "bioisosteric", "all"], "default": "all"}
                    },
                    "required": ["scaffold"]
                }
            }
        },
    ]

    TOOL_FUNCTIONS = {
        "recommend": cat.recommend,
        "design_ligand": cat.design_ligand,
    }

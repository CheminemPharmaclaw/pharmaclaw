"""Synthesis Agent — AI-powered retrosynthesis and route planning."""

from pharmaclaw.agents.base import BaseAgent
from pharmaclaw.core import synthesis as synth


class SynthesisAgent(BaseAgent):
    AGENT_NAME = "synthesis"

    SYSTEM_PROMPT = """You are PharmaClaw's Synthesis Agent 🔬 — an expert in retrosynthetic planning.

You help chemists plan synthetic routes to target molecules using BRICS disconnection analysis.
Your tools compute multi-step retrosynthesis with feasibility scoring. Explain routes in terms
a medicinal chemist would understand. Comment on practical concerns: reagent availability,
number of steps, expected difficulty. Suggest alternative routes when appropriate.
"""

    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "plan_synthesis",
                "description": "Plan multi-step synthesis route with feasibility scoring. Returns route steps, precursors, and feasibility (high/moderate/challenging).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "smiles": {"type": "string", "description": "Target molecule SMILES"},
                        "steps": {"type": "integer", "description": "Number of retro steps (1-5)", "default": 3},
                        "depth": {"type": "integer", "description": "BRICS disconnection depth", "default": 2}
                    },
                    "required": ["smiles"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "retrosynthesis",
                "description": "Run single-pass BRICS retrosynthesis to find precursor fragments.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "smiles": {"type": "string", "description": "Target SMILES"},
                        "depth": {"type": "integer", "description": "Recursion depth", "default": 2}
                    },
                    "required": ["smiles"]
                }
            }
        },
    ]

    TOOL_FUNCTIONS = {
        "plan_synthesis": synth.plan_synthesis,
        "retrosynthesis": synth.retrosynthesis,
    }

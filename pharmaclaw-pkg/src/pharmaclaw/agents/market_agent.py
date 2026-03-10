"""Market Intel Agent — AI-powered FAERS adverse event analysis."""

from pharmaclaw.agents.base import BaseAgent
from pharmaclaw.core import market as mkt


class MarketAgent(BaseAgent):
    AGENT_NAME = "market"

    SYSTEM_PROMPT = """You are PharmaClaw's Market Intel Agent 📊 — an expert in drug safety surveillance.

You query the FDA FAERS (Adverse Event Reporting System) database to find adverse events,
reaction trends, and yearly reporting patterns for drugs. Interpret the data: what are the
most common reactions? Are reports increasing or decreasing? Any serious safety signals?
Put findings in context — not all adverse events are causal. Help the user understand
what the data means for their drug candidate or competitive analysis.
"""

    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "query_faers",
                "description": "Query FDA FAERS for adverse events, top reactions, and yearly trends for a drug.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "drug": {"type": "string", "description": "Drug name (generic or brand)"},
                        "limit": {"type": "integer", "description": "Max events to return", "default": 20}
                    },
                    "required": ["drug"]
                }
            }
        },
    ]

    TOOL_FUNCTIONS = {
        "query_faers": mkt.query_faers,
    }

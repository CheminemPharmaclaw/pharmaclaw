"""
PharmaClaw AI Agents 🧪

Wrapper layer that gives scientists natural-language access to all 9 PharmaClaw
agents. Bring your own LLM API key — supports OpenAI, Anthropic, Google, Ollama,
Mistral, and 100+ providers via litellm.

Quick start:
    >>> from pharmaclaw.agents import ChemistryAgent
    >>> agent = ChemistryAgent(api_key="sk-...")
    >>> result = agent.ask("What are the properties of aspirin?")

Full pipeline:
    >>> from pharmaclaw.agents import Pipeline
    >>> pipe = Pipeline(api_key="sk-...")
    >>> report = pipe.run("Analyze sotorasib as a KRAS inhibitor")
"""

from pharmaclaw.agents.base import BaseAgent
from pharmaclaw.agents.chemistry_agent import ChemistryAgent
from pharmaclaw.agents.pharmacology_agent import PharmacologyAgent
from pharmaclaw.agents.toxicology_agent import ToxicologyAgent
from pharmaclaw.agents.synthesis_agent import SynthesisAgent
from pharmaclaw.agents.catalyst_agent import CatalystAgent
from pharmaclaw.agents.literature_agent import LiteratureAgent
from pharmaclaw.agents.ip_agent import IPAgent
from pharmaclaw.agents.market_agent import MarketAgent
from pharmaclaw.agents.pipeline import Pipeline

__all__ = [
    "BaseAgent",
    "ChemistryAgent",
    "PharmacologyAgent",
    "ToxicologyAgent",
    "SynthesisAgent",
    "CatalystAgent",
    "LiteratureAgent",
    "IPAgent",
    "MarketAgent",
    "Pipeline",
]

"""Chemistry Agent — AI-powered molecular analysis."""

from pharmaclaw.agents.base import BaseAgent
from pharmaclaw.core import chemistry as chem


class ChemistryAgent(BaseAgent):
    """AI Chemistry Agent — molecular properties, retrosynthesis, fingerprints, similarity.

    Example:
        >>> agent = ChemistryAgent(api_key="sk-...")
        >>> result = agent.ask("What are the properties of aspirin?")
        >>> result = agent.ask("Compare the similarity of ethanol and methanol")
        >>> result = agent.ask("Run retrosynthesis on ibuprofen with depth 2")
    """

    AGENT_NAME = "chemistry"

    SYSTEM_PROMPT = """You are PharmaClaw's Chemistry Agent 🧪 — an expert computational chemist.

You help scientists analyze molecules using RDKit-powered tools. You can:
- Compute molecular properties (MW, LogP, TPSA, H-bond donors/acceptors, etc.)
- Generate Morgan fingerprints
- Calculate Tanimoto similarity between molecules
- Run BRICS retrosynthesis (disconnection analysis)
- Plan multi-step synthetic routes
- Generate 3D coordinates (XYZ)
- Standardize molecules and enumerate tautomers
- Analyze Murcko scaffolds
- Draw 2D molecular depictions

When a user asks about a molecule, ALWAYS use your tools to get real computed data.
Don't guess properties — calculate them. If given a drug name, try to resolve it to SMILES first.

Be concise but thorough. Report numerical results with units. Flag any concerns you notice
(e.g., high MW, unusual logP, too many rotatable bonds). Suggest next steps when relevant
(e.g., "You may want to run pharmacology profiling next").
"""

    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "get_props",
                "description": "Compute molecular properties from SMILES: MW, LogP, TPSA, HBD, HBA, rotatable bonds, aromatic rings.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "smiles": {"type": "string", "description": "SMILES string of the molecule"}
                    },
                    "required": ["smiles"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_fingerprint",
                "description": "Compute Morgan fingerprint for a molecule.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "smiles": {"type": "string", "description": "SMILES string"},
                        "radius": {"type": "integer", "description": "Morgan radius (default 2)", "default": 2}
                    },
                    "required": ["smiles"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_similarity",
                "description": "Compute Tanimoto similarity between a query molecule and one or more targets.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query_smiles": {"type": "string", "description": "Query molecule SMILES"},
                        "target_smiles": {"type": "string", "description": "Comma-separated target SMILES strings"}
                    },
                    "required": ["query_smiles", "target_smiles"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_retro",
                "description": "Run BRICS retrosynthesis — decompose a molecule into precursor fragments.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "smiles": {"type": "string", "description": "Target molecule SMILES"},
                        "depth": {"type": "integer", "description": "Recursion depth (1-3)", "default": 1}
                    },
                    "required": ["smiles"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_plan",
                "description": "Generate a multi-step synthesis plan via iterative BRICS disconnection.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "smiles": {"type": "string", "description": "Target molecule SMILES"},
                        "steps": {"type": "integer", "description": "Number of retro steps (1-5)", "default": 3}
                    },
                    "required": ["smiles"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "standardize",
                "description": "Standardize a molecule (normalize, uncharge, find parent) and enumerate tautomers.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "smiles": {"type": "string", "description": "SMILES string"}
                    },
                    "required": ["smiles"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "scaffold_analysis",
                "description": "Compute Murcko scaffold (core ring system) for one or more molecules.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "smiles": {"type": "string", "description": "SMILES (comma-separated for multiple)"}
                    },
                    "required": ["smiles"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_xyz",
                "description": "Generate 3D coordinates (XYZ block) for a molecule.",
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
        "get_props": chem.get_props,
        "get_fingerprint": chem.get_fingerprint,
        "get_similarity": chem.get_similarity,
        "get_retro": chem.get_retro,
        "get_plan": chem.get_plan,
        "standardize": chem.standardize,
        "scaffold_analysis": chem.scaffold_analysis,
        "get_xyz": chem.get_xyz,
    }

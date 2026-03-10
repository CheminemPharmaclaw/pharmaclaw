"""
PharmaClaw 🧪 — AI-powered drug discovery pipeline.

9 chained agents: Chemistry, Cheminformatics, Pharmacology, Toxicology,
Synthesis, Catalyst Design, Literature, IP Check, Market Intel.

Quick start:
    >>> from pharmaclaw import chemistry, pharmacology, toxicology
    >>> props = chemistry.get_props("CC(=O)Oc1ccccc1C(=O)O")  # aspirin
    >>> profile = pharmacology.profile("CC(=O)Oc1ccccc1C(=O)O")
    >>> tox = toxicology.analyze("CC(=O)Oc1ccccc1C(=O)O")
"""

__version__ = "1.0.0"
__all__ = [
    "chemistry",
    "pharmacology",
    "toxicology",
    "synthesis",
    "catalyst",
    "literature",
    "ip_check",
    "market",
    "cheminformatics",
]

# Lazy imports — only load agents when accessed
def __getattr__(name):
    if name in __all__:
        import importlib
        module = importlib.import_module(f".core.{name}", __name__)
        globals()[name] = module
        return module
    raise AttributeError(f"module 'pharmaclaw' has no attribute {name!r}")

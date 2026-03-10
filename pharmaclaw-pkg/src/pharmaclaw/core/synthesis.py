"""
Synthesis Agent — Multi-step retrosynthesis route planning with feasibility scoring.

Usage:
    >>> from pharmaclaw.core.synthesis import plan_synthesis
    >>> result = plan_synthesis("CC(=O)Oc1ccccc1C(=O)O")
    >>> result["feasibility"]["score"]
    'high'
"""

from pharmaclaw.core.chemistry import _validate_smiles, _resolve_target, _brics_retro


def _score_feasibility(route: list) -> dict:
    """Score synthesis feasibility based on route complexity."""
    num_steps = len(route)
    total_precursors = sum(len(s.get("precursors", [])) for s in route)

    if num_steps <= 3 and total_precursors <= 10:
        score, confidence = "high", 0.75
    elif num_steps <= 5:
        score, confidence = "moderate", 0.55
    else:
        score, confidence = "challenging", 0.35

    return {
        "score": score,
        "confidence": confidence,
        "steps": num_steps,
        "total_precursors": total_precursors,
        "note": "BRICS-based disconnection; real yields require experimental validation",
    }


def plan_synthesis(smiles: str, target: str = None, depth: int = 2, steps: int = 3) -> dict:
    """Plan multi-step synthesis route for a molecule.

    Args:
        smiles: Target SMILES or compound name.
        target: Optional explicit target (overrides smiles for resolution).
        depth: BRICS disconnection depth per step.
        steps: Number of retrosynthetic steps.

    Returns dict with route, feasibility score, and precursors.
    """
    target_smiles = _resolve_target(target or smiles)
    mol = _validate_smiles(target_smiles)

    current_products = [target_smiles]
    route = []
    for step_num in range(1, steps + 1):
        precursors_step = []
        for prod_smi in current_products:
            prod_mol = _validate_smiles(prod_smi)
            step_precs = _brics_retro(prod_mol, 1)
            precursors_step.extend(step_precs)
        precursors_step = list(set(precursors_step))
        route.append({
            "step": step_num,
            "precursors": precursors_step[:10],
            "condition": "BRICS template (ester/amide/etc disconnects)",
            "yield_estimate": "N/A (BRICS)",
            "product": current_products[0],
        })
        current_products = precursors_step[:5]

    return {
        "agent": "synthesis",
        "smiles": target_smiles,
        "steps": steps,
        "templates_used": "BRICS",
        "route": route,
        "feasibility": _score_feasibility(route),
    }


def retrosynthesis(smiles: str, depth: int = 2) -> dict:
    """Run single-pass BRICS retrosynthesis."""
    from pharmaclaw.core.chemistry import get_retro
    result = get_retro(smiles, depth)
    result["agent"] = "synthesis"
    return result

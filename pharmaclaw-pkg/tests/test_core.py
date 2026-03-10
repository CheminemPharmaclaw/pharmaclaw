"""Tests for PharmaClaw core agents."""

import pytest


# ── Chemistry ──────────────────────────────────────────────

class TestChemistry:
    def test_get_props_ethanol(self):
        from pharmaclaw.core.chemistry import get_props
        result = get_props("CCO")
        assert result["agent"] == "chemistry"
        assert result["mw"] > 40  # ethanol ~46
        assert result["mw"] < 50
        assert "logp" in result
        assert "tpsa" in result

    def test_get_props_aspirin(self):
        from pharmaclaw.core.chemistry import get_props
        result = get_props("CC(=O)Oc1ccccc1C(=O)O")
        assert result["mw"] > 170  # aspirin ~180
        assert result["arom_rings"] == 1

    def test_invalid_smiles(self):
        from pharmaclaw.core.chemistry import get_props
        with pytest.raises(ValueError, match="Invalid SMILES"):
            get_props("INVALID_NOT_A_SMILES")

    def test_fingerprint(self):
        from pharmaclaw.core.chemistry import get_fingerprint
        result = get_fingerprint("CCO")
        assert result["num_bits"] == 2048
        assert len(result["bits_set"]) > 0

    def test_similarity(self):
        from pharmaclaw.core.chemistry import get_similarity
        result = get_similarity("CCO", "CCCO,c1ccccc1")
        assert len(result["results"]) == 2
        assert 0 <= result["max_similarity"] <= 1

    def test_retro(self):
        from pharmaclaw.core.chemistry import get_retro
        result = get_retro("CC(=O)Oc1ccccc1C(=O)O", depth=1)
        assert result["num_precursors"] > 0
        assert result["agent"] == "chemistry"

    def test_plan(self):
        from pharmaclaw.core.chemistry import get_plan
        result = get_plan("CCO", steps=2)
        assert len(result["route"]) == 2
        assert result["templates_used"] == "BRICS"

    def test_standardize(self):
        from pharmaclaw.core.chemistry import standardize
        result = standardize("CCO")
        assert result["standardized"] == "CCO"
        assert result["num_tautomers"] >= 1

    def test_scaffold(self):
        from pharmaclaw.core.chemistry import scaffold_analysis
        result = scaffold_analysis("c1ccc(cc1)CC(=O)O")
        assert len(result["results"]) == 1
        assert "murcko_scaffold" in result["results"][0]

    def test_mcs(self):
        from pharmaclaw.core.chemistry import mcs, _HAS_FMCS
        if not _HAS_FMCS:
            pytest.skip("rdFMCS not available (pip rdkit)")
        result = mcs(["c1ccccc1", "c1ccc(cc1)O"])
        assert result["num_atoms"] > 0

    def test_xyz(self):
        from pharmaclaw.core.chemistry import get_xyz
        result = get_xyz("CCO")
        assert "xyz" in result
        assert result["num_atoms"] > 0


# ── Pharmacology ───────────────────────────────────────────

class TestPharmacology:
    def test_profile_aspirin(self):
        from pharmaclaw.core.pharmacology import profile
        result = profile("CC(=O)Oc1ccccc1C(=O)O")
        assert result["status"] == "success"
        assert result["report"]["lipinski"]["pass"] is True
        assert result["report"]["qed"] is not None
        assert result["report"]["qed"] > 0

    def test_profile_invalid(self):
        from pharmaclaw.core.pharmacology import profile
        with pytest.raises(ValueError):
            profile("NOT_SMILES")

    def test_adme_predictions(self):
        from pharmaclaw.core.pharmacology import profile
        result = profile("CCO")
        adme = result["report"]["adme"]
        assert "bbb" in adme
        assert "solubility" in adme
        assert "gi_absorption" in adme
        assert "cyp3a4_inhibition" in adme


# ── Toxicology ─────────────────────────────────────────────

class TestToxicology:
    def test_analyze_ethanol(self):
        from pharmaclaw.core.toxicology import analyze
        result = analyze("CCO")
        assert result["agent"] == "toxicology"
        assert result["risk"] in ("Low", "Medium", "High")
        assert result["lipinski_violations"] == 0

    def test_analyze_invalid(self):
        from pharmaclaw.core.toxicology import analyze
        with pytest.raises(ValueError):
            analyze("INVALID")


# ── IP Check ──────────────────────────────────────────────

class TestIPCheck:
    def test_fto_ethanol(self):
        from pharmaclaw.core.ip_check import fto_analysis
        result = fto_analysis("CCO")
        assert result["overall_risk"] in ("LOW", "MODERATE", "HIGH")
        assert len(result["comparisons"]) > 0

    def test_bioisosteres(self):
        from pharmaclaw.core.ip_check import bioisostere_suggestions
        result = bioisostere_suggestions("CC(=O)Oc1ccccc1C(=O)O")
        assert len(result["suggested_replacements"]) > 0
        assert len(result["fragments"]) > 0


# ── Synthesis ─────────────────────────────────────────────

class TestSynthesis:
    def test_plan(self):
        from pharmaclaw.core.synthesis import plan_synthesis
        result = plan_synthesis("CC(=O)Oc1ccccc1C(=O)O")
        assert result["agent"] == "synthesis"
        assert result["feasibility"]["score"] in ("high", "moderate", "challenging")


# ── Catalyst ──────────────────────────────────────────────

class TestCatalyst:
    def test_recommend_suzuki(self):
        from pharmaclaw.core.catalyst import recommend
        result = recommend("suzuki")
        assert result["num_matches"] > 0
        assert result["recommendations"][0]["name"]

    def test_design_ligand(self):
        from pharmaclaw.core.catalyst import design_ligand
        result = design_ligand("PPh3", strategy="all")
        assert result["num_variants"] > 0


# ── Cheminformatics ───────────────────────────────────────

class TestCheminformatics:
    def test_conformers(self):
        from pharmaclaw.core.cheminformatics import generate_conformers
        result = generate_conformers("CCO", num_confs=3)
        assert result["num_generated"] > 0
        assert "xyz" in result["conformers"][0]

    def test_recap(self):
        from pharmaclaw.core.cheminformatics import recap_fragment
        result = recap_fragment("CC(=O)Oc1ccccc1C(=O)O")
        assert result["num_fragments"] > 0

    def test_stereoisomers(self):
        from pharmaclaw.core.cheminformatics import enumerate_stereoisomers
        # Alanine has a chiral center
        result = enumerate_stereoisomers("N[C@@H](C)C(=O)O")
        assert result["num_isomers"] >= 1

    def test_convert_inchi(self):
        from pharmaclaw.core.cheminformatics import convert_format
        result = convert_format("CCO", "inchi")
        assert result["inchi"].startswith("InChI=")


# ── Version ───────────────────────────────────────────────

class TestPackage:
    def test_version(self):
        import pharmaclaw
        assert pharmaclaw.__version__ == "1.0.0"

    def test_lazy_import(self):
        import pharmaclaw
        # Lazy import should work
        mod = pharmaclaw.chemistry
        assert hasattr(mod, "get_props")

"""Tests for BPX GitHub example files and Chen 2020 round-trip conversion.

This module tests:
1. Conversion of the BPX GitHub example files (NMC pouch cell and LFP 18650)
   to all supported output formats (battmo.m, battmo.jl, jsonld).
2. Round-trip consistency between the NMC BPX file and its BattMo counterpart,
   which represent the same cell parameterisation (the About:Energy NMC111|graphite
   dataset, also known as the "Chen 2020" example used in BPX and BattMo).
"""

import json
import os

import pytest

import BatteryModelMapper as bmm

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
ONTOLOGY_PATH = os.path.join(ASSETS_DIR, "battery-model-lithium-ion.ttl")
BPX_TEMPLATE = os.path.join(ASSETS_DIR, "bpx_template.json")
BATTMO_TEMPLATE = os.path.join(ASSETS_DIR, "battmo_template.json")

# BPX GitHub example files
NMC_BPX = os.path.join(ASSETS_DIR, "nmc_pouch_cell_BPX.json")
LFP_BPX = os.path.join(ASSETS_DIR, "lfp_18650_cell_BPX.json")

# Existing sample files that represent the same NMC dataset in BattMo format
SAMPLE_BATTMO = os.path.join(ASSETS_DIR, "sample_battmo_input.json")


@pytest.fixture(scope="module")
def ontology():
    return bmm.OntologyParser(ONTOLOGY_PATH)


def _convert(ontology, input_data, input_type, output_type, input_file):
    """Run a conversion and return the output dict."""
    mappings = ontology.get_mappings(input_type, output_type)
    if output_type in ("battmo.m", "battmo.jl"):
        template = bmm.JSONLoader.load(BATTMO_TEMPLATE)
    else:
        template = bmm.JSONLoader.load(BPX_TEMPLATE)
    template.pop("Validation", None)
    mapper = bmm.ParameterMapper(
        mappings, template, input_file, output_type, input_type
    )
    return mapper.map_parameters(input_data)


# ---------------------------------------------------------------------------
# NMC pouch cell BPX file (from BPX GitHub)
# ---------------------------------------------------------------------------
class TestNMCBPXToBattMo:
    """Convert the NMC pouch cell BPX file to BattMo format."""

    @pytest.fixture(autouse=True)
    def _setup(self, ontology):
        data = bmm.JSONLoader.load(NMC_BPX)
        data = bmm.PreprocessInput("bpx", data).process()
        self.result = _convert(ontology, data, "bpx", "battmo.m", NMC_BPX)

    def test_has_negative_electrode(self):
        assert "NegativeElectrode" in self.result

    def test_has_positive_electrode(self):
        assert "PositiveElectrode" in self.result

    def test_has_separator(self):
        assert "Separator" in self.result

    def test_has_electrolyte(self):
        assert "Electrolyte" in self.result

    def test_negative_thickness(self):
        val = self.result["NegativeElectrode"]["Coating"]["thickness"]
        assert val == pytest.approx(5.62e-05)

    def test_positive_thickness(self):
        val = self.result["PositiveElectrode"]["Coating"]["thickness"]
        assert val == pytest.approx(5.23e-05)

    def test_separator_thickness(self):
        assert self.result["Separator"]["thickness"] == pytest.approx(2e-05)

    def test_negative_particle_radius(self):
        val = self.result["NegativeElectrode"]["Coating"]["ActiveMaterial"][
            "SolidDiffusion"
        ]["particleRadius"]
        assert val == pytest.approx(4.12e-06)

    def test_positive_particle_radius(self):
        val = self.result["PositiveElectrode"]["Coating"]["ActiveMaterial"][
            "SolidDiffusion"
        ]["particleRadius"]
        assert val == pytest.approx(4.6e-06)

    def test_lower_cutoff_voltage(self):
        assert self.result["Control"]["lowerCutoffVoltage"] == pytest.approx(2.7)

    def test_upper_cutoff_voltage(self):
        assert self.result["Control"]["upperCutoffVoltage"] == pytest.approx(4.2)


class TestNMCBPXToBattMoJl:
    """battmo.m and battmo.jl produce identical output for the NMC file."""

    @pytest.fixture(autouse=True)
    def _setup(self, ontology):
        data = bmm.JSONLoader.load(NMC_BPX)
        data = bmm.PreprocessInput("bpx", data).process()
        self.result_m = _convert(ontology, data, "bpx", "battmo.m", NMC_BPX)
        self.result_jl = _convert(ontology, data, "bpx", "battmo.jl", NMC_BPX)

    def test_same_output(self):
        assert json.dumps(self.result_m, sort_keys=True) == json.dumps(
            self.result_jl, sort_keys=True
        )


class TestNMCBPXToJSONLD:
    """Convert the NMC pouch cell BPX file to JSON-LD."""

    @pytest.fixture(autouse=True)
    def _setup(self, ontology, tmp_path):
        data = bmm.JSONLoader.load(NMC_BPX)
        data = bmm.PreprocessInput("bpx", data).process()
        outpath = str(tmp_path / "nmc_bpx.jsonld")
        bmm.export_jsonld(
            ontology, "bpx", data, outpath,
            cell_id="NMCCell", cell_type="PouchCell",
        )
        with open(outpath) as f:
            self.result = json.load(f)

    def test_has_context(self):
        assert "@context" in self.result

    def test_has_graph(self):
        assert "@graph" in self.result

    def test_has_properties(self):
        assert len(self.result["@graph"]["hasProperty"]) > 0


# ---------------------------------------------------------------------------
# LFP 18650 BPX file (from BPX GitHub)
# ---------------------------------------------------------------------------
class TestLFPBPXToBattMo:
    """Convert the LFP 18650 BPX file to BattMo format."""

    @pytest.fixture(autouse=True)
    def _setup(self, ontology):
        data = bmm.JSONLoader.load(LFP_BPX)
        data = bmm.PreprocessInput("bpx", data).process()
        self.result = _convert(ontology, data, "bpx", "battmo.m", LFP_BPX)

    def test_has_negative_electrode(self):
        assert "NegativeElectrode" in self.result

    def test_has_positive_electrode(self):
        assert "PositiveElectrode" in self.result

    def test_has_separator(self):
        assert "Separator" in self.result

    def test_has_electrolyte(self):
        assert "Electrolyte" in self.result

    def test_negative_thickness(self):
        val = self.result["NegativeElectrode"]["Coating"]["thickness"]
        assert val == pytest.approx(4.44e-05)

    def test_positive_thickness(self):
        val = self.result["PositiveElectrode"]["Coating"]["thickness"]
        assert val == pytest.approx(6.43e-05)

    def test_separator_thickness(self):
        assert self.result["Separator"]["thickness"] == pytest.approx(2e-05)

    def test_negative_particle_radius(self):
        val = self.result["NegativeElectrode"]["Coating"]["ActiveMaterial"][
            "SolidDiffusion"
        ]["particleRadius"]
        assert val == pytest.approx(4.8e-06)

    def test_positive_particle_radius(self):
        val = self.result["PositiveElectrode"]["Coating"]["ActiveMaterial"][
            "SolidDiffusion"
        ]["particleRadius"]
        assert val == pytest.approx(5e-07)

    def test_lower_cutoff_voltage(self):
        assert self.result["Control"]["lowerCutoffVoltage"] == pytest.approx(2.0)

    def test_upper_cutoff_voltage(self):
        assert self.result["Control"]["upperCutoffVoltage"] == pytest.approx(3.65)


class TestLFPBPXToBattMoJl:
    """battmo.m and battmo.jl produce identical output for the LFP file."""

    @pytest.fixture(autouse=True)
    def _setup(self, ontology):
        data = bmm.JSONLoader.load(LFP_BPX)
        data = bmm.PreprocessInput("bpx", data).process()
        self.result_m = _convert(ontology, data, "bpx", "battmo.m", LFP_BPX)
        self.result_jl = _convert(ontology, data, "bpx", "battmo.jl", LFP_BPX)

    def test_same_output(self):
        assert json.dumps(self.result_m, sort_keys=True) == json.dumps(
            self.result_jl, sort_keys=True
        )


class TestLFPBPXToJSONLD:
    """Convert the LFP 18650 BPX file to JSON-LD."""

    @pytest.fixture(autouse=True)
    def _setup(self, ontology, tmp_path):
        data = bmm.JSONLoader.load(LFP_BPX)
        data = bmm.PreprocessInput("bpx", data).process()
        outpath = str(tmp_path / "lfp_bpx.jsonld")
        bmm.export_jsonld(
            ontology, "bpx", data, outpath,
            cell_id="LFPCell", cell_type="CylindricalCell",
        )
        with open(outpath) as f:
            self.result = json.load(f)

    def test_has_context(self):
        assert "@context" in self.result

    def test_has_graph(self):
        assert "@graph" in self.result

    def test_has_properties(self):
        assert len(self.result["@graph"]["hasProperty"]) > 0


# ---------------------------------------------------------------------------
# Chen 2020 round-trip: NMC BPX ↔ BattMo
#
# The nmc_pouch_cell_BPX.json (BPX GitHub) and sample_battmo_input.json
# represent the same NMC111|graphite parameterisation in two formats.
# These tests verify that converting between them yields consistent values.
# ---------------------------------------------------------------------------
class TestChen2020BPXToBattMo:
    """NMC BPX → BattMo conversion matches the reference BattMo sample."""

    @pytest.fixture(autouse=True)
    def _setup(self, ontology):
        data = bmm.JSONLoader.load(NMC_BPX)
        data = bmm.PreprocessInput("bpx", data).process()
        self.converted = _convert(ontology, data, "bpx", "battmo.m", NMC_BPX)
        self.reference = bmm.JSONLoader.load(SAMPLE_BATTMO)

    def test_negative_thickness_matches(self):
        assert self.converted["NegativeElectrode"]["Coating"][
            "thickness"
        ] == pytest.approx(
            self.reference["NegativeElectrode"]["Coating"]["thickness"]
        )

    def test_positive_thickness_matches(self):
        assert self.converted["PositiveElectrode"]["Coating"][
            "thickness"
        ] == pytest.approx(
            self.reference["PositiveElectrode"]["Coating"]["thickness"]
        )

    def test_separator_thickness_matches(self):
        assert self.converted["Separator"]["thickness"] == pytest.approx(
            self.reference["Separator"]["thickness"]
        )

    def test_negative_particle_radius_matches(self):
        converted_val = self.converted["NegativeElectrode"]["Coating"]["ActiveMaterial"][
            "SolidDiffusion"
        ]["particleRadius"]
        ref_val = self.reference["NegativeElectrode"]["Coating"]["ActiveMaterial"][
            "SolidDiffusion"
        ]["particleRadius"]
        assert converted_val == pytest.approx(ref_val)

    def test_positive_particle_radius_matches(self):
        converted_val = self.converted["PositiveElectrode"]["Coating"]["ActiveMaterial"][
            "SolidDiffusion"
        ]["particleRadius"]
        ref_val = self.reference["PositiveElectrode"]["Coating"]["ActiveMaterial"][
            "SolidDiffusion"
        ]["particleRadius"]
        assert converted_val == pytest.approx(ref_val)

    def test_negative_porosity_matches(self):
        assert self.converted["NegativeElectrode"]["Coating"][
            "porosity"
        ] == pytest.approx(
            self.reference["NegativeElectrode"]["Coating"]["porosity"]
        )

    def test_positive_porosity_matches(self):
        assert self.converted["PositiveElectrode"]["Coating"][
            "porosity"
        ] == pytest.approx(
            self.reference["PositiveElectrode"]["Coating"]["porosity"]
        )

    def test_electrolyte_transference_matches(self):
        assert self.converted["Electrolyte"]["species"][
            "transferenceNumber"
        ] == pytest.approx(
            self.reference["Electrolyte"]["species"]["transferenceNumber"]
        )


class TestChen2020BattMoToBPX:
    """BattMo sample → BPX conversion matches the reference NMC BPX file."""

    @pytest.fixture(autouse=True)
    def _setup(self, ontology):
        data = bmm.JSONLoader.load(SAMPLE_BATTMO)
        data = bmm.PreprocessInput("battmo.m", data).process()
        self.converted = _convert(ontology, data, "battmo.m", "bpx", SAMPLE_BATTMO)
        self.reference = bmm.JSONLoader.load(NMC_BPX)

    def test_negative_thickness_matches(self):
        assert self.converted["Parameterisation"]["Negative electrode"][
            "Thickness [m]"
        ] == pytest.approx(
            self.reference["Parameterisation"]["Negative electrode"]["Thickness [m]"]
        )

    def test_positive_thickness_matches(self):
        assert self.converted["Parameterisation"]["Positive electrode"][
            "Thickness [m]"
        ] == pytest.approx(
            self.reference["Parameterisation"]["Positive electrode"]["Thickness [m]"]
        )

    def test_separator_thickness_matches(self):
        assert self.converted["Parameterisation"]["Separator"][
            "Thickness [m]"
        ] == pytest.approx(
            self.reference["Parameterisation"]["Separator"]["Thickness [m]"]
        )

    def test_negative_particle_radius_matches(self):
        assert self.converted["Parameterisation"]["Negative electrode"][
            "Particle radius [m]"
        ] == pytest.approx(
            self.reference["Parameterisation"]["Negative electrode"][
                "Particle radius [m]"
            ]
        )

    def test_electrolyte_transference_matches(self):
        assert self.converted["Parameterisation"]["Electrolyte"][
            "Cation transference number"
        ] == pytest.approx(
            self.reference["Parameterisation"]["Electrolyte"][
                "Cation transference number"
            ]
        )

"""Tests for porosity ↔ volume fraction handling."""

import copy
import json
import os

import pytest

import BatteryModelMapper as bmm

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
ONTOLOGY_PATH = os.path.join(ASSETS_DIR, "battery-model-lithium-ion.ttl")
BPX_TEMPLATE = os.path.join(ASSETS_DIR, "bpx_template.json")
BATTMO_TEMPLATE = os.path.join(ASSETS_DIR, "battmo_template.json")
SAMPLE_BPX = os.path.join(ASSETS_DIR, "sample_bpx_input.json")
SAMPLE_BATTMO = os.path.join(ASSETS_DIR, "sample_battmo_input.json")


@pytest.fixture(scope="module")
def ontology():
    return bmm.OntologyParser(ONTOLOGY_PATH)


def _convert(ontology, input_data, input_type, output_type, input_file):
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


class TestVolumeFractionToPorosity:
    """When BattMo input has volumeFraction, preprocessor computes porosity."""

    def test_preprocessor_converts_volume_fraction_to_porosity(self):
        battmo_data = {
            "NegativeElectrode": {
                "Coating": {
                    "volumeFraction": 0.75,
                    "thickness": 5.62e-05,
                }
            },
            "PositiveElectrode": {
                "Coating": {
                    "volumeFraction": 0.70,
                    "thickness": 5.23e-05,
                }
            },
        }
        preprocessor = bmm.PreprocessInput("battmo.m", battmo_data)
        result = preprocessor.process()

        assert result["NegativeElectrode"]["Coating"]["porosity"] == pytest.approx(0.25)
        assert result["PositiveElectrode"]["Coating"]["porosity"] == pytest.approx(0.30)

    def test_preprocessor_preserves_existing_porosity_when_no_volume_fraction(self):
        battmo_data = {
            "NegativeElectrode": {
                "Coating": {
                    "porosity": 0.253991,
                    "thickness": 5.62e-05,
                }
            },
            "PositiveElectrode": {
                "Coating": {
                    "porosity": 0.277493,
                    "thickness": 5.23e-05,
                }
            },
        }
        preprocessor = bmm.PreprocessInput("battmo.m", battmo_data)
        result = preprocessor.process()

        assert result["NegativeElectrode"]["Coating"]["porosity"] == pytest.approx(
            0.253991
        )
        assert result["PositiveElectrode"]["Coating"]["porosity"] == pytest.approx(
            0.277493
        )

    def test_bpx_preprocessor_is_identity(self):
        bpx_data = bmm.JSONLoader.load(SAMPLE_BPX)
        original = copy.deepcopy(bpx_data)
        preprocessor = bmm.PreprocessInput("bpx", bpx_data)
        result = preprocessor.process()
        assert json.dumps(result, sort_keys=True) == json.dumps(
            original, sort_keys=True
        )


class TestBPXPorosityToBattMo:
    """BPX Porosity maps correctly to BattMo's porosity field."""

    def test_negative_porosity_maps(self, ontology):
        bpx_data = bmm.JSONLoader.load(SAMPLE_BPX)
        bpx_data = bmm.PreprocessInput("bpx", bpx_data).process()
        result = _convert(ontology, bpx_data, "bpx", "battmo.m", SAMPLE_BPX)

        assert result["NegativeElectrode"]["Coating"]["porosity"] == pytest.approx(
            0.253991
        )

    def test_positive_porosity_maps(self, ontology):
        bpx_data = bmm.JSONLoader.load(SAMPLE_BPX)
        bpx_data = bmm.PreprocessInput("bpx", bpx_data).process()
        result = _convert(ontology, bpx_data, "bpx", "battmo.m", SAMPLE_BPX)

        assert result["PositiveElectrode"]["Coating"]["porosity"] == pytest.approx(
            0.277493
        )

    def test_separator_porosity_maps(self, ontology):
        bpx_data = bmm.JSONLoader.load(SAMPLE_BPX)
        bpx_data = bmm.PreprocessInput("bpx", bpx_data).process()
        result = _convert(ontology, bpx_data, "bpx", "battmo.m", SAMPLE_BPX)

        assert result["Separator"]["porosity"] == pytest.approx(0.47)


class TestPorosityRoundTrip:
    """BPX → BattMo → BPX preserves porosity values."""

    def test_negative_porosity_round_trip(self, ontology):
        bpx_data = bmm.JSONLoader.load(SAMPLE_BPX)
        bpx_data = bmm.PreprocessInput("bpx", bpx_data).process()
        original_neg = bpx_data["Parameterisation"]["Negative electrode"]["Porosity"]

        battmo = _convert(ontology, bpx_data, "bpx", "battmo.m", SAMPLE_BPX)
        battmo = bmm.PreprocessInput("battmo.m", battmo).process()
        bpx_back = _convert(ontology, battmo, "battmo.m", "bpx", SAMPLE_BATTMO)

        restored_neg = bpx_back["Parameterisation"]["Negative electrode"]["Porosity"]
        assert restored_neg == pytest.approx(original_neg)

    def test_positive_porosity_round_trip(self, ontology):
        bpx_data = bmm.JSONLoader.load(SAMPLE_BPX)
        bpx_data = bmm.PreprocessInput("bpx", bpx_data).process()
        original_pos = bpx_data["Parameterisation"]["Positive electrode"]["Porosity"]

        battmo = _convert(ontology, bpx_data, "bpx", "battmo.m", SAMPLE_BPX)
        battmo = bmm.PreprocessInput("battmo.m", battmo).process()
        bpx_back = _convert(ontology, battmo, "battmo.m", "bpx", SAMPLE_BATTMO)

        restored_pos = bpx_back["Parameterisation"]["Positive electrode"]["Porosity"]
        assert restored_pos == pytest.approx(original_pos)

    def test_separator_porosity_round_trip(self, ontology):
        bpx_data = bmm.JSONLoader.load(SAMPLE_BPX)
        bpx_data = bmm.PreprocessInput("bpx", bpx_data).process()
        original_sep = bpx_data["Parameterisation"]["Separator"]["Porosity"]

        battmo = _convert(ontology, bpx_data, "bpx", "battmo.m", SAMPLE_BPX)
        battmo = bmm.PreprocessInput("battmo.m", battmo).process()
        bpx_back = _convert(ontology, battmo, "battmo.m", "bpx", SAMPLE_BATTMO)

        restored_sep = bpx_back["Parameterisation"]["Separator"]["Porosity"]
        assert restored_sep == pytest.approx(original_sep)

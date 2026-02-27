"""Test that BPX output is structurally valid."""

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


@pytest.fixture(scope="module")
def bpx_from_battmo(ontology):
    """Convert BattMo sample to BPX."""
    data = bmm.JSONLoader.load(SAMPLE_BATTMO)
    data = bmm.PreprocessInput("battmo.m", data).process()
    mappings = ontology.get_mappings("battmo.m", "bpx")
    template = bmm.JSONLoader.load(BPX_TEMPLATE)
    template.pop("Validation", None)
    mapper = bmm.ParameterMapper(
        mappings, template, SAMPLE_BATTMO, "bpx", "battmo.m"
    )
    return mapper.map_parameters(data)


@pytest.fixture(scope="module")
def bpx_original():
    """Load the original BPX sample file."""
    return bmm.JSONLoader.load(SAMPLE_BPX)


class TestBPXStructureFromConversion:
    """Verify BPX output from BattMo→BPX conversion has required structure."""

    def test_has_header(self, bpx_from_battmo):
        assert "Header" in bpx_from_battmo

    def test_header_has_bpx_version(self, bpx_from_battmo):
        assert "BPX" in bpx_from_battmo["Header"]

    def test_header_has_title(self, bpx_from_battmo):
        assert "Title" in bpx_from_battmo["Header"]

    def test_header_has_model(self, bpx_from_battmo):
        assert "Model" in bpx_from_battmo["Header"]

    def test_has_parameterisation(self, bpx_from_battmo):
        assert "Parameterisation" in bpx_from_battmo

    def test_has_cell_section(self, bpx_from_battmo):
        assert "Cell" in bpx_from_battmo["Parameterisation"]

    def test_has_electrolyte_section(self, bpx_from_battmo):
        assert "Electrolyte" in bpx_from_battmo["Parameterisation"]

    def test_has_negative_electrode_section(self, bpx_from_battmo):
        assert "Negative electrode" in bpx_from_battmo["Parameterisation"]

    def test_has_positive_electrode_section(self, bpx_from_battmo):
        assert "Positive electrode" in bpx_from_battmo["Parameterisation"]

    def test_has_separator_section(self, bpx_from_battmo):
        assert "Separator" in bpx_from_battmo["Parameterisation"]


class TestBPXNegativeElectrodeFields:
    """Verify all expected negative electrode fields are present."""

    EXPECTED_FIELDS = [
        "Particle radius [m]",
        "Thickness [m]",
        "Diffusivity [m2.s-1]",
        "OCP [V]",
        "Conductivity [S.m-1]",
        "Surface area per unit volume [m-1]",
        "Porosity",
        "Reaction rate constant [mol.m-2.s-1]",
        "Minimum stoichiometry",
        "Maximum stoichiometry",
        "Maximum concentration [mol.m-3]",
    ]

    @pytest.mark.parametrize("field", EXPECTED_FIELDS)
    def test_field_present(self, bpx_from_battmo, field):
        neg = bpx_from_battmo["Parameterisation"]["Negative electrode"]
        assert field in neg, f"Missing field: {field}"


class TestBPXPositiveElectrodeFields:
    """Verify all expected positive electrode fields are present."""

    EXPECTED_FIELDS = [
        "Particle radius [m]",
        "Thickness [m]",
        "Diffusivity [m2.s-1]",
        "OCP [V]",
        "Conductivity [S.m-1]",
        "Surface area per unit volume [m-1]",
        "Porosity",
        "Reaction rate constant [mol.m-2.s-1]",
        "Minimum stoichiometry",
        "Maximum stoichiometry",
        "Maximum concentration [mol.m-3]",
    ]

    @pytest.mark.parametrize("field", EXPECTED_FIELDS)
    def test_field_present(self, bpx_from_battmo, field):
        pos = bpx_from_battmo["Parameterisation"]["Positive electrode"]
        assert field in pos, f"Missing field: {field}"


class TestBPXElectrolyteFields:
    """Verify all expected electrolyte fields are present."""

    EXPECTED_FIELDS = [
        "Initial concentration [mol.m-3]",
        "Cation transference number",
        "Conductivity [S.m-1]",
        "Diffusivity [m2.s-1]",
    ]

    @pytest.mark.parametrize("field", EXPECTED_FIELDS)
    def test_field_present(self, bpx_from_battmo, field):
        elyte = bpx_from_battmo["Parameterisation"]["Electrolyte"]
        assert field in elyte, f"Missing field: {field}"


class TestBPXSeparatorFields:
    """Verify all expected separator fields are present."""

    EXPECTED_FIELDS = [
        "Thickness [m]",
        "Porosity",
        "Transport efficiency",
    ]

    @pytest.mark.parametrize("field", EXPECTED_FIELDS)
    def test_field_present(self, bpx_from_battmo, field):
        sep = bpx_from_battmo["Parameterisation"]["Separator"]
        assert field in sep, f"Missing field: {field}"


class TestBPXOriginalInput:
    """Verify the original BPX sample file is structurally valid."""

    def test_has_header(self, bpx_original):
        assert "Header" in bpx_original

    def test_has_bpx_version(self, bpx_original):
        assert "BPX" in bpx_original["Header"]

    def test_has_parameterisation(self, bpx_original):
        assert "Parameterisation" in bpx_original

    def test_all_sections_present(self, bpx_original):
        sections = bpx_original["Parameterisation"]
        for expected in [
            "Cell",
            "Electrolyte",
            "Negative electrode",
            "Positive electrode",
            "Separator",
        ]:
            assert expected in sections


class TestBPXLibraryValidation:
    """Try to validate BPX output with the bpx library if installed."""

    @pytest.fixture(autouse=True)
    def _check_bpx_library(self):
        pytest.importorskip("bpx")

    def test_validate_original_bpx(self):
        import bpx

        with open(SAMPLE_BPX) as f:
            data = json.load(f)
        bpx.parse_bpx_str(json.dumps(data))

    def test_validate_converted_bpx(self, bpx_from_battmo):
        import bpx

        bpx.parse_bpx_str(json.dumps(bpx_from_battmo))


class TestBPXOutputSerializable:
    """Verify BPX output can be serialized to JSON."""

    def test_serializable(self, bpx_from_battmo, tmp_path):
        outpath = str(tmp_path / "test_bpx_output.json")
        bmm.JSONWriter.write(bpx_from_battmo, outpath)

        with open(outpath) as f:
            reloaded = json.load(f)

        assert "Header" in reloaded
        assert "Parameterisation" in reloaded

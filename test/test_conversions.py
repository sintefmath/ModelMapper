"""Unit tests for parameter mapping across all conversion paths."""

import json
import os
import tempfile

import pytest

import BatteryModelMapper as bmm

# Resolve paths relative to this test file
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
def bpx_input():
    data = bmm.JSONLoader.load(SAMPLE_BPX)
    return bmm.PreprocessInput("bpx", data).process()


@pytest.fixture(scope="module")
def battmo_input():
    data = bmm.JSONLoader.load(SAMPLE_BATTMO)
    return bmm.PreprocessInput("battmo.m", data).process()


def _convert(ontology, input_data, input_type, output_type, input_file):
    """Helper to run a full conversion."""
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
# BPX → BattMo
# ---------------------------------------------------------------------------
class TestBPXToBattMo:
    """Test conversion from BPX format to BattMo format."""

    @pytest.fixture(autouse=True)
    def _setup(self, ontology, bpx_input):
        self.result = _convert(
            ontology, bpx_input, "bpx", "battmo.m", SAMPLE_BPX
        )

    def test_negative_electrode_thickness(self):
        val = self.result["NegativeElectrode"]["Coating"]["thickness"]
        assert val == pytest.approx(5.62e-05)

    def test_positive_electrode_thickness(self):
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

    def test_negative_porosity(self):
        val = self.result["NegativeElectrode"]["Coating"]["porosity"]
        assert val == pytest.approx(0.253991)

    def test_positive_porosity(self):
        val = self.result["PositiveElectrode"]["Coating"]["porosity"]
        assert val == pytest.approx(0.277493)

    def test_separator_porosity(self):
        assert self.result["Separator"]["porosity"] == pytest.approx(0.47)

    def test_negative_conductivity(self):
        val = self.result["NegativeElectrode"]["Coating"]["electronicConductivity"]
        assert val == pytest.approx(0.222)

    def test_positive_conductivity(self):
        val = self.result["PositiveElectrode"]["Coating"]["electronicConductivity"]
        assert val == pytest.approx(0.789)

    def test_negative_saturation_concentration(self):
        val = self.result["NegativeElectrode"]["Coating"]["ActiveMaterial"][
            "Interface"
        ]["saturationConcentration"]
        assert val == pytest.approx(29730)

    def test_positive_saturation_concentration(self):
        val = self.result["PositiveElectrode"]["Coating"]["ActiveMaterial"][
            "Interface"
        ]["saturationConcentration"]
        assert val == pytest.approx(46200)

    def test_negative_diffusivity(self):
        val = self.result["NegativeElectrode"]["Coating"]["ActiveMaterial"][
            "SolidDiffusion"
        ]["referenceDiffusionCoefficient"]
        assert val == pytest.approx(2.728e-14)

    def test_positive_diffusivity(self):
        val = self.result["PositiveElectrode"]["Coating"]["ActiveMaterial"][
            "SolidDiffusion"
        ]["referenceDiffusionCoefficient"]
        assert val == pytest.approx(3.2e-14)

    def test_negative_reaction_rate(self):
        val = self.result["NegativeElectrode"]["Coating"]["ActiveMaterial"][
            "Interface"
        ]["reactionRateConstant"]
        assert val == pytest.approx(5.199e-06)

    def test_positive_reaction_rate(self):
        val = self.result["PositiveElectrode"]["Coating"]["ActiveMaterial"][
            "Interface"
        ]["reactionRateConstant"]
        assert val == pytest.approx(2.305e-05)

    def test_negative_ocp_is_function_object(self):
        ocp = self.result["NegativeElectrode"]["Coating"]["ActiveMaterial"][
            "Interface"
        ]["openCircuitPotential"]
        assert isinstance(ocp, dict)
        assert ocp["functionFormat"] == "string expression"
        assert "stoichiometry" in ocp["argumentList"]
        assert "exp(" in ocp["expression"]

    def test_positive_ocp_is_function_object(self):
        ocp = self.result["PositiveElectrode"]["Coating"]["ActiveMaterial"][
            "Interface"
        ]["openCircuitPotential"]
        assert isinstance(ocp, dict)
        assert ocp["functionFormat"] == "string expression"
        assert "stoichiometry" in ocp["argumentList"]
        assert "tanh(" in ocp["expression"]

    def test_electrolyte_conductivity_is_function(self):
        cond = self.result["Electrolyte"]["ionicConductivity"]
        assert isinstance(cond, dict)
        assert cond["functionFormat"] == "string expression"
        assert "concentration" in cond["argumentList"]
        assert len(cond["expression"]) > 0

    def test_electrolyte_diffusivity_is_function(self):
        diff = self.result["Electrolyte"]["diffusionCoefficient"]
        assert isinstance(diff, dict)
        assert diff["functionFormat"] == "string expression"
        assert "concentration" in diff["argumentList"]
        assert len(diff["expression"]) > 0

    def test_electrolyte_transference_number(self):
        val = self.result["Electrolyte"]["species"]["transferenceNumber"]
        assert val == pytest.approx(0.2594)

    def test_electrolyte_initial_concentration(self):
        val = self.result["Electrolyte"]["species"]["nominalConcentration"]
        assert val == pytest.approx(1000)

    def test_lower_cutoff_voltage(self):
        assert self.result["Control"]["lowerCutoffVoltage"] == pytest.approx(2.7)

    def test_upper_cutoff_voltage(self):
        assert self.result["Control"]["upperCutoffVoltage"] == pytest.approx(4.2)

    def test_negative_stoichiometry_100(self):
        val = self.result["NegativeElectrode"]["Coating"]["ActiveMaterial"][
            "Interface"
        ]["guestStoichiometry100"]
        assert val == pytest.approx(0.75668)

    def test_negative_stoichiometry_0(self):
        val = self.result["NegativeElectrode"]["Coating"]["ActiveMaterial"][
            "Interface"
        ]["guestStoichiometry0"]
        assert val == pytest.approx(0.005504)

    def test_negative_activation_energy_reaction(self):
        val = self.result["NegativeElectrode"]["Coating"]["ActiveMaterial"][
            "Interface"
        ]["activationEnergyOfReaction"]
        assert val == pytest.approx(55000)

    def test_negative_activation_energy_diffusion(self):
        val = self.result["NegativeElectrode"]["Coating"]["ActiveMaterial"][
            "SolidDiffusion"
        ]["activationEnergyOfDiffusion"]
        assert val == pytest.approx(30000)


class TestBPXToBattMoJl:
    """Verify battmo.jl uses the same format as battmo.m."""

    @pytest.fixture(autouse=True)
    def _setup(self, ontology, bpx_input):
        self.result_m = _convert(
            ontology, bpx_input, "bpx", "battmo.m", SAMPLE_BPX
        )
        self.result_jl = _convert(
            ontology, bpx_input, "bpx", "battmo.jl", SAMPLE_BPX
        )

    def test_battmo_m_and_jl_produce_same_output(self):
        assert json.dumps(self.result_m, sort_keys=True) == json.dumps(
            self.result_jl, sort_keys=True
        )


# ---------------------------------------------------------------------------
# BattMo → BPX
# ---------------------------------------------------------------------------
class TestBattMoToBPX:
    """Test conversion from BattMo format to BPX format."""

    @pytest.fixture(autouse=True)
    def _setup(self, ontology, battmo_input):
        self.result = _convert(
            ontology, battmo_input, "battmo.m", "bpx", SAMPLE_BATTMO
        )

    def test_has_header(self):
        assert "Header" in self.result

    def test_has_parameterisation(self):
        assert "Parameterisation" in self.result

    def test_negative_thickness(self):
        val = self.result["Parameterisation"]["Negative electrode"]["Thickness [m]"]
        assert val == pytest.approx(5.62e-05)

    def test_positive_thickness(self):
        val = self.result["Parameterisation"]["Positive electrode"]["Thickness [m]"]
        assert val == pytest.approx(5.23e-05)

    def test_separator_thickness(self):
        val = self.result["Parameterisation"]["Separator"]["Thickness [m]"]
        assert val == pytest.approx(2e-05)

    def test_negative_particle_radius(self):
        val = self.result["Parameterisation"]["Negative electrode"][
            "Particle radius [m]"
        ]
        assert val == pytest.approx(4.12e-06)

    def test_positive_particle_radius(self):
        val = self.result["Parameterisation"]["Positive electrode"][
            "Particle radius [m]"
        ]
        assert val == pytest.approx(4.6e-06)

    def test_negative_porosity(self):
        val = self.result["Parameterisation"]["Negative electrode"]["Porosity"]
        assert val == pytest.approx(0.253991)

    def test_positive_porosity(self):
        val = self.result["Parameterisation"]["Positive electrode"]["Porosity"]
        assert val == pytest.approx(0.277493)

    def test_separator_porosity(self):
        val = self.result["Parameterisation"]["Separator"]["Porosity"]
        assert val == pytest.approx(0.47)

    def test_negative_conductivity(self):
        val = self.result["Parameterisation"]["Negative electrode"][
            "Conductivity [S.m-1]"
        ]
        assert val == pytest.approx(0.222)

    def test_positive_conductivity(self):
        val = self.result["Parameterisation"]["Positive electrode"][
            "Conductivity [S.m-1]"
        ]
        assert val == pytest.approx(0.789)

    def test_negative_max_concentration(self):
        val = self.result["Parameterisation"]["Negative electrode"][
            "Maximum concentration [mol.m-3]"
        ]
        assert val == pytest.approx(29730)

    def test_positive_max_concentration(self):
        val = self.result["Parameterisation"]["Positive electrode"][
            "Maximum concentration [mol.m-3]"
        ]
        assert val == pytest.approx(46200)

    def test_negative_ocp_is_string(self):
        ocp = self.result["Parameterisation"]["Negative electrode"]["OCP [V]"]
        assert isinstance(ocp, str)
        assert "exp(" in ocp

    def test_positive_ocp_is_string(self):
        ocp = self.result["Parameterisation"]["Positive electrode"]["OCP [V]"]
        assert isinstance(ocp, str)
        assert "tanh(" in ocp

    def test_electrolyte_conductivity_is_string(self):
        cond = self.result["Parameterisation"]["Electrolyte"]["Conductivity [S.m-1]"]
        assert isinstance(cond, str)
        assert len(cond) > 0

    def test_electrolyte_diffusivity_is_string(self):
        diff = self.result["Parameterisation"]["Electrolyte"]["Diffusivity [m2.s-1]"]
        assert isinstance(diff, str)
        assert len(diff) > 0

    def test_electrolyte_transference(self):
        val = self.result["Parameterisation"]["Electrolyte"][
            "Cation transference number"
        ]
        assert val == pytest.approx(0.2594)

    def test_electrolyte_initial_concentration(self):
        val = self.result["Parameterisation"]["Electrolyte"][
            "Initial concentration [mol.m-3]"
        ]
        assert val == pytest.approx(1000)

    def test_lower_cutoff_voltage(self):
        val = self.result["Parameterisation"]["Cell"]["Lower voltage cut-off [V]"]
        assert val == pytest.approx(2.7)

    def test_upper_cutoff_voltage(self):
        val = self.result["Parameterisation"]["Cell"]["Upper voltage cut-off [V]"]
        assert val == pytest.approx(4.2)

    def test_negative_diffusivity(self):
        val = self.result["Parameterisation"]["Negative electrode"][
            "Diffusivity [m2.s-1]"
        ]
        assert val == pytest.approx(2.728e-14)

    def test_negative_reaction_rate(self):
        val = self.result["Parameterisation"]["Negative electrode"][
            "Reaction rate constant [mol.m-2.s-1]"
        ]
        assert val == pytest.approx(5.199e-06)

    def test_negative_activation_energy_diffusion(self):
        val = self.result["Parameterisation"]["Negative electrode"][
            "Diffusivity activation energy [J.mol-1]"
        ]
        assert val == pytest.approx(30000)

    def test_negative_activation_energy_reaction(self):
        val = self.result["Parameterisation"]["Negative electrode"][
            "Reaction rate constant activation energy [J.mol-1]"
        ]
        assert val == pytest.approx(55000)


# ---------------------------------------------------------------------------
# BPX → JSON-LD
# ---------------------------------------------------------------------------
class TestBPXToJSONLD:
    """Test conversion from BPX format to JSON-LD."""

    @pytest.fixture(autouse=True)
    def _setup(self, ontology, bpx_input, tmp_path):
        outpath = str(tmp_path / "bpx_jsonld.json")
        bmm.export_jsonld(
            ontology, "bpx", bpx_input, outpath,
            cell_id="TestCell", cell_type="PouchCell",
        )
        with open(outpath) as f:
            self.result = json.load(f)

    def test_has_context(self):
        assert "@context" in self.result

    def test_has_graph(self):
        assert "@graph" in self.result

    def test_has_properties(self):
        assert "hasProperty" in self.result["@graph"]
        assert len(self.result["@graph"]["hasProperty"]) > 0

    def test_numeric_values_have_numerical_part(self):
        props = self.result["@graph"]["hasProperty"]
        numeric_props = [p for p in props if "hasNumericalPart" in p]
        assert len(numeric_props) > 0
        for prop in numeric_props:
            assert "hasNumericalValue" in prop["hasNumericalPart"]

    def test_string_values_have_string_part(self):
        props = self.result["@graph"]["hasProperty"]
        string_props = [p for p in props if "hasStringPart" in p]
        assert len(string_props) > 0
        for prop in string_props:
            assert "hasStringValue" in prop["hasStringPart"]


# ---------------------------------------------------------------------------
# BattMo → JSON-LD
# ---------------------------------------------------------------------------
class TestBattMoToJSONLD:
    """Test conversion from BattMo format to JSON-LD."""

    @pytest.fixture(autouse=True)
    def _setup(self, ontology, battmo_input, tmp_path):
        outpath = str(tmp_path / "battmo_jsonld.json")
        bmm.export_jsonld(
            ontology, "battmo.m", battmo_input, outpath,
            cell_id="BattMoCell", cell_type="PouchCell",
        )
        with open(outpath) as f:
            self.result = json.load(f)

    def test_has_context(self):
        assert "@context" in self.result

    def test_has_graph(self):
        assert "@graph" in self.result

    def test_cell_id(self):
        assert self.result["@graph"]["@id"] == "BattMoCell"

    def test_cell_type(self):
        assert self.result["@graph"]["@type"] == "PouchCell"

    def test_has_properties(self):
        assert len(self.result["@graph"]["hasProperty"]) > 0

    def test_numeric_values_have_numerical_part(self):
        props = self.result["@graph"]["hasProperty"]
        numeric_props = [p for p in props if "hasNumericalPart" in p]
        assert len(numeric_props) > 0

    def test_string_values_have_string_part(self):
        props = self.result["@graph"]["hasProperty"]
        string_props = [p for p in props if "hasStringPart" in p]
        assert len(string_props) > 0

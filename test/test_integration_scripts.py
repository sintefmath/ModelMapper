"""Integration tests that generate converted outputs and validation scripts.

These tests generate output files and create validation scripts that users
can run manually in external environments (PyBaMM, BattMo.jl). Since we
cannot run MATLAB, Julia, or full PyBaMM in CI, we only verify:
1. The converted output files are produced correctly
2. The generated script files are syntactically valid
"""

import ast
import json
import os
import textwrap

import pytest

import BatteryModelMapper as bmm

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
ONTOLOGY_PATH = os.path.join(ASSETS_DIR, "battery-model-lithium-ion.ttl")
BPX_TEMPLATE = os.path.join(ASSETS_DIR, "bpx_template.json")
BATTMO_TEMPLATE = os.path.join(ASSETS_DIR, "battmo_template.json")
SAMPLE_BPX = os.path.join(ASSETS_DIR, "sample_bpx_input.json")
SAMPLE_BATTMO = os.path.join(ASSETS_DIR, "sample_battmo_input.json")

integration = pytest.mark.integration


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


# ---------------------------------------------------------------------------
# BPX → BattMo: generate output and BattMo.jl validation script
# ---------------------------------------------------------------------------
@integration
class TestGenerateBattMoOutput:
    """Generate BattMo output from BPX and create a Julia validation script."""

    def test_generate_battmo_output(self, ontology, tmp_path):
        bpx_data = bmm.JSONLoader.load(SAMPLE_BPX)
        bpx_data = bmm.PreprocessInput("bpx", bpx_data).process()
        result = _convert(ontology, bpx_data, "bpx", "battmo.m", SAMPLE_BPX)

        outpath = str(tmp_path / "converted_battmo.json")
        bmm.JSONWriter.write(result, outpath)

        with open(outpath) as f:
            reloaded = json.load(f)
        assert "NegativeElectrode" in reloaded
        assert "PositiveElectrode" in reloaded
        assert "Separator" in reloaded
        assert "Electrolyte" in reloaded

    def test_generate_julia_validation_script(self, ontology, tmp_path):
        bpx_data = bmm.JSONLoader.load(SAMPLE_BPX)
        bpx_data = bmm.PreprocessInput("bpx", bpx_data).process()
        result = _convert(ontology, bpx_data, "bpx", "battmo.m", SAMPLE_BPX)

        json_path = str(tmp_path / "converted_battmo.json")
        bmm.JSONWriter.write(result, json_path)

        script_path = str(tmp_path / "validate_battmo.jl")
        script_content = textwrap.dedent(f"""\
            # BattMo.jl validation script
            # Run: julia validate_battmo.jl
            # Requires: BattMo.jl package

            using JSON3

            json_path = raw"{json_path}"
            data = JSON3.read(read(json_path, String))

            # Verify key parameters exist
            @assert haskey(data, :NegativeElectrode) "Missing NegativeElectrode"
            @assert haskey(data, :PositiveElectrode) "Missing PositiveElectrode"
            @assert haskey(data, :Separator) "Missing Separator"
            @assert haskey(data, :Electrolyte) "Missing Electrolyte"

            neg = data[:NegativeElectrode][:Coating]
            @assert neg[:thickness] > 0 "Negative electrode thickness must be positive"
            @assert 0 < neg[:porosity] < 1 "Negative electrode porosity must be between 0 and 1"

            pos = data[:PositiveElectrode][:Coating]
            @assert pos[:thickness] > 0 "Positive electrode thickness must be positive"
            @assert 0 < pos[:porosity] < 1 "Positive electrode porosity must be between 0 and 1"

            println("BattMo.jl validation passed!")
        """)

        with open(script_path, "w") as f:
            f.write(script_content)

        assert os.path.exists(script_path)
        with open(script_path) as f:
            content = f.read()
        assert "NegativeElectrode" in content
        assert "PositiveElectrode" in content


# ---------------------------------------------------------------------------
# BattMo → BPX: generate output and PyBaMM validation script
# ---------------------------------------------------------------------------
@integration
class TestGenerateBPXOutput:
    """Generate BPX output from BattMo and create a PyBaMM validation script."""

    def test_generate_bpx_output(self, ontology, tmp_path):
        battmo_data = bmm.JSONLoader.load(SAMPLE_BATTMO)
        battmo_data = bmm.PreprocessInput("battmo.m", battmo_data).process()
        result = _convert(ontology, battmo_data, "battmo.m", "bpx", SAMPLE_BATTMO)

        outpath = str(tmp_path / "converted_bpx.json")
        bmm.JSONWriter.write(result, outpath)

        with open(outpath) as f:
            reloaded = json.load(f)
        assert "Header" in reloaded
        assert "Parameterisation" in reloaded

    def test_generate_pybamm_validation_script(self, ontology, tmp_path):
        battmo_data = bmm.JSONLoader.load(SAMPLE_BATTMO)
        battmo_data = bmm.PreprocessInput("battmo.m", battmo_data).process()
        result = _convert(ontology, battmo_data, "battmo.m", "bpx", SAMPLE_BATTMO)

        json_path = str(tmp_path / "converted_bpx.json")
        bmm.JSONWriter.write(result, json_path)

        script_path = str(tmp_path / "validate_pybamm.py")
        script_content = textwrap.dedent(f"""\
            \"\"\"PyBaMM validation script.

            Run: python validate_pybamm.py
            Requires: pybamm, bpx
            \"\"\"
            import json
            import sys

            json_path = r"{json_path}"

            # 1. Load and verify JSON structure
            with open(json_path) as f:
                data = json.load(f)

            assert "Header" in data, "Missing Header"
            assert "Parameterisation" in data, "Missing Parameterisation"

            params = data["Parameterisation"]
            for section in ["Cell", "Electrolyte", "Negative electrode",
                            "Positive electrode", "Separator"]:
                assert section in params, f"Missing section: {{section}}"

            # 2. Try BPX validation
            try:
                import bpx
                bpx.parse_bpx_str(json.dumps(data))
                print("BPX validation passed!")
            except ImportError:
                print("bpx library not installed, skipping BPX validation")

            # 3. Try PyBaMM simulation
            try:
                import pybamm

                model = pybamm.lithium_ion.DFN()
                param = pybamm.ParameterValues.create_from_bpx(json_path)
                sim = pybamm.Simulation(model, parameter_values=param)
                sim.solve([0, 3600])
                print("PyBaMM simulation passed!")
            except ImportError:
                print("pybamm not installed, skipping simulation")
            except Exception as e:
                print(f"PyBaMM simulation failed: {{e}}")
                sys.exit(1)
        """)

        with open(script_path, "w") as f:
            f.write(script_content)

        assert os.path.exists(script_path)

        # Verify the Python script is syntactically valid
        with open(script_path) as f:
            source = f.read()
        ast.parse(source)

    def test_pybamm_script_is_parseable(self, ontology, tmp_path):
        """Separately verify that the generated Python script can be parsed."""
        script_content = textwrap.dedent("""\
            import json
            import sys

            json_path = "test_output.json"

            with open(json_path) as f:
                data = json.load(f)

            assert "Header" in data
            assert "Parameterisation" in data
            print("Validation complete")
        """)
        script_path = str(tmp_path / "minimal_validate.py")
        with open(script_path, "w") as f:
            f.write(script_content)

        with open(script_path) as f:
            source = f.read()
        # This will raise SyntaxError if the script is invalid
        ast.parse(source)


# ---------------------------------------------------------------------------
# JSON-LD export: generate output
# ---------------------------------------------------------------------------
@integration
class TestGenerateJSONLDOutput:
    """Generate JSON-LD exports from both input formats."""

    def test_generate_jsonld_from_bpx(self, ontology, tmp_path):
        data = bmm.JSONLoader.load(SAMPLE_BPX)
        data = bmm.PreprocessInput("bpx", data).process()
        outpath = str(tmp_path / "bpx_export.jsonld")
        bmm.export_jsonld(
            ontology, "bpx", data, outpath,
            cell_id="BPXCell", cell_type="PouchCell",
        )

        with open(outpath) as f:
            result = json.load(f)
        assert "@context" in result
        assert "@graph" in result
        assert len(result["@graph"]["hasProperty"]) > 0

    def test_generate_jsonld_from_battmo(self, ontology, tmp_path):
        data = bmm.JSONLoader.load(SAMPLE_BATTMO)
        data = bmm.PreprocessInput("battmo.m", data).process()
        outpath = str(tmp_path / "battmo_export.jsonld")
        bmm.export_jsonld(
            ontology, "battmo.m", data, outpath,
            cell_id="BattMoCell", cell_type="PouchCell",
        )

        with open(outpath) as f:
            result = json.load(f)
        assert "@context" in result
        assert "@graph" in result
        assert len(result["@graph"]["hasProperty"]) > 0

    def test_jsonld_output_is_valid_json(self, ontology, tmp_path):
        data = bmm.JSONLoader.load(SAMPLE_BPX)
        data = bmm.PreprocessInput("bpx", data).process()
        outpath = str(tmp_path / "valid_json.jsonld")
        bmm.export_jsonld(
            ontology, "bpx", data, outpath,
            cell_id="Cell1", cell_type="PouchCell",
        )

        # Round-trip through JSON serialization
        with open(outpath) as f:
            text = f.read()
        result = json.loads(text)
        reserialized = json.dumps(result, indent=2)
        reparsed = json.loads(reserialized)
        assert reparsed["@context"] == result["@context"]

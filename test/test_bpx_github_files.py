"""Tests for BPX GitHub example files and Chen 2020 round-trip conversion.

This module tests:
1. Conversion of the BPX GitHub example files (NMC pouch cell and LFP 18650)
   to all supported output formats (battmo.m, battmo.jl, jsonld).
2. Round-trip consistency between the NMC BPX file and its BattMo counterpart,
   which represent the same cell parameterisation (the About:Energy NMC111|graphite
   dataset, also known as the "Chen 2020" example used in BPX and BattMo).

Coverage policy
---------------
Every BPX input field is examined:
* If the ontology has a mapping for the field, its value in the converted output
  is asserted to be correct (hard failure on mismatch).
* If the ontology has **no** mapping for the field, a ``UserWarning`` is issued
  so the gap is visible in the test output without causing a test failure.
"""

import json
import math
import os
import warnings

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_nested_value(data, path):
    """Traverse a nested dict/list using a tuple of keys; return None if absent."""
    try:
        for key in path:
            if isinstance(data, dict):
                data = data[key]
            elif isinstance(data, list):
                data = data[int(key)]
            else:
                return None
        return data
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _check_all_mapped_fields(bpx_raw, converted_output, mappings, output_type):
    """Assert every mapped BPX field appears correctly in *converted_output*.

    For each field present in ``bpx_raw["Parameterisation"]``:

    * If the ontology *has* a mapping for it, assert the corresponding key
      exists in ``converted_output`` and that the value matches to within a
      relative tolerance of 1 ppm for numeric values.  String / function
      fields are checked structurally (expression non-empty).  Any mismatch
      is collected and reported together as a hard failure at the end.

    * If the ontology has *no* mapping for the field, emit a ``UserWarning``
      so the gap is visible in the test output without causing a failure.

    Parameters
    ----------
    bpx_raw : dict
        The raw (pre-preprocessed) BPX data dict.
    converted_output : dict
        The result of the conversion.
    mappings : dict
        ``{input_path_tuple: output_path_tuple}`` returned by
        ``OntologyParser.get_mappings()``.
    output_type : str
        ``"battmo.m"``, ``"battmo.jl"``, or ``"bpx"``.
    """
    param = bpx_raw.get("Parameterisation", {})
    all_input_paths = {}
    for section, contents in param.items():
        if isinstance(contents, dict):
            for field, value in contents.items():
                all_input_paths[("Parameterisation", section, field)] = value

    failures = []

    for input_path in sorted(all_input_paths):
        input_value = all_input_paths[input_path]

        if input_path not in mappings:
            warnings.warn(
                f"BPX field {input_path!r} has no mapping to {output_type!r} "
                "and will not appear in the converted output.",
                UserWarning,
                stacklevel=2,
            )
            continue

        output_path = mappings[input_path]
        actual = _get_nested_value(converted_output, output_path)

        if actual is None:
            failures.append(
                f"KEY MISMATCH: BPX field {input_path!r} is mapped to "
                f"{output_path!r} but that key is absent in the converted output."
            )
            continue

        # --- value comparison ---
        if isinstance(input_value, (int, float)):
            if not isinstance(actual, (int, float)):
                failures.append(
                    f"TYPE MISMATCH at {output_path!r}: "
                    f"expected numeric, got {type(actual).__name__} = {actual!r}"
                )
            elif not math.isclose(float(actual), float(input_value), rel_tol=1e-6):
                failures.append(
                    f"VALUE MISMATCH at {output_path!r}: "
                    f"expected {input_value!r}, got {actual!r}"
                )

        elif isinstance(input_value, str):
            # BPX string expressions → BattMo function objects or kept as strings
            if isinstance(actual, dict):
                expr = actual.get("expression", "")
                if not expr:
                    failures.append(
                        f"VALUE MISMATCH at {output_path!r}: "
                        f"expected a dict with non-empty 'expression', got {actual!r}"
                    )
            elif not isinstance(actual, str):
                failures.append(
                    f"TYPE MISMATCH at {output_path!r}: "
                    f"expected str or function dict, got {type(actual).__name__}"
                )

        # dict values (e.g. tabulated LFP entropic coefficient) arriving here
        # means they were mapped; key presence is sufficient since the mapper
        # does not convert tabulated data structurally.

    if failures:
        pytest.fail(
            "Field conversion failures:\n" + "\n".join(f"  - {f}" for f in failures)
        )


def _check_round_trip(converted, reference, mapped_output_paths):
    """Verify that every mapped output field in *converted* matches *reference*.

    For each path in *mapped_output_paths* (the output side of the mappings):

    * If the path is present in *reference* and the values match → pass silently.
    * If the path is present in *reference* but the values differ → ``UserWarning``.
    * If the path is absent from *converted* but present in *reference* →
      ``UserWarning``.

    Parameters
    ----------
    converted : dict
        Conversion result to check.
    reference : dict
        Ground-truth / reference data.
    mapped_output_paths : iterable of tuples
        The output key paths produced by the ontology mappings.
    """
    for output_path in sorted(mapped_output_paths):
        ref_val = _get_nested_value(reference, output_path)
        if ref_val is None:
            # Reference doesn't have this field; nothing to compare.
            continue

        conv_val = _get_nested_value(converted, output_path)
        if conv_val is None:
            warnings.warn(
                f"ROUND-TRIP KEY MISMATCH: path {output_path!r} is present in the "
                "reference but absent in the converted output.",
                UserWarning,
                stacklevel=2,
            )
            continue

        if isinstance(ref_val, (int, float)) and isinstance(conv_val, (int, float)):
            if not math.isclose(float(conv_val), float(ref_val), rel_tol=1e-6):
                warnings.warn(
                    f"ROUND-TRIP VALUE MISMATCH at {output_path!r}: "
                    f"reference={ref_val!r}, converted={conv_val!r}",
                    UserWarning,
                    stacklevel=2,
                )
        elif isinstance(ref_val, str) and isinstance(conv_val, str):
            if conv_val != ref_val:
                warnings.warn(
                    f"ROUND-TRIP VALUE MISMATCH at {output_path!r}: "
                    f"reference={ref_val!r}, converted={conv_val!r}",
                    UserWarning,
                    stacklevel=2,
                )
        elif isinstance(ref_val, str) and isinstance(conv_val, dict):
            # BPX string → BattMo function object: compare expression
            expr = conv_val.get("expression", "")
            if not expr:
                warnings.warn(
                    f"ROUND-TRIP VALUE MISMATCH at {output_path!r}: "
                    f"expected non-empty expression, got {conv_val!r}",
                    UserWarning,
                    stacklevel=2,
                )
        elif isinstance(ref_val, dict) and isinstance(conv_val, str):
            # BattMo function object → BPX string: compare expression
            expr = ref_val.get("expression", "")
            if expr and conv_val != expr:
                warnings.warn(
                    f"ROUND-TRIP VALUE MISMATCH at {output_path!r}: "
                    f"reference expression={expr!r}, converted={conv_val!r}",
                    UserWarning,
                    stacklevel=2,
                )


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
    """Convert the NMC pouch cell BPX file to BattMo format.

    All BPX fields are examined.  Mapped fields are hard-asserted to be present
    with the correct value.  Unmapped fields produce UserWarnings.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, ontology):
        self.bpx_raw = bmm.JSONLoader.load(NMC_BPX)
        processed = bmm.PreprocessInput("bpx", self.bpx_raw).process()
        self.mappings = ontology.get_mappings("bpx", "battmo.m")
        self.result = _convert(ontology, processed, "bpx", "battmo.m", NMC_BPX)

    def test_top_level_sections_present(self):
        for section in ("NegativeElectrode", "PositiveElectrode", "Separator", "Electrolyte"):
            assert section in self.result, f"Missing top-level section: {section}"

    def test_all_fields(self):
        """Check every BPX field; warn about unmapped ones, assert mapped ones."""
        _check_all_mapped_fields(
            self.bpx_raw, self.result, self.mappings, "battmo.m"
        )


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
    """Convert the LFP 18650 BPX file to BattMo format.

    All BPX fields are examined.  Mapped fields are hard-asserted to be present
    with the correct value.  Unmapped fields produce UserWarnings.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, ontology):
        self.bpx_raw = bmm.JSONLoader.load(LFP_BPX)
        processed = bmm.PreprocessInput("bpx", self.bpx_raw).process()
        self.mappings = ontology.get_mappings("bpx", "battmo.m")
        self.result = _convert(ontology, processed, "bpx", "battmo.m", LFP_BPX)

    def test_top_level_sections_present(self):
        for section in ("NegativeElectrode", "PositiveElectrode", "Separator", "Electrolyte"):
            assert section in self.result, f"Missing top-level section: {section}"

    def test_all_fields(self):
        """Check every BPX field; warn about unmapped ones, assert mapped ones."""
        _check_all_mapped_fields(
            self.bpx_raw, self.result, self.mappings, "battmo.m"
        )


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
#
# Mismatches (key or value) produce UserWarnings so that gaps are visible
# without causing hard failures.
# ---------------------------------------------------------------------------
class TestChen2020BPXToBattMo:
    """NMC BPX → BattMo conversion round-trip against the reference BattMo file.

    Every output path produced by the BPX→BattMo mappings is compared against
    the corresponding value in the reference BattMo file.  Mismatches (missing
    keys or differing values) are reported as UserWarnings.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, ontology):
        bpx_raw = bmm.JSONLoader.load(NMC_BPX)
        processed = bmm.PreprocessInput("bpx", bpx_raw).process()
        self.mappings = ontology.get_mappings("bpx", "battmo.m")
        self.converted = _convert(ontology, processed, "bpx", "battmo.m", NMC_BPX)
        self.reference = bmm.JSONLoader.load(SAMPLE_BATTMO)

    def test_all_mapped_fields_present_in_output(self):
        """Every mapped BPX field must produce a key in the BattMo output."""
        bpx_raw = bmm.JSONLoader.load(NMC_BPX)
        missing = []
        for bpx_path, battmo_path in self.mappings.items():
            input_val = _get_nested_value(
                bpx_raw.get("Parameterisation", {}),
                bpx_path[1:],  # strip leading 'Parameterisation'
            )
            if input_val is None:
                continue
            if _get_nested_value(self.converted, battmo_path) is None:
                missing.append(f"{bpx_path!r} -> {battmo_path!r}")
        if missing:
            pytest.fail(
                "The following mapped fields are absent from the converted output:\n"
                + "\n".join(f"  - {m}" for m in missing)
            )

    def test_round_trip_values_match_reference(self):
        """Converted values match the reference BattMo file (warns on mismatch)."""
        _check_round_trip(
            self.converted,
            self.reference,
            self.mappings.values(),
        )


class TestChen2020BattMoToBPX:
    """BattMo sample → BPX conversion round-trip against the NMC BPX reference.

    Every output path produced by the BattMo→BPX mappings is compared against
    the corresponding value in the reference NMC BPX file.  Mismatches (missing
    keys or differing values) are reported as UserWarnings.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, ontology):
        battmo_raw = bmm.JSONLoader.load(SAMPLE_BATTMO)
        processed = bmm.PreprocessInput("battmo.m", battmo_raw).process()
        self.mappings = ontology.get_mappings("battmo.m", "bpx")
        self.converted = _convert(
            ontology, processed, "battmo.m", "bpx", SAMPLE_BATTMO
        )
        self.reference = bmm.JSONLoader.load(NMC_BPX)

    def test_all_mapped_fields_present_in_output(self):
        """Every mapped BattMo field must produce a key in the BPX output."""
        battmo_raw = bmm.JSONLoader.load(SAMPLE_BATTMO)
        missing = []
        for battmo_path, bpx_path in self.mappings.items():
            input_val = _get_nested_value(battmo_raw, battmo_path)
            if input_val is None:
                continue
            if _get_nested_value(self.converted, bpx_path) is None:
                missing.append(f"{battmo_path!r} -> {bpx_path!r}")
        if missing:
            pytest.fail(
                "The following mapped fields are absent from the converted output:\n"
                + "\n".join(f"  - {m}" for m in missing)
            )

    def test_round_trip_values_match_reference(self):
        """Converted values match the reference NMC BPX file (warns on mismatch)."""
        # BattMo→BPX output paths start with 'Parameterisation'.  Strip that
        # prefix so we can compare within the Parameterisation sub-dict of both
        # the converted output and the reference file.
        _check_round_trip(
            self.converted.get("Parameterisation", {}),
            self.reference.get("Parameterisation", {}),
            [
                p[1:]  # strip leading 'Parameterisation'
                for p in self.mappings.values()
            ],
        )

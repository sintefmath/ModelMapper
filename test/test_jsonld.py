"""Test JSON-LD export structure and content."""

import json
import os

import pytest

import BatteryModelMapper as bmm

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
ONTOLOGY_PATH = os.path.join(ASSETS_DIR, "battery-model-lithium-ion.ttl")
SAMPLE_BPX = os.path.join(ASSETS_DIR, "sample_bpx_input.json")
SAMPLE_BATTMO = os.path.join(ASSETS_DIR, "sample_battmo_input.json")


@pytest.fixture(scope="module")
def ontology():
    return bmm.OntologyParser(ONTOLOGY_PATH)


@pytest.fixture(scope="module")
def jsonld_from_bpx(ontology, tmp_path_factory):
    data = bmm.JSONLoader.load(SAMPLE_BPX)
    data = bmm.PreprocessInput("bpx", data).process()
    outpath = str(tmp_path_factory.mktemp("jsonld") / "bpx_export.jsonld")
    bmm.export_jsonld(
        ontology, "bpx", data, outpath,
        cell_id="BPXCell", cell_type="PouchCell",
    )
    with open(outpath) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def jsonld_from_battmo(ontology, tmp_path_factory):
    data = bmm.JSONLoader.load(SAMPLE_BATTMO)
    data = bmm.PreprocessInput("battmo.m", data).process()
    outpath = str(tmp_path_factory.mktemp("jsonld") / "battmo_export.jsonld")
    bmm.export_jsonld(
        ontology, "battmo.m", data, outpath,
        cell_id="BattMoCell", cell_type="PouchCell",
    )
    with open(outpath) as f:
        return json.load(f)


class TestJSONLDStructureBPX:
    """Verify JSON-LD structure from BPX export."""

    def test_has_context(self, jsonld_from_bpx):
        assert "@context" in jsonld_from_bpx

    def test_context_value(self, jsonld_from_bpx):
        assert jsonld_from_bpx["@context"].startswith("https://w3id.org/")

    def test_has_graph(self, jsonld_from_bpx):
        assert "@graph" in jsonld_from_bpx

    def test_graph_has_id(self, jsonld_from_bpx):
        assert jsonld_from_bpx["@graph"]["@id"] == "BPXCell"

    def test_graph_has_type(self, jsonld_from_bpx):
        assert jsonld_from_bpx["@graph"]["@type"] == "PouchCell"

    def test_has_property_list(self, jsonld_from_bpx):
        assert "hasProperty" in jsonld_from_bpx["@graph"]
        assert isinstance(jsonld_from_bpx["@graph"]["hasProperty"], list)

    def test_properties_not_empty(self, jsonld_from_bpx):
        assert len(jsonld_from_bpx["@graph"]["hasProperty"]) > 0


class TestJSONLDStructureBattMo:
    """Verify JSON-LD structure from BattMo export."""

    def test_has_context(self, jsonld_from_battmo):
        assert "@context" in jsonld_from_battmo

    def test_has_graph(self, jsonld_from_battmo):
        assert "@graph" in jsonld_from_battmo

    def test_graph_has_id(self, jsonld_from_battmo):
        assert jsonld_from_battmo["@graph"]["@id"] == "BattMoCell"

    def test_properties_not_empty(self, jsonld_from_battmo):
        assert len(jsonld_from_battmo["@graph"]["hasProperty"]) > 0


class TestJSONLDPropertyTypes:
    """Verify properties have correct value types."""

    def test_numeric_properties_have_numerical_part(self, jsonld_from_bpx):
        props = jsonld_from_bpx["@graph"]["hasProperty"]
        numeric = [p for p in props if "hasNumericalPart" in p]
        assert len(numeric) > 0
        for prop in numeric:
            part = prop["hasNumericalPart"]
            assert "@type" in part
            assert part["@type"] == "Real"
            assert "hasNumericalValue" in part
            assert isinstance(part["hasNumericalValue"], (int, float))

    def test_string_properties_have_string_part(self, jsonld_from_bpx):
        props = jsonld_from_bpx["@graph"]["hasProperty"]
        strings = [p for p in props if "hasStringPart" in p]
        assert len(strings) > 0
        for prop in strings:
            part = prop["hasStringPart"]
            assert "@type" in part
            assert part["@type"] == "String"
            assert "hasStringValue" in part
            assert isinstance(part["hasStringValue"], str)

    def test_each_property_has_type(self, jsonld_from_bpx):
        props = jsonld_from_bpx["@graph"]["hasProperty"]
        for prop in props:
            assert "@type" in prop

    def test_each_property_has_label(self, jsonld_from_bpx):
        props = jsonld_from_bpx["@graph"]["hasProperty"]
        for prop in props:
            assert "rdfs:label" in prop


class TestJSONLDMappedParameters:
    """Verify that key parameters appear in JSON-LD output."""

    def _find_property_by_label_substring(self, props, substring):
        """Find a property whose label contains the given substring (case-insensitive)."""
        substring_lower = substring.lower()
        return [
            p for p in props
            if substring_lower in p.get("rdfs:label", "").lower()
        ]

    def test_porosity_properties_present(self, jsonld_from_bpx):
        props = jsonld_from_bpx["@graph"]["hasProperty"]
        porosity_props = self._find_property_by_label_substring(props, "porosity")
        assert len(porosity_props) > 0

    def test_thickness_properties_present(self, jsonld_from_bpx):
        props = jsonld_from_bpx["@graph"]["hasProperty"]
        thickness_props = self._find_property_by_label_substring(props, "thickness")
        assert len(thickness_props) > 0

    def test_ocp_properties_present(self, jsonld_from_bpx):
        props = jsonld_from_bpx["@graph"]["hasProperty"]
        ocp_props = self._find_property_by_label_substring(props, "opencircuit")
        assert len(ocp_props) > 0

    def test_conductivity_properties_present(self, jsonld_from_bpx):
        props = jsonld_from_bpx["@graph"]["hasProperty"]
        cond_props = self._find_property_by_label_substring(props, "conductivity")
        assert len(cond_props) > 0


class TestJSONLDSerializable:
    """Verify JSON-LD output is valid JSON."""

    def test_round_trip_serialization(self, jsonld_from_bpx, tmp_path):
        outpath = str(tmp_path / "roundtrip.jsonld")
        with open(outpath, "w") as f:
            json.dump(jsonld_from_bpx, f, indent=2)

        with open(outpath) as f:
            reloaded = json.load(f)

        assert reloaded["@context"] == jsonld_from_bpx["@context"]
        assert len(reloaded["@graph"]["hasProperty"]) == len(
            jsonld_from_bpx["@graph"]["hasProperty"]
        )

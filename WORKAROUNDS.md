# Workarounds and Known Issues

This document tracks workarounds applied in this repository that circumvent limitations
in the upstream EMMO ontology or in the external battery simulation software. These should
be addressed in the upstream projects when possible.

## TTL Ontology Workarounds

### 1. Upper Voltage Cut-Off (added locally)

**Issue**: The upstream EMMO battery ontology does not include a mapping for the upper
voltage cut-off parameter. Only the lower voltage cut-off
(`electrochemistry_534dd59c_904c_45d9_8550_ae9d2eb6bbc9`) was defined.

**Workaround**: Added a local class `:modellib_upper_cutoff_voltage` in
`assets/battery-model-lithium-ion.ttl` with mappings for:
- BPX: `['Parameterisation','Cell','Upper voltage cut-off [V]']`
- CIDEMOD: `['simulation','triggers','voltage','upper']`
- BattMo: `['Control','upperCutoffVoltage']`

**Upstream fix needed**: Add `UpperVoltageCutOff` to the EMMO electrochemistry domain
ontology with proper class hierarchy.

### 2. BattMo.jl uses same key as BattMo.m

**Issue**: BattMo.jl and BattMo.m use the same JSON input format, so they share the same
`battmoKey` annotation property in the TTL. If the formats diverge in the future, a
separate `battmoJlKey` annotation property would need to be added to the TTL.

**Current approach**: Both `battmo.m` and `battmo.jl` map to the same URI
(`bmli_e5e86474_8623_48ea_a1cf_502bdb10aa14`) in `OntologyParser.key_map`.

### 3. Missing BattMo mappings for some BPX parameters

**Issue**: Several BPX parameters have no BattMo equivalent in the TTL:
- Cell density (`Density [kg.m-3]`)
- Cell volume (`Volume [m3]`)
- Cell specific heat capacity (`Specific heat capacity [J.K-1.kg-1]`)
- Electrode area (`Electrode area [m2]`)
- External surface area (`External surface area [m2]`)
- Electrolyte conductivity activation energy
- Electrolyte diffusivity activation energy
- Entropic change coefficients (positive/negative electrode)

**Explanation**: These are cell-level or thermal properties that BattMo handles differently
(e.g., through its own thermal model or geometry configuration). Some would require
structural changes to BattMo's JSON format to support directly.

## Code Workarounds

### 4. Function representation conversion

**Issue**: BPX uses Python string expressions for functional parameters (OCP, conductivity,
diffusivity), while BattMo uses structured function objects with `functionFormat`,
`argumentList`, and either `expression` or `functionName`.

**Workaround**: The `ParameterMapper` class handles bidirectional conversion:
- BPX → BattMo: String expressions are wrapped in `{"functionFormat": "string expression", ...}`
- BattMo → BPX: Function objects are unwrapped to extract the expression string
- Named BattMo functions (e.g., `computeOCP_Graphite_Torchio`) cannot be converted to
  BPX and result in a comment string: `# Named function: ... (requires manual conversion)`

**Upstream fix needed**: BattMo.jl/BattMo.m should support string expression evaluation,
or a registry of standard functions with their analytical forms should be maintained.

### 5. Porosity ↔ Volume Fraction

**Issue**: BPX uses `Porosity` directly, while BattMo historically used `volumeFraction`
(where `porosity = 1 - volumeFraction`). Some BattMo input files use `porosity` directly.

**Workaround**: The `PreprocessInput` class computes `porosity = 1 - volumeFraction` when
processing BattMo input that contains `volumeFraction`. If `volumeFraction` is not present
(i.e., the input already has `porosity`), no conversion is performed.

### 6. TTL syntax error (fixed)

**Issue**: The original TTL file had `emmo::hasMeasurementUnit` (double colon) for the
`BatteryCellSurfaceArea` entry, and a duplicated `'Parameterisation'` in the BPX key path.

**Fix**: Corrected to `emmo:hasMeasurementUnit` and removed the duplicate from the path.

**Upstream fix needed**: Fix should be applied to the upstream EMMO battery model ontology.

## Suggestions for External Projects

### BattMo.jl / BattMo.m
- Consider supporting string expression evaluation for OCP and transport property functions,
  which would simplify interoperability with BPX/PyBaMM
- Consider adding cell-level thermal properties (density, specific heat, volume) to the
  JSON input format for better BPX compatibility

### PyBaMM / BPX
- Consider adding support for tabulated data (lookup tables) as an alternative to string
  expressions for OCP and transport properties, which is the standard in BattMo

### EMMO Battery Ontology
- Add `UpperVoltageCutOff` class
- Add transport efficiency / Bruggeman coefficient mappings
- Add electrolyte activation energy mappings for BattMo format
- Add entropic change coefficient mappings for BattMo format

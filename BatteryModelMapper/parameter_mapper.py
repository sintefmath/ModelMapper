import json
import re


class ParameterMapper:
    def __init__(self, mappings, template, input_url, output_type, input_type):
        self.mappings = mappings
        self.template = template
        self.input_url = input_url
        self.output_type = output_type
        self.input_type = input_type
        self.defaults_used = set(self.get_all_paths(template))

    def map_parameters(self, input_data):
        output_data = self.template.copy()
        for input_key, output_key in self.mappings.items():
            value = self.get_value_from_path(input_data, input_key)
            if value is not None:
                value = self.convert_value(value, input_key, output_key)
                self.set_value_from_path(output_data, output_key, value)
                self.remove_default_from_used(output_key)
        if self.output_type == "bpx":
            self.set_bpx_header(output_data)
        self.remove_high_level_defaults()
        return output_data

    def convert_value(self, value, input_key, output_key):
        """Convert a value between formats, handling expressions and functions."""
        # Handle string expressions (BPX/cidemod → battmo)
        if isinstance(value, str) and self.output_type in ("battmo.m", "battmo.jl"):
            value = self.replace_variables(value)
            # Check if target is a function field (OCP, conductivity, diffusivity)
            return self._string_expr_to_battmo_func(value, output_key)
        # Handle battmo function objects → BPX string expressions
        if isinstance(value, dict) and self.output_type == "bpx":
            return self._battmo_func_to_string_expr(value)
        # Handle string variable replacement for BPX output
        if isinstance(value, str) and self.output_type == "bpx":
            value = self.replace_variables(value)
        return value

    def _string_expr_to_battmo_func(self, expr, output_key):
        """Convert a BPX string expression to a BattMo function object."""
        output_path = list(output_key)
        # Determine if this is a function-valued parameter based on output path
        func_params = {
            "openCircuitPotential": (["stoichiometry"],),
            "ionicConductivity": (["concentration", "temperature"],),
            "diffusionCoefficient": (["concentration", "temperature"],),
        }
        for func_name, (arg_list,) in func_params.items():
            if func_name in output_path:
                return {
                    "functionFormat": "string expression",
                    "argumentList": arg_list,
                    "expression": expr,
                }
        return expr

    def _battmo_func_to_string_expr(self, func_obj):
        """Convert a BattMo function object to a string expression."""
        if isinstance(func_obj, dict):
            if "expression" in func_obj:
                return func_obj["expression"]
            if "functionName" in func_obj or "functionname" in func_obj:
                name = func_obj.get("functionName", func_obj.get("functionname", ""))
                return f"# Named function: {name} (requires manual conversion)"
        return str(func_obj)

    def replace_variables(self, value):
        if isinstance(value, str):
            value = re.sub(r"\bx_s\b", "x", value)
            value = re.sub(r"\bc_e\b", "x", value)
        return value

    def get_all_paths(self, data, path=""):
        paths = set()
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                paths.add(current_path)
                paths.update(self.get_all_paths(value, current_path))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                paths.add(current_path)
                paths.update(self.get_all_paths(item, current_path))
        return paths

    def get_value_from_path(self, data, keys):
        try:
            for key in keys:
                if isinstance(key, str):
                    key = key.strip()
                if isinstance(data, dict):
                    data = data[key]
                elif isinstance(data, list):
                    key = int(key)  # Convert key to integer for list index
                    data = data[key]
                else:
                    return None
            return data
        except (KeyError, IndexError, ValueError, TypeError) as e:
            print(f"Warning: accessing key {key} in path {keys}: {e}")
            return None

    def set_value_from_path(self, data, keys, value):
        try:
            for key in keys[:-1]:
                if isinstance(key, str):
                    key = key.strip()
                if isinstance(key, int) or key.isdigit():
                    key = int(key)
                    while len(data) <= key:
                        data.append({})
                    data = data[key]
                else:
                    if key not in data:
                        data[key] = {}
                    data = data[key]
            final_key = keys[-1]
            if isinstance(final_key, str):
                final_key = final_key.strip()
            if isinstance(final_key, int) or (
                isinstance(final_key, str) and final_key.isdigit()
            ):
                final_key = int(final_key)
            data[final_key] = value
            print(f"Set value for path {keys}: {value}")
        except (KeyError, IndexError, ValueError, TypeError) as e:
            print(f"Error setting value for path {keys}: {e}")

    def remove_default_from_used(self, keys):
        path = "Parameterisation"
        for key in keys:
            if isinstance(key, str):
                path += f".{key.strip()}"
            elif isinstance(key, int):
                path += f"[{key}]"
        self.defaults_used.discard(path)

    def set_bpx_header(self, data):
        data["Header"] = {
            "BPX": 0.1,
            "Title": "An autoconverted parameter set using BatteryModelMapper",
            "Description": f"This data set was automatically generated from {self.input_url}. Please check carefully.",
            "Model": "DFN",
        }
        data.pop("Validation", None)

    def remove_high_level_defaults(self):
        self.defaults_used = {
            path
            for path in self.defaults_used
            if not any(k in path for k in ["Parameterisation", "Header"])
        }

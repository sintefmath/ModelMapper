"""Utility script to extract validation data from a BPX JSON file.

The BPX format allows an optional "Validation" section containing experimental
discharge curves (e.g. C/20 discharge, 1C discharge). This script extracts
those curves and saves each experiment as a CSV file.

Usage::

    python scripts/extract_validation_data.py assets/nmc_pouch_cell_BPX.json

This will create one CSV file per experiment found in the Validation section,
named after the experiment (spaces replaced by underscores), e.g.:
    nmc_pouch_cell_BPX_C_20_discharge.csv
    nmc_pouch_cell_BPX_1C_discharge.csv

Each CSV contains the columns present in the experiment data, e.g.:
    Time [s], Current [A], Voltage [V], Temperature [K]

Options
-------
--output-dir   Directory in which to write output CSV files (default: same
               directory as the input file).
--list         List available experiments without writing any files.
"""

import argparse
import csv
import json
import os
import sys


def load_bpx(path):
    """Load a BPX JSON file and return the parsed dict."""
    with open(path) as f:
        return json.load(f)


def list_experiments(data):
    """Return the names of all experiments in the Validation section."""
    validation = data.get("Validation", {})
    return list(validation.keys())


def extract_experiment(data, experiment_name):
    """Return the rows (list of dicts) for a single experiment.

    Parameters
    ----------
    data : dict
        Parsed BPX data.
    experiment_name : str
        Key inside the ``Validation`` section.

    Returns
    -------
    list[dict]
        List of row dicts with column names as keys.
    """
    experiment = data["Validation"][experiment_name]
    columns = list(experiment.keys())
    n_rows = len(experiment[columns[0]])
    rows = []
    for i in range(n_rows):
        row = {col: experiment[col][i] for col in columns}
        rows.append(row)
    return rows, columns


def safe_filename(name):
    """Convert an experiment name to a safe filename fragment."""
    return name.replace("/", "_").replace(" ", "_").replace("\\", "_")


def write_csv(rows, columns, path):
    """Write rows to a CSV file."""
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Extract validation data from a BPX JSON file into CSV files."
    )
    parser.add_argument("bpx_file", help="Path to the BPX JSON file.")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for output CSV files (default: same directory as input file).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available experiments and exit without writing files.",
    )
    args = parser.parse_args(argv)

    bpx_path = args.bpx_file
    if not os.path.isfile(bpx_path):
        print(f"Error: file not found: {bpx_path}", file=sys.stderr)
        sys.exit(1)

    data = load_bpx(bpx_path)

    experiments = list_experiments(data)
    if not experiments:
        print("No Validation section found in the BPX file.", file=sys.stderr)
        sys.exit(0)

    if args.list:
        print("Available experiments:")
        for name in experiments:
            print(f"  {name}")
        return

    output_dir = args.output_dir or os.path.dirname(os.path.abspath(bpx_path))
    os.makedirs(output_dir, exist_ok=True)

    base = os.path.splitext(os.path.basename(bpx_path))[0]

    for experiment_name in experiments:
        rows, columns = extract_experiment(data, experiment_name)
        out_name = f"{base}_{safe_filename(experiment_name)}.csv"
        out_path = os.path.join(output_dir, out_name)
        write_csv(rows, columns, out_path)
        print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()

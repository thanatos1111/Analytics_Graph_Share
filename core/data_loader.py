"""
Load xlsx files with format:
  Row 1: header - A1=ts, rest=parameter names
  Row 2: units (empty for column A)
  Row 3+: timestamp and values
"""
from pathlib import Path

import pandas as pd


def load_xlsx(path: str | Path) -> tuple[pd.DataFrame, dict[str, str]]:
    """
    Load a single xlsx file. Returns (data_df, param_units).
    data_df has index = time (datetime) and columns = parameter names.
    param_units maps parameter name -> unit string (e.g. "Voltage (V)").
    """
    path = Path(path)
    # Read first two rows for header and units
    header_df = pd.read_excel(path, header=None, nrows=2)
    headers = header_df.iloc[0].astype(str).tolist()
    units_row = header_df.iloc[1]

    if headers[0].strip().lower() != "ts":
        raise ValueError(f"Expected column A to be 'ts', got '{headers[0]}'")

    param_names = headers[1:]
    param_units: dict[str, str] = {}
    for i, name in enumerate(param_names):
        u = units_row.iloc[i + 1]
        param_units[name] = str(u).strip() if pd.notna(u) and str(u).strip() else ""

    # Read data from row 3 (0-indexed row 2)
    data_df = pd.read_excel(path, header=None, skiprows=2)
    data_df.columns = headers
    data_df = data_df.rename(columns={headers[0]: "ts"})
    data_df["ts"] = pd.to_datetime(data_df["ts"])
    data_df = data_df.set_index("ts")
    # Keep only parameter columns
    data_df = data_df[param_names]

    return data_df, param_units

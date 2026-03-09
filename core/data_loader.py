"""
Load xlsx files with format:
  Row 1: header - A1=ts, rest=parameter names (original names)
  Row 2: alias with optional unit in brackets, e.g. "Flow (sccm)", "Arcs"
  Row 3+: timestamp and values
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

_ALIAS_UNIT_RE = re.compile(r'^(.+?)\s*\(([^)]+)\)\s*$')


def _parse_alias_unit(raw: str) -> tuple[str, str]:
    """Parse a row-2 cell like ``"Flow (sccm)"`` into ``("Flow", "sccm")``.
    Strips any ``|group=…`` suffix first.  Returns ``(alias, unit)``."""
    text = raw.split("|")[0].strip()
    m = _ALIAS_UNIT_RE.match(text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return text, ""


def load_xlsx(path: str | Path) -> tuple[pd.DataFrame, dict[str, str], dict[str, str]]:
    """
    Load a single xlsx file.

    Returns ``(data_df, param_units, param_aliases)``

    * ``data_df`` – index = time (datetime), columns = original parameter names.
    * ``param_units`` – maps original param name → unit string (e.g. ``"sccm"``).
    * ``param_aliases`` – maps original param name → alias string (e.g. ``"Flow"``).
    """
    path = Path(path)
    header_df = pd.read_excel(path, header=None, nrows=2)
    headers = header_df.iloc[0].astype(str).tolist()
    row2 = header_df.iloc[1]

    if headers[0].strip().lower() != "ts":
        raise ValueError(f"Expected column A to be 'ts', got '{headers[0]}'")

    param_names = headers[1:]
    param_units: dict[str, str] = {}
    param_aliases: dict[str, str] = {}
    for i, name in enumerate(param_names):
        cell = row2.iloc[i + 1]
        if pd.notna(cell) and str(cell).strip():
            alias, unit = _parse_alias_unit(str(cell).strip())
            param_aliases[name] = alias
            param_units[name] = unit
        else:
            param_aliases[name] = name
            param_units[name] = ""

    data_df = pd.read_excel(path, header=None, skiprows=2)
    data_df.columns = headers
    data_df = data_df.rename(columns={headers[0]: "ts"})
    data_df["ts"] = pd.to_datetime(data_df["ts"])
    data_df = data_df.set_index("ts")
    data_df = data_df[param_names]

    return data_df, param_units, param_aliases

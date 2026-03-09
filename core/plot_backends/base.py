"""
Plot backend base and shared data preparation for multi-band time-series charts.
All backends receive the same data contract: data_df, param_units, aliases, plot_style.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

# Shared colors (same as plot_builder)
TRACE_COLORS = [
    "#1f77b4", "#e63946", "#2a9d8f", "#e9c46a", "#9b59b6",
    "#3498db", "#e67e22", "#27ae60", "#c0392b", "#16a085",
    "#8e44ad", "#d35400", "#2980b9", "#27ae60", "#7f8c8d",
    "#2c3e50",
]


def group_params_by_unit(
    param_units: dict[str, str],
    param_order: list[str] | None = None,
    aliases: dict[str, str] | None = None,
) -> list[tuple[str, list[str]]]:
    """Group parameter names into bands.

    * Parameter **with** a unit → gets its own band (one param per band).
    * Parameter **without** a unit → grouped by alias name (same alias = same band).

    Returns list of ``(unit_label, [param_names])``.
    """
    aliases = aliases or {}
    order = param_order or list(param_units.keys())

    bands: list[list] = []          # [[unit_label, [param_names]], ...]
    no_unit_idx: dict[str, int] = {}  # alias -> index in bands

    for name in order:
        if name not in param_units:
            continue
        unit = param_units[name] or ""
        if unit:
            bands.append([unit, [name]])
        else:
            alias = aliases.get(name, name)
            if alias in no_unit_idx:
                bands[no_unit_idx[alias]][1].append(name)
            else:
                no_unit_idx[alias] = len(bands)
                bands.append(["(no unit)", [name]])

    return [(b[0], b[1]) for b in bands]


def prepare_chart_data(
    data_df: pd.DataFrame,
    param_units: dict[str, str],
    aliases: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Produce a JSON-serializable structure for JS backends.
    Returns:
      - time: list of ISO timestamp strings (or ms if preferred)
      - timeMs: list of numbers (ms since epoch) for numeric axes
      - bands: list of { unit, params: [ { name, alias, unit, color, values }, ... ], yMin, yMax }
    """
    aliases = aliases or {}
    param_order = [c for c in data_df.columns if c in param_units]
    groups = group_params_by_unit(param_units, param_order, aliases=aliases)
    ts = data_df.index
    time_strs = [pd.Timestamp(t).isoformat() for t in ts]
    time_ms = [int(pd.Timestamp(t).value / 1e6) for t in ts]

    def _fmt_display(t) -> str:
        p = pd.Timestamp(t)
        return f"{p.year}/{p.month}/{p.day} {p.hour}:{p.minute:02d}:{p.second:02d}"

    time_display = [_fmt_display(t) for t in ts]

    bands = []
    param_index = 0
    for unit_label, param_names in groups:
        params_data = []
        all_vals = []
        for param in param_names:
            if param not in data_df.columns:
                continue
            alias = aliases.get(param, param)
            unit_str = param_units.get(param, "")
            color = TRACE_COLORS[param_index % len(TRACE_COLORS)]
            param_index += 1
            vals = data_df[param].tolist()
            all_vals.extend([v for v in vals if v is not None and pd.notna(v)])
            params_data.append({
                "name": param,
                "alias": alias,
                "unit": unit_str,
                "color": color,
                "values": vals,
            })
        y_vals = [v for v in all_vals if v is not None]
        if y_vals:
            y_min, y_max = min(y_vals), max(y_vals)
            if y_min == y_max:
                y_min, y_max = y_min - 1, y_max + 1
            else:
                pad = (y_max - y_min) * 0.04 or 0.01
                y_min, y_max = y_min - pad, y_max + pad
        else:
            y_min, y_max = 0, 1
        bands.append({
            "unit": unit_label,
            "params": params_data,
            "yMin": y_min,
            "yMax": y_max,
        })

    return {
        "time": time_strs,
        "timeDisplay": time_display,
        "timeMs": time_ms,
        "bands": bands,
    }


def chart_data_to_json(data: dict[str, Any]) -> str:
    """Serialize chart data for embedding in HTML (handle NaN)."""
    def sanitize(obj):
        if isinstance(obj, dict):
            return {k: sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [sanitize(v) for v in obj]
        if isinstance(obj, float) and pd.isna(obj):
            return None
        return obj
    return json.dumps(sanitize(data), ensure_ascii=False)


class PlotBackend(ABC):
    """Abstract plot backend: produces full HTML for the chart."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique backend identifier (e.g. 'plotly', 'uplot')."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Display name for UI (e.g. 'Plotly', 'uPlot')."""
        ...

    @abstractmethod
    def build_html(
        self,
        data_df: pd.DataFrame,
        param_units: dict[str, str],
        *,
        aliases: dict[str, str] | None = None,
        plot_style: dict | None = None,
        for_export: bool = False,
    ) -> str:
        """
        Return full HTML string (including <!DOCTYPE>, <html>, etc.) to display
        the multi-band time-series chart. for_export=True may use CDN for libs.
        """
        ...

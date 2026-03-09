"""
Build a multi-Y time-series plot from a dataframe and param metadata.
Sections are grouped by unit; Y-axes alternate left/right.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# Total plot height in pixels — fixed so all sections fit the panel (no vertical scroll)
TOTAL_PLOT_HEIGHT = 620

# Distinct, readable colors per parameter (repeated if more params than colors)
TRACE_COLORS = [
    "#1f77b4", "#e63946", "#2a9d8f", "#e9c46a", "#9b59b6",
    "#3498db", "#e67e22", "#27ae60", "#c0392b", "#16a085",
    "#8e44ad", "#d35400", "#2980b9", "#27ae60", "#7f8c8d",
    "#2c3e50",
]


def _group_params_by_unit(
    param_units: dict[str, str],
    param_order: list[str] | None = None,
    aliases: dict[str, str] | None = None,
) -> list[tuple[str, list[str]]]:
    """Group parameter names into bands.

    * Parameter **with** a unit → gets its own band (one param per band).
    * Parameter **without** a unit → grouped by alias name (same alias = same band).

    Returns list of ``(unit_label, [param_names])``
    ordered by first occurrence (param_order = column order from file).
    """
    aliases = aliases or {}
    order = param_order or list(param_units.keys())

    bands: list[list] = []
    no_unit_idx: dict[str, int] = {}

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


def build_figure(
    data_df: pd.DataFrame,
    param_units: dict[str, str],
    aliases: dict[str, str] | None = None,
    show_markers: bool = False,
    line_mode: str = "lines",
    line_shape: str = "linear",
    marker_symbol: str = "circle",
    marker_size: int = 6,
) -> go.Figure:
    """
    Build a Plotly figure with one row per unit group, shared X (time),
    Y-axes alternating left/right. Hover shows original name, time, alias: value.
    """
    aliases = aliases or {}
    param_order = [c for c in data_df.columns if c in param_units]
    groups = _group_params_by_unit(param_units, param_order, aliases=aliases)
    n_rows = len(groups)

    if n_rows == 0:
        fig = go.Figure()
        fig.add_annotation(text="No parameters to plot", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    # Alternate Y-axis side: row 0 left, row 1 right, row 2 left, ...
    specs = [[{"secondary_y": (i % 2 == 1)}] for i in range(n_rows)]
    fig = make_subplots(
        rows=n_rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        specs=specs,
        subplot_titles=[None] * n_rows,
        row_heights=[1.0] * n_rows,
    )

    # Explicit y-domains: stack evenly; bottom row is [0, row_height] so x-axis is at figure bottom
    gap = 0.006
    row_height = (1.0 - (n_rows - 1) * gap) / n_rows
    for row_idx in range(n_rows):
        if row_idx < n_rows - 1:
            y_max = 1 - row_idx * (row_height + gap)
            y_min = 1 - (row_idx + 1) * (row_height + gap)
        else:
            y_min = 0
            y_max = row_height
        for k in range(2):
            ax_key = (2 * row_idx + 1 + k)
            key = "yaxis" if ax_key == 1 else f"yaxis{ax_key}"
            if key in fig.layout:
                fig.layout[key].update(domain=[y_min, y_max])

    # Only the bottom row shows the x-axis (common time axis at very bottom)
    for row in range(1, n_rows):
        fig.update_xaxes(
            showticklabels=False,
            title_text="",
            showline=False,
            showgrid=False,
            row=row,
            col=1,
        )
    fig.update_xaxes(title_text="Time", row=n_rows, col=1)

    param_index = 0
    for row_idx, (unit_label, param_names) in enumerate(groups):
        row = row_idx + 1
        # First row left (secondary_y=False), second right (True), then alternating
        secondary_y = (row_idx % 2) == 1

        for col_idx, param in enumerate(param_names):
            if param not in data_df.columns:
                continue
            alias = aliases.get(param, param)
            unit_str = param_units.get(param, "")
            # Y-axis / legend: alias and unit
            display_name = f"{alias} ({unit_str})" if unit_str else alias

            ts = data_df.index
            vals = data_df[param].values
            # Full timestamp for tooltip
            def _fmt(t):
                p = pd.Timestamp(t)
                return f"{p.year}/{p.month}/{p.day} {p.hour}:{p.minute:02d}:{p.second:02d}"
            time_strs = [_fmt(t) for t in ts]

            # Tooltip: row1 original param, row2 Time:, row3 alias: value. <extra></extra> hides default trace name/line
            hovertemplate = (
                "%{customdata[0]}<br>"
                "Time: %{customdata[2]}<br>"
                "%{customdata[1]}: %{y}"
                "<extra></extra>"
            )
            customdata = [
                [param, alias, time_strs[i]] for i in range(len(ts))
            ]

            color = TRACE_COLORS[param_index % len(TRACE_COLORS)]
            param_index += 1

            mode = "lines"
            if show_markers:
                mode = "lines+markers"

            fig.add_trace(
                go.Scatter(
                    x=ts,
                    y=vals,
                    name=display_name,
                    mode=mode,
                    line=dict(color=color, shape=line_shape),
                    marker=dict(symbol=marker_symbol, size=marker_size) if show_markers else None,
                    customdata=customdata,
                    hovertemplate=hovertemplate,
                ),
                row=row,
                col=1,
                secondary_y=secondary_y,
            )

        # Y-axis on one side only: left for even row_idx, right for odd
        fig.update_yaxes(
            title_text=unit_label,
            side="left" if not secondary_y else "right",
            row=row,
            col=1,
            secondary_y=secondary_y,
        )
        # Hide the other side's axis so it doesn't overlap
        fig.update_yaxes(
            showticklabels=False,
            showline=False,
            title_text="",
            row=row,
            col=1,
            secondary_y=not secondary_y,
        )

    # Ensure each row has a non-collapsed y range (fixes zero/constant data; each band stays visible)
    for row_idx, (unit_label, param_names) in enumerate(groups):
        row = row_idx + 1
        vals = []
        for param in param_names:
            if param in data_df.columns:
                vals.extend(data_df[param].dropna().tolist())
        if vals:
            vmin, vmax = min(vals), max(vals)
            if vmin == vmax:
                vmin, vmax = vmin - 1, vmax + 1
            else:
                pad = (vmax - vmin) * 0.04 or 0.01
                vmin, vmax = vmin - pad, vmax + pad
        else:
            vmin, vmax = 0, 1
        # Set range on BOTH primary and secondary y-axes for this row so the band never collapses
        fig.update_yaxes(range=[vmin, vmax], row=row, col=1, secondary_y=False)
        fig.update_yaxes(range=[vmin, vmax], row=row, col=1, secondary_y=True)

    # Fixed height; disable default drag so JS can do x-pan only on bottom axis, y-pan in body
    fig.update_layout(
        height=TOTAL_PLOT_HEIGHT,
        margin=dict(l=70, r=70, t=36, b=48),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="closest",
        paper_bgcolor="white",
        plot_bgcolor="white",
        hoverlabel=dict(
            bgcolor="rgba(255,255,204,0.95)",
            font=dict(size=12),
            namelength=0,
        ),
        dragmode=False,
    )
    # Ensure each subplot has white background
    for row in range(1, n_rows + 1):
        fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.1)", row=row, col=1)
    return fig

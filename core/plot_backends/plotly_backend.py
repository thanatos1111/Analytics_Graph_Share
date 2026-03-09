"""
Plotly backend: uses existing plot_builder + plotly.io.to_html + embed script.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.io as pio

from core.plot_builder import build_figure
from core.plot_backends.base import PlotBackend

# Embed script for crosshair and pan/zoom (only used by Plotly)
if getattr(sys, "frozen", False):
    _EMBED_SCRIPT_PATH = Path(sys._MEIPASS) / "ui" / "plot_embed_script.js"
else:
    _EMBED_SCRIPT_PATH = Path(__file__).resolve().parent.parent.parent / "ui" / "plot_embed_script.js"


class PlotlyBackend(PlotBackend):
    @property
    def id(self) -> str:
        return "plotly"

    @property
    def name(self) -> str:
        return "Plotly"

    def build_html(
        self,
        data_df: pd.DataFrame,
        param_units: dict[str, str],
        *,
        aliases: dict[str, str] | None = None,
        plot_style: dict | None = None,
        for_export: bool = False,
    ) -> str:
        plot_style = plot_style or {}
        aliases = aliases or {}
        fig = build_figure(
            data_df,
            param_units,
            aliases=aliases,
            show_markers=plot_style.get("show_markers", False),
            line_shape=plot_style.get("line_shape", "linear"),
            marker_symbol=plot_style.get("marker_symbol", "circle"),
            marker_size=int(plot_style.get("marker_size", 6)),
        )
        html = pio.to_html(
            fig,
            full_html=True,
            include_plotlyjs="cdn" if for_export else True,
            config={"responsive": True, "scrollZoom": False},
        )
        if _EMBED_SCRIPT_PATH.exists():
            script = _EMBED_SCRIPT_PATH.read_text(encoding="utf-8")
            html = html.replace("</body>", f"<script>\n{script}\n</script>\n</body>")
        return html

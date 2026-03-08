"""
Plot view: displays Plotly figure as HTML in a QWebEngineView.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QVBoxLayout, QWidget

import plotly.io as pio

from core.plot_builder import build_figure

# Temp dir for plot HTML files (loading from file fixes blank display in QWebEngineView)
_TEMP_PLOT_DIR = Path(tempfile.gettempdir()) / "analytics_graph_share"

# Script for crosshair and y-axis zoom/pan (injected into generated HTML)
_EMBED_SCRIPT_PATH = Path(__file__).resolve().parent / "plot_embed_script.js"


def _ensure_temp_dir():
    _TEMP_PLOT_DIR.mkdir(parents=True, exist_ok=True)


def _plot_html_path(view_id: int) -> Path:
    _ensure_temp_dir()
    return _TEMP_PLOT_DIR / f"plot_{view_id}.html"


class PlotView(QWidget):
    def __init__(self, main_window: QWidget, parent=None):
        super().__init__(parent)
        self._main_window = main_window
        self._data_df: pd.DataFrame | None = None
        self._param_units: dict[str, str] = {}
        self._browser = QWebEngineView(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._browser)

    def set_data(self, data_df: pd.DataFrame, param_units: dict[str, str]):
        self._data_df = data_df
        self._param_units = param_units

    def refresh_plot(self):
        if self._data_df is None or self._data_df.empty:
            self._browser.setHtml("<p>No data</p>")
            return
        aliases = getattr(self._main_window, "get_aliases", lambda: {})()
        plot_style = getattr(self._main_window, "get_plot_style", lambda: {})()
        fig = build_figure(
            self._data_df,
            self._param_units,
            aliases=aliases,
            show_markers=plot_style.get("show_markers", False),
            line_shape=plot_style.get("line_shape", "linear"),
            marker_symbol=plot_style.get("marker_symbol", "circle"),
            marker_size=int(plot_style.get("marker_size", 6)),
        )
        html = pio.to_html(
            fig,
            full_html=True,
            include_plotlyjs=True,
            config={"responsive": True, "scrollZoom": False},
        )
        # Inject crosshair and y-axis zoom/pan script
        if _EMBED_SCRIPT_PATH.exists():
            script = _EMBED_SCRIPT_PATH.read_text(encoding="utf-8")
            html = html.replace("</body>", f"<script>\n{script}\n</script>\n</body>")
        # Load from file: QWebEngineView often stays blank with setHtml(); loading a file URL works
        path = _plot_html_path(id(self))
        path.write_text(html, encoding="utf-8")
        self._browser.load(QUrl.fromLocalFile(str(path)))

    def refresh_plot_deferred(self):
        """Call refresh_plot after the layout has run (fixes blank plot when tab just added)."""
        QTimer.singleShot(100, self.refresh_plot)

    def export_html(self, path: str):
        if self._data_df is None or self._data_df.empty:
            return
        aliases = getattr(self._main_window, "get_aliases", lambda: {})()
        plot_style = getattr(self._main_window, "get_plot_style", lambda: {})()
        fig = build_figure(
            self._data_df,
            self._param_units,
            aliases=aliases,
            show_markers=plot_style.get("show_markers", False),
            line_shape=plot_style.get("line_shape", "linear"),
            marker_symbol=plot_style.get("marker_symbol", "circle"),
            marker_size=int(plot_style.get("marker_size", 6)),
        )
        html = pio.to_html(
            fig,
            full_html=True,
            include_plotlyjs="cdn",
            config={"responsive": True, "scrollZoom": False},
        )
        if _EMBED_SCRIPT_PATH.exists():
            script = _EMBED_SCRIPT_PATH.read_text(encoding="utf-8")
            html = html.replace("</body>", f"<script>\n{script}\n</script>\n</body>")
        Path(path).write_text(html, encoding="utf-8")

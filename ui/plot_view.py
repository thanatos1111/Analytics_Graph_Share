"""
Plot view: displays chart as HTML in a QWebEngineView (backend: Plotly, uPlot, D3, Observable Plot, ECharts).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from core.plot_backends import get_backend, get_default_backend_id
from core.plot_backends.html_utils import inline_external_resources

# Temp dir for plot HTML files (loading from file fixes blank display in QWebEngineView)
_TEMP_PLOT_DIR = Path(tempfile.gettempdir()) / "analytics_graph_share"


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
        backend_id = getattr(self._main_window, "get_plot_backend", lambda: get_default_backend_id())()
        backend = get_backend(backend_id)
        if backend is None:
            backend = get_backend(get_default_backend_id())
        aliases = getattr(self._main_window, "get_aliases", lambda: {})()
        plot_style = getattr(self._main_window, "get_plot_style", lambda: {})()
        html = backend.build_html(
            self._data_df,
            self._param_units,
            aliases=aliases,
            plot_style=plot_style,
            for_export=False,
        )
        # Inline external scripts/styles so chart renders from file:// in QWebEngineView
        html = inline_external_resources(html)
        path = _plot_html_path(id(self))
        path.write_text(html, encoding="utf-8")
        self._browser.load(QUrl.fromLocalFile(str(path)))

    def refresh_plot_deferred(self):
        """Call refresh_plot after the layout has run (fixes blank plot when tab just added)."""
        QTimer.singleShot(100, self.refresh_plot)

    def export_html(self, path: str):
        if self._data_df is None or self._data_df.empty:
            return
        backend_id = getattr(self._main_window, "get_plot_backend", lambda: get_default_backend_id())()
        backend = get_backend(backend_id)
        if backend is None:
            backend = get_backend(get_default_backend_id())
        aliases = getattr(self._main_window, "get_aliases", lambda: {})()
        plot_style = getattr(self._main_window, "get_plot_style", lambda: {})()
        html = backend.build_html(
            self._data_df,
            self._param_units,
            aliases=aliases,
            plot_style=plot_style,
            for_export=True,
        )
        Path(path).write_text(html, encoding="utf-8")

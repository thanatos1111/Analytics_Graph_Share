"""
Plot view: displays the D3.js chart as HTML in a QWebEngineView.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from core.plot_backends import get_backend, get_default_backend_id
from core.plot_backends.html_utils import inline_d3_resource, inline_external_resources

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
        self._param_aliases: dict[str, str] = {}
        self._browser = QWebEngineView(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._browser)

    def set_data(self, data_df: pd.DataFrame, param_units: dict[str, str],
                 param_aliases: dict[str, str] | None = None):
        self._data_df = data_df
        self._param_units = param_units
        self._param_aliases = param_aliases or {}

    def refresh_plot(self):
        if self._data_df is None or self._data_df.empty:
            self._browser.setHtml("<p>No data</p>")
            return
        backend = get_backend(get_default_backend_id())
        if backend is None:
            self._browser.setHtml("<p>Plot backend unavailable</p>")
            return
        plot_style = getattr(self._main_window, "get_plot_style", lambda: {})()
        html = backend.build_html(
            self._data_df,
            self._param_units,
            aliases=self._param_aliases,
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
        backend_id = get_default_backend_id()
        backend = get_backend(backend_id)
        if backend is None:
            return
        plot_style = getattr(self._main_window, "get_plot_style", lambda: {})()
        html = backend.build_html(
            self._data_df,
            self._param_units,
            aliases=self._param_aliases,
            plot_style=plot_style,
            for_export=True,
        )
        export_inline_d3 = getattr(self._main_window, "get_export_inline_d3", lambda: False)()
        if export_inline_d3 and backend_id == "d3":
            html = inline_d3_resource(html)
        Path(path).write_text(html, encoding="utf-8")

"""
Plot backends: switchable implementations (Plotly, uPlot, D3.js, Observable Plot, ECharts).
"""
from __future__ import annotations

from core.plot_backends.base import PlotBackend, prepare_chart_data, chart_data_to_json
from core.plot_backends.plotly_backend import PlotlyBackend
from core.plot_backends.uplot_backend import UPlotBackend
from core.plot_backends.d3_backend import D3Backend
from core.plot_backends.observable_plot_backend import ObservablePlotBackend
from core.plot_backends.echarts_backend import EChartsBackend

_BACKENDS: list[PlotBackend] = [
    PlotlyBackend(),
    UPlotBackend(),
    D3Backend(),
    ObservablePlotBackend(),
    EChartsBackend(),
]


def list_backends() -> list[PlotBackend]:
    """Return all registered backends in display order."""
    return list(_BACKENDS)


def get_backend(backend_id: str) -> PlotBackend | None:
    """Return the backend with the given id, or None."""
    for b in _BACKENDS:
        if b.id == backend_id:
            return b
    return None


def get_default_backend_id() -> str:
    """Default backend id when none is configured."""
    return "plotly"

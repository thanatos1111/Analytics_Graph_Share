"""
Plot backends registry.

The app now ships with the D3.js backend only.
"""
from __future__ import annotations

from core.plot_backends.base import PlotBackend, prepare_chart_data, chart_data_to_json
from core.plot_backends.d3_backend import D3Backend

_BACKENDS: list[PlotBackend] = [D3Backend()]


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
    return "d3"

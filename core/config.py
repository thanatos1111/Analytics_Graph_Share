"""
Load/save app config: last data folder, plot style, parameter aliases.
Config file is JSON in the application directory.
"""
from __future__ import annotations

import json
from pathlib import Path

# Default location: next to main.py (project root)
APP_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = APP_DIR / "config.json"

DEFAULT_PLOT_STYLE = {
    "show_markers": False,
    "line_shape": "linear",
    "marker_symbol": "circle",
    "marker_size": 6,
}


def load_config() -> dict:
    """Load config from disk. Returns dict with keys: last_data_folder, plot_style, aliases, auto_export_folder, auto_export_enabled."""
    out = {
        "last_data_folder": "",
        "plot_style": dict(DEFAULT_PLOT_STYLE),
        "aliases": {},
        "auto_export_folder": "",
        "auto_export_enabled": False,
    }
    if not CONFIG_PATH.exists():
        return out
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data.get("last_data_folder"), str):
            out["last_data_folder"] = data["last_data_folder"]
        if isinstance(data.get("plot_style"), dict):
            for k, v in DEFAULT_PLOT_STYLE.items():
                if k in data["plot_style"]:
                    out["plot_style"][k] = data["plot_style"][k]
        if isinstance(data.get("aliases"), dict):
            out["aliases"] = {str(k): str(v) for k, v in data["aliases"].items()}
        if isinstance(data.get("auto_export_folder"), str):
            out["auto_export_folder"] = data["auto_export_folder"]
        if isinstance(data.get("auto_export_enabled"), bool):
            out["auto_export_enabled"] = data["auto_export_enabled"]
    except Exception:
        pass
    return out


def save_config(
    last_data_folder: str | None = None,
    plot_style: dict | None = None,
    aliases: dict | None = None,
    auto_export_folder: str | None = None,
    auto_export_enabled: bool | None = None,
) -> None:
    """Save config to disk. Omitted keys are left unchanged (read then write)."""
    current = load_config()
    if last_data_folder is not None:
        current["last_data_folder"] = last_data_folder
    if plot_style is not None:
        current["plot_style"].update(plot_style)
    if aliases is not None:
        current["aliases"] = dict(aliases)
    if auto_export_folder is not None:
        current["auto_export_folder"] = auto_export_folder
    if auto_export_enabled is not None:
        current["auto_export_enabled"] = auto_export_enabled
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

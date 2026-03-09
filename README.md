# Analytics Graph Share

Desktop app for loading `.xlsx` time-series data, viewing it with the D3.js plot backend, and exporting interactive HTML for sharing.

## D3.js_only branch

This branch is the D3-only version of the app. The plot backend is fixed to `D3.js` for both in-app viewing and HTML export.

## Data format (`.xlsx`)

- **Row 1:** Header row. Cell `A1` must be `ts`. Remaining columns are the original parameter names.
- **Row 2:** Display label and optional unit for each parameter. Example: `Flow (sccm)` or `Arcs`.
- **Row 3+:** Timestamp and numeric data rows.

Behavior for row 2:

- If the cell contains `Alias (unit)`, the app uses `Alias` in labels/tooltips and `unit` for axis grouping.
- If the cell contains only text, that text is used as the alias and the parameter has no unit.

## Features

- **Multi-file workflow:** Load multiple `.xlsx` files at once. Each file appears in the left file list with a checkbox.
- **Tab-per-file plotting:** Checked files get their own plot tabs. Unchecking a file removes its tab.
- **Unit-grouped multi-Y chart:** Parameters are grouped into stacked Y-axis bands by unit. Bands alternate left/right axis placement.
- **Interactive D3 chart controls:**
  - Left-click and hold on a plotted line to show a snapped tooltip and crosshair.
  - Mouse wheel zooms the X axis from the plot area or bottom axis strip.
  - Mouse wheel over a Y ruler zooms that band vertically.
  - Right-drag on the bottom axis strip pans time.
  - Right-drag on a Y ruler pans that band vertically.
  - Drag a band handle to resize that unit band relative to the others.
- **Plot style settings:** Turn point markers on or off and choose marker symbol and size.
- **Export options:** Export the current tab as interactive HTML. Optionally embed the D3 library into the exported file for offline/standalone viewing.
- **Folder monitor auto-export:** Watch a folder for newly added `.xlsx` files and automatically write a same-name `.html` file beside each one.
- **System tray support:** Minimize the app to the system tray and start/stop folder monitoring from the tray menu.
- **Persistent app settings:** The app remembers the last data folder, plot style, watched folder, monitoring state, and export mode in `config.json`.

## Run

**Option A - batch files (Windows)**

1. Run `setup_env.bat` once to install dependencies.
2. Run `start_app.bat` to launch the app.

**Option B - manual**

```bash
pip install -r requirements.txt
python main.py
```

## Typical usage

1. Click `Load xlsx files...` and choose one or more data files.
2. Use the file-list checkboxes to control which plots appear as tabs.
3. Open `Settings -> Plot style and export...` to adjust markers or enable standalone D3 export.
4. Use `File -> Export plot to HTML...` to export the current tab.
5. If needed, set a folder in `Auto-export (folder monitor)` and enable monitoring.

## Requirements

- Python 3
- `pandas`
- `openpyxl`
- `PyQt6`
- `PyQt6-WebEngine`
- `watchdog` for folder monitoring

Install all Python dependencies with:

```bash
pip install -r requirements.txt
```

## Project layout

- `main.py` - Application entry point.
- `core/data_loader.py` - Reads `.xlsx` files and parses aliases/units from row 2.
- `core/config.py` - Loads and saves app settings in `config.json`.
- `core/plot_backends/d3_backend.py` - D3.js chart HTML generator.
- `core/plot_backends/html_utils.py` - Helpers for inlining D3/resources into HTML.
- `ui/main_window.py` - Main window, file list, tabs, tray integration, and auto-export flow.
- `ui/plot_view.py` - Embedded plot view and HTML export logic.
- `ui/settings_dialog.py` - Plot style and HTML export settings dialog.
- `ui/folder_watcher.py` - Folder monitoring for auto-export.
- `Demo_data/` - Sample input and exported demo files.
- `config.json` - Saved runtime settings.

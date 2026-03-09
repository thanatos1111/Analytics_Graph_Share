# Analytics Graph Share

Desktop app to load xlsx time-series data, visualize with multi-Y-axis plots, and export interactive HTML for sharing.

## Data format (xlsx)

- **Row 1:** Header. Cell A1 = `ts` (timestamp); remaining columns = parameter names.
- **Row 2:** Units for each parameter (column A has no unit).
- **Row 3+:** Timestamps and parameter values. Parameter count can vary per file.

## Features

- **Multi-file load:** Load multiple xlsx files; each appears in the file list with a checkbox.
- **Tabs:** Only checked files get a plot tab. Switch plots by clicking the tab (file name).
- **Multi-Y plot:** One graph per file. X-axis = time. Y-axis is split into sections (grouped by unit). Sections alternate left/right Y-axis labels and rulers. Parameters with the same unit share one section.
- **Hover tooltip:** Hover over the plot to see a vertical cursor and an info box: original parameter name, full timestamp, and alias (unit): value.
- **Settings (Settings → Parameter aliases and plot style):**
  - **Aliases:** Set a short name per parameter; used on the Y-axis and in the tooltip (row 3).
  - **Plot style:** Data point markers on/off, line shape (linear, spline, step), marker symbol and size.
- **Export:** File → Export plot to HTML. Saves the **current tab’s** plot as a standalone HTML file that can be opened in any browser and shared.
- **Auto-export (folder monitor):** In the left panel, set a folder path and turn **Monitor folder** on. When a new `.xlsx` file is added to that folder, the app generates an HTML file next to it (same name, `.html`). You can turn monitoring on or off anytime; the folder and toggle state are saved in config.

## Run

**Option A — batch files (Windows)**  
1. Double‑click `setup_env.bat` once to install dependencies into your system Python.  
2. Double‑click `start_app.bat` to launch the app (or run it anytime after setup).

**Option B — manual**  
```bash
pip install -r requirements.txt
python main.py
```

1. Click **Load xlsx files...** (or File → Load xlsx) and select one or more files.
2. Use the checkboxes in the file list to choose which files get a plot tab.
3. Open **Settings** to set aliases and plot style.
4. Use **File → Export plot to HTML...** to save the current plot as a shareable HTML file.

## Project layout

- `main.py` — Entry point.
- `core/data_loader.py` — Read xlsx (header, units, data).
- `core/config.py` — Load/save app config (JSON): last data folder, plot style, aliases, export options.
- `core/plot_builder.py` — Build plot figure (sections, alternating Y-axes, hover).
- `core/plot_backends/` — Pluggable plot backends (Plotly, ECharts, D3, Observable Plot, uPlot).
- `ui/main_window.py` — Main window (file list, tabs, menu).
- `ui/plot_view.py` — Plot area (HTML in QWebEngineView) and export.
- `ui/settings_dialog.py` — Aliases and plot-style dialog.
- `Demo_data/` — Sample xlsx files.
- `config.json` — Saved settings (created on first run or when you change settings): last data folder, plot style, and parameter aliases. Loaded automatically when the app starts.

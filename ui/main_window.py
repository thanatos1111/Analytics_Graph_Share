"""
Main window: file list (left), tabbed plot view (right), settings, export, folder monitor.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.io as pio
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStyle,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.config import load_config, save_config
from core.data_loader import load_xlsx
from core.plot_builder import build_figure
from ui.folder_watcher import FolderWatcher
from ui.plot_view import PlotView, _EMBED_SCRIPT_PATH
from ui.settings_dialog import SettingsDialog


class FileItem(QListWidgetItem):
    """List item that holds path, data, param_units, and checkbox state."""

    def __init__(self, path: Path, data_df: pd.DataFrame, param_units: dict[str, str], parent=None):
        super().__init__(parent)
        self.path = path
        self.data_df = data_df
        self.param_units = param_units
        self.setData(Qt.ItemDataRole.UserRole, path)
        self.setText(path.name)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Analytics Graph Share")
        self.setMinimumSize(1000, 600)
        self.resize(1200, 700)

        # Load saved config
        cfg = load_config()
        self._last_data_folder: str = cfg.get("last_data_folder", "") or ""
        self._aliases: dict[str, str] = dict(cfg.get("aliases", {}))
        self._plot_style: dict = dict(cfg.get("plot_style", {
            "show_markers": False,
            "line_shape": "linear",
            "marker_symbol": "circle",
            "marker_size": 6,
        }))
        self._auto_export_folder: str = cfg.get("auto_export_folder", "") or ""
        self._auto_export_enabled: bool = cfg.get("auto_export_enabled", False)
        self._folder_watcher = FolderWatcher(self)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: file list + auto-export
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Data files"))
        self.load_btn = QPushButton("Load xlsx files...")
        self.load_btn.clicked.connect(self._on_load_files)
        left_layout.addWidget(self.load_btn)
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.file_list.itemChanged.connect(self._on_file_item_changed)
        left_layout.addWidget(self.file_list)

        # Auto-export (folder monitor)
        auto_group = QGroupBox("Auto-export (folder monitor)")
        auto_layout = QVBoxLayout(auto_group)
        folder_row = QHBoxLayout()
        self._auto_export_edit = QLineEdit()
        self._auto_export_edit.setPlaceholderText("Folder to watch...")
        self._auto_export_edit.setText(self._auto_export_folder)
        self._auto_export_edit.textChanged.connect(self._on_auto_export_folder_changed)
        folder_row.addWidget(self._auto_export_edit)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_auto_export_browse)
        folder_row.addWidget(browse_btn)
        auto_layout.addLayout(folder_row)
        self._auto_export_toggle = QCheckBox("Monitor folder (auto-export new xlsx)")
        self._auto_export_toggle.setChecked(self._auto_export_enabled)
        self._auto_export_toggle.stateChanged.connect(self._on_auto_export_toggle_changed)
        auto_layout.addWidget(self._auto_export_toggle)
        self._auto_export_status = QLabel("")
        self._auto_export_status.setWordWrap(True)
        self._auto_export_status.setStyleSheet("color: gray; font-size: 11px;")
        auto_layout.addWidget(self._auto_export_status)
        if not self._folder_watcher.is_available:
            self._auto_export_toggle.setEnabled(False)
            self._auto_export_status.setText("Install 'watchdog' to enable.")
        left_layout.addWidget(auto_group)

        splitter.addWidget(left)

        # Right: tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(False)
        splitter.addWidget(self.tabs)

        splitter.setSizes([250, 750])
        layout.addWidget(splitter)

        # Menu
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        load_act = QAction("Load xlsx...", self)
        load_act.triggered.connect(self._on_load_files)
        file_menu.addAction(load_act)
        export_act = QAction("Export plot to HTML...", self)
        export_act.triggered.connect(self._on_export_html)
        file_menu.addAction(export_act)
        file_menu.addSeparator()
        self._minimize_to_tray_act = QAction("Minimize to system tray", self)
        self._minimize_to_tray_act.triggered.connect(self._minimize_to_tray)
        file_menu.addAction(self._minimize_to_tray_act)
        quit_act = QAction("Quit", self)
        quit_act.triggered.connect(self.close)
        file_menu.addAction(quit_act)

        settings_menu = menubar.addMenu("&Settings")
        aliases_act = QAction("Parameter aliases and plot style...", self)
        aliases_act.triggered.connect(self._on_settings)
        settings_menu.addAction(aliases_act)

        self._folder_watcher.new_xlsx_added.connect(self._on_auto_export_new_file)
        self._setup_system_tray()
        self._sync_tabs()
        self._update_auto_export_ui()
        if self._auto_export_enabled and self._auto_export_folder:
            self._start_folder_watcher()

    def _setup_system_tray(self) -> None:
        self._tray_icon = None
        self._tray_monitor_act = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self._minimize_to_tray_act.setEnabled(False)
            return
        self._tray_icon = QSystemTrayIcon(self)
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self._tray_icon.setIcon(icon)
        self._tray_icon.setToolTip("Analytics Graph Share")
        self._tray_menu = QMenu()
        show_act = QAction("Show", self)
        show_act.triggered.connect(self._restore_from_tray)
        self._tray_menu.addAction(show_act)
        self._tray_menu.addSeparator()
        self._tray_monitor_act = QAction("Start monitoring", self)
        self._tray_monitor_act.triggered.connect(self._tray_toggle_monitoring)
        self._tray_menu.addAction(self._tray_monitor_act)
        self._tray_menu.addSeparator()
        exit_act = QAction("Exit", self)
        exit_act.triggered.connect(self.close)
        self._tray_menu.addAction(exit_act)
        self._tray_icon.setContextMenu(self._tray_menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()
        self._update_tray_menu_text()

    def _update_tray_menu_text(self) -> None:
        if getattr(self, "_tray_monitor_act", None) is not None:
            self._tray_monitor_act.setText("Stop monitoring" if self._auto_export_enabled else "Start monitoring")

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.DoubleClick, QSystemTrayIcon.ActivationReason.Trigger):
            self._restore_from_tray()

    def _restore_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _minimize_to_tray(self) -> None:
        self.hide()

    def _tray_toggle_monitoring(self) -> None:
        self._auto_export_toggle.setChecked(not self._auto_export_toggle.isChecked())

    def closeEvent(self, event):
        self._folder_watcher.stop()
        if getattr(self, "_tray_icon", None) is not None:
            self._tray_icon.hide()
        save_config(
            last_data_folder=self._last_data_folder,
            plot_style=self._plot_style,
            aliases=self._aliases,
            auto_export_folder=self._auto_export_folder,
            auto_export_enabled=self._auto_export_enabled,
        )
        super().closeEvent(event)

    def _get_loaded_files(self) -> list[tuple[Path, pd.DataFrame, dict[str, str]]]:
        """Return list of (path, data_df, param_units) from current list."""
        result = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if isinstance(item, FileItem):
                result.append((item.path, item.data_df, item.param_units))
        return result

    def _get_selected_for_plot(self) -> list[tuple[Path, pd.DataFrame, dict[str, str]]]:
        """Return only files that are selected (checked) for plotting."""
        result = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if isinstance(item, FileItem) and item.checkState() == Qt.CheckState.Checked:
                result.append((item.path, item.data_df, item.param_units))
        return result

    def _on_load_files(self):
        start_dir = self._last_data_folder or str(Path.home())
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select xlsx files",
            start_dir,
            "Excel (*.xlsx);;All files (*)",
        )
        if not paths:
            return
        # Remember folder for next time (use parent of first selected file)
        self._last_data_folder = str(Path(paths[0]).resolve().parent)
        save_config(last_data_folder=self._last_data_folder)

        # Block itemChanged during bulk add to avoid re-entrant sync and window flicker
        self.file_list.blockSignals(True)
        try:
            for path_str in paths:
                path = Path(path_str)
                try:
                    data_df, param_units = load_xlsx(path)
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        "Load error",
                        f"Could not load {path.name}:\n{e}",
                    )
                    continue
                item = FileItem(path, data_df, param_units)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                self.file_list.addItem(item)
        finally:
            self.file_list.blockSignals(False)
        self._sync_tabs()
        # Keep main window on top after dialog closes (fixes window disappearing)
        self.raise_()
        self.activateWindow()

    def _sync_tabs(self):
        """Create/remove tabs so that one tab exists per selected file."""
        selected = self._get_selected_for_plot()
        current_names = {self.tabs.tabText(i) for i in range(self.tabs.count())}
        target_names = {p.name for p, _, _ in selected}

        # Remove tabs for deselected files
        to_remove = []
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) not in target_names:
                to_remove.append(i)
        for i in reversed(to_remove):
            self.tabs.removeTab(i)

        # Add or refresh tabs for selected files
        for path, data_df, param_units in selected:
            name = path.name
            idx = next((i for i in range(self.tabs.count()) if self.tabs.tabText(i) == name), None)
            is_new_tab = idx is None
            if is_new_tab:
                view = PlotView(self)
                self.tabs.addTab(view, name)
                idx = self.tabs.count() - 1
            else:
                view = self.tabs.widget(idx)
            assert isinstance(view, PlotView)
            view.set_data(data_df, param_units)
            # Defer first paint for new tabs so the WebEngineView has valid size
            if is_new_tab:
                view.refresh_plot_deferred()
            else:
                view.refresh_plot()

        if self.tabs.count() == 0 and self.file_list.count() > 0:
            # Nothing selected
            pass

    def _on_settings(self):
        # Params from opened files + any from saved config (so user can edit/delete old aliases)
        all_params: dict[str, str] = {}
        for path, _, param_units in self._get_loaded_files():
            for p, u in param_units.items():
                if p not in all_params:
                    all_params[p] = u
        for p in self._aliases:
            if p not in all_params:
                all_params[p] = ""  # saved alias but no file loaded for this param
        param_names = sorted(all_params.keys())
        dlg = SettingsDialog(
            self._aliases.copy(),
            self._plot_style.copy(),
            param_names,
            self,
        )
        if dlg.exec():
            self._aliases = dlg.get_aliases()
            self._plot_style = dlg.get_plot_style()
            save_config(plot_style=self._plot_style, aliases=self._aliases)
            for i in range(self.tabs.count()):
                view = self.tabs.widget(i)
                if isinstance(view, PlotView):
                    view.refresh_plot()

    def _on_export_html(self):
        if self.tabs.count() == 0:
            QMessageBox.information(self, "Export", "No plot to export. Load and select at least one file.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export plot as HTML",
            str(Path.home()),
            "HTML (*.html);;All files (*)",
        )
        if not path:
            return
        view = self.tabs.currentWidget()
        if isinstance(view, PlotView):
            view.export_html(path)

    def get_aliases(self) -> dict[str, str]:
        return self._aliases

    def get_plot_style(self) -> dict:
        return self._plot_style

    def _on_file_item_changed(self):
        """Called when checkbox of a file item is toggled."""
        self._sync_tabs()

    def _on_auto_export_folder_changed(self):
        self._auto_export_folder = self._auto_export_edit.text().strip()
        save_config(auto_export_folder=self._auto_export_folder)
        if not self._auto_export_folder:
            self._folder_watcher.stop()
        elif self._auto_export_enabled:
            self._start_folder_watcher()
        self._update_auto_export_ui()

    def _on_auto_export_browse(self):
        start = self._auto_export_folder or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Select folder to monitor", start)
        if folder:
            self._auto_export_edit.setText(folder)
            self._auto_export_folder = folder
            save_config(auto_export_folder=self._auto_export_folder)
            if self._auto_export_enabled:
                self._start_folder_watcher()
            self._update_auto_export_ui()

    def _on_auto_export_toggle_changed(self, state):
        self._auto_export_enabled = state == Qt.CheckState.Checked.value
        save_config(auto_export_enabled=self._auto_export_enabled)
        if self._auto_export_enabled:
            self._start_folder_watcher()
        else:
            self._folder_watcher.stop()
        self._update_auto_export_ui()
        self._update_tray_menu_text()

    def _update_auto_export_ui(self):
        if not self._folder_watcher.is_available:
            return
        if self._folder_watcher.is_watching:
            self._auto_export_status.setText("Watching for new .xlsx files...")
        else:
            self._auto_export_status.setText("Stopped." if self._auto_export_folder else "Set folder and turn on.")
        self._update_tray_menu_text()

    def _start_folder_watcher(self):
        if not self._folder_watcher.is_available or not self._auto_export_folder:
            self._folder_watcher.stop()
            return
        path = Path(self._auto_export_folder)
        if not path.is_dir():
            self._auto_export_status.setText("Folder not found.")
            return
        if self._folder_watcher.start(self._auto_export_folder):
            self._auto_export_status.setText("Watching for new .xlsx files...")
        else:
            self._auto_export_status.setText("Could not start watcher.")

    def _on_auto_export_new_file(self, xlsx_path: str):
        """Load the new xlsx, build figure, export HTML next to it (same stem, .html). Delay slightly so file is fully written."""
        path = Path(xlsx_path)
        if path.suffix.lower() != ".xlsx":
            return
        QTimer.singleShot(800, lambda: self._do_auto_export(str(path)))

    def _do_auto_export(self, xlsx_path: str):
        path = Path(xlsx_path)
        if not path.exists():
            return
        try:
            data_df, param_units = load_xlsx(path)
        except Exception as e:
            self._auto_export_status.setText(f"Auto-export failed: {path.name}")
            QMessageBox.warning(
                self,
                "Auto-export",
                f"Could not load {path.name}:\n{e}",
            )
            return
        out_path = path.with_suffix(".html")
        try:
            fig = build_figure(
                data_df,
                param_units,
                aliases=self._aliases,
                show_markers=self._plot_style.get("show_markers", False),
                line_shape=self._plot_style.get("line_shape", "linear"),
                marker_symbol=self._plot_style.get("marker_symbol", "circle"),
                marker_size=int(self._plot_style.get("marker_size", 6)),
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
            out_path.write_text(html, encoding="utf-8")
            self._auto_export_status.setText(f"Exported: {out_path.name}")
        except Exception as e:
            self._auto_export_status.setText(f"Auto-export failed: {path.name}")
            QMessageBox.warning(
                self,
                "Auto-export",
                f"Could not export {path.name} to HTML:\n{e}",
            )


# Ensure FileItem has checkState/setCheckState (from QListWidgetItem)
# QListWidgetItem supports ItemIsUserCheckable and setCheckState natively

"""
Settings dialog: plot style (markers, line shape, etc.) and export options.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)


class SettingsDialog(QDialog):
    def __init__(
        self,
        plot_style: dict,
        export_inline_d3: bool,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Settings - plot style, export")
        self.resize(500, 340)

        self._plot_style = dict(plot_style)
        self._export_inline_d3 = export_inline_d3

        layout = QVBoxLayout(self)

        # Plot style group
        style_group = QGroupBox("Plot style")
        style_layout = QFormLayout(style_group)
        self._show_markers = QCheckBox("Show data point markers")
        self._show_markers.setChecked(self._plot_style.get("show_markers", False))
        style_layout.addRow(self._show_markers)
        self._line_shape = QComboBox()
        self._line_shape.addItems(["linear", "spline", "hv", "vh", "hvh", "vhv"])
        self._line_shape.setCurrentText(self._plot_style.get("line_shape", "linear"))
        style_layout.addRow("Line shape:", self._line_shape)
        self._marker_symbol = QComboBox()
        self._marker_symbol.addItems([
            "circle", "square", "diamond", "cross", "x", "triangle-up", "triangle-down", "pentagon", "hexagon"
        ])
        self._marker_symbol.setCurrentText(self._plot_style.get("marker_symbol", "circle"))
        style_layout.addRow("Marker symbol:", self._marker_symbol)
        self._marker_size = QSpinBox()
        self._marker_size.setRange(2, 24)
        self._marker_size.setValue(int(self._plot_style.get("marker_size", 6)))
        style_layout.addRow("Marker size:", self._marker_size)
        layout.addWidget(style_group)

        export_group = QGroupBox("HTML export")
        export_layout = QVBoxLayout(export_group)
        self._export_inline_d3_checkbox = QCheckBox(
            "Embed D3 library in exported HTML for standalone viewing"
        )
        self._export_inline_d3_checkbox.setChecked(self._export_inline_d3)
        export_layout.addWidget(self._export_inline_d3_checkbox)
        export_hint = QLabel(
            "When enabled, exported HTML can open without CDN access."
        )
        export_hint.setWordWrap(True)
        export_layout.addWidget(export_hint)
        layout.addWidget(export_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_plot_style(self) -> dict:
        return {
            "show_markers": self._show_markers.isChecked(),
            "line_shape": self._line_shape.currentText(),
            "marker_symbol": self._marker_symbol.currentText(),
            "marker_size": self._marker_size.value(),
        }

    def get_export_inline_d3(self) -> bool:
        return self._export_inline_d3_checkbox.isChecked()

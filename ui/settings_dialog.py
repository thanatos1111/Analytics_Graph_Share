"""
Settings dialog: parameter aliases and plot style (markers, line shape, etc.).
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class SettingsDialog(QDialog):
    def __init__(
        self,
        aliases: dict[str, str],
        plot_style: dict,
        param_names: list[str],
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Settings — Aliases & plot style")
        self.resize(500, 500)

        self._aliases = dict(aliases)
        self._plot_style = dict(plot_style)
        self._param_names = param_names
        self._alias_edits: dict[str, QLineEdit] = {}

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

        # Aliases group
        alias_group = QGroupBox("Parameter aliases (short names for Y-axis and tooltip)")
        alias_hint = QLabel("Clear the alias and click OK to remove it from saved settings.")
        alias_hint.setWordWrap(True)
        alias_group_layout_top = QVBoxLayout()
        alias_group_layout_top.addWidget(alias_hint)
        alias_inner = QWidget()
        alias_layout = QFormLayout(alias_inner)
        for name in self._param_names:
            edit = QLineEdit()
            edit.setPlaceholderText(name)
            edit.setText(self._aliases.get(name, ""))
            alias_layout.addRow(QLabel(name[:50] + ("..." if len(name) > 50 else "") + ":"), edit)
            self._alias_edits[name] = edit
        scroll = QScrollArea()
        scroll.setWidget(alias_inner)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        alias_group_layout = QVBoxLayout(alias_group)
        alias_group_layout.addLayout(alias_group_layout_top)
        alias_group_layout.addWidget(scroll)
        layout.addWidget(alias_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_aliases(self) -> dict[str, str]:
        result = {}
        for name, edit in self._alias_edits.items():
            val = edit.text().strip()
            if val:
                result[name] = val
        return result

    def get_plot_style(self) -> dict:
        return {
            "show_markers": self._show_markers.isChecked(),
            "line_shape": self._line_shape.currentText(),
            "marker_symbol": self._marker_symbol.currentText(),
            "marker_size": self._marker_size.value(),
        }

"""
PySide6 GUI for the Exhaust Transmission Loss Calculator.
"""

from __future__ import annotations

import csv
import io
import math
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from exhaust_calc_gui.engine import (
    ExhaustParams,
    TLResult,
    compute_harmonics,
    compute_sweep,
)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Exhaust Transmission Loss Calculator")
        self.setMinimumSize(900, 650)
        self._results: List[TLResult] = []
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # Left panel: inputs + controls
        left = QWidget()
        left.setMaximumWidth(320)
        left_layout = QVBoxLayout(left)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        left_layout.addWidget(self._build_params_group())
        left_layout.addWidget(self._build_freq_group())
        left_layout.addWidget(self._build_buttons())
        splitter.addWidget(left)

        # Right panel: table + plot
        right = QWidget()
        right_layout = QVBoxLayout(right)
        self._table = self._build_table()
        right_layout.addWidget(self._table, stretch=1)
        self._canvas = self._build_plot()
        right_layout.addWidget(self._canvas, stretch=2)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

    def _build_params_group(self) -> QGroupBox:
        grp = QGroupBox("System Parameters")
        layout = QVBoxLayout(grp)

        def row(label: str, widget: QWidget) -> None:
            h = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setMinimumWidth(170)
            h.addWidget(lbl)
            h.addWidget(widget)
            layout.addLayout(h)

        self._inlet_diam = QDoubleSpinBox()
        self._inlet_diam.setRange(0.001, 10.0)
        self._inlet_diam.setDecimals(4)
        self._inlet_diam.setSingleStep(0.01)
        self._inlet_diam.setValue(0.06)
        self._inlet_diam.setSuffix(" m")
        row("Inlet pipe diameter:", self._inlet_diam)

        self._exhaust_diam = QDoubleSpinBox()
        self._exhaust_diam.setRange(0.001, 10.0)
        self._exhaust_diam.setDecimals(4)
        self._exhaust_diam.setSingleStep(0.01)
        self._exhaust_diam.setValue(0.48)
        self._exhaust_diam.setSuffix(" m")
        row("Exhaust (chamber) diameter:", self._exhaust_diam)

        self._exhaust_len = QDoubleSpinBox()
        self._exhaust_len.setRange(0.001, 100.0)
        self._exhaust_len.setDecimals(4)
        self._exhaust_len.setSingleStep(0.1)
        self._exhaust_len.setValue(0.4)
        self._exhaust_len.setSuffix(" m")
        row("Exhaust chamber length:", self._exhaust_len)

        self._temp = QDoubleSpinBox()
        self._temp.setRange(-50.0, 2000.0)
        self._temp.setDecimals(1)
        self._temp.setSingleStep(10.0)
        self._temp.setValue(450.0)
        self._temp.setSuffix(" °C")
        row("Exhaust fluid temperature:", self._temp)

        self._cylinders = QSpinBox()
        self._cylinders.setRange(1, 32)
        self._cylinders.setValue(6)
        row("Number of cylinders:", self._cylinders)

        return grp

    def _build_freq_group(self) -> QGroupBox:
        grp = QGroupBox("Frequency Input")
        layout = QVBoxLayout(grp)

        # Mode selector
        self._mode_single = QRadioButton("Single base frequency (harmonics view)")
        self._mode_sweep = QRadioButton("Frequency sweep")
        self._mode_single.setChecked(True)
        layout.addWidget(self._mode_single)
        layout.addWidget(self._mode_sweep)

        # Single frequency
        self._single_group = QGroupBox("Base frequency")
        sg = QHBoxLayout(self._single_group)
        self._single_freq = QDoubleSpinBox()
        self._single_freq.setRange(0.1, 20000.0)
        self._single_freq.setDecimals(1)
        self._single_freq.setSingleStep(10.0)
        self._single_freq.setValue(50.0)
        self._single_freq.setSuffix(" Hz")
        sg.addWidget(QLabel("Frequency:"))
        sg.addWidget(self._single_freq)
        layout.addWidget(self._single_group)

        # Sweep
        self._sweep_group = QGroupBox("Sweep parameters")
        swg = QVBoxLayout(self._sweep_group)

        def srow(label: str, widget: QWidget) -> None:
            h = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setMinimumWidth(55)
            h.addWidget(lbl)
            h.addWidget(widget)
            swg.addLayout(h)

        self._sweep_start = QDoubleSpinBox()
        self._sweep_start.setRange(0.1, 20000.0)
        self._sweep_start.setDecimals(1)
        self._sweep_start.setValue(100.0)
        self._sweep_start.setSuffix(" Hz")
        srow("Start:", self._sweep_start)

        self._sweep_stop = QDoubleSpinBox()
        self._sweep_stop.setRange(0.1, 20000.0)
        self._sweep_stop.setDecimals(1)
        self._sweep_stop.setValue(2000.0)
        self._sweep_stop.setSuffix(" Hz")
        srow("Stop:", self._sweep_stop)

        self._sweep_step = QDoubleSpinBox()
        self._sweep_step.setRange(0.1, 1000.0)
        self._sweep_step.setDecimals(1)
        self._sweep_step.setValue(10.0)
        self._sweep_step.setSuffix(" Hz")
        srow("Step:", self._sweep_step)

        layout.addWidget(self._sweep_group)

        # Toggle visibility on mode change
        self._mode_single.toggled.connect(self._on_mode_changed)
        self._sweep_group.setEnabled(False)

        return grp

    def _build_buttons(self) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        calc_btn = QPushButton("Calculate")
        calc_btn.clicked.connect(self._on_calculate)
        export_btn = QPushButton("Export CSV…")
        export_btn.clicked.connect(self._on_export_csv)
        h.addWidget(calc_btn)
        h.addWidget(export_btn)
        return w

    def _build_table(self) -> QTableWidget:
        tbl = QTableWidget(0, 2)
        tbl.setHorizontalHeaderLabels(["Frequency (Hz)", "Transmission Loss (dB)"])
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        return tbl

    def _build_plot(self) -> FigureCanvas:
        fig = Figure(figsize=(6, 3), tight_layout=True)
        self._ax = fig.add_subplot(111)
        self._ax.set_xlabel("Frequency (Hz)")
        self._ax.set_ylabel("Transmission Loss (dB)")
        self._ax.set_title("Exhaust Attenuation")
        self._ax.grid(True)
        canvas = FigureCanvas(fig)
        return canvas

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_mode_changed(self, single_checked: bool) -> None:
        self._single_group.setEnabled(single_checked)
        self._sweep_group.setEnabled(not single_checked)

    def _on_calculate(self) -> None:
        try:
            params = self._collect_params()
        except ValueError as exc:
            QMessageBox.warning(self, "Input Error", str(exc))
            return

        try:
            if self._mode_single.isChecked():
                base = self._single_freq.value()
                results = compute_harmonics(base, params)
            else:
                start = self._sweep_start.value()
                stop = self._sweep_stop.value()
                step = self._sweep_step.value()
                results = compute_sweep(start, stop, step, params)
        except Exception as exc:
            QMessageBox.critical(self, "Calculation Error", str(exc))
            return

        self._results = results
        self._populate_table(results)
        self._update_plot(results)

    def _on_export_csv(self) -> None:
        if not self._results:
            QMessageBox.information(self, "No Data", "Run a calculation first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", "", "CSV files (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["Frequency (Hz)", "Transmission Loss (dB)"])
                for r in self._results:
                    writer.writerow([r.frequency, f"{r.tl_db:.6f}"])
            QMessageBox.information(self, "Saved", f"Results saved to:\n{path}")
        except OSError as exc:
            QMessageBox.critical(self, "Save Error", str(exc))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _collect_params(self) -> ExhaustParams:
        inlet = self._inlet_diam.value()
        exhaust = self._exhaust_diam.value()
        if exhaust <= inlet:
            raise ValueError(
                "Exhaust chamber diameter must be larger than inlet pipe diameter."
            )
        return ExhaustParams(
            inlet_diameter=inlet,
            exhaust_diameter=exhaust,
            exhaust_length=self._exhaust_len.value(),
            temperature=self._temp.value(),
            num_cylinders=self._cylinders.value(),
        )

    def _populate_table(self, results: List[TLResult]) -> None:
        self._table.setRowCount(len(results))
        for row, r in enumerate(results):
            self._table.setItem(row, 0, QTableWidgetItem(f"{r.frequency:.1f}"))
            item = QTableWidgetItem(f"{r.tl_db:.4f}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 1, item)
        self._table.resizeColumnsToContents()

    def _update_plot(self, results: List[TLResult]) -> None:
        freqs = [r.frequency for r in results]
        tls = [r.tl_db for r in results]
        self._ax.cla()
        MAX_POINTS_WITH_MARKERS = 20
        self._ax.plot(freqs, tls, marker="o" if len(freqs) <= MAX_POINTS_WITH_MARKERS else None, linewidth=1.5)
        self._ax.set_xlabel("Frequency (Hz)")
        self._ax.set_ylabel("Transmission Loss (dB)")
        self._ax.set_title("Exhaust Attenuation")
        self._ax.grid(True)
        self._canvas.draw()


def run_app() -> None:
    """Launch the Qt application."""
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

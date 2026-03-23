"""
app_window.py — Main QMainWindow.
Hosts the tab widget, wires simulator → dashboard, control panel → simulator.
"""
import sys


from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QStatusBar, QLabel, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

sys.path.append("/Users/nguyenthanhvinh/Documents/PYTHON/Project/RL/sensor")

from sensor.sensor_simulator import SensorSimulator
from dashboard import DashboardTab
from controller import ControlPanelTab





class RoverApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IoT Rover — Monitor & Control")
        self.setMinimumSize(960, 660)
        self.resize(1100, 720)

        self._build_ui()
        self._start_simulator()

    def _build_ui(self):
        # ── tab widget ──
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #2e3040;
                border-radius: 8px;
                background: #1a1c24;
            }
            QTabBar::tab {
                background: #1e2028;
                color: #777;
                border: 1px solid #2e3040;
                border-bottom: none;
                padding: 8px 24px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 10pt;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #1a1c24;
                color: #2a82da;
                border-bottom: 2px solid #2a82da;
            }
            QTabBar::tab:hover:!selected { background: #252730; color: #aaa; }
        """)

        self._dashboard = DashboardTab()
        self._control   = ControlPanelTab()

        self._tabs.addTab(self._dashboard, "  Dashboard  ")
        self._tabs.addTab(self._control,   "  Control Panel  ")
        self.setCentralWidget(self._tabs)

        # ── status bar ──
        sb = QStatusBar()
        sb.setStyleSheet("background:#161820; color:#555; font-size:9pt; border-top:1px solid #2e3040;")
        self._sb_sim   = QLabel("Simulator: running")
        self._sb_sim.setStyleSheet("color:#27ae60; padding: 0 10px;")
        self._sb_tick  = QLabel("Tick: 0")
        self._sb_tick.setStyleSheet("color:#555; padding: 0 10px;")
        sb.addWidget(self._sb_sim)
        sb.addWidget(self._sb_tick)
        sb.addPermanentWidget(QLabel("No hardware required — simulated data  "))
        self.setStatusBar(sb)

    def _start_simulator(self):
        self._sim = SensorSimulator(interval_ms=1000)

        # Simulator → dashboard
        self._sim.data_ready.connect(self._dashboard.update_data)
        self._sim.data_ready.connect(self._on_tick)

        # Control panel → simulator
        self._control.command_sent.connect(self._sim.send_command)

        self._sim.start()

    def _on_tick(self, payload: dict):
        self._sb_tick.setText(f"Tick: {payload['tick']}")

    def closeEvent(self, event):
        self._sim.stop()
        event.accept()
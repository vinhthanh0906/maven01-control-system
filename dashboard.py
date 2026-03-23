"""
dashboard.py — Live sensor dashboard tab.
Shows scrolling line charts for Temperature, Humidity, CO₂, AQI and
a status bar with Battery, Speed, Direction.
"""

from collections import deque
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGridLayout, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import pyqtgraph as pg


MAX_POINTS = 60   # seconds of history shown


# ── helpers ──────────────────────────────────────────────────────────────────

def make_chart(title: str, unit: str, color: str, y_range=None) -> tuple:
    """Return (PlotWidget, curve) ready to embed."""
    plot = pg.PlotWidget()
    plot.setBackground("#161820")
    plot.setTitle(f"<span style='color:#aaa;font-size:11pt'>{title}</span>", color="#aaa")
    plot.showGrid(x=False, y=True, alpha=0.15)
    plot.getAxis("left").setLabel(unit, color="#888")
    plot.getAxis("left").setTextPen("#888")
    plot.getAxis("bottom").setTextPen("#888")
    plot.getAxis("bottom").setLabel("seconds ago", color="#888")
    if y_range:
        plot.setYRange(*y_range, padding=0.05)
    plot.setMouseEnabled(x=False, y=False)
    curve = plot.plot(pen=pg.mkPen(color=color, width=2))
    plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    return plot, curve


def status_card(label: str, value: str, unit: str = "", color: str = "#2a82da") -> tuple[QFrame, QLabel]:
    """Return (card frame, value label) for the status bar."""
    card = QFrame()
    card.setStyleSheet(f"""
        QFrame {{
            background: #1e2028;
            border: 1px solid #2e3040;
            border-radius: 8px;
            padding: 6px;
        }}
    """)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 8, 12, 8)
    layout.setSpacing(2)

    lbl = QLabel(label.upper())
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet("color:#666; font-size:9pt; letter-spacing:1px;")

    val = QLabel(f"{value} {unit}")
    val.setAlignment(Qt.AlignCenter)
    val.setStyleSheet(f"color:{color}; font-size:18pt; font-weight:600;")

    layout.addWidget(lbl)
    layout.addWidget(val)
    return card, val


# ── main widget ───────────────────────────────────────────────────────────────

class DashboardTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Data buffers (deque auto-drops oldest when maxlen reached)
        self._bufs = {k: deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS)
                      for k in ("temperature", "humidity", "co2", "aqi")}
        self._x = list(range(-MAX_POINTS + 1, 1))  # -59 … 0

        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ── status bar ──
        status_row = QHBoxLayout()
        status_row.setSpacing(10)

        self._sb_bat_card,  self._sb_bat   = status_card("Battery",   "100",  "%",    "#27ae60")
        self._sb_speed_card,self._sb_speed = status_card("Speed",     "0",    "cm/s", "#2a82da")
        self._sb_dir_card,  self._sb_dir   = status_card("Direction", "STOP", "",     "#e67e22")
        self._sb_temp_card, self._sb_temp  = status_card("Temp",      "—",    "°C",   "#e74c3c")
        self._sb_hum_card,  self._sb_hum   = status_card("Humidity",  "—",    "%",    "#3498db")

        for card in (self._sb_bat_card, self._sb_speed_card, self._sb_dir_card,
                     self._sb_temp_card, self._sb_hum_card):
            status_row.addWidget(card)

        root.addLayout(status_row)

        # ── charts grid ──
        grid = QGridLayout()
        grid.setSpacing(10)

        self._plot_temp, self._curve_temp = make_chart("Temperature", "°C",  "#e74c3c", (15, 45))
        self._plot_hum,  self._curve_hum  = make_chart("Humidity",    "%",   "#3498db", (30, 90))
        self._plot_co2,  self._curve_co2  = make_chart("CO₂",         "ppm", "#2ecc71", (350, 700))
        self._plot_aqi,  self._curve_aqi  = make_chart("Air Quality Index", "AQI", "#f39c12", (0, 200))

        grid.addWidget(self._plot_temp, 0, 0)
        grid.addWidget(self._plot_hum,  0, 1)
        grid.addWidget(self._plot_co2,  1, 0)
        grid.addWidget(self._plot_aqi,  1, 1)

        root.addLayout(grid)

    def update_data(self, payload: dict):
        """Called each tick with new sensor dict."""
        # Update buffers
        for key in self._bufs:
            self._bufs[key].append(payload.get(key, 0))

        # Redraw curves
        self._curve_temp.setData(self._x, list(self._bufs["temperature"]))
        self._curve_hum .setData(self._x, list(self._bufs["humidity"]))
        self._curve_co2 .setData(self._x, list(self._bufs["co2"]))
        self._curve_aqi .setData(self._x, list(self._bufs["aqi"]))

        # Update status cards
        bat = payload.get("battery", 0)
        bat_color = "#27ae60" if bat > 50 else "#e67e22" if bat > 20 else "#e74c3c"
        self._sb_bat.setText(f"{bat:.0f} %")
        self._sb_bat.setStyleSheet(f"color:{bat_color}; font-size:18pt; font-weight:600;")

        self._sb_speed.setText(f"{payload.get('speed', 0)} cm/s")
        self._sb_dir  .setText(payload.get("direction", "stop").upper())
        self._sb_temp .setText(f"{payload.get('temperature', 0):.1f} °C")
        self._sb_hum  .setText(f"{payload.get('humidity', 0):.1f} %")
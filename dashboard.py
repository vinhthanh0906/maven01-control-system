"""
dashboard.py — Live sensor dashboard (PyQt6)
Shows real DHT11 temperature + humidity from ESP32 via UDP,
plus motor status cards.
"""

from collections import deque
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QGridLayout, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt
import pyqtgraph as pg

MAX_POINTS = 60


def make_chart(title, unit, color, y_range=None):
    plot = pg.PlotWidget()
    plot.setBackground("#161820")
    plot.setTitle(f"<span style='color:#aaa;font-size:11pt'>{title}</span>")
    plot.showGrid(x=False, y=True, alpha=0.15)
    plot.getAxis("left").setLabel(unit, color="#888")
    plot.getAxis("left").setTextPen("#888")
    plot.getAxis("bottom").setTextPen("#888")
    plot.getAxis("bottom").setLabel("seconds ago", color="#888")
    if y_range:
        plot.setYRange(*y_range, padding=0.05)
    plot.setMouseEnabled(x=False, y=False)
    curve = plot.plot(pen=pg.mkPen(color=color, width=2))
    plot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    return plot, curve




def status_card(label, value, unit="", color="#2a82da"):
    card = QFrame()
    card.setStyleSheet(
        "QFrame { background:#1e2028; border:1px solid #2e3040; border-radius:8px; }")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 8, 12, 8)
    layout.setSpacing(2)

    lbl = QLabel(label.upper())
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet("color:#666; font-size:9pt; letter-spacing:1px;")

    val = QLabel(f"{value} {unit}".strip())
    val.setAlignment(Qt.AlignmentFlag.AlignCenter)
    val.setStyleSheet(f"color:{color}; font-size:18pt; font-weight:600;")

    layout.addWidget(lbl)
    layout.addWidget(val)
    return card, val


class DashboardTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._bufs = {
            "temperature": deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS),
            "humidity":    deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS),
        }
        self._x = list(range(-MAX_POINTS + 1, 1))
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ── status cards ──
        status_row = QHBoxLayout()
        status_row.setSpacing(10)

        self._c_temp,   self._v_temp   = status_card("Temperature", "—",    "°C",   "#e74c3c")
        self._c_hum,    self._v_hum    = status_card("Humidity",    "—",    "%",    "#3498db")
        self._c_cmd,    self._v_cmd    = status_card("Command",     "STOP", "",     "#e67e22")
        self._c_uptime, self._v_uptime = status_card("Uptime",      "0",    "s",    "#9b59b6")
        self._c_sensor, self._v_sensor = status_card("Sensor",      "—",    "",     "#27ae60")

        for card in (self._c_temp, self._c_hum, self._c_cmd,
                     self._c_uptime, self._c_sensor):
            status_row.addWidget(card)
        root.addLayout(status_row)

        # ── charts ──
        grid = QGridLayout()
        grid.setSpacing(10)

        self._plot_temp, self._curve_temp = make_chart(
            "Temperature (DHT11)", "°C", "#e74c3c", (0, 50))
        self._plot_hum,  self._curve_hum  = make_chart(
            "Humidity (DHT11)", "%", "#3498db", (0, 100))

        grid.addWidget(self._plot_temp, 0, 0)
        grid.addWidget(self._plot_hum,  0, 1)
        root.addLayout(grid)

        # ── raw payload display ──
        self._raw = QLabel("Waiting for data from ESP32...")
        self._raw.setStyleSheet(
            "background:#161820; color:#555; border:1px solid #2e3040;"
            "border-radius:6px; padding:6px 10px; font-family:monospace; font-size:9pt;")
        self._raw.setFixedHeight(36)
        root.addWidget(self._raw)

    def update_data(self, payload: dict):
        temp = payload.get("temperature", 0)
        hum  = payload.get("humidity",    0)
        cmd  = payload.get("cmd",         "stop")
        up   = payload.get("uptime",      0)
        ok   = payload.get("sensor_ok",   True)

        # Update buffers
        self._bufs["temperature"].append(temp)
        self._bufs["humidity"]   .append(hum)

        # Redraw charts
        self._curve_temp.setData(self._x, list(self._bufs["temperature"]))
        self._curve_hum .setData(self._x, list(self._bufs["humidity"]))

        # Update cards
        self._v_temp.setText(f"{temp:.1f} °C")
        temp_color = "#2ecc71" if 15 < temp < 35 else "#e74c3c"
        self._v_temp.setStyleSheet(f"color:{temp_color}; font-size:18pt; font-weight:600;")

        self._v_hum.setText(f"{hum:.1f} %")
        self._v_cmd.setText(cmd.upper())

        colors = {"forward":"#2ecc71","backward":"#e74c3c",
                  "left":"#3498db","right":"#f39c12","stop":"#888"}
        self._v_cmd.setStyleSheet(
            f"color:{colors.get(cmd,'#aaa')}; font-size:18pt; font-weight:600;")

        self._v_uptime.setText(f"{up} s")

        if ok:
            self._v_sensor.setText("OK")
            self._v_sensor.setStyleSheet("color:#27ae60; font-size:18pt; font-weight:600;")
        else:
            self._v_sensor.setText("ERROR")
            self._v_sensor.setStyleSheet("color:#e74c3c; font-size:18pt; font-weight:600;")

        # Raw payload
        self._raw.setText(
            f"temp={temp}°C  hum={hum}%  cmd={cmd}  uptime={up}s  "
            f"tick={payload.get('tick','—')}  sensor={'ok' if ok else 'ERR'}")
        


  
    
#place holder for like: battery-level, voltage-level, temperature
class LevelDashboard:
    pass



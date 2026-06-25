"""
merge_monitor.py — PyQt6 main window, single-tab (Dashboard + Controller fused).

The controller (D-pad, IP bar, speed selector, rover reply) now lives inside
DashboardTab via RoverCADWidget.  merge_monitor just wires UDP ↔ dashboard.
"""
from PyQt6.QtWidgets import QMainWindow, QStatusBar, QLabel
from PyQt6.QtCore import Qt

from tab.control_dash_2 import DashboardTab
from connection.client_udp import UdpClient


ESP32_IP = "192.168.4.1"   # default — user overrides in the IP field
UDP_SEND = 4210
UDP_RECV = 4211


class RoverApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IoT Rover — UDP Control")
        self.setMinimumSize(960, 660)
        self.resize(1100, 720)
        self._build_ui()
        self._start_udp()

    def _build_ui(self):
        self._dashboard = DashboardTab()
        self.setCentralWidget(self._dashboard)

        sb = QStatusBar()
        sb.setStyleSheet(
            "background:#161820; color:#555; font-size:9pt; border-top:1px solid #2e3040;")
        self._sb_proto  = QLabel("Protocol: UDP")
        self._sb_esp    = QLabel(f"ESP32: {ESP32_IP}:{UDP_SEND}")
        self._sb_status = QLabel("Status: waiting")
        for w in (self._sb_proto, self._sb_esp, self._sb_status):
            w.setStyleSheet("padding:0 10px;")
        sb.addWidget(self._sb_proto)
        sb.addWidget(self._sb_esp)
        sb.addWidget(self._sb_status)
        self.setStatusBar(sb)

    def _start_udp(self):
        self._udp = UdpClient(
            esp32_ip=ESP32_IP,
            esp32_port=UDP_SEND,
            listen_port=UDP_RECV,
        )

        # Rover status → dashboard (update_data + rover reply box)
        self._udp.status_received.connect(self._dashboard.on_rover_status)

        # Connection state → dashboard connection badge
        self._udp.connection_changed.connect(self._dashboard.on_connection_changed)
        self._udp.connection_changed.connect(self._on_connection)

        # Controller commands (D-pad / keyboard) → UDP send or IP update
        self._dashboard.command_sent.connect(self._on_command)

        self._udp.start()

    def _on_command(self, direction: str, speed: int):
        if direction.startswith("__ip__"):
            new_ip = direction[6:]
            self._udp.update_esp_ip(new_ip)
            self._sb_esp.setText(f"ESP32: {new_ip}:{UDP_SEND}")
        else:
            self._udp.send_command(direction, speed)

    def _on_connection(self, connected: bool):
        if connected:
            self._sb_status.setText("Status: connected")
            self._sb_status.setStyleSheet("color:#27ae60; padding:0 10px;")
        else:
            self._sb_status.setText("Status: waiting for ESP32")
            self._sb_status.setStyleSheet("color:#e74c3c; padding:0 10px;")

    def closeEvent(self, event):
        self._udp.stop()
        event.accept()
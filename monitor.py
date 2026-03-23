"""
app_window.py — PyQt6 main window, wires UDP client to control panel.
"""
from PyQt6.QtWidgets import QMainWindow, QTabWidget, QStatusBar, QLabel
from PyQt6.QtCore import Qt

from dashboard import DashboardTab
from controller import ControlPanelTab
from connection.client_udp import UdpClient

ESP32_IP    = "192.168.1.5"   # default — user overrides in the IP field
UDP_SEND    = 4210
UDP_RECV    = 4211


class RoverApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IoT Rover — UDP Control")
        self.setMinimumSize(960, 660)
        self.resize(1100, 720)
        self._build_ui()
        self._start_udp()

    def _build_ui(self):
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane { border:1px solid #2e3040; border-radius:8px; background:#1a1c24; }
            QTabBar::tab { background:#1e2028; color:#777; border:1px solid #2e3040;
                           border-bottom:none; padding:8px 24px;
                           border-top-left-radius:6px; border-top-right-radius:6px;
                           font-size:10pt; margin-right:2px; }
            QTabBar::tab:selected { background:#1a1c24; color:#2a82da; border-bottom:2px solid #2a82da; }
            QTabBar::tab:hover:!selected { background:#252730; color:#aaa; }
        """)
        self._dashboard = DashboardTab()
        self._control   = ControlPanelTab()
        self._tabs.addTab(self._dashboard, "  Dashboard  ")
        self._tabs.addTab(self._control,   "  Control Panel  ")
        self.setCentralWidget(self._tabs)

        sb = QStatusBar()
        sb.setStyleSheet("background:#161820; color:#555; font-size:9pt; border-top:1px solid #2e3040;")
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
        self._udp = UdpClient(esp32_ip=ESP32_IP,
                              esp32_port=UDP_SEND,
                              listen_port=UDP_RECV)
        # Rover status → dashboard + control panel
        self._udp.status_received  .connect(self._dashboard.update_data)
        self._udp.status_received  .connect(self._control.on_rover_status)
        self._udp.connection_changed.connect(self._control.on_connection_changed)
        self._udp.connection_changed.connect(self._on_connection)

        # Control panel → UDP send (or IP change)
        self._control.command_sent.connect(self._on_command)

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
"""
app_window.py — PyQt6 main window, wires UDP client to dashboard.
"""
from PyQt6.QtWidgets import QMainWindow, QStatusBar, QLabel
from PyQt6.QtCore import Qt

from new_dashboard_2 import DashboardTab
from connection.client_udp import UdpClient

ESP32_IP    = "192.168.4.1"   # default — user overrides in the IP field
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
        self._dashboard = DashboardTab()
        self.setCentralWidget(self._dashboard)

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
        # Rover status → dashboard
        self._udp.status_received  .connect(self._dashboard.update_data)
        self._udp.connection_changed.connect(self._dashboard.on_connection_changed)
        self._udp.connection_changed.connect(self._on_connection)

        # Dashboard connection requests → UDP
        self._dashboard.connection_requested.connect(self._on_connection_request)

        self._udp.start()

    def _on_connection(self, connected: bool):
        if connected:
            self._sb_status.setText("Status: connected")
            self._sb_status.setStyleSheet("color:#27ae60; padding:0 10px;")
        else:
            self._sb_status.setText("Status: waiting for ESP32")
            self._sb_status.setStyleSheet("color:#e74c3c; padding:0 10px;")

    def _on_connection_request(self, ip_address: str, should_connect: bool):
        """Handle connection/disconnection requests from dashboard."""
        if should_connect:
            # Update ESP32 IP and reconnect
            self._udp.update_esp_ip(ip_address)
            self._sb_esp.setText(f"ESP32: {ip_address}:{UDP_SEND}")
        else:
            # Disconnect
            self._udp.stop()
            # Optionally restart with default IP
            self._udp.start()

    def closeEvent(self, event):
        self._udp.stop()
        event.accept()
        
    
    
    
        
            
    
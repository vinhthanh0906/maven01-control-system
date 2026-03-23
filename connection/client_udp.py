"""
udp_client.py
Sends JSON commands to ESP32 over UDP and receives status replies.
Runs recv loop in a background QThread — never blocks the GUI.
"""

import json
import socket
import threading
from PyQt6.QtCore import QObject, pyqtSignal, QThread


class UdpClient(QObject):
    """
    Send  :  desktop → ESP32   port 4210
    Recv  :  ESP32   → desktop port 4211

    Signals:
        status_received(dict)   — every UDP reply from ESP32
        connection_changed(bool)— True when first reply arrives
    """

    status_received    = pyqtSignal(dict)
    connection_changed = pyqtSignal(bool)

    def __init__(self,
                 esp32_ip:   str = "192.168.1.xxx",
                 esp32_port: int = 4210,
                 listen_port:int = 4211,
                 parent=None):
        super().__init__(parent)
        self._esp_ip    = esp32_ip
        self._esp_port  = esp32_port
        self._listen_port = listen_port
        self._connected = False
        self._running   = False

        # Send socket (UDP, no bind needed)
        self._send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._send_sock.settimeout(1.0)

        # Recv socket (bind to listen_port)
        self._recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._recv_sock.settimeout(2.0)

        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)

    # ── public API ────────────────────────────────────────────────────────────

    def start(self):
        """Bind recv socket and start background listener thread."""
        try:
            self._recv_sock.bind(("0.0.0.0", self._listen_port))
            self._running = True
            self._recv_thread.start()
            print(f"[UDP] Listening for ESP32 replies on port {self._listen_port}")
        except OSError as e:
            print(f"[UDP] Failed to bind port {self._listen_port}: {e}")

    def stop(self):
        self._running = False
        self._recv_sock.close()
        self._send_sock.close()

    def send_command(self, direction: str, speed: int = 150):
        """Send a motor command to the ESP32."""
        payload = json.dumps({"cmd": direction, "speed": speed}).encode()
        try:
            self._send_sock.sendto(payload, (self._esp_ip, self._esp_port))
            print(f"[UDP TX] → {self._esp_ip}:{self._esp_port}  {payload.decode()}")
        except Exception as e:
            print(f"[UDP] Send error: {e}")

    def update_esp_ip(self, ip: str):
        """Change target IP at runtime (from settings dialog)."""
        self._esp_ip = ip
        print(f"[UDP] ESP32 IP updated to {ip}")

    # ── background recv loop ──────────────────────────────────────────────────

    def _recv_loop(self):
        while self._running:
            try:
                data, addr = self._recv_sock.recvfrom(256)
                payload = json.loads(data.decode())
                print(f"[UDP RX] ← {addr[0]}  {payload}")

                if not self._connected:
                    self._connected = True
                    self.connection_changed.emit(True)

                self.status_received.emit(payload)

            except socket.timeout:
                # No packet — if we were connected, signal lost connection
                if self._connected:
                    self._connected = False
                    self.connection_changed.emit(False)
            except (json.JSONDecodeError, OSError):
                pass
"""
udp_client.py
Sends JSON commands to ESP32 over UDP and receives status replies.
Runs recv loop in a background thread — never blocks the GUI.
"""

import json
import socket
import threading
from PyQt6.QtCore import QObject, pyqtSignal


class UdpClient(QObject):
    """
    Send  :  desktop → ESP32   port 4210
    Recv  :  ESP32   → desktop port 4211

    Signals:
        status_received(dict)   — every UDP reply from ESP32
        connection_changed(bool)— True when first reply arrives, False on timeout
    """

    status_received    = pyqtSignal(dict)
    connection_changed = pyqtSignal(bool)

    def __init__(self,
                 esp32_ip:    str = "192.168.1.xxx",
                 esp32_port:  int = 4210,
                 listen_port: int = 4211,
                 parent=None):
        super().__init__(parent)
        self._esp_ip      = esp32_ip
        self._esp_port    = esp32_port
        self._listen_port = listen_port
        self._connected   = False
        self._running     = False
        self._last_payload = None

        # Send socket — no timeout, UDP is fire-and-forget
        self._send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Recv socket — small buffer to avoid stale packet backlog
        self._recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
        self._recv_sock.settimeout(0.1)  # 100 ms — snappy disconnection detection

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
        """Signal the recv loop to stop and close both sockets."""
        self._running = False
        self._recv_thread.join(timeout=1.0)
        self._recv_sock.close()
        self._send_sock.close()

    def send_command(self, direction: str, speed: int = 150):
        """
        Send a motor command to the ESP32.
        Skips the send if the payload is identical to the last one.
        """
        payload = json.dumps({"cmd": direction, "speed": speed}).encode()
        if payload == self._last_payload:
            return
        self._last_payload = payload
        try:
            self._send_sock.sendto(payload, (self._esp_ip, self._esp_port))
            print(f"[UDP TX] → {self._esp_ip}:{self._esp_port}  {payload.decode()}")
        except OSError as e:
            print(f"[UDP] Send error: {e}")

    def force_send_command(self, direction: str, speed: int = 150):
        """Send even if payload is unchanged — useful for keepalives or stop commands."""
        self._last_payload = None
        self.send_command(direction, speed)

    def update_esp_ip(self, ip: str):
        """Change target IP at runtime (e.g. from a settings dialog)."""
        self._esp_ip = ip
        self._last_payload = None  # reset cache — new target may need full state
        print(f"[UDP] ESP32 IP updated to {ip}")

    # ── background recv loop ──────────────────────────────────────────────────

    def _recv_loop(self):
        consecutive_timeouts = 0
        timeout_threshold    = 10  # 10 × 100 ms = 1 s before marking disconnected

        while self._running:
            try:
                data, addr = self._recv_sock.recvfrom(256)
                consecutive_timeouts = 0  # reset on any successful recv

                try:
                    payload = json.loads(data.decode())
                except json.JSONDecodeError:
                    print(f"[UDP] Bad JSON from {addr[0]}")
                    continue

                print(f"[UDP RX] ← {addr[0]}  {payload}")

                if not self._connected:
                    self._connected = True
                    self.connection_changed.emit(True)

                self.status_received.emit(payload)

            except socket.timeout:
                consecutive_timeouts += 1
                if self._connected and consecutive_timeouts >= timeout_threshold:
                    self._connected = False
                    self.connection_changed.emit(False)

            except OSError:
                # Socket was closed — exit cleanly
                break
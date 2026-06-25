"""
udp_client.py
Sends JSON commands to ESP32 over UDP and receives control status replies.
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
        status_received(dict)   — control status from ESP32
        connection_changed(bool)— True when connected, False when disconnected
    """

    status_received    = pyqtSignal(dict)
    connection_changed = pyqtSignal(bool)

    def __init__(self,
                 esp32_ip:   str = "192.168.1.xxx",
                 esp32_port: int = 4210,
                 listen_port: int = 4211,
                 parent=None):
        
        #This is the port connection 
        super().__init__(parent)
        self._esp_ip      = esp32_ip
        self._esp_port    = esp32_port
        self._listen_port = listen_port
        self._connected   = False
        self._running     = False

        #Socket and cmd gap 
        self._send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._send_sock.settimeout(0.05)

        #Receive command gaps
        self._recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._recv_sock.settimeout(0.5)

        #Thread split for 
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

    # Socket close when the stop command received
    def stop(self):
        self._running = False
        self._recv_sock.close()
        self._send_sock.close()

    # Socket the command 
    def send_command(self, direction: str, speed: int = 100):
        """Send a motor command to the ESP32."""
        payload = json.dumps({"cmd": direction, "speed": speed}).encode()
        try:
            self._send_sock.sendto(payload, (self._esp_ip, self._esp_port))
            print(f"[UDP TX] → {self._esp_ip}:{self._esp_port}  {payload.decode()}")
        except Exception as e:
            print(f"[UDP] Send error: {e}")

    #Update to ip of esp
    def update_esp_ip(self, ip: str):
        """Change target IP at runtime (from settings dialog)."""
        self._esp_ip = ip
        print(f"[UDP] ESP32 IP updated to {ip}")

    # ── background recv loop ──────────────────────────────────────────────────

    def _recv_loop(self):
        """Background thread loop - parse incoming control status and sensor data."""
        while self._running:
            try:
                data, addr = self._recv_sock.recvfrom(512)
                payload = json.loads(data.decode())
                print(f"[UDP RX] ← {addr[0]}  raw: {payload}")

                if not self._connected:
                    self._connected = True
                    self.connection_changed.emit(True)

                # Emit control fields + DHT11 sensor data + INA219 power data
                # NOTE: "power" may be present but explicitly null (e.g. when
                # the INA219 hasn't been read yet / ina_ok is false), so
                # `payload.get("power", {})` is NOT enough — that default only
                # applies when the key is missing, not when it's null. Guard
                # with `or {}` so a literal null doesn't blow up `.get()` below.
                power_data = payload.get("power") or {}
                control_data = {
                    "status": payload.get("status", "unknown"),
                    "cmd": payload.get("cmd", "stop"),
                    "speed": payload.get("speed", 0),
                    "uptime": payload.get("uptime", 0),
                    "temperature": payload.get("temperature", None),
                    "humidity": payload.get("humidity", None),
                    "sensor_ok": payload.get("sensor_ok", False),
                    "voltage": power_data.get("bus_v", None),
                    "current": power_data.get("current_mA", None),
                    "power": power_data.get("power_mW", None),
                    "ina_ok": payload.get("ina_ok", False)
                }
                self.status_received.emit(control_data)

            except socket.timeout:
                if self._connected:
                    self._connected = False
                    self.connection_changed.emit(False)
            except (json.JSONDecodeError, OSError) as e:
                print(f"[UDP] Parse/socket error: {e}")
            except Exception as e:
                # Catch-all so a single malformed/unexpected packet can never
                # silently kill this background thread. Without this, one bad
                # packet (e.g. a null where a dict was expected) stops every
                # future update — including temperature/humidity/voltage —
                # with no visible error.
                print(f"[UDP] Unexpected error while handling packet: {e}")
"""
simulator.py — Generates fake sensor data every second.
Emits a signal with a dict payload, replacing real MQTT data.
"""

import random
import math
import time
from PyQt5.QtCore import QThread, pyqtSignal


class SensorSimulator(QThread):
    """Background thread that emits simulated sensor readings."""

    data_ready = pyqtSignal(dict)   # emits sensor dict each tick

    def __init__(self, interval_ms=1000, parent=None):
        super().__init__(parent)
        self._interval = interval_ms / 1000.0
        self._running = False
        self._tick = 0

        # Rover state (mutated by commands)
        self.speed = 0          # 0–100
        self.direction = "stop"

    def run(self):
        self._running = True
        while self._running:
            self._tick += 1
            t = self._tick

            payload = {
                "tick": t,
                # Temperature drifts around 28 °C with slight sine wave
                "temperature": round(28 + 3 * math.sin(t / 20) + random.uniform(-0.5, 0.5), 1),
                # Humidity oscillates between 50–70 %
                "humidity":    round(60 + 8 * math.cos(t / 15) + random.uniform(-1, 1), 1),
                # CO₂ rises slowly then resets (simulates environment change)
                "co2":         round(400 + (t % 60) * 4 + random.uniform(-5, 5)),
                # Air quality index 0–500 (lower is better)
                "aqi":         round(max(0, 80 + 20 * math.sin(t / 30) + random.uniform(-10, 10))),
                # Battery drains 0.05 % per tick, resets at 0
                "battery":     round(max(0, 100 - ((t * 0.05) % 100)), 1),
                # Rover state
                "speed":       self.speed,
                "direction":   self.direction,
                # Fake GPS (small walk around Hanoi)
                "lat":         21.0285 + (t % 100) * 0.00005 * math.sin(t / 10),
                "lon":        105.8542 + (t % 100) * 0.00005 * math.cos(t / 10),
            }

            self.data_ready.emit(payload)
            time.sleep(self._interval)

    def stop(self):
        self._running = False
        self.wait()

    # Called by control panel buttons
    def send_command(self, direction: str, speed: int = 60):
        self.direction = direction
        self.speed = speed if direction != "stop" else 0
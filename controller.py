"""
control_panel.py — Rover control tab.
D-pad buttons + speed slider. Emits commands to the simulator
(or swap simulator.send_command for mqtt_client.publish later).
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QSlider, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QKeyEvent


# ── styles ───────────────────────────────────────────────────────────────────

BTN_BASE = """
    QPushButton {{
        background: {bg};
        color: {fg};
        border: 1px solid {border};
        border-radius: 10px;
        font-size: 22pt;
        font-weight: 600;
        min-width: 70px;
        min-height: 70px;
    }}
    QPushButton:pressed {{
        background: {pressed};
    }}
    QPushButton:disabled {{
        background: #1e2028;
        color: #444;
        border-color: #2e3040;
    }}
"""

BTN_MOVE  = BTN_BASE.format(bg="#1e3a5f", fg="#5dade2", border="#2e6090", pressed="#2a82da")
BTN_STOP  = BTN_BASE.format(bg="#4a1a1a", fg="#e74c3c", border="#8b3030", pressed="#c0392b")
BTN_SPEED = """
    QPushButton {
        background: #1e3820;
        color: #2ecc71;
        border: 1px solid #2e6040;
        border-radius: 8px;
        font-size: 11pt;
        min-width: 80px;
        min-height: 34px;
        padding: 0 12px;
    }
    QPushButton:pressed { background: #27ae60; color: #fff; }
    QPushButton:checked { background: #27ae60; color: #fff; border-color: #1e8449; }
"""

LOG_STYLE = """
    QLabel {
        background: #161820;
        color: #888;
        border: 1px solid #2e3040;
        border-radius: 6px;
        padding: 6px 10px;
        font-family: monospace;
        font-size: 10pt;
    }
"""


# ── widget ───────────────────────────────────────────────────────────────────

class ControlPanelTab(QWidget):
    """Emits command_sent(direction, speed) signal."""

    command_sent = pyqtSignal(str, int)   # direction, speed

    def __init__(self, parent=None):
        super().__init__(parent)
        self._speed = 60
        self._last_dir = "stop"
        self._build_ui()
        self.setFocusPolicy(Qt.StrongFocus)  # capture keyboard

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # ── title ──
        title = QLabel("Rover Command Center")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color:#aaa; font-size:14pt; font-weight:500; letter-spacing:1px;")
        root.addWidget(title)

        hint = QLabel("Click buttons  ·  or use  W A S D  /  Arrow keys")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color:#555; font-size:9pt;")
        root.addWidget(hint)

        root.addSpacing(10)

        # ── center section: d-pad + status ──
        mid = QHBoxLayout()
        mid.addStretch()

        dpad_frame = QFrame()
        dpad_frame.setStyleSheet("QFrame { background: #1a1c24; border: 1px solid #2e3040; border-radius: 14px; }")
        dpad_frame.setFixedSize(280, 280)
        dpad = QGridLayout(dpad_frame)
        dpad.setSpacing(8)
        dpad.setContentsMargins(20, 20, 20, 20)

        self._btn_fwd  = QPushButton("▲"); self._btn_fwd .setStyleSheet(BTN_MOVE)
        self._btn_bwd  = QPushButton("▼"); self._btn_bwd .setStyleSheet(BTN_MOVE)
        self._btn_left = QPushButton("◀"); self._btn_left.setStyleSheet(BTN_MOVE)
        self._btn_rght = QPushButton("▶"); self._btn_rght.setStyleSheet(BTN_MOVE)
        self._btn_stop = QPushButton("■"); self._btn_stop.setStyleSheet(BTN_STOP)

        dpad.addWidget(self._btn_fwd,  0, 1)
        dpad.addWidget(self._btn_left, 1, 0)
        dpad.addWidget(self._btn_stop, 1, 1)
        dpad.addWidget(self._btn_rght, 1, 2)
        dpad.addWidget(self._btn_bwd,  2, 1)

        mid.addWidget(dpad_frame)
        mid.addSpacing(30)

        # Status panel on the right
        right = QVBoxLayout()
        right.setSpacing(12)
        right.addStretch()

        self._status_label = QLabel("STOPPED")
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setFixedWidth(160)
        self._status_label.setStyleSheet(
            "background:#1e2028; color:#e74c3c; border:1px solid #4a1a1a;"
            "border-radius:8px; font-size:16pt; font-weight:600; padding:10px;")
        right.addWidget(self._status_label)

        # Speed presets
        sp_lbl = QLabel("Speed preset")
        sp_lbl.setAlignment(Qt.AlignCenter)
        sp_lbl.setStyleSheet("color:#666; font-size:9pt;")
        right.addWidget(sp_lbl)

        sp_row = QHBoxLayout()
        sp_row.setSpacing(6)
        for label, val in (("Slow", 30), ("Mid", 60), ("Fast", 90)):
            b = QPushButton(label)
            b.setStyleSheet(BTN_SPEED)
            b.setCheckable(True)
            b.setChecked(val == 60)
            b.clicked.connect(lambda _, v=val, btn=b: self._set_speed(v, btn))
            sp_row.addWidget(b)
            setattr(self, f"_sp_{label.lower()}", b)
        right.addLayout(sp_row)

        # Speed display
        self._speed_display = QLabel(f"Speed: {self._speed} cm/s")
        self._speed_display.setAlignment(Qt.AlignCenter)
        self._speed_display.setStyleSheet("color:#2ecc71; font-size:11pt;")
        right.addWidget(self._speed_display)

        right.addStretch()
        mid.addLayout(right)
        mid.addStretch()
        root.addLayout(mid)

        # ── command log ──
        log_lbl = QLabel("Command log")
        log_lbl.setStyleSheet("color:#555; font-size:9pt;")
        root.addWidget(log_lbl)

        self._log = QLabel("— waiting for commands —")
        self._log.setStyleSheet(LOG_STYLE)
        self._log.setFixedHeight(80)
        self._log.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._log.setWordWrap(True)
        root.addWidget(self._log)

        self._log_lines = []

        # ── connect buttons ──
        self._btn_fwd .clicked.connect(lambda: self._send("forward"))
        self._btn_bwd .clicked.connect(lambda: self._send("backward"))
        self._btn_left.clicked.connect(lambda: self._send("left"))
        self._btn_rght.clicked.connect(lambda: self._send("right"))
        self._btn_stop.clicked.connect(lambda: self._send("stop"))

    # ── internal ──────────────────────────────────────────────────────────────

    def _send(self, direction: str):
        self._last_dir = direction
        self.command_sent.emit(direction, self._speed)

        color = {"forward":"#2ecc71","backward":"#e74c3c",
                 "left":"#3498db","right":"#f39c12","stop":"#e74c3c"}.get(direction,"#aaa")
        self._status_label.setText(direction.upper())
        self._status_label.setStyleSheet(
            f"background:#1e2028; color:{color}; border:1px solid {color}44;"
            "border-radius:8px; font-size:16pt; font-weight:600; padding:10px;")

        spd_str = f"{self._speed} cm/s" if direction != "stop" else "0 cm/s"
        self._log_lines.append(f"→ {direction.upper():10s}  speed={spd_str}")
        if len(self._log_lines) > 4:
            self._log_lines.pop(0)
        self._log.setText("\n".join(self._log_lines))

    def _set_speed(self, value: int, clicked_btn: QPushButton):
        self._speed = value
        self._speed_display.setText(f"Speed: {value} cm/s")
        for lbl in ("slow", "mid", "fast"):
            btn = getattr(self, f"_sp_{lbl}")
            btn.setChecked(btn is clicked_btn)

    # ── keyboard support ──────────────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent):
        mapping = {
            Qt.Key_W: "forward",  Qt.Key_Up:    "forward",
            Qt.Key_S: "backward", Qt.Key_Down:  "backward",
            Qt.Key_A: "left",     Qt.Key_Left:  "left",
            Qt.Key_D: "right",    Qt.Key_Right: "right",
            Qt.Key_Space: "stop",
        }
        direction = mapping.get(event.key())
        if direction and not event.isAutoRepeat():
            self._send(direction)
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        nav_keys = {Qt.Key_W, Qt.Key_S, Qt.Key_A, Qt.Key_D,
                    Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right}
        if event.key() in nav_keys and not event.isAutoRepeat():
            self._send("stop")
        else:
            super().keyReleaseEvent(event)
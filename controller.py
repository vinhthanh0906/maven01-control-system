"""
control_panel.py  (PyQt6 — UDP control edition)
D-pad + speed selector → UDP commands to ESP32.
Status panel shows live ACK from rover (cmd / speed / uptime).
Keyboard: W A S D / arrows to move, Space to stop.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QFrame, QLineEdit, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent

BTN_MOVE = """
QPushButton {
    background:#1e3a5f; color:#5dade2;
    border:1px solid #2e6090; border-radius:10px;
    font-size:22pt; font-weight:600;
    min-width:70px; min-height:70px;
}
QPushButton:pressed { background:#2a82da; color:#fff; }
"""
BTN_STOP = """
QPushButton {
    background:#4a1a1a; color:#e74c3c;
    border:1px solid #8b3030; border-radius:10px;
    font-size:22pt; font-weight:600;
    min-width:70px; min-height:70px;
}
QPushButton:pressed { background:#c0392b; color:#fff; }
"""
BTN_SPEED = """
QPushButton {
    background:#1e3820; color:#2ecc71;
    border:1px solid #2e6040; border-radius:8px;
    font-size:10pt; min-width:70px; min-height:30px;
}
QPushButton:pressed { background:#27ae60; color:#fff; }
QPushButton:checked  { background:#27ae60; color:#fff; border-color:#1e8449; }
"""


class ControlPanelTab(QWidget):
    command_sent = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._speed     = 150
        self._log_lines = []
        self._build_ui()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("Rover UDP Control")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color:#aaa; font-size:14pt; font-weight:500;")
        root.addWidget(title)

        hint = QLabel("W A S D / Arrow keys to move  ·  Space = stop")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color:#555; font-size:9pt;")
        root.addWidget(hint)

        # IP bar
        ip_row = QHBoxLayout()
        ip_lbl = QLabel("ESP32 IP:")
        ip_lbl.setStyleSheet("color:#888; font-size:10pt;")
        self._ip_input = QLineEdit("192.168.4.1")
        self._ip_input.setFixedWidth(160)
        self._ip_input.setStyleSheet(
            "background:#161820; color:#2a82da; border:1px solid #2e3040;"
            "border-radius:6px; padding:4px 8px; font-size:10pt; font-family:monospace;")
        self._ip_input.textChanged.connect(
            lambda ip: self.command_sent.emit("__ip__" + ip, 0))

        self._conn_badge = QLabel("not connected")
        self._conn_badge.setStyleSheet(
            "background:#2e1a1a; color:#e74c3c; border:1px solid #5a2a2a;"
            "border-radius:10px; padding:3px 12px; font-size:9pt;")

        ip_row.addStretch()
        ip_row.addWidget(ip_lbl)
        ip_row.addWidget(self._ip_input)
        ip_row.addSpacing(12)
        ip_row.addWidget(self._conn_badge)
        ip_row.addStretch()
        root.addLayout(ip_row)

        # Mid: dpad + status
        mid = QHBoxLayout()
        mid.addStretch()

        dpad_frame = QFrame()
        dpad_frame.setStyleSheet("QFrame{background:#1a1c24;border:1px solid #2e3040;border-radius:14px;}")
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
        mid.addSpacing(24)

        right = QVBoxLayout()
        right.setSpacing(10)
        right.addStretch()

        self._dir_badge = QLabel("STOPPED")
        self._dir_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dir_badge.setFixedWidth(160)
        self._dir_badge.setStyleSheet(
            "background:#1e2028; color:#e74c3c; border:1px solid #4a1a1a;"
            "border-radius:8px; font-size:16pt; font-weight:600; padding:10px;")
        right.addWidget(self._dir_badge)

        sp_lbl = QLabel("Speed (PWM 0–255)")
        sp_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sp_lbl.setStyleSheet("color:#666; font-size:9pt;")
        right.addWidget(sp_lbl)

        sp_row = QHBoxLayout()
        sp_row.setSpacing(6)
        for label, val in (("Slow", 80), ("Mid", 150), ("Fast", 220)):
            b = QPushButton(label)
            b.setStyleSheet(BTN_SPEED)
            b.setCheckable(True)
            b.setChecked(val == 150)
            b.clicked.connect(lambda _, v=val, btn=b: self._set_speed(v, btn))
            sp_row.addWidget(b)
            setattr(self, f"_sp_{label.lower()}", b)
        right.addLayout(sp_row)

        self._speed_lbl = QLabel(f"PWM: {self._speed} / 255")
        self._speed_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._speed_lbl.setStyleSheet("color:#2ecc71; font-size:10pt;")
        right.addWidget(self._speed_lbl)

        status_box = QGroupBox("Rover reply")
        status_box.setStyleSheet(
            "QGroupBox{color:#555;font-size:9pt;border:1px solid #2e3040;"
            "border-radius:8px;margin-top:8px;padding-top:4px;}"
            "QGroupBox::title{subcontrol-origin:margin;left:10px;}")
        status_box.setFixedWidth(160)
        sl = QVBoxLayout(status_box)
        sl.setSpacing(4)
        self._rv_cmd    = QLabel("cmd: —")
        self._rv_speed  = QLabel("speed: —")
        self._rv_uptime = QLabel("uptime: —")
        for lbl in (self._rv_cmd, self._rv_speed, self._rv_uptime):
            lbl.setStyleSheet("color:#888; font-size:9pt; font-family:monospace;")
            sl.addWidget(lbl)
        right.addWidget(status_box)
        right.addStretch()
        mid.addLayout(right)
        mid.addStretch()
        root.addLayout(mid)

        log_lbl = QLabel("Command log")
        log_lbl.setStyleSheet("color:#555; font-size:9pt;")
        root.addWidget(log_lbl)

        self._log = QLabel("— waiting for commands —")
        self._log.setStyleSheet(
            "background:#161820; color:#888; border:1px solid #2e3040;"
            "border-radius:6px; padding:6px 10px; font-family:monospace; font-size:10pt;")
        self._log.setFixedHeight(80)
        self._log.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._log.setWordWrap(True)
        root.addWidget(self._log)

        self._btn_fwd .clicked.connect(lambda: self._send("forward"))
        self._btn_bwd .clicked.connect(lambda: self._send("backward"))
        self._btn_left.clicked.connect(lambda: self._send("left"))
        self._btn_rght.clicked.connect(lambda: self._send("right"))
        self._btn_stop.clicked.connect(lambda: self._send("stop"))

    def _send(self, direction: str):
        self.command_sent.emit(direction, self._speed)
        colors = {"forward":"#2ecc71","backward":"#e74c3c",
                  "left":"#3498db","right":"#f39c12","stop":"#e74c3c"}
        c = colors.get(direction, "#aaa")
        self._dir_badge.setText(direction.upper())
        self._dir_badge.setStyleSheet(
            f"background:#1e2028; color:{c}; border:1px solid {c}44;"
            "border-radius:8px; font-size:16pt; font-weight:600; padding:10px;")
        spd = str(self._speed) if direction != "stop" else "0"
        self._log_lines.append(f"-> {direction.upper():10s}  pwm={spd}")
        if len(self._log_lines) > 4:
            self._log_lines.pop(0)
        self._log.setText("\n".join(self._log_lines))

    def _set_speed(self, value: int, clicked_btn):
        self._speed = value
        self._speed_lbl.setText(f"PWM: {value} / 255")
        for lbl in ("slow", "mid", "fast"):
            btn = getattr(self, f"_sp_{lbl}")
            btn.setChecked(btn is clicked_btn)

    def on_rover_status(self, payload: dict):
        self._rv_cmd   .setText(f"cmd: {payload.get('cmd','—')}")
        self._rv_speed .setText(f"speed: {payload.get('speed','—')}")
        self._rv_uptime.setText(f"uptime: {payload.get('uptime',0)}s")

    def on_connection_changed(self, connected: bool):
        if connected:
            self._conn_badge.setText("connected")
            self._conn_badge.setStyleSheet(
                "background:#1a2e1a; color:#2ecc71; border:1px solid #2e6040;"
                "border-radius:10px; padding:3px 12px; font-size:9pt;")
        else:
            self._conn_badge.setText("not connected")
            self._conn_badge.setStyleSheet(
                "background:#2e1a1a; color:#e74c3c; border:1px solid #5a2a2a;"
                "border-radius:10px; padding:3px 12px; font-size:9pt;")

    def keyPressEvent(self, event: QKeyEvent):
        mapping = {
            Qt.Key.Key_W:"forward", Qt.Key.Key_Up:"forward",
            Qt.Key.Key_S:"backward",Qt.Key.Key_Down:"backward",
            Qt.Key.Key_A:"left",    Qt.Key.Key_Left:"left",
            Qt.Key.Key_D:"right",   Qt.Key.Key_Right:"right",
            Qt.Key.Key_Space:"stop",
        }
        d = mapping.get(event.key())
        if d and not event.isAutoRepeat():
            self._send(d)
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        nav = {Qt.Key.Key_W,Qt.Key.Key_S,Qt.Key.Key_A,Qt.Key.Key_D,
               Qt.Key.Key_Up,Qt.Key.Key_Down,Qt.Key.Key_Left,Qt.Key.Key_Right}
        if event.key() in nav and not event.isAutoRepeat():
            self._send("stop")
        else:
            super().keyReleaseEvent(event)
            
            


#Place holder fo
class AutoPilot(QWidget):
    pass


    
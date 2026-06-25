import math
import time
from collections import deque

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QGridLayout, QSizePolicy, QProgressBar,
    QPushButton, QLineEdit, QTabWidget
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QFont,
    QPainterPath, QLinearGradient, QRadialGradient,
    QPolygonF, QConicalGradient
)

BG0      = "#0a0c12"
BG1      = "#0f1118"
BG2      = "#14161f"
BG3      = "#1a1d28"
BORDER   = "#1e2235"
ACCENT   = "#00d4ff"
ACCENT2  = "#0077ff"
GREEN    = "#00ff88"
AMBER    = "#ffaa00"
RED      = "#ff3355"
PURPLE   = "#9966ff"
DIM      = "#3a3f55"
TEXT_PRI = "#e8ecff"
TEXT_SEC = "#6b7299"
TEXT_DIM = "#3a3f55"


'''
Define global panel size 
'''
def panel(parent=None):
    f = QFrame(parent)
    f.setStyleSheet(f"""
        QFrame {{
            background: {BG2};
            border: 1px solid {BORDER};
            border-radius: 10px;
        }}
    """)
    return f


# split into : left, middle, right
def section_label(text):
    l = QLabel(text.upper())
    l.setStyleSheet(f"""
        color: {TEXT_SEC};
        font-size: 8pt;
        font-family: 'Courier New', monospace;
        letter-spacing: 2px;
        padding: 4px 0px 2px 0px;
    """)
    return l


#online/ off line
def status_dot(online=True):
    dot = QLabel("●")
    dot.setStyleSheet(f"color: {GREEN if online else RED}; font-size: 8pt;")
    return dot


def _to_float(val):
    """Best-effort numeric coercion. Returns None if val is missing or not
    something that can sensibly be turned into a float (so a bad/unexpected
    type from the rover never raises mid-update and stalls the rest of the
    dashboard refresh)."""
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


''' Custom widget 
- Linear compass view 
- Radar 
- gyro 
- 

'''


class CompassWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._heading = 0.0
        self.setMinimumHeight(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_heading(self, deg):
        self._heading = deg % 360
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        
        # Linear compass strip
        strip_y = h / 2 - 15
        strip_h = 30
        strip_margin = 60
        strip_w = w - strip_margin * 2
        strip_x = strip_margin
        
        # Background
        p.setPen(QPen(QColor(BORDER), 1.5))
        p.setBrush(QColor(BG1))
        p.drawRoundedRect(int(strip_x), int(strip_y), int(strip_w), int(strip_h), 8, 8)
        
        # Heading tape: show ±90° around current heading
        font_small = QFont("Courier New", 7)
        font_large = QFont("Courier New", 9)
        font_large.setBold(True)
        
        p.setPen(QColor(TEXT_DIM))
        p.setFont(font_small)
        
        pixels_per_degree = strip_w / 180.0  # Full 180° range displayed
        center_x = strip_x + strip_w / 2
        
        # Draw degree ticks and labels (-90 to +90 relative to heading)
        for rel_deg in range(-90, 91, 10):
            abs_deg = (self._heading + rel_deg) % 360
            x = center_x + rel_deg * pixels_per_degree
            
            if strip_x < x < strip_x + strip_w:
                # Tick mark
                tick_h = 8 if rel_deg % 30 == 0 else 4
                p.setPen(QPen(QColor(ACCENT if rel_deg % 30 == 0 else DIM), 1.5 if rel_deg % 30 == 0 else 0.8))
                p.drawLine(int(x), int(strip_y + strip_h - tick_h), int(x), int(strip_y + strip_h))
                
                # Labels every 30°
                if rel_deg % 30 == 0:
                    p.setPen(QColor(TEXT_SEC if rel_deg != 0 else ACCENT))
                    p.setFont(font_small)
                    label = f"{int(abs_deg):03d}°"
                    p.drawText(QRectF(x - 20, strip_y - 12, 40, 10),
                              Qt.AlignmentFlag.AlignCenter, label)
        
        # Center indicator (triangle pointing down)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(GREEN))
        triangle = QPolygonF([
            QPointF(center_x, strip_y - 8),
            QPointF(center_x - 8, strip_y),
            QPointF(center_x + 8, strip_y)
        ])
        p.drawPolygon(triangle)
        
        # Current heading display at bottom
        p.setPen(QColor(TEXT_PRI))
        p.setFont(font_large)
        p.drawText(QRectF(w/2 - 60, strip_y + strip_h + 12, 120, 20),
                  Qt.AlignmentFlag.AlignCenter, f"HDG {int(self._heading):03d}°")
        
        p.end()


class GyroWidget(QWidget):
    """Simplified 3D horizon indicator."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._roll  = 0.0
        self._pitch = 0.0
        self.setMinimumSize(140, 100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_attitude(self, roll, pitch):
        self._roll  = roll
        self._pitch = pitch
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = min(w, h) / 2 - 6

        p.setClipRegion(__import__('PyQt6.QtGui', fromlist=['QRegion']).QRegion(
            int(cx - r), int(cy - r), int(r * 2), int(r * 2), 
            __import__('PyQt6.QtGui', fromlist=['QRegion']).QRegion.RegionType.Ellipse))

        pitch_offset = self._pitch / 90.0 * r
        roll_rad = math.radians(self._roll)

        # Sky
        sky = QLinearGradient(0, 0, 0, h)
        sky.setColorAt(0, QColor("#003366"))
        sky.setColorAt(1, QColor("#0055aa"))
        p.fillRect(0, 0, w, h, sky)

        # Ground (rotated rect)
        p.save()
        p.translate(cx, cy + pitch_offset)
        p.rotate(self._roll)
        ground = QLinearGradient(0, 0, 0, r)
        ground.setColorAt(0, QColor("#3d2200"))
        ground.setColorAt(1, QColor("#5a3300"))
        p.setBrush(ground)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(-w, 0, w * 2, h)
        p.restore()

        # Horizon line
        p.save()
        p.translate(cx, cy + pitch_offset)
        p.rotate(self._roll)
        p.setPen(QPen(QColor("#ffffff"), 1.5))
        p.drawLine(-int(r * 1.5), 0, int(r * 1.5), 0)
        p.restore()

        p.setClipping(False)

        # Outer ring
        p.setPen(QPen(QColor(BORDER), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Center crosshair
        p.setPen(QPen(QColor(AMBER), 1.5))
        p.drawLine(int(cx - 20), int(cy), int(cx - 6), int(cy))
        p.drawLine(int(cx + 6),  int(cy), int(cx + 20), int(cy))
        p.drawLine(int(cx), int(cy - 6), int(cx), int(cy + 6))

        p.end()


class RadarWidget(QWidget):
    """
    Half-circle radar sweep (top half) — front-facing ultrasonic FOV.
    Sweep bounces 0°→180°→0° like a real sonar head.
    Origin sits at bottom-center, fan opens upward.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle   = 0.0      # 0–180 degrees across the half circle
        self._dir     = 1        # 1 = sweeping right, -1 = sweeping left
        self._blips   = []       # list of (angle_deg, dist 0-1, age)
        self._timer   = QTimer(self)
        self._timer.timeout.connect(self._sweep)
        self._timer.start(20)
        self.setMinimumHeight(110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _sweep(self):
        self._angle += self._dir * 1.8
        if self._angle >= 180:
            self._angle = 180; self._dir = -1
        elif self._angle <= 0:
            self._angle = 0;   self._dir = 1
        # Age blips
        self._blips = [(a, d, age + 1) for a, d, age in self._blips if age < 80]
        self.update()

    def add_blip(self, angle_deg: float, dist_norm: float):
        """Add a detection blip. angle 0–180, dist 0–1 (1 = max range)."""
        self._blips.append((angle_deg, dist_norm, 0))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Origin: bottom center; radius fills the widget
        cx = w / 2
        cy = h - 10          # origin sits near bottom edge
        r  = min(w / 2, h) - 12

        # ── clip to upper half-circle ──────────────────────────────────────
        clip = QPainterPath()
        clip.moveTo(cx, cy)
        clip.arcTo(QRectF(cx - r, cy - r, r * 2, r * 2), 0, 180)
        clip.closeSubpath()
        p.setClipPath(clip)

        # Background fill
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(BG1))
        p.drawPath(clip)

        # ── arc rings ──────────────────────────────────────────────────────
        pen_ring = QPen(QColor(DIM), 0.6)
        p.setPen(pen_ring)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(1, 5):
            ri = r * i / 4
            p.drawArc(QRectF(cx - ri, cy - ri, ri * 2, ri * 2), 0, 180 * 16)

        # ── radial spokes every 30° ────────────────────────────────────────
        p.setPen(QPen(QColor(DIM), 0.5))
        for deg in range(0, 181, 30):
            rad = math.radians(180 - deg)   # 0°=left, 180°=right mapped to screen
            p.drawLine(int(cx), int(cy),
                       int(cx + r * math.cos(rad)),
                       int(cy - r * math.sin(rad)))

        # ── sweep glow (conical, clipped to half) ─────────────────────────
        # Convert our 0–180 angle to screen angle (180°=left, 0°=right)
        screen_deg = 180 - self._angle
        cg = QConicalGradient(cx, cy, screen_deg)
        cg.setColorAt(0.0,   QColor(0, 212, 255, 200))
        cg.setColorAt(0.12,  QColor(0, 212, 255, 50))
        cg.setColorAt(0.13,  QColor(0, 0, 0, 0))
        cg.setColorAt(1.0,   QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(cg)
        p.drawPath(clip)

        # ── sweep line ────────────────────────────────────────────────────
        rad = math.radians(180 - self._angle)
        ex  = cx + r * math.cos(rad)
        ey  = cy - r * math.sin(rad)
        p.setPen(QPen(QColor(ACCENT), 1.8))
        p.drawLine(int(cx), int(cy), int(ex), int(ey))

        # ── blips ─────────────────────────────────────────────────────────
        for a, d, age in self._blips:
            alpha  = max(0, 255 - int(age * 3))
            brad   = math.radians(180 - a)
            bx     = cx + r * d * math.cos(brad)
            by_    = cy - r * d * math.sin(brad)
            size   = max(2, 6 - age // 15)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 255, 136, alpha))
            p.drawEllipse(QPointF(bx, by_), size, size)

        p.setClipping(False)

        # ── outer arc border ──────────────────────────────────────────────
        p.setPen(QPen(QColor(BORDER), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2), 0, 180 * 16)
        p.drawLine(int(cx - r), int(cy), int(cx + r), int(cy))  # baseline

        # Origin dot
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(ACCENT))
        p.drawEllipse(QPointF(cx, cy), 3, 3)

        # ── range labels ──────────────────────────────────────────────────
        font = QFont("Courier New", 6)
        p.setFont(font)
        p.setPen(QColor(TEXT_DIM))
        for i, lbl in enumerate(("25", "50", "75", "100"), 1):
            lx = cx + r * i / 4 + 3
            p.drawText(int(lx), int(cy) - 2, lbl + "cm")

        # Angle ticks at bottom baseline
        for deg in (0, 30, 60, 90, 120, 150, 180):
            rad2 = math.radians(180 - deg)
            tx = cx + (r + 6) * math.cos(rad2)
            ty = cy - (r + 6) * math.sin(rad2)
            p.drawText(QRectF(tx - 10, ty - 7, 20, 10),
                       Qt.AlignmentFlag.AlignCenter, f"{deg}°")

        # Pending label
        p.setPen(QColor(TEXT_DIM))
        p.drawText(QRectF(cx - 55, cy - r / 2 - 7, 110, 14),
                   Qt.AlignmentFlag.AlignCenter, "ULTRASONIC — PENDING")
        p.end()


class _CADPainter(QWidget):
    """Pure painter — 2D top-down rover silhouette (used inside RoverCADWidget)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cmd = "stop"
        self.setMinimumHeight(110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_command(self, cmd):
        self._cmd = cmd
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h   = self.width(), self.height()
        cx, cy = w / 2, h / 2
        bw, bh = min(w * 0.35, 70), min(h * 0.65, 90)

        left_active  = self._cmd in ("forward", "backward")
        right_active = self._cmd in ("forward", "backward")


        # Differential steering: turning spins the opposite side's wheels
        if self._cmd == "left":
            right_active = True   # right wheels drive → rover pivots left
        elif self._cmd == "right":
            left_active  = True   # left wheels drive  → rover pivots right

        # Body
        p.setPen(QPen(QColor(ACCENT2), 1))
        p.setBrush(QColor(BG3))
        p.drawRoundedRect(QRectF(cx - bw/2, cy - bh/2, bw, bh), 8, 8)

        # Direction arrow
        arr_color = QColor(GREEN) if self._cmd not in ("stop", "") else QColor(DIM)
        p.setPen(QPen(arr_color, 2))
        if self._cmd == "forward":
            p.drawLine(int(cx), int(cy + 10), int(cx), int(cy - 10))
            pts = QPolygonF([QPointF(cx, cy - 18), QPointF(cx - 7, cy - 8), QPointF(cx + 7, cy - 8)])
            p.setBrush(arr_color); p.drawPolygon(pts)
        elif self._cmd == "backward":
            p.drawLine(int(cx), int(cy - 10), int(cx), int(cy + 10))
            pts = QPolygonF([QPointF(cx, cy + 18), QPointF(cx - 7, cy + 8), QPointF(cx + 7, cy + 8)])
            p.setBrush(arr_color); p.drawPolygon(pts)
        elif self._cmd == "left":
            pts = QPolygonF([QPointF(cx - 18, cy), QPointF(cx - 8, cy - 7), QPointF(cx - 8, cy + 7)])
            p.setBrush(arr_color); p.drawPolygon(pts)
        elif self._cmd == "right":
            pts = QPolygonF([QPointF(cx + 18, cy), QPointF(cx + 8, cy - 7), QPointF(cx + 8, cy + 7)])
            p.setBrush(arr_color); p.drawPolygon(pts)

        # Wheels (4 corners)
        ww, wh = 10, 22
        wheel_col = lambda a: QColor(GREEN) if a else QColor(DIM)
        for wx, wy, wa in [
            (cx - bw/2 - ww + 2, cy - bh/2 + 4,  left_active),
            (cx - bw/2 - ww + 2, cy + bh/2 - 26, left_active),
            (cx + bw/2 - 2,      cy - bh/2 + 4,  right_active),
            (cx + bw/2 - 2,      cy + bh/2 - 26, right_active),
        ]:
            p.setPen(QPen(wheel_col(wa), 1))
            p.setBrush(QColor(BG1) if not wa else QColor(GREEN).darker(180))
            p.drawRoundedRect(QRectF(wx, wy, ww, wh), 3, 3)

        p.end()


class RoverCADWidget(QWidget):
    """
    Rover telemetry + controller in one compact panel.
    Keyboard: W/A/S/D or arrows to move, Space to stop.
    """
    command_sent = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._speed = 150          # fixed mid speed (no UI selector)
        self._build_ui()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ── build ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # ── IP bar ────────────────────────────────────────────────────────────
        ip_row = QHBoxLayout()
        ip_lbl = QLabel("ESP32 IP:")
        ip_lbl.setStyleSheet(f"color:{TEXT_SEC}; font-size:8pt; font-family:'Courier New';")

        self._ip_input = QLineEdit("192.168.4.1")
        self._ip_input.setFixedWidth(118)
        self._ip_input.setStyleSheet(
            f"background:{BG1}; color:{ACCENT2}; border:1px solid {BORDER};"
            "border-radius:4px; padding:2px 6px; font-size:8pt; font-family:monospace;")
        self._ip_input.textChanged.connect(
            lambda ip: self.command_sent.emit("__ip__" + ip, 0))

        self._conn_badge = QLabel("● OFFLINE")
        self._conn_badge.setStyleSheet(
            f"color:{RED}; font-size:7pt; font-family:'Courier New'; letter-spacing:1px;")

        ip_row.addWidget(ip_lbl)
        ip_row.addWidget(self._ip_input)
        ip_row.addSpacing(6)
        ip_row.addWidget(self._conn_badge)
        ip_row.addStretch()
        root.addLayout(ip_row)

        # ── Cross layout: [FWD] above, [LEFT] [CAD] [RIGHT], [BWD] below ─────
        #
        #  col:   0          1         2
        #  row 0:         [FWD btn]
        #  row 1: [LEFT] [CAD 2D]  [RIGHT]
        #  row 2:        [BWD btn]
        #  row 3:        [STOP btn]
        #
        grid = QGridLayout()
        grid.setSpacing(2)
        grid.setContentsMargins(0, 0, 0, 0)

        _BTN = """
            QPushButton {{
                background: {bg};
                color: {fg};
                border: 1px solid {bd};
                border-radius: 8px;
                font-size: 11pt;
                font-weight: 700;
                min-width: 48px;
                min-height: 48px;
                max-width: 52px;
                max-height: 52px;
            }}
            QPushButton:pressed {{ background: {pr}; color: #fff; }}
        """
        _STOP = """
            QPushButton {{
                background: #2a1010;
                color: {RED};
                border: 1px solid #6a2020;
                border-radius: 8px;
                font-size: 12pt;
                font-weight: 700;
                min-width: 48px;
                min-height: 28px;
                max-width: 52px;
                max-height: 32px;
            }}
            QPushButton:pressed {{ background: #8b1a1a; color: #fff; }}
        """.format(RED=RED)

        def _nav_btn(icon):
            b = QPushButton(icon)
            b.setStyleSheet(_BTN.format(
                bg="#0d1e30", fg=ACCENT, bd="#1a3a5a", pr=ACCENT2))
            return b

        self._btn_fwd  = _nav_btn("▲")
        self._btn_bwd  = _nav_btn("▼")
        self._btn_left = _nav_btn("◀")
        self._btn_rght = _nav_btn("▶")
        self._btn_stop = QPushButton("⏹")
        self._btn_stop.setStyleSheet(_STOP)

        # CAD painter — sized to sit neatly between the buttons
        self._cad_painter = _CADPainter()
        self._cad_painter.setMinimumSize(80, 80)   # ← was 100, 100
        self._cad_painter.setMaximumSize(110, 110) # ← was 140, 140)
        self._cad_painter.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)


        # Row 0: forward centred over CAD
        grid.addWidget(self._btn_fwd,  0, 1, Qt.AlignmentFlag.AlignHCenter)
        # Row 1: left | CAD | right
        grid.addWidget(self._btn_left, 1, 0, Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self._cad_painter, 1, 1)
        grid.addWidget(self._btn_rght, 1, 2, Qt.AlignmentFlag.AlignVCenter)
        # Row 2: backward centred under CAD
        grid.addWidget(self._btn_bwd,  2, 1, Qt.AlignmentFlag.AlignHCenter)
        # Row 3: stop centred
        grid.addWidget(self._btn_stop, 3, 1, Qt.AlignmentFlag.AlignHCenter)


        # Column stretch: side cols fixed, center grows
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)

        root.addLayout(grid)

        # ── Direction badge (compact, below grid) ─────────────────────────────
        self._dir_badge = QLabel("STANDBY")
        self._dir_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dir_badge.setStyleSheet(
            f"color:{DIM}; font-size:8pt; font-family:'Courier New';"
            "letter-spacing:2px; padding:2px 0;")
        root.addWidget(self._dir_badge)

        # Wire buttons
        self._btn_fwd .clicked.connect(lambda: self._send("forward"))
        self._btn_bwd .clicked.connect(lambda: self._send("backward"))
        self._btn_left.clicked.connect(lambda: self._send("left"))
        self._btn_rght.clicked.connect(lambda: self._send("right"))
        self._btn_stop.clicked.connect(lambda: self._send("stop"))

    # ────────────────────────────────── public API ──────────────────────────────

    #Command to the terminal and to the rover
    def set_command(self, cmd: str):
        """Update the CAD silhouette (called from DashboardTab.update_data)."""
        self._cad_painter.set_command(cmd)

    #Status: Stop, foward, left, right 
    def on_rover_status(self, payload: dict):
        # No reply box anymore — silhouette + badge carry the state
        cmd = payload.get("cmd", "stop")
        self._cad_painter.set_command(cmd)
        self._update_badge(cmd)


    #This the connection status text
    def on_connection_changed(self, connected: bool):
        if connected:
            self._conn_badge.setText("● ONLINE")
            self._conn_badge.setStyleSheet(
                f"color:{GREEN}; font-size:7pt; font-family:'Courier New'; letter-spacing:1px;")
        else:
            self._conn_badge.setText("● OFFLINE")
            self._conn_badge.setStyleSheet(
                f"color:{RED}; font-size:7pt; font-family:'Courier New'; letter-spacing:1px;")

    # ── keyboard ──────────────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        mapping = {
            Qt.Key.Key_W: "forward",  Qt.Key.Key_Up:    "forward",
            Qt.Key.Key_S: "backward", Qt.Key.Key_Down:  "backward",
            Qt.Key.Key_A: "left",     Qt.Key.Key_Left:  "left",
            Qt.Key.Key_D: "right",    Qt.Key.Key_Right: "right",
            Qt.Key.Key_Space: "stop",
        }
        d = mapping.get(event.key())
        if d and not event.isAutoRepeat():
            self._send(d)
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        nav = {Qt.Key.Key_W, Qt.Key.Key_S, Qt.Key.Key_A, Qt.Key.Key_D,
               Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right}
        if event.key() in nav and not event.isAutoRepeat():
            self._send("stop")
        else:
            super().keyReleaseEvent(event)

    # ── private ───────────────────────────────────────────────────────────────

    def _send(self, direction: str):
        self.command_sent.emit(direction, self._speed)
        self._cad_painter.set_command(direction)
        self._update_badge(direction)

    def _update_badge(self, direction: str):
        colors = {
            "forward":  GREEN,  "backward": RED,
            "left":     ACCENT, "right":    AMBER,
            "stop":     DIM,
        }
        labels = {
            "forward": "▲ FORWARD", "backward": "▼ BACKWARD",
            "left":    "◀ LEFT",    "right":    "▶ RIGHT",
            "stop":    "STANDBY",
        }
        c = colors.get(direction, DIM)
        self._dir_badge.setText(labels.get(direction, direction.upper()))
        self._dir_badge.setStyleSheet(
            f"color:{c}; font-size:8pt; font-family:'Courier New';"
            "letter-spacing:2px; padding:2px 0;")


class LineGraphWidget(QWidget):
    """
    Real-time strip-chart for a single sensor metric.
    Standard orientation: X-axis = time (scrolling, newest on the right),
    Y-axis = magnitude in the sensor's own unit.
    """
    def __init__(self, color=ACCENT, unit="", window_seconds=20.0,
                 time_gap=2.0, y_range=None, idle_range=(0, 100),
                 decimals=1, parent=None):
        super().__init__(parent)
        self._color          = QColor(color)
        self._unit            = unit
        self._window_seconds  = window_seconds
        self._time_gap        = time_gap
        self._data             = deque()          # list of (timestamp, value)
        self._fixed_range      = y_range           # optional (min, max) override
        self._idle_range       = idle_range        # Y-axis range before data arrives
        self._decimals         = decimals          # digits shown on Y-axis labels
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def add_point(self, value):
        """Append a reading, timestamped now. None readings are skipped."""
        if value is None:
            return
        now = time.monotonic()
        self._data.append((now, value))
        cutoff = now - self._window_seconds - self._time_gap
        while self._data and self._data[0][0] < cutoff:
            self._data.popleft()
        self.update()

    def clear(self):
        self._data.clear()
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        margin_l, margin_r, margin_t, margin_b = 44, 12, 10, 22
        plot_x = margin_l
        plot_y = margin_t
        plot_w = max(1, w - margin_l - margin_r)
        plot_h = max(1, h - margin_t - margin_b)

        # Background
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(BG1))
        p.drawRoundedRect(0, 0, w, h, 6, 6)

        pts = list(self._data)
        have_line = len(pts) >= 2

        # ── Y-axis: magnitude range ──────────────────────────────────────────
        if self._fixed_range:
            vmin, vmax = self._fixed_range
        elif have_line:
            vals = [v for (_, v) in pts]
            vmin, vmax = min(vals), max(vals)
            if vmin == vmax:
                vmin -= 1
                vmax += 1
            pad = (vmax - vmin) * 0.15
            vmin -= pad
            vmax += pad
        else:
            vmin, vmax = self._idle_range

        # ── X-axis: time range — fixed window, newest on the right ──────────
        t_now = pts[-1][0] if pts else time.monotonic()
        t_min = t_now - self._window_seconds
        t_max = t_now

        def x_for(ts):
            """Map a timestamp to a pixel X position (left=old, right=now)."""
            t = (ts - t_min) / (t_max - t_min) if t_max > t_min else 1.0
            t = max(0.0, min(1.0, t))
            return plot_x + t * plot_w

        def y_for(v):
            """Map a magnitude value to a pixel Y position (bottom=low, top=high)."""
            t = (v - vmin) / (vmax - vmin) if vmax > vmin else 0.5
            t = max(0.0, min(1.0, t))
            return plot_y + plot_h - t * plot_h   # invert: high value → top

        p.setFont(QFont("Courier New", 6))

        # ── Horizontal gridlines: magnitude (Y-axis) ─────────────────────────
        n_yticks = 4
        for i in range(n_yticks + 1):
            gy = plot_y + plot_h * i / n_yticks
            p.setPen(QPen(QColor(BORDER), 0.6))
            p.drawLine(int(plot_x), int(gy), int(plot_x + plot_w), int(gy))
            val_label = vmax - (vmax - vmin) * i / n_yticks  # top=max, bottom=min
            p.setPen(QColor(TEXT_DIM))
            p.drawText(QRectF(0, gy - 6, plot_x - 4, 12),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       f"{val_label:.{self._decimals}f}{self._unit}")

        # ── Vertical gridlines: time (X-axis) — labeled "NOW", "-2s", etc. ──
        t = t_now
        while t >= t_min - 1e-6:
            gx = x_for(t)
            p.setPen(QPen(QColor(BORDER), 0.6))
            p.drawLine(int(gx), int(plot_y), int(gx), int(plot_y + plot_h))
            secs_ago = t_now - t
            label = "NOW" if secs_ago < 0.05 else f"-{secs_ago:.0f}s"
            p.setPen(QColor(TEXT_DIM))
            p.drawText(QRectF(gx - 18, plot_y + plot_h + 4, 36, 12),
                       Qt.AlignmentFlag.AlignCenter, label)
            t -= self._time_gap

        if have_line:
            # ── filled area under the line ────────────────────────────────────
            line_path = QPainterPath()
            line_path.moveTo(x_for(pts[0][0]), y_for(pts[0][1]))
            for ts, v in pts[1:]:
                line_path.lineTo(x_for(ts), y_for(v))

            area_path = QPainterPath(line_path)
            area_path.lineTo(x_for(pts[-1][0]), plot_y + plot_h)
            area_path.lineTo(x_for(pts[0][0]),  plot_y + plot_h)
            area_path.closeSubpath()

            grad = QLinearGradient(0, plot_y, 0, plot_y + plot_h)
            fill  = QColor(self._color); fill.setAlpha(85)
            clear = QColor(self._color); clear.setAlpha(0)
            grad.setColorAt(0, fill)
            grad.setColorAt(1, clear)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(grad)
            p.drawPath(area_path)

            p.setPen(QPen(self._color, 1.8))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(line_path)

            # ── latest-point marker + value label ──────────────────────────
            lx = x_for(pts[-1][0])
            ly = y_for(pts[-1][1])
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self._color)
            p.drawEllipse(QPointF(lx, ly), 3.2, 3.2)

            label = f"{pts[-1][1]:.{self._decimals}f}{self._unit}"
            lbl_w = 64
            lx_clamped = min(max(lx - lbl_w / 2, plot_x), plot_x + plot_w - lbl_w)
            ly_clamped = min(max(ly - 14, plot_y), plot_y + plot_h - 14)
            p.setPen(QColor(TEXT_PRI))
            p.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
            p.drawText(QRectF(lx_clamped, ly_clamped, lbl_w, 14),
                       Qt.AlignmentFlag.AlignCenter, label)
        else:
            p.setPen(QColor(TEXT_DIM))
            p.setFont(QFont("Courier New", 9))
            msg = "COLLECTING DATA…" if pts else "AWAITING ROVER…"
            p.drawText(QRectF(plot_x, plot_y, plot_w, plot_h),
                       Qt.AlignmentFlag.AlignCenter, msg)

        # Outer border
        p.setPen(QPen(QColor(BORDER), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(0, 0, w - 1, h - 1, 6, 6)

        p.end()


class SensorGraphPanel(QWidget):
    """
    Tabbed real-time trend view for the 4 sensor-block metrics
    (Temperature / Humidity / Atmospheric Pressure / Air Quality). Replaces the old
    camera feed placeholder — call add_data(...) on every telemetry update
    to scroll all 4 graphs forward together.
    """
    def __init__(self, parent=None):

        #Content margin 
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                background: {BG1};
                border: 1px solid {BORDER};
                border-radius: 6px;
                top: -1px;
            }}
            QTabBar::tab {{
                background: {BG2};
                color: {TEXT_SEC};
                border: 1px solid {BORDER};
                border-bottom: none;
                padding: 5px 14px;
                margin-right: 2px;
                font-size: 8pt;
                font-family: 'Courier New';
                letter-spacing: 1px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }}
            QTabBar::tab:selected {{
                background: {BG1};
                color: {TEXT_PRI};
            }}
            QTabBar::tab:hover {{
                color: {TEXT_PRI};
            }}
        """)

        # key -> (tab title, color, unit, idle range, decimals)
        # idle range/decimals are what the axis scaffold uses before real
        # data arrives — colors match the SensorBlocks on the right.
        # Magnitude limits: temp=100°C, humidity=100%, pressure=10atm, aqi in ppm
        specs = [
            ("temp",  "TEMPERATURE",   "#ff6655", "°C",  (0, 100),  1),
            ("hum",   "HUMIDITY",      "#44aaff", "%",   (0, 100),  1),
            ("press", "ATM. PRESSURE", "#bb44ff", "atm", (0, 10),   2),
            ("aqi",   "AIR QUALITY",   "#44ff99", "ppm", (0, 500),  0),
        ]
        self._graphs = {}
        for key, title, color, unit, idle_range, decimals in specs:
            g = LineGraphWidget(color=color, unit=unit,
                                 idle_range=idle_range, decimals=decimals)
            self._graphs[key] = g
            self._tabs.addTab(g, title)

        layout.addWidget(self._tabs)

        # Keep the time axis ("NOW" / "-2s" / ...) sliding even before any
        # rover data arrives, so the grid doesn't look like a frozen image.
        self._idle_timer = QTimer(self)
        self._idle_timer.timeout.connect(self._tick_idle)
        self._idle_timer.start(1000)

    def _tick_idle(self):
        for g in self._graphs.values():
            g.update()

    def add_data(self, temp=None, hum=None, press=None, aqi=None):
        """Push one new reading into each graph. None values are skipped
        (that metric's line just doesn't advance this tick)."""
        self._graphs["temp"].add_point(temp)
        self._graphs["hum"].add_point(hum)
        self._graphs["press"].add_point(press)
        self._graphs["aqi"].add_point(aqi)


class SensorBlock(QWidget):
    """A labeled sensor value card with online/offline dot."""
    def __init__(self, label, unit, value="—", color=ACCENT, parent=None):
        super().__init__(parent)
        self._color   = color
        self._online  = False
        self._layout  = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 8, 10, 8)
        self._layout.setSpacing(2)

        # Header row: label + dot
        hdr = QHBoxLayout()
        self._lbl = QLabel(label.upper())
        self._lbl.setStyleSheet(f"color:{TEXT_SEC}; font-size:8pt; font-family:'Courier New'; letter-spacing:1px;")
        self._dot = QLabel("●")
        self._dot.setStyleSheet(f"color:{RED}; font-size:9pt;")
        self._dot.setAlignment(Qt.AlignmentFlag.AlignRight)
        hdr.addWidget(self._lbl)
        hdr.addStretch()
        hdr.addWidget(self._dot)
        self._layout.addLayout(hdr)

        # Value
        self._val = QLabel(value)
        self._val.setStyleSheet(f"color:{color}; font-size:20pt; font-weight:700; font-family:'Courier New';")
        self._val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._val)

        # Unit
        self._unit_lbl = QLabel(unit)
        self._unit_lbl.setStyleSheet(f"color:{TEXT_DIM}; font-size:8pt; font-family:'Courier New';")
        self._unit_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._unit_lbl)

        self.setStyleSheet(f"""
            SensorBlock {{
                background:{BG3};
                border:1px solid {BORDER};
                border-radius:8px;
            }}
        """)

    #This is the  set value as placeholder 
    def set_value(self, val, online=True):
        self._online = online
        self._val.setText(str(val))
        self._dot.setStyleSheet(f"color:{'#00ff88' if online else '#ff3355'}; font-size:9pt;")

    #Red bolder for alert
    def set_alert(self, alert=False):
        border = RED if alert else BORDER
        self.setStyleSheet(f"""
            SensorBlock {{
                background:{BG3};
                border:1px solid {border};
                border-radius:8px;
            }}
        """)




class DashboardTab(QWidget):
    command_sent = pyqtSignal(str, int)   # forwarded from RoverCADWidget

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_cmd = "stop"
        self._sim_heading = 0.0
        self._heading_offset = 0.0  # Track heading changes from gyro
        self._msg_lines = []        # Message log buffer
        self._build_ui()

        # Forward controller commands up to the app window
        self._cad.command_sent.connect(self.command_sent)

        # Animate compass placeholder
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick_anim)
        self._anim_timer.start(100)

    def _build_ui(self):
        self.setStyleSheet(f"background:{BG0}; color:{TEXT_PRI};")
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        root.addLayout(self._build_left(),   4)   # was 3
        root.addLayout(self._build_center(), 10)  # was 10 
        root.addLayout(self._build_right(),  1)   # was 3 

    # ── LEFT PANEL ────────────────────────────────────────────────────────────

    def _build_left(self):
        col = QVBoxLayout()
        col.setSpacing(6)

        # Power
        self._s_voltage = SensorBlock("Voltage", "V", "—", "#ffbb44")
        col.addWidget(self._s_voltage)

        # Gyro
        # gy = panel()
        # gl = QVBoxLayout(gy)
        # gl.setContentsMargins(10, 8, 10, 8)
        # gl.setSpacing(4)
        # hdr2 = QHBoxLayout()
        # hdr2.addWidget(section_label("Gyro / Attitude"))
        # self._gyro_dot = QLabel("●")
        # self._gyro_dot.setStyleSheet(f"color:{DIM}; font-size:8pt;")
        # hdr2.addStretch(); hdr2.addWidget(self._gyro_dot)
        # gl.addLayout(hdr2)
        # self._gyro = GyroWidget()
        # gl.addWidget(self._gyro)
        # # Roll / Pitch values
        # rp = QHBoxLayout()
        # self._roll_lbl  = QLabel("ROLL  0.0°")
        # self._pitch_lbl = QLabel("PITCH 0.0°")
        # for l in (self._roll_lbl, self._pitch_lbl):
        #     l.setStyleSheet(f"color:{TEXT_SEC}; font-size:8pt; font-family:'Courier New';")
        # rp.addWidget(self._roll_lbl); rp.addStretch(); rp.addWidget(self._pitch_lbl)
        # gl.addLayout(rp)
        # col.addWidget(gy)

        # Mode: The rover drive mode 
        # mo = panel()
        # ml = QVBoxLayout(mo)
        # ml.setContentsMargins(10, 8, 10, 8)
        # ml.setSpacing(6)
        # ml.addWidget(section_label("Drive Mode"))
        # mode_row = QHBoxLayout()
        # mode_row.setSpacing(6)
        # self._mode_fast = QLabel("⚡ FAST")
        # self._mode_eco  = QLabel("🌿 ECO")
        # self._mode_fast.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self._mode_eco .setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self._mode_fast.setStyleSheet(f"""
        #     background:#1a1200; color:{AMBER}; border:1px solid {AMBER};
        #     border-radius:8px; font-size:9pt; font-family:'Courier New';
        #     padding:6px 0;
        # """)
        # self._mode_eco.setStyleSheet(f"""
        #     background:{BG3}; color:{DIM}; border:1px solid {BORDER};
        #     border-radius:8px; font-size:9pt; font-family:'Courier New';
        #     padding:6px 0;
        # """)
        # mode_row.addWidget(self._mode_fast); mode_row.addWidget(self._mode_eco)
        # ml.addLayout(mode_row)
        # col.addWidget(mo)

        # Rover CAD
        cad = panel()
        cadl = QVBoxLayout(cad)
        cadl.setContentsMargins(10, 8, 10, 8)
        cadl.setSpacing(4)
        cadl.addWidget(section_label("Rover Telemetry"))
        self._cad = RoverCADWidget()
        cadl.addWidget(self._cad)
        self._cad_status = QLabel("STANDBY — MOTORS IDLE")
        self._cad_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cad_status.setStyleSheet(f"color:{DIM}; font-size:8pt; font-family:'Courier New';")
        cadl.addWidget(self._cad_status)
        col.addWidget(cad, 1)

        return col

    # ────────────────────────────── CENTER PANEL ──────────────────────────────────

    def _build_center(self):
        col = QVBoxLayout()
        col.setSpacing(6)

        # Compass
        cp = panel()
        cpl = QVBoxLayout(cp)
        cpl.setContentsMargins(10, 8, 10, 8)
        cpl.setSpacing(4)
        hdr = QHBoxLayout()
        hdr.addWidget(section_label("Compass / Heading"))
        self._compass_dot = QLabel("●")
        self._compass_dot.setStyleSheet(f"color:{DIM}; font-size:8pt;")
        hdr.addStretch(); hdr.addWidget(self._compass_dot)
        cpl.addLayout(hdr)
        self._compass = CompassWidget()
        cpl.addWidget(self._compass)
        col.addWidget(cp, 1)

        # Sensor Trends (was: Main Camera placeholder)
        trends = panel()
        trl = QVBoxLayout(trends)
        trl.setContentsMargins(10, 8, 10, 8)
        trl.setSpacing(4)
        trl.addWidget(section_label("Sensor Trends"))

        self._graph_panel = SensorGraphPanel()
        trl.addWidget(self._graph_panel)
        col.addWidget(trends, 3)

        # Radar
        # rd = panel()
        # rdl = QVBoxLayout(rd)
        # rdl.setContentsMargins(10, 8, 10, 8)
        # rdl.setSpacing(4)
        # hdr3 = QHBoxLayout()
        # hdr3.addWidget(section_label("Radar — Ultrasonic"))
        # self._radar_dot = QLabel("●")
        # self._radar_dot.setStyleSheet(f"color:{DIM}; font-size:8pt;")
        # hdr3.addStretch(); hdr3.addWidget(self._radar_dot)
        # rdl.addLayout(hdr3)
        # self._radar = RadarWidget()
        # rdl.addWidget(self._radar)
        # col.addWidget(rd, 2)
        return col

    # ──────────────────────── RIGHT PANEL ────────────────────────────────

    def _build_right(self):
        col = QVBoxLayout()
        col.setSpacing(6)

        # Sensor blocks
        self._s_temp  = SensorBlock("Temperature", "°C",  "—", "#ff6655")
        self._s_hum   = SensorBlock("Humidity",    "%",   "—", "#44aaff")
        self._s_press = SensorBlock("Atmospheric Pressure", "atm", "—", "#bb44ff")
        self._s_aqi   = SensorBlock("Air Quality", "ppm", "—", "#44ff99")

        #add widget each sensor
        for s in (self._s_temp, self._s_hum, self._s_press, self._s_aqi):
            col.addWidget(s, 1)   

        col.addStretch()

        # Status messages
        msg = panel()
        ml = QVBoxLayout(msg)
        ml.setContentsMargins(10, 8, 10, 8)
        ml.setSpacing(4)
        ml.addWidget(section_label("System Messages"))

        #Place holder for the all message from terminal
        self._msg_lines = []
        self._msg_label = QLabel("[ SYSTEM BOOT OK ]\n[ WAITING FOR ROVER ]")
        self._msg_label.setStyleSheet(f"""
            color:{GREEN}; font-size:8pt; font-family:'Courier New';
            background:{BG1}; border:1px solid {BORDER};
            border-radius:6px; padding:6px;
        """)
        self._msg_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._msg_label.setMinimumHeight(80)
        ml.addWidget(self._msg_label)
        col.addWidget(msg, 1)

        return col

    # ── update ────────────────────────────────────────────────────────────────
    # This is the function to write data
    def update_data(self, payload: dict):
        temp     = payload.get("temperature", None)
        hum      = payload.get("humidity",    None)
        ok       = payload.get("sensor_ok",   False)
        voltage  = payload.get("voltage",     None)
        current  = payload.get("current",     None)
        power    = payload.get("power",       None)
        ina_ok   = payload.get("ina_ok",      False)
        cmd      = payload.get("cmd",         "stop")
        uptime   = payload.get("uptime",      0)
        speed    = payload.get("speed",       0)

        # ── Voltage display (INA219) ──────────────────────────────────────────
        voltage_f = _to_float(voltage)
        if ina_ok and voltage_f is not None:
            self._s_voltage.set_value(f"{voltage_f:.2f}", online=True)
            # Alert if voltage is too low
            self._s_voltage.set_alert(voltage_f < 10.5)
        else:
            self._s_voltage.set_value("—", online=False)

        # ── Temperature & Humidity (DHT11) ────────────────────────────────────
        temp_f = _to_float(temp)
        if temp_f is not None:
            self._s_temp.set_value(f"{temp_f:.1f}", online=ok)
            self._s_temp.set_alert(temp_f > 40 or temp_f < 5)
        else:
            self._s_temp.set_value("—", online=False)

        hum_f = _to_float(hum)
        if hum_f is not None:
            self._s_hum.set_value(f"{hum_f:.1f}", online=ok)
        else:
            self._s_hum.set_value("—", online=False)

        # Placeholders stay offline
        self._s_press.set_value("—", online=False)
        self._s_aqi.set_value("—", online=False)

        # Push this tick's readings into the trend graphs (atmospheric
        # pressure/AQI have no live source yet, so those two tabs just sit
        # on "collecting data" until a payload actually carries them)
        self._graph_panel.add_data(
            temp=temp_f, hum=hum_f,
            press=_to_float(payload.get("pressure")),
            aqi=_to_float(payload.get("aqi")),
        )

        # Rover CAD + controller reply
        self._cad.set_command(cmd)
        self._cad.on_rover_status(payload)
        self._last_cmd = cmd
        status_txt = {
            "forward":  "MOVING FORWARD",
            "backward": "MOVING BACKWARD",
            "left":     "TURNING LEFT",
            "right":    "TURNING RIGHT",
            "stop":     "STANDBY — MOTORS IDLE",
        }.get(cmd, cmd.upper())
        color = GREEN if cmd != "stop" else DIM
        self._cad_status.setText(status_txt)
        self._cad_status.setStyleSheet(
            f"color:{color}; font-size:8pt; font-family:'Courier New';")

        # System message
        temp_str = f"{temp_f:.1f}°C" if temp_f is not None else "—"
        hum_str  = f"{hum_f:.1f}%" if hum_f is not None else "—"
        volt_str = f"{voltage_f:.2f}V" if voltage_f is not None else "—"
        self._log_msg(f"[ T+{uptime:05d}s ]  CMD={cmd.upper():8s}  "
                      f"SPD={speed:3d}  "
                      f"V={volt_str}  T={temp_str}  H={hum_str}")

    def _log_msg(self, text):
        self._msg_lines.append(text)
        if len(self._msg_lines) > 5:
            self._msg_lines.pop(0)
        self._msg_label.setText("\n".join(self._msg_lines))

    def on_rover_status(self, payload: dict):
        """Proxy — lets merge_monitor wire a single target for rover status."""
        self.update_data(payload)

    def on_connection_changed(self, connected: bool):
        """Proxy — forwards connection state to the embedded controller."""
        self._cad.on_connection_changed(connected)

    def _tick_anim(self):
        # Only update compass with simulated data if IMU is offline
        # When IMU is online, heading is updated directly from gyro integration
        pass
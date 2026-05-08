"""
dashboard.py — Rover Mission Control Dashboard (PyQt6)
Full redesign: Left panel (power/gyro/mode/telemetry),
Center (compass/camera/radar), Right (environment sensors)
"""

import math
import time
from collections import deque

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QGridLayout, QSizePolicy, QProgressBar,
    QLineEdit, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QFont,
    QPainterPath, QLinearGradient, QRadialGradient,
    QPolygonF, QConicalGradient
)


# ── palette ───────────────────────────────────────────────────────────────────
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


#status dot for connect norfication 
def status_dot(online=True):
    dot = QLabel("●")
    dot.setStyleSheet(f"color: {GREEN if online else RED}; font-size: 8pt;")
    return dot


# ── custom widgets ────────────────────────────────────────────────────────────

class CompassWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._heading = 0.0
        self.setMinimumSize(200, 100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_heading(self, deg):
        self._heading = deg % 360
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        
        # Dimensions for linear compass
        cx = w / 2
        cy = h / 2
        compass_width = w - 40
        compass_height = 60

        # ── Background panel ──
        p.setPen(QPen(QColor(BORDER), 1.5))
        p.setBrush(QColor(BG1))
        p.drawRoundedRect(int(cx - compass_width/2), int(cy - compass_height/2), 
                         int(compass_width), int(compass_height), 8, 8)

        # ── Compass scale markings ──
        # Show 360 degrees as a continuous line
        scale_y = int(cy - compass_height/4)
        scale_bottom_y = int(cy + compass_height/4)
        
        # Calculate pixel per degree
        pixels_per_degree = compass_width / 180  # Show 180 degree field of view
        
        # Draw scale background
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(BG2))
        p.drawRect(int(cx - compass_width/2), scale_y, int(compass_width), int(compass_height/2))
        
        # Draw degree markings
        p.setPen(QPen(QColor(DIM), 0.8))
        font_small = QFont("Courier New", 7)
        p.setFont(font_small)
        
        # Central heading position (where the pointer is)
        center_heading = self._heading
        
        # Draw marks from center_heading - 90 to center_heading + 90
        for offset in range(-90, 91, 10):
            deg_val = (center_heading + offset) % 360
            x_pos = cx + offset * pixels_per_degree
            
            # Skip if out of bounds
            if x_pos < cx - compass_width/2 or x_pos > cx + compass_width/2:
                continue
                
            # Main ticks every 30 degrees
            if offset % 30 == 0:
                tick_len = 12
                color = QColor(ACCENT)
                font_size = 8
            # Sub ticks every 10 degrees
            else:
                tick_len = 6
                color = QColor(TEXT_DIM)
                font_size = 6
            
            p.setPen(QPen(color, 1.5 if offset % 30 == 0 else 0.8))
            p.drawLine(int(x_pos), scale_y, int(x_pos), scale_y + tick_len)
            
            # Label cardinal directions
            cardinal_map = {0: "N", 90: "E", 180: "S", 270: "W"}
            if deg_val in cardinal_map:
                p.setPen(QColor(ACCENT if deg_val == 0 else TEXT_SEC))
                p_font = QFont("Courier New", font_size)
                p_font.setBold(True)
                p.setFont(p_font)
                p.drawText(int(x_pos - 8), scale_y + tick_len + 4, 16, 12,
                          Qt.AlignmentFlag.AlignCenter, cardinal_map[deg_val])
            else:
                # Draw degree values for major ticks
                if offset % 30 == 0 and offset != 0:
                    p.setPen(QColor(TEXT_DIM))
                    p_font = QFont("Courier New", 6)
                    p.setFont(p_font)
                    p.drawText(int(x_pos - 10), scale_y + tick_len + 4, 20, 12,
                              Qt.AlignmentFlag.AlignCenter, f"{int(deg_val)}")

        # ── Center pointer (needle) ──
        pointer_y_top = int(cy - compass_height/4 - 8)
        pointer_y_bottom = int(cy + compass_height/4 + 8)
        
        # Draw pointer triangle
        pts = QPolygonF([
            QPointF(cx - 8, pointer_y_top),
            QPointF(cx, pointer_y_top - 12),
            QPointF(cx + 8, pointer_y_top)
        ])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(ACCENT))
        p.drawPolygon(pts)
        
        # Draw center line
        p.setPen(QPen(QColor(ACCENT), 2))
        p.drawLine(int(cx), pointer_y_top, int(cx), pointer_y_bottom)

        # ── Heading readout ──
        p.setPen(QColor(TEXT_PRI))
        font_heading = QFont("Courier New", 14)
        font_heading.setBold(True)
        p.setFont(font_heading)
        
        heading_rect = QRectF(cx - 60, int(cy + compass_height/4 + 8), 120, 30)
        p.drawText(heading_rect, Qt.AlignmentFlag.AlignCenter, f"HDG {int(self._heading):03d}°")

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


class RoverCADWidget(QWidget):
    """2D top-down rover with 4 directional arrows and connection indicator."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cmd = "stop"
        self._connected = False
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_command(self, cmd):
        self._cmd = cmd
        self.update()

    def set_connected(self, connected):
        self._connected = connected
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h   = self.width(), self.height()
        cx, cy = w / 2, h / 2
        
        # ── Connection indicator light (top-left) ──
        conn_light_x = 15
        conn_light_y = 15
        conn_color = QColor(GREEN) if self._connected else QColor(RED)
        p.setPen(QPen(conn_color, 1.5))
        p.setBrush(conn_color)
        p.drawEllipse(conn_light_x - 4, conn_light_y - 4, 8, 8)
        
        # Connection glow
        if self._connected:
            glow = QRadialGradient(conn_light_x, conn_light_y, 4)
            glow.setColorAt(0, QColor(GREEN))
            glow.setColorAt(1, QColor(0, 255, 136, 30))
            p.setBrush(glow)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(conn_light_x - 8, conn_light_y - 8, 16, 16)
        
        # ── Center rover body ──
        bw, bh = 40, 50
        p.setPen(QPen(QColor(ACCENT2), 1.5))
        p.setBrush(QColor(BG3))
        p.drawRoundedRect(QRectF(cx - bw/2, cy - bh/2, bw, bh), 6, 6)
        
        # ── 4 Directional Arrows ──
        arrow_dist = 65
        arrow_size = 12
        
        # Up arrow (forward)
        fwd_active = self._cmd == "forward"
        fwd_color = GREEN if fwd_active else DIM
        p.setPen(QPen(QColor(fwd_color), 2))
        p.setBrush(QColor(fwd_color))
        up_arrow = QPolygonF([
            QPointF(cx, cy - arrow_dist),
            QPointF(cx - arrow_size, cy - arrow_dist + arrow_size + 2),
            QPointF(cx + arrow_size, cy - arrow_dist + arrow_size + 2)
        ])
        p.drawPolygon(up_arrow)
        
        # Down arrow (backward)
        bwd_active = self._cmd == "backward"
        bwd_color = GREEN if bwd_active else DIM
        p.setPen(QPen(QColor(bwd_color), 2))
        p.setBrush(QColor(bwd_color))
        down_arrow = QPolygonF([
            QPointF(cx, cy + arrow_dist),
            QPointF(cx - arrow_size, cy + arrow_dist - arrow_size - 2),
            QPointF(cx + arrow_size, cy + arrow_dist - arrow_size - 2)
        ])
        p.drawPolygon(down_arrow)
        
        # Left arrow (turn left)
        left_active = self._cmd == "left"
        left_color = GREEN if left_active else DIM
        p.setPen(QPen(QColor(left_color), 2))
        p.setBrush(QColor(left_color))
        left_arrow = QPolygonF([
            QPointF(cx - arrow_dist, cy),
            QPointF(cx - arrow_dist + arrow_size + 2, cy - arrow_size),
            QPointF(cx - arrow_dist + arrow_size + 2, cy + arrow_size)
        ])
        p.drawPolygon(left_arrow)
        
        # Right arrow (turn right)
        right_active = self._cmd == "right"
        right_color = GREEN if right_active else DIM
        p.setPen(QPen(QColor(right_color), 2))
        p.setBrush(QColor(right_color))
        right_arrow = QPolygonF([
            QPointF(cx + arrow_dist, cy),
            QPointF(cx + arrow_dist - arrow_size - 2, cy - arrow_size),
            QPointF(cx + arrow_dist - arrow_size - 2, cy + arrow_size)
        ])
        p.drawPolygon(right_arrow)
        
        # ── Wheels (4 corners of center body) ──
        ww, wh = 8, 16
        wheel_col_fwd = QColor(GREEN) if self._cmd in ("forward", "left", "right") else QColor(DIM)
        wheel_col_bwd = QColor(GREEN) if self._cmd in ("backward", "left", "right") else QColor(DIM)
        
        # Front wheels
        for wx_offset in [-bw/2 - ww + 2, bw/2 - 2]:
            p.setPen(QPen(wheel_col_fwd, 1))
            p.setBrush(QColor(BG1) if wheel_col_fwd == QColor(DIM) else QColor(GREEN).darker(200))
            p.drawRoundedRect(QRectF(cx + wx_offset, cy - bh/2 - 2, ww, wh), 2, 2)
        
        # Rear wheels
        for wx_offset in [-bw/2 - ww + 2, bw/2 - 2]:
            p.setPen(QPen(wheel_col_bwd, 1))
            p.setBrush(QColor(BG1) if wheel_col_bwd == QColor(DIM) else QColor(GREEN).darker(200))
            p.drawRoundedRect(QRectF(cx + wx_offset, cy + bh/2 - wh + 2, ww, wh), 2, 2)

        p.end()


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

    def set_value(self, val, online=True):
        self._online = online
        self._val.setText(str(val))
        self._dot.setStyleSheet(f"color:{'#00ff88' if online else '#ff3355'}; font-size:9pt;")

    def set_alert(self, alert=False):
        border = RED if alert else BORDER
        self.setStyleSheet(f"""
            SensorBlock {{
                background:{BG3};
                border:1px solid {border};
                border-radius:8px;
            }}
        """)


class BatteryWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = 85.0
        self._source = "MAIN"
        self.setMinimumHeight(56)

    def set_level(self, level, source="MAIN"):
        self._level = level
        self._source = source
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        bw, bh = w - 40, 28
        bx, by = 20, (h - bh) / 2

        # Battery shell
        p.setPen(QPen(QColor(DIM), 1.5))
        p.setBrush(QColor(BG1))
        p.drawRoundedRect(QRectF(bx, by, bw, bh), 4, 4)
        # Terminal nub
        p.setBrush(QColor(DIM))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(bx + bw, by + bh/2 - 5, 5, 10), 2, 2)

        # Fill
        fill_w = max(4, (self._level / 100.0) * (bw - 4))
        color  = QColor(GREEN) if self._level > 50 else QColor(AMBER) if self._level > 20 else QColor(RED)
        p.setBrush(color)
        p.drawRoundedRect(QRectF(bx + 2, by + 2, fill_w, bh - 4), 3, 3)

        # Text
        p.setPen(QColor(TEXT_PRI))
        font = QFont("Courier New", 9)
        font.setBold(True)
        p.setFont(font)
        p.drawText(QRectF(bx, by, bw, bh),
                   Qt.AlignmentFlag.AlignCenter,
                   f"{self._level:.0f}%  [{self._source}]")
        p.end()


# ── main dashboard ────────────────────────────────────────────────────────────

class DashboardTab(QWidget):
    # Signal to notify when user requests connection change
    connection_requested = pyqtSignal(str, bool)  # (ip_address, connect)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_cmd = "stop"
        self._sim_heading = 0.0
        self._connected = False
        self._build_ui()

        # Animate compass placeholder
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick_anim)
        self._anim_timer.start(100)

    def _build_ui(self):
        self.setStyleSheet(f"background:{BG0}; color:{TEXT_PRI};")
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        root.addLayout(self._build_left(),   1)
        root.addLayout(self._build_center(), 2)
        root.addLayout(self._build_right(),  1)

    # ── LEFT PANEL ────────────────────────────────────────────────────────────

    def _build_left(self):
        col = QVBoxLayout()
        col.setSpacing(6)

        # Power
        pw = panel()
        pl = QVBoxLayout(pw)
        pl.setContentsMargins(10, 8, 10, 8)
        pl.setSpacing(4)
        hdr = QHBoxLayout()
        hdr.addWidget(section_label("Power"))
        self._pwr_dot = QLabel("●")
        self._pwr_dot.setStyleSheet(f"color:{GREEN}; font-size:8pt;")
        hdr.addStretch(); hdr.addWidget(self._pwr_dot)
        pl.addLayout(hdr)
        self._battery = BatteryWidget()
        pl.addWidget(self._battery)
        # Source selector pills
        src_row = QHBoxLayout()
        src_row.setSpacing(4)
        for src in ("MAIN", "BACKUP"):
            b = QLabel(src)
            b.setAlignment(Qt.AlignmentFlag.AlignCenter)
            b.setStyleSheet(f"""
                background:{'#0d2a1a' if src=='MAIN' else BG3};
                color:{'#00ff88' if src=='MAIN' else TEXT_DIM};
                border:1px solid {'#00ff88' if src=='MAIN' else BORDER};
                border-radius:10px; font-size:8pt; font-family:'Courier New';
                padding:2px 10px;
            """)
            src_row.addWidget(b)
        pl.addLayout(src_row)
        col.addWidget(pw)

        # Gyro
        gy = panel()
        gl = QVBoxLayout(gy)
        gl.setContentsMargins(10, 8, 10, 8)
        gl.setSpacing(4)
        hdr2 = QHBoxLayout()
        hdr2.addWidget(section_label("Gyro / Attitude"))
        self._gyro_dot = QLabel("●")
        self._gyro_dot.setStyleSheet(f"color:{DIM}; font-size:8pt;")
        hdr2.addStretch(); hdr2.addWidget(self._gyro_dot)
        gl.addLayout(hdr2)
        self._gyro = GyroWidget()
        gl.addWidget(self._gyro)
        # Roll / Pitch values
        rp = QHBoxLayout()
        self._roll_lbl  = QLabel("ROLL  0.0°")
        self._pitch_lbl = QLabel("PITCH 0.0°")
        for l in (self._roll_lbl, self._pitch_lbl):
            l.setStyleSheet(f"color:{TEXT_SEC}; font-size:8pt; font-family:'Courier New';")
        rp.addWidget(self._roll_lbl); rp.addStretch(); rp.addWidget(self._pitch_lbl)
        gl.addLayout(rp)
        col.addWidget(gy)

        # Mode
        mo = panel()
        ml = QVBoxLayout(mo)
        ml.setContentsMargins(10, 8, 10, 8)
        ml.setSpacing(6)
        ml.addWidget(section_label("Drive Mode"))
        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)
        self._mode_fast = QLabel("⚡ FAST")
        self._mode_eco  = QLabel("🌿 ECO")
        self._mode_fast.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._mode_eco .setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._mode_fast.setStyleSheet(f"""
            background:#1a1200; color:{AMBER}; border:1px solid {AMBER};
            border-radius:8px; font-size:9pt; font-family:'Courier New';
            padding:6px 0;
        """)
        self._mode_eco.setStyleSheet(f"""
            background:{BG3}; color:{DIM}; border:1px solid {BORDER};
            border-radius:8px; font-size:9pt; font-family:'Courier New';
            padding:6px 0;
        """)
        mode_row.addWidget(self._mode_fast); mode_row.addWidget(self._mode_eco)
        ml.addLayout(mode_row)
        col.addWidget(mo)

        # Rover CAD
        cad = panel()
        cadl = QVBoxLayout(cad)
        cadl.setContentsMargins(10, 8, 10, 8)
        cadl.setSpacing(6)
        
        # Header
        cadl.addWidget(section_label("Rover Telemetry & Connection"))
        
        # Connection controls
        conn_row = QHBoxLayout()
        conn_row.setSpacing(4)
        conn_row.setContentsMargins(0, 0, 0, 0)
        
        # IP Address input
        self._ip_input = QLineEdit()
        self._ip_input.setText("192.168.4.1")
        self._ip_input.setPlaceholderText("Enter UDP IP address")
        self._ip_input.setStyleSheet(f"""
            QLineEdit {{
                background: {BG1};
                color: {TEXT_PRI};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 6px;
                font-size: 9pt;
                font-family: 'Courier New';
            }}
            QLineEdit:focus {{
                border: 1px solid {ACCENT};
            }}
        """)
        conn_row.addWidget(self._ip_input)
        
        # Connect/Disconnect button
        self._conn_btn = QPushButton("Connect")
        self._conn_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT2};
                color: {TEXT_PRI};
                border: 1px solid {ACCENT2};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 9pt;
                font-family: 'Courier New';
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {ACCENT};
            }}
            QPushButton:pressed {{
                background: #0055aa;
            }}
        """)
        self._conn_btn.setMaximumWidth(100)
        self._conn_btn.clicked.connect(self._on_conn_btn_clicked)
        conn_row.addWidget(self._conn_btn)
        cadl.addLayout(conn_row)
        
        # Rover CAD display (larger)
        self._cad = RoverCADWidget()
        self._cad.setMinimumHeight(240)
        cadl.addWidget(self._cad, 1)
        
        # Status text
        self._cad_status = QLabel("STANDBY — MOTORS IDLE")
        self._cad_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cad_status.setStyleSheet(f"color:{DIM}; font-size:8pt; font-family:'Courier New';")
        cadl.addWidget(self._cad_status)
        
        col.addWidget(cad, 1)

        return col

    # ── CENTER PANEL ──────────────────────────────────────────────────────────

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
        self._compass.setMinimumHeight(100)
        cpl.addWidget(self._compass)
        col.addWidget(cp, 1)

        # Camera
        cam = panel()
        caml = QVBoxLayout(cam)
        caml.setContentsMargins(10, 8, 10, 8)
        caml.setSpacing(4)
        hdr2 = QHBoxLayout()
        hdr2.addWidget(section_label("Main Camera"))
        self._cam_dot = QLabel("●")
        self._cam_dot.setStyleSheet(f"color:{DIM}; font-size:8pt;")
        hdr2.addStretch(); hdr2.addWidget(self._cam_dot)
        caml.addLayout(hdr2)

        cam_view = QFrame()
        cam_view.setStyleSheet(f"""
            QFrame {{
                background: {BG1};
                border: 1px solid {BORDER};
                border-radius: 6px;
            }}
        """)
        cam_view.setMinimumHeight(240)
        cam_inner = QVBoxLayout(cam_view)
        no_signal = QLabel("[ NO SIGNAL ]")
        no_signal.setAlignment(Qt.AlignmentFlag.AlignCenter)
        no_signal.setStyleSheet(f"""
            color:{DIM}; font-size:11pt; font-family:'Courier New';
            letter-spacing:4px;
        """)
        scan_lbl = QLabel("CAMERA MODULE — PENDING")
        scan_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scan_lbl.setStyleSheet(f"color:{TEXT_DIM}; font-size:8pt; font-family:'Courier New';")
        cam_inner.addStretch()
        cam_inner.addWidget(no_signal)
        cam_inner.addWidget(scan_lbl)
        cam_inner.addStretch()
        caml.addWidget(cam_view)
        col.addWidget(cam, 4)

        # Radar
        rd = panel()
        rdl = QVBoxLayout(rd)
        rdl.setContentsMargins(10, 8, 10, 8)
        rdl.setSpacing(4)
        hdr3 = QHBoxLayout()
        hdr3.addWidget(section_label("Radar — Ultrasonic"))
        self._radar_dot = QLabel("●")
        self._radar_dot.setStyleSheet(f"color:{DIM}; font-size:8pt;")
        hdr3.addStretch(); hdr3.addWidget(self._radar_dot)
        rdl.addLayout(hdr3)
        self._radar = RadarWidget()
        rdl.addWidget(self._radar)
        col.addWidget(rd, 1)

        return col

    # ── RIGHT PANEL ───────────────────────────────────────────────────────────

    def _build_right(self):
        col = QVBoxLayout()
        col.setSpacing(6)

        # Sensor blocks
        self._s_temp  = SensorBlock("Temperature", "°C",  "—", "#ff6655")
        self._s_hum   = SensorBlock("Humidity",    "%",   "—", "#44aaff")
        self._s_pres  = SensorBlock("Pressure",    "atm", "—", "#bb44ff")
        self._s_aqi   = SensorBlock("Air Quality", "AQI", "—", "#44ff99")

        for s in (self._s_temp, self._s_hum, self._s_pres, self._s_aqi):
            col.addWidget(s, 1)

        # Status messages
        msg = panel()
        ml = QVBoxLayout(msg)
        ml.setContentsMargins(10, 8, 10, 8)
        ml.setSpacing(4)
        ml.addWidget(section_label("System Messages"))

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

    def update_data(self, payload: dict):
        temp     = payload.get("temperature", None)
        hum      = payload.get("humidity",    None)
        ok       = payload.get("sensor_ok",   False)
        cmd      = payload.get("cmd",         "stop")
        uptime   = payload.get("uptime",      0)
        speed    = payload.get("speed",       0)

        # Sensor blocks
        if temp is not None:
            self._s_temp.set_value(f"{temp:.1f}", online=ok)
            self._s_temp.set_alert(temp > 40 or temp < 5)
        if hum is not None:
            self._s_hum.set_value(f"{hum:.1f}", online=ok)

        # Placeholders stay offline
        self._s_pres.set_value("—", online=False)
        self._s_aqi.set_value("—", online=False)

        # Rover CAD
        self._cad.set_command(cmd)
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

        # Battery placeholder
        self._battery.set_level(85.0, "MAIN")

        # System message
        self._log_msg(f"[ T+{uptime:05d}s ]  CMD={cmd.upper():8s}  "
                      f"SPD={speed:3d}  "
                      f"T={temp:.1f}°C  H={hum:.1f}%")

    def _log_msg(self, text):
        self._msg_lines.append(text)
        if len(self._msg_lines) > 5:
            self._msg_lines.pop(0)
        self._msg_label.setText("\n".join(self._msg_lines))

    def _tick_anim(self):
        # Slowly rotate compass heading for visual feedback
        if self._last_cmd == "left":
            self._sim_heading = (self._sim_heading - 2) % 360
        elif self._last_cmd == "right":
            self._sim_heading = (self._sim_heading + 2) % 360
        self._compass.set_heading(self._sim_heading)

    def on_connection_changed(self, connected: bool):
        """Handle rover connection status changes."""
        self._connected = connected
        self._cad.set_connected(connected)
        
        # Update button appearance
        if connected:
            self._conn_btn.setText("Disconnect")
            self._conn_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {RED};
                    color: {TEXT_PRI};
                    border: 1px solid {RED};
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 9pt;
                    font-family: 'Courier New';
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: #ff5577;
                }}
                QPushButton:pressed {{
                    background: #cc2244;
                }}
            """)
            self._ip_input.setReadOnly(True)
            self._log_msg("[ ROVER CONNECTED ]")
        else:
            self._conn_btn.setText("Connect")
            self._conn_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {ACCENT2};
                    color: {TEXT_PRI};
                    border: 1px solid {ACCENT2};
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 9pt;
                    font-family: 'Courier New';
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: {ACCENT};
                }}
                QPushButton:pressed {{
                    background: #0055aa;
                }}
            """)
            self._ip_input.setReadOnly(False)
            self._log_msg("[ CONNECTION LOST ]")

    def _on_conn_btn_clicked(self):
        """Handle connect/disconnect button click."""
        if self._connected:
            # Disconnect
            self.connection_requested.emit(self._ip_input.text(), False)
        else:
            # Connect
            ip_addr = self._ip_input.text().strip()
            if ip_addr:
                self.connection_requested.emit(ip_addr, True)
            else:
                self._log_msg("[ ERROR: Invalid IP address ]")
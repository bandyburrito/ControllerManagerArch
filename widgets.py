"""Custom widgets — controller cards, analog stick / trigger / button visualizers."""

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QProgressBar,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush

from backend import Controller, BRAND_COLORS, BRAND_ICONS


# ---------------------------------------------------------------------------
# Controller card for the main list
# ---------------------------------------------------------------------------

class ControllerCard(QFrame):
    test_clicked = pyqtSignal(object)

    def __init__(self, ctrl: Controller, parent=None):
        super().__init__(parent)
        self.ctrl = ctrl
        self._build()

    def _build(self):
        color = BRAND_COLORS.get(self.ctrl.brand, "#6C63FF")
        self.setObjectName("card")
        self.setStyleSheet(f"""
            QFrame#card {{
                background: #1E1E1E;
                border: 2px solid {color};
                border-radius: 12px;
            }}
            QFrame#card:hover {{ background: #252525; }}
        """)

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(16)

        # Badge
        badge = QFrame()
        badge.setFixedSize(56, 56)
        badge.setStyleSheet(f"background:{color}; border-radius:12px; border:none;")
        bl = QVBoxLayout(badge)
        bl.setContentsMargins(0, 0, 0, 0)
        icon = QLabel(BRAND_ICONS.get(self.ctrl.brand, "GP"))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("color:#fff; font-size:22px; font-weight:bold; border:none;")
        bl.addWidget(icon)
        root.addWidget(badge)

        # Info column
        info = QVBoxLayout()
        info.setSpacing(3)

        name = QLabel(self.ctrl.friendly_name)
        name.setStyleSheet("color:#fff; font-size:15px; font-weight:bold; border:none;")
        info.addWidget(name)

        brand_label = QLabel(self.ctrl.brand.capitalize())
        brand_label.setStyleSheet(f"color:{color}; font-size:11px; font-weight:bold; border:none;")
        info.addWidget(brand_label)

        meta = f"{self.ctrl.connection}  ·  {self.ctrl.path}"
        meta_l = QLabel(meta)
        meta_l.setStyleSheet("color:#777; font-size:10px; border:none;")
        info.addWidget(meta_l)

        ids = QLabel(f"VID {self.ctrl.vendor:04X}  PID {self.ctrl.product:04X}")
        ids.setStyleSheet("color:#555; font-size:10px; font-family:monospace; border:none;")
        info.addWidget(ids)

        root.addLayout(info, stretch=1)

        # Right column: battery + test button
        right = QVBoxLayout()
        right.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        right.setSpacing(8)

        if self.ctrl.battery_percent is not None:
            pct = self.ctrl.battery_percent
            bc = "#4caf50" if pct > 50 else "#ff9800" if pct > 20 else "#f44336"
            bl2 = QVBoxLayout()
            bl2.setSpacing(2)
            pct_l = QLabel(f"{pct}%")
            pct_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pct_l.setStyleSheet(f"color:{bc}; font-size:13px; font-weight:bold; border:none;")
            bl2.addWidget(pct_l)
            bar = QProgressBar()
            bar.setValue(pct)
            bar.setFixedSize(80, 6)
            bar.setTextVisible(False)
            bar.setStyleSheet(f"""
                QProgressBar {{ background:#333; border-radius:3px; border:none; }}
                QProgressBar::chunk {{ background:{bc}; border-radius:3px; }}
            """)
            bl2.addWidget(bar, alignment=Qt.AlignmentFlag.AlignCenter)
            if self.ctrl.battery_status:
                st = QLabel(self.ctrl.battery_status)
                st.setAlignment(Qt.AlignmentFlag.AlignCenter)
                st.setStyleSheet("color:#666; font-size:9px; border:none;")
                bl2.addWidget(st)
            right.addLayout(bl2)

        btn = QPushButton("Test Input")
        btn.setFixedWidth(100)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background:{color}; color:#fff; border:none;
                border-radius:6px; padding:8px 0; font-size:12px; font-weight:bold;
            }}
            QPushButton:hover {{ background:{color}dd; }}
            QPushButton:pressed {{ background:{color}aa; }}
        """)
        btn.clicked.connect(lambda: self.test_clicked.emit(self.ctrl))
        right.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        root.addLayout(right)


# ---------------------------------------------------------------------------
# Analog stick visualizer
# ---------------------------------------------------------------------------

class StickVis(QFrame):
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._label = label
        self.x = 0.0
        self.y = 0.0
        self.setFixedSize(130, 150)

    def set_pos(self, x: float, y: float):
        self.x = max(-1.0, min(1.0, x))
        self.y = max(-1.0, min(1.0, y))
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        p.setPen(QColor("#bbb"))
        p.drawText(0, 14, self.width(), 16, Qt.AlignmentFlag.AlignCenter, self._label)

        cx, cy, r = 65, 85, 48
        p.setPen(QPen(QColor("#444"), 2))
        p.setBrush(QBrush(QColor("#111")))
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        p.setPen(QPen(QColor("#282828"), 1))
        p.drawLine(cx - r, cy, cx + r, cy)
        p.drawLine(cx, cy - r, cx, cy + r)

        dx = cx + int(self.x * (r - 6))
        dy = cy + int(self.y * (r - 6))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#4fc3f7")))
        p.drawEllipse(dx - 7, dy - 7, 14, 14)
        p.end()


# ---------------------------------------------------------------------------
# Trigger bar
# ---------------------------------------------------------------------------

class TriggerVis(QFrame):
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._label = label
        self.val = 0.0
        self.setFixedSize(50, 150)

    def set_val(self, v: float):
        self.val = max(0.0, min(1.0, v))
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        p.setPen(QColor("#bbb"))
        p.drawText(0, 14, self.width(), 16, Qt.AlignmentFlag.AlignCenter, self._label)

        bx, by, bw, bh = 10, 30, 30, 105
        p.setPen(QPen(QColor("#444"), 2))
        p.setBrush(QBrush(QColor("#111")))
        p.drawRoundedRect(bx, by, bw, bh, 4, 4)

        fh = int(self.val * (bh - 4))
        if fh > 0:
            c = QColor("#ff7043") if self.val > 0.8 else QColor("#66bb6a")
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(c))
            p.drawRoundedRect(bx + 2, by + bh - 2 - fh, bw - 4, fh, 3, 3)
        p.end()


# ---------------------------------------------------------------------------
# D-Pad visualizer
# ---------------------------------------------------------------------------

class DPadVis(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hx = 0  # -1, 0, 1
        self.hy = 0
        self.setFixedSize(100, 150)

    def set_dir(self, hx: int, hy: int):
        self.hx = hx
        self.hy = hy
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        p.setPen(QColor("#bbb"))
        p.drawText(0, 14, self.width(), 16, Qt.AlignmentFlag.AlignCenter, "D-Pad")

        cx, cy, s = 50, 88, 18
        off = QColor("#1a1a1a")
        on = QColor("#4fc3f7")
        border = QPen(QColor("#444"), 1)

        dirs = [
            (0, -1, cx - s // 2, cy - s - s // 2 - 2, s, s),  # up
            (0, 1, cx - s // 2, cy + s // 2 + 2, s, s),         # down
            (-1, 0, cx - s - s // 2 - 2, cy - s // 2, s, s),   # left
            (1, 0, cx + s // 2 + 2, cy - s // 2, s, s),         # right
        ]
        # center square
        p.setPen(border)
        p.setBrush(QBrush(off))
        p.drawRoundedRect(cx - s // 2, cy - s // 2, s, s, 3, 3)

        for dx, dy, rx, ry, rw, rh in dirs:
            active = (self.hx == dx and dx != 0) or (self.hy == dy and dy != 0)
            p.setPen(border)
            p.setBrush(QBrush(on if active else off))
            p.drawRoundedRect(rx, ry, rw, rh, 3, 3)

        p.end()


# ---------------------------------------------------------------------------
# Button indicator
# ---------------------------------------------------------------------------

class ButtonDot(QFrame):
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._label = label
        self.pressed = False
        self.setFixedSize(80, 32)

    def set_pressed(self, v: bool):
        self.pressed = v
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        r = 8
        cy = 16
        if self.pressed:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor("#4fc3f7")))
        else:
            p.setPen(QPen(QColor("#444"), 2))
            p.setBrush(QBrush(QColor("#111")))
        p.drawEllipse(4, cy - r, r * 2, r * 2)

        p.setPen(QColor("#ddd") if self.pressed else QColor("#888"))
        f = p.font()
        f.setPointSize(8)
        p.setFont(f)
        p.drawText(24, 4, 54, 24, Qt.AlignmentFlag.AlignVCenter, self._label)
        p.end()

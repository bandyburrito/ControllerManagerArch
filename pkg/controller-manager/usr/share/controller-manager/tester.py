"""Live input test dialog — reads evdev events and shows them visually."""

import threading

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QGridLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject

import evdev

from backend import Controller
from widgets import StickVis, TriggerVis, DPadVis, ButtonDot

BTN_LABELS = {
    0x130: "A / ✕",
    0x131: "B / ○",
    0x132: "X / □",
    0x133: "Y / △",
    0x134: "LB / L1",
    0x135: "RB / R1",
    0x136: "LT / L2",
    0x137: "RT / R2",
    0x138: "Back / Share",
    0x139: "Start / Opt",
    0x13A: "L3",
    0x13B: "R3",
    0x13C: "Home / PS",
    0x13D: "Misc",
    0x220: "D-Up",
    0x221: "D-Down",
    0x222: "D-Left",
    0x223: "D-Right",
    0x120: "Trigger",
    0x121: "Thumb",
    0x122: "Thumb2",
    0x123: "Top",
    0x124: "Top2",
    0x125: "Pinkie",
    0x126: "Base",
    0x127: "Base2",
    0x128: "Base3",
    0x129: "Base4",
}

AXIS_LABELS = {
    0x00: "LX", 0x01: "LY",
    0x02: "LT/Z", 0x03: "RX",
    0x04: "RY", 0x05: "RT/RZ",
    0x10: "Hat0X", 0x11: "Hat0Y",
}


class _Signals(QObject):
    btn = pyqtSignal(int, bool)
    axis = pyqtSignal(int, float)


class InputTesterDialog(QDialog):
    def __init__(self, ctrl: Controller, parent=None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.setWindowTitle(f"Test — {ctrl.friendly_name}")
        self.setMinimumSize(720, 520)
        self._sig = _Signals()
        self._sig.btn.connect(self._on_btn)
        self._sig.axis.connect(self._on_axis)
        self._btn_widgets: dict[int, ButtonDot] = {}
        self._axis_ranges: dict[int, tuple[int, int]] = {}
        self._running = False
        self._dev = None
        self._dpad_x = 0
        self._dpad_y = 0
        self._setup_style()
        self._build_ui()
        self._start()

    def _setup_style(self):
        self.setStyleSheet("""
            QDialog { background: #121212; }
            QGroupBox {
                color: #ccc; font-weight: bold;
                border: 1px solid #333; border-radius: 8px;
                margin-top: 14px; padding-top: 18px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 12px; padding: 0 6px;
            }
        """)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(20, 16, 20, 12)

        hdr = QLabel(self.ctrl.friendly_name)
        hdr.setStyleSheet("color:#fff; font-size:17px; font-weight:bold;")
        hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(hdr)

        sub = QLabel("Move sticks and press buttons — changes show in real time")
        sub.setStyleSheet("color:#666; font-size:11px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(sub)

        # Analog group
        ag = QGroupBox("Sticks / Triggers")
        ah = QHBoxLayout(ag)
        ah.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ah.setSpacing(16)

        self._lt = TriggerVis("LT")
        self._ls = StickVis("Left Stick")
        self._dpad = DPadVis()
        self._rs = StickVis("Right Stick")
        self._rt = TriggerVis("RT")

        for w in (self._lt, self._ls, self._dpad, self._rs, self._rt):
            ah.addWidget(w)
        root.addWidget(ag)

        # Buttons group
        bg = QGroupBox("Buttons")
        self._btn_grid = QGridLayout(bg)
        self._btn_grid.setSpacing(4)
        root.addWidget(bg)

        self._status = QLabel("Opening device…")
        self._status.setStyleSheet("color:#555; font-size:10px;")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._status)

    def _start(self):
        try:
            self._dev = evdev.InputDevice(self.ctrl.path)
        except (PermissionError, OSError) as e:
            self._status.setText(
                f"Cannot open {self.ctrl.path}: {e}\n"
                "Fix: sudo usermod -aG input $USER  (then re-login)"
            )
            self._status.setStyleSheet("color:#f44336; font-size:11px;")
            return

        caps = self._dev.capabilities(verbose=False)

        # Build button widgets
        col = row = 0
        for code in sorted(caps.get(evdev.ecodes.EV_KEY, [])):
            label = BTN_LABELS.get(code, f"0x{code:03X}")
            w = ButtonDot(label)
            self._btn_widgets[code] = w
            self._btn_grid.addWidget(w, row, col)
            col += 1
            if col >= 6:
                col = 0
                row += 1

        # Store axis ranges
        for item in caps.get(evdev.ecodes.EV_ABS, []):
            code, ai = (item if isinstance(item, tuple) else (item, self._dev.absinfo(item)))
            self._axis_ranges[code] = (ai.min, ai.max)

        self._status.setText("Reading…")
        self._status.setStyleSheet("color:#4caf50; font-size:10px;")
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        try:
            for ev in self._dev.read_loop():
                if not self._running:
                    break
                if ev.type == evdev.ecodes.EV_KEY:
                    self._sig.btn.emit(ev.code, ev.value != 0)
                elif ev.type == evdev.ecodes.EV_ABS:
                    mn, mx = self._axis_ranges.get(ev.code, (0, 255))
                    span = mx - mn
                    norm = (ev.value - mn) / span * 2.0 - 1.0 if span else 0.0
                    self._sig.axis.emit(ev.code, norm)
        except OSError:
            pass

    # --- slots ----

    def _on_btn(self, code: int, pressed: bool):
        w = self._btn_widgets.get(code)
        if w:
            w.set_pressed(pressed)
        label = BTN_LABELS.get(code, f"0x{code:03X}")
        self._status.setText(f"{label} {'pressed' if pressed else 'released'}")

    def _on_axis(self, code: int, v: float):
        if code == 0x00:
            self._ls.set_pos(v, self._ls.y)
        elif code == 0x01:
            self._ls.set_pos(self._ls.x, v)
        elif code == 0x03:
            self._rs.set_pos(v, self._rs.y)
        elif code == 0x04:
            self._rs.set_pos(self._rs.x, v)
        elif code == 0x02:
            self._lt.set_val((v + 1.0) / 2.0)
        elif code == 0x05:
            self._rt.set_val((v + 1.0) / 2.0)
        elif code == 0x10:
            self._dpad_x = round(v)
            self._dpad.set_dir(self._dpad_x, self._dpad_y)
        elif code == 0x11:
            self._dpad_y = round(v)
            self._dpad.set_dir(self._dpad_x, self._dpad_y)

        label = AXIS_LABELS.get(code, f"0x{code:02X}")
        self._status.setText(f"{label}: {v:+.2f}")

    def closeEvent(self, ev):
        self._running = False
        if self._dev:
            try:
                self._dev.close()
            except Exception:
                pass
        super().closeEvent(ev)

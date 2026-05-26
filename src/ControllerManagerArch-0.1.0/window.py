"""Main application window — lists controllers, handles hotplug, opens tester."""

import os

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject

from backend import Controller, detect_controllers, DeviceMonitor
from widgets import ControllerCard
from tester import InputTesterDialog

STYLE = """
QMainWindow { background: #121212; }
QScrollArea  { border: none; background: #121212; }
QWidget      { background: #121212; }
QScrollBar:vertical {
    background: #1a1a1a; width: 8px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #333; min-height: 30px; border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


class _HotplugBridge(QObject):
    changed = pyqtSignal()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Controller Manager")
        self.setMinimumSize(820, 600)
        self.resize(920, 660)
        self.setStyleSheet(STYLE)

        self._controllers: list[Controller] = []
        self._bridge = _HotplugBridge()
        self._bridge.changed.connect(self._on_hotplug)

        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(350)
        self._debounce.timeout.connect(self._refresh)

        self._build_ui()
        self._monitor = DeviceMonitor(callback=self._bridge.changed.emit)
        self._monitor.start()
        self._refresh()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(28, 24, 28, 18)
        root.setSpacing(14)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("Controller Manager")
        title.setStyleSheet("color:#fff; font-size:22px; font-weight:bold;")
        hdr.addWidget(title)

        hdr.addStretch()

        self._count = QLabel()
        self._count.setStyleSheet("color:#777; font-size:13px;")
        hdr.addWidget(self._count)

        ref = QPushButton("Refresh")
        ref.setCursor(Qt.CursorShape.PointingHandCursor)
        ref.setStyleSheet("""
            QPushButton {
                background:#252525; color:#ccc; border:1px solid #444;
                border-radius:6px; padding:7px 20px; font-size:12px;
            }
            QPushButton:hover { background:#333; }
        """)
        ref.clicked.connect(self._refresh)
        hdr.addWidget(ref)
        root.addLayout(hdr)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background:#2a2a2a;")
        sep.setFixedHeight(1)
        root.addWidget(sep)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._list = QWidget()
        self._list_layout = QVBoxLayout(self._list)
        self._list_layout.setContentsMargins(0, 0, 8, 0)
        self._list_layout.setSpacing(10)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self._list)
        root.addWidget(scroll, stretch=1)

        # Footer
        self._footer = QLabel()
        self._footer.setStyleSheet("color:#555; font-size:10px;")
        self._footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._footer)

    # -------------------------------------------------------------- Logic

    def _on_hotplug(self):
        self._debounce.start()

    def _refresh(self):
        self._controllers = detect_controllers()

        # Clear cards
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        n = len(self._controllers)
        self._count.setText(f"{n} controller{'s' if n != 1 else ''}")

        if n == 0:
            self._show_empty()
        else:
            for c in self._controllers:
                card = ControllerCard(c)
                card.test_clicked.connect(self._test)
                self._list_layout.addWidget(card)

        self._footer.setText(f"{n} detected  ·  monitoring for hotplug events")

    def _show_empty(self):
        box = QFrame()
        box.setStyleSheet("""
            QFrame { background:#161616; border:2px dashed #2a2a2a; border-radius:12px; }
        """)
        vb = QVBoxLayout(box)
        vb.setContentsMargins(40, 50, 40, 50)
        vb.setAlignment(Qt.AlignmentFlag.AlignCenter)

        big = QLabel("No controllers detected")
        big.setStyleSheet("color:#777; font-size:17px; font-weight:bold; border:none;")
        big.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vb.addWidget(big)

        hint = QLabel(
            "Connect a gamepad via USB or Bluetooth.\n"
            "It will appear here automatically."
        )
        hint.setStyleSheet("color:#444; font-size:12px; border:none;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vb.addWidget(hint)

        if not os.access("/dev/input/event0", os.R_OK):
            perm = QLabel(
                "\nFor full features (live input testing), add yourself\n"
                "to the input group:  sudo usermod -aG input $USER\n"
                "Then log out and back in."
            )
            perm.setStyleSheet("color:#ff9800; font-size:11px; border:none;")
            perm.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vb.addWidget(perm)

        self._list_layout.addWidget(box)

    def _test(self, ctrl: Controller):
        if not os.access(ctrl.path, os.R_OK):
            QMessageBox.warning(
                self, "Permission Denied",
                f"Cannot open {ctrl.path}.\n\n"
                "Run:  sudo usermod -aG input $USER\n"
                "Then log out and log back in.",
            )
            return
        dlg = InputTesterDialog(ctrl, parent=self)
        dlg.exec()

    def closeEvent(self, ev):
        self._monitor.stop()
        super().closeEvent(ev)

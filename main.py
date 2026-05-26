#!/usr/bin/env python3
"""Controller Manager for Linux — shows connected game controllers with live input testing."""

import sys
from PyQt6.QtWidgets import QApplication
from window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Controller Manager")
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

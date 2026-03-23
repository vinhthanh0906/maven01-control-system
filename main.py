"""
IoT Rover Monitor & Control — Main Entry Point
Run: python main.py
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from monitor import RoverApp


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark palette
    from PyQt5.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.Window,          QColor(30, 32, 40))
    palette.setColor(QPalette.WindowText,      QColor(220, 220, 225))
    palette.setColor(QPalette.Base,            QColor(22, 24, 30))
    palette.setColor(QPalette.AlternateBase,   QColor(38, 40, 50))
    palette.setColor(QPalette.ToolTipBase,     QColor(255, 255, 220))
    palette.setColor(QPalette.ToolTipText,     QColor(0, 0, 0))
    palette.setColor(QPalette.Text,            QColor(220, 220, 225))
    palette.setColor(QPalette.Button,          QColor(45, 48, 60))
    palette.setColor(QPalette.ButtonText,      QColor(220, 220, 225))
    palette.setColor(QPalette.BrightText,      Qt.red)
    palette.setColor(QPalette.Highlight,       QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

    window = RoverApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
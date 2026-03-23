"""
IoT Rover Monitor & Control — Main Entry Point
Run: python main.py
"""

"""
IoT Rover Monitor & Control — Main Entry Point
Run: python main.py
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from monitor import RoverApp


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark palette
    from PyQt6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(30, 32, 40))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(220, 220, 225))
    palette.setColor(QPalette.ColorRole.Base,            QColor(22, 24, 30))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(38, 40, 50))
    palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor(255, 255, 220))
    palette.setColor(QPalette.ColorRole.ToolTipText,     QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Text,            QColor(220, 220, 225))
    palette.setColor(QPalette.ColorRole.Button,          QColor(45, 48, 60))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(220, 220, 225))
    palette.setColor(QPalette.ColorRole.BrightText,      Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(palette)

    window = RoverApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
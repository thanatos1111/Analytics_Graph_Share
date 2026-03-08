"""
Analytics Graph Share — load xlsx time-series data, plot with multi-Y axes, export to HTML.
"""
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    # Helps QWebEngineView render correctly on some systems
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
    app = QApplication(sys.argv)
    app.setApplicationName("Analytics Graph Share")
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

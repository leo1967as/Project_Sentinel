"""
Project Sentinel - PySide6 GUI Application
Entry point for the trading guardian dashboard.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from gui.main_window import SentinelMainWindow
from gui.theme import ThemeManager


def main() -> None:
    """Application entry point"""
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("Project Sentinel")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Sentinel")
    
    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Apply theme
    theme = ThemeManager()
    theme.apply_dark_theme(app)
    
    # Create and show main window
    window = SentinelMainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

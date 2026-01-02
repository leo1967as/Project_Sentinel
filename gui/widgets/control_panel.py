"""
Control Panel Widget - Start/Stop/Emergency/Reset/Settings buttons
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PySide6.QtCore import Signal


class ControlPanel(QWidget):
    """Control buttons panel with Reset and Settings"""
    
    # Signals
    start_clicked = Signal()
    stop_clicked = Signal()
    emergency_clicked = Signal()
    reset_clicked = Signal()
    settings_clicked = Signal()
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._is_running = False
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Start button
        self.start_btn = QPushButton("▶ Start Monitoring")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self.start_clicked.emit)
        layout.addWidget(self.start_btn)
        
        # Stop button  
        self.stop_btn = QPushButton("⏹ Stop Monitoring")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        layout.addWidget(self.stop_btn)
        
        # Reset P&L button
        self.reset_btn = QPushButton("🔄 Reset P&L (Exit Block)")
        self.reset_btn.setMinimumHeight(36)
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #1f3460;
                border: 2px solid #ffd32a;
                color: #ffd32a;
            }
            QPushButton:hover {
                background-color: #ffd32a;
                color: #1a1a2e;
            }
        """)
        self.reset_btn.clicked.connect(self.reset_clicked.emit)
        layout.addWidget(self.reset_btn)
        
        # Emergency button
        self.emergency_btn = QPushButton("🚨 EMERGENCY CLOSE ALL")
        self.emergency_btn.setObjectName("emergency")
        self.emergency_btn.setMinimumHeight(50)
        self.emergency_btn.clicked.connect(self.emergency_clicked.emit)
        layout.addWidget(self.emergency_btn)
        
        # Settings button
        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.setMinimumHeight(36)
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self.settings_btn)
    
    def set_running(self, is_running: bool) -> None:
        """Update button states based on running status"""
        self._is_running = is_running
        self.start_btn.setEnabled(not is_running)
        self.stop_btn.setEnabled(is_running)
    
    def set_emergency_enabled(self, enabled: bool) -> None:
        """Enable/disable emergency button"""
        self.emergency_btn.setEnabled(enabled)
    
    def set_reset_enabled(self, enabled: bool) -> None:
        """Enable/disable reset button"""
        self.reset_btn.setEnabled(enabled)


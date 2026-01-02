"""
Mode Indicator Widget - NORMAL/BLOCK mode display
"""

from datetime import datetime
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Signal, Slot, QTimer


class ModeIndicatorWidget(QFrame):
    """Trading mode indicator with timer"""
    
    # Signals
    mode_clicked = Signal()
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._mode = "NORMAL"
        self._block_since: datetime = None
        self._setup_ui()
        
        # Timer for block mode duration
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_timer)
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Mode label
        self.mode_label = QLabel("NORMAL MODE")
        self.mode_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #00ff88;
            padding: 8px;
        """)
        layout.addWidget(self.mode_label)
        
        # Duration label (for block mode)
        self.duration_label = QLabel("")
        self.duration_label.setObjectName("subtitle")
        self.duration_label.setVisible(False)
        layout.addWidget(self.duration_label)
    
    @Slot(str, object)
    def set_mode(self, mode: str, since: datetime = None) -> None:
        """Set current trading mode"""
        self._mode = mode
        self._block_since = since
        
        if mode == "NORMAL":
            self.mode_label.setText("✅ NORMAL MODE")
            self.mode_label.setStyleSheet("""
                font-size: 18px;
                font-weight: bold;
                color: #00ff88;
                padding: 8px;
            """)
            self.setStyleSheet("background-color: rgba(0, 255, 136, 0.1);")
            self.duration_label.setVisible(False)
            self._timer.stop()
        else:
            self.mode_label.setText("🚫 BLOCK MODE")
            self.mode_label.setStyleSheet("""
                font-size: 18px;
                font-weight: bold;
                color: #ff4757;
                padding: 8px;
            """)
            self.setStyleSheet("background-color: rgba(255, 71, 87, 0.2);")
            self.duration_label.setVisible(True)
            self._timer.start(1000)
            self._update_timer()
    
    def _update_timer(self) -> None:
        """Update block duration display"""
        if self._block_since:
            duration = datetime.now() - self._block_since
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            seconds = int(duration.total_seconds() % 60)
            self.duration_label.setText(
                f"Blocked for: {hours:02d}:{minutes:02d}:{seconds:02d}"
            )
        else:
            self.duration_label.setText("Blocked")

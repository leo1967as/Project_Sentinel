"""
Tick Stats Widget - Tick collection statistics display
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Slot


class TickStatsWidget(QWidget):
    """Tick collection statistics display"""
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("📊 Tick Collection")
        title.setObjectName("title")
        layout.addWidget(title)
        
        # Stats grid
        stats_layout = QHBoxLayout()
        
        # Total ticks
        total_col = QVBoxLayout()
        total_col.addWidget(QLabel("Total Ticks"))
        self.total_label = QLabel("0")
        self.total_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #00d4ff;")
        total_col.addWidget(self.total_label)
        stats_layout.addLayout(total_col)
        
        # Rate
        rate_col = QVBoxLayout()
        rate_col.addWidget(QLabel("Rate/min"))
        self.rate_label = QLabel("0")
        self.rate_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        rate_col.addWidget(self.rate_label)
        stats_layout.addLayout(rate_col)
        
        # Buffer
        buffer_col = QVBoxLayout()
        buffer_col.addWidget(QLabel("Buffer"))
        self.buffer_label = QLabel("0/1000")
        self.buffer_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        buffer_col.addWidget(self.buffer_label)
        stats_layout.addLayout(buffer_col)
        
        layout.addLayout(stats_layout)
        layout.addStretch()
    
    @Slot(dict)
    def update_stats(self, stats: dict) -> None:
        """Update statistics display"""
        self.total_label.setText(f"{stats.get('total', 0):,}")
        self.rate_label.setText(f"{stats.get('rate', 0):.1f}")
    
    @Slot(int, int)
    def update_buffer(self, current: int, max_size: int) -> None:
        """Update buffer status"""
        self.buffer_label.setText(f"{current}/{max_size}")

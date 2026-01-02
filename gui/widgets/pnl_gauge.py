"""
PnL Gauge Widget - Visual gauge showing P&L vs threshold
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Signal, Slot


class PnLGaugeWidget(QWidget):
    """Visual P&L gauge with threshold marker"""
    
    # Signals
    threshold_clicked = Signal()
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._threshold = -300.0
        self._current_pnl = 0.0
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("📊 Daily P&L")
        title.setObjectName("title")
        layout.addWidget(title)
        
        # P&L value
        self.pnl_label = QLabel("$0.00")
        self.pnl_label.setStyleSheet("""
            font-size: 36px;
            font-weight: bold;
            color: #00d4ff;
        """)
        layout.addWidget(self.pnl_label)
        
        # Progress bar (negative indicates danger)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(-500)
        self.progress_bar.setMaximum(200)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimumHeight(20)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #2d3436;
                border-radius: 10px;
                background-color: #1f3460;
            }
            QProgressBar::chunk {
                border-radius: 10px;
                background-color: #00ff88;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Threshold label
        self.threshold_label = QLabel(f"Threshold: ${self._threshold:.0f}")
        self.threshold_label.setObjectName("subtitle")
        layout.addWidget(self.threshold_label)
        
        layout.addStretch()
    
    @Slot(float)
    def set_value(self, pnl: float) -> None:
        """Update P&L value"""
        self._current_pnl = pnl
        self.pnl_label.setText(f"${pnl:+.2f}")
        
        # Update color based on value
        if pnl >= 0:
            color = "#00ff88"  # Green
        elif pnl > self._threshold:
            color = "#ffd32a"  # Yellow
        else:
            color = "#ff4757"  # Red
        
        self.pnl_label.setStyleSheet(f"""
            font-size: 36px;
            font-weight: bold;
            color: {color};
        """)
        
        # Update progress bar
        self.progress_bar.setValue(int(pnl))
        
        # Change progress bar color
        chunk_color = color
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #2d3436;
                border-radius: 10px;
                background-color: #1f3460;
            }}
            QProgressBar::chunk {{
                border-radius: 10px;
                background-color: {chunk_color};
            }}
        """)
    
    def set_threshold(self, threshold: float) -> None:
        """Set the loss threshold"""
        self._threshold = threshold
        self.threshold_label.setText(f"Threshold: ${threshold:.0f}")

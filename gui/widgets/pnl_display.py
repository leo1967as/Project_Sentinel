"""
PnL Display Widget - Clean, large text-based P&L display
Replaces confusing QProgressBar with simple color-coded text
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt


class PnLDisplayWidget(QFrame):
    """
    Large P&L display with color coding.
    
    Colors:
    - Green: Positive P&L
    - Yellow: Negative but above threshold
    - Red: At or below threshold (danger zone)
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            PnLDisplayWidget {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        
        # Title
        self.title = QLabel("Daily P&L")
        self.title.setStyleSheet("color: #8b949e; font-size: 12px; font-weight: bold;")
        self.title.setAlignment(Qt.AlignCenter)
        
        # Main value
        self.value_label = QLabel("$0.00")
        self.value_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #00ff88;")
        self.value_label.setAlignment(Qt.AlignCenter)
        
        # Threshold indicator
        self.threshold_label = QLabel("Limit: $-500.00")
        self.threshold_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        self.threshold_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.title)
        layout.addWidget(self.value_label)
        layout.addWidget(self.threshold_label)
        
        self._threshold = -500.0
    
    def set_threshold(self, threshold: float):
        """Set the danger threshold"""
        self._threshold = threshold
        self.threshold_label.setText(f"Limit: ${threshold:,.2f}")
    
    def update_pnl(self, pnl: float):
        """Update display with color based on value"""
        # Determine color
        if pnl >= 0:
            color = "#00ff88"  # Green - profit
            bg_color = "#0d1f17"
        elif pnl > self._threshold:
            color = "#ffd60a"  # Yellow - loss but safe
            bg_color = "#1f1d0d"
        else:
            color = "#ff4757"  # Red - danger zone
            bg_color = "#1f0d0d"
        
        self.value_label.setText(f"${pnl:+,.2f}")
        self.value_label.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {color};")
        self.setStyleSheet(f"""
            PnLDisplayWidget {{
                background-color: {bg_color};
                border: 2px solid {color};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
    
    def setValue(self, pnl: float):
        """Alias for compatibility with existing code"""
        self.update_pnl(pnl)


if __name__ == "__main__":
    # Quick test
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    widget = PnLDisplayWidget()
    widget.set_threshold(-300)
    widget.update_pnl(-150.50)
    widget.show()
    sys.exit(app.exec())

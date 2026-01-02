"""
Quick Stats Card - Balance/Equity summary display
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Slot


class QuickStatsCard(QFrame):
    """Quick statistics display card"""
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Title
        title = QLabel("💰 Account Stats")
        title.setObjectName("title")
        layout.addWidget(title)
        
        # Balance row
        balance_row = QHBoxLayout()
        balance_row.addWidget(QLabel("Balance:"))
        self.balance_label = QLabel("$0.00")
        self.balance_label.setStyleSheet("font-weight: bold; color: #00d4ff;")
        balance_row.addWidget(self.balance_label)
        balance_row.addStretch()
        layout.addLayout(balance_row)
        
        # Equity row
        equity_row = QHBoxLayout()
        equity_row.addWidget(QLabel("Equity:"))
        self.equity_label = QLabel("$0.00")
        self.equity_label.setStyleSheet("font-weight: bold;")
        equity_row.addWidget(self.equity_label)
        equity_row.addStretch()
        layout.addLayout(equity_row)
        
        # Daily P&L row
        pnl_row = QHBoxLayout()
        pnl_row.addWidget(QLabel("Daily P&L:"))
        self.pnl_label = QLabel("$0.00")
        self.pnl_label.setStyleSheet("font-weight: bold;")
        pnl_row.addWidget(self.pnl_label)
        pnl_row.addStretch()
        layout.addLayout(pnl_row)
    
    @Slot(float, float)
    def update_stats(self, balance: float, equity: float) -> None:
        """Update balance and equity"""
        self.balance_label.setText(f"${balance:.2f}")
        self.equity_label.setText(f"${equity:.2f}")
    
    @Slot(float)
    def update_pnl(self, pnl: float) -> None:
        """Update daily P&L with color"""
        self.pnl_label.setText(f"${pnl:+.2f}")
        
        if pnl >= 0:
            self.pnl_label.setStyleSheet("font-weight: bold; color: #00ff88;")
        else:
            self.pnl_label.setStyleSheet("font-weight: bold; color: #ff4757;")

"""
Connection Card Widget - MT5 connection status display
"""

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PySide6.QtCore import Signal


class ConnectionCard(QFrame):
    """MT5 connection status card with reconnect button"""
    
    # Signals
    reconnect_clicked = Signal()
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Title
        title = QLabel("🔌 MT5 Connection")
        title.setObjectName("title")
        layout.addWidget(title)
        
        # Status row
        status_row = QHBoxLayout()
        
        self.status_icon = QLabel("●")
        self.status_icon.setStyleSheet("color: #ff4757; font-size: 16px;")
        status_row.addWidget(self.status_icon)
        
        self.status_label = QLabel("Disconnected")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        
        layout.addLayout(status_row)
        
        # Account info
        self.account_label = QLabel("Account: -")
        self.account_label.setObjectName("subtitle")
        layout.addWidget(self.account_label)
        
        self.server_label = QLabel("Server: -")
        self.server_label.setObjectName("subtitle")
        layout.addWidget(self.server_label)
        
        # Reconnect button
        self.reconnect_btn = QPushButton("Reconnect")
        self.reconnect_btn.clicked.connect(self.reconnect_clicked.emit)
        layout.addWidget(self.reconnect_btn)
    
    def set_connected(self, connected: bool, info: dict = None) -> None:
        """Update connection status"""
        if connected:
            self.status_icon.setStyleSheet("color: #00ff88; font-size: 16px;")
            self.status_label.setText("Connected")
            self.reconnect_btn.setEnabled(False)
            
            if info:
                self.account_label.setText(f"Account: {info.get('login', '-')}")
                self.server_label.setText(f"Server: {info.get('server', '-')}")
        else:
            self.status_icon.setStyleSheet("color: #ff4757; font-size: 16px;")
            self.status_label.setText("Disconnected")
            self.reconnect_btn.setEnabled(True)
            self.account_label.setText("Account: -")
            self.server_label.setText("Server: -")

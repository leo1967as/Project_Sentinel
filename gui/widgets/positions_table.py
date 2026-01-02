"""
Positions Table Widget - Live positions display
"""

from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QPushButton, QHBoxLayout, QWidget
)
from PySide6.QtCore import Signal, Slot, Qt


class PositionsTableWidget(QTableWidget):
    """Table showing open positions with close buttons"""
    
    # Signals
    # Use object (or str) to handle 64-bit MT5 tickets that overflow 32-bit C++ int
    close_requested = Signal(object)      # ticket
    close_all_requested = Signal()
    
    COLUMNS = ['Ticket', 'Symbol', 'Type', 'Volume', 'Price', 'Profit', 'Action']
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.verticalHeader().setVisible(False)
        
        # Column widths
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
    
    @Slot(list)
    def update_positions(self, positions: list) -> None:
        """Update table with new positions data"""
        self.setRowCount(len(positions))
        
        for row, pos in enumerate(positions):
            # Ticket
            self.setItem(row, 0, QTableWidgetItem(str(pos.get('ticket', '-'))))
            
            # Symbol
            self.setItem(row, 1, QTableWidgetItem(pos.get('symbol', '-')))
            
            # Type
            pos_type = pos.get('type', 'BUY')
            type_item = QTableWidgetItem(pos_type)
            type_item.setForeground(
                Qt.green if pos_type == 'BUY' else Qt.red
            )
            self.setItem(row, 2, type_item)
            
            # Volume
            self.setItem(row, 3, QTableWidgetItem(f"{pos.get('volume', 0):.2f}"))
            
            # Price
            self.setItem(row, 4, QTableWidgetItem(f"{pos.get('open_price', 0):.2f}"))
            
            # Profit
            profit = pos.get('profit', 0)
            profit_item = QTableWidgetItem(f"${profit:+.2f}")
            profit_item.setForeground(Qt.green if profit >= 0 else Qt.red)
            self.setItem(row, 5, profit_item)
            
            # Close button
            close_btn = QPushButton("Close")
            close_btn.setProperty("ticket", pos.get('ticket', 0))
            close_btn.clicked.connect(self._on_close_clicked)
            self.setCellWidget(row, 6, close_btn)
    
    def _on_close_clicked(self) -> None:
        """Handle close button click"""
        btn = self.sender()
        if btn:
            ticket = btn.property("ticket")
            if ticket:
                self.close_requested.emit(ticket)
    
    def clear_all(self) -> None:
        """Clear all rows"""
        self.setRowCount(0)

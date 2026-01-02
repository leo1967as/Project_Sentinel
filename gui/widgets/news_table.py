"""
News Table Widget - Upcoming economic news display
"""

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtCore import Slot, Qt


class NewsTableWidget(QTableWidget):
    """Table showing upcoming news events"""
    
    COLUMNS = ['Time', 'Currency', 'Impact', 'Event']
    
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
        header.setSectionResizeMode(3, QHeaderView.Stretch)
    
    @Slot(list)
    def update_news(self, news_list: list) -> None:
        """Update table with news events"""
        self.setRowCount(len(news_list))
        
        for row, news in enumerate(news_list):
            # Time
            time_str = news.get('event_time', '-')
            if hasattr(time_str, 'strftime'):
                time_str = time_str.strftime("%H:%M")
            self.setItem(row, 0, QTableWidgetItem(str(time_str)))
            
            # Currency
            self.setItem(row, 1, QTableWidgetItem(news.get('currency', '-')))
            
            # Impact
            impact = news.get('impact', 'Low')
            impact_item = QTableWidgetItem(impact)
            if impact == 'High':
                impact_item.setBackground(Qt.darkRed)
            elif impact == 'Medium':
                impact_item.setBackground(Qt.darkYellow)
            self.setItem(row, 2, impact_item)
            
            # Event name
            self.setItem(row, 3, QTableWidgetItem(news.get('event_name', '-')))

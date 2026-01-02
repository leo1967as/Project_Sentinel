
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QCalendarWidget, 
                               QLabel, QSplitter, QFrame, QPushButton, QProgressBar, QMessageBox)
from PySide6.QtCore import Qt, Signal, QDate, QRect
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush
from datetime import datetime

class PnLCalendarWidget(QCalendarWidget):
    """Calendar that paints cells based on daily PnL"""
    
    dateSelected = Signal(datetime)
    
    def __init__(self, journal_manager):
        super().__init__()
        self.manager = journal_manager
        self.data = {} # { 'YYYY-MM-DD': {'pnl': float, 'count': int, 'wins': int} }
        
        # Style
        self.setGridVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.NavigationBarVisible = True
        
        # Connect page change (month change)
        self.currentPageChanged.connect(self.fetch_monthly_data)
        self.clicked.connect(self._on_date_clicked)
        
        # Initial fetch (current month)
        self.fetch_monthly_data(self.yearShown(), self.monthShown())
        
    def fetch_monthly_data(self, year, month):
        try:
            self.data = self.manager.get_monthly_stats(year, month)
            self.updateCell(QDate(year, month, 1)) # Trigger repaint
            self.update()
        except Exception as e:
            print(f"Error fetching calendar data: {e}")
            
    def _on_date_clicked(self, date):
        dt = datetime(date.year(), date.month(), date.day())
        self.dateSelected.emit(dt)

    def paintCell(self, painter, rect, date):
        # 1. Default Painting (Background, Day Number)
        # super().paintCell(painter, rect, date) # This paints default selection too
        
        # We manually paint to control everything
        painter.save()
        
        # Background
        key = date.toString("yyyy-MM-dd")
        pnl = 0.0
        has_data = False
        
        if key in self.data:
            pnl = self.data[key]['pnl']
            has_data = True
            
            # Color logic
            if pnl > 0:
                bg_color = QColor(0, 50, 0, 150) # Dark Green
                text_color = QColor("#00ff88")
            elif pnl < 0:
                bg_color = QColor(50, 0, 0, 150) # Dark Red
                text_color = QColor("#ff4757")
            else:
                bg_color = QColor(50, 50, 50, 100)
                text_color = QColor("white")
                
            painter.fillRect(rect, bg_color)
        else:
            # No data or diff month?
            # If different month, dim it
            if date.month() != self.monthShown():
                painter.setOpacity(0.3)
                
        # Draw Day Number
        painter.setPen(Qt.white)
        painter.drawText(rect.adjusted(5, 5, -5, -5), Qt.AlignTop | Qt.AlignLeft, str(date.day()))
        
        # Draw PnL if exists
        if has_data:
            font = painter.font()
            font.setPointSize(8)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(text_color)
            
            pnl_str = f"{pnl:+.0f}"
            painter.drawText(rect.adjusted(5, 5, -5, -5), Qt.AlignCenter, pnl_str)
            
        # Draw Selection Border
        if date == self.selectedDate():
            painter.setPen(QPen(QColor("#3498db"), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect.adjusted(1, 1, -1, -1))
            
        painter.restore()

class HistoryTab(QWidget):
    """Tab for Viewing History and Calendar"""
    
    requestEditJournal = Signal(datetime) # Signal to switch tab
    
    def __init__(self, journal_manager):
        super().__init__()
        self.manager = journal_manager
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        
        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # Left: Calendar
        self.calendar = PnLCalendarWidget(self.manager)
        self.calendar.dateSelected.connect(self.update_stats_panel)
        splitter.addWidget(self.calendar)
        
        # Right: Stats Panel
        self.stats_panel = QFrame()
        self.stats_panel.setFrameShape(QFrame.StyledPanel)
        self.stats_panel.setStyleSheet("background-color: #1e1e1e; border-radius: 10px;")
        splitter.addWidget(self.stats_panel)
        
        self.setup_stats_panel()
        
        # Initial Update
        self.update_stats_panel(datetime.now())
        
    def setup_stats_panel(self):
        vbox = QVBoxLayout(self.stats_panel)
        
        # Header
        self.lbl_date = QLabel("Today")
        self.lbl_date.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        self.lbl_date.setAlignment(Qt.AlignCenter)
        vbox.addWidget(self.lbl_date)
        
        vbox.addSpacing(20)
        
        # Total PnL
        lbl_pnl_title = QLabel("Daily P&L")
        lbl_pnl_title.setStyleSheet("color: #888; font-size: 12px;")
        lbl_pnl_title.setAlignment(Qt.AlignCenter)
        vbox.addWidget(lbl_pnl_title)
        
        self.lbl_pnl = QLabel("$0.00")
        self.lbl_pnl.setStyleSheet("font-size: 32px; font-weight: bold; color: white;")
        self.lbl_pnl.setAlignment(Qt.AlignCenter)
        vbox.addWidget(self.lbl_pnl)
        
        vbox.addSpacing(20)
        
        # Stats Grid
        stats_layout = QHBoxLayout()
        
        # Trades
        self.lbl_trades = QLabel("Trades: 0")
        self.lbl_trades.setStyleSheet("color: white;")
        stats_layout.addWidget(self.lbl_trades)
        
        # Win Rate
        self.lbl_winrate = QLabel("Win Rate: 0%")
        self.lbl_winrate.setStyleSheet("color: white;")
        stats_layout.addWidget(self.lbl_winrate)
        
        vbox.addLayout(stats_layout)
        
        vbox.addStretch()
        
        # Actions
        btn_layout = QHBoxLayout()
        
        self.btn_edit = QPushButton("✏️ Edit Journal")
        self.btn_edit.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
        """)
        self.btn_edit.clicked.connect(self.on_edit_journal)
        
        self.btn_report = QPushButton("📄 Generate Report")
        self.btn_report.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.btn_report.clicked.connect(self.generate_report)
        
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_report)
        vbox.addLayout(btn_layout)
        
    def on_edit_journal(self):
        if self.selected_date:
            self.requestEditJournal.emit(self.selected_date)
        
    def update_stats_panel(self, date: datetime):
        self.selected_date = date
        date_str = date.strftime("%Y-%m-%d")
        self.lbl_date.setText(date.strftime("%A, %d %B %Y"))
        
        # Fetch data from calendar cache or manager
        # Use calendar cache for speed if available, or fetch fresh?
        # Calendar cache key is YYYY-MM-DD
        
        if date_str in self.calendar.data:
            stats = self.calendar.data[date_str]
            pnl = stats['pnl']
            count = stats['count']
            wins = stats.get('wins', 0)
            win_rate = (wins / count * 100) if count > 0 else 0
            
            color = "#00ff88" if pnl >= 0 else "#ff4757"
            self.lbl_pnl.setText(f"${pnl:,.2f}")
            self.lbl_pnl.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {color};")
            
            self.lbl_trades.setText(f"Trades: {count}")
            self.lbl_winrate.setText(f"Win Rate: {win_rate:.0f}%")
            self.btn_report.setEnabled(True)
        else:
            self.lbl_pnl.setText("$0.00")
            self.lbl_pnl.setStyleSheet("font-size: 32px; font-weight: bold; color: white;")
            self.lbl_trades.setText("Trades: 0")
            self.lbl_winrate.setText("Win Rate: 0%")
            self.btn_report.setEnabled(False) # No trades to report?
            
    def generate_report(self):
        try:
            # Call Manager to generate report
            # We assume JournalManager has this method or we need to implement it
            success = self.manager.generate_daily_report(self.selected_date)
            
            if success:
                QMessageBox.information(self, "Report Sent", f"Report for {self.selected_date.strftime('%Y-%m-%d')} sent to Discord!")
            else:
                QMessageBox.warning(self, "Report Failed", "Failed to generate or send report.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

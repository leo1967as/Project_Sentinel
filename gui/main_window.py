"""
Sentinel Main Window - INTEGRATED with Core Business Logic
Uses: TradingGuardian, DataCollector, DatabaseManager
"""

import sys
from datetime import datetime
from pathlib import Path
import MetaTrader5 as mt5

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTabWidget, QStatusBar,
    QLabel, QMessageBox, QPushButton
)
from PySide6.QtCore import Qt, Slot, QTimer, Signal, QThread
from PySide6.QtGui import QAction, QCloseEvent

from .widgets import (
    ConnectionCard, QuickStatsCard, ControlPanel,
    PnLDisplayWidget, PositionsTableWidget, ModeIndicatorWidget,
    TickStatsWidget, NewsTableWidget, LogViewerWidget,
    StagingTab
)
from .workers.report_worker import ReportGenWorker
from .dialogs import SettingsDialog

# Import CORE business logic
from active_block_monitor import TradingGuardian, GuardianState
from data_collector import DatabaseManager, TickCollector, NewsScraper
from config import get_config


# =============================================================================
# GUARDIAN WORKER - Real integration with TradingGuardian
# =============================================================================

class IntegratedGuardianWorker(QThread):
    """Worker that uses the REAL TradingGuardian logic"""
    
    # Signals
    pnl_updated = Signal(float)
    positions_changed = Signal(list)
    mode_changed = Signal(str, object)
    threshold_exceeded = Signal(float, float)
    position_closed = Signal(int, str, float)
    account_updated = Signal(dict)
    log = Signal(str, str)
    error = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._guardian = None
        self._config = get_config()
        self._bypass_threshold = False  # Flag to skip threshold check
    
    def set_bypass_threshold(self, bypass: bool):
        """Enable/disable threshold bypass"""
        self._bypass_threshold = bypass
        if bypass:
            self.log.emit("WARNING", "⚠️ Threshold check BYPASSED - trading allowed despite loss")
    
    def run(self):
        """Main monitoring loop using TradingGuardian"""
        self._running = True
        self.log.emit("INFO", "Starting Guardian Worker...")
        
        try:
            # Create Guardian instance
            self._guardian = TradingGuardian()
            
            if not self._guardian.connect():
                self.error.emit("Failed to connect to MT5")
                return
            
            self.log.emit("INFO", f"Guardian active (threshold: ${self._guardian.max_loss})")
            
            # Get threshold
            threshold = self._guardian.max_loss
            
            while self._running:
                # Update account info
                account = mt5.account_info()
                if account:
                    self.account_updated.emit({
                        'balance': account.balance,
                        'equity': account.equity,
                        'profit': account.profit
                    })
                
                # Get daily P&L (using Guardian's method - includes realized + unrealized)
                pnl = self._guardian.get_daily_pnl()
                self.pnl_updated.emit(pnl)
                
                # Get positions (already returns list of dicts)
                positions = self._guardian.get_positions()
                self.positions_changed.emit(positions)
                
                # Check mode (skip threshold check if bypass enabled)
                if self._bypass_threshold:
                    # Bypass mode - just monitor, don't trigger block
                    if not hasattr(self, '_last_mode') or self._last_mode != "BYPASS":
                        self.mode_changed.emit("NORMAL", None)
                        self._last_mode = "BYPASS"
                    self.msleep(5000)
                    
                elif self._guardian.state.is_trading_allowed:
                    if not hasattr(self, '_last_mode') or self._last_mode != "NORMAL":
                        self.mode_changed.emit("NORMAL", None)
                        self._last_mode = "NORMAL"
                    
                    # Run NORMAL mode check (this triggers auto-close if needed!)
                    self._guardian.run_normal_mode()
                    
                    # Check if mode changed after normal check
                    if not self._guardian.state.is_trading_allowed:
                        self.mode_changed.emit("BLOCK", 
                            self._guardian.state.block_triggered_time)
                        self._last_mode = "BLOCK"
                        self.threshold_exceeded.emit(pnl, threshold)
                        self.log.emit("WARNING", 
                            f"🚨 THRESHOLD EXCEEDED! P&L: ${pnl:.2f} (limit: ${threshold})")
                    
                    # Normal interval
                    self.msleep(5000)  # 5 seconds
                    
                else:
                    # BLOCK MODE - run block mode logic
                    self._guardian.run_block_mode()
                    self.msleep(500)  # 0.5 seconds in block mode
            
            self._guardian.disconnect()
            
        except Exception as e:
            self.error.emit(str(e))
            self.log.emit("ERROR", f"Guardian error: {e}")
        
        self.log.emit("INFO", "Guardian Worker stopped")
    
    def stop(self):
        """Stop the worker"""
        self._running = False
    
    def force_close_all(self):
        """Emergency close all positions"""
        if self._guardian:
            success, failed = self._guardian.close_all_positions()
            self.log.emit("WARNING", f"Emergency close: {success} closed, {failed} failed")
            return success, failed
        return 0, 0


# =============================================================================
# DATA WORKER - Real integration with DataCollector
# =============================================================================

class IntegratedDataWorker(QThread):
    """Worker for REAL tick collection"""
    
    stats_updated = Signal(dict)
    buffer_status = Signal(int, int)
    news_updated = Signal(list)
    log = Signal(str, str)
    
    BATCH_SIZE = 1000
    SYMBOL = "XAUUSDm"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._db = None
        self._buffer = []
        self._total_ticks = 0
        self._last_tick_time = 0
    
    def run(self):
        """Main collection loop with REAL tick collection + Trade sync"""
        self._running = True
        self.log.emit("INFO", "Starting Data Worker...")
        
        try:
            # Initialize database
            db_path = Path(__file__).parent.parent / "database" / "sentinel_data.db"
            self._db = DatabaseManager(db_path)
            
            # Initialize TradeCollector for auto-sync
            from data_collector import TradeCollector
            self._trade_collector = TradeCollector(self._db)
            last_trade_sync = datetime.now()
            TRADE_SYNC_INTERVAL = 60  # Sync trades every 60 seconds
            
            # Get initial stats
            stats = self._db.get_stats()
            self._total_ticks = stats.get('total_ticks', 0)
            self.stats_updated.emit({
                'total': self._total_ticks,
                'rate': 0
            })
            
            # Get upcoming news
            try:
                news = self._db.get_upcoming_news(hours_ahead=24)
                news_list = []
                for n in news:
                    news_list.append({
                        'event_time': n[0],
                        'currency': n[1],
                        'impact': n[2],
                        'event_name': n[3]
                    })
                self.news_updated.emit(news_list)
            except:
                pass
            
            tick_count_interval = 0
            last_stats_time = datetime.now()
            
            self.log.emit("INFO", f"Tick collection started for {self.SYMBOL}")
            self.log.emit("INFO", f"Trade sync enabled (every {TRADE_SYNC_INTERVAL}s)")
            
            while self._running:
                # Collect tick
                tick = mt5.symbol_info_tick(self.SYMBOL)
                if tick and tick.time > self._last_tick_time:
                    self._last_tick_time = tick.time
                    self._buffer.append({
                        'timestamp': datetime.fromtimestamp(tick.time),
                        'bid': tick.bid,
                        'ask': tick.ask,
                        'last': tick.last,
                        'volume': tick.volume,
                        'flags': tick.flags
                    })
                    tick_count_interval += 1
                
                # Update buffer status
                self.buffer_status.emit(len(self._buffer), self.BATCH_SIZE)
                
                # Flush buffer if full
                if len(self._buffer) >= self.BATCH_SIZE:
                    try:
                        inserted = self._db.insert_ticks(self._buffer)
                        self._total_ticks += inserted
                        self._buffer.clear()
                        self.log.emit("INFO", f"Flushed {inserted} ticks to DB")
                    except Exception as e:
                        self.log.emit("ERROR", f"DB flush error: {e}")
                
                # Update stats every 5 seconds
                now = datetime.now()
                if (now - last_stats_time).total_seconds() >= 5:
                    rate = tick_count_interval / 5.0 * 60  # per minute
                    self.stats_updated.emit({
                        'total': self._total_ticks + len(self._buffer),
                        'rate': rate
                    })
                    tick_count_interval = 0
                    last_stats_time = now
                
                # Auto-sync trades every TRADE_SYNC_INTERVAL seconds
                if (now - last_trade_sync).total_seconds() >= TRADE_SYNC_INTERVAL:
                    try:
                        synced = self._trade_collector.sync_trades()
                        if synced > 0:
                            self.log.emit("INFO", f"Auto-synced {synced} trades")
                    except Exception as e:
                        self.log.emit("ERROR", f"Trade sync error: {e}")
                    last_trade_sync = now
                
                self.msleep(100)  # 100ms polling
                
        except Exception as e:
            self.log.emit("ERROR", f"Data worker error: {e}")
        
        # Final flush
        if self._buffer and self._db:
            try:
                self._db.insert_ticks(self._buffer)
            except:
                pass
        
        self.log.emit("INFO", "Data Worker stopped")
    
    def stop(self):
        self._running = False


# =============================================================================
# MAIN WINDOW - FULLY INTEGRATED
# =============================================================================

class SentinelMainWindow(QMainWindow):
    """Main window with REAL Guardian integration"""
    
    def __init__(self) -> None:
        super().__init__()
        
        self.setWindowTitle("Project Sentinel - Trading Guardian")
        self.setMinimumSize(1200, 800)
        
        # State
        self._is_monitoring = False
        self._config = get_config()
        
        # Workers
        self._guardian_worker = None
        self._data_worker = None
        
        # Setup UI
        self._setup_menu()
        self._setup_ui()
        self._setup_status_bar()
        self._connect_signals()
        
        # Status bar timer
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_status_bar)
        self._status_timer.start(1000)
        
        # Show threshold
        # Show threshold
        threshold = self._config.max_loss_production
        self.pnl_gauge.set_threshold(threshold)
        self.log_viewer.append_log("INFO", 
            f"Config Loaded | Threshold: ${threshold}")
    
    def _setup_menu(self) -> None:
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("&File")
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left Panel
        left_panel = QWidget()
        left_panel.setFixedWidth(280)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        
        self.connection_card = ConnectionCard()
        left_layout.addWidget(self.connection_card)
        
        self.quick_stats = QuickStatsCard()
        left_layout.addWidget(self.quick_stats)
        
        self.mode_indicator = ModeIndicatorWidget()
        left_layout.addWidget(self.mode_indicator)
        
        self.control_panel = ControlPanel()
        left_layout.addWidget(self.control_panel)
        
        left_layout.addStretch()
        splitter.addWidget(left_panel)
        
        # Right Panel (Tabs)
        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)
        
        # Dashboard Tab
        dashboard_tab = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_tab)
        
        self.pnl_gauge = PnLDisplayWidget()
        dashboard_layout.addWidget(self.pnl_gauge)
        
        self.positions_table = PositionsTableWidget()
        dashboard_layout.addWidget(self.positions_table)
        
        self.tabs.addTab(dashboard_tab, "📊 Dashboard")
        
        # Staging Tab (Journal)
        self.staging_tab = StagingTab()
        self.tabs.addTab(self.staging_tab, "🕵️ Journal")
        
        # History Tab (Calendar)
        from gui.widgets.history_tab import HistoryTab
        self.history_tab = HistoryTab(self.staging_tab.journal_manager) # Share manager
        self.history_tab.requestEditJournal.connect(self.switch_to_journal)
        self.tabs.addTab(self.history_tab, "📅 History")
        
        # Data Tab
        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        
        # AI Controls
        ai_control_layout = QHBoxLayout()
        
        self.btn_run_collector = QPushButton("▶ Run Data Collector")
        self.btn_run_collector.clicked.connect(self.run_data_collector)
        ai_control_layout.addWidget(self.btn_run_collector)
        
        self.btn_gen_report = QPushButton("📊 Generate AI Report")
        self.btn_gen_report.clicked.connect(self.generate_ai_report)
        ai_control_layout.addWidget(self.btn_gen_report)
        
        data_layout.addLayout(ai_control_layout)
        
        self.tick_stats = TickStatsWidget()
        data_layout.addWidget(self.tick_stats)
        
        self.news_table = NewsTableWidget()
        data_layout.addWidget(self.news_table)
        
        self.tabs.addTab(data_tab, "📈 Data")
        
        # Logs Tab
        logs_tab = QWidget()
        logs_layout = QVBoxLayout(logs_tab)
        
        self.log_viewer = LogViewerWidget()
        logs_layout.addWidget(self.log_viewer)
        
        self.tabs.addTab(logs_tab, "📜 Logs")
        
        splitter.setSizes([280, 900])
    
    def _setup_status_bar(self) -> None:
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.status_connection = QLabel("● Stopped")
        self.status_connection.setStyleSheet("color: #a4b0be;")
        self.status_bar.addWidget(self.status_connection)
        
        self.status_bar.addWidget(QLabel(" | "))
        
        self.status_mode = QLabel("Mode: NORMAL")
        self.status_bar.addWidget(self.status_mode)
        
        self.status_bar.addWidget(QLabel(" | "))
        
        self.status_time = QLabel("")
        self.status_bar.addPermanentWidget(self.status_time)
    
    def _connect_signals(self) -> None:
        self.control_panel.start_clicked.connect(self.start_monitoring)
        self.control_panel.stop_clicked.connect(self.stop_monitoring)
        self.control_panel.emergency_clicked.connect(self.emergency_close_all)
        self.control_panel.reset_clicked.connect(self.reset_pnl)
        self.control_panel.settings_clicked.connect(self.open_settings)
        self.connection_card.reconnect_clicked.connect(self.start_monitoring)
        self.positions_table.close_requested.connect(self._close_position)
    
    # =========================================================================
    # MONITORING
    # =========================================================================
    
    def switch_to_journal(self, target_date):
        """Switch to Journal tab and load specific date"""
        index = self.tabs.indexOf(self.staging_tab)
        if index != -1:
            self.tabs.setCurrentIndex(index)
            from PySide6.QtCore import QDate
            qdate = QDate(target_date.year, target_date.month, target_date.day)
            self.staging_tab.date_picker.setDate(qdate)
            
    @Slot()
    def start_monitoring(self) -> None:
        """Start Guardian and Data workers"""
        if self._is_monitoring:
            return
        
        self._is_monitoring = True
        self.control_panel.set_running(True)
        self.log_viewer.append_log("INFO", "🚀 Starting monitoring...")
        
        # Start Guardian Worker
        self._guardian_worker = IntegratedGuardianWorker()
        self._guardian_worker.pnl_updated.connect(self._on_pnl_updated)
        self._guardian_worker.positions_changed.connect(self._on_positions_changed)
        self._guardian_worker.mode_changed.connect(self._on_mode_changed)
        self._guardian_worker.account_updated.connect(self._on_account_updated)
        self._guardian_worker.threshold_exceeded.connect(self._on_threshold_exceeded)
        self._guardian_worker.log.connect(self._on_worker_log)
        self._guardian_worker.error.connect(self._on_worker_error)
        self._guardian_worker.start()
        
        # Start Data Worker
        self._data_worker = IntegratedDataWorker()
        self._data_worker.stats_updated.connect(self._on_stats_updated)
        self._data_worker.news_updated.connect(self._on_news_updated)
        self._data_worker.log.connect(self._on_worker_log)
        self._data_worker.start()
        
        # Update status
        self.status_connection.setText("● Running")
        self.status_connection.setStyleSheet("color: #00ff88;")
        self.connection_card.set_connected(True, {"login": "Active", "server": "Monitoring"})
    
    @Slot()
    def stop_monitoring(self) -> None:
        """Stop all workers"""
        if not self._is_monitoring:
            return
        
        self._is_monitoring = False
        self.control_panel.set_running(False)
        self.log_viewer.append_log("INFO", "⏹ Stopping monitoring...")
        
        # Stop workers
        if self._guardian_worker:
            self._guardian_worker.stop()
            self._guardian_worker.wait(3000)
            self._guardian_worker = None
        
        if self._data_worker:
            self._data_worker.stop()
            self._data_worker.wait(3000)
            self._data_worker = None
        
        self.status_connection.setText("● Stopped")
        self.status_connection.setStyleSheet("color: #a4b0be;")
        self.connection_card.set_connected(False)
    
    @Slot()
    def emergency_close_all(self) -> None:
        """Emergency close using Guardian"""
        reply = QMessageBox.warning(
            self,
            "🚨 Emergency Close",
            "This will close ALL positions using TradingGuardian!\n\nAre you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.log_viewer.append_log("WARNING", "🚨 EMERGENCY CLOSE TRIGGERED")
        
        if self._guardian_worker:
            success, failed = self._guardian_worker.force_close_all()
            self.log_viewer.append_log("INFO", f"Result: {success} closed, {failed} failed")
    
    @Slot(object)
    def _close_position(self, ticket: object) -> None:
        """Actually close a position via MT5"""
        self.log_viewer.append_log("INFO", f"Closing position {ticket}...")
        
        try:
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                self.log_viewer.append_log("ERROR", f"Position {ticket} not found")
                return
            
            pos = positions[0]
            symbol = pos.symbol
            
            # Determine close type
            if pos.type == 0:  # BUY -> close with SELL
                close_type = mt5.ORDER_TYPE_SELL
                price = mt5.symbol_info_tick(symbol).bid
            else:  # SELL -> close with BUY
                close_type = mt5.ORDER_TYPE_BUY
                price = mt5.symbol_info_tick(symbol).ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": pos.volume,
                "type": close_type,
                "position": ticket,
                "price": price,
                "deviation": 20,
                "magic": 999999,
                "comment": "Sentinel GUI Close",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                self.log_viewer.append_log("INFO", f"✅ Position {ticket} closed (profit: ${pos.profit:.2f})")
            else:
                error = result.comment if result else "Unknown error"
                self.log_viewer.append_log("ERROR", f"❌ Failed to close {ticket}: {error}")
                
        except Exception as e:
            self.log_viewer.append_log("ERROR", f"Close error: {e}")
    
    @Slot()
    def reset_pnl(self) -> None:
        """Force daily reset - like new trading day started"""
        reply = QMessageBox.question(
            self,
            "🔄 Daily Reset",
            "This will simulate a NEW TRADING DAY:\n\n"
            "• Reset daily P&L counter to $0\n"
            "• Exit BLOCK mode\n"
            "• Clear position tracking\n"
            "• Allow trading again\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.log_viewer.append_log("INFO", "🔄 Forcing daily reset...")
        
        # Call Guardian's reset_daily method
        if self._guardian_worker and self._guardian_worker.isRunning():
            if self._guardian_worker._guardian:
                self._guardian_worker._guardian.reset_daily()
                self.log_viewer.append_log("INFO", "✅ Daily reset complete - new trading day")
            else:
                self.log_viewer.append_log("WARNING", "Guardian not initialized")
        else:
            self.log_viewer.append_log("WARNING", "Monitoring not running - start monitoring first")
            return
        
        # Reset UI state
        self.mode_indicator.set_mode("NORMAL")
        self.status_mode.setText("Mode: NORMAL")
        self.status_mode.setStyleSheet("")
        
        # Also disable bypass if it was enabled
        if hasattr(self._guardian_worker, '_bypass_threshold'):
            self._guardian_worker._bypass_threshold = False
    
    @Slot()
    def open_settings(self) -> None:
        """Open settings dialog"""
        dialog = SettingsDialog(self)
        dialog.settings_saved.connect(self._on_settings_saved)
        dialog.exec()
    
    @Slot()
    def _on_settings_saved(self) -> None:
        """Handle settings saved - auto-restart monitoring if active"""
        self.log_viewer.append_log("INFO", "⚙️ Settings saved")
        
        # Reload config
        self._config = get_config()
        
        # Update threshold display
        threshold = self._config.max_loss_production
        self.pnl_gauge.set_threshold(threshold)
        self.log_viewer.append_log("INFO", f"New threshold: ${threshold}")
        
        # Auto-restart monitoring if active
        if self._is_monitoring:
            self.log_viewer.append_log("INFO", "🔄 Auto-restarting monitoring with new settings...")
            self._stop_monitoring()
            # Use QTimer to give workers time to stop cleanly
            from PySide6.QtCore import QTimer
            QTimer.singleShot(500, self._start_monitoring)

    # =========================================================================
    # AI & DATA CONTROL
    # =========================================================================
    
    @Slot()
    def run_data_collector(self) -> None:
        """Manually start Data Collector independent of Guardian"""
        if self._data_worker and self._data_worker.isRunning():
            QMessageBox.information(self, "Info", "Data Collector is already running!")
            return
            
        self.log_viewer.append_log("INFO", "▶ Starting manual Data Collector...")
        
        # Initialize if not exists
        if not self._data_worker:
            self._data_worker = IntegratedDataWorker()
            self._data_worker.stats_updated.connect(self._on_stats_updated)
            self._data_worker.news_updated.connect(self._on_news_updated)
            self._data_worker.log.connect(self._on_worker_log)
        
        self._data_worker.start()
        self.btn_run_collector.setText("⏸ Stop Data Collector")
        self.btn_run_collector.clicked.disconnect()
        self.btn_run_collector.clicked.connect(self.stop_data_collector)
        
    @Slot()
    def stop_data_collector(self) -> None:
        """Stop manual Data Collector"""
        if self._data_worker:
            self._data_worker.stop()
            self._data_worker.wait(1000)
            self.log_viewer.append_log("INFO", "⏹ Data Collector stopped")
            
        self.btn_run_collector.setText("▶ Run Data Collector")
        self.btn_run_collector.clicked.disconnect()
        self.btn_run_collector.clicked.connect(self.run_data_collector)
    
    @Slot()
    def generate_ai_report(self) -> None:
        """Start background report generation"""
        self.log_viewer.append_log("INFO", "⏳ Starting AI Report Generation (Current Session)...")
        self.btn_gen_report.setEnabled(False)
        self.btn_gen_report.setText("⏳ Generating...")
        
        self._report_worker = ReportGenWorker(mode="TODAY")
        self._report_worker.log.connect(self._on_worker_log)
        self._report_worker.error.connect(self._on_worker_error)
        self._report_worker.finished.connect(self._on_report_finished)
        self._report_worker.start()
        
    @Slot(bool)
    def _on_report_finished(self, success: bool) -> None:
        """Handle report completion"""
        self.btn_gen_report.setEnabled(True)
        self.btn_gen_report.setText("📊 Generate AI Report")
        
        if success:
            QMessageBox.information(self, "Success", "Daily Report generated and sent!")
        else:
            QMessageBox.warning(self, "Warning", "Report generation finished with errors. Check logs.")
    
    @Slot()
    def force_sync_trades(self) -> None:
        """Manually sync trade history from MT5 to database"""
        self.log_viewer.append_log("INFO", "🔄 Starting manual trade sync...")
        
        try:
            from data_collector import TradeCollector, DatabaseManager
            from pathlib import Path
            
            db_path = Path(__file__).parent.parent / "database" / "sentinel_data.db"
            db = DatabaseManager(db_path)
            collector = TradeCollector(db)
            count = collector.sync_trades()
            
            self.log_viewer.append_log("INFO", f"✅ Synced {count} new trades")
            QMessageBox.information(self, "Sync Complete", f"Synced {count} new trades from MT5")
        except Exception as e:
            self.log_viewer.append_log("ERROR", f"Sync failed: {e}")
            QMessageBox.warning(self, "Sync Failed", str(e))

    # =========================================================================
    # SIGNAL HANDLERS FROM WORKERS
    # =========================================================================
    
    @Slot(float)
    def _on_pnl_updated(self, pnl: float) -> None:
        self.pnl_gauge.update_pnl(pnl)
        self.quick_stats.update_pnl(pnl)
    
    @Slot(list)
    def _on_positions_changed(self, positions: list) -> None:
        self.positions_table.update_positions(positions)
    
    @Slot(str, object)
    def _on_mode_changed(self, mode: str, since) -> None:
        self.mode_indicator.set_mode(mode, since)
        if mode == "BLOCK":
            self.status_mode.setText("Mode: 🚫 BLOCK")
            self.status_mode.setStyleSheet("color: #ff4757;")
        else:
            self.status_mode.setText("Mode: NORMAL")
            self.status_mode.setStyleSheet("")
    
    @Slot(dict)
    def _on_account_updated(self, info: dict) -> None:
        self.quick_stats.update_stats(info.get('balance', 0), info.get('equity', 0))
    
    @Slot(float, float)
    def _on_threshold_exceeded(self, current: float, threshold: float) -> None:
        QMessageBox.warning(
            self,
            "⚠️ Threshold Exceeded!",
            f"Daily P&L: ${current:.2f}\nThreshold: ${threshold:.2f}\n\n"
            "BLOCK MODE ACTIVATED!\nAll positions will be auto-closed."
        )
    
    @Slot(dict)
    def _on_stats_updated(self, stats: dict) -> None:
        self.tick_stats.update_stats(stats)
    
    @Slot(list)
    def _on_news_updated(self, news: list) -> None:
        self.news_table.update_news(news)
    
    @Slot(str, str)
    def _on_worker_log(self, level: str, message: str) -> None:
        self.log_viewer.append_log(level, message)
    
    @Slot(str)
    def _on_worker_error(self, message: str) -> None:
        self.log_viewer.append_log("ERROR", message)
        QMessageBox.critical(self, "Error", message)
    
    # =========================================================================
    # MISC
    # =========================================================================
    
    @Slot()
    def _update_status_bar(self) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_time.setText(now)
    
    @Slot()
    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About Project Sentinel",
            "Project Sentinel v1.0.0\n\n"
            "INTEGRATED with:\n"
            "- TradingGuardian (auto-close)\n"
            "- DataCollector (tick & news)\n"
            "- Config system\n\n"
            "Real-time P&L monitoring with automatic position closing."
        )
    
    def closeEvent(self, event: QCloseEvent) -> None:
        if self._is_monitoring:
            self.stop_monitoring()
        event.accept()

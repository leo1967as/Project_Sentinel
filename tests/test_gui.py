"""
Comprehensive Tests for Project Sentinel GUI
Run with: python -m pytest tests/ -v
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Create QApplication once for all tests
app = None

def get_app():
    global app
    if app is None:
        app = QApplication.instance() or QApplication([])
    return app


# =============================================================================
# WIDGET TESTS
# =============================================================================

class TestConnectionCard:
    """Tests for ConnectionCard widget"""
    
    def test_init(self):
        from gui.widgets.connection_card import ConnectionCard
        get_app()
        widget = ConnectionCard()
        assert widget is not None
        assert widget.status_label.text() == "Disconnected"
    
    def test_set_connected_true(self):
        from gui.widgets.connection_card import ConnectionCard
        get_app()
        widget = ConnectionCard()
        
        widget.set_connected(True, {"login": 12345, "server": "TestServer"})
        
        assert widget.status_label.text() == "Connected"
        assert "12345" in widget.account_label.text()
        assert "TestServer" in widget.server_label.text()
        assert not widget.reconnect_btn.isEnabled()
    
    def test_set_connected_false(self):
        from gui.widgets.connection_card import ConnectionCard
        get_app()
        widget = ConnectionCard()
        
        widget.set_connected(False)
        
        assert widget.status_label.text() == "Disconnected"
        assert widget.reconnect_btn.isEnabled()


class TestQuickStatsCard:
    """Tests for QuickStatsCard widget"""
    
    def test_init(self):
        from gui.widgets.quick_stats import QuickStatsCard
        get_app()
        widget = QuickStatsCard()
        assert widget is not None
    
    def test_update_stats(self):
        from gui.widgets.quick_stats import QuickStatsCard
        get_app()
        widget = QuickStatsCard()
        
        widget.update_stats(1000.50, 1050.25)
        
        assert "1000.50" in widget.balance_label.text()
        assert "1050.25" in widget.equity_label.text()
    
    def test_update_pnl_positive(self):
        from gui.widgets.quick_stats import QuickStatsCard
        get_app()
        widget = QuickStatsCard()
        
        widget.update_pnl(25.50)
        
        assert "+25.50" in widget.pnl_label.text()
        assert "#00ff88" in widget.pnl_label.styleSheet()  # Green
    
    def test_update_pnl_negative(self):
        from gui.widgets.quick_stats import QuickStatsCard
        get_app()
        widget = QuickStatsCard()
        
        widget.update_pnl(-50.00)
        
        assert "-50.00" in widget.pnl_label.text()
        assert "#ff4757" in widget.pnl_label.styleSheet()  # Red


class TestControlPanel:
    """Tests for ControlPanel widget"""
    
    def test_init(self):
        from gui.widgets.control_panel import ControlPanel
        get_app()
        widget = ControlPanel()
        assert widget is not None
        assert widget.start_btn.isEnabled()
        assert not widget.stop_btn.isEnabled()
    
    def test_set_running_true(self):
        from gui.widgets.control_panel import ControlPanel
        get_app()
        widget = ControlPanel()
        
        widget.set_running(True)
        
        assert not widget.start_btn.isEnabled()
        assert widget.stop_btn.isEnabled()
    
    def test_set_running_false(self):
        from gui.widgets.control_panel import ControlPanel
        get_app()
        widget = ControlPanel()
        
        widget.set_running(False)
        
        assert widget.start_btn.isEnabled()
        assert not widget.stop_btn.isEnabled()
    
    def test_signals(self):
        from gui.widgets.control_panel import ControlPanel
        get_app()
        widget = ControlPanel()
        
        # Test signal emission
        start_called = []
        widget.start_clicked.connect(lambda: start_called.append(True))
        widget.start_btn.click()
        
        assert len(start_called) == 1


class TestPnLGaugeWidget:
    """Tests for PnLGaugeWidget"""
    
    def test_init(self):
        from gui.widgets.pnl_gauge import PnLGaugeWidget
        get_app()
        widget = PnLGaugeWidget()
        assert widget is not None
    
    def test_set_value_positive(self):
        from gui.widgets.pnl_gauge import PnLGaugeWidget
        get_app()
        widget = PnLGaugeWidget()
        
        widget.set_value(100.50)
        
        assert "+100.50" in widget.pnl_label.text()
        assert "#00ff88" in widget.pnl_label.styleSheet()  # Green
    
    def test_set_value_negative_above_threshold(self):
        from gui.widgets.pnl_gauge import PnLGaugeWidget
        get_app()
        widget = PnLGaugeWidget()
        widget.set_threshold(-300)
        
        widget.set_value(-100)
        
        assert "-100" in widget.pnl_label.text()
        assert "#ffd32a" in widget.pnl_label.styleSheet()  # Yellow
    
    def test_set_value_below_threshold(self):
        from gui.widgets.pnl_gauge import PnLGaugeWidget
        get_app()
        widget = PnLGaugeWidget()
        widget.set_threshold(-300)
        
        widget.set_value(-350)
        
        assert "-350" in widget.pnl_label.text()
        assert "#ff4757" in widget.pnl_label.styleSheet()  # Red
    
    def test_set_threshold(self):
        from gui.widgets.pnl_gauge import PnLGaugeWidget
        get_app()
        widget = PnLGaugeWidget()
        
        widget.set_threshold(-500)
        
        assert "-500" in widget.threshold_label.text()


class TestModeIndicatorWidget:
    """Tests for ModeIndicatorWidget"""
    
    def test_init(self):
        from gui.widgets.mode_indicator import ModeIndicatorWidget
        get_app()
        widget = ModeIndicatorWidget()
        assert widget is not None
    
    def test_set_mode_normal(self):
        from gui.widgets.mode_indicator import ModeIndicatorWidget
        get_app()
        widget = ModeIndicatorWidget()
        
        widget.set_mode("NORMAL")
        
        assert "NORMAL" in widget.mode_label.text()
        assert "#00ff88" in widget.mode_label.styleSheet()  # Green
    
    def test_set_mode_block(self):
        from gui.widgets.mode_indicator import ModeIndicatorWidget
        get_app()
        widget = ModeIndicatorWidget()
        
        widget.set_mode("BLOCK", datetime.now())
        
        assert "BLOCK" in widget.mode_label.text()
        assert "#ff4757" in widget.mode_label.styleSheet()  # Red
        # Note: isVisible() returns False if parent is not shown
        # Check that visibility was set instead
        assert not widget.duration_label.isHidden()


class TestPositionsTableWidget:
    """Tests for PositionsTableWidget"""
    
    def test_init(self):
        from gui.widgets.positions_table import PositionsTableWidget
        get_app()
        widget = PositionsTableWidget()
        assert widget is not None
        assert widget.columnCount() == 7
    
    def test_update_positions(self):
        from gui.widgets.positions_table import PositionsTableWidget
        get_app()
        widget = PositionsTableWidget()
        
        positions = [
            {'ticket': 123, 'symbol': 'XAUUSD', 'type': 'BUY', 
             'volume': 0.1, 'open_price': 2650.0, 'profit': 15.50},
            {'ticket': 456, 'symbol': 'XAUUSD', 'type': 'SELL',
             'volume': 0.2, 'open_price': 2660.0, 'profit': -10.00},
        ]
        
        widget.update_positions(positions)
        
        assert widget.rowCount() == 2
        assert widget.item(0, 0).text() == "123"
        assert widget.item(0, 1).text() == "XAUUSD"
    
    def test_clear_all(self):
        from gui.widgets.positions_table import PositionsTableWidget
        get_app()
        widget = PositionsTableWidget()
        
        widget.update_positions([{'ticket': 1, 'symbol': 'X', 'type': 'BUY',
                                   'volume': 0.1, 'open_price': 100, 'profit': 0}])
        widget.clear_all()
        
        assert widget.rowCount() == 0


class TestLogViewerWidget:
    """Tests for LogViewerWidget"""
    
    def test_init(self):
        from gui.widgets.log_viewer import LogViewerWidget
        get_app()
        widget = LogViewerWidget()
        assert widget is not None
        assert widget.isReadOnly()
    
    def test_append_log(self):
        from gui.widgets.log_viewer import LogViewerWidget
        get_app()
        widget = LogViewerWidget()
        
        widget.append_log("INFO", "Test message")
        
        text = widget.toPlainText()
        assert "INFO" in text
        assert "Test message" in text
    
    def test_append_multiple_logs(self):
        from gui.widgets.log_viewer import LogViewerWidget
        get_app()
        widget = LogViewerWidget()
        
        widget.append_log("INFO", "Message 1")
        widget.append_log("WARNING", "Message 2")
        widget.append_log("ERROR", "Message 3")
        
        text = widget.toPlainText()
        assert "Message 1" in text
        assert "Message 2" in text
        assert "Message 3" in text
    
    def test_clear_logs(self):
        from gui.widgets.log_viewer import LogViewerWidget
        get_app()
        widget = LogViewerWidget()
        
        widget.append_log("INFO", "Test")
        widget.clear_logs()
        
        assert widget.toPlainText() == ""


class TestTickStatsWidget:
    """Tests for TickStatsWidget"""
    
    def test_init(self):
        from gui.widgets.tick_stats import TickStatsWidget
        get_app()
        widget = TickStatsWidget()
        assert widget is not None
    
    def test_update_stats(self):
        from gui.widgets.tick_stats import TickStatsWidget
        get_app()
        widget = TickStatsWidget()
        
        widget.update_stats({'total': 1500, 'rate': 25.5})
        
        assert "1,500" in widget.total_label.text()
        assert "25.5" in widget.rate_label.text()
    
    def test_update_buffer(self):
        from gui.widgets.tick_stats import TickStatsWidget
        get_app()
        widget = TickStatsWidget()
        
        widget.update_buffer(500, 1000)
        
        assert "500/1000" in widget.buffer_label.text()


class TestNewsTableWidget:
    """Tests for NewsTableWidget"""
    
    def test_init(self):
        from gui.widgets.news_table import NewsTableWidget
        get_app()
        widget = NewsTableWidget()
        assert widget is not None
        assert widget.columnCount() == 4
    
    def test_update_news(self):
        from gui.widgets.news_table import NewsTableWidget
        get_app()
        widget = NewsTableWidget()
        
        news_list = [
            {'event_time': '14:30', 'currency': 'USD', 
             'impact': 'High', 'event_name': 'FOMC'},
        ]
        
        widget.update_news(news_list)
        
        assert widget.rowCount() == 1
        assert widget.item(0, 1).text() == "USD"


# =============================================================================
# WORKER TESTS
# =============================================================================

class TestBaseWorker:
    """Tests for BaseWorker"""
    
    def test_init(self):
        from gui.workers.base_worker import BaseWorker
        get_app()
        
        # BaseWorker is abstract, test basic properties
        class TestWorker(BaseWorker):
            def run(self):
                pass
        
        worker = TestWorker()
        assert worker is not None
        assert not worker.is_stopped()
    
    def test_stop(self):
        from gui.workers.base_worker import BaseWorker
        get_app()
        
        class TestWorker(BaseWorker):
            def run(self):
                pass
        
        worker = TestWorker()
        worker.stop()
        
        assert worker.is_stopped()


class TestGuardianWorker:
    """Tests for GuardianWorker"""
    
    def test_init(self):
        from gui.workers.guardian_worker import GuardianWorker
        get_app()
        
        worker = GuardianWorker()
        assert worker is not None
    
    def test_set_guardian(self):
        from gui.workers.guardian_worker import GuardianWorker
        get_app()
        
        worker = GuardianWorker()
        mock_guardian = MagicMock()
        
        worker.set_guardian(mock_guardian)
        
        assert worker._guardian == mock_guardian


class TestDataWorker:
    """Tests for DataWorker"""
    
    def test_init(self):
        from gui.workers.data_worker import DataWorker
        get_app()
        
        worker = DataWorker()
        assert worker is not None


class TestMT5Worker:
    """Tests for MT5Worker"""
    
    def test_init(self):
        from gui.workers.mt5_worker import MT5Worker
        get_app()
        
        worker = MT5Worker()
        assert worker is not None


# =============================================================================
# THEME TESTS
# =============================================================================

class TestThemeManager:
    """Tests for ThemeManager"""
    
    def test_init(self):
        from gui.theme import ThemeManager
        
        theme = ThemeManager()
        assert theme is not None
        assert theme.current_theme == 'dark'
    
    def test_get_color(self):
        from gui.theme import ThemeManager
        
        theme = ThemeManager()
        
        assert theme.get_color('primary') == '#00d4ff'
        assert theme.get_color('danger') == '#ff4757'
        assert theme.get_color('success') == '#00ff88'


# =============================================================================
# MAIN WINDOW TESTS
# =============================================================================

class TestSentinelMainWindow:
    """Tests for SentinelMainWindow"""
    
    def test_init(self):
        from gui.main_window import SentinelMainWindow
        get_app()
        
        window = SentinelMainWindow()
        assert window is not None
        assert window.windowTitle() == "Project Sentinel - Trading Guardian"
    
    def test_has_required_widgets(self):
        from gui.main_window import SentinelMainWindow
        get_app()
        
        window = SentinelMainWindow()
        
        assert hasattr(window, 'connection_card')
        assert hasattr(window, 'quick_stats')
        assert hasattr(window, 'control_panel')
        assert hasattr(window, 'pnl_gauge')
        assert hasattr(window, 'positions_table')
        assert hasattr(window, 'mode_indicator')
        assert hasattr(window, 'log_viewer')
    
    def test_initial_state(self):
        from gui.main_window import SentinelMainWindow
        get_app()
        
        window = SentinelMainWindow()
        
        assert window._is_monitoring == False


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

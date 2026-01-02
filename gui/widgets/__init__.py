"""
Widgets package - All custom widgets for Sentinel GUI
"""

from .connection_card import ConnectionCard
from .quick_stats import QuickStatsCard
from .control_panel import ControlPanel
from .pnl_gauge import PnLGaugeWidget
from .positions_table import PositionsTableWidget
from .mode_indicator import ModeIndicatorWidget
from .tick_stats import TickStatsWidget
from .news_table import NewsTableWidget
from .log_viewer import LogViewerWidget

__all__ = [
    'ConnectionCard',
    'QuickStatsCard', 
    'ControlPanel',
    'PnLGaugeWidget',
    'PositionsTableWidget',
    'ModeIndicatorWidget',
    'TickStatsWidget',
    'NewsTableWidget',
    'LogViewerWidget',
]

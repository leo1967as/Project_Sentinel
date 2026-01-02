"""
===============================================================================
PROJECT SENTINEL - CHART PLOTTER UTILITY
===============================================================================
Utility functions for generating trading analysis charts.
Used by daily_report.py

Author: Project Sentinel
===============================================================================
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyArrowPatch, Rectangle
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Non-interactive backend
import matplotlib
matplotlib.use('Agg')

# =============================================================================
# STYLE CONFIGURATION
# =============================================================================

# Dark theme colors
COLORS = {
    'background': '#1a1a2e',
    'panel': '#16213e',
    'primary': '#00d4ff',
    'win': '#00ff88',
    'loss': '#ff4757',
    'neutral': '#a4b0be',
    'warning': '#ffd32a',
    'text': '#ffffff',
    'grid': '#2d3436'
}

def apply_dark_style(ax):
    """Apply dark theme to axis"""
    ax.set_facecolor(COLORS['panel'])
    ax.tick_params(colors=COLORS['text'])
    ax.xaxis.label.set_color(COLORS['text'])
    ax.yaxis.label.set_color(COLORS['text'])
    ax.spines['bottom'].set_color(COLORS['grid'])
    ax.spines['left'].set_color(COLORS['grid'])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, alpha=0.2, color=COLORS['grid'])

# =============================================================================
# CHART TYPES
# =============================================================================

def create_price_chart(times: List[datetime], prices: List[float], 
                      title: str = "Price Chart",
                      figsize: Tuple[int, int] = (12, 6)) -> Tuple[plt.Figure, plt.Axes]:
    """
    Create a basic price line chart with dark theme.
    
    Args:
        times: List of datetime objects
        prices: List of price values
        title: Chart title
        figsize: Figure size
    
    Returns:
        Figure and Axes objects
    """
    fig, ax = plt.subplots(figsize=figsize, facecolor=COLORS['background'])
    apply_dark_style(ax)
    
    # Plot price line
    ax.plot(times, prices, color=COLORS['primary'], linewidth=1, alpha=0.9)
    ax.fill_between(times, prices, alpha=0.1, color=COLORS['primary'])
    
    # Formatting
    ax.set_title(title, color=COLORS['text'], fontsize=14, fontweight='bold')
    ax.set_xlabel('Time', color=COLORS['text'])
    ax.set_ylabel('Price', color=COLORS['text'])
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    
    return fig, ax

def add_trade_markers(ax: plt.Axes, trades: List[Dict], 
                      show_profit: bool = True):
    """
    Add entry/exit markers to a chart.
    
    Args:
        ax: Matplotlib axes
        trades: List of trade dicts with keys:
            - open_time, close_time
            - open_price, close_price
            - order_type ('BUY' or 'SELL')
            - profit
    """
    for trade in trades:
        is_win = trade['profit'] > 0
        color = COLORS['win'] if is_win else COLORS['loss']
        
        # Entry arrow
        arrow_dir = 1 if trade['order_type'] == 'BUY' else -1
        ax.annotate(
            '',
            xy=(trade['open_time'], trade['open_price']),
            xytext=(trade['open_time'], trade['open_price'] - arrow_dir * 0.5),
            arrowprops=dict(arrowstyle='->', color=color, lw=2)
        )
        
        # Exit marker (X)
        ax.scatter(
            trade['close_time'], trade['close_price'],
            color=color, s=60, marker='x', zorder=5, linewidths=2
        )
        
        # Profit label
        if show_profit:
            ax.annotate(
                f"${trade['profit']:+.1f}",
                xy=(trade['close_time'], trade['close_price']),
                xytext=(5, 10),
                textcoords='offset points',
                fontsize=8,
                color=color,
                fontweight='bold'
            )

def add_news_markers(ax: plt.Axes, news_events: List[Dict],
                    y_position: str = 'top'):
    """
    Add vertical lines for news events.
    
    Args:
        ax: Matplotlib axes
        news_events: List of dicts with keys:
            - event_time: datetime
            - currency: str
            - impact: str ('High', 'Medium', 'Low')
            - event_name: str
        y_position: 'top' or 'bottom' for label placement
    """
    for news in news_events:
        # Line color based on impact
        if news['impact'] == 'High':
            color = COLORS['loss']
        elif news['impact'] == 'Medium':
            color = COLORS['warning']
        else:
            color = COLORS['neutral']
        
        ax.axvline(
            x=news['event_time'],
            color=color,
            linestyle='--',
            alpha=0.7,
            linewidth=1
        )
        
        # Label
        ylim = ax.get_ylim()
        y = ylim[1] if y_position == 'top' else ylim[0]
        
        ax.annotate(
            f"📰 {news['currency']}",
            xy=(news['event_time'], y),
            fontsize=7,
            color=color,
            ha='center',
            rotation=90 if len(news['currency']) > 3 else 0
        )

def create_volume_profile(ax: plt.Axes, prices: List[float],
                         num_bins: int = 30, 
                         orientation: str = 'horizontal'):
    """
    Add volume profile histogram.
    
    Args:
        ax: Matplotlib axes
        prices: List of price values
        num_bins: Number of histogram bins
        orientation: 'horizontal' (for right side) or 'vertical'
    """
    apply_dark_style(ax)
    
    # Calculate histogram
    hist, bin_edges = np.histogram(prices, bins=num_bins)
    
    if orientation == 'horizontal':
        ax.barh(
            bin_edges[:-1], hist,
            height=np.diff(bin_edges)[0],
            color=COLORS['primary'],
            alpha=0.6
        )
        ax.set_xlabel('Volume', color=COLORS['text'])
    else:
        ax.bar(
            bin_edges[:-1], hist,
            width=np.diff(bin_edges)[0],
            color=COLORS['primary'],
            alpha=0.6
        )
        ax.set_ylabel('Volume', color=COLORS['text'])
    
    ax.set_title('Volume Profile', color=COLORS['text'], fontsize=10)

def create_pnl_curve(trades: List[Dict], 
                    figsize: Tuple[int, int] = (12, 4)) -> Tuple[plt.Figure, plt.Axes]:
    """
    Create cumulative P&L curve.
    
    Args:
        trades: List of trade dicts with 'close_time' and 'profit'
        figsize: Figure size
    
    Returns:
        Figure and Axes objects
    """
    if not trades:
        return None, None
    
    # Sort by close time
    sorted_trades = sorted(trades, key=lambda t: t['close_time'])
    
    # Calculate cumulative P&L
    times = []
    pnls = []
    cumulative = 0
    
    for trade in sorted_trades:
        cumulative += trade['profit']
        times.append(trade['close_time'])
        pnls.append(cumulative)
    
    # Create figure
    fig, ax = plt.subplots(figsize=figsize, facecolor=COLORS['background'])
    apply_dark_style(ax)
    
    # Plot
    ax.fill_between(times, pnls, alpha=0.3, color=COLORS['primary'])
    ax.plot(times, pnls, color=COLORS['primary'], linewidth=2)
    ax.axhline(y=0, color=COLORS['text'], linestyle='-', alpha=0.5)
    
    # Color final result
    final_pnl = pnls[-1]
    result_color = COLORS['win'] if final_pnl >= 0 else COLORS['loss']
    
    ax.set_title(
        f"P&L Curve | Final: ${final_pnl:+.2f}",
        color=result_color, fontsize=14, fontweight='bold'
    )
    ax.set_xlabel('Time', color=COLORS['text'])
    ax.set_ylabel('Cumulative P&L ($)', color=COLORS['text'])
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    
    return fig, ax

def create_battle_chart(times: List[datetime], prices: List[float],
                       trades: List[Dict], news_events: List[Dict] = None,
                       title: str = "Battle Analysis") -> plt.Figure:
    """
    Create complete battle analysis chart with:
    - Price chart with trade markers
    - Volume profile on right
    - News event markers
    
    Args:
        times: Price timestamps
        prices: Price values
        trades: Trade data
        news_events: Optional news data
        title: Chart title
    
    Returns:
        Complete figure
    """
    # Create figure with gridspec
    fig, (ax1, ax2) = plt.subplots(
        1, 2,
        figsize=(14, 6),
        gridspec_kw={'width_ratios': [4, 1]},
        facecolor=COLORS['background']
    )
    
    # Main price chart
    apply_dark_style(ax1)
    ax1.plot(times, prices, color=COLORS['primary'], linewidth=0.8, alpha=0.8)
    ax1.fill_between(times, prices, alpha=0.1, color=COLORS['primary'])
    
    # Add trade markers
    add_trade_markers(ax1, trades)
    
    # Add news markers
    if news_events:
        add_news_markers(ax1, news_events)
    
    # Formatting
    ax1.set_title(title, color=COLORS['text'], fontsize=12, fontweight='bold')
    ax1.set_xlabel('Time', color=COLORS['text'])
    ax1.set_ylabel('Price', color=COLORS['text'])
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    
    # Volume profile
    create_volume_profile(ax2, prices)
    
    plt.tight_layout()
    return fig

def save_chart(fig: plt.Figure, filepath: Path, dpi: int = 150):
    """Save chart to file"""
    fig.savefig(filepath, dpi=dpi, facecolor=COLORS['background'])
    plt.close(fig)
    return filepath

# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    import random
    
    # Generate sample data
    base_time = datetime.now() - timedelta(hours=2)
    times = [base_time + timedelta(minutes=i) for i in range(120)]
    prices = [2650 + random.uniform(-5, 5) + i*0.01 for i in range(120)]
    
    trades = [
        {
            'open_time': times[20],
            'close_time': times[40],
            'open_price': prices[20],
            'close_price': prices[40],
            'order_type': 'BUY',
            'profit': 15.5
        },
        {
            'open_time': times[60],
            'close_time': times[80],
            'open_price': prices[60],
            'close_price': prices[80],
            'order_type': 'SELL',
            'profit': -8.2
        }
    ]
    
    news = [
        {
            'event_time': times[30],
            'currency': 'USD',
            'impact': 'High',
            'event_name': 'FOMC'
        }
    ]
    
    # Create chart
    fig = create_battle_chart(times, prices, trades, news, "Test Battle")
    save_chart(fig, Path("test_chart.png"))
    print("Chart saved to test_chart.png")

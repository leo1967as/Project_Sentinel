# chart_gen.py - AI-Optimized Chart Generator with Indicators
"""
Chart design optimized for Vision AI (PE/CLIP) pattern recognition:
- EMA 20/50 for trend direction
- Session lines (London/NY open)
- Recent High/Low levels
- Detailed grid for reference
- Volume bars for move strength
"""
import MetaTrader5 as mt5
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import AutoMinorLocator
from datetime import datetime, timedelta
import os
import numpy as np

def get_data(symbol, timeframe, n=100):
    """ดึงข้อมูลแท่งเทียนจาก MT5"""
    if not mt5.terminal_info():
        if not mt5.initialize():
            print("❌ Failed to initialize MT5")
            return None
    
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
    if rates is None or len(rates) == 0:
        symbols = mt5.symbols_get()
        if symbols:
            for s in symbols:
                if symbol in s.name:
                    rates = mt5.copy_rates_from_pos(s.name, timeframe, 0, n)
                    if rates is not None and len(rates) > 0:
                        break
    
    if rates is None or len(rates) == 0:
        return None
        
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    
    # Add EMAs
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    return df


def get_session_times():
    """Get session open times (UTC)"""
    now = datetime.utcnow()
    today = now.date()
    
    sessions = {
        'London': datetime.combine(today, datetime.strptime('08:00', '%H:%M').time()),
        'NY': datetime.combine(today, datetime.strptime('13:00', '%H:%M').time()),
    }
    
    # If before London open, use yesterday's sessions
    if now.hour < 8:
        yesterday = today - timedelta(days=1)
        sessions = {
            'London': datetime.combine(yesterday, datetime.strptime('08:00', '%H:%M').time()),
            'NY': datetime.combine(yesterday, datetime.strptime('13:00', '%H:%M').time()),
        }
    
    return sessions


def draw_candlestick_with_indicators(ax, df, show_volume=True, show_ema=True, 
                                      show_highlow=True, show_sessions=True):
    """Draw candlesticks with EMA, High/Low, and Session lines"""
    x = np.arange(len(df))
    
    # Colors
    up_color = '#00d26a'
    down_color = '#ff4757'
    ema20_color = '#00b4d8'  # Cyan
    ema50_color = '#ffd60a'  # Yellow
    
    # Draw candles
    for i in range(len(df)):
        o = df['open'].iloc[i]
        h = df['high'].iloc[i]
        l = df['low'].iloc[i]
        c = df['close'].iloc[i]
        
        is_up = c >= o
        color = up_color if is_up else down_color
        
        # Wick
        ax.plot([i, i], [l, h], color=color, linewidth=0.8)
        
        # Body
        body_bottom = min(o, c)
        body_height = abs(c - o)
        
        if body_height < (h - l) * 0.01:  # Doji
            ax.plot([i-0.3, i+0.3], [o, o], color=color, linewidth=1.2)
        else:
            rect = mpatches.Rectangle(
                (i - 0.35, body_bottom), 0.7, body_height,
                facecolor=color, edgecolor=color, linewidth=0.5
            )
            ax.add_patch(rect)
    
    # EMA Lines
    if show_ema and 'ema20' in df.columns and 'ema50' in df.columns:
        ax.plot(x, df['ema20'].values, color=ema20_color, linewidth=1.2, 
                alpha=0.9, label='EMA 20')
        ax.plot(x, df['ema50'].values, color=ema50_color, linewidth=1.2, 
                alpha=0.9, label='EMA 50')
    
    # Recent High/Low (last 20 candles)
    if show_highlow:
        recent = df.tail(20)
        recent_high = recent['high'].max()
        recent_low = recent['low'].min()
        
        ax.axhline(y=recent_high, color='#9d4edd', linestyle=':', 
                   linewidth=1.0, alpha=0.7)
        ax.axhline(y=recent_low, color='#9d4edd', linestyle=':', 
                   linewidth=1.0, alpha=0.7)
    
    # Session Lines (vertical)
    if show_sessions:
        sessions = get_session_times()
        for i, (time, row) in enumerate(df.iterrows()):
            # Check if this candle is at session open
            for session_name, session_time in sessions.items():
                # Allow 1 hour window for matching
                time_diff = abs((time.replace(tzinfo=None) - session_time).total_seconds())
                if time_diff < 3600:  # Within 1 hour
                    color = '#ff9f1c' if session_name == 'London' else '#00b4d8'
                    ax.axvline(x=i, color=color, linestyle='--', 
                               linewidth=0.8, alpha=0.5)
    
    # Volume overlay
    if show_volume and 'tick_volume' in df.columns:
        ax_vol = ax.twinx()
        volumes = df['tick_volume'].values
        colors = [up_color if df['close'].iloc[i] >= df['open'].iloc[i] else down_color 
                  for i in range(len(df))]
        
        ax_vol.bar(x, volumes, color=colors, alpha=0.2, width=0.6)
        ax_vol.set_ylim(0, max(volumes) * 5)
        ax_vol.set_yticks([])
    
    return ax


def create_trade_chart(symbol, ticket_id, entry_price=0, sl=0, tp=0, 
                       candle_count=80, show_volume=True):
    """
    สร้างกราฟ 4-Panel สำหรับ AI Learning
    
    Features:
    - EMA 20/50 overlay
    - Session lines (London/NY)
    - Recent High/Low
    - Detailed grid
    - Volume bars
    """
    # 1. ดึงข้อมูล
    data = {}
    tfs = {
        'H1': mt5.TIMEFRAME_H1,
        'M15': mt5.TIMEFRAME_M15,
        'M5': mt5.TIMEFRAME_M5,
        'M1': mt5.TIMEFRAME_M1
    }
    
    for name, tf in tfs.items():
        df = get_data(symbol, tf, n=candle_count)
        if df is None or df.empty:
            print(f"❌ Failed to get {name} data")
            return None
        data[name] = df

    # 2. ไฟล์
    filename = f"images/auto_{ticket_id}.jpg"
    os.makedirs("images", exist_ok=True)

    # 3. สร้าง Figure
    fig = plt.figure(figsize=(16, 12), facecolor='#0d1117')
    fig.subplots_adjust(hspace=0.3, wspace=0.2, top=0.93, bottom=0.05, left=0.05, right=0.95)
    
    # Title
    fig.suptitle(f'{symbol} Multi-Timeframe Analysis', 
                 fontsize=14, fontweight='bold', color='#e6edf3')
    
    names = ['H1', 'M15', 'M5', 'M1']
    titles = {
        'H1': 'H1 - Trend Context',
        'M15': 'M15 - Market Structure', 
        'M5': 'M5 - Setup Zone',
        'M1': 'M1 - Entry Trigger'
    }
    positions = [221, 222, 223, 224]
    
    for name, pos in zip(names, positions):
        ax = fig.add_subplot(pos)
        df = data[name]
        
        # Background
        ax.set_facecolor('#0d1117')
        
        # Draw candles with all indicators
        draw_candlestick_with_indicators(
            ax, df, 
            show_volume=show_volume,
            show_ema=True,
            show_highlow=True,
            show_sessions=(name in ['H1', 'M15'])  # Sessions only for larger TFs
        )
        
        # Detailed Grid - More visible
        ax.yaxis.grid(True, linestyle='-', linewidth=0.6, color='#3d4450', alpha=0.9)
        ax.xaxis.grid(True, linestyle='-', linewidth=0.3, color='#2d333b', alpha=0.6)
        
        # Minor grid for extra detail
        ax.yaxis.set_minor_locator(AutoMinorLocator(2))
        ax.yaxis.grid(True, which='minor', linestyle=':', linewidth=0.3, 
                      color='#21262d', alpha=0.5)
        
        # Draw entry/SL/TP lines
        if entry_price > 0:
            ax.axhline(y=entry_price, color='#00b4d8', linestyle='--', 
                       linewidth=1.5, alpha=0.8)
        if sl > 0:
            ax.axhline(y=sl, color='#ff4757', linestyle=':', 
                       linewidth=1.2, alpha=0.8)
        if tp > 0:
            ax.axhline(y=tp, color='#00d26a', linestyle=':', 
                       linewidth=1.2, alpha=0.8)
        
        # Title
        ax.set_title(titles[name], fontsize=11, fontweight='bold', 
                     color='#e6edf3', pad=8, loc='left')
        
        # Axes styling
        ax.set_xlim(-1, len(df))
        ax.tick_params(axis='both', colors='#8b949e', labelsize=8)
        
        # Y-axis: Price labels
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.2f}'))
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position('right')
        
        # X-axis: Time labels
        n_labels = 6
        step = max(1, len(df) // n_labels)
        x_ticks = list(range(0, len(df), step))
        x_labels = [df.index[i].strftime('%H:%M') for i in x_ticks if i < len(df)]
        ax.set_xticks(x_ticks[:len(x_labels)])
        ax.set_xticklabels(x_labels, fontsize=7, color='#8b949e')
        
        # Bottom-left indicator labels
        indicator_text = "EMA20 · EMA50 · H/L"
        if name in ['H1', 'M15']:
            indicator_text += " · Sessions"
        ax.text(0.02, 0.02, indicator_text, transform=ax.transAxes,
                fontsize=7, color='#8b949e', alpha=0.8,
                verticalalignment='bottom', horizontalalignment='left',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#0d1117', 
                          edgecolor='#30363d', alpha=0.8))
        
        # Spines
        for spine in ax.spines.values():
            spine.set_color('#30363d')
            spine.set_linewidth(0.5)
    
    # Legend (bottom right)
    legend_elements = [
        mpatches.Patch(facecolor='#00b4d8', label='EMA 20'),
        mpatches.Patch(facecolor='#ffd60a', label='EMA 50'),
        mpatches.Patch(facecolor='#9d4edd', label='High/Low'),
        mpatches.Patch(facecolor='#ff9f1c', label='London'),
        mpatches.Patch(facecolor='#00b4d8', label='NY'),
    ]
    fig.legend(handles=legend_elements, loc='lower right', 
               fontsize=8, facecolor='#0d1117', edgecolor='#30363d',
               labelcolor='#e6edf3', ncol=5)
    
    # Current price - Add to M1 chart (top-right)
    last_price = data['M1']['close'].iloc[-1]
    # Get M1 subplot (position 224 = index 3)
    ax_m1 = fig.axes[3] if len(fig.axes) >= 4 else fig.axes[-1]
    ax_m1.text(0.98, 0.98, f'Last: {last_price:.2f}', transform=ax_m1.transAxes,
               fontsize=10, color='#00b4d8', fontweight='bold',
               verticalalignment='top', horizontalalignment='right',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='#0d1117', 
                         edgecolor='#00b4d8', alpha=0.9))
    
    # Timestamp
    fig.text(0.05, 0.02, datetime.now().strftime('%Y-%m-%d %H:%M'), 
             ha='left', fontsize=9, color='#8b949e')
    
    # Save
    fig.savefig(filename, dpi=150, 
                facecolor='#0d1117', edgecolor='none',
                format='jpg', pil_kwargs={'quality': 92})
    plt.close(fig)
    
    print(f"✅ Chart saved: {filename}")
    return filename


if __name__ == "__main__":
    if mt5.initialize():
        result = create_trade_chart("XAUUSD", "test_full")
        print(f"Result: {result}")
        mt5.shutdown()

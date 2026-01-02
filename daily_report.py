"""
===============================================================================
PROJECT SENTINEL - AI DAILY REPORT GENERATOR
===============================================================================
Generates AI-powered trading analysis reports with charts.
Runs at 05:00 AM daily via scheduled task.

Features:
- Trade clustering into "battles" (15 min / $2 range)
- Price charts with Entry/Exit markers
- Volume profile histogram
- News event markers
- AI analysis via OpenRouter (Gemini/GPT fallback)
- Line Notify delivery

Author: Project Sentinel
===============================================================================
"""

import sqlite3
import requests
import json
import io
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import logging

# Matplotlib (non-interactive backend for server)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyArrowPatch
import matplotlib.patches as mpatches
from matplotlib.ticker import AutoMinorLocator
import numpy as np
import pandas as pd
from data_collector import DatabaseManager
import MetaTrader5 as mt5

# Local imports
import sys
import time
sys.path.insert(0, str(Path(__file__).parent))
from config import get_config, AuditLogger

# =============================================================================
# CONFIGURATION
# =============================================================================

config = get_config()

PROJECT_ROOT = Path(__file__).parent
DB_FILE = PROJECT_ROOT / "database" / "sentinel_data.db"
CHART_DIR = PROJECT_ROOT / "charts"
CHART_DIR.mkdir(exist_ok=True)

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Battle clustering parameters
BATTLE_TIME_THRESHOLD = 15 * 60  # 15 minutes in seconds
BATTLE_PRICE_THRESHOLD = 2.0    # $2 price range

# Token usage tracking file
TOKEN_USAGE_FILE = LOG_DIR / "token_usage.json"

# =============================================================================
# LOGGING
# =============================================================================

logger = logging.getLogger("daily_report")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    fh = logging.FileHandler(LOG_DIR / "daily_report.log", encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
    logger.addHandler(fh)
    
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
    logger.addHandler(ch)

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Trade:
    """Single trade record"""
    ticket: int
    symbol: str
    order_type: str  # 'BUY' or 'SELL'
    volume: float
    open_price: float
    close_price: float
    profit: float
    open_time: datetime
    close_time: datetime
    
    @property
    def is_win(self) -> bool:
        return self.profit > 0
    
    @property
    def duration_minutes(self) -> float:
        return (self.close_time - self.open_time).total_seconds() / 60

@dataclass
class Battle:
    """Cluster of related trades"""
    trades: List[Trade] = field(default_factory=list)
    start_time: datetime = None
    end_time: datetime = None
    center_price: float = 0.0
    total_profit: float = 0.0
    
    def add_trade(self, trade: Trade):
        self.trades.append(trade)
        self._recalculate()
    
    def _recalculate(self):
        if not self.trades:
            return
        
        self.start_time = min(t.open_time for t in self.trades)
        self.end_time = max(t.close_time for t in self.trades)
        self.center_price = np.mean([t.open_price for t in self.trades])
        self.total_profit = sum(t.profit for t in self.trades)
    
    @property
    def is_win(self) -> bool:
        return self.total_profit > 0
    
    @property
    def trade_count(self) -> int:
        return len(self.trades)
    
    def matches(self, trade: Trade) -> bool:
        """Check if trade belongs to this battle"""
        if not self.trades:
            return True
        
        # Time check
        time_diff = abs((trade.open_time - self.start_time).total_seconds())
        if time_diff > BATTLE_TIME_THRESHOLD:
            return False
        
        # Price check
        price_diff = abs(trade.open_price - self.center_price)
        if price_diff > BATTLE_PRICE_THRESHOLD:
            return False
        
        return True

@dataclass
class NewsEvent:
    """News event for marking on chart"""
    event_time: datetime
    currency: str
    impact: str
    event_name: str

@dataclass
class TokenUsage:
    """Track API token usage and costs"""
    date: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float

# =============================================================================
# DATABASE QUERIES
# =============================================================================

class DataLoader:
    """Load data from SQLite database"""
    
    def __init__(self, db_path: Path = DB_FILE):
        self.db_path = db_path
    
    def get_trades_for_period(self, start: datetime, end: datetime) -> List[Trade]:
        """Get trades within a specific time range"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if trades table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='trades'
        """)
        
        if not cursor.fetchone():
            conn.close()
            return []
        
        cursor.execute("""
            SELECT * FROM trades 
            WHERE close_time BETWEEN ? AND ?
            ORDER BY open_time
        """, (start.isoformat(), end.isoformat()))
        
        trades = []
        for row in cursor.fetchall():
            try:
                trades.append(Trade(
                    ticket=row['ticket'],
                    symbol=row['symbol'],
                    order_type=row['order_type'],
                    volume=row['volume'],
                    open_price=row['open_price'],
                    close_price=row['close_price'] or row['open_price'],
                    profit=row['profit'] or 0,
                    open_time=datetime.fromisoformat(row['open_time']),
                    close_time=datetime.fromisoformat(row['close_time']) if row['close_time'] else datetime.now()
                ))
            except Exception as e:
                logger.warning(f"Error parsing trade: {e}")
        
        conn.close()
        return trades

    def get_yesterday_trades(self) -> List[Trade]:
        """Get all trades from yesterday"""
        yesterday = datetime.now() - timedelta(days=1)
        start = yesterday.replace(hour=config.reset_hour, minute=0, second=0)
        end = start + timedelta(days=1)
        return self.get_trades_for_period(start, end)

    def get_today_trades(self) -> List[Trade]:
        """Get all trades from today (since reset time until now)"""
        now = datetime.now()
        start = now.replace(hour=config.reset_hour, minute=0, second=0)
        
        # If currently before reset time, 'today' means 'since yesterday's reset'
        if now.hour < config.reset_hour:
            start -= timedelta(days=1)
            
        end = now
        return self.get_trades_for_period(start, end)
    
    def get_ticks_range(self, start: datetime, end: datetime, 
                        symbol: str = None) -> List[Dict]:
        """Get tick data for time range"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute("""
                SELECT timestamp, bid, ask FROM ticks 
                WHERE timestamp BETWEEN ? AND ? AND symbol = ?
                ORDER BY timestamp
            """, (start.isoformat(), end.isoformat(), symbol))
        else:
            cursor.execute("""
                SELECT timestamp, bid, ask FROM ticks 
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp
            """, (start.isoformat(), end.isoformat()))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_news_for_period(self, start: datetime, end: datetime,
                            impact_filter: str = 'High') -> List[NewsEvent]:
        """Get news events for time period"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM news 
            WHERE event_time BETWEEN ? AND ? AND impact = ?
            ORDER BY event_time
        """, (start.isoformat(), end.isoformat(), impact_filter))
        
        events = []
        for row in cursor.fetchall():
            events.append(NewsEvent(
                event_time=datetime.fromisoformat(row['event_time']),
                currency=row['currency'],
                impact=row['impact'],
                event_name=row['event_name']
            ))
        
        conn.close()
        return events

# =============================================================================
# BATTLE CLUSTERING
# =============================================================================

def cluster_trades_into_battles(trades: List[Trade]) -> List[Battle]:
    """Group trades within 15 min / $2 range into battles"""
    if not trades:
        return []
    
    # Sort by open time
    sorted_trades = sorted(trades, key=lambda t: t.open_time)
    
    battles = []
    current_battle = Battle()
    
    for trade in sorted_trades:
        if current_battle.matches(trade):
            current_battle.add_trade(trade)
        else:
            # Save current battle if not empty
            if current_battle.trades:
                battles.append(current_battle)
            
            # Start new battle
            current_battle = Battle()
            current_battle.add_trade(trade)
    
    # Don't forget last battle
    if current_battle.trades:
        battles.append(current_battle)
    
    logger.info(f"Clustered {len(trades)} trades into {len(battles)} battles")
    return battles

# =============================================================================
# CHART GENERATOR
# =============================================================================

class ChartGenerator:
    """Generate advanced trading analysis charts (AI-Optimized)"""
    
    def __init__(self, data_loader: DataLoader):
        self.loader = data_loader
    
    def _get_mt5_data(self, symbol: str, timeframe, start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch candle data from MT5"""
        from utils.mt5_connect import get_mt5_manager
        manager = get_mt5_manager()
        
        if not manager.ensure_connected():
            logger.error("MT5 connection failed for chart generation")
            return pd.DataFrame()
                
        rates = mt5.copy_rates_range(symbol, timeframe, start, end)
        if rates is None or len(rates) == 0:
            return pd.DataFrame()
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        # Add EMAs
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        return df

    def _draw_candlestick(self, ax, df, show_ema=True, show_sessions=True):
        """Draw text-book style candlesticks with dynamic width"""
        if df.empty:
            return

        up_color = '#00d26a'
        down_color = '#ff4757'
        
        # Calculate dynamic width based on timeframe
        # df.index is DatetimeIndex. Matplotlib uses days as units.
        if len(df) > 1:
            avg_delta = (df.index[1] - df.index[0]).total_seconds()
            # Convert seconds to days (1 day = 86400 sec)
            # Use 70% of the candle duration as width
            width = (avg_delta / 86400) * 0.7
            width2 = width * 0.1
        else:
            width = 0.0004 # default to ~30 sec
            width2 = width * 0.1
        
        up = df[df.close >= df.open]
        down = df[df.close < df.open]
        
        # Wicks
        ax.bar(up.index, up.high - up.low, width2, bottom=up.low, color=up_color)
        ax.bar(down.index, down.high - down.low, width2, bottom=down.low, color=down_color)
        
        # Bodies
        ax.bar(up.index, up.close - up.open, width, bottom=up.open, color=up_color)
        ax.bar(down.index, down.open - down.close, width, bottom=down.close, color=down_color)
        
        # EMAs
        if show_ema:
            if 'ema20' in df.columns:
                ax.plot(df.index, df['ema20'], color='#00b4d8', linewidth=1.0, alpha=0.8, label='EMA 20')
            if 'ema50' in df.columns:
                ax.plot(df.index, df['ema50'], color='#ffd60a', linewidth=1.0, alpha=0.8, label='EMA 50')

    def generate_battle_chart(self, battle: Battle, news_events: List[NewsEvent] = None) -> Path:
        """
        Generate 4-Panel Multi-Timeframe Chart for AI Analysis
        (Top-Left: H1, Top-Right: M15, Bottom-Left: M5, Bottom-Right: M1)
        """
        symbol = battle.trades[0].symbol if battle.trades else self.loader.config.symbol
        
        # Define ranges: M1/M5 cover the battle, H1/M15 give context
        end_time = battle.end_time + timedelta(minutes=15)
        
        # Data requirements
        specs = [
            ('H1', mt5.TIMEFRAME_H1, timedelta(hours=48)),
            ('M15', mt5.TIMEFRAME_M15, timedelta(hours=12)),
            ('M5', mt5.TIMEFRAME_M5, timedelta(hours=4)),
            ('M1', mt5.TIMEFRAME_M1, timedelta(minutes=60)) 
        ]
        
        data = {}
        for name, tf, delta in specs:
            start_time = end_time - delta
            df = self._get_mt5_data(symbol, tf, start_time, end_time)
            data[name] = df
            
        if data['M1'].empty:
            logger.warning("No M1 data for chart")
            return None
            
        # Create 4-panel figure
        fig = plt.figure(figsize=(16, 12), facecolor='#0d1117')
        fig.subplots_adjust(hspace=0.3, wspace=0.2)
        
        panels = [
            ('H1', 221, "Trend Context"),
            ('M15', 222, "Market Structure"),
            ('M5', 223, "Setup Zone"),
            ('M1', 224, "Entry Execution")
        ]
        
        for name, pos, title in panels:
            ax = fig.add_subplot(pos)
            df = data.get(name)
            
            if df is None or df.empty:
                ax.text(0.5, 0.5, "No Data", color='white', ha='center')
                continue
                
            ax.set_facecolor('#0d1117')
            ax.set_title(f"{name} - {title}", color='#e6edf3', fontsize=10, fontweight='bold')
            
            # Draw Candles
            self._draw_candlestick(ax, df, show_ema=True)
            
            # Draw Trades (Overlay logic)
            # Only draw trades on M1 and M5 to avoid clutter
            if name in ['M1', 'M5']:
                for trade in battle.trades:
                    # Use trade times directly (test script already uses MT5 time)
                    t_open = trade.open_time
                    t_close = trade.close_time
                    
                    # Check visibility (at least one point in range)
                    chart_start = df.index[0]
                    chart_end = df.index[-1]
                    is_entry_visible = chart_start <= t_open <= chart_end
                    is_exit_visible = chart_start <= t_close <= chart_end
                    
                    if not (is_entry_visible or is_exit_visible):
                        continue  # Skip if completely outside
                    
                    color = '#00ff88' if trade.profit >= 0 else '#ff4757'
                    
                    # 1. Dashed Connector Line (Entry -> Exit)
                    ax.plot([t_open, t_close], 
                            [trade.open_price, trade.close_price],
                            color=color, linestyle='--', linewidth=1.5, alpha=0.8, zorder=3)
                    
                    # 2. Entry Arrow (▲ = BUY, ▼ = SELL)
                    if is_entry_visible:
                        marker = '^' if trade.order_type == 'BUY' else 'v'
                        ax.plot(t_open, trade.open_price, 
                                marker=marker, color=color, 
                                markersize=12, markeredgecolor='white', markeredgewidth=1.5, zorder=5)
                    
                    # 3. Exit X Marker
                    if is_exit_visible:
                        ax.plot(t_close, trade.close_price, 
                                marker='X', color='white', 
                                markersize=10, markeredgecolor=color, markeredgewidth=1.5, zorder=5)
                        
                        # 4. P&L Label Box
                        ax.annotate(
                            f'${trade.profit:+.2f}',
                            xy=(t_close, trade.close_price),
                            xytext=(8, 12 if trade.profit >= 0 else -12),
                            textcoords='offset points',
                            fontsize=9, fontweight='bold', color='white',
                            bbox=dict(boxstyle='round,pad=0.3', fc=color, ec='none', alpha=0.9),
                            zorder=6
                        )

            # Draw News
            if news_events and name in ['M5', 'M1']:
                for news in news_events:
                    if df.index[0] <= news.event_time <= df.index[-1]:
                        ax.axvline(x=news.event_time, color='#ffd32a', linestyle=':', linewidth=1.5, alpha=0.7)

            # Grid and Formatting
            ax.grid(True, color='#30363d', linestyle='--', linewidth=0.5, alpha=0.5)
            ax.tick_params(colors='#8b949e', labelsize=8)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            
        # Overall Title
        fig.suptitle(f'{symbol} Battle Analysis | P&L: ${battle.total_profit:+.2f}', color='white', fontsize=14, fontweight='bold')
        
        path = CHART_DIR / f"battle_{battle.start_time.strftime('%Y%m%d_%H%M%S')}.png"
        fig.savefig(path, facecolor='#0d1117')
        plt.close(fig)
        return path

    def generate_daily_summary_chart(self, battles: List[Battle]) -> Path:
        """Simple P&L curve chart for daily summary"""
        if not battles:
            return None
        
        fig, ax = plt.subplots(figsize=(12, 4), facecolor='#1a1a2e')
        ax.set_facecolor('#16213e')
        
        # Calculate cumulative P&L
        times = []
        pnls = []
        cumulative = 0
        
        for battle in sorted(battles, key=lambda b: b.end_time):
            for trade in sorted(battle.trades, key=lambda t: t.close_time):
                cumulative += trade.profit
                times.append(trade.close_time)
                pnls.append(cumulative)
        
        # Plot P&L curve
        colors = ['#00ff88' if p >= 0 else '#ff4757' for p in pnls]
        ax.fill_between(times, pnls, alpha=0.3, color='#00d4ff')
        ax.plot(times, pnls, color='#00d4ff', linewidth=2)
        
        # Zero line
        ax.axhline(y=0, color='white', linestyle='-', alpha=0.5)
        
        # Formatting
        final_pnl = pnls[-1] if pnls else 0
        result_color = '#00ff88' if final_pnl >= 0 else '#ff4757'
        ax.set_title(
            f"Daily P&L Curve | Final: ${final_pnl:+.2f}",
            color=result_color, fontsize=14, fontweight='bold'
        )
        ax.set_xlabel('Time', color='white')
        ax.set_ylabel('Cumulative P&L ($)', color='white')
        ax.tick_params(colors='white')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.grid(True, alpha=0.2, color='white')
        
        plt.tight_layout()
        
        filename = f"daily_pnl_{datetime.now().strftime('%Y%m%d')}.png"
        filepath = CHART_DIR / filename
        plt.savefig(filepath, dpi=150, facecolor='#1a1a2e')
        plt.close()
        
        return filepath

# =============================================================================
# AI ANALYZER (OpenRouter)
# =============================================================================

class AIAnalyzer:
    """AI-powered trade analysis via OpenRouter"""
    
    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    def __init__(self):
        self.config = get_config()
        self.token_usage = []
    
    def _load_token_usage(self) -> List[Dict]:
        """Load historical token usage"""
        if TOKEN_USAGE_FILE.exists():
            with open(TOKEN_USAGE_FILE, 'r') as f:
                return json.load(f)
        return []
    
    def _save_token_usage(self, usage: TokenUsage):
        """Save token usage to file"""
        history = self._load_token_usage()
        history.append({
            'date': usage.date,
            'model': usage.model,
            'prompt_tokens': usage.prompt_tokens,
            'completion_tokens': usage.completion_tokens,
            'total_tokens': usage.total_tokens,
            'estimated_cost': usage.estimated_cost
        })
        
        with open(TOKEN_USAGE_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    
    def _estimate_cost(self, model: str, prompt_tokens: int, 
                       completion_tokens: int) -> float:
        """Estimate API cost based on model"""
        # Approximate costs per 1M tokens (varies by model)
        costs = {
            'google/gemini-2.0-flash-001': {'input': 0.075, 'output': 0.30},
            'openai/gpt-4o-mini': {'input': 0.15, 'output': 0.60},
            'default': {'input': 0.50, 'output': 1.50}
        }
        
        rates = costs.get(model, costs['default'])
        cost = (prompt_tokens * rates['input'] + completion_tokens * rates['output']) / 1_000_000
        return round(cost, 6)
    
    def analyze_battle(self, battle: Battle, news_context: str = "",
                       chart_base64: str = None) -> Optional[str]:
        """
        Send battle data to AI for analysis.
        Returns analysis text or None on failure.
        """
        if not self.config.openrouter_api_key:
            logger.warning("OpenRouter API key not configured")
            return None
        
        # Build prompt
        trade_summary = "\n".join([
            f"  - {t.order_type} {t.volume} @ {t.open_price} -> {t.close_price} = ${t.profit:+.2f}"
            for t in battle.trades
        ])
        
        prompt = f"""วิเคราะห์การเทรดใน Battle นี้ให้หน่อย:

**Battle Summary:**
- เวลา: {battle.start_time.strftime('%H:%M')} - {battle.end_time.strftime('%H:%M')}
- จำนวนไม้: {battle.trade_count}
- กำไร/ขาดทุนรวม: ${battle.total_profit:+.2f}

**รายละเอียดเทรด:**
{trade_summary}

**บริบทข่าว:** {news_context if news_context else 'ไม่มีข่าวสำคัญ'}

**คำถาม:**
1. ฉันใช้อารมณ์หรือเทคนิค?
2. การเข้าหลายไม้ซ้อนกันมีเหตุผลไหม?
3. Order Flow สนับสนุนทิศทางไหม?

**กรุณาระบุ:**
- 3 ข้อผิดพลาดสำคัญ (ถ้ามี)
- 3 สิ่งที่ควรปรับปรุง
- คะแนนวินัย 1-10
"""

        # Build messages
        messages = [
            {
                "role": "system",
                "content": "คุณคือ Trading Coach ที่เชี่ยวชาญใน SMC และ Order Flow ช่วยวิเคราะห์การเทรดอย่างตรงไปตรงมาแต่ให้กำลังใจ"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # Add image if provided
        if chart_base64:
            messages[1]["content"] = [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{chart_base64}"
                    }
                }
            ]
        
        # Try primary model, fallback if needed
        models_to_try = [
            self.config.openrouter_model,
            self.config.openrouter_fallback_model
        ]
        
        for model in models_to_try:
            try:
                response = requests.post(
                    self.OPENROUTER_URL,
                    headers={
                        "Authorization": f"Bearer {self.config.openrouter_api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://project-sentinel.local",
                        "X-Title": "Project Sentinel"
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": self.config.ai_max_tokens,
                        "temperature": self.config.ai_temperature
                    },
                    timeout=60
                )
                
                response.raise_for_status()
                data = response.json()
                
                # Extract response
                content = data['choices'][0]['message']['content']
                
                # Track usage
                usage = data.get('usage', {})
                prompt_tokens = usage.get('prompt_tokens', 0)
                completion_tokens = usage.get('completion_tokens', 0)
                total_tokens = prompt_tokens + completion_tokens
                cost = self._estimate_cost(model, prompt_tokens, completion_tokens)
                
                token_usage = TokenUsage(
                    date=datetime.now().isoformat(),
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    estimated_cost=cost
                )
                self._save_token_usage(token_usage)
                
                logger.info(f"AI analysis complete: {total_tokens} tokens, ${cost:.4f}")
                
                # Check cost alert
                if cost > self.config.cost_alert_threshold:
                    logger.warning(f"Cost alert! ${cost:.4f} exceeds threshold")
                
                return content
                
            except requests.RequestException as e:
                logger.warning(f"AI request failed with {model}: {e}")
                continue
        
        logger.error("All AI models failed")
        return None

# =============================================================================
# DISCORD NOTIFIER
# =============================================================================

class DiscordNotifier:
    """Send reports via Discord Webhook"""
    
    def __init__(self):
        self.config = get_config()

    def send_message(self, message: str, image_path: Path = None) -> bool:
        """
        Send message to Discord using Embeds to handle long reports.
        Splits report by '━━━ Battle' logic to avoid 2000 char limits.
        """
        token = self.config.discord_bot_token
        channel_id = self.config.discord_channel_id
        
        if not token or not channel_id:
            logger.warning("Discord Bot Token or Channel ID not configured")
            return False
            
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        headers = {"Authorization": f"Bot {token}"}

        # 1. PARSE REPORT INTO SECTIONS
        # The report format is known: "Summary" then "━━━ Battle #1" ...
        sections = []
        
        # Split by Battle separator
        raw_chunks = message.split('━━━ Battle')
        
        # First chunk is the Summary (plus header)
        sections.append({
            "title": "📊 AI DAILY REPORT",
            "description": raw_chunks[0],
            "color": 0x00d4ff # Cyan
        })
        
        # Subsequent chunks are Battles
        for i, chunk in enumerate(raw_chunks[1:], 1):
            sections.append({
                "title": f"⚔️ Battle #{i}",
                "description": f"━━━ Battle{chunk}", # Re-add prefix for context
                "color": 0xff9f1c # Orange
            })

        # 2. SEND SECTIONS SEQUENTIALLY
        success_all = True
        
        for i, section in enumerate(sections):
            embed = {
                "title": section["title"],
                "description": section["description"],
                "color": section["color"],
                "footer": {"text": "Project Sentinel AI Coach 🤖"}
            }
            
            # If description is still too long (>4096), we must chunk it brutally
            # (Unlikely with per-battle splitting, but safety first)
            if len(embed["description"]) > 4000:
                embed["description"] = embed["description"][:4000] + "\n...(truncated)"
            
            # Prepare payload
            payload = {"embeds": [embed]}
            
            # Attach image ONLY to the very last message
            files = {}
            if i == len(sections) - 1 and image_path and image_path.exists():
                files = {
                    "file": (image_path.name, open(image_path, "rb"), "image/png")
                }
            
            try:
                response = requests.post(
                    url, headers=headers, json=payload if not files else None,
                    data={"payload_json": json.dumps(payload)} if files else None, # Multipart trick
                    files=files,
                    timeout=30
                )
                
                if files:
                    files["file"][1].close()
                
                if response.status_code not in [200, 201]:
                    logger.error(f"Discord API Error {response.status_code}: {response.text}")
                    # Fallback to plain text if Embed fails? No, retry logic usually better but let's log.
                    success_all = False
                
            except requests.RequestException as e:
                logger.error(f"Discord notification failed: {e}")
                success_all = False
                
            # Rate limit protection
            time.sleep(1.0) 

        if success_all:
            logger.info("Discord report sent successfully (Split into Embeds)")
            return True
        return False

    def send_report_segments(self, segments: List[Dict]) -> bool:
        """
        Send a structured list of report segments.
        Each segment dict:
        {
            "title": str,
            "description": str,
            "color": int,
            "image_path": Path (optional),
            "footer": str (optional)
        }
        """
        token = self.config.discord_bot_token
        channel_id = self.config.discord_channel_id
        
        if not token or not channel_id:
            logger.warning("Discord Bot Token/Channel ID not configured")
            return False
            
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        headers = {"Authorization": f"Bot {token}"}
        
        success_all = True
        
        for i, segment in enumerate(segments):
            # Construct Embed
            embed = {
                "title": segment.get("title", ""),
                "description": segment.get("description", ""),
                "color": segment.get("color", 0x3498db),
                "footer": {"text": segment.get("footer", "Project Sentinel AI Coach 🤖")}
            }
            
            # Truncate description if needed (Discord limit 4096)
            if len(embed["description"]) > 4000:
                embed["description"] = embed["description"][:4000] + "\n...(truncated)"
                
            payload = {"embeds": [embed]}
            
            # Handle Image
            files = {}
            img_path = segment.get("image_path")
            if img_path and isinstance(img_path, Path) and img_path.exists():
                files = {
                    "file": (img_path.name, open(img_path, "rb"), "image/png")
                }
                
            try:
                # Send request
                if files:
                    response = requests.post(
                        url, headers=headers, 
                        data={"payload_json": json.dumps(payload)}, 
                        files=files, timeout=30
                    )
                else:
                    response = requests.post(
                        url, headers=headers, json=payload, timeout=30
                    )
                    
                # Close file handle
                if files:
                    files["file"][1].close()
                    
                if response.status_code not in [200, 201]:
                    logger.error(f"Discord API Error {response.status_code}: {response.text}")
                    success_all = False
            
            except Exception as e:
                logger.error(f"Failed to send segment {i}: {e}")
                success_all = False
                
            # Rate limit pause
            time.sleep(1.0)
            
        if success_all:
            logger.info(f"Successfully sent {len(segments)} report segments")
            return True
        return False

# =============================================================================
# JOURNAL MANAGER (Staging)
# =============================================================================

class JournalManager:
    """Manages trading journal, staging, and manual analysis"""
    
    def __init__(self):
        self.config = get_config()
        # Create DB manager
        db_path = Path(__file__).parent / "database" / "sentinel_data.db"
        self.db = DatabaseManager(db_path)
        
        # Reuse existing components
        self.loader = DataLoader()
        self.chart_gen = ChartGenerator(self.loader)
        self.ai = AIAnalyzer()
        
    def sync_battles(self) -> List[Dict]:
        """
        Sync today's trades into battles and create/update journal entries.
        Returns list of journal entries (merged with pending status).
        """
        # 1. Get today's trades
        trades = self.loader.get_today_trades()
        if not trades:
            return []
            
        # 2. Cluster into battles
        # We assume cluster_trades_into_battles is available or we define it locally
        try:
            battles = cluster_trades_into_battles(trades)
        except NameError:
            # Fallback if function not found (should be defined in this file)
            battles = self._cluster_trades_fallback(trades)
            
        synced_entries = []
        
        for battle in battles:
            # Generate deterministic ID based on start time
            battle_id = f"B_{battle.start_time.strftime('%Y%m%d_%H%M%S')}"
            
            # Key Metrics
            pnl = battle.total_profit
            count = len(battle.trades)
            
            # Check if exists
            existing = self.db.get_journal_entry(battle_id)
            
            if not existing:
                # Create new pending entry
                entry = {
                    'battle_id': battle_id,
                    'pnl': pnl,
                    'trade_count': count,
                    'start_time': battle.start_time.isoformat(),
                    'end_time': battle.end_time.isoformat(),
                    'status': 'pending',
                    'strategy_tag': 'Unspecified',
                    'user_notes': '',
                    'emotion_score': 0
                }
                self.db.save_journal_entry(entry)
                synced_entries.append(entry)
            else:
                synced_entries.append(existing)
                
        return synced_entries

    def update_context(self, battle_id: str, strategy: str, notes: str, emotion: int) -> bool:
        """Update user context for a battle"""
        existing = self.db.get_journal_entry(battle_id)
        if not existing:
            return False
            
        existing['strategy_tag'] = strategy
        existing['user_notes'] = notes
        existing['emotion_score'] = emotion
        
        return self.db.save_journal_entry(existing)

    def analyze_staged_battle(self, battle_id: str) -> bool:
        """Run AI analysis on a specific staged battle"""
        # 1. Get entry
        entry = self.db.get_journal_entry(battle_id)
        if not entry:
            return False
            
        # 2. Reconstruct Battle Object
        # We need to reload trades. For simplicity, we assume trades are in DB
        # This is a bit tricky, but we can search trades by time range approx
        start = datetime.fromisoformat(entry['start_time'])
        end = datetime.fromisoformat(entry['end_time'])
        
        # Add buffer to ensure we get all trades
        trades = self.loader.get_trades_for_period(
            start - timedelta(seconds=1), 
            end + timedelta(seconds=1)
        )
        
        if not trades:
            print(f"No trades found for battle {battle_id}")
            return False
            
        battle = Battle(start, end, trades, entry['pnl'])
        
        # 3. Generate Chart (if not exists)
        news = self.loader.get_news_for_period(
            start - timedelta(hours=1), end + timedelta(minutes=30)
        )
        news_context = ", ".join([f"{n.currency} {n.event_name}" for n in news])
        
        chart_path = self.chart_gen.generate_battle_chart(battle, news)
        
        # 4. Prepare AI Context
        chart_base64 = None
        if chart_path and chart_path.exists():
            with open(chart_path, 'rb') as f:
                chart_base64 = base64.b64encode(f.read()).decode()
        
        # Inject User Context
        user_context = f"""
        User Strategy: {entry.get('strategy_tag', 'N/A')}
        User Notes: "{entry.get('user_notes', '-')}"
        Emotion Score: {entry.get('emotion_score', 0)}/5
        """
        
        # 5. Analyze
        # Modifying prompt context slightly by appending user context
        final_context = f"{news_context}\n\nUSER CONTEXT:\n{user_context}"
        
        analysis_text = self.ai.analyze_battle(battle, final_context, chart_base64)
        
        if analysis_text:
            # Update DB with analysis
            self.db.update_journal_analysis(battle_id, {
                'ai_analysis': analysis_text,
                'ai_coaching': 'See analysis', # Placeholder
                'ai_grade': 'C' # Placeholder
            })
            return True
            
        return False

    def _cluster_trades_fallback(self, trades: List[Trade]) -> List[Battle]:
        """Simple clustering if main function missing"""
        if not trades: return []
        sorted_trades = sorted(trades, key=lambda t: t.open_time)
        battles = []
        current_battle_trades = []
        
        for trade in sorted_trades:
            if not current_battle_trades:
                current_battle_trades.append(trade)
                continue
                
            last_trade = current_battle_trades[-1]
            time_diff = (trade.open_time - last_trade.close_time).total_seconds() / 60
            
            if time_diff <= 15:
                current_battle_trades.append(trade)
            else:
                start = min(t.open_time for t in current_battle_trades)
                end = max(t.close_time for t in current_battle_trades)
                pnl = sum(t.profit for t in current_battle_trades)
                battles.append(Battle(start, end, current_battle_trades, pnl))
                current_battle_trades = [trade]
                
        if current_battle_trades:
            start = min(t.open_time for t in current_battle_trades)
            end = max(t.close_time for t in current_battle_trades)
            pnl = sum(t.profit for t in current_battle_trades)
            battles.append(Battle(start, end, current_battle_trades, pnl))
            
        return battles

# =============================================================================
# REPORT GENERATOR
# =============================================================================

class DailyReportGenerator:
    """Main report generation coordinator"""
    
    def __init__(self):
        self.loader = DataLoader()
        self.chart_gen = ChartGenerator(self.loader)
        self.ai = AIAnalyzer()
        self.discord_notifier = DiscordNotifier()
    
    def send_notification(self, message: str, image_path: Path = None):
        """Send to configured channels (Discord)"""
        sent = False
        
        if self.discord_notifier.send_message(message, image_path):
            sent = True
            
        if not sent:
            logger.warning("No notifications sent (check config)")
            
    def generate_report(self, mode: str = 'YESTERDAY') -> bool:
        """Generate and send daily report (mode: 'YESTERDAY' or 'TODAY')"""
        logger.info("=" * 50)
        logger.info(f"Starting Report Generation (Mode: {mode})")
        logger.info("=" * 50)
        
        # 1. Load trades based on mode
        if mode == 'TODAY':
            trades = self.loader.get_today_trades()
            report_title = "📊 CURRENT SESSION REPORT (Today)"
            no_trades_msg = "No trades found for today's session"
        else:
            trades = self.loader.get_yesterday_trades()
            report_title = "📊 DAILY TRADING REPORT (Yesterday)"
            no_trades_msg = "No trades found for yesterday"
        
        if not trades:
            logger.info(f"{no_trades_msg} - sending simple summary")
            self.send_notification(f"\n{report_title}: {no_trades_msg}")
            return True
        
        logger.info(f"Loaded {len(trades)} trades")
        
        # 2. Cluster into battles
        battles = cluster_trades_into_battles(trades)
        
        # 3. Generate daily P&L chart
        pnl_chart = self.chart_gen.generate_daily_summary_chart(battles)
        
        # 4. Analyze each battle
        analyses = []
        
        for i, battle in enumerate(battles):
            logger.info(f"Processing battle {i+1}/{len(battles)}")
            
            # Get news context
            news = self.loader.get_news_for_period(
                battle.start_time - timedelta(hours=1),
                battle.end_time + timedelta(minutes=30)
            )
            news_context = ", ".join([f"{n.currency} {n.event_name}" for n in news])
            
            # Generate chart
            chart_path = self.chart_gen.generate_battle_chart(battle, news)
            
            # Read chart as base64 for AI
            chart_base64 = None
            if chart_path and chart_path.exists():
                with open(chart_path, 'rb') as f:
                    chart_base64 = base64.b64encode(f.read()).decode()
            
            # AI analysis
            analysis = self.ai.analyze_battle(battle, news_context, chart_base64)
            
            if analysis:
                analyses.append({
                    'battle': battle,
                    'analysis': analysis,
                    'chart': chart_path
                })
        
        # 5. Build final report
        total_pnl = sum(t.profit for t in trades)
        wins = sum(1 for t in trades if t.profit > 0)
        losses = len(trades) - wins
        
        # 5. Build Report Segments (Structured Delivery)
        segments = []
        
        # Segment 1: Daily Summary
        summary_text = f"""
{report_title}
━━━━━━━━━━━━━━━━━━━━━

📈 Summary:
• Total Trades: {len(trades)}
• Win Rate: {wins}/{len(trades)} ({100*wins/len(trades):.1f}%)
• Net P&L: ${total_pnl:+.2f}
• Battles: {len(battles)}
"""
        segments.append({
            "title": "📊 AI DAILY REPORT",
            "description": summary_text,
            "color": 0x00d4ff, # Cyan
            "image_path": pnl_chart
        })
        
        # Segment 2..N: Battle Analysis
        for i, item in enumerate(analyses):
            segments.append({
                "title": f"⚔️ Battle #{i+1}",
                "description": f"{item['analysis']}",
                "color": 0xff9f1c, # Orange
                "image_path": item['chart'] # Attach specific battle chart!
            })
        
        # 6. Send via Discord (Structured)
        # 6. Send via Discord (Structured)
        logger.info(f"Sending {len(segments)} report segments to Discord (VERSION 2.0)...")
        self.discord_notifier.send_report_segments(segments)
        
        return True
        
        logger.info("Daily report complete!")
        return True

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  PROJECT SENTINEL - DAILY REPORT GENERATOR")
    print("=" * 60)
    print(f"  Database: {DB_FILE}")
    print(f"  Charts: {CHART_DIR}")
    print("=" * 60)
    
    generator = DailyReportGenerator()
    generator.generate_report()

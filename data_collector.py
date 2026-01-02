"""
===============================================================================
PROJECT SENTINEL - DATA COLLECTOR
===============================================================================
Continuously collects XAUUSD tick data and scrapes economic calendar.
Stores data in SQLite database for AI analysis.

Author: Project Sentinel
Hardware: Intel N95 Mini PC (optimized for memory efficiency)
Platform: Python 3.9+ / MetaTrader 5 (Exness)
===============================================================================
"""

import MetaTrader5 as mt5
import sqlite3
import time
import requests
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import deque
import threading
import json

# =============================================================================
# CONFIGURATION
# =============================================================================

# ---- Symbol to Record ----
SYMBOL = "XAUUSDm"  # Exness cent account symbol

# ---- Database Settings ----
DB_DIR = Path(__file__).parent / "database"
DB_DIR.mkdir(exist_ok=True)
DB_FILE = DB_DIR / "sentinel_data.db"

# ---- Tick Collection ----
TICK_BATCH_SIZE = 1000          # Insert every N ticks (memory efficient)
TICK_POLL_INTERVAL = 0.1        # Seconds between tick checks
MAX_TICKS_IN_MEMORY = 5000      # Safety limit before force-flush

# ---- News Scraping ----
NEWS_SCRAPE_INTERVAL = 3600     # 1 hour in seconds
FOREX_FACTORY_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

# ---- Connection Settings ----
MT5_RECONNECT_DELAY = 5
MT5_MAX_RECONNECT_ATTEMPTS = 10

# ---- Logging ----
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TickRecord:
    """Single tick data point"""
    timestamp: datetime
    symbol: str
    bid: float
    ask: float
    volume: int
    flags: int

@dataclass
class NewsEvent:
    """Economic calendar event"""
    event_time: datetime
    currency: str
    impact: str  # 'High', 'Medium', 'Low'
    event_name: str
    actual: str
    forecast: str
    previous: str

# =============================================================================
# DATABASE MANAGER
# =============================================================================

class DatabaseManager:
    """Handles SQLite database operations"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Create tables if they don't exist"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            # Enable WAL mode for better concurrent read/write performance
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            
            # Ticks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ticks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    bid REAL NOT NULL,
                    ask REAL NOT NULL,
                    volume INTEGER,
                    flags INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(timestamp, symbol, bid, ask)
                )
            """)
            
            # Create index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ticks_timestamp 
                ON ticks(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ticks_symbol 
                ON ticks(symbol)
            """)
            
            # News table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_time TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    impact TEXT NOT NULL,
                    event_name TEXT NOT NULL,
                    actual TEXT,
                    forecast TEXT,
                    previous TEXT,
                    scraped_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(event_time, currency, event_name)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_news_time 
                ON news(event_time)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_news_impact 
                ON news(impact)
            """)
            
            # Trade log table (for AI analysis)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket INTEGER UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    order_type TEXT NOT NULL,
                    volume REAL NOT NULL,
                    open_price REAL NOT NULL,
                    close_price REAL,
                    profit REAL,
                    open_time TEXT NOT NULL,
                    close_time TEXT,
                    magic INTEGER,
                    comment TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            
        print(f"[DB] Database initialized: {self.db_path}")
    
    def insert_ticks_batch(self, ticks: List[TickRecord]) -> int:
        """Insert batch of ticks, skip duplicates. Returns count inserted."""
        if not ticks:
            return 0
            
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            inserted = 0
            for tick in ticks:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO ticks 
                        (timestamp, symbol, bid, ask, volume, flags)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        tick.timestamp.isoformat(),
                        tick.symbol,
                        tick.bid,
                        tick.ask,
                        tick.volume,
                        tick.flags
                    ))
                    if cursor.rowcount > 0:
                        inserted += 1
                except sqlite3.IntegrityError:
                    pass  # Skip duplicates
            
            conn.commit()
            conn.close()
            
        return inserted
    
    def insert_news_batch(self, news_list: List[NewsEvent]) -> int:
        """Insert batch of news events, skip duplicates. Returns count inserted."""
        if not news_list:
            return 0
            
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            inserted = 0
            for news in news_list:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO news 
                        (event_time, currency, impact, event_name, actual, forecast, previous)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        news.event_time.isoformat(),
                        news.currency,
                        news.impact,
                        news.event_name,
                        news.actual,
                        news.forecast,
                        news.previous
                    ))
                    if cursor.rowcount > 0:
                        inserted += 1
                except sqlite3.IntegrityError:
                    pass
            
            conn.commit()
            conn.close()
            
        return inserted
    
    def get_ticks_range(self, start: datetime, end: datetime, 
                        symbol: str = None) -> List[Dict]:
        """Retrieve ticks within time range"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if symbol:
                cursor.execute("""
                    SELECT * FROM ticks 
                    WHERE timestamp BETWEEN ? AND ? AND symbol = ?
                    ORDER BY timestamp
                """, (start.isoformat(), end.isoformat(), symbol))
            else:
                cursor.execute("""
                    SELECT * FROM ticks 
                    WHERE timestamp BETWEEN ? AND ?
                    ORDER BY timestamp
                """, (start.isoformat(), end.isoformat()))
            
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
        return results
    
    def get_upcoming_news(self, hours_ahead: int = 24, 
                          impact_filter: str = None) -> List[Dict]:
        """Get upcoming news events"""
        now = datetime.now()
        end = now + timedelta(hours=hours_ahead)
        
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if impact_filter:
                cursor.execute("""
                    SELECT * FROM news 
                    WHERE event_time BETWEEN ? AND ? AND impact = ?
                    ORDER BY event_time
                """, (now.isoformat(), end.isoformat(), impact_filter))
            else:
                cursor.execute("""
                    SELECT * FROM news 
                    WHERE event_time BETWEEN ? AND ?
                    ORDER BY event_time
                """, (now.isoformat(), end.isoformat()))
            
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
        return results
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM ticks")
            tick_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM news")
            news_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM ticks")
            tick_range = cursor.fetchone()
            
            conn.close()
            
        return {
            'tick_count': tick_count,
            'news_count': news_count,
            'tick_date_range': tick_range
        }

# =============================================================================
# TICK COLLECTOR
# =============================================================================

class TickCollector:
    """Collects tick data from MT5 in real-time"""
    
    def __init__(self, db: DatabaseManager, symbol: str = SYMBOL):
        self.db = db
        self.symbol = symbol
        self.tick_buffer: deque = deque(maxlen=MAX_TICKS_IN_MEMORY)
        self.last_tick_time: Optional[datetime] = None
        self.total_collected = 0
        self.running = False
    
    def connect(self) -> bool:
        """Connect to MT5"""
        for attempt in range(MT5_MAX_RECONNECT_ATTEMPTS):
            if mt5.initialize():
                # Select symbol
                if not mt5.symbol_select(self.symbol, True):
                    print(f"[TICK] Warning: Could not select {self.symbol}")
                    
                account = mt5.account_info()
                if account:
                    print(f"[TICK] Connected: {account.login} @ {account.server}")
                    return True
            
            print(f"[TICK] Connection attempt {attempt + 1} failed, retrying...")
            time.sleep(MT5_RECONNECT_DELAY)
        
        return False
    
    def disconnect(self):
        """Disconnect from MT5"""
        mt5.shutdown()
        print("[TICK] Disconnected from MT5")
    
    def ensure_connected(self) -> bool:
        """Ensure MT5 connection is alive"""
        if mt5.terminal_info() is None:
            print("[TICK] Connection lost, reconnecting...")
            return self.connect()
        return True
    
    def collect_tick(self) -> Optional[TickRecord]:
        """Get latest tick if new"""
        tick = mt5.symbol_info_tick(self.symbol)
        
        if tick is None:
            return None
        
        tick_time = datetime.fromtimestamp(tick.time)
        
        # Skip if same tick
        if self.last_tick_time == tick_time:
            return None
        
        self.last_tick_time = tick_time
        
        return TickRecord(
            timestamp=tick_time,
            symbol=self.symbol,
            bid=tick.bid,
            ask=tick.ask,
            volume=tick.volume,
            flags=tick.flags
        )
    
    def flush_buffer(self):
        """Write buffered ticks to database"""
        if not self.tick_buffer:
            return
        
        ticks = list(self.tick_buffer)
        self.tick_buffer.clear()
        
        inserted = self.db.insert_ticks_batch(ticks)
        print(f"[TICK] Flushed {inserted}/{len(ticks)} ticks to database")
    
    def run(self, stop_event: threading.Event):
        """Main tick collection loop"""
        print(f"[TICK] Starting collection for {self.symbol}")
        
        if not self.connect():
            print("[TICK] Failed to connect to MT5")
            return
        
        self.running = True
        
        try:
            while not stop_event.is_set():
                if not self.ensure_connected():
                    time.sleep(MT5_RECONNECT_DELAY)
                    continue
                
                tick = self.collect_tick()
                
                if tick:
                    self.tick_buffer.append(tick)
                    self.total_collected += 1
                    
                    # Batch insert when buffer is full
                    if len(self.tick_buffer) >= TICK_BATCH_SIZE:
                        self.flush_buffer()
                
                time.sleep(TICK_POLL_INTERVAL)
                
        except Exception as e:
            print(f"[TICK] Error: {e}")
        finally:
            # Flush remaining ticks
            self.flush_buffer()
            self.disconnect()
            self.running = False
            
        print(f"[TICK] Collection stopped. Total collected: {self.total_collected}")

# =============================================================================
# NEWS SCRAPER
# =============================================================================

class NewsScraper:
    """Scrapes economic calendar from ForexFactory"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.last_scrape: Optional[datetime] = None
        self.running = False
    
    def scrape_forex_factory(self) -> List[NewsEvent]:
        """Fetch economic calendar from ForexFactory JSON API"""
        try:
            response = requests.get(
                FOREX_FACTORY_URL,
                headers={'User-Agent': 'Mozilla/5.0'},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            events = []
            
            for item in data:
                try:
                    # Parse date and time
                    date_str = item.get('date', '')
                    time_str = item.get('time', '')
                    
                    if not date_str:
                        continue
                    
                    # Handle "All Day" events
                    if time_str == 'All Day' or not time_str:
                        time_str = '00:00'
                    
                    # Parse datetime (FF uses Eastern Time)
                    try:
                        event_time = datetime.strptime(
                            f"{date_str} {time_str}", 
                            "%Y-%m-%d %H:%M"
                        )
                    except ValueError:
                        continue
                    
                    # Map impact
                    impact_raw = item.get('impact', 'Low')
                    impact = 'High' if impact_raw == 'High' else \
                             'Medium' if impact_raw == 'Medium' else 'Low'
                    
                    events.append(NewsEvent(
                        event_time=event_time,
                        currency=item.get('country', 'USD'),
                        impact=impact,
                        event_name=item.get('title', 'Unknown'),
                        actual=item.get('actual', ''),
                        forecast=item.get('forecast', ''),
                        previous=item.get('previous', '')
                    ))
                    
                except Exception as e:
                    continue
            
            return events
            
        except requests.RequestException as e:
            print(f"[NEWS] Scrape error: {e}")
            return []
    
    def run(self, stop_event: threading.Event):
        """Main news scraping loop"""
        print("[NEWS] Starting news scraper")
        self.running = True
        
        try:
            while not stop_event.is_set():
                # Check if it's time to scrape
                now = datetime.now()
                should_scrape = (
                    self.last_scrape is None or 
                    (now - self.last_scrape).total_seconds() >= NEWS_SCRAPE_INTERVAL
                )
                
                if should_scrape:
                    print("[NEWS] Scraping economic calendar...")
                    events = self.scrape_forex_factory()
                    
                    if events:
                        # Filter high impact only for logging
                        high_impact = [e for e in events if e.impact == 'High']
                        
                        inserted = self.db.insert_news_batch(events)
                        print(f"[NEWS] Scraped {len(events)} events, "
                              f"inserted {inserted} new, "
                              f"{len(high_impact)} high-impact")
                    else:
                        print("[NEWS] No events retrieved")
                    
                    self.last_scrape = now
                
                # Sleep in small intervals to allow stopping
                for _ in range(60):  # Check every second for 60 seconds
                    if stop_event.is_set():
                        break
                    time.sleep(1)
                    
        except Exception as e:
            print(f"[NEWS] Error: {e}")
        finally:
            self.running = False
            
        print("[NEWS] Scraper stopped")

# =============================================================================
# MAIN COLLECTOR
# =============================================================================

class DataCollector:
    """Main coordinator for all data collection"""
    
    def __init__(self):
        self.db = DatabaseManager(DB_FILE)
        self.tick_collector = TickCollector(self.db, SYMBOL)
        self.news_scraper = NewsScraper(self.db)
        self.stop_event = threading.Event()
        self.threads: List[threading.Thread] = []
    
    def start(self):
        """Start all collectors"""
        print("=" * 60)
        print("  PROJECT SENTINEL - DATA COLLECTOR")
        print("=" * 60)
        print(f"  Symbol: {SYMBOL}")
        print(f"  Database: {DB_FILE}")
        print(f"  Tick batch size: {TICK_BATCH_SIZE}")
        print(f"  News interval: {NEWS_SCRAPE_INTERVAL}s")
        print("=" * 60)
        print()
        
        # Start tick collector thread
        tick_thread = threading.Thread(
            target=self.tick_collector.run,
            args=(self.stop_event,),
            name="TickCollector"
        )
        tick_thread.daemon = True
        tick_thread.start()
        self.threads.append(tick_thread)
        
        # Start news scraper thread
        news_thread = threading.Thread(
            target=self.news_scraper.run,
            args=(self.stop_event,),
            name="NewsScraper"
        )
        news_thread.daemon = True
        news_thread.start()
        self.threads.append(news_thread)
        
        print("[MAIN] All collectors started. Press Ctrl+C to stop.")
        
        # Monitor loop
        try:
            while True:
                time.sleep(60)  # Print stats every minute
                stats = self.db.get_stats()
                print(f"[STATS] Ticks: {stats['tick_count']:,} | "
                      f"News: {stats['news_count']}")
                
        except KeyboardInterrupt:
            print("\n[MAIN] Shutting down...")
            self.stop()
    
    def stop(self):
        """Stop all collectors gracefully"""
        self.stop_event.set()
        
        # Wait for threads to finish
        for thread in self.threads:
            thread.join(timeout=10)
            
        print("[MAIN] All collectors stopped")
        
        # Final stats
        stats = self.db.get_stats()
        print(f"\nFinal Statistics:")
        print(f"  Total ticks: {stats['tick_count']:,}")
        print(f"  Total news events: {stats['news_count']}")
        if stats['tick_date_range'][0]:
            print(f"  Tick date range: {stats['tick_date_range'][0]} to "
                  f"{stats['tick_date_range'][1]}")

# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    collector = DataCollector()
    collector.start()

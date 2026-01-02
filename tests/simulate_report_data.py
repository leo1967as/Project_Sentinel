
import sqlite3
import random
import math
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import get_config

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'sentinel_data.db')

def generate_sine_wave_price(start_price, num_points):
    prices = []
    for i in range(num_points):
        # Create a realistic-looking wiggly line using sine + random noise
        trend = math.sin(i / 50) * 2.0  # Main wave
        noise = random.uniform(-0.5, 0.5) # Jitter
        price = start_price + trend + noise
        prices.append(price)
    return prices

def seed_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"🔌 Connected to DB: {DB_PATH}")
    
    # 1. Clear existing data for today (optional, but cleaner)
    # cursor.execute("DELETE FROM ticks")
    # cursor.execute("DELETE FROM trades")
    # cursor.execute("DELETE FROM news")
    
    now = datetime.now()
    start_time = now - timedelta(hours=2)
    
    # =========================================================================
    # 2. INJECT TICKS (Last 2 hours)
    # =========================================================================
    print("⏳ Injecting 7200 simulated ticks...")
    base_price = 2000.00
    prices = generate_sine_wave_price(base_price, 7200) # 1 tick per sec for 2 hours
    
    ticks_data = []
    for i, price in enumerate(prices):
        t_time = start_time + timedelta(seconds=i)
        bid = round(price, 2)
        ask = round(price + 0.15, 2) # Spread
        # (timestamp, symbol, bid, ask, volume, flags)
        ticks_data.append((t_time.isoformat(), "XAUUSDm", bid, ask, 10, 0))
        
    cursor.executemany(
        "INSERT INTO ticks (timestamp, symbol, bid, ask, volume, flags) VALUES (?, ?, ?, ?, ?, ?)",
        ticks_data
    )
    
    # =========================================================================
    # 3. INJECT TRADES (3 Fake Trades)
    # =========================================================================
    print("💰 Injecting 3 simulated trades...")
    
    # Trade 1: Big Win (Long)
    t1_open = start_time + timedelta(minutes=15)
    t1_close = t1_open + timedelta(minutes=45)
    
    # Trade 2: Small Loss (Short)
    t2_open = start_time + timedelta(minutes=60)
    t2_close = t2_open + timedelta(minutes=10)
    
    # Trade 3: Break Even (Long)
    t3_open = start_time + timedelta(minutes=80)
    t3_close = t3_open + timedelta(minutes=20)
    
    trades = [
        # ticket, symbol, type, vol, open_p, close_p, profit, open_t, close_t, magic, comment
        (1001, "XAUUSDm", "BUY", 0.10, 2000.00, 2005.00, 50.00, t1_open.isoformat(), t1_close.isoformat(), 999999, "Simulated Win"),
        (1002, "XAUUSDm", "SELL", 0.05, 2004.00, 2006.00, -10.00, t2_open.isoformat(), t2_close.isoformat(), 999999, "Simulated Loss"),
        (1003, "XAUUSDm", "BUY", 0.01, 2002.50, 2002.60, 0.10, t3_open.isoformat(), t3_close.isoformat(), 999999, "Simulated BE"),
    ]
    
    # Ensure table exists (just in case)
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
    
    cursor.executemany(
        """INSERT OR REPLACE INTO trades 
           (ticket, symbol, order_type, volume, open_price, close_price, profit, open_time, close_time, magic, comment) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        trades
    )
    
    # =========================================================================
    # 4. INJECT NEWS
    # =========================================================================
    print("📰 Injecting simulated news...")
    
    news_time = start_time + timedelta(minutes=30)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news (
            event_id TEXT PRIMARY KEY,
            time TEXT,
            currency TEXT,
            impact TEXT,
            event TEXT,
            actual TEXT,
            forecast TEXT,
            previous TEXT
        )
    """)
    
    # event_time, currency, impact, event_name, actual, forecast, previous
    news_items = [
        (news_time.isoformat(), "USD", "High", "CPI Data (YoY)", "3.5%", "3.2%", "3.2%")
    ]
    
    cursor.executemany(
        "INSERT OR IGNORE INTO news (event_time, currency, impact, event_name, actual, forecast, previous) VALUES (?, ?, ?, ?, ?, ?, ?)", 
        news_items
    )
    
    conn.commit()
    conn.close()
    print("✅ Simulation data injected successfully!")
    print("👉 Now click 'Generate AI Report' in the GUI.")

if __name__ == "__main__":
    seed_data()

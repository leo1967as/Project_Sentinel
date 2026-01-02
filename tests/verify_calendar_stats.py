
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_collector import DatabaseManager
from daily_report import JournalManager, Trade, DataLoader

# Mock Config (or use partial)
class MockConfig:
    reset_hour = 5 
    # 5 AM reset time

def test_calendar_logic():
    print("running test_calendar_logic...")
    
    # 1. Setup Temp DB
    db_path = Path("tests/temp_calendar_test.db")
    if db_path.exists():
        db_path.unlink()
        
    db = DatabaseManager(db_path)
    # Initialize tables
    db._init_database()
    
    # 2. Insert Test Trades
    # Scenario: 
    # Trade A: May 1st 10:00 AM -> Should be May 1st
    # Trade B: May 2nd 02:00 AM -> Should be May 1st (Before 5 AM)
    # Trade C: May 2nd 06:00 AM -> Should be May 2nd
    
    trades = [
        # Date, Price, PnL
        ("2024-05-01 10:00:00", 100.0, 50.0),   # May 1
        ("2024-05-02 02:00:00", 100.0, -20.0),  # May 1 (Late night)
        ("2024-05-02 06:00:00", 100.0, 100.0),  # May 2
    ]
    
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for t_time, price, pnl in trades:
        # Minimal insert
        cursor.execute("""
            INSERT INTO trades (
                ticket, symbol, order_type, volume, open_price, close_price, 
                open_time, close_time, profit, magic
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            hash(t_time), "XAUUSD", "BUY", 0.1, price, price, 
            t_time, t_time, pnl, 0
        ))
    conn.commit()
    conn.close()
    
    # 3. Test Logic (Simulating JournalManager.get_monthly_stats)
    # We will Implement this function in JournalManager later, 
    # but here we define EXPECTED logic to verify it against.
    
    manager = JournalManager()
    manager.db = db # Inject mock DB
    manager.loader = DataLoader(db_path) # Inject loader with test DB
    # We need to inject config too if main uses it
    manager.config = MockConfig() 
    
    # Expected: 
    # May 1: 50 - 20 = 30
    # May 2: 100
    
    print("Testing get_monthly_stats for May 2024...")
    
    try:
        stats = manager.get_monthly_stats(2024, 5)
        
        print(f"Stats received: {stats}")
        
        # Verify May 1
        day1 = stats.get('2024-05-01')
        if not day1:
            print("[FAIL] Missing data for May 1st")
            sys.exit(1)
            
        if abs(day1['pnl'] - 30.0) > 0.001:
            print(f"[FAIL] May 1st PnL mismatch. Expected 30.0, got {day1['pnl']}")
            sys.exit(1)
            
        # Verify May 2
        day2 = stats.get('2024-05-02')
        if not day2:
            print("[FAIL] Missing data for May 2nd")
            sys.exit(1)
            
        if abs(day2['pnl'] - 100.0) > 0.001:
            print(f"[FAIL] May 2nd PnL mismatch. Expected 100.0, got {day2['pnl']}")
            sys.exit(1)
            
        print("[PASS] Calendar Logic Verified!")
        
    except AttributeError:
        print("[FAIL] Method get_monthly_stats not implemented yet")
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Exception: {e}")
        sys.exit(1)
    finally:
        if db_path.exists():
            db_path.unlink()

if __name__ == "__main__":
    test_calendar_logic()

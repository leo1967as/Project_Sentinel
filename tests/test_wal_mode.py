"""
Test Script: Verify SQLite WAL Mode
Expected: FAIL before fix, PASS after fix
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(r"D:\CodingNoGoogle\ProgramETC\Trading\Project_Sentinel\database\sentinel_data.db")

def test_wal_mode():
    """Check if WAL mode is enabled"""
    if not DB_PATH.exists():
        print(f"[SKIP] Database not found at {DB_PATH}")
        return None
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Query current journal mode
    cursor.execute("PRAGMA journal_mode;")
    result = cursor.fetchone()[0]
    conn.close()
    
    print(f"Current journal_mode: {result}")
    
    if result.lower() == 'wal':
        print("[PASS] WAL mode is enabled ✅")
        return True
    else:
        print(f"[FAIL] Expected 'wal', got '{result}' ❌")
        return False

if __name__ == "__main__":
    test_wal_mode()

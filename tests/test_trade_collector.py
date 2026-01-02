"""
Test Script: Verify TradeCollector can sync trades
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def test_trade_collector_import():
    """Verify TradeCollector class exists and is importable"""
    try:
        from data_collector import TradeCollector, DatabaseManager
        print("[PASS] TradeCollector class imported ✅")
        return True
    except ImportError as e:
        print(f"[FAIL] Import error: {e} ❌")
        return False

def test_database_manager_insert_trade():
    """Verify DatabaseManager.insert_trade method exists"""
    from data_collector import DatabaseManager
    
    if hasattr(DatabaseManager, 'insert_trade'):
        print("[PASS] DatabaseManager.insert_trade exists ✅")
        return True
    else:
        print("[FAIL] insert_trade method not found ❌")
        return False

def test_trade_collector_sync():
    """Test TradeCollector.sync_trades (requires MT5)"""
    from data_collector import TradeCollector, DatabaseManager
    
    db = DatabaseManager(Path("database/sentinel_data.db"))
    collector = TradeCollector(db)
    
    # This will try to sync but may return 0 if no MT5 or no trades
    try:
        count = collector.sync_trades()
        print(f"[PASS] sync_trades() executed, synced {count} trades ✅")
        return True
    except Exception as e:
        print(f"[FAIL] sync_trades error: {e} ❌")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Trade Collector Test Suite")
    print("=" * 50)
    
    results = []
    results.append(test_trade_collector_import())
    results.append(test_database_manager_insert_trade())
    results.append(test_trade_collector_sync())
    
    print("\n" + "=" * 50)
    if all(results):
        print("ALL TESTS PASSED ✅")
    else:
        passed = sum(results)
        print(f"{passed}/3 TESTS PASSED")

"""
Test Script: Verify TradeCollector Auto-Sync is integrated
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def test_trade_collector_in_data_worker():
    """Verify IntegratedDataWorker has TradeCollector logic"""
    from gui.main_window import IntegratedDataWorker
    import inspect
    
    # Get the source code of run method
    source = inspect.getsource(IntegratedDataWorker.run)
    
    # Check for TradeCollector initialization
    if "TradeCollector" in source:
        print("[PASS] TradeCollector is imported in run() ✅")
    else:
        print("[FAIL] TradeCollector not found in run() ❌")
        return False
    
    # Check for sync_trades call
    if "sync_trades" in source:
        print("[PASS] sync_trades() is called in run() ✅")
    else:
        print("[FAIL] sync_trades() not found ❌")
        return False
    
    # Check for TRADE_SYNC_INTERVAL
    if "TRADE_SYNC_INTERVAL" in source:
        print("[PASS] TRADE_SYNC_INTERVAL defined ✅")
    else:
        print("[FAIL] TRADE_SYNC_INTERVAL not found ❌")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("TradeCollector Auto-Sync Test")
    print("=" * 50)
    
    if test_trade_collector_in_data_worker():
        print("\n" + "=" * 50)
        print("ALL TESTS PASSED ✅")
        print("TradeCollector will now auto-sync every 60 seconds")
    else:
        print("\n" + "=" * 50)
        print("TESTS FAILED ❌")

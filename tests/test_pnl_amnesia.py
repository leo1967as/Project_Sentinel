"""
Test Script: Verify PnL Amnesia Fix
Expected: last_reset_date should be calculated from RESET_HOUR, not datetime.now()
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

def test_pnl_amnesia_fix():
    """
    Verify that GuardianState.last_reset_date uses get_last_reset_time()
    instead of datetime.now()
    """
    from utils.time_utils import get_last_reset_time
    
    # Mock a specific time: 14:00 UTC on 2026-01-02
    mock_time = datetime(2026, 1, 2, 14, 0, 0)
    
    with patch('utils.time_utils.get_server_time_or_fallback', return_value=mock_time):
        reset_time = get_last_reset_time(reset_hour=4)
        
        # Expected: 04:00 UTC on 2026-01-02 (same day since 14:00 > 04:00)
        expected = datetime(2026, 1, 2, 4, 0, 0)
        
        if reset_time == expected:
            print(f"[PASS] Last reset calculated correctly: {reset_time} ✅")
            return True
        else:
            print(f"[FAIL] Expected {expected}, got {reset_time} ❌")
            return False

def test_pre_reset_hour():
    """
    Test when current time is BEFORE reset hour (should use yesterday's reset)
    """
    from utils.time_utils import get_last_reset_time
    
    # Mock time: 02:00 UTC (before 04:00 reset)
    mock_time = datetime(2026, 1, 2, 2, 0, 0)
    
    with patch('utils.time_utils.get_server_time_or_fallback', return_value=mock_time):
        reset_time = get_last_reset_time(reset_hour=4)
        
        # Expected: 04:00 UTC on 2026-01-01 (YESTERDAY)
        expected = datetime(2026, 1, 1, 4, 0, 0)
        
        if reset_time == expected:
            print(f"[PASS] Pre-reset hour handled correctly: {reset_time} ✅")
            return True
        else:
            print(f"[FAIL] Expected {expected}, got {reset_time} ❌")
            return False

def test_guardian_state_uses_server_time():
    """
    Verify GuardianState imports and uses get_last_reset_time
    """
    import inspect
    from active_block_monitor import GuardianState
    
    # Check if the default_factory is get_last_reset_time
    fields = {f.name: f for f in GuardianState.__dataclass_fields__.values()}
    last_reset_field = fields.get('last_reset_date')
    
    if last_reset_field is None:
        print("[FAIL] last_reset_date field not found ❌")
        return False
    
    factory_name = last_reset_field.default_factory.__name__ if last_reset_field.default_factory else "None"
    
    if factory_name == "get_last_reset_time":
        print(f"[PASS] GuardianState uses get_last_reset_time ✅")
        return True
    else:
        print(f"[FAIL] Expected 'get_last_reset_time', got '{factory_name}' ❌")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("PnL Amnesia Fix Test Suite")
    print("=" * 50)
    
    results = []
    results.append(test_pnl_amnesia_fix())
    results.append(test_pre_reset_hour())
    results.append(test_guardian_state_uses_server_time())
    
    print("\n" + "=" * 50)
    if all(results):
        print("ALL TESTS PASSED ✅")
    else:
        print("SOME TESTS FAILED ❌")

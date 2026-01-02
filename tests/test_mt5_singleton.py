"""
Test Script: Verify MT5 Singleton Pattern
Expected: All modules get the SAME manager instance
"""
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_singleton():
    """Verify get_mt5_manager returns same instance"""
    from utils.mt5_connect import get_mt5_manager
    
    m1 = get_mt5_manager()
    m2 = get_mt5_manager()
    
    if m1 is m2:
        print("[PASS] Singleton works - same instance ✅")
        print(f"       Instance ID: {id(m1)}")
        return True
    else:
        print(f"[FAIL] Different instances! ❌")
        print(f"       m1 id: {id(m1)}")
        print(f"       m2 id: {id(m2)}")
        return False

def test_no_direct_mt5_init():
    """Check that key files don't call mt5.initialize() directly"""
    import ast
    
    files_to_check = [
        Path(__file__).parent.parent / "active_block_monitor.py",
        Path(__file__).parent.parent / "data_collector.py",
        Path(__file__).parent.parent / "daily_report.py",
        Path(__file__).parent.parent / "chart_gen.py",
    ]
    
    violations = []
    
    for file_path in files_to_check:
        if not file_path.exists():
            continue
            
        content = file_path.read_text(encoding='utf-8')
        
        # Simple check: look for "mt5.initialize" pattern
        if "mt5.initialize" in content:
            # Count occurrences
            count = content.count("mt5.initialize")
            violations.append(f"{file_path.name}: {count} direct mt5.initialize() calls")
    
    if violations:
        print("[FAIL] Direct mt5.initialize() calls found: ❌")
        for v in violations:
            print(f"       - {v}")
        return False
    else:
        print("[PASS] No direct mt5.initialize() calls in main files ✅")
        return True

if __name__ == "__main__":
    print("=" * 50)
    print("MT5 Singleton Test Suite")
    print("=" * 50)
    
    results = []
    results.append(test_singleton())
    results.append(test_no_direct_mt5_init())
    
    print("\n" + "=" * 50)
    if all(results):
        print("ALL TESTS PASSED ✅")
    else:
        print("SOME TESTS FAILED ❌")

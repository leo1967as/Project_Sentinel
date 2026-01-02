
import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestImport(unittest.TestCase):
    def test_import_daily_report(self):
        """
        Trap: Verify that importing daily_report fails because 'pd' is not defined
        """
        try:
            import daily_report
            print("[PASS] Imported daily_report successfully (Fix Verified)")
        except NameError as e:
            print(f"[FAIL] Caught NameError: {e}")
            self.fail(f"Import failed: {e}")
        except Exception as e:
            print(f"[FAIL] Caught unexpected exception: {e}")
            self.fail(f"Import failed with unexpected error: {e}")

if __name__ == '__main__':
    unittest.main()

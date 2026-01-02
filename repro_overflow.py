
import sys
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Signal, QObject, Slot

class SignalTester(QObject):
    # This mimics the FIXED signal
    close_requested = Signal(object)

    def __init__(self):
        super().__init__()
        self.received_ticket = None

    @Slot(object)
    def on_close_requested(self, ticket):
        print(f"Slot received: {ticket}")
        self.received_ticket = ticket

def test_overflow():
    app = QApplication.instance() or QApplication(sys.argv)
    
    tester = SignalTester()
    tester.close_requested.connect(tester.on_close_requested)
    
    # 3.4 Billion (exceeds signed 32-bit int limit of ~2.14B)
    large_ticket = 3398000331
    
    print(f"Emitting ticket: {large_ticket}")
    try:
        tester.close_requested.emit(large_ticket)
        print("Emit successful")
    except Exception as e:
        print(f"Emit FAILED with: {e}")
    except RuntimeError as e:
        print(f"RuntimeError caught: {e}") 

if __name__ == "__main__":
    test_overflow()

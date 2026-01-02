"""
MT5 Worker - Connection management in background thread
"""

from PySide6.QtCore import Signal
from .base_worker import BaseWorker


class MT5Worker(BaseWorker):
    """MT5 connection management worker"""
    
    # Signals
    connected = Signal(dict)           # Account info
    disconnected = Signal(str)         # Reason
    connection_lost = Signal()
    reconnecting = Signal(int)         # Attempt number
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._mt5_manager = None
        self._check_interval = 5.0
    
    def set_mt5_manager(self, manager) -> None:
        """Set the MT5ConnectionManager instance"""
        self._mt5_manager = manager
    
    def run(self) -> None:
        """Connection monitoring loop"""
        if not self._mt5_manager:
            self.error.emit("MT5 manager not set")
            return
        
        self.log.emit("INFO", "MT5 worker started")
        
        try:
            while not self.is_stopped():
                # Check connection
                if not self._mt5_manager.is_connected():
                    self.connection_lost.emit()
                    
                    # Attempt reconnect
                    for attempt in range(5):
                        if self.is_stopped():
                            break
                        self.reconnecting.emit(attempt + 1)
                        
                        if self._mt5_manager.connect():
                            info = self._mt5_manager.get_account_info()
                            self.connected.emit(info or {})
                            break
                        
                        self._stop_event.wait(2)
                
                # Wait
                self._stop_event.wait(self._check_interval)
                
        except Exception as e:
            self.error.emit(str(e))
        
        self.log.emit("INFO", "MT5 worker stopped")
    
    def connect_now(self) -> None:
        """Manual connect trigger"""
        if self._mt5_manager:
            if self._mt5_manager.connect():
                info = self._mt5_manager.get_account_info()
                self.connected.emit(info or {})
            else:
                self.error.emit("Connection failed")
    
    def disconnect_now(self) -> None:
        """Manual disconnect"""
        if self._mt5_manager:
            self._mt5_manager.disconnect()
            self.disconnected.emit("Manual disconnect")

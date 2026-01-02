"""
Base Worker - Abstract base class for all QThread workers
"""

from PySide6.QtCore import QThread, Signal
import threading


class BaseWorker(QThread):
    """Abstract base for all background workers"""
    
    # Signals
    error = Signal(str)           # Emit on exception
    log = Signal(str, str)        # level, message
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._stop_event = threading.Event()
    
    def stop(self) -> None:
        """Request worker to stop"""
        self._stop_event.set()
    
    def is_stopped(self) -> bool:
        """Check if stop was requested"""
        return self._stop_event.is_set()
    
    def run(self) -> None:
        """Override in subclass"""
        raise NotImplementedError("Subclass must implement run()")

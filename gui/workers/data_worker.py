"""
Data Worker - Tick collection in background thread
"""

from PySide6.QtCore import Signal
from .base_worker import BaseWorker


class DataWorker(BaseWorker):
    """Tick collection worker thread"""
    
    # Signals
    tick_collected = Signal(object)          # TickRecord
    buffer_status = Signal(int, int)         # current, max
    buffer_flushed = Signal(int)             # count inserted
    stats_updated = Signal(dict)             # {total, rate, ...}
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._collector = None
        self._poll_interval = 0.1
    
    def set_collector(self, collector) -> None:
        """Set the TickCollector instance"""
        self._collector = collector
    
    def run(self) -> None:
        """Main collection loop"""
        if not self._collector:
            self.error.emit("Collector not set")
            return
        
        self.log.emit("INFO", "Data worker started")
        
        try:
            while not self.is_stopped():
                # Collect tick
                tick = self._collector.collect_tick()
                if tick:
                    self.tick_collected.emit(tick)
                
                # Buffer status
                buffer_size = len(self._collector.buffer)
                self.buffer_status.emit(buffer_size, self._collector.batch_size)
                
                # Flush if needed
                if buffer_size >= self._collector.batch_size:
                    count = self._collector.flush_buffer()
                    self.buffer_flushed.emit(count)
                
                # Wait
                self._stop_event.wait(self._poll_interval)
                
        except Exception as e:
            self.error.emit(str(e))
        
        # Final flush
        if self._collector:
            self._collector.flush_buffer()
        
        self.log.emit("INFO", "Data worker stopped")

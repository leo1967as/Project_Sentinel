"""
Guardian Worker - P&L monitoring in background thread
"""

from datetime import datetime
from PySide6.QtCore import Signal
from .base_worker import BaseWorker


class GuardianWorker(BaseWorker):
    """P&L monitoring worker thread"""
    
    # Signals
    pnl_updated = Signal(float)                    # Daily P&L value
    positions_changed = Signal(list)               # List of position dicts
    mode_changed = Signal(str, object)             # "NORMAL"/"BLOCK", timestamp
    threshold_exceeded = Signal(float, float)      # current, threshold
    position_closed = Signal(int, str, float)      # ticket, symbol, profit
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._guardian = None
        self._check_interval = 5.0  # Normal mode
        self._block_interval = 0.5  # Block mode
    
    def set_guardian(self, guardian) -> None:
        """Set the TradingGuardian instance"""
        self._guardian = guardian
    
    def run(self) -> None:
        """Main monitoring loop"""
        if not self._guardian:
            self.error.emit("Guardian not set")
            return
        
        self.log.emit("INFO", "Guardian worker started")
        current_mode = "NORMAL"
        
        try:
            while not self.is_stopped():
                # Check P&L
                pnl = self._guardian.get_daily_pnl()
                self.pnl_updated.emit(pnl)
                
                # Check positions
                positions = self._guardian.get_positions()
                self.positions_changed.emit(positions)
                
                # Check mode change
                if self._guardian.state.is_trading_allowed:
                    if current_mode != "NORMAL":
                        current_mode = "NORMAL"
                        self.mode_changed.emit("NORMAL", None)
                    interval = self._check_interval
                else:
                    if current_mode != "BLOCK":
                        current_mode = "BLOCK"
                        self.mode_changed.emit("BLOCK", 
                            self._guardian.state.block_triggered_time)
                    interval = self._block_interval
                    
                    # Block mode - close new positions
                    self._guardian.block_new_positions()
                
                # Check threshold
                if pnl <= self._guardian.max_loss:
                    self.threshold_exceeded.emit(pnl, self._guardian.max_loss)
                
                # Wait
                self._stop_event.wait(interval)
                
        except Exception as e:
            self.error.emit(str(e))
        
        self.log.emit("INFO", "Guardian worker stopped")
    
    def force_close_all(self) -> None:
        """Emergency close all positions"""
        if self._guardian:
            success, failed = self._guardian.close_all_positions()
            self.log.emit("WARNING", f"Closed {success}, failed {failed}")

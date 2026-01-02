"""
===============================================================================
PROJECT SENTINEL - ACTIVE BLOCK MONITOR (Risk Guardian)
===============================================================================
Real-time trading position monitor with IMMEDIATE shutdown capability.
Monitors daily P&L and auto-closes positions when threshold exceeded.

Author: Project Sentinel
Hardware: Intel N95 Mini PC (optimized for low CPU)
Platform: Python 3.9+ / MetaTrader 5 (Exness)
===============================================================================
"""

import MetaTrader5 as mt5
import time
import csv
import os
import signal
import sys
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Set, Optional, List, Dict
from pathlib import Path
from dotenv import load_dotenv
from utils.mt5_connect import get_mt5_manager

# Load .env file
load_dotenv(Path(__file__).parent / ".env")

# =============================================================================
# CONFIGURATION - EDIT THESE VALUES
# =============================================================================

# ---- Loss Thresholds (in cents for Exness Cent account) ----
MAX_LOSS_PRODUCTION = int(os.getenv("MAX_LOSS_PRODUCTION", "-300"))  # Read from .env

# ---- Daily Reset Time (Server Time - Exness uses UTC+0) ----
RESET_HOUR = int(os.getenv("RESET_HOUR", "4"))  # Default 04:00
RESET_MINUTE = int(os.getenv("RESET_MINUTE", "0"))  # Default :00

# ---- Monitoring Intervals (seconds) ----
NORMAL_CHECK_INTERVAL = 5.0    # When trading is allowed
BLOCK_CHECK_INTERVAL = 0.5     # When in active block mode (CRITICAL!)

# ---- Connection Settings ----
MT5_RECONNECT_DELAY = 5        # Seconds between reconnection attempts
MT5_MAX_RECONNECT_ATTEMPTS = 10

# ---- Symbol (for position filtering - leave empty for all) ----
SYMBOL_FILTER = ""  # e.g., "XAUUSDm" or "" for all symbols

# ---- Logging ----
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class GuardianState:
    """Tracks the current state of the guardian system"""
    is_trading_allowed: bool = True
    known_positions: Set[int] = field(default_factory=set)
    daily_pnl: float = 0.0
    last_reset_date: datetime = field(default_factory=datetime.now)
    block_triggered_time: Optional[datetime] = None
    positions_closed_today: int = 0
    sneaky_positions_blocked: int = 0

# =============================================================================
# GUARDIAN CLASS
# =============================================================================

class TradingGuardian:
    """
    The Risk Guardian - Monitors trading and enforces discipline.
    
    Features:
    - Real-time P&L monitoring
    - Auto-close all positions when max loss exceeded  
    - Active Block mode: Closes ANY new positions within 1 second
    - Daily reset at configured hour
    - CSV logging of all actions
    """
    
    def __init__(self, stop_event: threading.Event = None):
        self.state = GuardianState()
        self.running = False
        self.stop_event = stop_event  # External stop event from main_guardian
        self.running = False
        self.stop_event = stop_event  # External stop event from main_guardian
        self.max_loss = MAX_LOSS_PRODUCTION
        self._setup_logging()
        self._setup_signal_handlers()
        
    def _setup_logging(self):
        """Initialize CSV log file for today"""
        today = datetime.now().strftime("%Y-%m-%d")
        self.log_file = LOG_DIR / f"guardian_{today}.csv"
        
        # Create header if file doesn't exist
        if not self.log_file.exists():
            with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'action', 'details', 'pnl', 
                    'positions_count', 'result'
                ])
    
    def _setup_signal_handlers(self):
        """Handle graceful shutdown on Ctrl+C (only in main thread)"""
        try:
            # Only set up signal handlers if we're in the main thread
            if threading.current_thread() is threading.main_thread():
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
        except Exception:
            # Silently ignore if signal handling not available
            pass
        
    def _signal_handler(self, signum, frame):
        """Graceful shutdown"""
        self.log_action("SHUTDOWN", "Received termination signal", "Graceful exit")
        self.running = False
        
    def log_action(self, action: str, details: str, result: str = "OK"):
        """Log action to CSV file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        positions = len(self.state.known_positions)
        
        try:
            with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp, action, details, 
                    f"{self.state.daily_pnl:.2f}", positions, result
                ])
        except Exception as e:
            print(f"[LOG ERROR] {e}")
            
        # Also print to console
        status = "🟢" if self.state.is_trading_allowed else "🔴"
        print(f"{timestamp} | {status} | {action}: {details} [{result}]")
    
    # =========================================================================
    # MT5 CONNECTION
    # =========================================================================
    
    def connect(self) -> bool:
        """Connect to MT5 terminal using centralized manager"""
        manager = get_mt5_manager()
        if manager.ensure_connected():
            account = mt5.account_info()
            if account:
                self.log_action(
                    "CONNECTED", 
                    f"Account: {account.login} | Server: {account.server}",
                    "SUCCESS"
                )
                return True
            
            error = mt5.last_error()
            self.log_action(
                "CONNECT_RETRY", 
                f"Attempt {attempt + 1}/{MT5_MAX_RECONNECT_ATTEMPTS}: {error}",
                "WAITING"
            )
            time.sleep(MT5_RECONNECT_DELAY)
        
        self.log_action("CONNECT_FAILED", "Max attempts reached", "CRITICAL")
        return False
    
    def disconnect(self):
        """Safely disconnect from MT5"""
        mt5.shutdown()
        self.log_action("DISCONNECTED", "MT5 connection closed", "OK")
    
    def reset_daily(self):
        """Force daily reset - like new trading day started"""
        self.state.is_trading_allowed = True
        self.state.daily_pnl = 0.0
        self.state.block_triggered_time = None
        self.state.known_positions = set()
        self.state.positions_closed_today = 0
        self.state.sneaky_positions_blocked = 0
        self.state.last_reset_date = datetime.now()
        self.log_action("DAILY_RESET", "Manual reset - new trading day", "FORCED")
    
    def ensure_connected(self) -> bool:
        """Check connection and reconnect if needed"""
        if mt5.terminal_info() is None:
            self.log_action("CONNECTION_LOST", "Attempting reconnect...", "RETRY")
            return self.connect()
        return True
    
    # =========================================================================
    # POSITION MANAGEMENT
    # =========================================================================
    
    def get_positions(self) -> List[Dict]:
        """Get all open positions"""
        if SYMBOL_FILTER:
            positions = mt5.positions_get(symbol=SYMBOL_FILTER)
        else:
            positions = mt5.positions_get()
            
        if positions is None:
            return []
            
        return [
            {
                'ticket': p.ticket,
                'symbol': p.symbol,
                'type': 'BUY' if p.type == 0 else 'SELL',
                'volume': p.volume,
                'profit': p.profit,
                'open_price': p.price_open,
                'current_price': p.price_current,
                'time': datetime.fromtimestamp(p.time)
            }
            for p in positions
        ]
    
    def close_position(self, ticket: int, symbol: str, volume: float, 
                       position_type: str) -> bool:
        """Close a specific position by ticket"""
        # Determine close order type (opposite of position)
        close_type = mt5.ORDER_TYPE_SELL if position_type == 'BUY' else mt5.ORDER_TYPE_BUY
        
        # Get current price
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            self.log_action("CLOSE_FAILED", f"No tick for {symbol}", "ERROR")
            return False
            
        price = tick.bid if position_type == 'BUY' else tick.ask
        
        # Prepare close request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 50,  # 50 points slippage allowed
            "magic": 999999,  # Guardian magic number
            "comment": "Sentinel_Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Send order
        result = mt5.order_send(request)
        
        if result is None:
            self.log_action("CLOSE_FAILED", f"Ticket {ticket}: No response", "ERROR")
            return False
            
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            self.log_action(
                "POSITION_CLOSED", 
                f"Ticket: {ticket} | {symbol} {position_type} {volume}",
                "SUCCESS"
            )
            return True
        else:
            self.log_action(
                "CLOSE_FAILED", 
                f"Ticket {ticket}: {result.comment} (code: {result.retcode})",
                "ERROR"
            )
            return False
    
    def close_all_positions(self) -> tuple:
        """Close ALL open positions. Returns (success_count, fail_count)"""
        positions = self.get_positions()
        success = 0
        failed = 0
        
        for pos in positions:
            if self.close_position(
                pos['ticket'], pos['symbol'], 
                pos['volume'], pos['type']
            ):
                success += 1
            else:
                failed += 1
                
        self.log_action(
            "CLOSE_ALL", 
            f"Closed: {success}, Failed: {failed}",
            "COMPLETE"
        )
        return success, failed
    
    # =========================================================================
    # PNL CALCULATION
    # =========================================================================
    
    def get_reset_time_today(self) -> datetime:
        """Get today's reset time (e.g., 04:30 AM server time)"""
        now = datetime.now()
        reset_time = now.replace(hour=RESET_HOUR, minute=RESET_MINUTE, second=0, microsecond=0)
        
        # If current time is before reset, use yesterday's reset
        if now.hour < RESET_HOUR or (now.hour == RESET_HOUR and now.minute < RESET_MINUTE):
            reset_time -= timedelta(days=1)
            
        return reset_time
    
    def get_daily_pnl(self) -> float:
        """
        Calculate daily P&L:
        - Realized: Closed trades since LAST RESET (manual or scheduled)
        - Unrealized: Floating P&L on open positions
        """
        # USE THE STATE VARIABLE which tracks manual resets
        reset_time = self.state.last_reset_date
        
        # ---- Realized P&L (closed trades) ----
        realized_pnl = 0.0
        deals = mt5.history_deals_get(reset_time, datetime.now())
        
        if deals:
            for deal in deals:
                # Only count actual trades (not deposits/withdrawals)
                if deal.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]:
                    realized_pnl += deal.profit + deal.swap + deal.commission
        
        # ---- Unrealized P&L (open positions) ----
        unrealized_pnl = 0.0
        positions = self.get_positions()
        for pos in positions:
            unrealized_pnl += pos['profit']
        
        total_pnl = realized_pnl + unrealized_pnl
        self.state.daily_pnl = total_pnl
        
        return total_pnl
    
    # =========================================================================
    # ACTIVE BLOCK MODE
    # =========================================================================
    
    def check_for_new_positions(self) -> List[Dict]:
        """Detect any NEW positions opened since last check"""
        current_positions = self.get_positions()
        current_tickets = {p['ticket'] for p in current_positions}
        
        # Find new positions
        new_tickets = current_tickets - self.state.known_positions
        new_positions = [p for p in current_positions if p['ticket'] in new_tickets]
        
        # Update known positions
        self.state.known_positions = current_tickets
        
        return new_positions
    
    def block_new_positions(self):
        """Close any sneaky new positions opened during block mode"""
        new_positions = self.check_for_new_positions()
        
        for pos in new_positions:
            self.log_action(
                "🚨 BLOCKED", 
                f"Closing sneaky position: {pos['ticket']} | {pos['symbol']} {pos['type']}",
                "ENFORCING"
            )
            
            if self.close_position(
                pos['ticket'], pos['symbol'],
                pos['volume'], pos['type']
            ):
                self.state.sneaky_positions_blocked += 1
    
    def check_daily_reset(self) -> bool:
        """Check if we should reset for a new trading day"""
        reset_time = self.get_reset_time_today()
        
        if reset_time > self.state.last_reset_date:
            self.state.last_reset_date = reset_time
            self.state.is_trading_allowed = True
            self.state.block_triggered_time = None
            self.state.positions_closed_today = 0
            self.state.sneaky_positions_blocked = 0
            
            # Rotate log file for new day
            self._setup_logging()
            
            self.log_action("DAILY_RESET", "New trading day started", "TRADING ALLOWED")
            return True
        return False
    
    # =========================================================================
    # MAIN LOOPS
    # =========================================================================
    
    def run_normal_mode(self):
        """Normal monitoring mode - check P&L every 5 seconds"""
        if not self.ensure_connected():
            time.sleep(MT5_RECONNECT_DELAY)
            return
        
        # Update known positions
        self.check_for_new_positions()
        
        # Check daily P&L
        pnl = self.get_daily_pnl()
        
        # Check if threshold exceeded
        if pnl <= self.max_loss:
            self.log_action(
                "⚠️ THRESHOLD EXCEEDED", 
                f"Daily P&L: {pnl:.2f} <= Limit: {self.max_loss}",
                "ACTIVATING BLOCK"
            )
            
            # Close all positions
            success, failed = self.close_all_positions()
            self.state.positions_closed_today = success
            
            # Enter block mode
            self.state.is_trading_allowed = False
            self.state.block_triggered_time = datetime.now()
            
            self.log_action(
                "🔴 ACTIVE BLOCK MODE", 
                f"All trading blocked until {RESET_HOUR:02d}:{RESET_MINUTE:02d}",
                "ENFORCEMENT ACTIVE"
            )
    
    def run_block_mode(self):
        """Active block mode - monitor every 0.5 seconds for sneaky trades"""
        if not self.ensure_connected():
            time.sleep(MT5_RECONNECT_DELAY)
            return
            
        # Check for new positions and close them
        self.block_new_positions()
        
        # Check for daily reset
        self.check_daily_reset()
    
    def run(self):
        """Main entry point - runs forever until stopped"""
        print("=" * 60)
        print("  PROJECT SENTINEL - RISK GUARDIAN")
        print("=" * 60)
        print(f"  Mode: {'TEST' if TEST_MODE else 'PRODUCTION'}")
        print(f"  Max Loss: {self.max_loss} cents")
        print(f"  Daily Reset: {RESET_HOUR}:00")
        print("=" * 60)
        print()
        
        if not self.connect():
            print("Failed to connect to MT5. Exiting.")
            return
        
        self.running = True
        self.log_action("START", f"Guardian active (limit: {self.max_loss})", "MONITORING")
        
        try:
            while self.running:
                # Check external stop event if provided
                if self.stop_event and self.stop_event.is_set():
                    self.running = False
                    break
                
                if self.state.is_trading_allowed:
                    self.run_normal_mode()
                    time.sleep(NORMAL_CHECK_INTERVAL)
                else:
                    self.run_block_mode()
                    time.sleep(BLOCK_CHECK_INTERVAL)
                    
        except Exception as e:
            self.log_action("ERROR", str(e), "EXCEPTION")
            raise
        finally:
            self.disconnect()
            print("\nGuardian stopped. Final stats:")
            print(f"  Positions closed today: {self.state.positions_closed_today}")
            print(f"  Sneaky trades blocked: {self.state.sneaky_positions_blocked}")

# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    guardian = TradingGuardian()
    guardian.run()

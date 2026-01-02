"""
===============================================================================
PROJECT SENTINEL - MT5 CONNECTION MANAGER
===============================================================================
Robust MT5 connection with auto-reconnect, rate limiting, and detailed logging.

Author: Project Sentinel
===============================================================================
"""

import MetaTrader5 as mt5
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from pathlib import Path
from functools import wraps
import sys

# Add parent to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get_config, AuditLogger

# =============================================================================
# LOGGING SETUP
# =============================================================================

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("mt5_connect")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    # File handler
    fh = logging.FileHandler(LOG_DIR / "mt5_connection.log", encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s'
    ))
    logger.addHandler(fh)
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
    logger.addHandler(ch)

# =============================================================================
# RATE LIMITER
# =============================================================================

class RateLimiter:
    """Prevents API abuse by limiting call frequency"""
    
    def __init__(self, max_calls: int = 10, period_seconds: float = 1.0):
        self.max_calls = max_calls
        self.period = period_seconds
        self.calls: list = []
        self._lock = threading.Lock()
    
    def acquire(self) -> bool:
        """Check if we can make a call. Returns True if allowed."""
        with self._lock:
            now = time.time()
            
            # Remove old calls
            self.calls = [t for t in self.calls if now - t < self.period]
            
            if len(self.calls) < self.max_calls:
                self.calls.append(now)
                return True
            
            return False
    
    def wait_if_needed(self):
        """Block until rate limit allows"""
        while not self.acquire():
            time.sleep(0.05)

def rate_limited(limiter: RateLimiter):
    """Decorator to apply rate limiting to a function"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter.wait_if_needed()
            return func(*args, **kwargs)
        return wrapper
    return decorator

# =============================================================================
# CONNECTION STATE
# =============================================================================

@dataclass
class ConnectionState:
    """Tracks MT5 connection state"""
    connected: bool = False
    account_login: int = 0
    account_server: str = ""
    account_balance: float = 0.0
    account_type: str = ""  # "demo" or "real"
    last_connected: Optional[datetime] = None
    last_error: str = ""
    reconnect_attempts: int = 0
    total_reconnects: int = 0

# =============================================================================
# MT5 CONNECTION MANAGER
# =============================================================================

class MT5ConnectionManager:
    """
    Robust MT5 connection manager with:
    - Auto-reconnect on failure
    - Rate limiting to prevent API bans
    - Detailed error logging
    - Demo/live account detection
    """
    
    _instance: Optional['MT5ConnectionManager'] = None
    _lock = threading.RLock()
    
    # Rate limiters
    _order_limiter = RateLimiter(max_calls=5, period_seconds=1.0)
    _data_limiter = RateLimiter(max_calls=20, period_seconds=1.0)
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.state = ConnectionState()
        self.config = get_config()
        self._initialized = True
        
        # Connection settings
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5  # seconds
        self.reconnect_backoff = 1.5  # multiplier
    
    # =========================================================================
    # CONNECTION MANAGEMENT
    # =========================================================================
    
    def connect(self, use_credentials: bool = True) -> bool:
        """
        Connect to MT5 terminal.
        
        Args:
            use_credentials: If True, use login/password from config.
                           If False, connect to already-logged-in terminal.
        """
        with self._lock:
            logger.info("Attempting MT5 connection...")
            
            # Initialize MT5
            init_params = {}
            
            if self.config.mt5_terminal_path:
                init_params['path'] = self.config.mt5_terminal_path
            
            if use_credentials and self.config.mt5_login > 0:
                init_params['login'] = self.config.mt5_login
                init_params['password'] = self.config.mt5_password
                init_params['server'] = self.config.mt5_server
            
            if init_params:
                success = mt5.initialize(**init_params)
            else:
                success = mt5.initialize()
            
            if not success:
                error = mt5.last_error()
                self.state.last_error = str(error)
                logger.error(f"MT5 initialize failed: {error}")
                return False
            
            # Get account info
            account = mt5.account_info()
            if account is None:
                self.state.last_error = "Could not get account info"
                logger.error(self.state.last_error)
                mt5.shutdown()
                return False
            
            # Update state
            self.state.connected = True
            self.state.account_login = account.login
            self.state.account_server = account.server
            self.state.account_balance = account.balance
            self.state.account_type = "demo" if account.trade_mode == 0 else "real"
            self.state.last_connected = datetime.now()
            self.state.reconnect_attempts = 0
            
            logger.info(
                f"Connected: Account {account.login} ({self.state.account_type}) "
                f"@ {account.server} | Balance: {account.balance:.2f}"
            )
            
            return True
    
    def disconnect(self):
        """Safely disconnect from MT5"""
        with self._lock:
            if self.state.connected:
                mt5.shutdown()
                self.state.connected = False
                logger.info("Disconnected from MT5")
    
    def ensure_connected(self) -> bool:
        """Check connection and auto-reconnect if needed"""
        # Quick check
        if mt5.terminal_info() is not None:
            return True
        
        # Connection lost - attempt reconnect
        self.state.connected = False
        logger.warning("Connection lost, attempting reconnect...")
        
        delay = self.reconnect_delay
        
        for attempt in range(self.max_reconnect_attempts):
            self.state.reconnect_attempts = attempt + 1
            
            if self.connect():
                self.state.total_reconnects += 1
                logger.info(f"Reconnected after {attempt + 1} attempts")
                return True
            
            logger.warning(f"Reconnect attempt {attempt + 1} failed, waiting {delay:.1f}s...")
            time.sleep(delay)
            delay = min(delay * self.reconnect_backoff, 60)  # Max 60s
        
        logger.error("Max reconnection attempts reached")
        return False
    
    def is_connected(self) -> bool:
        """Check if currently connected"""
        return self.state.connected and mt5.terminal_info() is not None
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get current account information"""
        if not self.ensure_connected():
            return None
        
        account = mt5.account_info()
        if account is None:
            return None
        
        return {
            'login': account.login,
            'server': account.server,
            'balance': account.balance,
            'equity': account.equity,
            'margin': account.margin,
            'free_margin': account.margin_free,
            'profit': account.profit,
            'leverage': account.leverage,
            'currency': account.currency,
            'trade_mode': 'demo' if account.trade_mode == 0 else 'real'
        }
    
    # =========================================================================
    # TRADING OPERATIONS (Rate Limited)
    # =========================================================================
    
    @rate_limited(_order_limiter)
    def send_order(self, request: Dict) -> Optional[Any]:
        """Send order with rate limiting"""
        if not self.ensure_connected():
            logger.error("Cannot send order: Not connected")
            return None
        
        logger.debug(f"Sending order: {request}")
        result = mt5.order_send(request)
        
        if result is None:
            logger.error(f"Order failed: No response")
        elif result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order failed: {result.comment} (code: {result.retcode})")
        else:
            logger.info(f"Order success: {result.order}")
        
        return result
    
    @rate_limited(_order_limiter)
    def close_position(self, ticket: int) -> bool:
        """Close position by ticket"""
        if not self.ensure_connected():
            return False
        
        # Get position
        position = mt5.positions_get(ticket=ticket)
        if not position:
            logger.warning(f"Position {ticket} not found")
            return False
        
        pos = position[0]
        
        # Determine close type
        close_type = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY
        
        # Get price
        tick = mt5.symbol_info_tick(pos.symbol)
        if tick is None:
            return False
        
        price = tick.bid if pos.type == 0 else tick.ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 50,
            "magic": 999999,
            "comment": "Sentinel_Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = self.send_order(request)
        return result is not None and result.retcode == mt5.TRADE_RETCODE_DONE
    
    # =========================================================================
    # DATA OPERATIONS (Rate Limited)
    # =========================================================================
    
    @rate_limited(_data_limiter)
    def get_positions(self, symbol: str = None) -> list:
        """Get open positions"""
        if not self.ensure_connected():
            return []
        
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
        
        return list(positions) if positions else []
    
    @rate_limited(_data_limiter)
    def get_tick(self, symbol: str):
        """Get latest tick for symbol"""
        if not self.ensure_connected():
            return None
        return mt5.symbol_info_tick(symbol)
    
    @rate_limited(_data_limiter)
    def get_history_deals(self, from_date: datetime, to_date: datetime = None):
        """Get deal history"""
        if not self.ensure_connected():
            return None
        
        if to_date is None:
            to_date = datetime.now()
        
        return mt5.history_deals_get(from_date, to_date)
    
    # =========================================================================
    # HEALTH CHECK
    # =========================================================================
    
    def health_check(self) -> Dict[str, Any]:
        """Get connection health status"""
        connected = self.is_connected()
        
        status = {
            'connected': connected,
            'account_login': self.state.account_login,
            'account_type': self.state.account_type,
            'last_connected': self.state.last_connected.isoformat() if self.state.last_connected else None,
            'last_error': self.state.last_error,
            'reconnect_attempts': self.state.reconnect_attempts,
            'total_reconnects': self.state.total_reconnects,
        }
        
        if connected:
            account = self.get_account_info()
            if account:
                status['balance'] = account['balance']
                status['equity'] = account['equity']
                status['profit'] = account['profit']
        
        return status

# =============================================================================
# HELPER FUNCTION
# =============================================================================

_manager: Optional[MT5ConnectionManager] = None

def get_mt5_manager() -> MT5ConnectionManager:
    """Get singleton MT5 connection manager"""
    global _manager
    if _manager is None:
        _manager = MT5ConnectionManager()
    return _manager

# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    print("Testing MT5 Connection Manager...")
    
    manager = get_mt5_manager()
    
    if manager.connect(use_credentials=False):  # Connect to existing terminal
        print("\nConnection Health:")
        health = manager.health_check()
        for key, value in health.items():
            print(f"  {key}: {value}")
        
        print("\nPositions:")
        positions = manager.get_positions()
        print(f"  Open: {len(positions)}")
        
        manager.disconnect()
    else:
        print("Connection failed!")

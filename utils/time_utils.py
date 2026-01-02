"""
===============================================================================
PROJECT SENTINEL - TIME UTILITIES
===============================================================================
Provides timezone-aware time functions using MT5 Server Time.

IMPORTANT: Always use these functions instead of datetime.now() for:
- Daily P&L reset calculations
- Trade history queries
- Report period boundaries

Server Time: UTC (GMT+0)
Thai Time: UTC+7
===============================================================================
"""

import MetaTrader5 as mt5
from datetime import datetime, timedelta
from typing import Optional


def get_server_time() -> Optional[datetime]:
    """
    Get current MT5 server time as naive datetime (UTC).
    
    Returns:
        datetime in UTC, or None if MT5 not connected
    """
    try:
        timestamp = mt5.time_current()
        if timestamp is None or timestamp == 0:
            return None
        return datetime.utcfromtimestamp(timestamp)
    except Exception:
        return None


def get_server_time_or_fallback() -> datetime:
    """
    Get server time, fallback to UTC now if MT5 not connected.
    Use this when you MUST have a time value.
    """
    server_time = get_server_time()
    if server_time is None:
        return datetime.utcnow()
    return server_time


def get_last_reset_time(reset_hour: int = 4) -> datetime:
    """
    Calculate the last daily reset time based on server time.
    
    Args:
        reset_hour: Hour in UTC when daily reset occurs (default: 4 = 04:00 UTC = 11:00 Thai)
        
    Returns:
        datetime of last reset in UTC
        
    Examples:
        - If now is 10:00 UTC and reset_hour=4, returns today 04:00 UTC
        - If now is 02:00 UTC and reset_hour=4, returns yesterday 04:00 UTC
    """
    now = get_server_time_or_fallback()
    reset_today = now.replace(hour=reset_hour, minute=0, second=0, microsecond=0)
    
    if now < reset_today:
        # Before today's reset, use yesterday's
        return reset_today - timedelta(days=1)
    return reset_today


def get_next_reset_time(reset_hour: int = 4) -> datetime:
    """
    Calculate the next daily reset time.
    
    Args:
        reset_hour: Hour in UTC when daily reset occurs
        
    Returns:
        datetime of next reset in UTC
    """
    now = get_server_time_or_fallback()
    reset_today = now.replace(hour=reset_hour, minute=0, second=0, microsecond=0)
    
    if now >= reset_today:
        # After today's reset, next is tomorrow
        return reset_today + timedelta(days=1)
    return reset_today


def server_to_thai(utc_time: datetime) -> datetime:
    """
    Convert UTC time to Thai time (UTC+7).
    For display purposes only - internal logic should use UTC.
    """
    return utc_time + timedelta(hours=7)


def thai_to_server(thai_time: datetime) -> datetime:
    """
    Convert Thai time to UTC (server time).
    Use when user inputs time in Thai timezone.
    """
    return thai_time - timedelta(hours=7)


# =============================================================================
# QUICK REFERENCE
# =============================================================================
# RESET_HOUR | Server (UTC) | Thai Time
# -----------|--------------|----------
#     4      | 04:00 UTC    | 11:00 Thai
#    17      | 17:00 UTC    | 00:00 Thai (midnight)
#    21      | 21:00 UTC    | 04:00 Thai


if __name__ == "__main__":
    # Test the functions
    print("=" * 50)
    print("Time Utils Test")
    print("=" * 50)
    
    if mt5.initialize():
        server = get_server_time()
        print(f"Server Time (UTC): {server}")
        print(f"Thai Time:         {server_to_thai(server)}")
        print(f"Last Reset (04:00 UTC): {get_last_reset_time(4)}")
        print(f"Next Reset (04:00 UTC): {get_next_reset_time(4)}")
        mt5.shutdown()
    else:
        print("MT5 not connected, using fallback")
        now = get_server_time_or_fallback()
        print(f"Fallback UTC: {now}")

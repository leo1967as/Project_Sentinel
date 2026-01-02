"""
MT5 Connection & Order Close Test Script
Tests the core trading functionality
"""

import MetaTrader5 as mt5
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env
load_dotenv(Path(__file__).parent / ".env")

def test_connection():
    """Test MT5 connection"""
    print("\n" + "="*60)
    print("🔌 TESTING MT5 CONNECTION")
    print("="*60)
    
    # Initialize MT5
    if not mt5.initialize():
        print(f"❌ MT5 initialize failed: {mt5.last_error()}")
        return False
    
    # Get account info
    account = mt5.account_info()
    if account is None:
        print(f"❌ Failed to get account info: {mt5.last_error()}")
        return False
    
    print(f"✅ Connected successfully!")
    print(f"   Account: {account.login}")
    print(f"   Server: {account.server}")
    print(f"   Balance: ${account.balance:.2f}")
    print(f"   Equity: ${account.equity:.2f}")
    print(f"   Profit: ${account.profit:+.2f}")
    print(f"   Type: {'Demo' if account.trade_mode == 0 else 'Live'}")
    
    return True


def test_get_positions():
    """Test getting open positions"""
    print("\n" + "="*60)
    print("📊 TESTING GET POSITIONS")
    print("="*60)
    
    positions = mt5.positions_get()
    
    if positions is None:
        print(f"❌ Failed to get positions: {mt5.last_error()}")
        return []
    
    if len(positions) == 0:
        print("📭 No open positions")
        return []
    
    print(f"✅ Found {len(positions)} open position(s):\n")
    
    position_list = []
    for pos in positions:
        pos_type = "BUY" if pos.type == 0 else "SELL"
        print(f"   Ticket: {pos.ticket}")
        print(f"   Symbol: {pos.symbol}")
        print(f"   Type: {pos_type}")
        print(f"   Volume: {pos.volume}")
        print(f"   Open Price: {pos.price_open}")
        print(f"   Current: {pos.price_current}")
        print(f"   Profit: ${pos.profit:+.2f}")
        print()
        
        position_list.append({
            'ticket': pos.ticket,
            'symbol': pos.symbol,
            'type': pos_type,
            'volume': pos.volume,
            'open_price': pos.price_open,
            'profit': pos.profit
        })
    
    return position_list


def test_close_position(ticket: int, symbol: str, volume: float, pos_type: str):
    """Test closing a specific position"""
    print("\n" + "="*60)
    print(f"🔒 TESTING CLOSE POSITION #{ticket}")
    print("="*60)
    
    # Get symbol info for filling mode
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"❌ Symbol {symbol} not found")
        return False
    
    # Determine close type (opposite of position type)
    if pos_type == "BUY":
        close_type = mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(symbol).bid
    else:
        close_type = mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).ask
    
    # Build close request
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": close_type,
        "position": ticket,
        "price": price,
        "deviation": 20,
        "magic": 999999,
        "comment": "Sentinel Test Close",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    print(f"   Sending close request...")
    print(f"   Symbol: {symbol}")
    print(f"   Volume: {volume}")
    print(f"   Price: {price}")
    
    # Send order
    result = mt5.order_send(request)
    
    if result is None:
        print(f"❌ Order send failed: {mt5.last_error()}")
        return False
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Close failed: {result.comment} (code: {result.retcode})")
        return False
    
    print(f"✅ Position closed successfully!")
    print(f"   Deal: {result.deal}")
    print(f"   Order: {result.order}")
    print(f"   Volume: {result.volume}")
    
    return True


def main():
    """Main test runner"""
    print("\n" + "="*60)
    print("🧪 PROJECT SENTINEL - MT5 TEST SUITE")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Connection
    if not test_connection():
        print("\n❌ Connection test failed. Aborting.")
        return
    
    # Test 2: Get Positions
    positions = test_get_positions()
    
    # Test 3: Close Position (if any exist)
    if positions:
        print("\n" + "="*60)
        print("❓ TEST CLOSE POSITION?")
        print("="*60)
        
        for i, pos in enumerate(positions):
            print(f"   [{i+1}] Ticket {pos['ticket']} - {pos['symbol']} {pos['type']} ({pos['profit']:+.2f})")
        
        choice = input("\nEnter number to close (or 'n' to skip): ").strip()
        
        if choice.lower() != 'n' and choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(positions):
                pos = positions[idx]
                confirm = input(f"⚠️  Confirm close ticket {pos['ticket']}? (y/n): ").strip()
                
                if confirm.lower() == 'y':
                    test_close_position(
                        pos['ticket'], 
                        pos['symbol'], 
                        pos['volume'], 
                        pos['type']
                    )
    
    # Cleanup
    mt5.shutdown()
    
    print("\n" + "="*60)
    print("✅ TEST SUITE COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()

"""
Test Script: Verify Chart Arrows
Creates fake trades aligned with MT5 server time and generates a chart.
"""
import sys
import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import MetaTrader5 as mt5

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from daily_report import ChartGenerator, DataLoader, Battle, Trade, CHART_DIR

def main():
    # 1. Initialize MT5
    if not mt5.initialize():
        print("❌ MT5 Init Failed")
        return
    
    # 2. Get current server time from MT5 (this is crucial!)
    # MT5 uses UNIX timestamp which is UTC
    symbol = "XAUUSDm"  # Use user's symbol with 'm' suffix
    
    # Get latest tick to know current MT5 time
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"❌ No tick data for {symbol}, trying EURUSD")
        symbol = "EURUSD"
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            print("❌ No tick data available")
            return
    
    # MT5 tick.time is UNIX timestamp
    # IMPORTANT: Use fromtimestamp (LOCAL) not utcfromtimestamp (UTC)
    # because mt5.copy_rates_range() interprets naive datetimes as LOCAL TIME
    mt5_now = datetime.fromtimestamp(tick.time)
    print(f"✅ MT5 Time (Local): {mt5_now}")
    
    # 3. Create fake trades that align with MT5 time
    # Trade 1: WIN (BUY) - 20 mins ago
    t1 = Trade(
        ticket=9001,
        symbol=symbol,
        order_type="BUY",
        volume=1.0,
        open_price=tick.bid - 5,  # Entry below current price
        close_price=tick.bid,      # Exit at current
        profit=50.0,
        open_time=mt5_now - timedelta(minutes=20),
        close_time=mt5_now - timedelta(minutes=10)
    )
    
    # Trade 2: LOSS (SELL) - 5 mins ago
    t2 = Trade(
        ticket=9002,
        symbol=symbol,
        order_type="SELL",
        volume=0.5,
        open_price=tick.bid + 2,  # Entry above current
        close_price=tick.bid + 5,  # Exit even higher (loss for SELL)
        profit=-30.0,
        open_time=mt5_now - timedelta(minutes=8),
        close_time=mt5_now - timedelta(minutes=3)
    )
    
    # 4. Create Battle
    battle = Battle()
    battle.add_trade(t1)
    battle.add_trade(t2)
    
    print(f"📊 Battle: {battle.trade_count} trades, P&L: ${battle.total_profit:+.2f}")
    print(f"   Trade 1: BUY @ {t1.open_time} -> {t1.close_time} = ${t1.profit:+.2f}")
    print(f"   Trade 2: SELL @ {t2.open_time} -> {t2.close_time} = ${t2.profit:+.2f}")
    
    # 5. Generate Chart
    loader = DataLoader()
    chart_gen = ChartGenerator(loader)
    
    print("🎨 Generating chart...")
    chart_path = chart_gen.generate_battle_chart(battle)
    
    if chart_path and chart_path.exists():
        # Copy to a known location for easy viewing
        output_path = CHART_DIR / "test_arrows.png"
        shutil.copy(chart_path, output_path)
        print(f"✅ Chart saved: {output_path}")
        
        # Also copy to artifacts for agent viewing
        artifacts_dir = Path(r"C:\Users\LEO\.gemini\antigravity\brain\f54ce0f5-5166-4b02-b3d4-1c0385744930")
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        artifacts_path = artifacts_dir / "test_arrows.png"
        shutil.copy(chart_path, artifacts_path)
        print(f"✅ Copied to artifacts: {artifacts_path}")
    else:
        print("❌ Chart generation failed")

if __name__ == "__main__":
    main()

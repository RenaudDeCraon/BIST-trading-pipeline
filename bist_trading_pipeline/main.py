import argparse
import sys
from datetime import datetime, timedelta
from data_fetcher import fetch_intraday_data, fetch_history
from optimizer import ProfitOptimizer, SimpleStrategy
from simulation import SimulationEngine
import pandas as pd

def main():
    parser = argparse.ArgumentParser(description="BIST Trading Pipeline & Profit Maximizer")
    parser.add_argument("symbol", type=str, nargs='?', help="Stock symbol (e.g., THYAO) - Optional if simulating day")
    parser.add_argument("--date", type=str, help="Date to analyze (YYYY-MM-DD)", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--capital", type=float, help="Initial capital", default=10000.0)
    parser.add_argument("--simulate-day", action="store_true", help="Run full market simulation with scanner")
    args = parser.parse_args()

    if args.simulate_day:
        sim = SimulationEngine(args.date)
        sim.run()
        return

    symbol = args.symbol
    if not symbol:
        print("Error: Symbol required unless --simulate-day is used.")
        return
    print(f"--- Analyzing {symbol} for {args.date} ---")

    # 1. Fetch Data
    # For a specific past day, we need to know the range. 
    # yfinance 'period' argument is relative to 'now' usually. 
    # To get a specific intraday date in the past 60 days, we might need start/end dates.
    # yfinance `.history(start=..., end=...)` works for intraday if within last 60 days.
    
    start_date_obj = datetime.strptime(args.date, "%Y-%m-%d")
    end_date_obj = start_date_obj + timedelta(days=1)
    
    # We try to strict fetch for that day
    # Note: Intraday data is only available for recent past (60 days usually for 1m interval)
    print("Fetching data...")
    # Attempt to fetch 1m data
    try:
        # Ticker.history with start/end handles intraday if interval is set
        import yfinance as yf
        ticker_obj = yf.Ticker(symbol if symbol.endswith('.IS') else f"{symbol}.IS")
        df = ticker_obj.history(start=args.date, end=end_date_obj.strftime("%Y-%m-%d"), interval="1m")
    except Exception as e:
        print(f"Error fetching data: {e}")
        return

    if df.empty:
        print("No data found for this date. (Note: Intraday 1m data is only available for the last 30-60 days)")
        return

    print(f"Loaded {len(df)} data points.")
    print(f"Open: {df.iloc[0]['Open']}, Close: {df.iloc[-1]['Close']}")

    # 2. Theoretical Max Profit
    print("\n--- Theoretical Max Profit (Hindsight) ---")
    optimizer = ProfitOptimizer(df)
    max_res = optimizer.calculate_max_possible_profit(initial_capital=args.capital)
    
    print(f"Initial Capital: {max_res['initial_capital']:.2f} TRY")
    print(f"Final Balance:   {max_res['final_balance']:.2f} TRY")
    print(f"Net Profit:      {max_res['profit_amount']:.2f} TRY ({max_res['profit_pct']:.2f}%)")
    print(f"Total Trades:    {max_res['trade_count']}")
    print("(This assumes perfectly catching every 1-minute upward move)")

    # 3. Simple Strategy
    print("\n--- Simple Strategy (SMA Crossover) ---")
    strategy = SimpleStrategy(df)
    # Using small windows for 1m chart: 5m and 15m equivalent roughly?
    # SMA 5 and SMA 20 on 1m bars
    strat_res = strategy.run_sma_crossover(short_window=5, long_window=20, initial_capital=args.capital)
    
    print(f"Initial Capital: {strat_res['initial_capital']:.2f} TRY")
    print(f"Final Balance:   {strat_res['final_balance']:.2f} TRY")
    print(f"Net Profit:      {strat_res['profit_amount']:.2f} TRY ({strat_res['profit_pct']:.2f}%)")
    print(f"Total Trades:    {strat_res['trades']}")

    # 4. Comparison
    print("\n--- Performance ---")
    if max_res['profit_amount'] > 0:
        efficiency = (strat_res['profit_amount'] / max_res['profit_amount']) * 100
    else:
        efficiency = 0.0
    print(f"Strategy Efficiency vs Theoretical Max: {efficiency:.2f}%")

if __name__ == "__main__":
    main()

import pandas as pd
import yfinance as yf
from datetime import datetime
from scanner import MarketScanner
from portfolio import Portfolio
import time

class SimulationEngine:
    def __init__(self, date_str: str, debug=False):
        self.date_str = date_str
        self.scanner = MarketScanner()
        self.portfolio = Portfolio(initial_capital=2000.0)
        self.debug = debug
        self.market_data = {} # {ticker: dataframe}
        self.timestamps = []

    def load_market_data(self):
        print("Loading market data for simulation (this may take a moment)...")
        tickers = self.scanner.get_tickers()
        
        # We need start/end date for fetch
        start_date = self.date_str
        end_date_obj = datetime.strptime(self.date_str, "%Y-%m-%d")
        # yfinance end date is exclusive, so add 1 day or ample time
        # Actually for 'interval=1m', we rely on .history(start=, end=)
        # Note: 1m data is only available for last ~30 days.
        
        # Batch fetching is better but let's be safe with loop for now or bulk download
        # yf.download is faster for bulk
        try:
            # Downloading all at once
            print(f"Downloading data for {len(tickers)} tickers...")
            # yfinance download structure is MultiIndex (Price, Ticker)
            data = yf.download(tickers, start=start_date, interval="1m", progress=False)
            
            # If we only asked for 1 day, sometimes 'end' is needed explicitly
            # But let's check what we got.
            
            # Only keep data for the specific day
            # (yf.download might give more if start is undefined, but we set start)
            pass
            
            # We need to restructure into self.market_data = {ticker: df}
            # The columns are like ('Close', 'AKBNK.IS'), ('Open', 'AKBNK.IS') ...
            
            if data.empty:
                print("No data fetched.")
                return

            # Flatten/Iterate
            # Timestamps are the index
            self.timestamps = sorted(data.index.unique())
            
            # Create per-ticker DFs for easier access
            # We care about Open and Close primarily for simulation
            # We need 'Current Price' which we will simulate as 'Close' of that minute
            # And 'Open' of the day for % change calculation.
            
            # Wait, 'Open' in 1m bar is Open of that minute.
            # We need 'Day Open' for the scanner logic. 
            # We can get Day Open from the first minute of the day for that ticker.
            
            for ticker in tickers:
                try:
                    # Extract ticker slice
                    # Handle MultiIndex
                    # df_ticker = data.xs(ticker, level=1, axis=1) # If level 1 is ticker
                    # yfinance format varies by version. 
                    # Usually: Columns = Level0 (Price Type), Level1 (Ticker)
                    
                    # Let's try to slice properly
                    # Reconstruct a simple DF for each ticker
                    idx = pd.IndexSlice
                    
                    # Check if MultiIndex
                    if isinstance(data.columns, pd.MultiIndex):
                        # Close, Open, Volume
                        # If single ticker, it's not MultiIndex usually, but we passed a list.
                        t_close = data['Close'][ticker]
                        t_open = data['Open'][ticker]
                        t_volume = data['Volume'][ticker] if 'Volume' in data else None
                        
                        df_t = pd.DataFrame({'Close': t_close, 'Open': t_open})
                        if t_volume is not None:
                            df_t['Volume'] = t_volume
                    else:
                        # Single ticker case (Edge case)
                        df_t = data
                    
                    # Filter for day just in case
                    df_t = df_t[df_t.index.strftime("%Y-%m-%d") == self.date_str]
                    
                    if not df_t.empty:
                        # Calculate Day Open (First 'Open' of the day)
                        day_open = df_t.iloc[0]['Open']
                        df_t['DayOpen'] = day_open
                        self.market_data[ticker] = df_t
                        
                except KeyError:
                    if self.debug: print(f"Data missing for {ticker}")
                    continue
                    
        except Exception as e:
            print(f"Error executing bulk download: {e}")
            return

        print(f"Data loaded. Found data for {len(self.market_data)} tickers.")
        print(f"Time steps: {len(self.timestamps)}")

    def run(self):
        if not self.market_data:
            self.load_market_data()
        
        print(f"Starting simulation for {self.date_str}...")
        print(f"Initial Capital: {self.portfolio.cash} TRY")
        
        for ts in self.timestamps:
            # 1. Build Snapshot for this minute
            current_prices = {}
            snapshot_rows = []
            
            for ticker, df in self.market_data.items():
                if ts in df.index:
                    row = df.loc[ts]
                    price = row['Close']
                    day_open = row['DayOpen']
                    
                    if pd.isna(price):
                        continue
                        
                    current_prices[ticker] = price
                    
                    snapshot_rows.append({
                        'ticker': ticker,
                        'Price': price,
                        'Open': day_open,
                        'Volume': row['Volume'] if 'Volume' in row else 0 # Volume is for that minute
                    })
            
            if not snapshot_rows:
                continue
            
            snapshot_df = pd.DataFrame(snapshot_rows).set_index('ticker')
            
            # 2. Portfolio Updates (Stop Loss / Take Profit)
            # Hyper-Scalping: Trailing stop 0.5% (Lock small gains), Hard Stop 1.0%
            # We want to churn capital: Buy -> +1% -> Sell -> Repeat.
            self.portfolio.check_stop_loss_take_profit(current_prices, ts, trailing_stop_pct=0.005, stop_loss_pct=0.01) 
            
            # 3. Scanner to find entries
            # Only buy if we have cash > 100
            if self.portfolio.cash > 100: 
                opportunities = self.scanner.find_opportunities(snapshot_df)
                
                # Buy top opportunities if not already held
                positions_count = len(self.portfolio.positions)
                max_positions = 5 # Diversify a bit more
                
                for opp in opportunities:
                    if positions_count >= max_positions:
                        break
                        
                    ticker = opp['ticker']
                    if ticker not in self.portfolio.positions:
                        # Position Sizing: Aggressive. 
                        # Divide remaining cash significantly.
                        # If we have 2000, buy 1000. If we have 4000, buy 1000.
                        # Let's fix size to 1000 or full cash if less.
                        amount = min(self.portfolio.cash, 2000) 
                        
                        if amount > 100:
                            price = opp['price']
                            print(f"[{ts.time()}] BUY SIGNAL: {ticker} @ {price:.2f} (Daily Change: {opp['score']:.2f}%)")
                            if self.portfolio.buy(ticker, price, amount, ts):
                                positions_count += 1
            
            # Optional: Report status periodically
            if self.debug and ts.minute % 30 == 0:
                eq = self.portfolio.get_total_equity(current_prices)
                print(f"[{ts.time()}] Equity: {eq:.2f}")

        # End of Day: Close all positions
        print("End of Day: Closing all positions.")
        # Use last known prices
        final_prices = {}
        for ticker, df in self.market_data.items():
            if not df.empty:
                final_prices[ticker] = df.iloc[-1]['Close']
                
        # Force sell
        remaining_tickers = list(self.portfolio.positions.keys())
        for ticker in remaining_tickers:
            price = final_prices.get(ticker, self.portfolio.positions[ticker]['avg_price'])
            self.portfolio.sell(ticker, price, reason="EOD Close")

        # Final Report
        final_equity = self.portfolio.cash
        print("\n--- Simulation Results ---")
        print(f"Final Capital: {final_equity:.2f} TRY")
        print(f"Net Profit: {final_equity - self.portfolio.start_capital:.2f} TRY")
        print(f"Return: {((final_equity - self.portfolio.start_capital) / self.portfolio.start_capital)*100:.2f}%")
        print(f"Total Trades: {len(self.portfolio.history)//2}") # Approx trades

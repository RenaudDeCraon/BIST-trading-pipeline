import pandas as pd
import yfinance as yf
from datetime import datetime, time as dt_time
from improved_scanner import ImprovedMarketScanner
from improved_portfolio import ImprovedPortfolio

class ImprovedSimulationEngine:
    """
    Enhanced simulation engine following BIST Trading Agent Guide.
    
    Features:
    - Comprehensive technical analysis
    - Transaction costs (commission + slippage)
    - Partial exits and risk management
    - Detailed reporting
    """
    
    def __init__(self, date_str: str, initial_capital: float = 2000.0, debug=False):
        self.date_str = date_str
        self.scanner = ImprovedMarketScanner()
        self.portfolio = ImprovedPortfolio(
            initial_capital=initial_capital,
            commission_rate=0.0015,   # 0.15%
            slippage_rate=0.001        # 0.1%
        )
        self.debug = debug
        self.market_data = {}  # {ticker: DataFrame with indicators}
        self.timestamps = []
        self.signals_generated = []
        
    def load_market_data(self):
        """Load and prepare market data for simulation."""
        print("Loading market data for simulation...")
        tickers = self.scanner.get_tickers()
        
        try:
            print(f"Downloading data for {len(tickers)} tickers...")
            data = yf.download(tickers, start=self.date_str, interval="1m", progress=False)
            
            if data.empty:
                print("No data fetched.")
                return
            
            self.timestamps = sorted(data.index.unique())
            
            # Process each ticker
            for ticker in tickers:
                try:
                    if isinstance(data.columns, pd.MultiIndex):
                        t_close = data['Close'][ticker]
                        t_open = data['Open'][ticker]
                        t_high = data['High'][ticker]
                        t_low = data['Low'][ticker]
                        t_volume = data['Volume'][ticker] if 'Volume' in data else None
                        
                        df_t = pd.DataFrame({
                            'Close': t_close,
                            'Open': t_open,
                            'High': t_high,
                            'Low': t_low
                        })
                        if t_volume is not None:
                            df_t['Volume'] = t_volume
                    else:
                        df_t = data
                    
                    # Filter for the specific day
                    df_t = df_t[df_t.index.strftime("%Y-%m-%d") == self.date_str]
                    
                    if not df_t.empty and len(df_t) >= 20:
                        # Calculate day open for reference
                        day_open = df_t.iloc[0]['Open']
                        df_t['DayOpen'] = day_open
                        
                        # Calculate all technical indicators
                        df_t = self.scanner.calculate_indicators(df_t)
                        
                        self.market_data[ticker] = df_t
                        
                except KeyError:
                    if self.debug:
                        print(f"Data missing for {ticker}")
                    continue
                    
        except Exception as e:
            print(f"Error downloading data: {e}")
            return
        
        print(f"Data loaded. Found data for {len(self.market_data)} tickers.")
        print(f"Time steps: {len(self.timestamps)}")
    
    def run(self):
        """Run the simulation following guide's trading rules."""
        if not self.market_data:
            self.load_market_data()
        
        if len(self.market_data) == 0:
            print("\n⚠️  No market data available for simulation.")
            print("Note: 1-minute data is only available for the last 7-30 days from Yahoo Finance.")
            return
        
        print(f"\n{'='*60}")
        print(f"BIST Trading Simulation - {self.date_str}")
        print(f"{'='*60}")
        print(f"Initial Capital: {self.portfolio.initial_capital:.2f} TRY")
        print(f"Commission Rate: {self.portfolio.commission_rate*100:.2f}%")
        print(f"Slippage Rate: {self.portfolio.slippage_rate*100:.2f}%")
        print(f"Expected Round-Trip Cost: {(self.portfolio.commission_rate + self.portfolio.slippage_rate)*2*100:.2f}%")
        print(f"{'='*60}\n")
        
        last_report_minute = None
        
        for ts in self.timestamps:
            current_time = ts.time()
            
            # Build current market snapshot
            current_prices = {}
            for ticker, df in self.market_data.items():
                if ts in df.index:
                    row = df.loc[ts]
                    price = row['Close']
                    if not pd.isna(price):
                        current_prices[ticker] = price
            
            if not current_prices:
                continue
            
            # 1. Check daily loss limit (circuit breaker)
            if self.portfolio.check_daily_loss_limit(current_prices):
                print(f"\n🚨 CIRCUIT BREAKER: Daily loss limit (3%) hit at {current_time}")
                print("Closing all positions and stopping trading.")
                self.portfolio.close_all_positions(current_prices, ts, reason="Circuit Breaker")
                break
            
            # 2. Check exit conditions on all open positions
            # Use guide's parameters: 1.5% hard stop, 1.0% trailing, 1.5% target1, 3.0% target2
            exit_trades = self.portfolio.check_exits(
                current_prices, 
                ts,
                hard_stop_pct=0.015,
                trailing_stop_pct=0.01,
                target1_pct=0.015,
                target2_pct=0.03
            )
            
            for trade in exit_trades:
                print(f"[{current_time}] SELL: {trade.ticker} @ {trade.price:.2f} TRY")
                print(f"           Reason: {trade.reason}")
                print(f"           P&L: {trade.pnl:+.2f} TRY ({trade.pnl_pct:+.2f}%)")
                print(f"           Net P&L (after costs): {trade.pnl - trade.commission:+.2f} TRY\n")
            
            # 3. Look for new entry opportunities
            # Only if we have capacity and it's appropriate time
            # Avoid last 30 minutes (after 17:30)
            if current_time < dt_time(17, 30) and self.portfolio.cash > 100:
                num_positions = len(self.portfolio.positions)
                
                if num_positions < self.portfolio.max_positions:
                    # Scan for opportunities
                    opportunities = self.scanner.find_opportunities(self.market_data, ts)
                    
                    for opp in opportunities:
                        ticker = opp['ticker']
                        
                        # Skip if already have position
                        if ticker in self.portfolio.positions:
                            continue
                        
                        # Only trade STRONG or MODERATE signals in simulation
                        if opp['strength'] not in ['STRONG', 'MODERATE']:
                            continue
                        
                        # Calculate position size
                        position_size = self.portfolio.calculate_position_size(self.portfolio.cash)
                        
                        if position_size >= 100:
                            # Execute buy
                            trade = self.portfolio.buy(ticker, opp['price'], position_size, ts)
                            
                            if trade:
                                self.signals_generated.append(opp)
                                print(f"[{current_time}] BUY: {ticker} @ {trade.price:.2f} TRY")
                                print(f"           Signal: {opp['strength']}")
                                print(f"           Day Change: {opp['day_change_pct']:+.2f}%")
                                print(f"           RSI: {opp['rsi']:.1f} | Volume: {opp['volume_ratio']:.2f}x")
                                print(f"           Position Size: {position_size:.2f} TRY")
                                print(f"           Stop Loss: {opp['stop_loss']:.2f} TRY | Target: {opp['target1']:.2f} TRY\n")
                                
                                # Only one buy per scan cycle
                                break
            
            # 4. Periodic status update (every 30 minutes)
            if self.debug and current_time.minute % 30 == 0:
                if last_report_minute != current_time.minute:
                    equity = self.portfolio.get_total_equity(current_prices)
                    pnl = equity - self.portfolio.initial_capital
                    pnl_pct = (pnl / self.portfolio.initial_capital) * 100
                    print(f"[{current_time}] Status: Equity={equity:.2f} TRY | P&L={pnl:+.2f} TRY ({pnl_pct:+.2f}%) | Cash={self.portfolio.cash:.2f} | Positions={len(self.portfolio.positions)}")
                    last_report_minute = current_time.minute
        
        # End of Day: Close all remaining positions
        print(f"\n{'='*60}")
        print("End of Day: Closing all positions...")
        print(f"{'='*60}\n")
        
        final_prices = {}
        for ticker, df in self.market_data.items():
            if not df.empty:
                final_prices[ticker] = df.iloc[-1]['Close']
        
        eod_trades = self.portfolio.close_all_positions(final_prices, self.timestamps[-1], reason="EOD Close")
        
        for trade in eod_trades:
            print(f"EOD CLOSE: {trade.ticker} @ {trade.price:.2f} TRY | P&L: {trade.pnl:+.2f} TRY ({trade.pnl_pct:+.2f}%)")
        
        # Generate final summary
        self.print_final_report(final_prices)
    
    def print_final_report(self, current_prices: dict):
        """Print comprehensive final report."""
        summary = self.portfolio.get_daily_summary(current_prices)
        
        print(f"\n\n{'='*60}")
        print("FINAL DAILY REPORT")
        print(f"{'='*60}")
        print(f"Date: {self.date_str}")
        print(f"\nPERFORMANCE:")
        print(f"  Starting Capital:  {summary['starting_capital']:>12.2f} TRY")
        print(f"  Ending Capital:    {summary['ending_capital']:>12.2f} TRY")
        print(f"  Gross P&L:         {summary['gross_pnl']:>+12.2f} TRY")
        print(f"  Transaction Costs: {summary['total_commissions']:>12.2f} TRY")
        print(f"  Net P&L:           {summary['net_pnl']:>+12.2f} TRY ({summary['net_pnl_pct']:+.2f}%)")
        
        print(f"\nTRADE STATISTICS:")
        print(f"  Total Signals Generated: {len(self.signals_generated)}")
        print(f"  Total Trades Executed:   {summary['total_trades']}")
        print(f"  Winning Trades:          {summary['winning_trades']} ({summary['win_rate']:.1f}%)")
        print(f"  Losing Trades:           {summary['losing_trades']}")
        
        if summary['total_trades'] > 0:
            print(f"  Average Win:             {summary['avg_win']:+.2f}%")
            print(f"  Average Loss:            {summary['avg_loss']:.2f}%")
            print(f"  Profit Factor:           {summary['profit_factor']:.2f}")
        
        if summary['best_trade']:
            best = summary['best_trade']
            print(f"\n  🏆 Best Trade:  {best.ticker} → {best.pnl:+.2f} TRY ({best.pnl_pct:+.2f}%)")
        
        if summary['worst_trade']:
            worst = summary['worst_trade']
            print(f"  📉 Worst Trade: {worst.ticker} → {worst.pnl:+.2f} TRY ({worst.pnl_pct:+.2f}%)")
        
        print(f"\nRISK METRICS:")
        print(f"  Max Concurrent Positions: {self.portfolio.max_positions}")
        print(f"  Daily Loss Limit:         {self.portfolio.daily_loss_limit*100:.1f}%")
        print(f"  Commission + Slippage:    {(self.portfolio.commission_rate + self.portfolio.slippage_rate)*100:.2f}% per side")
        
        print(f"\n{'='*60}\n")
        
        # Print all trade details
        if self.portfolio.trade_history:
            print("TRADE HISTORY:")
            print(f"{'Time':<10} {'Action':<6} {'Ticker':<12} {'Price':>10} {'Shares':>8} {'P&L':>12} {'Reason':<30}")
            print("-" * 120)
            
            for trade in self.portfolio.trade_history:
                time_str = trade.time.strftime("%H:%M:%S")
                pnl_str = f"{trade.pnl:+.2f}" if trade.pnl else "-"
                reason = trade.reason or "-"
                print(f"{time_str:<10} {trade.action:<6} {trade.ticker:<12} {trade.price:>10.2f} {trade.shares:>8.2f} {pnl_str:>12} {reason:<30}")
        
        print(f"\n{'='*60}")

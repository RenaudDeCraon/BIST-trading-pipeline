class Portfolio:
    def __init__(self, initial_capital=2000.0):
        self.cash = initial_capital
        self.start_capital = initial_capital
        self.positions = {} # {ticker: {'shares': 10, 'avg_price': 100.0, 'highest_price': 100.0}}
        self.history = []
        self.equity_curve = []

    def get_total_equity(self, current_prices: dict) -> float:
        equity = self.cash
        for ticker, pos in self.positions.items():
            current_price = current_prices.get(ticker, pos['avg_price'])
            equity += pos['shares'] * current_price
        return equity

    def buy(self, ticker, price, amount_try, timestamp):
        if self.cash < amount_try:
            amount_try = self.cash
        
        if amount_try < 10: # Minimum trade size
            return False

        shares = amount_try / price
        self.cash -= amount_try
        
        if ticker not in self.positions:
            self.positions[ticker] = {'shares': 0, 'avg_price': 0.0}
        
        # Update avg price
        old_shares = self.positions[ticker]['shares']
        old_cost = old_shares * self.positions[ticker]['avg_price']
        new_cost = amount_try
        total_shares = old_shares + shares
        
        self.positions[ticker]['shares'] = total_shares
        self.positions[ticker]['avg_price'] = (old_cost + new_cost) / total_shares
        self.positions[ticker]['highest_price'] = price
        
        self.history.append({
            'action': 'BUY',
            'ticker': ticker,
            'price': price,
            'shares': shares,
            'time': timestamp,
            'balance': self.cash
        })
        return True

    def sell(self, ticker, price, factor=1.0, timestamp=None, reason="Signal"):
        """factor: 1.0 = sell all, 0.5 = sell half"""
        if ticker not in self.positions:
            return False
        
        shares_to_sell = self.positions[ticker]['shares'] * factor
        revenue = shares_to_sell * price
        
        self.cash += revenue
        self.positions[ticker]['shares'] -= shares_to_sell
        
        # Realized PnL
        buy_price = self.positions[ticker]['avg_price']
        pnl = (price - buy_price) * shares_to_sell
        pnl_pct = (pnl / (buy_price * shares_to_sell)) * 100 if buy_price > 0 else 0
        
        self.history.append({
            'action': 'SELL',
            'ticker': ticker,
            'price': price,
            'shares': shares_to_sell,
            'time': timestamp,
            'balance': self.cash,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'reason': reason
        })
        
        if self.positions[ticker]['shares'] < 1e-6:
            del self.positions[ticker]
            
        return True

    def check_stop_loss_take_profit(self, current_prices, timestamp, trailing_stop_pct=0.015, stop_loss_pct=0.03):
        """
        Trailing Stop Strategy:
        - If price drops 'stop_loss_pct' below entry -> STOP LOSS.
        - If price drops 'trailing_stop_pct' below highest reached price -> TAKE PROFIT/EXIT.
        """
        to_sell = []
        for ticker, pos in self.positions.items():
            current_price = current_prices.get(ticker)
            if not current_price:
                continue
            
            # Update high water mark
            if current_price > pos.get('highest_price', 0):
                self.positions[ticker]['highest_price'] = current_price
            
            entry_price = pos['avg_price']
            highest_price = pos['highest_price']
            
            # Calculate drops
            drawdown_from_peak = (highest_price - current_price) / highest_price
            loss_from_entry = (entry_price - current_price) / entry_price
            gain_from_entry = (current_price - entry_price) / entry_price
            
            # 1. Hard Stop Loss (e.g. 3% down from entry)
            if loss_from_entry > stop_loss_pct:
                 to_sell.append((ticker, current_price, f"Stop Loss (-{loss_from_entry*100:.2f}%)"))
                 
            # 2. Trailing Stop
            # Only activate trailing stop if we are in profit (above entry) 
            # OR if we want to protect from deep falls even if below entry (but Hard SL handles that).
            # Usually Trailing Stop is to lock profits.
            elif current_price > entry_price and drawdown_from_peak > trailing_stop_pct:
                 to_sell.append((ticker, current_price, f"Trailing Stop (Peak: {highest_price:.2f})"))
        
        for ticker, price, reason in to_sell:
            self.sell(ticker, price, timestamp=timestamp, reason=reason)

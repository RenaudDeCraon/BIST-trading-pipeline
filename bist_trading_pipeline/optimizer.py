import pandas as pd
import numpy as np

class ProfitOptimizer:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        if 'Close' not in self.data.columns:
            raise ValueError("Data must to have a 'Close' column")

    def calculate_max_possible_profit(self, initial_capital: float = 10000.0) -> dict:
        """
        Calculates the theoretical maximum profit by capturing every upward movement.
        Assumes we can buy and sell instantly at the Close price.
        """
        prices = self.data['Close'].values
        dates = self.data.index
        
        balance = initial_capital
        total_profit = 0.0
        trades = []
        
        # Greedy approach: If price[i] > price[i-1], we effectively 'held' or 'bought' at i-1 and 'sold' at i.
        # To simulate realistic compounding or fixed trades, we need to be careful.
        # For simplicity "Max Points" approach: Sum of all positive deltas.
        
        # Let's simulate a full compounding approach:
        # If P[i] > P[i-1]: Buy at P[i-1], Sell at P[i]
        
        shares = 0
        in_position = False
        
        for i in range(1, len(prices)):
            if prices[i] > prices[i-1]:
                # Price went up. If we knew this, we would have bought at i-1.
                # Theoretical gain per share = prices[i] - prices[i-1]
                delta = prices[i] - prices[i-1]
                percent_gain = delta / prices[i-1]
                
                # Update theoretical balance (compounding)
                balance = balance * (1 + percent_gain)
                trades.append({
                    'type': 'win',
                    'entry_time': dates[i-1],
                    'exit_time': dates[i],
                    'entry_price': prices[i-1],
                    'exit_price': prices[i],
                    'profit_pct': percent_gain
                })
        
        return {
            'initial_capital': initial_capital,
            'final_balance': balance,
            'profit_amount': balance - initial_capital,
            'profit_pct': ((balance - initial_capital) / initial_capital) * 100,
            'trade_count': len(trades)
        }

    def calculate_single_trade_max_profit(self, initial_capital: float = 10000.0) -> dict:
        """
        Finds the single best trade (Buy Min, Sell Max after Min).
        """
        prices = self.data['Close'].values
        dates = self.data.index
        
        if len(prices) < 2:
            return {'profit_amount': 0}
            
        min_price = prices[0]
        max_profit = 0.0
        min_price_idx = 0
        
        best_entry_idx = 0
        best_exit_idx = 0
        
        for i in range(1, len(prices)):
            if prices[i] - min_price > max_profit:
                max_profit = prices[i] - min_price
                best_exit_idx = i
                best_entry_idx = min_price_idx
            
            if prices[i] < min_price:
                min_price = prices[i]
                min_price_idx = i
                
        entry_price = prices[best_entry_idx]
        exit_price = prices[best_exit_idx]
        shares = initial_capital / entry_price
        final_balance = shares * exit_price
        
        return {
            'initial_capital': initial_capital,
            'final_balance': final_balance,
            'profit_amount': final_balance - initial_capital,
            'profit_pct': ((final_balance - initial_capital) / initial_capital) * 100,
            'entry_time': dates[best_entry_idx],
            'exit_time': dates[best_exit_idx],
            'entry_price': entry_price,
            'exit_price': exit_price
        }

class SimpleStrategy:
    def __init__(self, data: pd.DataFrame):
        self.data = data.copy()
        
    def run_sma_crossover(self, short_window=5, long_window=20, initial_capital=10000.0):
        """
        Simple Moving Average Crossover Strategy.
        Buy when Short SMA > Long SMA.
        Sell when Short SMA < Long SMA.
        """
        self.data['SMA_Short'] = self.data['Close'].rolling(window=short_window).mean()
        self.data['SMA_Long'] = self.data['Close'].rolling(window=long_window).mean()
        
        # Signal: 1 (Buy), 0 (Hold/Neutral), -1 (Sell)
        self.data['Signal'] = 0.0
        self.data.iloc[short_window:, self.data.columns.get_loc('Signal')] = np.where(
            self.data['SMA_Short'][short_window:] > self.data['SMA_Long'][short_window:], 1.0, 0.0
        )
        
        # Position: 1 (Long), 0 (Neutral)
        self.data['Position'] = self.data['Signal'].diff()
        
        balance = initial_capital
        shares = 0
        holdings = 0
        trades = []
        
        # Iterate to calculate profit (simplified backtest)
        for index, row in self.data.iterrows():
            if row['Position'] == 1.0: # Buy Signal
                if balance > 0:
                    shares = balance / row['Close']
                    balance = 0
                    trades.append({'type': 'buy', 'time': index, 'price': row['Close']})
            elif row['Position'] == -1.0: # Sell Signal
                if shares > 0:
                    balance = shares * row['Close']
                    shares = 0
                    trades.append({'type': 'sell', 'time': index, 'price': row['Close']})
                    
        # Mark to market at end
        final_balance = balance + (shares * self.data.iloc[-1]['Close'])
        
        return {
            'initial_capital': initial_capital,
            'final_balance': final_balance,
            'profit_amount': final_balance - initial_capital,
            'profit_pct': ((final_balance - initial_capital) / initial_capital) * 100,
            'trades': len(trades)
        }

import pandas as pd
import numpy as np

# BIST 30 Tickers (Liquid for simulation)
BIST30_TICKERS = [
    "AKBNK", "ALARK", "ARCLK", "ASELS", "ASTOR", "BIMAS", "BRSAN", "DOAS",
    "EKGYO", "ENJSA", "EREGL", "FROTO", "GARAN", "GUBRF", "HEKTS", "ISCTR",
    "KCHOL", "KONTR", "KOZAL", "KRDMD", "ODAS", "OYAKC", "PETKM", "PGSUS",
    "SAHOL", "SASA", "SISE", "TAVHL", "TCELL", "THYAO", "TOASO", "TUPRS",
    "YKBNK"
]

class ImprovedMarketScanner:
    """
    Enhanced market scanner with comprehensive technical analysis.
    Follows BIST Trading Agent Guide specifications.
    """
    
    def __init__(self, tickers=None):
        self.tickers = tickers if tickers else BIST30_TICKERS
    
    def get_tickers(self):
        """Return tickers with .IS suffix for Yahoo Finance."""
        return [f"{t}.IS" if not t.endswith('.IS') else t for t in self.tickers]
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all technical indicators for a stock's data.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with added indicator columns
        """
        if len(df) < 20:
            return df
        
        # Moving Averages
        df['SMA5'] = df['Close'].rolling(window=5).mean()
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        
        # RSI (14-period)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # VWAP (Volume Weighted Average Price) - cumulative for the day
        df['TypicalPrice'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['CumTPV'] = (df['TypicalPrice'] * df['Volume']).cumsum()
        df['CumVolume'] = df['Volume'].cumsum()
        df['VWAP'] = df['CumTPV'] / df['CumVolume']
        
        # Volume ratio (current vs 20-period average)
        df['AvgVolume20'] = df['Volume'].rolling(window=20).mean()
        df['VolumeRatio'] = df['Volume'] / df['AvgVolume20']
        
        return df
    
    def evaluate_entry_signal(self, row: pd.Series, day_open: float, current_time=None) -> dict:
        """
        Evaluate if current conditions warrant an entry signal.
        
        Entry Criteria (from guide):
        1. Price > SMA5 > SMA20
        2. Daily change: +0.3% to +5.0%
        3. Volume > 1.2x average
        4. RSI between 40 and 70
        5. Price above VWAP
        6. Not extended (< 7% daily change)
        
        Args:
            row: Latest data row with indicators
            day_open: Opening price of the day
            current_time: Current timestamp (to avoid last 30min)
            
        Returns:
            Signal dictionary with details or None if no signal
        """
        current_price = row['Close']
        
        # Calculate day change percentage
        day_change_pct = ((current_price - day_open) / day_open) * 100
        
        # Check all entry conditions
        conditions = {
            'price_above_sma5': current_price > row.get('SMA5', 0),
            'sma5_above_sma20': row.get('SMA5', 0) > row.get('SMA20', 0),
            'day_change_valid': 0.3 < day_change_pct < 5.0,
            'rsi_valid': 40 < row.get('RSI', 50) < 70,
            'volume_confirmed': row.get('VolumeRatio', 0) > 1.2,
            'above_vwap': current_price > row.get('VWAP', 0),
            'not_extended': day_change_pct < 7.0
        }
        
        # Count passing conditions
        passed = sum(conditions.values())
        total = len(conditions)
        
        # Determine signal strength based on conditions met
        if passed >= 6:
            strength = 'STRONG'
        elif passed >= 5:
            strength = 'MODERATE'
        elif passed >= 4:
            strength = 'WEAK'
        else:
            return None  # Not enough conditions met
        
        # Calculate stop loss and targets (from guide)
        stop_loss = current_price * 0.985      # 1.5% stop
        target1 = current_price * 1.015        # 1.5% target
        target2 = current_price * 1.030        # 3.0% target
        
        # Calculate risk/reward ratio
        risk = current_price - stop_loss
        reward = target1 - current_price
        risk_reward = reward / risk if risk > 0 else 0
        
        return {
            'signal': 'BUY',
            'strength': strength,
            'price': current_price,
            'day_change_pct': day_change_pct,
            'conditions': conditions,
            'conditions_met': f"{passed}/{total}",
            'sma5': row.get('SMA5'),
            'sma20': row.get('SMA20'),
            'rsi': row.get('RSI'),
            'vwap': row.get('VWAP'),
            'volume_ratio': row.get('VolumeRatio'),
            'stop_loss': stop_loss,
            'target1': target1,
            'target2': target2,
            'risk_reward': risk_reward,
            'day_open': day_open
        }
    
    def find_opportunities(self, market_data: dict, current_time=None) -> list:
        """
        Scan all tickers and return sorted trading opportunities.
        
        Args:
            market_data: {ticker: DataFrame with OHLCV + indicators}
            current_time: Current timestamp
            
        Returns:
            List of signal dictionaries, sorted by strength then day change
        """
        opportunities = []
        
        for ticker in self.tickers:
            full_ticker = f"{ticker}.IS" if not ticker.endswith('.IS') else ticker
            
            if full_ticker not in market_data:
                continue
            
            df = market_data[full_ticker]
            if df.empty or len(df) < 20:
                continue
            
            # Get day open (first bar's open price)
            day_open = df.iloc[0]['Open']
            
            # Calculate indicators if not already present
            if 'SMA5' not in df.columns:
                df = self.calculate_indicators(df)
                market_data[full_ticker] = df  # Update in place
            
            # Get latest row
            latest = df.iloc[-1]
            
            # Evaluate entry signal
            signal = self.evaluate_entry_signal(latest, day_open, current_time)
            
            if signal:
                signal['ticker'] = full_ticker
                signal['time'] = current_time
                opportunities.append(signal)
        
        # Sort by strength (STRONG > MODERATE > WEAK) then by day change (highest first)
        strength_order = {'STRONG': 0, 'MODERATE': 1, 'WEAK': 2}
        opportunities.sort(key=lambda x: (strength_order[x['strength']], -x['day_change_pct']))
        
        return opportunities
    
    def format_signal(self, signal: dict) -> str:
        """
        Format signal for human-readable output.
        Follows guide's signal template.
        """
        if not signal:
            return ""
        
        conditions_str = "\n".join([
            f"  {'✓' if v else '✗'} {k.replace('_', ' ').title()}"
            for k, v in signal.get('conditions', {}).items()
        ])
        
        output = f"""
=== {signal['signal']} SIGNAL ===
Ticker: {signal['ticker']}
Signal Strength: {signal['strength']}
Time: {signal.get('time', 'N/A')}

PRICE DATA:
- Current: {signal['price']:.2f} TRY
- Day Open: {signal['day_open']:.2f} TRY
- Daily Change: {signal['day_change_pct']:+.2f}%

INDICATORS:
- SMA5: {signal['sma5']:.2f} | SMA20: {signal['sma20']:.2f}
- RSI(14): {signal['rsi']:.1f}
- VWAP: {signal['vwap']:.2f}
- Volume Ratio: {signal['volume_ratio']:.2f}x

CONDITIONS MET: {signal['conditions_met']}
{conditions_str}

TRADE PLAN:
- Entry: {signal['price']:.2f} TRY
- Stop Loss: {signal['stop_loss']:.2f} TRY (-1.5%)
- Target 1: {signal['target1']:.2f} TRY (+1.5%)
- Target 2: {signal['target2']:.2f} TRY (+3.0%)
- Risk/Reward: 1:{signal['risk_reward']:.2f}
"""
        return output

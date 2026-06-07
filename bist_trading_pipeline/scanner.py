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

class MarketScanner:
    def __init__(self, tickers=None):
        self.tickers = tickers if tickers else BIST30_TICKERS
    
    def get_tickers(self):
        return [f"{t}.IS" if not t.endswith('.IS') else t for t in self.tickers]

    def find_opportunities(self, current_snapshot: pd.DataFrame) -> list:
        """
        Identify stocks suitable for aggressive buying.
        current_snapshot needs 'Price', 'Open', and optionally 'PrevClose' or moving averages.
        """
        opportunities = []
        
        # Simple Momentum Strategy:
        # 1. Price is up > 1.0% from Open (Lowered threshold for more activity)
        # 2. Prefer stocks with high daily volume (already filtered by BIST30 list roughly)
        
        for ticker, row in current_snapshot.iterrows():
            price = row['Price']
            open_price = row['Open']
            
            if pd.isna(price) or pd.isna(open_price):
                continue
                
            day_change_pct = ((price - open_price) / open_price) * 100
            
            # Aggressive Scalping logic: 
            # - Buy if Day Change is > 0.5% (Catch very early moves)
            # - Capped at 9.5% (Avoid ceiling)
            if day_change_pct > 0.5 and day_change_pct < 9.5: 
                opportunities.append({
                    'ticker': ticker,
                    'price': price,
                    'score': day_change_pct
                })
        
        # Sort by score (highest momentum first)
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        return opportunities

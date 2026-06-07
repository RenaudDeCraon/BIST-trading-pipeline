import yfinance as yf
import pandas as pd
from datetime import datetime
import os

def get_bist_ticker(symbol: str) -> str:
    """Appends .IS to the symbol if not present."""
    if not symbol.endswith('.IS'):
        return f"{symbol}.IS"
    return symbol

def fetch_history(symbol: str, start_date: str, end_date: str = None, interval: str = '1d') -> pd.DataFrame:
    """
    Fetches historical data for a given BIST symbol.
    
    Args:
        symbol: The stock symbol (e.g., THYAO)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD), optional
        interval: Data interval (1d, 1wk, 1mo)
        
    Returns:
        pandas DataFrame with historical data
    """
    ticker = get_bist_ticker(symbol)
    print(f"Fetching data for {ticker}...")
    
    try:
        data = yf.download(ticker, start=start_date, end=end_date, interval=interval, progress=False)
        if data.empty:
            print(f"Warning: No data found for {ticker}")
        else:
            print(f"Successfully fetched {len(data)} rows.")
        return data
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

def fetch_intraday_data(symbol: str, period: str = '1d', interval: str = '1m') -> pd.DataFrame:
    """
    Fetches intraday data for a given BIST symbol.
    Useful for day trading simulation.
    
    Args:
        symbol: The stock symbol
        period: Period to download (1d, 5d, 1mo)
        interval: Interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h)
        
    Returns:
        pandas DataFrame with intraday data
    """
    ticker = get_bist_ticker(symbol)
    print(f"Fetching intraday data for {ticker}...")
    
    try:
        # yf.download sometimes behaves differently than Ticker.history for intraday
        stock = yf.Ticker(ticker)
        data = stock.history(period=period, interval=interval)
        
        if data.empty:
            print(f"Warning: No intraday data found for {ticker}")
        else:
            print(f"Successfully fetched {len(data)} rows.")
        return data
    except Exception as e:
        print(f"Error fetching intraday data: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    # Test
    df = fetch_intraday_data("THYAO", period="1d", interval="1m")
    if not df.empty:
        print(df.head())
        print(df.tail())

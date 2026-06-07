# BIST Trading Pipeline & Profit Maximizer

An algorithmic stock trading simulation, analysis, and backtesting pipeline tailored for Borsa Istanbul (BIST) stock market data. This tool allows users to fetch historical and intraday stock data, calculate the theoretical maximum profit using hindsight optimization, and simulate trading strategies to evaluate their relative efficiency.

## Features

- **Data Acquisition**: Fetches historical and intraday (up to 1-minute interval) market data for Borsa Istanbul stocks (automatically appends `.IS` suffix) using `yfinance`.
- **Hindsight Profit Optimization**: Computes the absolute theoretical maximum profit achievable by catching every upward movement in 1-minute intervals.
- **Backtesting & Simulation**: Includes a full market simulation engine to test strategies (e.g., Simple SMA Crossover) and measures their efficiency against the theoretical maximum profit.
- **Stock Scanner**: Scans and evaluates multiple assets based on technical indicators.

## Project Structure

- `main.py`: Entry point of the pipeline. Runs single symbol analysis or full-day simulation.
- `data_fetcher.py`: Handles fetching historical and intraday data via `yfinance`.
- `optimizer.py`: Contains `ProfitOptimizer` for theoretical maximum profit calculation and baseline strategy setups.
- `simulation.py` & `improved_simulation.py`: Engines to simulate trading over days/symbols with capital allocation rules.
- `scanner.py` & `improved_scanner.py`: Filters and scans BIST stocks for setup triggers.
- `portfolio.py` & `improved_portfolio.py`: Manages mock trading accounts, balances, and asset tracking.
- `trading_agent.py`: Decides order placements based on technical analysis indicators.

## Setup and Usage

### Requirements
Install requirements listed in `requirements.txt`:
```bash
pip install -r requirements.txt
```

### Run Single Symbol Analysis
Analyze a stock's historical theoretical maximum profit and SMA crossover strategy efficiency for a specific date:
```bash
python main.py THYAO --date 2026-06-01 --capital 10000
```

### Run Full Market Simulation
Simulate a day's trading across multiple scanner-triggered BIST symbols:
```bash
python main.py --simulate-day --date 2026-06-01
```

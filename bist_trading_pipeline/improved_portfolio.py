from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta

@dataclass
class Position:
    """Represents an open position in a stock."""
    ticker: str
    shares: float
    entry_price: float
    entry_time: datetime
    highest_price: float
    target1_hit: bool = False
    
@dataclass
class Trade:
    """Represents a completed trade."""
    ticker: str
    action: str  # 'BUY' or 'SELL'
    price: float
    shares: float
    time: datetime
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    reason: Optional[str] = None
    commission: float = 0.0

class ImprovedPortfolio:
    """
    Enhanced portfolio manager with transaction costs and risk management.
    Follows BIST Trading Agent Guide specifications.
    """
    
    def __init__(self, 
                 initial_capital: float = 10000.0,
                 commission_rate: float = 0.0015,   # 0.15% broker commission
                 slippage_rate: float = 0.001):      # 0.1% slippage
        
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Trade] = []
        self.equity_curve: List[tuple] = []  # (time, equity)
        
        # Risk management parameters (from guide)
        self.daily_starting_capital = initial_capital
        self.max_positions = 5
        self.max_position_pct = 0.25   # 25% max in single stock
        self.daily_loss_limit = 0.03    # 3% daily loss limit
        
    def get_total_equity(self, current_prices: dict) -> float:
        """Calculate total portfolio value (cash + open positions)."""
        equity = self.cash
        for ticker, pos in self.positions.items():
            price = current_prices.get(ticker, pos.entry_price)
            equity += pos.shares * price
        return equity
    
    def check_daily_loss_limit(self, current_prices: dict) -> bool:
        """Check if daily loss limit has been hit (circuit breaker)."""
        current_equity = self.get_total_equity(current_prices)
        daily_pnl_pct = (current_equity - self.daily_starting_capital) / self.daily_starting_capital
        return daily_pnl_pct <= -self.daily_loss_limit
    
    def calculate_position_size(self, available_cash: float) -> float:
        """
        Calculate appropriate position size following guide rules.
        
        Rules:
        - 20% of available cash
        - Respect max positions limit
        - Never exceed 25% of total capital in single stock
        """
        num_positions = len(self.positions)
        
        if num_positions >= self.max_positions:
            return 0
        
        remaining_slots = self.max_positions - num_positions
        
        # 20% of available cash, but distribute across remaining slots
        size = min(
            available_cash * 0.20,
            available_cash / remaining_slots,
            self.initial_capital * self.max_position_pct
        )
        
        return size if size > 100 else 0  # Minimum 100 TRY trade
    
    def buy(self, ticker: str, price: float, amount: float, timestamp: datetime) -> Optional[Trade]:
        """
        Execute a buy order with realistic transaction costs.
        
        Args:
            ticker: Stock ticker (e.g., 'THYAO.IS')
            price: Current market price
            amount: Amount in TRY to invest
            timestamp: Time of trade
            
        Returns:
            Trade object if successful, None otherwise
        """
        # Check if already have position
        if ticker in self.positions:
            return None
        
        # Ensure we have enough cash
        if amount > self.cash:
            amount = self.cash
        
        if amount < 100:
            return None
        
        # Calculate total costs (commission + slippage)
        commission = amount * self.commission_rate
        slippage_cost = amount * self.slippage_rate
        total_cost = amount + commission + slippage_cost
        
        if total_cost > self.cash:
            # Adjust amount to fit available cash
            amount = self.cash / (1 + self.commission_rate + self.slippage_rate)
            commission = amount * self.commission_rate
            slippage_cost = amount * self.slippage_rate
            total_cost = amount + commission + slippage_cost
        
        # Execute buy with slippage (worse fill)
        effective_price = price * (1 + self.slippage_rate)
        shares = amount / effective_price
        
        self.cash -= total_cost
        
        # Create position
        self.positions[ticker] = Position(
            ticker=ticker,
            shares=shares,
            entry_price=effective_price,
            entry_time=timestamp,
            highest_price=effective_price
        )
        
        # Record trade
        trade = Trade(
            ticker=ticker,
            action='BUY',
            price=effective_price,
            shares=shares,
            time=timestamp,
            commission=commission + slippage_cost
        )
        self.trade_history.append(trade)
        
        return trade
    
    def sell(self, ticker: str, price: float, timestamp: datetime, 
             reason: str = "Manual", partial: float = 1.0) -> Optional[Trade]:
        """
        Execute a sell order with transaction costs.
        
        Args:
            ticker: Stock ticker
            price: Current market price
            timestamp: Time of trade
            reason: Reason for selling (for reporting)
            partial: Fraction to sell (1.0 = all, 0.5 = half)
            
        Returns:
            Trade object if successful, None otherwise
        """
        if ticker not in self.positions:
            return None
        
        pos = self.positions[ticker]
        shares_to_sell = pos.shares * partial
        
        # Calculate costs with slippage (worse fill on sell)
        effective_price = price * (1 - self.slippage_rate)
        gross_revenue = shares_to_sell * effective_price
        commission = gross_revenue * self.commission_rate
        net_revenue = gross_revenue - commission
        
        # Calculate P&L
        cost_basis = shares_to_sell * pos.entry_price
        pnl = net_revenue - cost_basis
        pnl_pct = (pnl / cost_basis) * 100 if cost_basis > 0 else 0
        
        self.cash += net_revenue
        
        # Update or remove position
        pos.shares -= shares_to_sell
        if pos.shares < 0.0001:  # Close position if negligible shares remain
            del self.positions[ticker]
        
        # Record trade
        trade = Trade(
            ticker=ticker,
            action='SELL',
            price=effective_price,
            shares=shares_to_sell,
            time=timestamp,
            pnl=pnl,
            pnl_pct=pnl_pct,
            reason=reason,
            commission=commission
        )
        self.trade_history.append(trade)
        
        return trade
    
    def check_exits(self, current_prices: dict, timestamp: datetime,
                    hard_stop_pct: float = 0.015,      # 1.5% hard stop
                    trailing_stop_pct: float = 0.01,    # 1.0% trailing stop
                    target1_pct: float = 0.015,         # 1.5% target 1
                    target2_pct: float = 0.03,          # 3.0% target 2
                    time_stop_hours: float = 2.0,       # 2 hour time stop
                    time_stop_min_gain: float = 0.005   # 0.5% min gain
                    ) -> List[Trade]:
        """
        Check all positions for exit conditions following guide rules.
        
        Exit Rules (from guide):
        1. Hard Stop Loss: -1.5% from entry → SELL 100%
        2. Trailing Stop: -1.0% from peak → SELL 100%
        3. Target 1: +1.5% → SELL 50%
        4. Target 2: +3.0% → SELL 100%
        5. Time Stop: >2 hours with <0.5% gain → SELL 100%
        
        Returns:
            List of executed trades
        """
        trades = []
        tickers_to_check = list(self.positions.keys())
        
        for ticker in tickers_to_check:
            if ticker not in self.positions:
                continue
                
            pos = self.positions[ticker]
            current_price = current_prices.get(ticker)
            
            if current_price is None:
                continue
            
            # Update highest price seen
            if current_price > pos.highest_price:
                self.positions[ticker].highest_price = current_price
            
            entry = pos.entry_price
            highest = pos.highest_price
            
            # Calculate metrics
            loss_from_entry = (entry - current_price) / entry
            gain_from_entry = (current_price - entry) / entry
            drawdown_from_peak = (highest - current_price) / highest
            time_in_position = timestamp - pos.entry_time
            
            # 1. Hard Stop Loss (mandatory exit)
            if loss_from_entry >= hard_stop_pct:
                trade = self.sell(ticker, current_price, timestamp,
                                  reason=f"Hard Stop Loss (-{loss_from_entry*100:.2f}%)")
                if trade:
                    trades.append(trade)
                continue
            
            # 2. Trailing Stop (only if in profit)
            if gain_from_entry > 0 and drawdown_from_peak >= trailing_stop_pct:
                trade = self.sell(ticker, current_price, timestamp,
                                  reason=f"Trailing Stop (Peak: {highest:.2f} TRY)")
                if trade:
                    trades.append(trade)
                continue
            
            # 3. Take Profit Target 1 (partial exit - 50%)
            if not pos.target1_hit and gain_from_entry >= target1_pct:
                trade = self.sell(ticker, current_price, timestamp,
                                  reason=f"Target 1 (+{gain_from_entry*100:.2f}%)",
                                  partial=0.5)
                if trade:
                    trades.append(trade)
                    if ticker in self.positions:
                        self.positions[ticker].target1_hit = True
                continue
            
            # 4. Take Profit Target 2 (full exit)
            if gain_from_entry >= target2_pct:
                trade = self.sell(ticker, current_price, timestamp,
                                  reason=f"Target 2 (+{gain_from_entry*100:.2f}%)")
                if trade:
                    trades.append(trade)
                continue
            
            # 5. Time Stop (held too long without sufficient gain)
            if time_in_position > timedelta(hours=time_stop_hours):
                if gain_from_entry < time_stop_min_gain:
                    trade = self.sell(ticker, current_price, timestamp,
                                      reason=f"Time Stop ({time_in_position.seconds//3600}h, +{gain_from_entry*100:.2f}%)")
                    if trade:
                        trades.append(trade)
                    continue
        
        return trades
    
    def close_all_positions(self, current_prices: dict, timestamp: datetime, reason: str = "EOD") -> List[Trade]:
        """Close all open positions (e.g., end of day)."""
        trades = []
        tickers = list(self.positions.keys())
        
        for ticker in tickers:
            price = current_prices.get(ticker, self.positions[ticker].entry_price)
            trade = self.sell(ticker, price, timestamp, reason=reason)
            if trade:
                trades.append(trade)
        
        return trades
    
    def get_daily_summary(self, current_prices: dict) -> dict:
        """
        Generate comprehensive daily performance summary.
        Follows guide's reporting template.
        """
        equity = self.get_total_equity(current_prices)
        
        # Filter sell trades with P&L
        sells = [t for t in self.trade_history if t.action == 'SELL' and t.pnl is not None]
        
        wins = [t for t in sells if t.pnl > 0]
        losses = [t for t in sells if t.pnl <= 0]
        
        total_commissions = sum(t.commission for t in self.trade_history)
        
        # Calculate profit factor
        total_wins = sum(t.pnl for t in wins) if wins else 0
        total_losses = abs(sum(t.pnl for t in losses)) if losses else 0
        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0
        
        return {
            'starting_capital': self.daily_starting_capital,
            'ending_capital': equity,
            'gross_pnl': equity - self.daily_starting_capital,
            'total_commissions': total_commissions,
            'net_pnl': equity - self.daily_starting_capital,
            'net_pnl_pct': ((equity - self.daily_starting_capital) / self.daily_starting_capital) * 100,
            'total_trades': len(sells),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': (len(wins) / len(sells) * 100) if sells else 0,
            'avg_win': (sum(t.pnl_pct for t in wins) / len(wins)) if wins else 0,
            'avg_loss': (sum(t.pnl_pct for t in losses) / len(losses)) if losses else 0,
            'profit_factor': profit_factor,
            'open_positions': len(self.positions),
            'best_trade': max(wins, key=lambda t: t.pnl_pct) if wins else None,
            'worst_trade': min(losses, key=lambda t: t.pnl_pct) if losses else None
        }
    
    def format_daily_summary(self, summary: dict) -> str:
        """Format daily summary for human-readable output."""
        best = summary['best_trade']
        worst = summary['worst_trade']
        
        output = f"""
=== DAILY TRADING SUMMARY ===

PERFORMANCE:
- Starting Capital: {summary['starting_capital']:.2f} TRY
- Ending Capital: {summary['ending_capital']:.2f} TRY
- Gross P&L: {summary['gross_pnl']:+.2f} TRY
- Estimated Costs: {summary['total_commissions']:.2f} TRY
- Net P&L: {summary['net_pnl']:+.2f} TRY ({summary['net_pnl_pct']:+.2f}%)

TRADE STATISTICS:
- Total Trades: {summary['total_trades']}
- Winning Trades: {summary['winning_trades']} ({summary['win_rate']:.1f}%)
- Losing Trades: {summary['losing_trades']}
- Average Win: {summary['avg_win']:+.2f}%
- Average Loss: {summary['avg_loss']:.2f}%
- Profit Factor: {summary['profit_factor']:.2f}
"""
        
        if best:
            output += f"\nBEST TRADE: {best.ticker} {best.pnl:+.2f} TRY ({best.pnl_pct:+.2f}%)"
        if worst:
            output += f"\nWORST TRADE: {worst.ticker} {worst.pnl:+.2f} TRY ({worst.pnl_pct:+.2f}%)"
        
        return output

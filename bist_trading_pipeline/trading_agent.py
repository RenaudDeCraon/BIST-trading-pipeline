#!/usr/bin/env python3
"""
BIST Trading Agent - Professional Edition
Follows comprehensive trading guide specifications.

Usage:
    python trading_agent.py --simulate --date 2026-01-23 --capital 10000
"""

import argparse
from datetime import datetime
from improved_simulation import ImprovedSimulationEngine

def main():
    parser = argparse.ArgumentParser(
        description="BIST Trading Agent - Professional Edition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run simulation for today
  python trading_agent.py --simulate --capital 10000
  
  # Run simulation for specific date
  python trading_agent.py --simulate --date 2026-01-23 --capital 5000
  
  # Run with debug output
  python trading_agent.py --simulate --date 2026-01-23 --debug
        """
    )
    
    parser.add_argument(
        '--simulate',
        action='store_true',
        help='Run full day simulation with scanner'
    )
    
    parser.add_argument(
        '--date',
        type=str,
        default=datetime.now().strftime("%Y-%m-%d"),
        help='Date to simulate (YYYY-MM-DD), default: today'
    )
    
    parser.add_argument(
        '--capital',
        type=float,
        default=2000.0,
        help='Initial capital in TRY, default: 2000'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output'
    )
    
    args = parser.parse_args()
    
    if args.simulate:
        print("\n" + "="*70)
        print("BIST TRADING AGENT - PROFESSIONAL EDITION")
        print("="*70)
        print(f"\nStarting simulation for {args.date}")
        print(f"Initial Capital: {args.capital:.2f} TRY")
        print("\nThis agent follows professional trading rules:")
        print("  ✓ Technical analysis (SMA, RSI, VWAP, Volume)")
        print("  ✓ Transaction costs (0.15% commission + 0.1% slippage)")
        print("  ✓ Risk management (1.5% stop loss, 1.0% trailing stop)")
        print("  ✓ Partial exits (50% at +1.5%, 100% at +3.0%)")
        print("  ✓ Daily loss limit (3% circuit breaker)")
        print("="*70 + "\n")
        
        engine = ImprovedSimulationEngine(
            date_str=args.date,
            initial_capital=args.capital,
            debug=args.debug
        )
        
        try:
            engine.run()
        except KeyboardInterrupt:
            print("\n\nSimulation interrupted by user.")
        except Exception as e:
            print(f"\n\n❌ Error during simulation: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
        
    else:
        parser.print_help()
        print("\n⚠️  Please use --simulate flag to run simulation.")

if __name__ == "__main__":
    main()

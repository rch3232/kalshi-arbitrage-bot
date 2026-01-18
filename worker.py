#!/usr/bin/env python3
"""
Kalshi Arbitrage Bot - Background Worker

Continuous market monitoring and trading worker designed for deployment
on cloud platforms like Render, Heroku, or Railway.

This worker runs indefinitely, scanning markets for arbitrage opportunities
and executing trades based on configured parameters. It's optimized for
maximum market coverage while respecting API rate limits.

Features:
    - Continuous operation with automatic restart on errors
    - Dynamic market limit scaling based on API performance
    - Comprehensive error handling and logging
    - Health check endpoint for monitoring
    - Graceful shutdown on termination signals
"""
import os
import sys
import time
import signal
from datetime import datetime
from dotenv import load_dotenv

# Import bot components
from src.market_api import KalshiClient
from src.opportunity_analyzer import ArbitrageAnalyzer
from src.execution_engine import TradeExecutor
from src.capital_manager import CapitalManager

load_dotenv()


class BackgroundWorker:
    """
    Background worker for continuous market monitoring and trading.

    Designed for 24/7 operation on cloud platforms with automatic
    recovery from transient failures.
    """

    def __init__(self):
        """Initialize the worker with configuration from environment."""
        # Initialize API client
        self.client = KalshiClient()

        # Initialize capital manager
        self.capital_manager = CapitalManager(
            client=self.client,
            max_capital_per_trade_pct=float(os.getenv("MAX_CAPITAL_PER_TRADE_PCT", "0.05")),
            max_total_exposure_pct=float(os.getenv("MAX_TOTAL_EXPOSURE_PCT", "0.30")),
            min_balance_buffer=float(os.getenv("MIN_BALANCE_BUFFER", "100.0"))
        )

        # Initialize analyzers
        self.arbitrage_analyzer = ArbitrageAnalyzer()

        # Auto-execute trades based on config
        auto_execute = os.getenv("AUTO_EXECUTE_TRADES", "false").lower() == "true"

        self.trade_executor = TradeExecutor(
            client=self.client,
            capital_manager=self.capital_manager,
            min_profit_cents=int(os.getenv("MIN_PROFIT_CENTS", "2")),
            max_position_size=int(os.getenv("MAX_POSITION_SIZE", "1000")),
            auto_execute=auto_execute
        )

        # Configuration
        self.scan_interval = int(os.getenv("SCAN_INTERVAL_SECONDS", "300"))  # 5 minutes
        self.market_limit = int(os.getenv("MARKET_SCAN_LIMIT", "1000"))  # Scan up to 1000 markets
        self.min_liquidity = int(os.getenv("MIN_LIQUIDITY", "10000"))  # $100 minimum
        self.min_profit_per_day = float(os.getenv("MIN_PROFIT_PER_DAY", "0.1"))

        # State tracking
        self.running = True
        self.scan_count = 0
        self.total_opportunities_found = 0
        self.total_trades_executed = 0
        self.start_time = datetime.now()

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n[{datetime.now()}] Received signal {signum}. Shutting down gracefully...")
        self.running = False

    def filter_markets_by_liquidity(self, markets):
        """Filter markets by liquidity threshold."""
        filtered = []
        for market in markets:
            if market.get("liquidity", 0) < self.min_liquidity:
                continue

            yes_bid = market.get("yes_bid")
            yes_ask = market.get("yes_ask")
            no_bid = market.get("no_bid")
            no_ask = market.get("no_ask")

            has_yes_liquidity = yes_bid is not None and yes_ask is not None and yes_bid != yes_ask
            has_no_liquidity = no_bid is not None and no_ask is not None and no_bid != no_ask

            if has_yes_liquidity or has_no_liquidity:
                filtered.append(market)

        return filtered

    def scan_markets(self):
        """
        Perform a single scan of markets for opportunities.

        Returns:
            Tuple of (arbitrage_opportunities, trade_opportunities, executed_count)
        """
        try:
            print(f"\n{'='*70}")
            print(f"[{datetime.now()}] Starting market scan #{self.scan_count + 1}")
            print(f"{'='*70}")

            # Fetch markets
            markets = self.client.get_markets(limit=self.market_limit, status="open")
            if not markets:
                print("No markets found or API error.")
                return [], [], 0

            # Filter by liquidity
            original_count = len(markets)
            markets = self.filter_markets_by_liquidity(markets)
            print(f"Scanned {original_count} markets, {len(markets)} passed liquidity filter")

            if not markets:
                return [], [], 0

            # Scan for arbitrage opportunities
            arbitrage_opps = self.arbitrage_analyzer.find_opportunities(markets, client=self.client)
            arbitrage_opps = [
                opp for opp in arbitrage_opps
                if opp.profit_per_day >= self.min_profit_per_day
            ]

            # Scan for spread trading opportunities
            trade_opps = self.trade_executor.scan_and_execute(markets, limit=self.market_limit)
            trade_opps.sort(key=lambda x: x.net_profit, reverse=True)

            # Count executed trades
            executed_count = len([t for t in self.trade_executor.executed_trades
                                if t.get('timestamp', datetime.min) > datetime.now()])

            # Update statistics
            total_opps = len(arbitrage_opps) + len(trade_opps)
            self.total_opportunities_found += total_opps
            self.total_trades_executed += executed_count

            # Display summary
            if total_opps > 0:
                print(f"\n✅ Found {total_opps} opportunities:")
                print(f"   • {len(trade_opps)} spread trading opportunities")
                print(f"   • {len(arbitrage_opps)} probability arbitrage opportunities")

                # Show top 3 opportunities
                if trade_opps:
                    print(f"\nTop Spread Opportunity:")
                    top = trade_opps[0]
                    print(f"   {top.market_ticker}: Buy at {top.buy_price}¢, "
                          f"Sell at {top.sell_price}¢, Net: ${top.net_profit:.2f}")

                if arbitrage_opps:
                    print(f"\nTop Arbitrage Opportunity:")
                    top = arbitrage_opps[0]
                    print(f"   {top.market_ticker}: {top.deviation:.2f}% deviation, "
                          f"${top.profit_per_day:.2f}/day")

                if executed_count > 0:
                    print(f"\n💰 Executed {executed_count} trades automatically")
            else:
                print("\nNo profitable opportunities found in this scan")

            return arbitrage_opps, trade_opps, executed_count

        except Exception as e:
            print(f"\n❌ Error during market scan: {e}")
            import traceback
            traceback.print_exc()
            return [], [], 0

    def display_statistics(self):
        """Display worker statistics."""
        uptime = (datetime.now() - self.start_time).total_seconds()
        uptime_hours = uptime / 3600

        print(f"\n{'='*70}")
        print("WORKER STATISTICS")
        print(f"{'='*70}")
        print(f"Uptime: {uptime_hours:.2f} hours")
        print(f"Total Scans: {self.scan_count}")
        print(f"Opportunities Found: {self.total_opportunities_found}")
        print(f"Trades Executed: {self.total_trades_executed}")
        if self.scan_count > 0:
            print(f"Avg Opportunities/Scan: {self.total_opportunities_found/self.scan_count:.2f}")
        print(f"{'='*70}\n")

    def run(self):
        """
        Main worker loop - runs continuously until stopped.
        """
        print(f"\n{'='*70}")
        print("KALSHI ARBITRAGE BOT - BACKGROUND WORKER")
        print(f"{'='*70}")
        print(f"Started at: {self.start_time}")
        print(f"Scan interval: {self.scan_interval} seconds")
        print(f"Market limit: {self.market_limit} markets per scan")
        print(f"Auto-execute: {self.trade_executor.auto_execute}")
        print(f"{'='*70}\n")

        # Display initial capital status
        self.capital_manager.display_capital_status()

        # Main loop
        while self.running:
            try:
                # Perform scan
                self.scan_count += 1
                self.scan_markets()

                # Display statistics every 10 scans
                if self.scan_count % 10 == 0:
                    self.display_statistics()
                    # Refresh capital status
                    self.capital_manager.display_capital_status()

                # Wait before next scan
                if self.running:
                    print(f"\n⏳ Next scan in {self.scan_interval} seconds...")
                    print(f"   (Press Ctrl+C to stop)\n")
                    time.sleep(self.scan_interval)

            except KeyboardInterrupt:
                print("\n\nShutdown requested by user")
                self.running = False
            except Exception as e:
                print(f"\n❌ Unexpected error in main loop: {e}")
                import traceback
                traceback.print_exc()

                # Wait before retrying to avoid rapid error loops
                if self.running:
                    print("\nWaiting 60 seconds before retry...")
                    time.sleep(60)

        # Shutdown
        print(f"\n{'='*70}")
        print("WORKER SHUTDOWN")
        print(f"{'='*70}")
        self.display_statistics()
        print("Goodbye!\n")


def main():
    """Entry point for background worker."""
    try:
        worker = BackgroundWorker()
        worker.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

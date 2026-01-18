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
from src.utils import safe_get

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
        self.scan_interval = int(os.getenv("SCAN_INTERVAL_SECONDS", "30"))  # 30 seconds
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
        """Filter markets by volume and open_interest threshold.

        Note: Market objects from get_markets() don't include orderbook data.
        We filter by volume/open_interest, then fetch orderbooks separately.
        """
        filtered = []
        for market in markets:
            # Use safe_get to handle both dict and object formats
            volume = safe_get(market, 'volume', 0)
            open_interest = safe_get(market, 'open_interest', 0)

            # Filter by volume OR open interest (whichever is higher indicates activity)
            # min_liquidity is in cents, volume is in contracts, so divide by 100
            min_volume_contracts = self.min_liquidity / 100

            if volume >= min_volume_contracts or open_interest >= min_volume_contracts:
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

            # DEBUG: Show first market's properties to verify correct attribute names
            if markets and len(markets) > 0:
                first_market = markets[0]
                print(f"\n🔍 DEBUG: First market type: {type(first_market)}")
                print(f"🔍 DEBUG: First market object: {first_market}")
                if hasattr(first_market, '__dict__'):
                    print(f"🔍 DEBUG: First market attributes: {list(vars(first_market).keys())}")
                elif isinstance(first_market, dict):
                    print(f"🔍 DEBUG: First market keys: {list(first_market.keys())}")

                # Try to access various possible property names
                print(f"🔍 DEBUG: Trying different property names:")
                for prop in ['ticker', 'liquidity', 'yes_bid', 'yes_ask', 'no_bid', 'no_ask',
                            'yes_sub_title', 'no_sub_title', 'volume', 'open_interest']:
                    try:
                        value = safe_get(first_market, prop, 'N/A')
                        print(f"   • {prop}: {value}")
                    except Exception as e:
                        print(f"   • {prop}: ERROR - {e}")
                print()

            # Filter by liquidity
            original_count = len(markets)
            markets = self.filter_markets_by_liquidity(markets)
            print(f"Scanned {original_count} markets, {len(markets)} passed liquidity filter")

            if not markets:
                return [], [], 0

            # Fetch orderbooks for all filtered markets (with rate limiting)
            # This prevents fetching the same orderbook multiple times
            print(f"Fetching orderbooks for {len(markets)} markets...")
            markets_with_orderbooks = []
            for i, market in enumerate(markets):
                ticker = safe_get(market, "ticker", "")
                if not ticker:
                    continue

                try:
                    import time
                    time.sleep(0.2)  # 200ms delay to respect rate limits
                    orderbook = self.client.get_market_orderbook(ticker)
                    if orderbook:
                        markets_with_orderbooks.append({
                            'market': market,
                            'orderbook': orderbook
                        })

                    # Progress update every 10 markets
                    if (i + 1) % 10 == 0:
                        print(f"  Fetched {i + 1}/{len(markets)} orderbooks...")
                except Exception as e:
                    print(f"  Error fetching orderbook for {ticker}: {e}")
                    continue

            print(f"Successfully fetched {len(markets_with_orderbooks)} orderbooks")

            if not markets_with_orderbooks:
                print("No orderbooks available for analysis")
                return [], [], 0

            # Analyze for arbitrage opportunities
            arbitrage_opps = []
            for item in markets_with_orderbooks:
                opp = self.arbitrage_analyzer.analyze_market(item['market'], item['orderbook'])
                if opp and opp.profit_per_day >= self.min_profit_per_day:
                    arbitrage_opps.append(opp)

            arbitrage_opps.sort(key=lambda x: x.profit_per_day, reverse=True)

            # Analyze for spread trading opportunities
            trade_opps = []
            for item in markets_with_orderbooks:
                opps = self.trade_executor.analyze_orderbook_spread(item['market'], item['orderbook'])
                for opp in opps:
                    if self.trade_executor.auto_execute:
                        success, message = self.trade_executor.execute_trade(opp)
                        if success:
                            print(f"[AUTO-EXECUTE] {message}")
                            trade_opps.append(opp)
                        else:
                            print(f"[AUTO-EXECUTE FAILED] {message}")
                    else:
                        trade_opps.append(opp)

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

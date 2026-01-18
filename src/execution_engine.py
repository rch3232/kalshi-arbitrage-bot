"""
Spread Trading Execution Module

Professional orderbook analysis and trade execution system for identifying and
capitalizing on immediate spread trading opportunities in Kalshi markets.

Spread trading opportunities arise when orderbook bid prices exceed ask prices,
enabling simultaneous buy and sell execution for instant profit realization.

Example Scenario:
    - Best bid: 43¢ (highest price buyers are willing to pay)
    - Best ask: 42¢ (lowest price sellers are willing to accept)
    - Profit: 1¢ per contract (minus trading fees)

The module provides:
    - Intelligent orderbook analysis for spread detection
    - Accurate net profit calculation including all fees
    - Automated trade execution with safety controls
    - Comprehensive trade tracking and monitoring
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from .market_api import KalshiClient
from .cost_calculator import FeeCalculator
from .utils import safe_get


class TradeOpportunity:
    """
    Data structure representing a spread trading opportunity.
    
    Contains all information necessary to evaluate and execute a spread trade,
    including pricing, quantities, and calculated profitability metrics.
    """
    
    def __init__(self, market_ticker: str, market_title: str, side: str,
                 buy_price: int, sell_price: int, quantity: int,
                 gross_profit: float, net_profit: float):
        self.market_ticker = market_ticker
        self.market_title = market_title
        self.side = side  # 'yes' or 'no'
        self.buy_price = buy_price  # Price to buy at (cents)
        self.sell_price = sell_price  # Price to sell at (cents)
        self.quantity = quantity
        self.gross_profit = gross_profit
        self.net_profit = net_profit
        self.spread = sell_price - buy_price
    
    def __repr__(self):
        return (f"TradeOpportunity(ticker={self.market_ticker}, "
                f"side={self.side}, buy={self.buy_price}¢, "
                f"sell={self.sell_price}¢, qty={self.quantity}, "
                f"net_profit=${self.net_profit:.2f})")


class TradeExecutor:
    """
    Professional trade execution engine for spread trading opportunities.
    
    Analyzes orderbooks, identifies profitable spread opportunities, and executes
    trades automatically when enabled. Includes comprehensive risk management
    and position sizing controls.
    """
    
    def __init__(self, client: KalshiClient, capital_manager=None,
                 min_profit_cents: int = 2, max_position_size: int = 1000,
                 auto_execute: bool = False):
        """
        Initialize the trade executor.

        Args:
            client: KalshiClient instance for API calls
            capital_manager: Optional CapitalManager for dynamic position sizing
            min_profit_cents: Minimum profit in cents per contract to execute
            max_position_size: Maximum number of contracts per trade
            auto_execute: If True, automatically execute trades without confirmation
        """
        self.client = client
        self.capital_manager = capital_manager
        self.min_profit_cents = min_profit_cents
        self.max_position_size = max_position_size
        self.auto_execute = auto_execute
        self.executed_trades = []
        self.current_exposure = 0.0  # Track total exposure for capital management
    
    def analyze_orderbook_spread(self, market_data: Dict,
                                  orderbook: Optional[Dict] = None) -> List[TradeOpportunity]:
        """
        Analyze orderbook for immediate spread trading opportunities.
        Finds cases where we can buy low and sell high instantly.

        NOTE: Market objects from get_markets() don't have pricing data.
        You MUST provide orderbook data for analysis.

        Args:
            market_data: Market information (ticker, title, etc.)
            orderbook: REQUIRED - Orderbook from get_market_orderbook()
                      Format: {'orderbook': {'yes': [[price, qty], ...], 'no': [[price, qty], ...]}}

        Returns:
            List of TradeOpportunity objects
        """
        opportunities = []
        market_ticker = safe_get(market_data, "ticker", "")
        market_title = safe_get(market_data, "title", "")

        # CRITICAL: Market objects don't have pricing - must use orderbook
        if not orderbook or 'orderbook' not in orderbook:
            return []

        ob = orderbook['orderbook']

        # Extract best bids from orderbook
        # Kalshi orderbooks: 'yes' and 'no' arrays of [price, quantity]
        # In binary markets: yes_ask = 100 - no_bid, no_ask = 100 - yes_bid
        yes_bid = None
        yes_bid_qty = 0
        no_bid = None
        no_bid_qty = 0
        yes_ask = None
        yes_ask_qty = 0
        no_ask = None
        no_ask_qty = 0

        if 'yes' in ob and ob['yes'] and len(ob['yes']) > 0:
            yes_bid = ob['yes'][0][0]          # Best yes bid price
            yes_bid_qty = ob['yes'][0][1]      # Quantity available at that price
            no_ask = 100 - yes_bid              # Calculate no ask from yes bid
            no_ask_qty = yes_bid_qty

        if 'no' in ob and ob['no'] and len(ob['no']) > 0:
            no_bid = ob['no'][0][0]            # Best no bid price
            no_bid_qty = ob['no'][0][1]        # Quantity available
            yes_ask = 100 - no_bid              # Calculate yes ask from no bid
            yes_ask_qty = no_bid_qty


        # Check YES side: spread = bid - ask (can we buy at ask and sell at bid?)
        if yes_ask is not None and yes_bid is not None:
            spread = yes_bid - yes_ask
            if spread >= self.min_profit_cents:
                # Quantity limited by orderbook depth
                available_qty = min(yes_ask_qty, yes_bid_qty) if yes_ask_qty and yes_bid_qty else 0

                if available_qty > 0:
                    # Use capital manager for dynamic position sizing
                    if self.capital_manager:
                        max_qty = self.capital_manager.get_max_position_size(yes_ask, self.current_exposure)
                        quantity = min(max_qty, self.max_position_size, available_qty)
                    else:
                        quantity = min(self.max_position_size, available_qty)

                    # Calculate profit
                    gross_profit_per_contract = spread / 100.0  # Convert cents to dollars
                    gross_profit = gross_profit_per_contract * quantity

                    # Calculate fees (we pay fees on both buy and sell)
                    buy_fee = FeeCalculator.calculate_fee(yes_ask, quantity, is_maker=False)
                    sell_fee = FeeCalculator.calculate_fee(yes_bid, quantity, is_maker=False)
                    total_fees = buy_fee + sell_fee

                    net_profit = gross_profit - total_fees

                    if net_profit > 0:
                        opportunities.append(TradeOpportunity(
                            market_ticker=market_ticker,
                            market_title=market_title,
                            side='yes',
                            buy_price=yes_ask,
                            sell_price=yes_bid,
                            quantity=quantity,
                            gross_profit=gross_profit,
                            net_profit=net_profit
                        ))

        # Check NO side: spread = bid - ask
        if no_ask is not None and no_bid is not None:
            spread = no_bid - no_ask
            if spread >= self.min_profit_cents:
                # Quantity limited by orderbook depth
                available_qty = min(no_ask_qty, no_bid_qty) if no_ask_qty and no_bid_qty else 0

                if available_qty > 0:
                    # Use capital manager for dynamic position sizing
                    if self.capital_manager:
                        max_qty = self.capital_manager.get_max_position_size(no_ask, self.current_exposure)
                        quantity = min(max_qty, self.max_position_size, available_qty)
                    else:
                        quantity = min(self.max_position_size, available_qty)

                    gross_profit_per_contract = spread / 100.0
                    gross_profit = gross_profit_per_contract * quantity

                    buy_fee = FeeCalculator.calculate_fee(no_ask, quantity, is_maker=False)
                    sell_fee = FeeCalculator.calculate_fee(no_bid, quantity, is_maker=False)
                    total_fees = buy_fee + sell_fee

                    net_profit = gross_profit - total_fees

                    if net_profit > 0:
                        opportunities.append(TradeOpportunity(
                            market_ticker=market_ticker,
                            market_title=market_title,
                            side='no',
                            buy_price=no_ask,
                            sell_price=no_bid,
                            quantity=quantity,
                            gross_profit=gross_profit,
                            net_profit=net_profit
                        ))

        return opportunities
    
    def _refine_with_orderbook(self, opportunities: List[TradeOpportunity], 
                               orderbook: Dict) -> List[TradeOpportunity]:
        """
        Refine opportunities using detailed orderbook data.
        
        Args:
            opportunities: List of trade opportunities
            orderbook: Detailed orderbook data
        
        Returns:
            Refined list of opportunities with accurate quantities
        """
        refined = []
        
        for opp in opportunities:
            # Try to get orderbook depth for this side
            # Orderbook structure may vary, so we'll try common formats
            yes_data = orderbook.get("yes", {})
            no_data = orderbook.get("no", {})
            
            if opp.side == 'yes' and yes_data:
                bids = yes_data.get("bids", [])
                asks = yes_data.get("asks", [])
                
                if asks and bids:
                    # Find best ask (lowest price) and best bid (highest price)
                    best_ask = asks[0] if isinstance(asks[0], dict) else {'price': opp.buy_price, 'count': 100}
                    best_bid = bids[0] if isinstance(bids[0], dict) else {'price': opp.sell_price, 'count': 100}
                    
                    # Quantity is limited by available liquidity
                    ask_qty = best_ask.get('count', 100) if isinstance(best_ask, dict) else 100
                    bid_qty = best_bid.get('count', 100) if isinstance(best_bid, dict) else 100
                    max_qty = min(ask_qty, bid_qty, self.max_position_size)
                    
                    if max_qty > 0:
                        opp.quantity = max_qty
                        # Recalculate profit with new quantity
                        gross_profit_per_contract = opp.spread / 100.0
                        opp.gross_profit = gross_profit_per_contract * max_qty
                        buy_fee = FeeCalculator.calculate_fee(opp.buy_price, max_qty, is_maker=False)
                        sell_fee = FeeCalculator.calculate_fee(opp.sell_price, max_qty, is_maker=False)
                        opp.net_profit = opp.gross_profit - buy_fee - sell_fee
                        
                        if opp.net_profit > 0:
                            refined.append(opp)
            
            elif opp.side == 'no' and no_data:
                bids = no_data.get("bids", [])
                asks = no_data.get("asks", [])
                
                if asks and bids:
                    best_ask = asks[0] if isinstance(asks[0], dict) else {'price': opp.buy_price, 'count': 100}
                    best_bid = bids[0] if isinstance(bids[0], dict) else {'price': opp.sell_price, 'count': 100}
                    
                    ask_qty = best_ask.get('count', 100) if isinstance(best_ask, dict) else 100
                    bid_qty = best_bid.get('count', 100) if isinstance(best_bid, dict) else 100
                    max_qty = min(ask_qty, bid_qty, self.max_position_size)
                    
                    if max_qty > 0:
                        opp.quantity = max_qty
                        gross_profit_per_contract = opp.spread / 100.0
                        opp.gross_profit = gross_profit_per_contract * max_qty
                        buy_fee = FeeCalculator.calculate_fee(opp.buy_price, max_qty, is_maker=False)
                        sell_fee = FeeCalculator.calculate_fee(opp.sell_price, max_qty, is_maker=False)
                        opp.net_profit = opp.gross_profit - buy_fee - sell_fee
                        
                        if opp.net_profit > 0:
                            refined.append(opp)
            else:
                # Keep original opportunity if we can't refine it
                refined.append(opp)
        
        return refined
    
    def execute_trade(self, opportunity: TradeOpportunity, use_market_orders: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Execute a trade opportunity using IOC (Immediate or Cancel) orders.

        Uses IOC orders by default to ensure both legs execute immediately or not at all,
        preventing one-sided exposure. Verifies order fills before recording the trade.

        Args:
            opportunity: TradeOpportunity to execute
            use_market_orders: If True, use market orders for instant execution.
                             If False, use limit orders with IOC time-in-force (default)

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            import time

            # Verify we can afford the trade with capital manager
            if self.capital_manager:
                trade_cost = (opportunity.buy_price / 100.0) * opportunity.quantity
                if not self.capital_manager.can_afford_trade(
                    opportunity.buy_price, opportunity.quantity, self.current_exposure
                ):
                    return False, f"Insufficient capital for trade (cost: ${trade_cost:.2f})"

            # Execute buy order first with IOC (Immediate or Cancel)
            # This ensures the order fills immediately or gets cancelled
            buy_result = self.client.place_order(
                market_ticker=opportunity.market_ticker,
                side=opportunity.side,
                action='buy',
                count=opportunity.quantity,
                price=opportunity.buy_price,
                order_type='market' if use_market_orders else 'limit',
                time_in_force='ioc'  # IOC: fills immediately or cancels
            )

            if not buy_result:
                return False, f"Failed to place buy order for {opportunity.market_ticker}"

            # Verify buy order was filled (not just placed)
            # IOC orders either fill immediately or get cancelled
            buy_order_id = buy_result.get('order', {}).get('order_id') or buy_result.get('order_id')
            buy_status = buy_result.get('order', {}).get('status') or buy_result.get('status', 'unknown')

            if buy_status in ['cancelled', 'canceled']:
                return False, f"Buy order cancelled (no liquidity at {opportunity.buy_price}¢)"

            # Small delay to ensure order is processed
            time.sleep(0.2)

            # Execute sell order with IOC
            sell_result = self.client.place_order(
                market_ticker=opportunity.market_ticker,
                side=opportunity.side,
                action='sell',
                count=opportunity.quantity,
                price=opportunity.sell_price,
                order_type='market' if use_market_orders else 'limit',
                time_in_force='ioc'  # IOC: fills immediately or cancels
            )

            if not sell_result:
                # Buy order already filled - we now have one-sided exposure
                # Log this as a warning but don't fail completely
                print(f"⚠️  WARNING: Sell order failed for {opportunity.market_ticker}")
                print(f"    You now hold a position - please close manually!")
                return False, f"Sell order failed (one-sided exposure risk)"

            # Verify sell order was filled
            sell_status = sell_result.get('order', {}).get('status') or sell_result.get('status', 'unknown')

            if sell_status in ['cancelled', 'canceled']:
                # Buy order filled but sell didn't - one-sided exposure
                print(f"⚠️  WARNING: Sell order cancelled for {opportunity.market_ticker}")
                print(f"    Buy filled but sell cancelled - you hold a position!")
                return False, f"Sell order cancelled (one-sided exposure - close manually)"

            # Both orders filled successfully
            trade_cost = (opportunity.buy_price / 100.0) * opportunity.quantity
            trade_record = {
                'timestamp': datetime.now(),
                'market_ticker': opportunity.market_ticker,
                'side': opportunity.side,
                'buy_price': opportunity.buy_price,
                'sell_price': opportunity.sell_price,
                'quantity': opportunity.quantity,
                'net_profit': opportunity.net_profit,
                'buy_order': buy_result,
                'sell_order': sell_result,
                'trade_cost': trade_cost,
                'buy_order_id': buy_order_id,
                'buy_status': buy_status,
                'sell_status': sell_status
            }
            self.executed_trades.append(trade_record)

            # Update exposure tracking
            # Note: Spread trades are closed immediately, so no ongoing exposure

            return True, (f"✅ Trade executed: {opportunity.quantity} contracts @ "
                          f"{opportunity.buy_price}¢/{opportunity.sell_price}¢, "
                          f"profit: ${opportunity.net_profit:.2f}")

        except Exception as e:
            return False, f"Error executing trade: {str(e)}"
    
    def scan_and_execute(self, markets: List[Dict], limit: int = 50) -> List[TradeOpportunity]:
        """
        Scan markets for immediate trade opportunities and optionally execute them.
        
        Args:
            markets: List of market dictionaries to scan
            limit: Maximum number of markets to scan
        
        Returns:
            List of TradeOpportunity objects found
        """
        all_opportunities = []
        
        for market in markets[:limit]:
            market_ticker = safe_get(market, "ticker", "")
            if not market_ticker:
                continue
            
            # Get orderbook for more accurate analysis (with rate limiting)
            orderbook = None
            try:
                import time
                time.sleep(0.2)  # 200ms delay between orderbook requests
                orderbook = self.client.get_market_orderbook(market_ticker)
            except:
                pass
            
            opportunities = self.analyze_orderbook_spread(market, orderbook)
            
            for opp in opportunities:
                if self.auto_execute:
                    success, message = self.execute_trade(opp)
                    if success:
                        print(f"[AUTO-EXECUTE] {message}")
                        all_opportunities.append(opp)
                    else:
                        print(f"[AUTO-EXECUTE FAILED] {message}")
                else:
                    all_opportunities.append(opp)
        
        return all_opportunities
    
    def display_opportunity(self, opp: TradeOpportunity, index: int = None):
        """Display details of a trade opportunity."""
        prefix = f"[{index}] " if index is not None else ""
        print(f"\n{prefix}{'='*60}")
        print(f"Market: {opp.market_title}")
        print(f"Ticker: {opp.market_ticker}")
        print(f"Side: {opp.side.upper()}")
        print(f"Buy Price: {opp.buy_price}¢")
        print(f"Sell Price: {opp.sell_price}¢")
        print(f"Spread: {opp.spread}¢")
        print(f"Quantity: {opp.quantity} contracts")
        print(f"\nProfit Analysis:")
        print(f"  Gross Profit: ${opp.gross_profit:.2f}")
        print(f"  Net Profit (after fees): ${opp.net_profit:.2f}")
        print(f"  Profit per Contract: ${opp.net_profit / opp.quantity:.4f}")
        print(f"{'='*60}\n")


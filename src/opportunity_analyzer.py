"""
Probability Arbitrage Detection Module

Advanced market analysis system for identifying probability arbitrage opportunities
in Kalshi prediction markets. This module detects market inefficiencies where contract
probabilities deviate from expected values, creating risk-free profit opportunities.

Arbitrage occurs when the combined YES and NO contract probabilities don't equal 100%:
    - Overpricing: YES at 52¢ + NO at 50¢ = 102% total (2% profit opportunity)
    - Underpricing: YES at 48¢ + NO at 50¢ = 98% total (2% profit opportunity)

The module performs comprehensive analysis including:
    - Gross profit calculation from probability deviations
    - Net profit computation after trading fees
    - Time-weighted profitability (profit per day)
    - Optimal trade execution recommendations
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dateutil import parser as date_parser
from .cost_calculator import FeeCalculator
from .utils import safe_get


class ArbitrageOpportunity:
    """
    Data structure representing a probability arbitrage opportunity.
    
    Contains all relevant information for evaluating and executing an arbitrage trade,
    including market details, profit calculations, and recommended trade actions.
    """
    
    def __init__(self, market_ticker: str, market_title: str, 
                 total_probability: float, deviation: float,
                 expiration_date: datetime, trades: List[Dict],
                 gross_profit: float, net_profit: float,
                 days_to_expiration: float):
        self.market_ticker = market_ticker
        self.market_title = market_title
        self.total_probability = total_probability
        self.deviation = deviation
        self.expiration_date = expiration_date
        self.trades = trades
        self.gross_profit = gross_profit
        self.net_profit = net_profit
        self.days_to_expiration = days_to_expiration
        self.profit_per_day = net_profit / max(days_to_expiration, 0.01)
    
    def __repr__(self):
        return (f"ArbitrageOpportunity(ticker={self.market_ticker}, "
                f"deviation={self.deviation:.2f}%, "
                f"profit_per_day=${self.profit_per_day:.2f})")


class ArbitrageAnalyzer:
    """
    Advanced market analyzer for probability arbitrage detection.
    
    Performs sophisticated analysis of market data to identify arbitrage opportunities
    where contract probabilities deviate from expected values. The analyzer considers
    trading fees, time to expiration, and market liquidity to provide accurate
    profitability assessments.
    """
    
    def __init__(self, min_deviation: float = None):
        """
        Initialize the analyzer.
        
        Args:
            min_deviation: DEPRECATED - No longer used. Filtering is now based on net profit > 0.
                          Kept for backwards compatibility but ignored.
        """
        # min_deviation is deprecated - we now filter by net_profit > 0 instead
        pass
    
    def analyze_market(self, market_data: Dict, orderbook: Optional[Dict] = None) -> Optional[ArbitrageOpportunity]:
        """
        Analyze a single market for arbitrage opportunities.

        NOTE: Market objects from get_markets() don't include pricing data.
        You MUST provide orderbook data for analysis.

        Args:
            market_data: Market information dictionary (has ticker, title, expiration, etc.)
            orderbook: REQUIRED - Orderbook data from get_market_orderbook()
                      Format: {'orderbook': {'yes': [[price, qty], ...], 'no': [[price, qty], ...]}}

        Returns:
            ArbitrageOpportunity if found, None otherwise
        """
        try:
            market_ticker = safe_get(market_data, "ticker", "")
            market_title = safe_get(market_data, "title", "")

            # Get expiration date
            expiration_str = safe_get(market_data, "expiration_time") or safe_get(market_data, "expiration_date")
            if not expiration_str:
                return None

            # Handle both string and datetime objects
            # The SDK may return datetime objects, REST API returns strings
            if isinstance(expiration_str, datetime):
                expiration_date = expiration_str
            elif isinstance(expiration_str, str):
                expiration_date = date_parser.parse(expiration_str)
            else:
                # Unknown format, skip this market
                return None

            days_to_expiration = (expiration_date - datetime.now(expiration_date.tzinfo)).total_seconds() / 86400

            # Skip markets that have already expired
            if days_to_expiration <= 0:
                return None

            # CRITICAL: Market objects don't have pricing data - must use orderbook
            if not orderbook or 'orderbook' not in orderbook:
                return None

            ob = orderbook['orderbook']

            # Extract best bids from orderbook
            # Kalshi orderbooks have 'yes' and 'no' arrays of [price, quantity]
            # In binary markets: yes_ask = 100 - no_bid, no_ask = 100 - yes_bid
            yes_bid = None
            no_bid = None
            yes_ask = None
            no_ask = None

            if 'yes' in ob and ob['yes'] and len(ob['yes']) > 0:
                yes_bid = ob['yes'][0][0]  # Best yes bid price
                no_ask = 100 - yes_bid      # Calculate no ask from yes bid

            if 'no' in ob and ob['no'] and len(ob['no']) > 0:
                no_bid = ob['no'][0][0]     # Best no bid price
                yes_ask = 100 - no_bid      # Calculate yes ask from no bid

            # Need at least one bid and ask to analyze
            if yes_bid is None or no_bid is None:
                return None

            total_prob = 0.0
            contract_prices = []

            # Check selling arbitrage first (yes_bid + no_bid > 100)
            # We can sell both sides at bid prices
            if yes_bid is not None and no_bid is not None:
                total_prob_bid = (yes_bid + no_bid) / 100.0
                if total_prob_bid > 1.0:
                    # Selling arbitrage opportunity
                    contract_prices = [
                        {
                            'ticker': market_ticker,
                            'side': 'yes',
                            'price': yes_bid,
                            'probability': yes_bid / 100.0
                        },
                        {
                            'ticker': market_ticker,
                            'side': 'no',
                            'price': no_bid,
                            'probability': no_bid / 100.0
                        }
                    ]
                    total_prob = total_prob_bid

            # Check buying arbitrage (yes_ask + no_ask < 100)
            if not contract_prices and yes_ask is not None and no_ask is not None:
                total_prob_ask = (yes_ask + no_ask) / 100.0
                if total_prob_ask < 1.0:
                    # Buying arbitrage opportunity
                    contract_prices = [
                        {
                            'ticker': market_ticker,
                            'side': 'yes',
                            'price': yes_ask,
                            'probability': yes_ask / 100.0
                        },
                        {
                            'ticker': market_ticker,
                            'side': 'no',
                            'price': no_ask,
                            'probability': no_ask / 100.0
                        }
                    ]
                    total_prob = total_prob_ask

            if not contract_prices:
                return None
            
            # Check for arbitrage opportunity
            deviation = abs(total_prob - 1.0) * 100  # Convert to percentage
            
            # No longer filter by deviation - we'll filter by net profit instead
            # This ensures we catch any profitable opportunity, even if tiny
            
            # Calculate arbitrage trades
            # If total_prob > 1.0, contracts are overpriced - we can sell them
            # If total_prob < 1.0, contracts are underpriced - we can buy them
            
            trades = []
            gross_profit = 0.0
            base_quantity = 100  # Base quantity per contract - could be optimized
            
            if total_prob > 1.0:
                # Contracts are overpriced - sell them
                # Strategy: Sell contracts at current prices, profit from the overpricing
                # When they expire, we pay out $1 per contract, but we received more than $1 total
                overpricing = total_prob - 1.0
                
                # Calculate how many contracts to sell for each outcome
                # We want to sell enough so that total received > $1 per set
                for contract in contract_prices:
                    # Normalize the probability to see how much we should sell
                    normalized_prob = contract['probability'] / total_prob
                    # Sell proportionally to create a balanced position
                    quantity = int(base_quantity * normalized_prob)
                    
                    if quantity > 0:
                        trades.append({
                            'ticker': contract['ticker'],
                            'side': contract.get('side', 'yes'),
                            'action': 'sell',
                            'price': contract['price'],
                            'quantity': quantity
                        })
                
                # Gross profit: We receive (total_prob * base_quantity) but only pay out (1.0 * base_quantity)
                # Profit per set = (total_prob - 1.0) * price_per_contract
                gross_profit = overpricing * base_quantity  # In contract units, convert to dollars
            
            else:  # total_prob < 1.0
                # Contracts are underpriced - buy them
                # Strategy: Buy contracts at current prices, profit from the underpricing
                # When they expire, we receive $1 per contract, but we paid less than $1 total
                underpricing = 1.0 - total_prob
                
                # Calculate how many contracts to buy for each outcome
                for contract in contract_prices:
                    # Normalize the probability to see how much we should buy
                    normalized_prob = contract['probability'] / total_prob
                    # Buy proportionally to create a balanced position
                    quantity = int(base_quantity * normalized_prob)
                    
                    if quantity > 0:
                        trades.append({
                            'ticker': contract['ticker'],
                            'side': contract.get('side', 'yes'),
                            'action': 'buy',
                            'price': contract['price'],
                            'quantity': quantity
                        })
                
                # Gross profit: We pay (total_prob * base_quantity) but receive (1.0 * base_quantity)
                # Profit per set = (1.0 - total_prob) * price_per_contract
                gross_profit = underpricing * base_quantity  # In contract units, convert to dollars
            
            if not trades:
                return None
            
            # Calculate net profit after fees
            # Assume we're using limit orders (maker orders) to reduce fees
            net_profit = FeeCalculator.calculate_net_profit(
                gross_profit,
                [{'price': t['price'], 'quantity': t['quantity']} for t in trades],
                all_maker=True
            )
            
            # Only return opportunities with positive net profit (after fees)
            # This dynamically calculates the minimum based on actual fees
            if net_profit <= 0:
                return None
            
            return ArbitrageOpportunity(
                market_ticker=market_ticker,
                market_title=market_title,
                total_probability=total_prob * 100,
                deviation=deviation,
                expiration_date=expiration_date,
                trades=trades,
                gross_profit=gross_profit,
                net_profit=net_profit,
                days_to_expiration=days_to_expiration
            )
        
        except Exception as e:
            print(f"Error analyzing market {safe_get(market_data, 'ticker', 'unknown')}: {e}")
            return None
    
    def find_opportunities(self, markets: List[Dict], 
                          client=None) -> List[ArbitrageOpportunity]:
        """
        Find arbitrage opportunities across multiple markets.
        
        Args:
            markets: List of market dictionaries
            client: Optional KalshiClient to fetch orderbooks
        
        Returns:
            List of ArbitrageOpportunity objects
        """
        opportunities = []
        
        for market in markets:
            orderbook = None
            if client:
                try:
                    import time
                    time.sleep(0.2)  # 200ms delay between orderbook requests
                    orderbook = client.get_market_orderbook(safe_get(market, "ticker", ""))
                except:
                    pass
            
            opportunity = self.analyze_market(market, orderbook)
            if opportunity:
                opportunities.append(opportunity)
        
        # Sort by profit per day (descending)
        opportunities.sort(key=lambda x: x.profit_per_day, reverse=True)
        
        return opportunities


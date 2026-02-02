"""
Capital Management Module

Dynamic trade sizing and risk management system for Kalshi trading bot.
Automatically fetches portfolio balance and calculates appropriate position sizes
based on available capital and risk parameters.

Key Features:
    - Automatic portfolio balance fetching from Kalshi API
    - Dynamic position sizing based on available capital
    - Risk management with configurable capital allocation percentages
    - Trade limit calculation to prevent overexposure
"""
from typing import Dict, Optional
from .market_api import KalshiClient


class CapitalManager:
    """
    Professional capital management system for automated trading.

    Manages portfolio balance tracking, dynamic position sizing, and risk limits
    to ensure safe trading within available capital constraints.
    """

    def __init__(self, client: KalshiClient,
                 max_capital_per_trade_pct: float = 0.05,
                 max_total_exposure_pct: float = 0.30,
                 min_balance_buffer: float = 100.0):
        """
        Initialize the capital manager.

        Args:
            client: KalshiClient instance for API calls
            max_capital_per_trade_pct: Maximum % of capital to risk per trade (default: 5%)
            max_total_exposure_pct: Maximum % of capital to have exposed at once (default: 30%)
            min_balance_buffer: Minimum balance buffer to maintain in dollars (default: $100)
        """
        self.client = client
        self.max_capital_per_trade_pct = max_capital_per_trade_pct
        self.max_total_exposure_pct = max_total_exposure_pct
        self.min_balance_buffer = min_balance_buffer

        # Cache for portfolio data
        self._cached_balance = None
        self._cache_timestamp = 0
        self._cache_ttl = 60  # Cache balance for 60 seconds

    def get_portfolio_balance(self, use_cache: bool = True) -> Optional[float]:
        """
        Fetch current portfolio balance from Kalshi API.

        Args:
            use_cache: Whether to use cached balance if available

        Returns:
            Available balance in dollars, None on error
        """
        import time

        # Return cached value if valid
        if use_cache and self._cached_balance is not None:
            if time.time() - self._cache_timestamp < self._cache_ttl:
                return self._cached_balance

        try:
            portfolio = self.client.get_portfolio()
            if not portfolio:
                print("Warning: Could not fetch portfolio data")
                return None

            # Extract balance - the exact field name may vary
            # Common field names: 'balance', 'available_balance', 'cash', 'available_cash'
            balance = None

            # Try different possible field names
            if isinstance(portfolio, dict):
                balance = (portfolio.get('balance') or
                          portfolio.get('available_balance') or
                          portfolio.get('cash') or
                          portfolio.get('available_cash'))

                # Some APIs return balance in cents
                if balance and balance > 10000:  # Likely in cents if > $100
                    balance = balance / 100.0

            if balance is not None:
                self._cached_balance = balance
                self._cache_timestamp = time.time()
                return balance
            else:
                print(f"Warning: Could not find balance field in portfolio data: {portfolio}")
                return None

        except Exception as e:
            print(f"Error fetching portfolio balance: {e}")
            return None

    def get_max_position_size(self, price_cents: int,
                             current_exposure: float = 0.0) -> int:
        """
        Calculate maximum position size based on available capital.

        Args:
            price_cents: Contract price in cents
            current_exposure: Current total exposure in dollars

        Returns:
            Maximum number of contracts to trade
        """
        balance = self.get_portfolio_balance()

        if balance is None:
            # Fallback to conservative default if we can't get balance
            print("Warning: Using default max position size (100 contracts)")
            return 100

        # Calculate available capital
        available_capital = balance - self.min_balance_buffer

        if available_capital <= 0:
            print(f"Warning: Insufficient balance (${balance:.2f}) - below minimum buffer")
            return 0

        # Calculate max capital for this trade
        max_trade_capital = available_capital * self.max_capital_per_trade_pct

        # Calculate max exposure limit
        max_total_exposure = balance * self.max_total_exposure_pct
        remaining_exposure = max_total_exposure - current_exposure

        if remaining_exposure <= 0:
            print(f"Warning: Maximum exposure reached (${current_exposure:.2f}/${max_total_exposure:.2f})")
            return 0

        # Use the more conservative limit
        max_capital = min(max_trade_capital, remaining_exposure)

        # Calculate max contracts based on price
        contract_price_dollars = price_cents / 100.0
        max_contracts = int(max_capital / contract_price_dollars)

        # Ensure at least 1 contract if we have any capital
        return max(1, max_contracts) if max_contracts > 0 else 0

    def can_afford_trade(self, price_cents: int, quantity: int,
                        current_exposure: float = 0.0) -> bool:
        """
        Check if we can afford a specific trade.

        Args:
            price_cents: Contract price in cents
            quantity: Number of contracts
            current_exposure: Current total exposure in dollars

        Returns:
            True if trade is affordable, False otherwise
        """
        balance = self.get_portfolio_balance()

        if balance is None:
            # Conservative: reject if we can't verify balance
            return False

        # Calculate trade cost
        trade_cost = (price_cents / 100.0) * quantity

        # Check if we have enough balance
        available_capital = balance - self.min_balance_buffer
        if trade_cost > available_capital:
            return False

        # Check if trade would exceed exposure limits
        max_total_exposure = balance * self.max_total_exposure_pct
        total_exposure_after = current_exposure + trade_cost

        if total_exposure_after > max_total_exposure:
            return False

        # Check if trade would exceed per-trade limit
        max_trade_capital = available_capital * self.max_capital_per_trade_pct
        if trade_cost > max_trade_capital:
            return False

        return True

    def get_capital_status(self) -> Dict:
        """
        Get comprehensive capital status report.

        Returns:
            Dictionary with balance, limits, and exposure information
        """
        balance = self.get_portfolio_balance()

        if balance is None:
            return {
                'balance': None,
                'available_capital': None,
                'max_trade_capital': None,
                'max_total_exposure': None,
                'error': 'Could not fetch portfolio balance'
            }

        available_capital = balance - self.min_balance_buffer
        max_trade_capital = available_capital * self.max_capital_per_trade_pct
        max_total_exposure = balance * self.max_total_exposure_pct

        return {
            'balance': balance,
            'available_capital': available_capital,
            'max_trade_capital': max_trade_capital,
            'max_total_exposure': max_total_exposure,
            'min_balance_buffer': self.min_balance_buffer,
            'max_capital_per_trade_pct': self.max_capital_per_trade_pct * 100,
            'max_total_exposure_pct': self.max_total_exposure_pct * 100
        }

    def display_capital_status(self):
        """Display formatted capital status."""
        status = self.get_capital_status()

        if status.get('error'):
            print(f"\n⚠️  {status['error']}")
            return

        print("\n" + "="*60)
        print("CAPITAL STATUS")
        print("="*60)
        print(f"Total Balance: ${status['balance']:.2f}")
        print(f"Available Capital: ${status['available_capital']:.2f}")
        print(f"Min Balance Buffer: ${status['min_balance_buffer']:.2f}")
        print(f"\nRisk Limits:")
        print(f"  Max Per Trade: ${status['max_trade_capital']:.2f} ({status['max_capital_per_trade_pct']:.1f}%)")
        print(f"  Max Total Exposure: ${status['max_total_exposure']:.2f} ({status['max_total_exposure_pct']:.1f}%)")
        print("="*60 + "\n")

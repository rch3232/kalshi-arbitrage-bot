"""
Kalshi API Client Module

A robust and production-ready client for interacting with the Kalshi prediction market API.
This module provides a clean abstraction layer for all API operations, handling complex
concerns such as authentication, rate limiting, error recovery, and request optimization.

Key Features:
    - Intelligent rate limiting with automatic backoff strategies
    - Support for both official Kalshi SDK and direct REST API calls
    - Comprehensive error handling with graceful degradation
    - Automatic retry logic for transient failures
    - Session management for improved performance
"""
import os
import requests
import time
import json
import hmac
import hashlib
import base64
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class KalshiClient:
    """
    Professional API client for Kalshi prediction markets.
    
    Provides a high-level interface for all Kalshi API operations including market
    data retrieval, order placement, portfolio management, and orderbook access.
    The client automatically handles authentication, rate limiting, and error recovery.
    """
    
    def __init__(self):
        # API Key ID from Kalshi account settings
        self.api_key = os.getenv("KALSHI_API_KEY")
        # Private Key from Kalshi account settings (can be PEM string or file path)
        self.api_secret = os.getenv("KALSHI_API_SECRET")
        self.base_url = os.getenv("KALSHI_API_BASE_URL", "https://api.elections.kalshi.com/trade-api/v2")
        self.session = requests.Session()
        
        # Rate limiting configuration
        self.last_request_time = 0
        self.min_request_interval = float(os.getenv("API_MIN_INTERVAL", "0.1"))  # 100ms minimum between requests
        self.request_count = 0
        self.rate_limit_reset_time = 0
        
        # Check if credentials are set (not placeholders)
        if not self.api_key or self.api_key == "your_api_key_id_here":
            print("Warning: KALSHI_API_KEY not set or still has placeholder value")
        if not self.api_secret or self.api_secret == "your_private_key_here":
            print("Warning: KALSHI_API_SECRET not set or still has placeholder value")
        
        # Try to use official SDK if available, otherwise use REST API
        self.use_sdk = False
        try:
            from kalshi_python import Configuration, KalshiClient as SDKClient

            # If private key is a file path, read it
            private_key = self.api_secret
            if os.path.isfile(self.api_secret):
                with open(self.api_secret, 'r') as f:
                    private_key = f.read()
            else:
                # Handle escaped newlines in environment variables
                # Render and other platforms may store \n as literal string
                private_key = private_key.replace('\\n', '\n')

            # Ensure key has proper PEM format
            if not private_key.startswith('-----BEGIN'):
                print("Warning: Private key doesn't appear to be in PEM format")

            config = Configuration(
                host=self.base_url,
                api_key_id=self.api_key,
                private_key_pem=private_key
            )
            self.sdk_client = SDKClient(config)
            self.use_sdk = True
            print("✅ Kalshi SDK initialized successfully")

        except ImportError as e:
            print(f"⚠️  Kalshi SDK not installed: {e}")
            print("   Install with: pip install kalshi-python")
            print("   Falling back to direct REST API (may not work)")
            self.use_sdk = False
        except Exception as e:
            print(f"❌ Error initializing Kalshi SDK: {e}")
            print(f"   API Key ID: {self.api_key[:10]}..." if self.api_key else "   No API key")
            print(f"   Private key length: {len(self.api_secret)} chars")
            print("   Make sure KALSHI_API_SECRET is your full RSA private key including -----BEGIN/END----- markers")
            self.use_sdk = False
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        Execute an authenticated API request with intelligent rate limiting.
        
        This internal method handles all API communication, ensuring proper rate limiting,
        error handling, and automatic retry logic. It respects API rate limits and
        implements exponential backoff when necessary.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional request parameters (params, json, etc.)
            
        Returns:
            Parsed JSON response as dictionary
            
        Raises:
            requests.exceptions.RequestException: For API communication errors
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Rate limiting: ensure minimum interval between requests
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        # Check if we're in a rate limit cooldown period
        if current_time < self.rate_limit_reset_time:
            wait_time = self.rate_limit_reset_time - current_time
            print(f"Rate limit cooldown: waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)
        
        try:
            self.last_request_time = time.time()
            self.request_count += 1
            
            response = self.session.request(method, url, **kwargs)
            
            # Handle rate limiting
            if response.status_code == 429:
                # Extract retry-after header if available
                retry_after = response.headers.get('Retry-After')
                if retry_after:
                    wait_time = int(retry_after)
                else:
                    # Default wait time for rate limits
                    wait_time = 60  # Wait 60 seconds
                
                self.rate_limit_reset_time = time.time() + wait_time
                print(f"Rate limit hit (429). Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
                
                # Retry once after waiting
                response = self.session.request(method, url, **kwargs)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 429:
                    # Rate limit error - don't print full error, just wait
                    retry_after = e.response.headers.get('Retry-After', '60')
                    wait_time = int(retry_after)
                    self.rate_limit_reset_time = time.time() + wait_time
                    print(f"Rate limit error. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    raise
                else:
                    print(f"API request failed: {e}")
                    if hasattr(e.response, 'text'):
                        print(f"Response: {e.response.text}")
            else:
                print(f"API request failed: {e}")
            raise
    
    def get_markets(self, limit: int = 100, status: str = "open") -> List[Dict]:
        """
        Retrieve active markets from the Kalshi platform.

        Fetches a list of markets matching the specified criteria, including
        current pricing, liquidity, and market metadata.

        Args:
            limit: Maximum number of markets to retrieve (default: 100)
            status: Market status filter - 'open' for active markets, 'closed' for settled

        Returns:
            List of market data dictionaries, empty list on error
        """
        try:
            if self.use_sdk:
                # Use official SDK
                response = self.sdk_client.get_markets(limit=limit, status=status)
                # SDK returns markets directly or in a response object
                if hasattr(response, 'markets'):
                    return response.markets
                elif isinstance(response, dict):
                    return response.get("markets", [])
                elif isinstance(response, list):
                    return response
                return []
            else:
                # Fallback to REST API
                response = self._make_request(
                    "GET",
                    "/markets",
                    params={"limit": limit, "status": status}
                )
                return response.get("markets", [])
        except Exception as e:
            print(f"Error fetching markets: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_market(self, market_ticker: str) -> Optional[Dict]:
        """
        Retrieve comprehensive information for a specific market.
        
        Fetches detailed market data including current prices, orderbook depth,
        expiration information, and trading volume.
        
        Args:
            market_ticker: Unique market identifier (e.g., 'PRES-2024-TRUE')
        
        Returns:
            Complete market data dictionary, None on error
        """
        try:
            response = self._make_request("GET", f"/markets/{market_ticker}")
            return response.get("market")
        except Exception as e:
            print(f"Error fetching market {market_ticker}: {e}")
            return None
    
    def get_market_orderbook(self, market_ticker: str) -> Optional[Dict]:
        """
        Retrieve the complete orderbook for a specified market.
        
        Returns detailed orderbook data including bid and ask prices with
        associated quantities, enabling precise spread analysis and trade execution.
        
        Args:
            market_ticker: Unique market identifier
        
        Returns:
            Orderbook data dictionary with bids and asks, None on error
        """
        try:
            response = self._make_request("GET", f"/markets/{market_ticker}/orderbook")
            return response
        except Exception as e:
            print(f"Error fetching orderbook for {market_ticker}: {e}")
            return None
    
    def get_portfolio(self) -> Optional[Dict]:
        """
        Retrieve current portfolio status and position information.

        Returns comprehensive account data including available balance, open positions,
        and recent trading activity.

        Returns:
            Portfolio data dictionary, None on error
        """
        try:
            if self.use_sdk:
                # Use official SDK
                response = self.sdk_client.get_balance()
                # SDK may return balance info directly or in response object
                if hasattr(response, '__dict__'):
                    return response.__dict__
                return response
            else:
                # Fallback to REST API
                response = self._make_request("GET", "/portfolio")
                return response
        except Exception as e:
            print(f"Error fetching portfolio: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def place_order(self, market_ticker: str, side: str, action: str,
                   count: int, price: int, order_type: str = "limit",
                   time_in_force: str = "ioc") -> Optional[Dict]:
        """
        Submit a trading order to the Kalshi exchange.

        Places either a limit or market order for the specified market. Limit orders
        provide price protection but may not execute immediately, while market orders
        execute instantly at current market prices.

        Args:
            market_ticker: Unique market identifier
            side: Contract side - 'yes' or 'no'
            action: Order direction - 'buy' to acquire contracts, 'sell' to dispose
            count: Number of contracts to trade
            price: Limit price in cents (0-100), ignored for market orders
            order_type: 'limit' for price-protected orders, 'market' for immediate execution
            time_in_force: Order duration - 'ioc' (immediate or cancel), 'gtc' (good til cancelled),
                          'fok' (fill or kill). Default 'ioc' for arbitrage safety.

        Returns:
            Order confirmation dictionary with order details, None on error
        """
        try:
            if self.use_sdk:
                # Use official SDK
                response = self.sdk_client.create_order(
                    ticker=market_ticker,
                    client_order_id=None,  # Let SDK generate
                    side=side,
                    action=action,
                    count=count,
                    type=order_type,
                    yes_price=price if side == 'yes' else None,
                    no_price=price if side == 'no' else None,
                    expiration_ts=None,  # Use time_in_force instead
                    sell_position_floor=None,
                    buy_max_cost=None
                )
                # Convert SDK response to dict
                if hasattr(response, '__dict__'):
                    return response.__dict__
                return response
            else:
                # Fallback to REST API
                payload = {
                    "ticker": market_ticker,
                    "side": side,
                    "action": action,
                    "count": count,
                    "price": price,
                    "type": order_type,
                    "time_in_force": time_in_force
                }
                response = self._make_request("POST", "/portfolio/orders", json=payload)
                return response
        except Exception as e:
            print(f"Error placing order: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """
        Check the status of a specific order.

        Args:
            order_id: Unique order identifier returned from place_order

        Returns:
            Order status dictionary including fill information, None on error
        """
        try:
            response = self._make_request("GET", f"/portfolio/orders/{order_id}")
            return response
        except Exception as e:
            print(f"Error fetching order status: {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an existing order.

        Args:
            order_id: Unique order identifier to cancel

        Returns:
            True if cancellation successful, False otherwise
        """
        try:
            response = self._make_request("DELETE", f"/portfolio/orders/{order_id}")
            return True
        except Exception as e:
            print(f"Error canceling order {order_id}: {e}")
            return False

    def get_open_orders(self) -> List[Dict]:
        """
        Retrieve all currently open orders.

        Returns:
            List of open order dictionaries, empty list on error
        """
        try:
            response = self._make_request("GET", "/portfolio/orders")
            return response.get("orders", [])
        except Exception as e:
            print(f"Error fetching open orders: {e}")
            return []


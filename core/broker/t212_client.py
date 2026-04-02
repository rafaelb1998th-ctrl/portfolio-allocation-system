"""
Trading 212 Client with API and Automation backends
"""

import os
import time
import json
import requests  # pyright: ignore[reportMissingModuleSource]
from typing import List, Dict, Optional, Literal, Any, TypedDict
from abc import ABC, abstractmethod
import logging

# Type definitions
Side = Literal["buy", "sell"]
OrderType = Literal["market", "limit"]

class Quote(TypedDict):
    symbol: str
    bid: float
    ask: float
    last: float
    ts: float

class Position(TypedDict):
    symbol: str
    qty: float
    avg_price: float
    market_value: float
    currency: str

class OrderResponse(TypedDict):
    id: str
    status: Literal["accepted", "rejected", "filled", "partial", "pending"]
    filled_qty: float
    avg_fill_price: Optional[float]
    message: Optional[str]

class BrokerClient(ABC):
    """Abstract base class for broker clients."""
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the broker."""
        pass
    
    @abstractmethod
    def get_quotes(self, symbols: List[str]) -> List[Quote]:
        """Get quotes for symbols."""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Position]:
        """Get current positions."""
        pass
    
    @abstractmethod
    def get_cash(self, currency: str = "GBP") -> float:
        """Get available cash in specified currency."""
        pass
    
    @abstractmethod
    def place_order(self, symbol: str, side: Side, qty: float,
                    order_type: OrderType = "market",
                    limit_price: Optional[float] = None) -> OrderResponse:
        """Place an order."""
        pass

logger = logging.getLogger(__name__)

class _T212APIBackend:
    """Trading 212 API backend for portfolio/quotes/orders."""
    
    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://live.trading212.com/api/v0"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.session = requests.Session()
        # Use Basic Authentication as per Trading 212 API docs
        import base64
        credentials_string = f"{api_key}:{api_secret}"
        encoded_credentials = base64.b64encode(credentials_string.encode('utf-8')).decode('utf-8')
        
        self.session.headers.update({
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/json',
            'User-Agent': 'HEDGE/1.0'
        })
        self.connected = False
        self._instruments_cache = None  # Cache for instruments list
        self._instruments_file = None  # Path to exported instruments file

    def _request(self, method: str, path: str, *, json_payload=None, params=None, max_retries: int = 3):
        """Make a rate-limit-aware request and return the response.

        Implements Trading 212 rate limit guidance by inspecting:
        - x-ratelimit-remaining
        - x-ratelimit-reset (unix ts)
        - Retry-After (seconds) on 429
        """
        url = f"{self.base_url}{path}"
        attempt = 0
        while True:
            attempt += 1
            resp = self.session.request(method, url, json=json_payload, params=params)

            # If OK or client/server error not related to rate limiting, return immediately
            if resp.status_code != 429:
                # Proactive pacing based on remaining
                try:
                    remaining = int(resp.headers.get('x-ratelimit-remaining', '0'))
                    reset_ts = int(resp.headers.get('x-ratelimit-reset', '0'))
                except ValueError:
                    remaining, reset_ts = 0, 0

                if remaining <= 1 and reset_ts > 0:
                    import time as _time, random as _random
                    sleep_s = max(0, reset_ts - int(_time.time())) + _random.uniform(0.05, 0.25)
                    if sleep_s > 0:
                        _time.sleep(min(sleep_s, 2.0))  # be polite but don't over-sleep
                return resp

            # 429 Too Many Requests → back off using headers
            import time as _time, random as _random
            retry_after_hdr = resp.headers.get('Retry-After')
            reset_hdr = resp.headers.get('x-ratelimit-reset')

            backoff_s = 1.0  # default small backoff
            if retry_after_hdr:
                try:
                    backoff_s = float(retry_after_hdr)
                except ValueError:
                    pass
            elif reset_hdr:
                try:
                    reset_ts = int(reset_hdr)
                    backoff_s = max(0, reset_ts - int(_time.time()))
                except ValueError:
                    pass

            # Add jitter
            backoff_s += _random.uniform(0.1, 0.4)

            if attempt >= max_retries:
                return resp

            _time.sleep(min(backoff_s, 5.0))
    
    def connect(self) -> bool:
        """Connect to T212 API."""
        try:
            # Try cash endpoint first (might have different rate limits)
            response = self._request("GET", "/equity/account/cash")
            if response.status_code == 200:
                self.connected = True
                logger.info("✅ T212 API connected successfully")
                return True
            elif response.status_code == 429:
                # Rate limit means auth is working, connection is valid
                self.connected = True
                logger.warning("⚠️ T212 API connected but rate limited - will retry on next request")
                return True
            else:
                logger.error(f"❌ T212 API connection failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ T212 API connection error: {e}")
            return False
    
    def get_quotes(self, symbols: List[str]) -> List[Quote]:
        """Get quotes for symbols from T212 API using the /equity/quotes endpoint.
        
        This endpoint accepts multiple tickers as query parameters and returns
        the latest bid/ask/last prices for all requested instruments.
        """
        if not symbols:
            return []
        
        try:
            # Map symbols to T212 instruments
            tickers = []
            symbol_to_ticker = {}
            ticker_to_symbol = {}
            
            for symbol in symbols:
                instrument = self._get_instrument(symbol)
                if instrument:
                    tickers.append(instrument)
                    symbol_to_ticker[symbol] = instrument
                    ticker_to_symbol[instrument] = symbol
                else:
                    logger.warning(f"Could not find T212 instrument for {symbol}")
            
            if not tickers:
                logger.warning("No valid T212 instruments found for symbols")
                return []
            
            # Use the correct quotes endpoint: /equity/quotes?tickers=SPY,GLD,XLU
            # This endpoint accepts multiple tickers and returns all quotes in one call
            tickers_str = ','.join(tickers)
            print(f"    🔍 Fetching prices for {len(tickers)} instruments from T212 API...")
            response = self._request("GET", f"/equity/quotes?tickers={tickers_str}")
            
            quotes = []
            
            if response.status_code == 200:
                data = response.json()
                # Response is a list of quote objects
                if isinstance(data, list):
                    for quote_data in data:
                        ticker = quote_data.get('ticker', '')
                        symbol = ticker_to_symbol.get(ticker, ticker)
                        
                        last_price = float(quote_data.get('last', 0) or 0)
                        bid_price = float(quote_data.get('bid', 0) or 0)
                        ask_price = float(quote_data.get('ask', 0) or 0)
                        
                        # Use last price if available, otherwise use mid of bid/ask
                        if last_price > 0:
                            price = last_price
                        elif ask_price > 0 and bid_price > 0:
                            price = (bid_price + ask_price) / 2.0
                        elif ask_price > 0:
                            price = ask_price
                        elif bid_price > 0:
                            price = bid_price
                        else:
                            logger.warning(f"No price data for {symbol} ({ticker})")
                            continue
                        
                        quote = Quote(
                            symbol=symbol,
                            bid=bid_price,
                            ask=ask_price,
                            last=price,
                            ts=time.time()
                        )
                        quotes.append(quote)
                        logger.info(f"✅ Got price for {symbol} ({ticker}): ${price:.2f}")
                        print(f"    ✅ {symbol} ({ticker}) = ${price:.2f}")
                else:
                    logger.warning(f"Unexpected response format: {type(data)}")
            
            elif response.status_code == 404:
                logger.warning(f"Quotes endpoint not found (404) - may not be available in your API plan")
                print(f"    ⚠️ Quotes endpoint returned 404 - may not be available")
            else:
                logger.warning(f"Failed to get quotes: status {response.status_code}")
                print(f"    ❌ Failed to get quotes: status {response.status_code}")
                if response.text:
                    print(f"       Response: {response.text[:200]}")
            
            if quotes:
                logger.info(f"✅ Successfully retrieved {len(quotes)}/{len(symbols)} quotes from T212")
                print(f"    ✅ Got {len(quotes)} real prices from T212")
            else:
                logger.warning(f"⚠️ No quotes retrieved from T212 for {len(symbols)} symbols")
                print(f"    ⚠️ No quotes retrieved - will try alternative methods")
            
            return quotes
        except Exception as e:
            logger.error(f"Error getting quotes: {e}")
            print(f"    ❌ Error getting quotes: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def get_positions(self) -> List[Position]:
        """Get current positions."""
        try:
            response = self._request("GET", "/equity/portfolio")
            if response.status_code != 200:
                return []
            
            data = response.json()
            positions = []
            
            # Handle both list and dict responses
            positions_data = data if isinstance(data, list) else data.get('positions', [])
            
            # Log raw response for debugging
            if not positions_data:
                logger.warning(f"No positions found in API response. Response keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
                logger.warning(f"Full response: {data}")
            
            for pos in positions_data:
                ticker = pos.get('ticker', '')
                quantity = float(pos.get('quantity', 0))
                avg_price = float(pos.get('averagePrice', 0))
                current_price = float(pos.get('currentPrice', 0))  # API provides currentPrice directly!
                market_value = float(pos.get('marketValue', 0))
                
                # If marketValue not provided, calculate from currentPrice * quantity
                if market_value == 0 and current_price > 0 and quantity > 0:
                    market_value = current_price * quantity
                
                # Log position for debugging
                if quantity > 0:
                    logger.info(f"Found position: {ticker} - {quantity} shares @ ${current_price:.2f} = ${market_value:.2f}")
                    print(f"    📊 Found position: {ticker} - {quantity} shares @ ${current_price:.2f} = ${market_value:.2f}")
                elif ticker:
                    logger.debug(f"Position with zero quantity: {ticker}")
                
                position = Position(
                    symbol=ticker,
                    qty=quantity,
                    avg_price=avg_price,
                    market_value=market_value,
                    currency=pos.get('currency', 'GBP')
                )
                # Add current_price to the dict (Position is TypedDict)
                position['current_price'] = current_price
                positions.append(position)
            
            if not positions:
                logger.warning("No positions retrieved from T212 API")
                print("    ⚠️ No positions found in portfolio")
            
            return positions
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_cash(self, currency: str = "GBP") -> float:
        """Get available cash from account.
        
        Rate Limit: 1 request per 2 seconds
        
        Returns:
            Available cash balance in the account's base currency
        """
        try:
            logger.info("Fetching account cash balance from Trading 212 API...")
            logger.info("⚠️  Rate limit: 1 request per 2 seconds")
            
            response = self._request("GET", "/equity/account/cash")
            if response.status_code != 200:
                logger.error(f"Failed to get cash: status {response.status_code}")
                if response.text:
                    logger.error(f"   Response: {response.text[:200]}")
                return 0.0
            
            data = response.json()
            # The API returns a single cash object (not currency-specific)
            # Structure: {"free": 19.79, "total": 249.66, "ppl": -0.32, "result": -148.76, "invested": 9.58, "pieCash": 0.0, "blocked": 220.62}
            # The currency is the account's base currency (likely GBP for UK accounts)
            # For US ETFs, Trading 212 will automatically convert GBP to USD at market rate
            
            if isinstance(data, dict):
                # Get available cash (free = available for trading)
                available = data.get('free', data.get('available', 0.0))
                total_cash = data.get('total', available)
                invested = data.get('invested', 0.0)
                result = data.get('result', 0.0)  # P&L
                blocked = data.get('blocked', 0.0)
                
                logger.info(f"✅ Account cash breakdown:")
                logger.info(f"   Available (free): £{float(available):.2f}")
                logger.info(f"   Total cash: £{float(total_cash):.2f}")
                logger.info(f"   Blocked: £{float(blocked):.2f}")
                logger.info(f"   Invested: £{float(invested):.2f}")
                logger.info(f"   P&L (result): £{float(result):.2f}")
                logger.info(f"   ℹ️  Note: API returns account base currency. T212 will auto-convert for USD orders if needed.")
                
                return float(available)
            
            logger.error(f"❌ Could not extract cash balance from response: {data}")
            return 0.0
        except Exception as e:
            logger.error(f"Error getting cash: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return 0.0
    
    def get_account_summary(self) -> Dict[str, float]:
        """Get full account summary including cash, invested, and NAV.
        
        Rate Limit: 1 request per 2 seconds
        
        Returns:
            Dict with keys: free, total, invested, result, blocked, nav
        """
        try:
            response = self._request("GET", "/equity/account/cash")
            if response.status_code != 200:
                logger.error(f"Failed to get account summary: status {response.status_code}")
                return {}
            
            data = response.json()
            if isinstance(data, dict):
                free = float(data.get('free', 0.0))
                total = float(data.get('total', 0.0))
                invested = float(data.get('invested', 0.0))
                result = float(data.get('result', 0.0))
                blocked = float(data.get('blocked', 0.0))
                
                # NAV should be calculated from actual position market values
                # The 'invested' field may be cost basis, not market value
                # We'll calculate NAV from positions separately, but include it here for reference
                # Actual NAV = total cash + sum of position market values (calculated separately)
                nav = total + invested  # This is approximate; actual NAV should use position market values
                
                return {
                    'free': free,
                    'total': total,
                    'invested': invested,
                    'result': result,
                    'blocked': blocked,
                    'nav': nav
                }
            
            return {}
        except Exception as e:
            logger.error(f"Error getting account summary: {e}")
            return {}
    
    def get_instruments(self, use_cache: bool = True, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch all instruments that your account has access to.
        
        Rate Limit: 1 request per 50 seconds
        
        Args:
            use_cache: If True, return cached instruments if available
            force_refresh: If True, force a fresh API call even if cache exists
        
        Returns:
            List of instrument dictionaries containing ticker, type, isin, etc.
        """
        # Return cached instruments if available and not forcing refresh
        if use_cache and not force_refresh and hasattr(self, '_instruments_list') and self._instruments_list:
            logger.debug(f"Returning cached instruments list ({len(self._instruments_list)} instruments)")
            return self._instruments_list
        
        try:
            logger.info("Fetching instruments from Trading 212 API...")
            logger.info("⚠️  Rate limit: 1 request per 50 seconds")
            
            response = self._request("GET", "/equity/metadata/instruments")
            
            if response.status_code == 200:
                instruments = response.json()
                # Handle both list and dict responses
                if isinstance(instruments, list):
                    self._instruments_list = instruments
                elif isinstance(instruments, dict):
                    # Some APIs return dict with 'data' or 'instruments' key
                    self._instruments_list = instruments.get('data', instruments.get('instruments', []))
                else:
                    self._instruments_list = []
                
                logger.info(f"✅ Successfully fetched {len(self._instruments_list)} instruments")
                return self._instruments_list
            elif response.status_code == 429:
                logger.warning("⚠️  Rate limited (429) - instruments endpoint has strict rate limit (1 per 50s)")
                logger.warning("   Consider using cached instruments or waiting before retry")
                # Return cached instruments if available, even if stale
                if hasattr(self, '_instruments_list') and self._instruments_list:
                    logger.warning("   Returning cached instruments")
                    return self._instruments_list
                return []
            else:
                logger.error(f"❌ Failed to fetch instruments: status {response.status_code}")
                if response.text:
                    logger.error(f"   Response: {response.text[:200]}")
                # Return cached instruments if available
                if hasattr(self, '_instruments_list') and self._instruments_list:
                    logger.warning("   Returning cached instruments")
                    return self._instruments_list
                return []
        except Exception as e:
            logger.error(f"Error fetching instruments: {e}")
            # Return cached instruments if available
            if hasattr(self, '_instruments_list') and self._instruments_list:
                logger.warning("   Returning cached instruments")
                return self._instruments_list
            return []
    
    def get_market_prices_direct(self, tickers: List[str]) -> Dict[str, float]:
        """Get market prices directly using the /equity/quotes endpoint.
        
        This is a faster method that fetches multiple prices in one API call.
        Uses the ticker format directly (e.g., 'SPY', 'GLD' or 'SPY_US_ETF').
        
        Args:
            tickers: List of ticker symbols (can be short names like 'SPY' or full T212 format)
        
        Returns:
            Dictionary mapping ticker to price (last price)
        
        Note:
            This endpoint may not be available in all API plans. Returns empty dict
            if endpoint returns 404.
        """
        if not tickers:
            return {}
        
        try:
            # Join tickers as comma-separated query parameter
            tickers_str = ','.join(tickers)
            response = self._request("GET", f"/equity/quotes?tickers={tickers_str}")
            
            prices = {}
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    for quote in data:
                        ticker = quote.get('ticker', '')
                        last_price = float(quote.get('last', 0) or 0)
                        if last_price > 0:
                            prices[ticker] = last_price
                        else:
                            # Fallback to bid/ask mid if no last price
                            bid = float(quote.get('bid', 0) or 0)
                            ask = float(quote.get('ask', 0) or 0)
                            if bid > 0 and ask > 0:
                                prices[ticker] = (bid + ask) / 2.0
                            elif ask > 0:
                                prices[ticker] = ask
                            elif bid > 0:
                                prices[ticker] = bid
                    
                    logger.info(f"✅ Got {len(prices)} prices from /equity/quotes endpoint")
                else:
                    logger.warning(f"Unexpected response format from /equity/quotes: {type(data)}")
            elif response.status_code == 404:
                logger.debug("Quotes endpoint not available (404) - may not be in your API plan")
            else:
                logger.warning(f"Failed to get quotes: status {response.status_code}")
            
            return prices
        except Exception as e:
            logger.error(f"Error getting market prices directly: {e}")
            return {}
    
    def place_order(self, symbol: str, side: Side, qty: float,
                    order_type: OrderType = "market",
                    limit_price: Optional[float] = None) -> OrderResponse:
        """Place an order."""
        try:
            # Get instrument code from T212 metadata API
            instrument = self._get_instrument(symbol)
            if not instrument:
                return OrderResponse(
                    id="",
                    status="rejected",
                    filled_qty=0.0,
                    avg_fill_price=None,
                    message=f"Unknown symbol: {symbol}"
                )
            
            # Skip quote check to avoid rate limits - just try placing order
            # Quotes aren't always available but trading might still work
            
            # Use the instrument code we got from _get_instrument
            # It should already be in the correct format (e.g., "SPY_US_ETF")
            instrument_code = instrument
            
            # Trading 212 API expects: ticker and quantity
            # For sells, quantity should be negative
            quantity = qty if side == "buy" else -abs(qty)
            
            # Market order format based on Trading 212 API docs
            if order_type == "limit" and limit_price:
                endpoint = "/equity/orders/limit"
                order_data = {
                    "ticker": instrument_code,
                    "quantity": quantity,
                    "limitPrice": limit_price
                }
            elif order_type == "market":
                endpoint = "/equity/orders/market"
                order_data = {
                    "ticker": instrument_code,
                    "quantity": quantity
                }
            else:
                endpoint = "/equity/orders/market"
                order_data = {
                    "ticker": instrument_code,
                    "quantity": quantity
                }

            logger.debug(f"Placing order: {order_data}")
            response = self._request("POST", endpoint, json_payload=order_data)
            
            if response.status_code == 200:
                data = response.json()
                return OrderResponse(
                    id=str(data.get('id', '')),
                    status="accepted",
                    filled_qty=0.0,
                    avg_fill_price=None,
                    message="Order placed successfully"
                )
            else:
                # Log full error details for debugging
                error_text = response.text
                
                # Check if response is HTML (Cloudflare challenge or access denied)
                if response.headers.get('content-type', '').startswith('text/html') or '<html' in error_text.lower():
                    error_detail = "API access denied - Cloudflare protection or invalid endpoint"
                    logger.error(f"Order rejected for {symbol}: HTML response received (likely Cloudflare protection)")
                    logger.debug(f"Response status: {response.status_code}, Content-Type: {response.headers.get('content-type')}")
                    
                    # Extract useful info from HTML if possible
                    if 'Access Denied' in error_text:
                        error_detail = "API Access Denied - Check API credentials and endpoint permissions"
                    elif 'Cloudflare' in error_text or 'cf-challenge' in error_text.lower():
                        error_detail = "Cloudflare protection blocking API request - May need to whitelist IP or use automation mode"
                    else:
                        error_detail = f"HTML response received (status {response.status_code}) - API may be unavailable"
                else:
                    try:
                        error_json = response.json()
                        error_detail = error_json.get('detail', error_json.get('message', error_text[:200]))
                        error_type = error_json.get('type', '')
                        
                        # Check for specific errors that we can handle
                        if 'not-available-for-dealer' in error_detail.lower() or 'not available for your dealer' in error_detail.lower():
                            error_detail = f"Instrument {instrument_code} not available for your account type. Try using automation mode or check if symbol is tradeable on your account."
                            logger.warning(f"Dealer availability issue for {symbol} ({instrument_code}) - consider using automation mode")
                        elif 'api-errors' in error_detail:
                            # Extract the actual error from the path
                            error_path = error_detail
                            if '/' in error_path:
                                actual_error = error_path.split('/')[-1]
                                error_detail = f"API error: {actual_error.replace('-', ' ').title()}"
                        
                        logger.error(f"Order rejected for {symbol} ({instrument_code}): {error_type} - {error_detail}")
                    except:
                        # Not JSON, but also not HTML - return first 200 chars
                        error_detail = error_text[:200] if error_text else f"Unknown error (status {response.status_code})"
                
                return OrderResponse(
                    id="",
                    status="rejected",
                    filled_qty=0.0,
                    avg_fill_price=None,
                    message=f"Order rejected: {error_detail}"
                )
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return OrderResponse(
                id="",
                status="rejected",
                filled_qty=0.0,
                avg_fill_price=None,
                message=f"Order error: {e}"
            )
    
    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """Get all pending orders (active orders not yet filled, cancelled, or expired).
        
        Rate Limit: 1 request per 5 seconds
        
        Returns:
            List of order dictionaries containing order details
        """
        try:
            logger.info("Fetching pending orders from Trading 212 API...")
            logger.info("⚠️  Rate limit: 1 request per 5 seconds")
            
            response = self._request("GET", "/equity/orders")
            
            if response.status_code == 200:
                orders = response.json()
                # Handle both list and dict responses
                if isinstance(orders, list):
                    logger.info(f"✅ Successfully fetched {len(orders)} pending orders")
                    return orders
                elif isinstance(orders, dict):
                    # Some APIs return dict with 'data' or 'orders' key
                    orders_list = orders.get('data', orders.get('orders', []))
                    logger.info(f"✅ Successfully fetched {len(orders_list)} pending orders")
                    return orders_list
                else:
                    logger.warning(f"Unexpected response format: {type(orders)}")
                    return []
            elif response.status_code == 429:
                logger.warning("⚠️  Rate limited (429) - orders endpoint has rate limit (1 per 5s)")
                logger.warning("   Consider waiting before retry")
                return []
            else:
                logger.error(f"❌ Failed to fetch pending orders: status {response.status_code}")
                if response.text:
                    logger.error(f"   Response: {response.text[:200]}")
                return []
        except Exception as e:
            logger.error(f"Error fetching pending orders: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def cancel_order(self, order_id: int) -> Dict[str, Any]:
        """Cancel a pending order by its unique ID.
        
        Rate Limit: 50 requests per 1 minute
        
        Args:
            order_id: The unique identifier of the order to cancel
        
        Returns:
            Dictionary with cancellation result
        """
        try:
            logger.info(f"Cancelling order {order_id}...")
            
            response = self._request("DELETE", f"/equity/orders/{order_id}")
            
            if response.status_code == 200:
                # DELETE endpoint may return empty body or JSON
                try:
                    data = response.json() if response.text else {}
                except:
                    data = {}
                logger.info(f"✅ Successfully cancelled order {order_id}")
                return {
                    "success": True,
                    "order_id": order_id,
                    "message": "Order cancelled successfully",
                    "data": data
                }
            elif response.status_code == 404:
                logger.warning(f"⚠️  Order {order_id} not found (may already be filled or cancelled)")
                return {
                    "success": False,
                    "order_id": order_id,
                    "message": "Order not found (may already be filled or cancelled)"
                }
            elif response.status_code == 429:
                logger.warning("⚠️  Rate limited (429) - orders endpoint has rate limit (50 per 1 min)")
                return {
                    "success": False,
                    "order_id": order_id,
                    "message": "Rate limited - try again later"
                }
            else:
                logger.error(f"❌ Failed to cancel order {order_id}: status {response.status_code}")
                if response.text:
                    logger.error(f"   Response: {response.text[:200]}")
                return {
                    "success": False,
                    "order_id": order_id,
                    "message": f"Failed to cancel order: status {response.status_code}",
                    "error": response.text[:200] if response.text else None
                }
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return {
                "success": False,
                "order_id": order_id,
                "message": f"Error cancelling order: {e}"
            }
    
    def _get_instrument(self, symbol: str) -> Optional[str]:
        """Map symbol to T212 instrument code by searching instruments list."""
        # First try cached lookup
        if not hasattr(self, '_instrument_cache'):
            self._instrument_cache = {}
        
        if symbol in self._instrument_cache:
            return self._instrument_cache[symbol]
        
        # Load instruments from exported file FIRST (avoids rate limits)
        if not hasattr(self, '_instruments_list') or self._instruments_list is None or len(self._instruments_list) == 0:
            import json
            import os
            import glob
            
            # Try to find the latest exported instruments file
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            out_dir = os.path.join(project_root, "out")
            if os.path.exists(out_dir):
                json_files = glob.glob(os.path.join(out_dir, "t212_instruments_*.json"))
                if json_files:
                    latest_file = max(json_files, key=os.path.getctime)
                    try:
                        with open(latest_file, 'r') as f:
                            self._instruments_list = json.load(f)
                        logger.info(f"Loaded {len(self._instruments_list)} instruments from {latest_file}")
                    except Exception as e:
                        logger.warning(f"Could not load instruments from file: {e}")
                        self._instruments_list = []
                else:
                    self._instruments_list = []
            else:
                self._instruments_list = []
            
            # If file load failed, try API as fallback (but this is rate-limited)
            if not self._instruments_list:
                try:
                    logger.debug(f"Loading instruments list from API for symbol {symbol}...")
                    # Use the new get_instruments() method which handles caching and rate limits
                    self._instruments_list = self.get_instruments(use_cache=True, force_refresh=False)
                    if self._instruments_list:
                        logger.debug(f"Loaded {len(self._instruments_list)} instruments from API")
                    else:
                        logger.warning("Failed to load instruments from API - may be rate limited")
                except Exception as e:
                    logger.warning(f"Error loading instruments list from API: {e}")
                    self._instruments_list = []
        
        instruments = self._instruments_list
        if not instruments or len(instruments) == 0:
            logger.warning(f"Instruments list is empty - cannot resolve {symbol}")
            return None
        
        # Search cached instruments list for the correct ticker format
        try:
            if instruments:
                    # Search for instrument matching our symbol
                    # Priority: 1) ISIN match (most reliable), 2) Exact shortName, 3) US ticker format
                    
                    # First pass: try symbol mapping ISIN to find exact match
                    try:
                        import json as json_module
                        from pathlib import Path as _Path
                        _map_path = _Path(__file__).resolve().parents[2] / "brokers" / "symbol_map.json"
                        with _map_path.open("r", encoding="utf-8") as f:
                            mapping = json_module.load(f)
                            target_isin = mapping.get(symbol, {}).get('isin')
                            
                            if target_isin:
                                for inst in instruments:
                                    isin = inst.get('isin', '')
                                    if isin == target_isin:
                                        ticker = inst.get('ticker', '')
                                        self._instrument_cache[symbol] = ticker
                                        logger.debug(f"Found instrument for {symbol} by ISIN {target_isin}: {ticker}")
                                        return ticker
                    except Exception as e:
                        logger.debug(f"ISIN lookup failed for {symbol}: {e}")
                    
                    # Second pass: exact shortName match (reliable for stocks)
                    for inst in instruments:
                        short_name = inst.get('shortName', '')
                        if short_name == symbol:
                            ticker = inst.get('ticker', '')
                            self._instrument_cache[symbol] = ticker
                            logger.debug(f"Found instrument for {symbol} by shortName: {ticker}")
                            return ticker
                    
                    # Third pass: US ticker format (SYMBOL_US_EQ or SYMBOL_US_ETF)
                    for inst in instruments:
                        ticker = inst.get('ticker', '')
                        # Match exact format: SYMBOL_US_EQ or SYMBOL_US_ETF
                        if ticker == f"{symbol}_US_EQ" or ticker == f"{symbol}_US_ETF":
                            self._instrument_cache[symbol] = ticker
                            logger.debug(f"Found instrument for {symbol} by US ticker: {ticker}")
                            return ticker
                    
                    # Fourth pass: _EQ format (European/UK ETFs like IVV_EQ, EQQQl_EQ)
                    for inst in instruments:
                        ticker = inst.get('ticker', '')
                        # Match _EQ format that starts with symbol
                        if ticker.startswith(f"{symbol}") and ticker.endswith("_EQ"):
                            self._instrument_cache[symbol] = ticker
                            logger.debug(f"Found instrument for {symbol} by _EQ ticker: {ticker}")
                            return ticker
        except Exception as e:
            logger.warning(f"Error searching instruments list: {e}")
        
        # Fallback: try symbol mapping file
        try:
            from pathlib import Path as _Path
            _map_path = _Path(__file__).resolve().parents[2] / "brokers" / "symbol_map.json"
            with _map_path.open("r", encoding="utf-8") as f:
                mapping = json.load(f)
                mapped = mapping.get(symbol, {}).get('t212')
                if mapped:
                    # Check if mapped ticker exists in instruments list
                    for inst in instruments:
                        if inst.get('ticker') == mapped:
                            self._instrument_cache[symbol] = mapped
                            logger.debug(f"Found instrument for {symbol} via mapping: {mapped}")
                            return mapped
        except:
            pass
        
        # Last fallback: try to find ANY matching instrument
        # Don't create non-existent tickers - only return if found
        logger.warning(f"Instrument {symbol} not found - no matching ticker in instruments list")
        return None

class _T212AutomationBackend:
    """Trading 212 automation backend using Playwright for scraping."""
    
    def __init__(self, profile_dir: str = "./t212_profile"):
        self.profile_dir = profile_dir
        self.browser = None
        self.page = None
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to T212 via automation."""
        try:
            from playwright.sync_api import sync_playwright  # pyright: ignore[reportMissingImports]
            
            # Start playwright and keep it alive
            if not hasattr(self, '_playwright') or self._playwright is None:
                self._playwright = sync_playwright().start()
            
            # Launch persistent context (keeps browser alive)
            if self.browser is None:
                self.browser = self._playwright.chromium.launch_persistent_context(
                    user_data_dir=self.profile_dir,
                    headless=False,  # Set to True for headless mode
                    viewport={'width': 1280, 'height': 720}
                )
            
            # Get or create page
            if self.page is None or self.page.is_closed():
                pages = self.browser.pages
                if len(pages) > 0:
                    self.page = pages[0]
                else:
                    self.page = self.browser.new_page()
            
            # Navigate to Trading 212
            try:
                self.page.goto("https://live.trading212.com", wait_until="domcontentloaded", timeout=30000)
            except Exception as nav_error:
                logger.warning(f"Navigation warning: {nav_error} - continuing anyway")
            
            # Wait for page to load
            time.sleep(3)
            
            # Check if we're on the trading page or login page
            current_url = self.page.url
            if "trading212.com" in current_url:
                self.connected = True
                logger.info("✅ T212 automation connected successfully")
                logger.info(f"Current URL: {current_url}")
                return True
            else:
                logger.warning(f"Unexpected URL: {current_url} - but connected anyway")
                self.connected = True
                return True
                
        except Exception as e:
            logger.error(f"❌ T212 automation connection error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def get_quotes(self, symbols: List[str]) -> List[Quote]:
        """Get quotes via automation."""
        try:
            quotes = []
            for symbol in symbols:
                # Navigate to symbol page or use search
                self.page.goto(f"https://live.trading212.com/en/instruments/{symbol}")
                time.sleep(2)
                
                # Extract price data from page
                try:
                    bid = float(self.page.locator('[data-testid="bid-price"]').text_content() or "0")
                    ask = float(self.page.locator('[data-testid="ask-price"]').text_content() or "0")
                    last = float(self.page.locator('[data-testid="last-price"]').text_content() or "0")
                    
                    quote = Quote(
                        symbol=symbol,
                        bid=bid,
                        ask=ask,
                        last=last,
                        ts=time.time()
                    )
                    quotes.append(quote)
                except:
                    # Fallback to last price only
                    try:
                        last = float(self.page.locator('[data-testid="price"]').text_content() or "0")
                        quote = Quote(
                            symbol=symbol,
                            bid=last,
                            ask=last,
                            last=last,
                            ts=time.time()
                        )
                        quotes.append(quote)
                    except:
                        continue
            
            return quotes
        except Exception as e:
            logger.error(f"Error getting quotes via automation: {e}")
            return []
    
    def get_positions(self) -> List[Position]:
        """Get positions via automation."""
        try:
            # Navigate to portfolio page
            self.page.goto("https://live.trading212.com/en/portfolio")
            time.sleep(3)
            
            positions = []
            
            # Extract position data from portfolio table
            rows = self.page.locator('[data-testid="portfolio-row"]')
            for row in rows:
                try:
                    symbol = row.locator('[data-testid="symbol"]').text_content() or ""
                    qty = float(row.locator('[data-testid="quantity"]').text_content() or "0")
                    avg_price = float(row.locator('[data-testid="avg-price"]').text_content() or "0")
                    market_value = float(row.locator('[data-testid="market-value"]').text_content() or "0")
                    
                    position = Position(
                        symbol=symbol,
                        qty=qty,
                        avg_price=avg_price,
                        market_value=market_value,
                        currency="GBP"
                    )
                    positions.append(position)
                except:
                    continue
            
            return positions
        except Exception as e:
            logger.error(f"Error getting positions via automation: {e}")
            return []
    
    def get_cash(self, currency: str = "GBP") -> float:
        """Get available cash via automation."""
        try:
            # Navigate to account page
            self.page.goto("https://live.trading212.com/en/account")
            time.sleep(3)
            
            # Extract cash balance
            cash_element = self.page.locator('[data-testid="available-cash"]')
            if cash_element.count() > 0:
                cash_text = cash_element.text_content() or "0"
                # Remove currency symbol and convert to float
                cash = float(cash_text.replace("£", "").replace(",", ""))
                return cash
            
            return 0.0
        except Exception as e:
            logger.error(f"Error getting cash via automation: {e}")
            return 0.0
    
    def place_order(self, symbol: str, side: Side, qty: float,
                    order_type: OrderType = "market",
                    limit_price: Optional[float] = None) -> OrderResponse:
        """Place order via automation."""
        try:
            # Navigate to symbol page
            self.page.goto(f"https://live.trading212.com/en/instruments/{symbol}")
            time.sleep(2)
            
            # Click buy/sell button
            if side == "buy":
                self.page.click('[data-testid="buy-button"]')
            else:
                self.page.click('[data-testid="sell-button"]')
            
            time.sleep(1)
            
            # Enter quantity
            self.page.fill('[data-testid="quantity-input"]', str(qty))
            
            # Set order type if limit
            if order_type == "limit" and limit_price:
                self.page.click('[data-testid="limit-order"]')
                self.page.fill('[data-testid="limit-price"]', str(limit_price))
            
            # Submit order
            self.page.click('[data-testid="submit-order"]')
            time.sleep(2)
            
            # Check for success/error message
            success_msg = self.page.locator('[data-testid="order-success"]')
            if success_msg.count() > 0:
                return OrderResponse(
                    id="auto_" + str(int(time.time())),
                    status="accepted",
                    filled_qty=0.0,
                    avg_fill_price=None,
                    message="Order placed successfully"
                )
            else:
                error_msg = self.page.locator('[data-testid="order-error"]').text_content() or "Unknown error"
                return OrderResponse(
                    id="",
                    status="rejected",
                    filled_qty=0.0,
                    avg_fill_price=None,
                    message=error_msg
                )
                
        except Exception as e:
            logger.error(f"Error placing order via automation: {e}")
            return OrderResponse(
                id="",
                status="rejected",
                filled_qty=0.0,
                avg_fill_price=None,
                message=f"Order error: {e}"
            )

class T212(BrokerClient):
    """Trading 212 client with API and automation backends."""
    
    def __init__(self, mode: Literal["api", "automation"] = "api",
                 api_key: Optional[str] = None, api_secret: Optional[str] = None, 
                 profile_dir: Optional[str] = None):
        self.mode = mode
        self.backend = None
        
        if mode == "api":
            if not api_key:
                api_key = os.getenv("T212_API_KEY")
            if not api_secret:
                api_secret = os.getenv("T212_API_SECRET")
            if not api_key or not api_secret:
                raise ValueError("T212 API key and secret required for API mode")
            self.backend = _T212APIBackend(api_key, api_secret)
        else:
            self.backend = _T212AutomationBackend(profile_dir or "./t212_profile")
    
    def connect(self) -> bool:
        """Connect to T212."""
        return self.backend.connect()
    
    def disconnect(self) -> None:
        """Disconnect from T212."""
        if hasattr(self.backend, 'browser') and self.backend.browser:
            self.backend.browser.close()
        self.backend.connected = False
    
    def get_quotes(self, symbols: List[str]) -> List[Quote]:
        """Get quotes for symbols."""
        return self.backend.get_quotes(symbols)
    
    def get_positions(self) -> List[Position]:
        """Get current positions."""
        return self.backend.get_positions()
    
    def get_cash(self, currency: str = "GBP") -> float:
        """Get available cash."""
        return self.backend.get_cash(currency)
    
    def get_account_summary(self) -> Dict[str, float]:
        """Get full account summary including cash, invested, and NAV."""
        if hasattr(self.backend, 'get_account_summary'):
            return self.backend.get_account_summary()
        # Fallback: construct from get_cash and positions
        cash = self.get_cash()
        positions = self.get_positions()
        equity = sum(pos.get('market_value', 0) or pos.get('value', 0) for pos in positions)
        return {
            'free': cash,
            'total': cash,
            'invested': equity,
            'result': 0.0,
            'blocked': 0.0,
            'nav': cash + equity
        }
    
    def get_instruments(self, use_cache: bool = True, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch all instruments that your account has access to.
        
        Rate Limit: 1 request per 50 seconds
        
        Args:
            use_cache: If True, return cached instruments if available
            force_refresh: If True, force a fresh API call even if cache exists
        
        Returns:
            List of instrument dictionaries containing ticker, type, isin, etc.
        
        Note:
            This method is only available in API mode. In automation mode, it returns an empty list.
        """
        if self.mode == "api" and hasattr(self.backend, 'get_instruments'):
            return self.backend.get_instruments(use_cache=use_cache, force_refresh=force_refresh)
        else:
            logger.warning("get_instruments() is only available in API mode")
            return []
    
    def place_order(self, symbol: str, side: Side, qty: float,
                    order_type: OrderType = "market",
                    limit_price: Optional[float] = None) -> OrderResponse:
        """Place an order."""
        return self.backend.place_order(symbol, side, qty, order_type, limit_price)
    
    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """Get all pending orders (active orders not yet filled, cancelled, or expired).
        
        Rate Limit: 1 request per 5 seconds
        
        Returns:
            List of order dictionaries containing order details
        
        Note:
            This method is only available in API mode. In automation mode, it returns an empty list.
        """
        if self.mode == "api" and hasattr(self.backend, 'get_pending_orders'):
            return self.backend.get_pending_orders()
        else:
            logger.warning("get_pending_orders() is only available in API mode")
            return []
    
    def cancel_order(self, order_id: int) -> Dict[str, Any]:
        """Cancel a pending order by its unique ID.
        
        Rate Limit: 50 requests per 1 minute
        
        Args:
            order_id: The unique identifier of the order to cancel
        
        Returns:
            Dictionary with cancellation result
        
        Note:
            This method is only available in API mode. In automation mode, it returns an error.
        """
        if self.mode == "api" and hasattr(self.backend, 'cancel_order'):
            return self.backend.cancel_order(order_id)
        else:
            logger.warning("cancel_order() is only available in API mode")
            return {
                "success": False,
                "order_id": order_id,
                "message": "cancel_order() is only available in API mode"
            }
    
    def get_portfolio(self) -> Optional[Dict]:
        """Get portfolio summary with weights."""
        try:
            positions = self.get_positions()
            cash = self.get_cash()
            
            from core.utils.symbol_map_loader import t212_to_internal_map

            try:
                symbol_map = t212_to_internal_map()
            except Exception as e:
                logger.debug(f"Could not load symbol map: {e}")
                print(f"    ⚠️ Could not load symbol map: {e}")
                symbol_map = {}
            
            # Debug: show symbol map size
            if symbol_map:
                print(f"    📋 Loaded {len(symbol_map)} symbol mappings")
                # Show mappings for user's positions
                test_tickers = ['EEMMF_US_EQ', 'ISPYm_EQ', 'EQQQm_EQ']
                for ticker in test_tickers:
                    if ticker in symbol_map:
                        print(f"    ✅ {ticker} → {symbol_map[ticker]}")
            else:
                print(f"    ⚠️ Symbol map is empty!")
            
            # Convert positions to ETF symbols and calculate total value
            total_value = cash
            converted_positions = []
            market_prices = self.get_market_prices()  # Get current prices for market value calculation
            
            for pos in positions:
                # Handle both dict and Position object
                if hasattr(pos, 'symbol'):
                    # Position object (from data_structures.Position)
                    t212_ticker = pos.symbol
                    qty = getattr(pos, 'qty', getattr(pos, 'quantity', 0))
                    avg_price = getattr(pos, 'avg_price', 0.0)
                    market_value = getattr(pos, 'market_value', 0.0)
                    currency = getattr(pos, 'currency', 'GBP')
                else:
                    # Dict
                    t212_ticker = pos.get('symbol', '')
                    qty = pos.get('qty', pos.get('quantity', 0))
                    avg_price = pos.get('avg_price', 0.0)
                    market_value = pos.get('market_value', 0.0)
                    currency = pos.get('currency', 'GBP')
                
                # Convert to ETF symbol if mapping exists
                etf_symbol = symbol_map.get(t212_ticker, t212_ticker)
                if etf_symbol != t212_ticker:
                    logger.info(f"Converted T212 ticker {t212_ticker} → ETF symbol {etf_symbol}")
                    print(f"    ✅ Converted {t212_ticker} → {etf_symbol}")
                else:
                    # Position not in symbol map - keep original ticker
                    logger.info(f"Position {t212_ticker} not in symbol map - keeping original ticker")
                    print(f"    ℹ️  Position {t212_ticker} (no conversion available - keeping original ticker)")
                
                # If market_value is 0 or missing, calculate it from current price
                if market_value == 0 and qty > 0:
                    # Try to get current price from market_prices using ETF symbol
                    current_price = market_prices.get(etf_symbol, 0)
                    if current_price == 0:
                        # Fallback: use average price if current price not available
                        current_price = avg_price
                    market_value = qty * current_price
                
                total_value += market_value
                
                # Create position dict with ETF symbol
                converted_pos = {
                    'symbol': etf_symbol,
                    't212_ticker': t212_ticker,  # Keep original for reference
                    'qty': qty,
                    'avg_price': avg_price,
                    'market_value': market_value,
                    'current_price': market_prices.get(etf_symbol, avg_price),
                    'currency': pos.get('currency', 'GBP')
                }
                converted_positions.append(converted_pos)
            
            # Calculate weights using ETF symbols
            weights = {}
            for pos in converted_positions:
                if total_value > 0 and pos['market_value'] > 0:
                    weights[pos['symbol']] = pos['market_value'] / total_value
            
            return {
                'total_value': total_value,
                'weights': weights,
                'positions': converted_positions,
                'cash': cash
            }
        except Exception as e:
            logger.error(f"Error getting portfolio: {e}")
            return None
    
    def get_comprehensive_account_summary(self) -> Optional[Dict]:
        """Get comprehensive account summary."""
        try:
            portfolio = self.get_portfolio()
            if not portfolio:
                return None
            
            return {
                'total_net_liquidation': portfolio['total_value'],
                'total_available_funds': portfolio['cash'],
                'total_buying_power': portfolio['cash'],
                'currencies': {
                    'GBP': {
                        'net_liquidation': portfolio['total_value'],
                        'available_funds': portfolio['cash'],
                        'buying_power': portfolio['cash'],
                        'total_equity': portfolio['total_value'],
                        'cash': portfolio['cash']
                    }
                },
                'account_types': {},
                'detailed_summary': {}
            }
        except Exception as e:
            logger.error(f"Error getting account summary: {e}")
            return None
    
    @property
    def connected(self) -> bool:
        """Check if connected to T212."""
        return self.backend.connected if self.backend else False
    
    @classmethod
    def from_env(cls) -> 'T212':
        """Create T212Client from environment variables."""
        mode = os.getenv("T212_MODE", "api")
        api_key = os.getenv("T212_API_KEY")
        api_secret = os.getenv("T212_API_SECRET")
        profile_dir = os.getenv("T212_PROFILE_DIR", "./t212_profile")
        
        return cls(
            mode=mode,
            api_key=api_key,
            api_secret=api_secret,
            profile_dir=profile_dir
        )
    
    def get_market_prices(self) -> Dict[str, float]:
        """Quotes regime signal names plus any held lines; fills internal + T212 ticker aliases.

        Does not call get_portfolio (avoids recursion). Always requests REGIME_INTERNAL_SYMBOLS
        so regime logic works with an empty portfolio.
        """
        from core.utils.symbol_map_loader import (
            REGIME_INTERNAL_SYMBOLS,
            load_symbol_map,
            regime_signal_t212_candidates,
            t212_to_internal_map,
        )

        t212_rev = t212_to_internal_map()
        positions = self.get_positions()
        position_tickers: List[str] = []
        for pos in positions:
            if isinstance(pos, dict):
                t = pos.get("symbol", "") or ""
            else:
                t = getattr(pos, "symbol", "") or ""
            if t:
                position_tickers.append(t)

        internal_from_positions = {t212_rev.get(t, t) for t in position_tickers}
        symbols_to_quote = sorted(set(REGIME_INTERNAL_SYMBOLS) | internal_from_positions)
        print(
            f"    🔍 Fetching T212 quotes for {len(symbols_to_quote)} symbols "
            f"({len(REGIME_INTERNAL_SYMBOLS)} regime + positions)..."
        )

        quotes = self.get_quotes(symbols_to_quote)
        prices: Dict[str, float] = {}
        for q in quotes:
            last = float(q.get("last") or 0)
            if last > 0:
                prices[q["symbol"]] = last

        # Fill from API position snapshots where quotes failed
        for pos in positions:
            if isinstance(pos, dict):
                ticker = pos.get("symbol", "")
                price = float(pos.get("current_price") or 0)
                if price == 0:
                    qty = float(pos.get("qty") or pos.get("quantity") or 0)
                    mv = float(pos.get("market_value") or 0)
                    price = (mv / qty) if qty > 0 else 0.0
            else:
                ticker = getattr(pos, "symbol", "") or ""
                price = float(getattr(pos, "current_price", 0) or 0)
                if price == 0:
                    qty = float(getattr(pos, "qty", 0) or 0)
                    mv = float(getattr(pos, "market_value", 0) or 0)
                    price = (mv / qty) if qty > 0 else 0.0
            if price <= 0 or not ticker:
                continue
            etf = t212_rev.get(ticker, ticker)
            prices.setdefault(etf, price)

        # Direct /equity/quotes by raw T212 tickers for any still-missing regime names
        missing_regime = [s for s in REGIME_INTERNAL_SYMBOLS if not prices.get(s)]
        if missing_regime and self.mode == "api" and hasattr(self.backend, "get_market_prices_direct"):
            flat: List[str] = []
            cands = regime_signal_t212_candidates()
            for s in missing_regime:
                flat.extend(cands.get(s, []))
            flat = list(dict.fromkeys(flat))
            if flat:
                direct = self.backend.get_market_prices_direct(flat)
                for t212, p in direct.items():
                    if not p or p <= 0:
                        continue
                    internal = t212_rev.get(t212)
                    if internal:
                        prices.setdefault(internal, float(p))

        # Alias: internal name -> primary and alt T212 ids (so consumers can look up either)
        try:
            mapping = load_symbol_map()
            for internal, info in mapping.items():
                p = prices.get(internal)
                if not p or p <= 0:
                    continue
                prim = info.get("t212")
                if prim:
                    prices.setdefault(str(prim), float(p))
                for alt in info.get("t212_alt") or []:
                    if alt:
                        prices.setdefault(str(alt), float(p))
        except Exception as e:
            logger.debug("Could not alias T212 tickers in prices: %s", e)

        return prices
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary in the format expected by services."""
        positions = self.get_positions()
        cash = self.get_cash()
        
        # Convert positions to simple format
        pos_list = []
        equity = 0.0
        for pos in positions:
            if hasattr(pos, 'symbol'):
                symbol = pos.symbol
                qty = pos.qty
                avg_cost = pos.avg_price
                value = pos.market_value
            else:
                symbol = pos.get('symbol', '')
                qty = pos.get('qty', 0)
                avg_cost = pos.get('avg_price', 0)
                value = pos.get('market_value', 0)
            
            if qty > 0:
                pos_list.append({
                    "symbol": symbol,
                    "qty": qty,
                    "avg_cost": avg_cost,
                    "value": value
                })
                equity += value
        
        nav = cash + equity
        
        return {
            "cash": cash,
            "equity": equity,
            "positions": pos_list,
            "nav": nav
        }
    
    def place_market_order(self, symbol: str, qty: float) -> Dict[str, Any]:
        """Place a market order (simplified interface)."""
        side = "buy" if qty > 0 else "sell"
        qty = abs(qty)
        response = self.place_order(symbol, side, qty, "market")
        
        # Convert to dict
        if hasattr(response, '__dict__'):
            return {
                "id": response.id,
                "status": response.status,
                "filled_qty": response.filled_qty,
                "avg_fill_price": response.avg_fill_price,
                "message": response.message
            }
        return response

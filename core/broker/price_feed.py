"""
Price Feed - Abstract interface for fetching prices from multiple sources.
Implements T212 adapter (preferred), Yahoo Finance, and Alpha Vantage fallbacks.
"""

from typing import Optional, Dict, List, Tuple
from abc import ABC, abstractmethod
import logging
import yfinance as yf  # pyright: ignore[reportMissingImports]
import requests  # pyright: ignore[reportMissingModuleSource]
import os

logger = logging.getLogger(__name__)


class PriceFeed(ABC):
    """Abstract base class for price feeds."""
    
    @abstractmethod
    def get_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol. Returns None if unavailable."""
        pass
    
    @abstractmethod
    def get_quote(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get bid/ask/mid quote for a symbol. Returns None if unavailable."""
        pass
    
    @abstractmethod
    def get_quotes(self, symbols: List[str]) -> Dict[str, Optional[Dict[str, float]]]:
        """Get quotes for multiple symbols. Returns dict mapping symbol to quote."""
        pass


class T212PriceFeed(PriceFeed):
    """Trading 212 price feed adapter."""
    
    def __init__(self, t212_client):
        self.t212 = t212_client
    
    def get_price(self, symbol: str) -> Optional[float]:
        """Get current price from T212."""
        try:
            # Try quotes endpoint first
            quotes = self.t212.get_quotes([symbol])
            if quotes and len(quotes) > 0:
                quote = quotes[0]
                price = quote.get('last', 0) or quote.get('bid', 0) or quote.get('ask', 0)
                if price and price > 0:
                    return float(price)
            
            # Try positions (if we hold it)
            positions = self.t212.get_positions()
            for pos in positions:
                if pos.get('symbol') == symbol:
                    price = pos.get('current_price', 0)
                    if price > 0:
                        return float(price)
            
            # Try portfolio/ticker endpoint
            try:
                response = self.t212.backend._request("POST", "/equity/portfolio/ticker", 
                                                     json_payload={"ticker": symbol})
                if response.status_code == 200:
                    data = response.json()
                    price = float(data.get('currentPrice', 0))
                    if price > 0:
                        return price
            except:
                pass
            
            return None
        except Exception as e:
            logger.debug(f"T212 price fetch failed for {symbol}: {e}")
            return None
    
    def get_quote(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get bid/ask/mid quote from T212."""
        try:
            quotes = self.t212.get_quotes([symbol])
            if quotes and len(quotes) > 0:
                quote = quotes[0]
                bid = quote.get('bid', 0)
                ask = quote.get('ask', 0)
                last = quote.get('last', 0)
                
                if bid > 0 and ask > 0:
                    mid = (bid + ask) / 2
                    return {
                        'bid': float(bid),
                        'ask': float(ask),
                        'mid': float(mid),
                        'last': float(last) if last > 0 else mid
                    }
                elif last > 0:
                    return {
                        'bid': float(last),
                        'ask': float(last),
                        'mid': float(last),
                        'last': float(last)
                    }
            
            return None
        except Exception as e:
            logger.debug(f"T212 quote fetch failed for {symbol}: {e}")
            return None
    
    def get_quotes(self, symbols: List[str]) -> Dict[str, Optional[Dict[str, float]]]:
        """Get quotes for multiple symbols."""
        results = {}
        for symbol in symbols:
            results[symbol] = self.get_quote(symbol)
        return results


class YahooPriceFeed(PriceFeed):
    """Yahoo Finance price feed adapter (fallback)."""
    
    # UCITS ETF symbol mapping (Yahoo Finance uses different tickers)
    UCITS_MAPPING = {
        "EQQQ": "EQQQ.L",  # iShares Nasdaq 100 UCITS ETF (London)
        "IDUP": "IDUP.L",  # iShares Developed Markets UCITS ETF (London)
        "XLIS": "CSPX.L",  # iShares Core S&P 500 UCITS ETF (London)
        "SPY4": "MDY",     # SPDR S&P 400 Mid-Cap (US)
        "IGLT": "IGLT.L",  # iShares Core UK Gilts UCITS ETF (London)
        "VUKE": "VUKE.L",  # Vanguard FTSE 100 UCITS ETF (London)
        "VHYL": "VHYL.L",  # Vanguard FTSE All-World High Dividend Yield UCITS ETF (London)
    }
    
    def get_price(self, symbol: str) -> Optional[float]:
        """Get current price from Yahoo Finance."""
        # Try UCITS mapping first
        yahoo_symbol = self.UCITS_MAPPING.get(symbol, symbol)
        
        try:
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info
            
            # Try different price fields
            price = info.get('regularMarketPrice') or info.get('currentPrice') or info.get('previousClose')
            if price and price > 0:
                price = float(price)
                # UK stocks/ETFs are often quoted in pence - convert to pounds if price > 1000
                # (e.g., EQQQ.L might be 45892 pence = £458.92)
                if yahoo_symbol.endswith('.L') and price > 1000:
                    price = price / 100.0
                    logger.info(f"Yahoo price for {symbol} ({yahoo_symbol}): {price:.2f} pence → £{price:.2f}")
                else:
                    logger.info(f"Yahoo price for {symbol} ({yahoo_symbol}): ${price:.2f}")
                return price
            
            # Try getting latest price from history (1 day)
            try:
                hist = ticker.history(period="1d", interval="1m")
                if not hist.empty:
                    latest_price = float(hist['Close'].iloc[-1])
                    if latest_price > 0:
                        logger.info(f"Yahoo price for {symbol} ({yahoo_symbol}) from history: ${latest_price:.2f}")
                        return latest_price
            except:
                pass
            
            # Try 5-day history with daily interval
            try:
                hist = ticker.history(period="5d", interval="1d")
                if not hist.empty:
                    latest_price = float(hist['Close'].iloc[-1])
                    if latest_price > 0:
                        logger.info(f"Yahoo price for {symbol} ({yahoo_symbol}) from 5d history: ${latest_price:.2f}")
                        return latest_price
            except:
                pass
            
            # If original symbol failed and we used mapping, try original symbol
            if yahoo_symbol != symbol:
                try:
                    ticker_orig = yf.Ticker(symbol)
                    info_orig = ticker_orig.info
                    price_orig = info_orig.get('regularMarketPrice') or info_orig.get('currentPrice') or info_orig.get('previousClose')
                    if price_orig and price_orig > 0:
                        logger.info(f"Yahoo price for {symbol} (original): ${price_orig:.2f}")
                        return float(price_orig)
                except:
                    pass
            
            return None
        except Exception as e:
            logger.debug(f"Yahoo price fetch failed for {symbol} ({yahoo_symbol}): {e}")
            return None
    
    def get_quote(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get bid/ask/mid quote from Yahoo Finance."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            bid = info.get('bid', 0)
            ask = info.get('ask', 0)
            price = info.get('regularMarketPrice') or info.get('currentPrice', 0)
            
            if bid > 0 and ask > 0:
                mid = (bid + ask) / 2
                return {
                    'bid': float(bid),
                    'ask': float(ask),
                    'mid': float(mid),
                    'last': float(price) if price > 0 else mid
                }
            elif price > 0:
                return {
                    'bid': float(price),
                    'ask': float(price),
                    'mid': float(price),
                    'last': float(price)
                }
            
            return None
        except Exception as e:
            logger.debug(f"Yahoo quote fetch failed for {symbol}: {e}")
            return None
    
    def get_quotes(self, symbols: List[str]) -> Dict[str, Optional[Dict[str, float]]]:
        """Get quotes for multiple symbols."""
        results = {}
        for symbol in symbols:
            results[symbol] = self.get_quote(symbol)
        return results


class AlphaVantagePriceFeed(PriceFeed):
    """Alpha Vantage price feed adapter (fallback)."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY", "")
        self.base_url = "https://www.alphavantage.co/query"
    
    def get_price(self, symbol: str) -> Optional[float]:
        """Get current price from Alpha Vantage."""
        if not self.api_key:
            return None
        
        try:
            # Alpha Vantage Global Quote endpoint
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                quote = data.get("Global Quote", {})
                
                # Try different price fields (Alpha Vantage uses numbered keys)
                price_str = quote.get("05. price") or quote.get("08. previous close")
                if price_str:
                    try:
                        price = float(price_str)
                        if price > 0:
                            logger.info(f"Alpha Vantage price for {symbol}: ${price:.2f}")
                            return price
                    except (ValueError, TypeError):
                        pass
            
            return None
        except Exception as e:
            logger.debug(f"Alpha Vantage price fetch failed for {symbol}: {e}")
            return None
    
    def get_quote(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get bid/ask/mid quote from Alpha Vantage."""
        if not self.api_key:
            return None
        
        try:
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                quote = data.get("Global Quote", {})
                
                price = float(quote.get("05. price", 0) or quote.get("08. previous close", 0))
                if price > 0:
                    return {
                        'bid': price,
                        'ask': price,
                        'mid': price,
                        'last': price
                    }
            
            return None
        except Exception as e:
            logger.debug(f"Alpha Vantage quote fetch failed for {symbol}: {e}")
            return None
    
    def get_quotes(self, symbols: List[str]) -> Dict[str, Optional[Dict[str, float]]]:
        """Get quotes for multiple symbols."""
        results = {}
        for symbol in symbols:
            results[symbol] = self.get_quote(symbol)
        return results


class CompositePriceFeed(PriceFeed):
    """Composite price feed that tries T212 first, then Yahoo Finance, then Alpha Vantage."""
    
    def __init__(self, t212_client, prefer_yahoo: bool = False):
        self.t212_feed = T212PriceFeed(t212_client)
        self.yahoo_feed = YahooPriceFeed()
        self.alpha_vantage_feed = AlphaVantagePriceFeed()
        self.prefer_yahoo = prefer_yahoo  # If True, prioritize Yahoo Finance
    
    def get_price(self, symbol: str) -> Optional[float]:
        """Get price: try T212 first (or Yahoo if preferred), fallback to Yahoo/Alpha Vantage."""
        if self.prefer_yahoo:
            # Prioritize Yahoo Finance
            price = self.yahoo_feed.get_price(symbol)
            if price:
                return price
            # Fallback to Alpha Vantage
            price = self.alpha_vantage_feed.get_price(symbol)
            if price:
                return price
            # Last resort: T212
            return self.t212_feed.get_price(symbol)
        else:
            # Try T212 first, then Yahoo, then Alpha Vantage
            price = self.t212_feed.get_price(symbol)
            if price:
                return price
            price = self.yahoo_feed.get_price(symbol)
            if price:
                return price
            # Fallback to Alpha Vantage
            return self.alpha_vantage_feed.get_price(symbol)
    
    def get_quote(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get quote: try T212 first, fallback to Yahoo, then Alpha Vantage."""
        quote = self.t212_feed.get_quote(symbol)
        if quote:
            return quote
        
        quote = self.yahoo_feed.get_quote(symbol)
        if quote:
            return quote
        
        return self.alpha_vantage_feed.get_quote(symbol)
    
    def get_quotes(self, symbols: List[str]) -> Dict[str, Optional[Dict[str, float]]]:
        """Get quotes: try T212 first, fallback to Yahoo, then Alpha Vantage."""
        results = {}
        
        # Try T212 for all symbols
        t212_results = self.t212_feed.get_quotes(symbols)
        
        # Fallback to Yahoo for any that failed
        for symbol in symbols:
            if t212_results.get(symbol):
                results[symbol] = t212_results[symbol]
            else:
                quote = self.yahoo_feed.get_quote(symbol)
                if quote:
                    results[symbol] = quote
                else:
                    # Last resort: Alpha Vantage
                    results[symbol] = self.alpha_vantage_feed.get_quote(symbol)
        
        return results


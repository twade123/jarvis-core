"""
OANDA Handler for Jarvis

MCP server handler for the OANDA v20 REST API. Provides complete access to
all OANDA endpoints: accounts, instruments, orders, trades, positions,
pricing, and transactions. Designed for use with the Jarvis Agent SDK
and Swarm MCP agent orchestration.

All endpoints from: https://developer.oanda.com/rest-live-v20/introduction/

Usage via MCP:
    python -m Jarvis_Agent_SDK.mcp_server_launcher oanda

Usage direct:
    from Handler.handler_oanda import OandaHandler
    handler = OandaHandler()
    result = await handler.get_account_summary()
"""

import os
import sys
import json
import time
import logging
import asyncio
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone

import requests

# Add project root to Python path
project_root = Path(__file__).parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from Handler.handler_base import BaseHandler, HandlerResult

# Configure logging
logger = logging.getLogger("OandaHandler")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _sh = logging.StreamHandler()
    _sh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(_sh)


# ─── Configuration ────────────────────────────────────────────────────────────

def _load_api_key() -> str:
    """Load OANDA API key from file or environment."""
    key_path = os.environ.get(
        "OANDA_API_KEY_PATH",
        os.path.join(project_root, "API", "OANDA_API_KEY.txt")
    )
    try:
        with open(key_path) as f:
            return f.read().strip()
    except FileNotFoundError:
        key = os.environ.get("OANDA_API_KEY", "")
        if not key:
            raise FileNotFoundError(
                f"OANDA API key not found at {key_path} and "
                "OANDA_API_KEY env var not set."
            )
        return key


DEFAULT_ACCOUNT_ID = os.environ.get("OANDA_ACCOUNT_ID", "101-001-24637237-001")
PRACTICE_URL = "https://api-fxpractice.oanda.com"
LIVE_URL = "https://api-fxtrade.oanda.com"
STREAM_PRACTICE_URL = "https://stream-fxpractice.oanda.com"
STREAM_LIVE_URL = "https://stream-fxtrade.oanda.com"

GRANULARITIES = [
    "S5", "S10", "S15", "S30",
    "M1", "M2", "M4", "M5", "M10", "M15", "M30",
    "H1", "H2", "H3", "H4", "H6", "H8", "H12",
    "D", "W", "M",
]


# ─── Rate Limiter ─────────────────────────────────────────────────────────────

class RateLimiter:
    """Simple rate limiter for OANDA API (max 100 req/s, 2 new connections/s)."""

    def __init__(self, max_per_second: int = 100):
        self.max_per_second = max_per_second
        self._timestamps: List[float] = []

    def wait_if_needed(self):
        now = time.time()
        self._timestamps = [t for t in self._timestamps if now - t < 1.0]
        if len(self._timestamps) >= self.max_per_second:
            sleep_time = 1.0 - (now - self._timestamps[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
        self._timestamps.append(time.time())


# ─── OANDA API Client ─────────────────────────────────────────────────────────

class OandaAPIError(Exception):
    """Exception for OANDA API errors."""
    def __init__(self, status_code: int, error_body: Any, url: str, method: str = "GET"):
        self.status_code = status_code
        self.error_body = error_body
        self.url = url
        self.method = method
        if isinstance(error_body, dict):
            msg = error_body.get("errorMessage", str(error_body))
        else:
            msg = str(error_body)
        super().__init__(f"OANDA API {method} {url} → {status_code}: {msg}")


class OandaClient:
    """Low-level OANDA v20 REST API client using requests.Session."""

    def __init__(self, api_key: str = None, account_id: str = None, practice: bool = True):
        self.api_key = api_key or _load_api_key()
        self.account_id = account_id or DEFAULT_ACCOUNT_ID
        self.base_url = PRACTICE_URL if practice else LIVE_URL
        self.stream_url = STREAM_PRACTICE_URL if practice else STREAM_LIVE_URL
        self.practice = practice
        self._rate_limiter = RateLimiter()
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept-Datetime-Format": "RFC3339",
        })

    def close(self):
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _request(self, method: str, path: str, params: dict = None,
                 json_body: dict = None, stream_url: bool = False) -> dict:
        """Make authenticated API request."""
        self._rate_limiter.wait_if_needed()
        base = self.stream_url if stream_url else self.base_url
        url = f"{base}{path}"

        resp = self._session.request(
            method=method, url=url, params=params, json=json_body, timeout=30
        )

        if resp.status_code >= 400:
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            raise OandaAPIError(resp.status_code, body, url, method)

        if resp.status_code == 204:
            return {}
        return resp.json()

    # ──────────────────────────────────────────────────────────────────────
    # ACCOUNT ENDPOINTS
    # ──────────────────────────────────────────────────────────────────────

    def list_accounts(self) -> dict:
        """GET /v3/accounts — List all accounts for current token."""
        return self._request("GET", "/v3/accounts")

    def get_account(self, account_id: str = None) -> dict:
        """GET /v3/accounts/{accountID} — Full account details."""
        aid = account_id or self.account_id
        return self._request("GET", f"/v3/accounts/{aid}")

    def get_account_summary(self, account_id: str = None) -> dict:
        """GET /v3/accounts/{accountID}/summary — Account summary."""
        aid = account_id or self.account_id
        return self._request("GET", f"/v3/accounts/{aid}/summary")

    def get_account_instruments(self, account_id: str = None,
                                 instruments: str = None) -> dict:
        """GET /v3/accounts/{accountID}/instruments — Tradeable instruments."""
        aid = account_id or self.account_id
        params = {}
        if instruments:
            params["instruments"] = instruments
        return self._request("GET", f"/v3/accounts/{aid}/instruments", params=params)

    def set_account_configuration(self, account_id: str = None,
                                   alias: str = None,
                                   margin_rate: str = None) -> dict:
        """PATCH /v3/accounts/{accountID}/configuration — Set account config."""
        aid = account_id or self.account_id
        body = {}
        if alias is not None:
            body["alias"] = alias
        if margin_rate is not None:
            body["marginRate"] = margin_rate
        return self._request("PATCH", f"/v3/accounts/{aid}/configuration", json_body=body)

    def get_account_changes(self, since_transaction_id: str,
                             account_id: str = None) -> dict:
        """GET /v3/accounts/{accountID}/changes — Poll for changes since txn ID."""
        aid = account_id or self.account_id
        return self._request("GET", f"/v3/accounts/{aid}/changes",
                             params={"sinceTransactionID": since_transaction_id})

    # ──────────────────────────────────────────────────────────────────────
    # INSTRUMENT ENDPOINTS
    # ──────────────────────────────────────────────────────────────────────

    def get_candles(self, instrument: str, price: str = "M",
                    granularity: str = "H1", count: int = None,
                    from_time: str = None, to_time: str = None,
                    smooth: bool = None, include_first: bool = None,
                    daily_alignment: int = None,
                    alignment_timezone: str = None,
                    weekly_alignment: str = None) -> dict:
        """GET /v3/instruments/{instrument}/candles — Fetch candlestick data."""
        params = {"price": price, "granularity": granularity}
        if count is not None:
            params["count"] = count
        if from_time is not None:
            params["from"] = from_time
        if to_time is not None:
            params["to"] = to_time
        if smooth is not None:
            params["smooth"] = str(smooth).lower()
        if include_first is not None:
            params["includeFirst"] = str(include_first).lower()
        if daily_alignment is not None:
            params["dailyAlignment"] = daily_alignment
        if alignment_timezone is not None:
            params["alignmentTimezone"] = alignment_timezone
        if weekly_alignment is not None:
            params["weeklyAlignment"] = weekly_alignment
        return self._request("GET", f"/v3/instruments/{instrument}/candles", params=params)

    # ──────────────────────────────────────────────────────────────────────
    # ORDER ENDPOINTS
    # ──────────────────────────────────────────────────────────────────────

    def create_order(self, order: dict, account_id: str = None) -> dict:
        """POST /v3/accounts/{accountID}/orders — Create an order."""
        aid = account_id or self.account_id
        return self._request("POST", f"/v3/accounts/{aid}/orders",
                             json_body={"order": order})

    def list_orders(self, account_id: str = None, ids: str = None,
                    state: str = None, instrument: str = None,
                    count: int = None, before_id: str = None) -> dict:
        """GET /v3/accounts/{accountID}/orders — List orders."""
        aid = account_id or self.account_id
        params = {}
        if ids:
            params["ids"] = ids
        if state:
            params["state"] = state
        if instrument:
            params["instrument"] = instrument
        if count is not None:
            params["count"] = count
        if before_id:
            params["beforeID"] = before_id
        return self._request("GET", f"/v3/accounts/{aid}/orders", params=params)

    def list_pending_orders(self, account_id: str = None) -> dict:
        """GET /v3/accounts/{accountID}/pendingOrders — List pending orders."""
        aid = account_id or self.account_id
        return self._request("GET", f"/v3/accounts/{aid}/pendingOrders")

    def get_order(self, order_specifier: str, account_id: str = None) -> dict:
        """GET /v3/accounts/{accountID}/orders/{orderSpecifier} — Get order details."""
        aid = account_id or self.account_id
        return self._request("GET", f"/v3/accounts/{aid}/orders/{order_specifier}")

    def replace_order(self, order_specifier: str, order: dict,
                      account_id: str = None) -> dict:
        """PUT /v3/accounts/{accountID}/orders/{orderSpecifier} — Replace order."""
        aid = account_id or self.account_id
        return self._request("PUT", f"/v3/accounts/{aid}/orders/{order_specifier}",
                             json_body={"order": order})

    def cancel_order(self, order_specifier: str, account_id: str = None) -> dict:
        """PUT /v3/accounts/{accountID}/orders/{orderSpecifier}/cancel — Cancel order."""
        aid = account_id or self.account_id
        return self._request("PUT", f"/v3/accounts/{aid}/orders/{order_specifier}/cancel")

    def set_order_client_extensions(self, order_specifier: str,
                                     client_extensions: dict = None,
                                     trade_client_extensions: dict = None,
                                     account_id: str = None) -> dict:
        """PUT /v3/accounts/{accountID}/orders/{orderSpecifier}/clientExtensions"""
        aid = account_id or self.account_id
        body = {}
        if client_extensions:
            body["clientExtensions"] = client_extensions
        if trade_client_extensions:
            body["tradeClientExtensions"] = trade_client_extensions
        return self._request("PUT",
                             f"/v3/accounts/{aid}/orders/{order_specifier}/clientExtensions",
                             json_body=body)

    # ──────────────────────────────────────────────────────────────────────
    # ORDER CONVENIENCE METHODS
    # ──────────────────────────────────────────────────────────────────────

    def place_market_order(self, instrument: str, units: int,
                           time_in_force: str = "FOK",
                           stop_loss_price: str = None,
                           take_profit_price: str = None,
                           trailing_stop_distance: str = None,
                           client_extensions: dict = None,
                           account_id: str = None) -> dict:
        """Place a market order with optional SL/TP/TSL."""
        order = {
            "type": "MARKET",
            "instrument": instrument,
            "units": str(units),
            "timeInForce": time_in_force,
            "positionFill": "DEFAULT",
        }
        if stop_loss_price:
            order["stopLossOnFill"] = {"price": stop_loss_price, "timeInForce": "GTC"}
        if take_profit_price:
            order["takeProfitOnFill"] = {"price": take_profit_price}
        if trailing_stop_distance:
            order["trailingStopLossOnFill"] = {"distance": trailing_stop_distance}
        if client_extensions:
            order["clientExtensions"] = client_extensions
        return self.create_order(order, account_id)

    def place_limit_order(self, instrument: str, units: int, price: str,
                          time_in_force: str = "GTC",
                          stop_loss_price: str = None,
                          take_profit_price: str = None,
                          trailing_stop_distance: str = None,
                          client_extensions: dict = None,
                          account_id: str = None) -> dict:
        """Place a limit order."""
        order = {
            "type": "LIMIT",
            "instrument": instrument,
            "units": str(units),
            "price": price,
            "timeInForce": time_in_force,
            "positionFill": "DEFAULT",
        }
        if stop_loss_price:
            order["stopLossOnFill"] = {"price": stop_loss_price, "timeInForce": "GTC"}
        if take_profit_price:
            order["takeProfitOnFill"] = {"price": take_profit_price}
        if trailing_stop_distance:
            order["trailingStopLossOnFill"] = {"distance": trailing_stop_distance}
        if client_extensions:
            order["clientExtensions"] = client_extensions
        return self.create_order(order, account_id)

    def place_stop_order(self, instrument: str, units: int, price: str,
                         time_in_force: str = "GTC",
                         stop_loss_price: str = None,
                         take_profit_price: str = None,
                         trailing_stop_distance: str = None,
                         client_extensions: dict = None,
                         account_id: str = None) -> dict:
        """Place a stop order."""
        order = {
            "type": "STOP",
            "instrument": instrument,
            "units": str(units),
            "price": price,
            "timeInForce": time_in_force,
            "positionFill": "DEFAULT",
        }
        if stop_loss_price:
            order["stopLossOnFill"] = {"price": stop_loss_price, "timeInForce": "GTC"}
        if take_profit_price:
            order["takeProfitOnFill"] = {"price": take_profit_price}
        if trailing_stop_distance:
            order["trailingStopLossOnFill"] = {"distance": trailing_stop_distance}
        if client_extensions:
            order["clientExtensions"] = client_extensions
        return self.create_order(order, account_id)

    def place_market_if_touched_order(self, instrument: str, units: int, price: str,
                                       time_in_force: str = "GTC",
                                       stop_loss_price: str = None,
                                       take_profit_price: str = None,
                                       trailing_stop_distance: str = None,
                                       client_extensions: dict = None,
                                       account_id: str = None) -> dict:
        """Place a market-if-touched order."""
        order = {
            "type": "MARKET_IF_TOUCHED",
            "instrument": instrument,
            "units": str(units),
            "price": price,
            "timeInForce": time_in_force,
            "positionFill": "DEFAULT",
        }
        if stop_loss_price:
            order["stopLossOnFill"] = {"price": stop_loss_price, "timeInForce": "GTC"}
        if take_profit_price:
            order["takeProfitOnFill"] = {"price": take_profit_price}
        if trailing_stop_distance:
            order["trailingStopLossOnFill"] = {"distance": trailing_stop_distance}
        if client_extensions:
            order["clientExtensions"] = client_extensions
        return self.create_order(order, account_id)

    def place_take_profit_order(self, trade_id: str, price: str,
                                 time_in_force: str = "GTC",
                                 account_id: str = None) -> dict:
        """Place a take-profit order on an existing trade."""
        order = {
            "type": "TAKE_PROFIT",
            "tradeID": trade_id,
            "price": price,
            "timeInForce": time_in_force,
        }
        return self.create_order(order, account_id)

    def place_stop_loss_order(self, trade_id: str, price: str,
                               time_in_force: str = "GTC",
                               account_id: str = None) -> dict:
        """Place a stop-loss order on an existing trade."""
        order = {
            "type": "STOP_LOSS",
            "tradeID": trade_id,
            "price": price,
            "timeInForce": time_in_force,
        }
        return self.create_order(order, account_id)

    def place_trailing_stop_loss_order(self, trade_id: str, distance: str,
                                        time_in_force: str = "GTC",
                                        account_id: str = None) -> dict:
        """Place a trailing stop-loss order on an existing trade."""
        order = {
            "type": "TRAILING_STOP_LOSS",
            "tradeID": trade_id,
            "distance": distance,
            "timeInForce": time_in_force,
        }
        return self.create_order(order, account_id)

    def place_guaranteed_stop_loss_order(self, trade_id: str, price: str,
                                          time_in_force: str = "GTC",
                                          account_id: str = None) -> dict:
        """Place a guaranteed stop-loss order on an existing trade."""
        order = {
            "type": "GUARANTEED_STOP_LOSS",
            "tradeID": trade_id,
            "price": price,
            "timeInForce": time_in_force,
        }
        return self.create_order(order, account_id)

    # ──────────────────────────────────────────────────────────────────────
    # TRADE ENDPOINTS
    # ──────────────────────────────────────────────────────────────────────

    def list_trades(self, account_id: str = None, ids: str = None,
                    state: str = None, instrument: str = None,
                    count: int = None, before_id: str = None) -> dict:
        """GET /v3/accounts/{accountID}/trades — List trades."""
        aid = account_id or self.account_id
        params = {}
        if ids:
            params["ids"] = ids
        if state:
            params["state"] = state
        if instrument:
            params["instrument"] = instrument
        if count is not None:
            params["count"] = count
        if before_id:
            params["beforeID"] = before_id
        return self._request("GET", f"/v3/accounts/{aid}/trades", params=params)

    def list_open_trades(self, account_id: str = None) -> dict:
        """GET /v3/accounts/{accountID}/openTrades — List open trades."""
        aid = account_id or self.account_id
        return self._request("GET", f"/v3/accounts/{aid}/openTrades")

    def get_trade(self, trade_specifier: str, account_id: str = None) -> dict:
        """GET /v3/accounts/{accountID}/trades/{tradeSpecifier} — Get trade details."""
        aid = account_id or self.account_id
        return self._request("GET", f"/v3/accounts/{aid}/trades/{trade_specifier}")

    def close_trade(self, trade_specifier: str, units: str = "ALL",
                    account_id: str = None) -> dict:
        """PUT /v3/accounts/{accountID}/trades/{tradeSpecifier}/close — Close trade."""
        aid = account_id or self.account_id
        return self._request("PUT", f"/v3/accounts/{aid}/trades/{trade_specifier}/close",
                             json_body={"units": units})

    def set_trade_client_extensions(self, trade_specifier: str,
                                     client_extensions: dict,
                                     account_id: str = None) -> dict:
        """PUT /v3/accounts/{accountID}/trades/{tradeSpecifier}/clientExtensions"""
        aid = account_id or self.account_id
        return self._request(
            "PUT", f"/v3/accounts/{aid}/trades/{trade_specifier}/clientExtensions",
            json_body={"clientExtensions": client_extensions}
        )

    def set_trade_dependent_orders(self, trade_specifier: str,
                                    take_profit: dict = None,
                                    stop_loss: dict = None,
                                    trailing_stop_loss: dict = None,
                                    guaranteed_stop_loss: dict = None,
                                    account_id: str = None) -> dict:
        """PUT /v3/accounts/{accountID}/trades/{tradeSpecifier}/orders — Set TP/SL/TSL."""
        aid = account_id or self.account_id
        body = {}
        if take_profit is not None:
            body["takeProfit"] = take_profit
        if stop_loss is not None:
            body["stopLoss"] = stop_loss
        if trailing_stop_loss is not None:
            body["trailingStopLoss"] = trailing_stop_loss
        if guaranteed_stop_loss is not None:
            body["guaranteedStopLoss"] = guaranteed_stop_loss
        return self._request("PUT", f"/v3/accounts/{aid}/trades/{trade_specifier}/orders",
                             json_body=body)

    # ──────────────────────────────────────────────────────────────────────
    # POSITION ENDPOINTS
    # ──────────────────────────────────────────────────────────────────────

    def list_positions(self, account_id: str = None) -> dict:
        """GET /v3/accounts/{accountID}/positions — List all positions."""
        aid = account_id or self.account_id
        return self._request("GET", f"/v3/accounts/{aid}/positions")

    def list_open_positions(self, account_id: str = None) -> dict:
        """GET /v3/accounts/{accountID}/openPositions — List open positions."""
        aid = account_id or self.account_id
        return self._request("GET", f"/v3/accounts/{aid}/openPositions")

    def get_position(self, instrument: str, account_id: str = None) -> dict:
        """GET /v3/accounts/{accountID}/positions/{instrument} — Get position."""
        aid = account_id or self.account_id
        return self._request("GET", f"/v3/accounts/{aid}/positions/{instrument}")

    def close_position(self, instrument: str,
                       long_units: str = None, short_units: str = None,
                       long_client_extensions: dict = None,
                       short_client_extensions: dict = None,
                       account_id: str = None) -> dict:
        """PUT /v3/accounts/{accountID}/positions/{instrument}/close — Close position."""
        aid = account_id or self.account_id
        body = {}
        if long_units is not None:
            body["longUnits"] = long_units
        if short_units is not None:
            body["shortUnits"] = short_units
        if long_client_extensions:
            body["longClientExtensions"] = long_client_extensions
        if short_client_extensions:
            body["shortClientExtensions"] = short_client_extensions
        return self._request("PUT", f"/v3/accounts/{aid}/positions/{instrument}/close",
                             json_body=body)

    # ──────────────────────────────────────────────────────────────────────
    # PRICING ENDPOINTS
    # ──────────────────────────────────────────────────────────────────────

    def get_pricing(self, instruments: str, since: str = None,
                    include_units_available: bool = None,
                    include_home_conversions: bool = None,
                    account_id: str = None) -> dict:
        """GET /v3/accounts/{accountID}/pricing — Get current prices."""
        aid = account_id or self.account_id
        params = {"instruments": instruments}
        if since:
            params["since"] = since
        if include_units_available is not None:
            params["includeUnitsAvailable"] = str(include_units_available).lower()
        if include_home_conversions is not None:
            params["includeHomeConversions"] = str(include_home_conversions).lower()
        return self._request("GET", f"/v3/accounts/{aid}/pricing", params=params)

    def get_latest_candles(self, candle_specifications: str,
                           units: str = None, smooth: bool = None,
                           daily_alignment: int = None,
                           alignment_timezone: str = None,
                           weekly_alignment: str = None,
                           account_id: str = None) -> dict:
        """GET /v3/accounts/{accountID}/candles/latest — Get latest candles."""
        aid = account_id or self.account_id
        params = {"candleSpecifications": candle_specifications}
        if units:
            params["units"] = units
        if smooth is not None:
            params["smooth"] = str(smooth).lower()
        if daily_alignment is not None:
            params["dailyAlignment"] = daily_alignment
        if alignment_timezone:
            params["alignmentTimezone"] = alignment_timezone
        if weekly_alignment:
            params["weeklyAlignment"] = weekly_alignment
        return self._request("GET", f"/v3/accounts/{aid}/candles/latest", params=params)

    def get_account_candles(self, instrument: str, account_id: str = None,
                             price: str = "M", granularity: str = "H1",
                             count: int = None, from_time: str = None,
                             to_time: str = None, smooth: bool = None,
                             include_first: bool = None,
                             daily_alignment: int = None,
                             alignment_timezone: str = None,
                             weekly_alignment: str = None,
                             units: str = None) -> dict:
        """GET /v3/accounts/{accountID}/instruments/{instrument}/candles — Account candles."""
        aid = account_id or self.account_id
        params = {"price": price, "granularity": granularity}
        if count is not None:
            params["count"] = count
        if from_time:
            params["from"] = from_time
        if to_time:
            params["to"] = to_time
        if smooth is not None:
            params["smooth"] = str(smooth).lower()
        if include_first is not None:
            params["includeFirst"] = str(include_first).lower()
        if daily_alignment is not None:
            params["dailyAlignment"] = daily_alignment
        if alignment_timezone:
            params["alignmentTimezone"] = alignment_timezone
        if weekly_alignment:
            params["weeklyAlignment"] = weekly_alignment
        if units:
            params["units"] = units
        return self._request("GET", f"/v3/accounts/{aid}/instruments/{instrument}/candles",
                             params=params)

    # NOTE: Streaming endpoints (pricing/stream, transactions/stream) are
    # long-lived connections. They are exposed here but should be consumed
    # via a dedicated streaming process, not typical request/response.

    def get_pricing_stream_url(self, instruments: str, snapshot: bool = True,
                                account_id: str = None) -> str:
        """Build the URL for the pricing stream (use with streaming client)."""
        aid = account_id or self.account_id
        params = f"instruments={instruments}&snapshot={'true' if snapshot else 'false'}"
        return f"{self.stream_url}/v3/accounts/{aid}/pricing/stream?{params}"

    def get_transaction_stream_url(self, account_id: str = None) -> str:
        """Build the URL for the transaction stream."""
        aid = account_id or self.account_id
        return f"{self.stream_url}/v3/accounts/{aid}/transactions/stream"

    # ──────────────────────────────────────────────────────────────────────
    # TRANSACTION ENDPOINTS
    # ──────────────────────────────────────────────────────────────────────

    def list_transactions(self, account_id: str = None,
                          from_time: str = None, to_time: str = None,
                          page_size: int = None,
                          type_filter: str = None) -> dict:
        """GET /v3/accounts/{accountID}/transactions — List transaction pages."""
        aid = account_id or self.account_id
        params = {}
        if from_time:
            params["from"] = from_time
        if to_time:
            params["to"] = to_time
        if page_size is not None:
            params["pageSize"] = page_size
        if type_filter:
            params["type"] = type_filter
        return self._request("GET", f"/v3/accounts/{aid}/transactions", params=params)

    def get_transaction(self, transaction_id: str, account_id: str = None) -> dict:
        """GET /v3/accounts/{accountID}/transactions/{transactionID}"""
        aid = account_id or self.account_id
        return self._request("GET", f"/v3/accounts/{aid}/transactions/{transaction_id}")

    def get_transactions_id_range(self, from_id: str, to_id: str,
                                   type_filter: str = None,
                                   account_id: str = None) -> dict:
        """GET /v3/accounts/{accountID}/transactions/idrange"""
        aid = account_id or self.account_id
        params = {"from": from_id, "to": to_id}
        if type_filter:
            params["type"] = type_filter
        return self._request("GET", f"/v3/accounts/{aid}/transactions/idrange", params=params)

    def get_transactions_since_id(self, since_id: str,
                                   type_filter: str = None,
                                   account_id: str = None) -> dict:
        """GET /v3/accounts/{accountID}/transactions/sinceid"""
        aid = account_id or self.account_id
        params = {"id": since_id}
        if type_filter:
            params["type"] = type_filter
        return self._request("GET", f"/v3/accounts/{aid}/transactions/sinceid", params=params)


# ─── HANDLER (MCP Interface) ─────────────────────────────────────────────────

class OandaHandler(BaseHandler):
    """
    Jarvis MCP Handler for OANDA v20 API.
    
    Exposes all OANDA endpoints as MCP tools via the Jarvis Agent SDK.
    All public methods are automatically discovered and registered as tools.
    """

    def __init__(self, practice: bool = True):
        super().__init__(app_name="OandaHandler", app_version="1.0.0")
        self.handler_name = "oanda"
        self.practice = practice
        self._client = None

    @property
    def client(self) -> OandaClient:
        if self._client is None:
            self._client = OandaClient(practice=self.practice)
        return self._client

    async def handle(self, task_description: Dict[str, Any]) -> HandlerResult:
        """Main dispatch — route action to appropriate method."""
        action = task_description.get("action", "").lower()
        params = task_description.get("parameters", {})

        method = getattr(self, action, None)
        if method is None or action.startswith("_"):
            return self.create_error_result(
                f"Unknown action: {action}. Available: {self._list_actions()}"
            )
        try:
            if asyncio.iscoroutinefunction(method):
                result = await method(**params)
            else:
                result = method(**params)
            return self.create_success_result(data=result)
        except OandaAPIError as e:
            return self.create_error_result(str(e), metadata={
                "status_code": e.status_code,
                "error_body": e.error_body
            })
        except Exception as e:
            logger.error(f"Error in action '{action}': {traceback.format_exc()}")
            return self.create_error_result(str(e))

    def _list_actions(self) -> List[str]:
        """List all available public action methods."""
        skip = {"handle", "client", "create_success_result", "create_error_result",
                "handle_error", "execute", "cleanup", "close"}
        return sorted([
            m for m in dir(self)
            if not m.startswith("_") and callable(getattr(self, m)) and m not in skip
        ])

    # ──── ACCOUNT ACTIONS ─────────────────────────────────────────────────

    def list_accounts(self) -> dict:
        """List all accounts authorized for the API token."""
        return self.client.list_accounts()

    def get_account(self, account_id: str = None) -> dict:
        """Get full account details including positions, orders, trades."""
        return self.client.get_account(account_id)

    def get_account_summary(self, account_id: str = None) -> dict:
        """Get account summary (balance, NAV, margin, P&L)."""
        return self.client.get_account_summary(account_id)

    def get_account_instruments(self, account_id: str = None,
                                 instruments: str = None) -> dict:
        """List tradeable instruments for the account. Pass instrument names as CSV."""
        return self.client.get_account_instruments(account_id, instruments)

    def set_account_configuration(self, alias: str = None,
                                   margin_rate: str = None,
                                   account_id: str = None) -> dict:
        """Set account alias or margin rate."""
        return self.client.set_account_configuration(account_id, alias, margin_rate)

    def get_account_changes(self, since_transaction_id: str,
                             account_id: str = None) -> dict:
        """Poll for account changes since a specific transaction ID."""
        return self.client.get_account_changes(since_transaction_id, account_id)

    # ──── INSTRUMENT ACTIONS ──────────────────────────────────────────────

    def get_candles(self, instrument: str, price: str = "M",
                    granularity: str = "H1", count: int = 500,
                    from_time: str = None, to_time: str = None,
                    smooth: bool = None, include_first: bool = None,
                    daily_alignment: int = None,
                    alignment_timezone: str = None,
                    weekly_alignment: str = None) -> dict:
        """Fetch candlestick data for any instrument. Supports all granularities from S5 to M (monthly)."""
        return self.client.get_candles(
            instrument, price, granularity, count, from_time, to_time,
            smooth, include_first, daily_alignment, alignment_timezone,
            weekly_alignment
        )

    # ──── ORDER ACTIONS ───────────────────────────────────────────────────

    def create_order(self, order: dict, account_id: str = None) -> dict:
        """Create any order type using raw order specification dict."""
        return self.client.create_order(order, account_id)

    def place_market_order(self, instrument: str, units: int,
                           stop_loss_price: str = None,
                           take_profit_price: str = None,
                           trailing_stop_distance: str = None,
                           time_in_force: str = "FOK",
                           client_extensions: dict = None,
                           account_id: str = None) -> dict:
        """Place a market order. Positive units = buy, negative = sell."""
        return self.client.place_market_order(
            instrument, units, time_in_force, stop_loss_price,
            take_profit_price, trailing_stop_distance, client_extensions, account_id
        )

    def place_limit_order(self, instrument: str, units: int, price: str,
                          stop_loss_price: str = None,
                          take_profit_price: str = None,
                          trailing_stop_distance: str = None,
                          time_in_force: str = "GTC",
                          client_extensions: dict = None,
                          account_id: str = None) -> dict:
        """Place a limit order at a specified price."""
        return self.client.place_limit_order(
            instrument, units, price, time_in_force, stop_loss_price,
            take_profit_price, trailing_stop_distance, client_extensions, account_id
        )

    def place_stop_order(self, instrument: str, units: int, price: str,
                         stop_loss_price: str = None,
                         take_profit_price: str = None,
                         trailing_stop_distance: str = None,
                         time_in_force: str = "GTC",
                         client_extensions: dict = None,
                         account_id: str = None) -> dict:
        """Place a stop order triggered at a specified price."""
        return self.client.place_stop_order(
            instrument, units, price, time_in_force, stop_loss_price,
            take_profit_price, trailing_stop_distance, client_extensions, account_id
        )

    def place_market_if_touched_order(self, instrument: str, units: int, price: str,
                                       stop_loss_price: str = None,
                                       take_profit_price: str = None,
                                       trailing_stop_distance: str = None,
                                       time_in_force: str = "GTC",
                                       client_extensions: dict = None,
                                       account_id: str = None) -> dict:
        """Place a market-if-touched (entry) order."""
        return self.client.place_market_if_touched_order(
            instrument, units, price, time_in_force, stop_loss_price,
            take_profit_price, trailing_stop_distance, client_extensions, account_id
        )

    def place_take_profit_order(self, trade_id: str, price: str,
                                 time_in_force: str = "GTC",
                                 account_id: str = None) -> dict:
        """Place a take-profit order on an existing trade."""
        return self.client.place_take_profit_order(trade_id, price, time_in_force, account_id)

    def place_stop_loss_order(self, trade_id: str, price: str,
                               time_in_force: str = "GTC",
                               account_id: str = None) -> dict:
        """Place a stop-loss order on an existing trade."""
        return self.client.place_stop_loss_order(trade_id, price, time_in_force, account_id)

    def place_trailing_stop_loss_order(self, trade_id: str, distance: str,
                                        time_in_force: str = "GTC",
                                        account_id: str = None) -> dict:
        """Place a trailing stop-loss order on an existing trade."""
        return self.client.place_trailing_stop_loss_order(
            trade_id, distance, time_in_force, account_id
        )

    def place_guaranteed_stop_loss_order(self, trade_id: str, price: str,
                                          time_in_force: str = "GTC",
                                          account_id: str = None) -> dict:
        """Place a guaranteed stop-loss order on an existing trade."""
        return self.client.place_guaranteed_stop_loss_order(
            trade_id, price, time_in_force, account_id
        )

    def list_orders(self, account_id: str = None, ids: str = None,
                    state: str = None, instrument: str = None,
                    count: int = None, before_id: str = None) -> dict:
        """List orders. Filter by IDs, state (PENDING/FILLED/ALL), instrument."""
        return self.client.list_orders(account_id, ids, state, instrument, count, before_id)

    def list_pending_orders(self, account_id: str = None) -> dict:
        """List all pending orders for the account."""
        return self.client.list_pending_orders(account_id)

    def get_order(self, order_specifier: str, account_id: str = None) -> dict:
        """Get details of a single order by ID or client ID (@my_order)."""
        return self.client.get_order(order_specifier, account_id)

    def replace_order(self, order_specifier: str, order: dict,
                      account_id: str = None) -> dict:
        """Replace (cancel + recreate) an existing order."""
        return self.client.replace_order(order_specifier, order, account_id)

    def cancel_order(self, order_specifier: str, account_id: str = None) -> dict:
        """Cancel a pending order by ID or client ID (@my_order)."""
        return self.client.cancel_order(order_specifier, account_id)

    def set_order_client_extensions(self, order_specifier: str,
                                     client_extensions: dict = None,
                                     trade_client_extensions: dict = None,
                                     account_id: str = None) -> dict:
        """Set client extensions (id/tag/comment) on an order."""
        return self.client.set_order_client_extensions(
            order_specifier, client_extensions, trade_client_extensions, account_id
        )

    # ──── TRADE ACTIONS ───────────────────────────────────────────────────

    def list_trades(self, account_id: str = None, ids: str = None,
                    state: str = None, instrument: str = None,
                    count: int = None, before_id: str = None) -> dict:
        """List trades. Filter by IDs, state (OPEN/CLOSED/ALL), instrument."""
        return self.client.list_trades(account_id, ids, state, instrument, count, before_id)

    def list_open_trades(self, account_id: str = None) -> dict:
        """List all currently open trades."""
        return self.client.list_open_trades(account_id)

    def get_trade(self, trade_specifier: str, account_id: str = None) -> dict:
        """Get details of a specific trade by ID or client ID (@my_trade)."""
        return self.client.get_trade(trade_specifier, account_id)

    def close_trade(self, trade_specifier: str, units: str = "ALL",
                    account_id: str = None) -> dict:
        """Close a trade fully or partially. units='ALL' or a number."""
        return self.client.close_trade(trade_specifier, units, account_id)

    def set_trade_client_extensions(self, trade_specifier: str,
                                     client_extensions: dict,
                                     account_id: str = None) -> dict:
        """Set client extensions (id/tag/comment) on a trade."""
        return self.client.set_trade_client_extensions(
            trade_specifier, client_extensions, account_id
        )

    def set_trade_dependent_orders(self, trade_specifier: str,
                                    take_profit: dict = None,
                                    stop_loss: dict = None,
                                    trailing_stop_loss: dict = None,
                                    guaranteed_stop_loss: dict = None,
                                    account_id: str = None) -> dict:
        """Set/modify/cancel TP, SL, TSL, GSL on a trade. Pass null to cancel."""
        return self.client.set_trade_dependent_orders(
            trade_specifier, take_profit, stop_loss,
            trailing_stop_loss, guaranteed_stop_loss, account_id
        )

    # ──── POSITION ACTIONS ────────────────────────────────────────────────

    def list_positions(self, account_id: str = None) -> dict:
        """List all positions (including instruments with no current position)."""
        return self.client.list_positions(account_id)

    def list_open_positions(self, account_id: str = None) -> dict:
        """List only open positions (instruments with active trades)."""
        return self.client.list_open_positions(account_id)

    def get_position(self, instrument: str, account_id: str = None) -> dict:
        """Get position details for a specific instrument."""
        return self.client.get_position(instrument, account_id)

    def close_position(self, instrument: str,
                       long_units: str = None, short_units: str = None,
                       account_id: str = None) -> dict:
        """Close a position. Use long_units='ALL' or short_units='ALL' or specific amounts."""
        return self.client.close_position(instrument, long_units, short_units,
                                           account_id=account_id)

    # ──── PRICING ACTIONS ─────────────────────────────────────────────────

    def get_pricing(self, instruments: str, since: str = None,
                    include_home_conversions: bool = None,
                    account_id: str = None) -> dict:
        """Get current bid/ask pricing for instruments (CSV list)."""
        return self.client.get_pricing(instruments, since,
                                        include_home_conversions=include_home_conversions,
                                        account_id=account_id)

    def get_latest_candles(self, candle_specifications: str,
                           units: str = None, smooth: bool = None,
                           account_id: str = None) -> dict:
        """Get latest candles for specifications (e.g. 'EUR_USD:S5:BM,USD_CAD:H1:M')."""
        return self.client.get_latest_candles(
            candle_specifications, units, smooth, account_id=account_id
        )

    def get_account_candles(self, instrument: str,
                             price: str = "M", granularity: str = "H1",
                             count: int = 500, from_time: str = None,
                             to_time: str = None, units: str = None,
                             account_id: str = None) -> dict:
        """Fetch candles through the account endpoint (volume-weighted with units)."""
        return self.client.get_account_candles(
            instrument, account_id, price, granularity, count,
            from_time, to_time, units=units
        )

    def get_pricing_stream_url(self, instruments: str,
                                account_id: str = None) -> str:
        """Get the streaming URL for live price updates (for external consumer)."""
        return self.client.get_pricing_stream_url(instruments, account_id=account_id)

    # ──── TRANSACTION ACTIONS ─────────────────────────────────────────────

    def list_transactions(self, from_time: str = None, to_time: str = None,
                          page_size: int = None, type_filter: str = None,
                          account_id: str = None) -> dict:
        """List transaction pages in a time range. Returns page URLs."""
        return self.client.list_transactions(account_id, from_time, to_time,
                                              page_size, type_filter)

    def get_transaction(self, transaction_id: str, account_id: str = None) -> dict:
        """Get details of a single transaction by ID."""
        return self.client.get_transaction(transaction_id, account_id)

    def get_transactions_id_range(self, from_id: str, to_id: str,
                                   type_filter: str = None,
                                   account_id: str = None) -> dict:
        """Get transactions within an ID range."""
        return self.client.get_transactions_id_range(from_id, to_id, type_filter, account_id)

    def get_transactions_since_id(self, since_id: str,
                                   type_filter: str = None,
                                   account_id: str = None) -> dict:
        """Get all transactions since a specific ID (exclusive)."""
        return self.client.get_transactions_since_id(since_id, type_filter, account_id)

    def get_transaction_stream_url(self, account_id: str = None) -> str:
        """Get the streaming URL for live transaction updates."""
        return self.client.get_transaction_stream_url(account_id)

    # ──── UTILITY ACTIONS ─────────────────────────────────────────────────

    def get_available_actions(self) -> List[str]:
        """List all available actions this handler supports."""
        return self._list_actions()

    def get_supported_granularities(self) -> List[str]:
        """List all supported candlestick granularities."""
        return GRANULARITIES

    def ping(self) -> dict:
        """Test connectivity by fetching account summary."""
        try:
            result = self.client.get_account_summary()
            return {
                "status": "ok",
                "account_id": self.client.account_id,
                "practice": self.practice,
                "balance": result.get("account", {}).get("balance"),
                "nav": result.get("account", {}).get("NAV"),
                "currency": result.get("account", {}).get("currency"),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

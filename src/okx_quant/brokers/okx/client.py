"""Minimal OKX REST client.

Only a small set of endpoints is wrapped here. Each wrapped endpoint maps to
an OKX API concept recorded in docs/EVIDENCE.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from okx_quant.brokers.okx.auth import OKXAuth
from okx_quant.brokers.okx.orders import OKXCancelOrderRequest, OKXPlaceOrderRequest


OKX_REST_BASE_URL = "https://openapi.okx.com"
DEFAULT_USER_AGENT = "okx-quant-lab/0.1"


def _default_rest_base_url() -> str:
    return os.getenv("OKX_REST_BASE_URL", OKX_REST_BASE_URL).rstrip("/")


@dataclass(frozen=True)
class OKXRestClient:
    base_url: str = field(default_factory=_default_rest_base_url)
    auth: OKXAuth | None = None
    timeout_seconds: int = 10
    max_retries: int = 2
    retry_delay_seconds: float = 1.0

    def get_public_instruments(self, inst_type: str = "SPOT") -> dict[str, Any]:
        return self._get("/api/v5/public/instruments", {"instType": inst_type})

    def get_history_candles(
        self,
        inst_id: str,
        bar: str = "1H",
        limit: int = 100,
        after: str | None = None,
        before: str | None = None,
    ) -> dict[str, Any]:
        params = {"instId": inst_id, "bar": bar, "limit": str(limit)}
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        return self._get("/api/v5/market/history-candles", params)

    def get_candles(self, inst_id: str, bar: str = "1H", limit: int = 100) -> dict[str, Any]:
        return self._get(
            "/api/v5/market/candles",
            {"instId": inst_id, "bar": bar, "limit": str(limit)},
        )

    def get_ticker(self, inst_id: str) -> dict[str, Any]:
        return self._get("/api/v5/market/ticker", {"instId": inst_id})

    def get_order_book(self, inst_id: str, size: int = 5) -> dict[str, Any]:
        return self._get("/api/v5/market/books", {"instId": inst_id, "sz": str(size)})

    def get_trade_fee(self, inst_type: str = "SPOT", inst_id: str | None = None) -> dict[str, Any]:
        params = {"instType": inst_type}
        if inst_id:
            params["instId"] = inst_id
        return self._get_private("/api/v5/account/trade-fee", params)

    def get_balance(self, ccy: str | None = None) -> dict[str, Any]:
        params: dict[str, str] = {}
        if ccy:
            params["ccy"] = ccy
        return self._get_private("/api/v5/account/balance", params)

    def place_order(self, order: OKXPlaceOrderRequest) -> dict[str, Any]:
        return self._post_private("/api/v5/trade/order", order.to_payload())

    def cancel_order(self, order: OKXCancelOrderRequest) -> dict[str, Any]:
        return self._post_private("/api/v5/trade/cancel-order", order.to_payload())

    def get_order(self, *, inst_id: str, client_order_id: str | None = None, exchange_order_id: str | None = None) -> dict[str, Any]:
        if not client_order_id and not exchange_order_id:
            raise ValueError("client_order_id or exchange_order_id is required")
        params = {"instId": inst_id}
        if client_order_id:
            params["clOrdId"] = client_order_id
        if exchange_order_id:
            params["ordId"] = exchange_order_id
        return self._get_private("/api/v5/trade/order", params)

    def get_orders_pending(self, *, inst_type: str = "SPOT", inst_id: str | None = None, limit: int = 100) -> dict[str, Any]:
        params = {"instType": inst_type, "limit": str(limit)}
        if inst_id:
            params["instId"] = inst_id
        return self._get_private("/api/v5/trade/orders-pending", params)

    def get_orders_history(self, *, inst_type: str = "SPOT", inst_id: str | None = None, limit: int = 100) -> dict[str, Any]:
        params = {"instType": inst_type, "limit": str(limit)}
        if inst_id:
            params["instId"] = inst_id
        return self._get_private("/api/v5/trade/orders-history", params)

    def get_fills(self, *, inst_type: str = "SPOT", inst_id: str | None = None, limit: int = 100) -> dict[str, Any]:
        params = {"instType": inst_type, "limit": str(limit)}
        if inst_id:
            params["instId"] = inst_id
        return self._get_private("/api/v5/trade/fills", params)

    def get_bills(self, *, inst_type: str | None = "SPOT", ccy: str | None = None, limit: int = 100) -> dict[str, Any]:
        params = {"limit": str(limit)}
        if inst_type:
            params["instType"] = inst_type
        if ccy:
            params["ccy"] = ccy
        return self._get_private("/api/v5/account/bills", params)

    def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        request_path = build_request_path(path, params)
        return self._open_json(
            lambda: Request(
                f"{self.base_url}{request_path}",
                headers={"User-Agent": DEFAULT_USER_AGENT},
                method="GET",
            )
        )

    def _get_private(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        if self.auth is None:
            raise ValueError("private OKX endpoint requires auth")
        request_path = build_request_path(path, params)
        return self._open_json(
            lambda: Request(
                f"{self.base_url}{request_path}",
                headers={"User-Agent": DEFAULT_USER_AGENT, **self.auth.headers("GET", request_path)},
                method="GET",
            )
        )

    def _post_private(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self.auth is None:
            raise ValueError("private OKX endpoint requires auth")
        body = json.dumps(payload, separators=(",", ":"))
        return self._open_json(
            lambda: Request(
                f"{self.base_url}{path}",
                data=body.encode("utf-8"),
                headers={"User-Agent": DEFAULT_USER_AGENT, **self.auth.headers("POST", path, body)},
                method="POST",
            )
        )

    def _open_json(self, request_factory: Callable[[], Request]) -> dict[str, Any]:
        last_error: BaseException | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with urlopen(request_factory(), timeout=self.timeout_seconds) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except HTTPError as exc:
                if 400 <= exc.code < 500:
                    raise
                last_error = exc
            except (TimeoutError, URLError) as exc:
                last_error = exc

            if attempt < self.max_retries:
                time.sleep(self.retry_delay_seconds)

        if last_error is not None:
            raise last_error
        raise RuntimeError("request failed without an exception")


def build_request_path(path: str, params: dict[str, str]) -> str:
    if not params:
        return path
    return f"{path}?{urlencode(params)}"

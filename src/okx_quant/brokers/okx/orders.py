"""OKX order payload helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from okx_quant.domain.enums import OrderSide, OrderStatus, OrderType


PRICE_REQUIRED_TYPES = {OrderType.LIMIT, OrderType.POST_ONLY, OrderType.FOK, OrderType.IOC}


@dataclass(frozen=True)
class OKXPlaceOrderRequest:
    inst_id: str
    side: OrderSide
    order_type: OrderType
    size: Decimal
    client_order_id: str
    price: Decimal | None = None
    td_mode: str = "cash"

    def to_payload(self) -> dict[str, str]:
        if self.order_type in PRICE_REQUIRED_TYPES and self.price is None:
            raise ValueError(f"{self.order_type} requires price")
        payload = {
            "instId": self.inst_id,
            "tdMode": self.td_mode,
            "side": self.side.value,
            "ordType": self.order_type.value,
            "sz": decimal_to_okx_str(self.size),
            "clOrdId": self.client_order_id,
        }
        if self.price is not None:
            payload["px"] = decimal_to_okx_str(self.price)
        return payload


@dataclass(frozen=True)
class OKXCancelOrderRequest:
    inst_id: str
    client_order_id: str | None = None
    exchange_order_id: str | None = None

    def to_payload(self) -> dict[str, str]:
        if not self.client_order_id and not self.exchange_order_id:
            raise ValueError("client_order_id or exchange_order_id is required")
        payload = {"instId": self.inst_id}
        if self.client_order_id:
            payload["clOrdId"] = self.client_order_id
        if self.exchange_order_id:
            payload["ordId"] = self.exchange_order_id
        return payload


def map_okx_order_state(state: str) -> OrderStatus:
    mapping = {
        "live": OrderStatus.ACCEPTED,
        "partially_filled": OrderStatus.PARTIALLY_FILLED,
        "filled": OrderStatus.FILLED,
        "canceled": OrderStatus.CANCELLED,
    }
    return mapping.get(state, OrderStatus.UNKNOWN)


def decimal_to_okx_str(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("Decimal value must be finite")
    return format(value.normalize(), "f")


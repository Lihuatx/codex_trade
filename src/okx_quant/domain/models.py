"""Core trading domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from okx_quant.domain.enums import OrderSide, OrderStatus, OrderType


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_client_order_id(prefix: str = "oq") -> str:
    return f"{prefix}{utc_now().strftime('%Y%m%d%H%M%S')}{uuid4().hex[:10]}"


@dataclass(frozen=True)
class TradeIntent:
    strategy_id: str
    inst_id: str
    side: OrderSide
    notional: Decimal
    reference_price: Decimal
    reason: str
    created_at: datetime


@dataclass
class Order:
    client_order_id: str
    inst_id: str
    side: OrderSide
    order_type: OrderType
    size: Decimal
    price: Decimal | None
    status: OrderStatus = OrderStatus.CREATED
    exchange_order_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class Fill:
    fill_id: str
    client_order_id: str
    exchange_order_id: str | None
    inst_id: str
    side: OrderSide
    price: Decimal
    size: Decimal
    fee: Decimal
    fee_ccy: str
    filled_at: datetime

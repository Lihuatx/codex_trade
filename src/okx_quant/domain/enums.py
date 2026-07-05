"""Shared trading enums."""

from __future__ import annotations

from enum import StrEnum


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    POST_ONLY = "post_only"
    FOK = "fok"
    IOC = "ioc"


class OrderStatus(StrEnum):
    CREATED = "created"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCEL_PENDING = "cancel_pending"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


ACTIVE_ORDER_STATUSES = {
    OrderStatus.CREATED,
    OrderStatus.SUBMITTED,
    OrderStatus.ACCEPTED,
    OrderStatus.PARTIALLY_FILLED,
    OrderStatus.CANCEL_PENDING,
    OrderStatus.UNKNOWN,
}


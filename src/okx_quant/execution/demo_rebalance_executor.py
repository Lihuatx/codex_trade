"""Helpers for the OKX demo rebalance executor."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from okx_quant.brokers.okx.orders import OKXPlaceOrderRequest
from okx_quant.domain.enums import ACTIVE_ORDER_STATUSES, OrderSide, OrderStatus, OrderType
from okx_quant.domain.instruments import InstrumentRules
from okx_quant.domain.models import TradeIntent
from okx_quant.execution.order_sizer import SizedOrder, size_spot_limit_order_by_quote_notional
from okx_quant.portfolio.rebalance_signal import RiskCappedIntent


@dataclass(frozen=True)
class PreparedDemoOrder:
    trade_intent: TradeIntent
    request: OKXPlaceOrderRequest
    sized_order: SizedOrder


def select_first_actionable_intent(capped_intents: list[RiskCappedIntent]) -> RiskCappedIntent | None:
    for item in capped_intents:
        if item.actionable:
            return item
    return None


def active_local_orders(statuses: dict[str, OrderStatus]) -> dict[str, OrderStatus]:
    return {
        client_order_id: status
        for client_order_id, status in statuses.items()
        if status in ACTIVE_ORDER_STATUSES
    }


def build_passive_post_only_order(
    *,
    capped_intent: RiskCappedIntent,
    trade_intent: TradeIntent,
    rules: InstrumentRules,
    bid: Decimal,
    ask: Decimal,
    price_offset_bps: Decimal,
    client_order_id: str,
) -> PreparedDemoOrder:
    price = passive_limit_price(
        side=capped_intent.intent.side,
        rules=rules,
        bid=bid,
        ask=ask,
        price_offset_bps=price_offset_bps,
    )
    sized = size_spot_limit_order_by_quote_notional(
        rules=rules,
        quote_notional=capped_intent.capped_notional_usdt,
        reference_price=price,
    )
    return PreparedDemoOrder(
        trade_intent=trade_intent,
        request=OKXPlaceOrderRequest(
            inst_id=rules.inst_id,
            side=capped_intent.intent.side,
            order_type=OrderType.POST_ONLY,
            size=sized.size,
            price=price,
            client_order_id=client_order_id,
        ),
        sized_order=sized,
    )


def passive_limit_price(
    *,
    side: OrderSide,
    rules: InstrumentRules,
    bid: Decimal,
    ask: Decimal,
    price_offset_bps: Decimal,
) -> Decimal:
    offset = price_offset_bps / Decimal("10000")
    if side == OrderSide.BUY:
        return rules.round_price(bid * (Decimal("1") - offset))
    if side == OrderSide.SELL:
        return rules.round_price(ask * (Decimal("1") + offset))
    raise ValueError(f"Unsupported side: {side}")

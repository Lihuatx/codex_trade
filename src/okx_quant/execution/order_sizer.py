"""Order sizing based on exchange instrument rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from okx_quant.domain.instruments import InstrumentRules


@dataclass(frozen=True)
class SizedOrder:
    inst_id: str
    size: Decimal
    rounded_notional: Decimal
    reference_price: Decimal


def size_spot_limit_order_by_quote_notional(
    *,
    rules: InstrumentRules,
    quote_notional: Decimal,
    reference_price: Decimal,
) -> SizedOrder:
    if quote_notional <= 0:
        raise ValueError("quote_notional must be positive")
    if reference_price <= 0:
        raise ValueError("reference_price must be positive")

    raw_size = quote_notional / reference_price
    size = rules.round_size(raw_size)
    rules.validate_size(size)
    return SizedOrder(
        inst_id=rules.inst_id,
        size=size,
        rounded_notional=size * reference_price,
        reference_price=reference_price,
    )


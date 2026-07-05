"""Execution cost model for conservative first-pass backtests."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from okx_quant.domain.enums import OrderSide


BPS_DENOMINATOR = Decimal("10000")


@dataclass(frozen=True)
class ExecutionCostModel:
    taker_fee_bps: Decimal
    slippage_bps: Decimal
    spread_bps: Decimal = Decimal("0")

    @property
    def taker_fee_rate(self) -> Decimal:
        return self.taker_fee_bps / BPS_DENOMINATOR

    def fill_price(self, side: OrderSide, reference_price: Decimal) -> Decimal:
        half_spread_bps = self.spread_bps / Decimal("2")
        adjustment = (half_spread_bps + self.slippage_bps) / BPS_DENOMINATOR
        if side == OrderSide.BUY:
            return reference_price * (Decimal("1") + adjustment)
        if side == OrderSide.SELL:
            return reference_price * (Decimal("1") - adjustment)
        raise ValueError(f"Unsupported side: {side}")

    def fee(self, notional: Decimal) -> Decimal:
        return notional * self.taker_fee_rate

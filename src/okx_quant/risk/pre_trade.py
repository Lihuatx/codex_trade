"""Pre-trade risk checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from okx_quant.domain.enums import OrderSide
from okx_quant.domain.models import TradeIntent


@dataclass(frozen=True)
class RiskLimits:
    max_total_crypto_exposure: Decimal
    max_order_notional: Decimal
    max_daily_loss: Decimal
    max_spread_bps: Decimal
    max_price_deviation_bps: Decimal
    stale_market_data_seconds: int
    read_only_mode: bool = True
    kill_switch: bool = False
    reconcile_required: bool = False


@dataclass(frozen=True)
class MarketSnapshot:
    inst_id: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    observed_at: datetime

    @property
    def mid(self) -> Decimal:
        return (self.bid + self.ask) / Decimal("2")

    @property
    def spread_bps(self) -> Decimal:
        if self.mid <= 0:
            return Decimal("Infinity")
        return (self.ask - self.bid) / self.mid * Decimal("10000")


@dataclass(frozen=True)
class PortfolioSnapshot:
    total_crypto_exposure: Decimal
    daily_pnl: Decimal


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)


class PreTradeRiskEngine:
    def __init__(self, limits: RiskLimits) -> None:
        self._limits = limits

    def evaluate(
        self,
        intent: TradeIntent,
        market: MarketSnapshot,
        portfolio: PortfolioSnapshot,
        now: datetime | None = None,
    ) -> RiskDecision:
        now = now or datetime.now(timezone.utc)
        reasons: list[str] = []

        if self._limits.kill_switch:
            reasons.append("kill_switch_enabled")
        if self._limits.read_only_mode:
            reasons.append("read_only_mode")
        if self._limits.reconcile_required:
            reasons.append("reconcile_required")
        if intent.notional > self._limits.max_order_notional:
            reasons.append("max_order_notional_exceeded")
        projected_exposure = portfolio.total_crypto_exposure
        if intent.side == OrderSide.BUY:
            projected_exposure += intent.notional
            if projected_exposure > self._limits.max_total_crypto_exposure:
                reasons.append("max_total_crypto_exposure_exceeded")
        if portfolio.daily_pnl <= -self._limits.max_daily_loss:
            reasons.append("max_daily_loss_exceeded")
        if market.spread_bps > self._limits.max_spread_bps:
            reasons.append("max_spread_bps_exceeded")
        if _age_seconds(now, market.observed_at) > self._limits.stale_market_data_seconds:
            reasons.append("stale_market_data")

        deviation_bps = _abs_bps(intent.reference_price, market.last)
        if deviation_bps > self._limits.max_price_deviation_bps:
            reasons.append("max_price_deviation_bps_exceeded")

        return RiskDecision(approved=not reasons, reasons=tuple(reasons))


def _age_seconds(now: datetime, observed_at: datetime) -> float:
    return (now - observed_at).total_seconds()


def _abs_bps(reference: Decimal, value: Decimal) -> Decimal:
    if reference <= 0:
        return Decimal("Infinity")
    return abs(value - reference) / reference * Decimal("10000")

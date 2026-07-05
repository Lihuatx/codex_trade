"""Read-only threshold rebalance signal generation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from okx_quant.domain.enums import OrderSide


@dataclass(frozen=True)
class PortfolioAsset:
    asset: str
    quantity: Decimal
    price_usdt: Decimal

    @property
    def value_usdt(self) -> Decimal:
        return self.quantity * self.price_usdt


@dataclass(frozen=True)
class RebalanceIntent:
    asset: str
    side: OrderSide
    notional_usdt: Decimal
    current_weight: Decimal
    target_weight: Decimal
    reason: str

    def as_dict(self) -> dict[str, str]:
        return {
            "asset": self.asset,
            "side": self.side.value,
            "notional_usdt": str(self.notional_usdt),
            "current_weight": str(self.current_weight),
            "target_weight": str(self.target_weight),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class RebalanceSignal:
    equity_usdt: Decimal
    weights: dict[str, Decimal]
    target_weights: dict[str, Decimal]
    intents: list[RebalanceIntent]

    def as_dict(self) -> dict[str, object]:
        return {
            "equity_usdt": str(self.equity_usdt),
            "weights": {asset: str(weight) for asset, weight in self.weights.items()},
            "target_weights": {asset: str(weight) for asset, weight in self.target_weights.items()},
            "intents": [intent.as_dict() for intent in self.intents],
        }


def generate_rebalance_signal(
    *,
    cash_usdt: Decimal,
    assets: list[PortfolioAsset],
    target_weights: dict[str, Decimal],
    threshold: Decimal,
    min_trade_notional: Decimal,
) -> RebalanceSignal:
    _validate_target_weights(target_weights)
    equity = cash_usdt + sum(asset.value_usdt for asset in assets)
    if equity <= 0:
        raise ValueError("portfolio equity must be positive")

    asset_by_name = {asset.asset: asset for asset in assets}
    weights = {"USDT": cash_usdt / equity}
    for asset in assets:
        weights[asset.asset] = asset.value_usdt / equity

    intents: list[RebalanceIntent] = []
    for asset, target_weight in target_weights.items():
        if asset == "USDT":
            continue
        current_weight = weights.get(asset, Decimal("0"))
        deviation = current_weight - target_weight
        if abs(deviation) < threshold:
            continue
        notional = abs(deviation) * equity
        if notional < min_trade_notional:
            continue
        side = OrderSide.SELL if deviation > 0 else OrderSide.BUY
        if side == OrderSide.SELL and asset_by_name.get(asset, PortfolioAsset(asset, Decimal("0"), Decimal("0"))).quantity <= 0:
            continue
        intents.append(
            RebalanceIntent(
                asset=asset,
                side=side,
                notional_usdt=notional,
                current_weight=current_weight,
                target_weight=target_weight,
                reason="threshold_deviation",
            )
        )

    return RebalanceSignal(equity, weights, target_weights, intents)


def _validate_target_weights(target_weights: dict[str, Decimal]) -> None:
    total = sum(target_weights.values(), Decimal("0"))
    if total != Decimal("1"):
        raise ValueError(f"target weights must sum to 1, got {total}")
    if "USDT" not in target_weights:
        raise ValueError("target weights must include USDT")


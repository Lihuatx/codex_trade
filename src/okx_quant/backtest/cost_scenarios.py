"""Named fee/spread/slippage assumptions for sensitivity checks."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from okx_quant.backtest.cost_model import ExecutionCostModel


@dataclass(frozen=True)
class CostScenario:
    name: str
    taker_fee_bps: Decimal
    spread_bps: Decimal
    slippage_bps: Decimal

    def cost_model(self) -> ExecutionCostModel:
        return ExecutionCostModel(
            taker_fee_bps=self.taker_fee_bps,
            spread_bps=self.spread_bps,
            slippage_bps=self.slippage_bps,
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "taker_fee_bps": str(self.taker_fee_bps),
            "spread_bps": str(self.spread_bps),
            "slippage_bps": str(self.slippage_bps),
        }


DEFAULT_COST_SCENARIOS = (
    CostScenario("optimistic", Decimal("8"), Decimal("2"), Decimal("2")),
    CostScenario("neutral", Decimal("10"), Decimal("5"), Decimal("5")),
    CostScenario("pessimistic", Decimal("15"), Decimal("10"), Decimal("15")),
)


def parse_cost_scenarios(raw_items: Iterable[str] | None) -> tuple[CostScenario, ...]:
    if not raw_items:
        return DEFAULT_COST_SCENARIOS
    return tuple(parse_cost_scenario(item) for item in raw_items)


def parse_cost_scenario(raw: str) -> CostScenario:
    parts = [part.strip() for part in raw.split(":")]
    if len(parts) != 4 or not all(parts):
        raise ValueError("cost scenario must be name:taker_fee_bps:spread_bps:slippage_bps")
    return CostScenario(
        name=parts[0],
        taker_fee_bps=Decimal(parts[1]),
        spread_bps=Decimal(parts[2]),
        slippage_bps=Decimal(parts[3]),
    )

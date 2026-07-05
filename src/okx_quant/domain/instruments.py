"""Instrument trading rules.

OKX exposes tick size, lot size, and minimum size in product metadata.
Keep all price and size handling in Decimal so order rounding is explicit.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN


@dataclass(frozen=True)
class InstrumentRules:
    inst_id: str
    base_ccy: str
    quote_ccy: str
    tick_size: Decimal
    lot_size: Decimal
    min_size: Decimal

    @classmethod
    def from_okx(cls, payload: dict[str, str]) -> "InstrumentRules":
        return cls(
            inst_id=payload["instId"],
            base_ccy=payload.get("baseCcy", ""),
            quote_ccy=payload.get("quoteCcy", ""),
            tick_size=Decimal(payload["tickSz"]),
            lot_size=Decimal(payload["lotSz"]),
            min_size=Decimal(payload["minSz"]),
        )

    def round_price(self, price: Decimal) -> Decimal:
        return _round_to_step(price, self.tick_size)

    def round_size(self, size: Decimal) -> Decimal:
        return _round_to_step(size, self.lot_size)

    def validate_size(self, size: Decimal) -> None:
        if size < self.min_size:
            raise ValueError(f"{self.inst_id} size {size} is below min_size {self.min_size}")
        rounded = self.round_size(size)
        if rounded != size:
            raise ValueError(f"{self.inst_id} size {size} does not match lot_size {self.lot_size}")


def _round_to_step(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        raise ValueError("step must be positive")
    units = (value / step).to_integral_value(rounding=ROUND_DOWN)
    return units * step


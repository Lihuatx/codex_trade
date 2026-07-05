from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from okx_quant.domain.enums import OrderSide
from okx_quant.domain.models import TradeIntent
from okx_quant.risk.pre_trade import MarketSnapshot, PortfolioSnapshot, PreTradeRiskEngine, RiskLimits


class PreTradeRiskEngineTests(unittest.TestCase):
    def test_read_only_rejects_order(self) -> None:
        now = datetime.now(timezone.utc)
        engine = PreTradeRiskEngine(
            RiskLimits(
                max_total_crypto_exposure=Decimal("300"),
                max_order_notional=Decimal("20"),
                max_daily_loss=Decimal("10"),
                max_spread_bps=Decimal("20"),
                max_price_deviation_bps=Decimal("30"),
                stale_market_data_seconds=10,
                read_only_mode=True,
            )
        )

        decision = engine.evaluate(_intent(now), _market(now), PortfolioSnapshot(Decimal("0"), Decimal("0")), now)

        self.assertFalse(decision.approved)
        self.assertIn("read_only_mode", decision.reasons)

    def test_approves_within_limits(self) -> None:
        now = datetime.now(timezone.utc)
        engine = PreTradeRiskEngine(
            RiskLimits(
                max_total_crypto_exposure=Decimal("300"),
                max_order_notional=Decimal("20"),
                max_daily_loss=Decimal("10"),
                max_spread_bps=Decimal("20"),
                max_price_deviation_bps=Decimal("30"),
                stale_market_data_seconds=10,
                read_only_mode=False,
            )
        )

        decision = engine.evaluate(_intent(now), _market(now), PortfolioSnapshot(Decimal("100"), Decimal("0")), now)

        self.assertTrue(decision.approved)

    def test_rejects_stale_market_data(self) -> None:
        now = datetime.now(timezone.utc)
        engine = PreTradeRiskEngine(
            RiskLimits(
                max_total_crypto_exposure=Decimal("300"),
                max_order_notional=Decimal("20"),
                max_daily_loss=Decimal("10"),
                max_spread_bps=Decimal("20"),
                max_price_deviation_bps=Decimal("30"),
                stale_market_data_seconds=10,
                read_only_mode=False,
            )
        )
        stale_market = _market(now - timedelta(seconds=11))

        decision = engine.evaluate(_intent(now), stale_market, PortfolioSnapshot(Decimal("0"), Decimal("0")), now)

        self.assertFalse(decision.approved)
        self.assertIn("stale_market_data", decision.reasons)

    def test_sell_does_not_increase_crypto_exposure(self) -> None:
        now = datetime.now(timezone.utc)
        engine = PreTradeRiskEngine(
            RiskLimits(
                max_total_crypto_exposure=Decimal("300"),
                max_order_notional=Decimal("20"),
                max_daily_loss=Decimal("10"),
                max_spread_bps=Decimal("20"),
                max_price_deviation_bps=Decimal("30"),
                stale_market_data_seconds=10,
                read_only_mode=False,
            )
        )
        intent = TradeIntent(
            strategy_id="test",
            inst_id="BTC-USDT",
            side=OrderSide.SELL,
            notional=Decimal("10"),
            reference_price=Decimal("100"),
            reason="unit-test",
            created_at=now,
        )

        decision = engine.evaluate(intent, _market(now), PortfolioSnapshot(Decimal("295"), Decimal("0")), now)

        self.assertTrue(decision.approved)

    def test_sell_can_reduce_exposure_even_when_current_exposure_is_over_limit(self) -> None:
        now = datetime.now(timezone.utc)
        engine = PreTradeRiskEngine(
            RiskLimits(
                max_total_crypto_exposure=Decimal("30"),
                max_order_notional=Decimal("20"),
                max_daily_loss=Decimal("10"),
                max_spread_bps=Decimal("20"),
                max_price_deviation_bps=Decimal("30"),
                stale_market_data_seconds=10,
                read_only_mode=False,
            )
        )
        intent = TradeIntent(
            strategy_id="test",
            inst_id="BTC-USDT",
            side=OrderSide.SELL,
            notional=Decimal("10"),
            reference_price=Decimal("100"),
            reason="unit-test",
            created_at=now,
        )

        decision = engine.evaluate(intent, _market(now), PortfolioSnapshot(Decimal("35"), Decimal("0")), now)

        self.assertTrue(decision.approved)

    def test_buy_rejects_when_projected_exposure_exceeds_limit(self) -> None:
        now = datetime.now(timezone.utc)
        engine = PreTradeRiskEngine(
            RiskLimits(
                max_total_crypto_exposure=Decimal("30"),
                max_order_notional=Decimal("20"),
                max_daily_loss=Decimal("10"),
                max_spread_bps=Decimal("20"),
                max_price_deviation_bps=Decimal("30"),
                stale_market_data_seconds=10,
                read_only_mode=False,
            )
        )

        decision = engine.evaluate(_intent(now), _market(now), PortfolioSnapshot(Decimal("25"), Decimal("0")), now)

        self.assertFalse(decision.approved)
        self.assertIn("max_total_crypto_exposure_exceeded", decision.reasons)


def _intent(now: datetime) -> TradeIntent:
    return TradeIntent(
        strategy_id="test",
        inst_id="BTC-USDT",
        side=OrderSide.BUY,
        notional=Decimal("10"),
        reference_price=Decimal("100"),
        reason="unit-test",
        created_at=now,
    )


def _market(now: datetime) -> MarketSnapshot:
    return MarketSnapshot(
        inst_id="BTC-USDT",
        bid=Decimal("99.95"),
        ask=Decimal("100.05"),
        last=Decimal("100"),
        observed_at=now,
    )


if __name__ == "__main__":
    unittest.main()

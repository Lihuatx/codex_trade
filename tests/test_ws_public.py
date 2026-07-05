from datetime import datetime, timezone
import unittest

from okx_quant.brokers.okx.ws_public import PublicWSMessage, PublicWSSubscription, build_subscribe_message


class OKXPublicWSTests(unittest.TestCase):
    def test_build_subscribe_message(self) -> None:
        message = build_subscribe_message(
            [
                PublicWSSubscription("tickers", "BTC-USDT"),
                PublicWSSubscription("books5", "BTC-USDT"),
            ]
        )

        self.assertEqual(message["op"], "subscribe")
        self.assertEqual(
            message["args"],
            [
                {"channel": "tickers", "instId": "BTC-USDT"},
                {"channel": "books5", "instId": "BTC-USDT"},
            ],
        )

    def test_public_message_channel_and_inst_id(self) -> None:
        msg = PublicWSMessage(
            received_at=datetime.now(timezone.utc),
            payload={"arg": {"channel": "trades", "instId": "BTC-USDT"}, "data": []},
        )

        self.assertEqual(msg.channel, "trades")
        self.assertEqual(msg.inst_id, "BTC-USDT")


if __name__ == "__main__":
    unittest.main()


import unittest

from okx_quant.brokers.okx.ws_private import (
    OKXWSPrivateAuth,
    PrivateWSSubscription,
    build_login_message,
    build_private_subscribe_message,
)


class OKXPrivateWSTests(unittest.TestCase):
    def test_build_login_message(self) -> None:
        message = build_login_message(OKXWSPrivateAuth("key", "secret", "pass"), timestamp="1700000000")

        self.assertEqual(message["op"], "login")
        arg = message["args"][0]
        self.assertEqual(arg["apiKey"], "key")
        self.assertEqual(arg["passphrase"], "pass")
        self.assertEqual(arg["timestamp"], "1700000000")
        self.assertTrue(arg["sign"])

    def test_build_private_subscribe_message(self) -> None:
        message = build_private_subscribe_message([PrivateWSSubscription(channel="orders", inst_type="ANY")])

        self.assertEqual(message, {"op": "subscribe", "args": [{"channel": "orders", "instType": "ANY"}]})


if __name__ == "__main__":
    unittest.main()


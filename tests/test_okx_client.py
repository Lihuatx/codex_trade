import unittest

from okx_quant.brokers.okx.client import build_request_path


class OKXClientTests(unittest.TestCase):
    def test_build_request_path_without_params_has_no_trailing_question_mark(self) -> None:
        self.assertEqual(build_request_path("/api/v5/account/balance", {}), "/api/v5/account/balance")

    def test_build_request_path_with_params(self) -> None:
        self.assertEqual(
            build_request_path("/api/v5/account/trade-fee", {"instType": "SPOT"}),
            "/api/v5/account/trade-fee?instType=SPOT",
        )


if __name__ == "__main__":
    unittest.main()


import os
import unittest
from unittest.mock import patch

from okx_quant.brokers.okx.client import OKX_REST_BASE_URL, OKXRestClient, build_request_path


class OKXClientTests(unittest.TestCase):
    def test_default_rest_base_url_uses_official_openapi_domain(self) -> None:
        self.assertEqual(OKX_REST_BASE_URL, "https://openapi.okx.com")
        self.assertEqual(OKXRestClient().base_url, "https://openapi.okx.com")

    def test_rest_base_url_can_be_overridden_by_environment(self) -> None:
        old_value = os.environ.get("OKX_REST_BASE_URL")
        os.environ["OKX_REST_BASE_URL"] = "https://example.test/"
        try:
            self.assertEqual(OKXRestClient().base_url, "https://example.test")
        finally:
            if old_value is None:
                os.environ.pop("OKX_REST_BASE_URL", None)
            else:
                os.environ["OKX_REST_BASE_URL"] = old_value

    def test_build_request_path_without_params_has_no_trailing_question_mark(self) -> None:
        self.assertEqual(build_request_path("/api/v5/account/balance", {}), "/api/v5/account/balance")

    def test_build_request_path_with_params(self) -> None:
        self.assertEqual(
            build_request_path("/api/v5/account/trade-fee", {"instType": "SPOT"}),
            "/api/v5/account/trade-fee?instType=SPOT",
        )

    def test_get_public_instruments_can_scope_to_inst_id(self) -> None:
        client = OKXRestClient()

        with patch.object(OKXRestClient, "_get", return_value={"code": "0", "data": []}) as mocked_get:
            client.get_public_instruments("SPOT", inst_id="BTC-USDT")

        mocked_get.assert_called_once_with("/api/v5/public/instruments", {"instType": "SPOT", "instId": "BTC-USDT"})


if __name__ == "__main__":
    unittest.main()

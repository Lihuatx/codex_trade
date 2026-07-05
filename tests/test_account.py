from decimal import Decimal
import unittest

from okx_quant.domain.account import parse_okx_account_balances


class AccountParsingTests(unittest.TestCase):
    def test_parse_okx_account_balances(self) -> None:
        payload = {
            "code": "0",
            "data": [
                {
                    "details": [
                        {
                            "ccy": "USDT",
                            "eq": "100.5",
                            "availBal": "99.5",
                            "frozenBal": "1",
                        }
                    ]
                }
            ],
        }

        balances = parse_okx_account_balances(payload)

        self.assertEqual(len(balances), 1)
        self.assertEqual(balances[0].ccy, "USDT")
        self.assertEqual(balances[0].equity, Decimal("100.5"))
        self.assertEqual(balances[0].available, Decimal("99.5"))
        self.assertEqual(balances[0].frozen, Decimal("1"))


if __name__ == "__main__":
    unittest.main()


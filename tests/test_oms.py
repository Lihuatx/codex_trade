import unittest

from okx_quant.domain.enums import OrderStatus
from okx_quant.oms.state_machine import InvalidOrderTransition, transition_order_status


class OrderStateMachineTests(unittest.TestCase):
    def test_valid_transition(self) -> None:
        result = transition_order_status(OrderStatus.CREATED, OrderStatus.SUBMITTED)

        self.assertEqual(result.previous, OrderStatus.CREATED)
        self.assertEqual(result.next, OrderStatus.SUBMITTED)

    def test_terminal_status_rejects_transition(self) -> None:
        with self.assertRaises(InvalidOrderTransition):
            transition_order_status(OrderStatus.FILLED, OrderStatus.CANCELLED)

    def test_unknown_can_reconcile_to_final_state(self) -> None:
        result = transition_order_status(OrderStatus.UNKNOWN, OrderStatus.FILLED)

        self.assertEqual(result.next, OrderStatus.FILLED)

    def test_exchange_can_cancel_live_order_without_local_cancel_pending(self) -> None:
        result = transition_order_status(OrderStatus.ACCEPTED, OrderStatus.CANCELLED)

        self.assertEqual(result.next, OrderStatus.CANCELLED)

    def test_exchange_can_cancel_partially_filled_order(self) -> None:
        result = transition_order_status(OrderStatus.PARTIALLY_FILLED, OrderStatus.CANCELLED)

        self.assertEqual(result.next, OrderStatus.CANCELLED)


if __name__ == "__main__":
    unittest.main()

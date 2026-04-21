import unittest

from claude_usage_meter.models import AlertState


class AlertStateTests(unittest.TestCase):
    def test_alert_once_while_above_threshold(self) -> None:
        state = AlertState()

        self.assertFalse(state.should_fire(79, 80))
        self.assertTrue(state.should_fire(80, 80))
        self.assertFalse(state.should_fire(90, 80))

    def test_alert_rearms_after_drop_below_threshold(self) -> None:
        state = AlertState()

        self.assertTrue(state.should_fire(85, 80))
        self.assertFalse(state.should_fire(84, 80))
        self.assertFalse(state.should_fire(20, 80))
        self.assertTrue(state.should_fire(82, 80))


if __name__ == "__main__":
    unittest.main()

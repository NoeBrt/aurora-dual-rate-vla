import unittest

from aurora.safety_critic import SafetyCritic, SafetyObservation
from aurora.types import IntentFlag


def _chunk() -> tuple[tuple[float, ...], ...]:
    return tuple((0.1,) * 11 for _ in range(8))


class SafetyCriticTest(unittest.TestCase):
    def test_safety_allows_nominal_action(self) -> None:
        decision = SafetyCritic().evaluate(
            SafetyObservation(force_torque=(1.0, 2.0, 3.0, 0.0, 0.0, 0.0), peer_exclusion_distance=0.8),
            _chunk(),
            intent_age_ms=30.0,
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reasons, ())

    def test_safety_vetoes_stale_intent_and_peer_exclusion(self) -> None:
        decision = SafetyCritic().evaluate(
            SafetyObservation(peer_exclusion_distance=0.2),
            _chunk(),
            intent_age_ms=500.0,
        )

        self.assertFalse(decision.allowed)
        self.assertIn("STALE_INTENT", decision.reasons)
        self.assertIn("PEER_EXCLUSION", decision.reasons)
        self.assertTrue(all(all(value == 0.0 for value in row) for row in decision.action_chunk))

    def test_safety_vetoes_drawer_side_load(self) -> None:
        decision = SafetyCritic().evaluate(
            SafetyObservation(force_torque=(0.0, 35.0, 0.0, 0.0, 0.0, 0.0), intent_flags=int(IntentFlag.DRAWER)),
            _chunk(),
            intent_age_ms=10.0,
        )

        self.assertFalse(decision.allowed)
        self.assertIn("DRAWER_SIDE_LOAD", decision.reasons)


if __name__ == "__main__":
    unittest.main()

from dataclasses import replace
import unittest

from aurora.intent_ring import IntentRing
from aurora.semantic_planner import MockSemanticPlanner, SemanticObservation


class IntentRingTest(unittest.TestCase):
    def test_intent_ring_returns_latest_fresh_record(self) -> None:
        ring = IntentRing(slots=4, ttl_ms=100)
        intent = MockSemanticPlanner().plan(SemanticObservation(language="retrieve the wrench"))
        published = ring.publish(intent, timestamp_ns=1_000_000_000)

        latest = ring.read_latest(now_ns=1_050_000_000)

        self.assertEqual(latest, published)
        self.assertIsNotNone(latest)
        self.assertTrue(latest.validate_crc())

    def test_intent_ring_rejects_stale_record(self) -> None:
        ring = IntentRing(slots=4, ttl_ms=100)
        intent = MockSemanticPlanner().plan(SemanticObservation(language="open the drawer"))
        ring.publish(intent, timestamp_ns=1_000_000_000)

        result = ring.read_latest_result(now_ns=1_250_000_000)

        self.assertIsNone(result.intent)
        self.assertEqual(result.reason, "no_valid_fresh_intent")

    def test_intent_crc_detects_corruption(self) -> None:
        intent = MockSemanticPlanner().plan(SemanticObservation(language="handoff flashlight"))
        stamped = intent.with_publish_metadata(seq=1, timestamp_ns=1_000_000_000)
        corrupted = replace(stamped, semantic_latent=(0.9,) + stamped.semantic_latent[1:])

        self.assertTrue(stamped.validate_crc())
        self.assertFalse(corrupted.validate_crc())


if __name__ == "__main__":
    unittest.main()

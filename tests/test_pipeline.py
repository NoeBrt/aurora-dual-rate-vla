import unittest

from aurora.pipeline import AuroraPipeline
from aurora.reactive_controller import ControllerInput
from aurora.safety_critic import SafetyObservation
from aurora.semantic_planner import SemanticObservation
from aurora.types import IntentFlag


class PipelineTest(unittest.TestCase):
    def test_pipeline_runs_handoff_drawer_tool_command(self) -> None:
        pipeline = AuroraPipeline()
        intent = pipeline.publish_semantics(
            SemanticObservation(language="handoff the flashlight, open the drawer, retrieve the wrench")
        )

        step = pipeline.control_step(ControllerInput(), SafetyObservation(peer_exclusion_distance=0.9))

        self.assertIsNotNone(step.intent)
        self.assertIn(IntentFlag.HANDOFF, intent.flags)
        self.assertIn(IntentFlag.DRAWER, intent.flags)
        self.assertIn(IntentFlag.TOOL, intent.flags)
        self.assertTrue(step.safety_decision.allowed)
        self.assertEqual(len(step.safety_decision.action_chunk), 8)

    def test_pipeline_holds_without_fresh_intent(self) -> None:
        pipeline = AuroraPipeline()

        step = pipeline.control_step(ControllerInput(), SafetyObservation())

        self.assertIsNone(step.intent)
        self.assertFalse(step.safety_decision.allowed)
        self.assertIn("EMPTY", step.safety_decision.reasons)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from dataclasses import dataclass

from aurora.intent_ring import IntentRing
from aurora.reactive_controller import ControllerInput, ControllerOutput, ReactiveController
from aurora.safety_critic import SafetyCritic, SafetyDecision, SafetyObservation
from aurora.semantic_planner import MockSemanticPlanner, SemanticObservation
from aurora.types import AuroraIntent, monotonic_ns


@dataclass(frozen=True)
class PipelineStep:
    intent: AuroraIntent | None
    controller_output: ControllerOutput | None
    safety_decision: SafetyDecision
    ring_reason: str


class AuroraPipeline:
    """Single-robot reference pipeline wiring System 2, ring, System 1, and safety."""

    def __init__(
        self,
        planner: MockSemanticPlanner | None = None,
        controller: ReactiveController | None = None,
        safety: SafetyCritic | None = None,
        ring: IntentRing | None = None,
    ) -> None:
        self.planner = planner or MockSemanticPlanner()
        self.controller = controller or ReactiveController()
        self.safety = safety or SafetyCritic()
        self.ring = ring or IntentRing()

    def publish_semantics(self, obs: SemanticObservation, timestamp_ns: int | None = None) -> AuroraIntent:
        return self.ring.publish(self.planner.plan(obs), timestamp_ns=timestamp_ns)

    def control_step(
        self,
        ctrl_in: ControllerInput,
        safety_obs: SafetyObservation,
        now_ns: int | None = None,
    ) -> PipelineStep:
        now = monotonic_ns() if now_ns is None else now_ns
        result = self.ring.read_latest_result(now)
        if result.intent is None:
            empty_chunk = tuple((0.0,) * 11 for _ in range(self.controller.chunk_horizon))
            decision = SafetyDecision(False, (result.reason.upper(),), empty_chunk)
            return PipelineStep(None, None, decision, result.reason)

        output = self.controller.predict(ctrl_in, result.intent)
        safety_with_flags = SafetyObservation(
            force_torque=safety_obs.force_torque,
            peer_gripper_unknown=safety_obs.peer_gripper_unknown,
            peer_exclusion_distance=safety_obs.peer_exclusion_distance,
            occ_uncertainty=safety_obs.occ_uncertainty,
            intent_flags=result.intent.intent_flags,
        )
        decision = self.safety.evaluate(
            safety_with_flags,
            output.action_chunk,
            result.intent.age_ms(now),
        )
        return PipelineStep(result.intent, output, decision, result.reason)

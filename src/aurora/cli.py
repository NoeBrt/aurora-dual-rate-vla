from __future__ import annotations

import argparse
import json

from aurora.pipeline import AuroraPipeline
from aurora.reactive_controller import ControllerInput
from aurora.safety_critic import SafetyObservation
from aurora.semantic_planner import SemanticObservation


def run_demo(language: str) -> dict[str, object]:
    pipeline = AuroraPipeline()
    intent = pipeline.publish_semantics(SemanticObservation(language=language))
    step = pipeline.control_step(
        ControllerInput(),
        SafetyObservation(peer_exclusion_distance=0.8),
    )
    first_action = step.safety_decision.action_chunk[0]
    return {
        "language": language,
        "intent_seq": intent.seq,
        "intent_flags": int(intent.intent_flags),
        "ring_reason": step.ring_reason,
        "allowed": step.safety_decision.allowed,
        "veto_reasons": list(step.safety_decision.reasons),
        "first_action": [round(v, 5) for v in first_action],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the AURORA reference pipeline demo.")
    parser.add_argument(
        "--language",
        default="Robot A hold the flashlight while Robot B opens the drawer and retrieves the wrench",
    )
    args = parser.parse_args(argv)
    print(json.dumps(run_demo(args.language), indent=2, sort_keys=True))
    return 0

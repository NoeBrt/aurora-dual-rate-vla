"""AURORA reference implementation.

This package implements the runtime boundary and control scaffolding described
in the AURORA paper draft. It intentionally ships with deterministic mock
models instead of private trained checkpoints.
"""

from aurora.intent_ring import IntentRing
from aurora.pipeline import AuroraPipeline
from aurora.reactive_controller import ReactiveController
from aurora.safety_critic import SafetyCritic
from aurora.semantic_planner import MockSemanticPlanner
from aurora.types import AuroraIntent, IntentFlag

__all__ = [
    "AuroraIntent",
    "AuroraPipeline",
    "IntentFlag",
    "IntentRing",
    "MockSemanticPlanner",
    "ReactiveController",
    "SafetyCritic",
]

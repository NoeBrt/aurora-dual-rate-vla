from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math

from aurora.types import AuroraIntent, IntentFlag


@dataclass(frozen=True)
class SemanticObservation:
    language: str
    proprio_summary: tuple[float, ...] = (0.0,) * 48
    peer_summary: tuple[float, ...] = (0.0,) * 64
    camera_uncertainty_ms: float = 4.0
    object_slot_count: int = 8


class MockSemanticPlanner:
    """Deterministic stand-in for the 7B semantic planner.

    The mock maps language to intent flags and produces a stable latent from a
    hash of the observation. Replace this class with a real VLA adapter while
    preserving the AuroraIntent contract.
    """

    def __init__(self, planner_rate_hz: float = 7.5) -> None:
        self.planner_rate_hz = planner_rate_hz

    def plan(self, obs: SemanticObservation) -> AuroraIntent:
        flags = self._flags_from_language(obs.language)
        latent = self._latent(obs.language, 256)
        uncertainty0 = min(1.0, max(0.0, obs.camera_uncertainty_ms / 60.0))
        uncertainty = (uncertainty0, 0.12, 0.18, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        goal_poses = self._goal_pose_hypotheses(latent)
        return AuroraIntent(
            intent_flags=int(flags),
            object_slot_count=obs.object_slot_count,
            semantic_latent=latent,
            goal_poses=goal_poses,
            uncertainty=uncertainty,
            safety_bounds=(0.42, 36.0, 52.0, 80.0) + (0.0,) * 28,
        )

    @staticmethod
    def _flags_from_language(language: str) -> IntentFlag:
        text = language.lower()
        flags = IntentFlag.NONE
        if any(word in text for word in ("handoff", "hand off", "pass", "give")):
            flags |= IntentFlag.HANDOFF
        if any(word in text for word in ("clear", "clutter", "debris")):
            flags |= IntentFlag.CLEAR
        if "drawer" in text:
            flags |= IntentFlag.DRAWER
        if any(word in text for word in ("tool", "wrench", "screwdriver", "flashlight", "prybar")):
            flags |= IntentFlag.TOOL
        if any(word in text for word in ("recover", "stuck", "slip", "retry")):
            flags |= IntentFlag.RECOVERY
        return flags or IntentFlag.TOOL

    @staticmethod
    def _latent(text: str, length: int) -> tuple[float, ...]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        while len(values) < length:
            for byte in digest:
                values.append((byte / 127.5) - 1.0)
                if len(values) == length:
                    break
            digest = hashlib.sha256(digest).digest()
        return tuple(values)

    @staticmethod
    def _goal_pose_hypotheses(latent: tuple[float, ...]) -> tuple[float, ...]:
        poses: list[float] = []
        for idx in range(6):
            x = 0.25 + 0.05 * latent[idx]
            y = 0.05 * latent[idx + 6]
            z = 0.35 + 0.04 * latent[idx + 12]
            yaw = math.pi * latent[idx + 18]
            poses.extend([x, y, z, 0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)])
        return tuple(poses)

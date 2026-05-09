from __future__ import annotations

from dataclasses import dataclass
import math

from aurora.types import IntentFlag


@dataclass(frozen=True)
class SafetyObservation:
    force_torque: tuple[float, ...] = (0.0,) * 6
    peer_gripper_unknown: bool = False
    peer_exclusion_distance: float = 1.0
    occ_uncertainty: float = 0.05
    intent_flags: int = 0


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    reasons: tuple[str, ...]
    action_chunk: tuple[tuple[float, ...], ...]


class SafetyCritic:
    """Controller-side hard veto and clipping layer."""

    def __init__(
        self,
        wrist_force_soft_lateral_n: float = 36.0,
        wrist_force_soft_axial_n: float = 52.0,
        wrist_force_hard_n: float = 80.0,
        peer_exclusion_radius_m: float = 0.42,
        stale_intent_fallback_ms: float = 420.0,
        occ_uncertainty_limit: float = 0.48,
        drawer_side_load_n: float = 31.0,
    ) -> None:
        self.wrist_force_soft_lateral_n = wrist_force_soft_lateral_n
        self.wrist_force_soft_axial_n = wrist_force_soft_axial_n
        self.wrist_force_hard_n = wrist_force_hard_n
        self.peer_exclusion_radius_m = peer_exclusion_radius_m
        self.stale_intent_fallback_ms = stale_intent_fallback_ms
        self.occ_uncertainty_limit = occ_uncertainty_limit
        self.drawer_side_load_n = drawer_side_load_n

    def evaluate(
        self,
        obs: SafetyObservation,
        action_chunk: tuple[tuple[float, ...], ...],
        intent_age_ms: float,
    ) -> SafetyDecision:
        reasons: list[str] = []
        force = obs.force_torque + (0.0,) * max(0, 6 - len(obs.force_torque))
        lateral = math.sqrt(force[0] * force[0] + force[1] * force[1])
        axial = abs(force[2])
        max_force = max(abs(v) for v in force[:6])
        flags = IntentFlag(obs.intent_flags)

        if lateral > self.wrist_force_soft_lateral_n:
            reasons.append("FORCE_LATERAL_SOFT")
        if axial > self.wrist_force_soft_axial_n:
            reasons.append("FORCE_AXIAL_SOFT")
        if max_force > self.wrist_force_hard_n:
            reasons.append("FORCE_HARD")
        if obs.peer_gripper_unknown:
            reasons.append("PEER_GRIPPER_UNKNOWN")
        if obs.peer_exclusion_distance < self.peer_exclusion_radius_m:
            reasons.append("PEER_EXCLUSION")
        if intent_age_ms > self.stale_intent_fallback_ms:
            reasons.append("STALE_INTENT")
        if obs.occ_uncertainty > self.occ_uncertainty_limit:
            reasons.append("OCC_UNCERTAINTY")
        if IntentFlag.DRAWER in flags and abs(force[1]) > self.drawer_side_load_n:
            reasons.append("DRAWER_SIDE_LOAD")

        if reasons:
            return SafetyDecision(False, tuple(reasons), self._hold_chunk(action_chunk))
        return SafetyDecision(True, tuple(), self._clip_chunk(action_chunk))

    @staticmethod
    def _hold_chunk(action_chunk: tuple[tuple[float, ...], ...]) -> tuple[tuple[float, ...], ...]:
        return tuple(tuple(0.0 for _ in row) for row in action_chunk)

    @staticmethod
    def _clip_chunk(action_chunk: tuple[tuple[float, ...], ...]) -> tuple[tuple[float, ...], ...]:
        clipped: list[tuple[float, ...]] = []
        for row in action_chunk:
            out = list(row)
            if len(out) >= 2:
                out[0] = max(-0.25, min(0.25, out[0]))
                out[1] = max(-0.18, min(0.18, out[1]))
            if len(out) >= 10:
                out[9] = max(-0.2, min(0.2, out[9]))
            clipped.append(tuple(out))
        return tuple(clipped)

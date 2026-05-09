from __future__ import annotations

from dataclasses import dataclass
import math

from aurora.types import AuroraIntent, IntentFlag


ACTION_DIM = 11


@dataclass(frozen=True)
class ControllerInput:
    proprio: tuple[float, ...] = (0.0,) * 96
    action_history: tuple[tuple[float, ...], ...] = ((0.0,) * ACTION_DIM,) * 16
    force_torque: tuple[float, ...] = (0.0,) * 6
    peer_state: tuple[float, ...] = (0.0,) * 72
    occ_uncertainty: float = 0.05
    safety_mask: tuple[bool, ...] = (False,) * 32


@dataclass(frozen=True)
class ControllerOutput:
    action_chunk: tuple[tuple[float, ...], ...]
    stop_logits: tuple[float, float, float, float]
    critic_margin: tuple[float, ...]


class ReactiveController:
    """Fast deterministic controller surrogate for the 88M TRT engine."""

    def __init__(self, chunk_horizon: int = 8, action_dim: int = ACTION_DIM, delay_steps: int = 3) -> None:
        self.chunk_horizon = chunk_horizon
        self.action_dim = action_dim
        self.delay_steps = delay_steps

    def predict(self, ctrl_in: ControllerInput, intent: AuroraIntent) -> ControllerOutput:
        latent = intent.semantic_latent
        flags = intent.flags
        base_speed = 0.09 if IntentFlag.CLEAR in flags else 0.04
        if IntentFlag.HANDOFF in flags:
            base_speed *= 0.55
        if IntentFlag.DRAWER in flags:
            base_speed *= 0.35

        lateral_force = abs(ctrl_in.force_torque[1]) if len(ctrl_in.force_torque) > 1 else 0.0
        force_damping = max(0.15, 1.0 - lateral_force / 45.0)
        delayed = self._delay_compensate(ctrl_in.action_history)

        rows: list[tuple[float, ...]] = []
        for step in range(self.chunk_horizon):
            phase = (step + 1) / self.chunk_horizon
            action = [0.0] * self.action_dim
            action[0] = base_speed * math.tanh(latent[step]) * force_damping
            action[1] = base_speed * 0.5 * math.tanh(latent[step + 8]) * force_damping
            action[2] = 0.08 * math.tanh(latent[step + 16])
            action[3] = 0.018 * math.tanh(latent[step + 24]) * force_damping
            action[4] = 0.018 * math.tanh(latent[step + 32]) * force_damping
            action[5] = 0.014 * math.tanh(latent[step + 40])
            action[6] = 0.035 * math.tanh(latent[step + 48])
            action[7] = 0.035 * math.tanh(latent[step + 56])
            action[8] = 0.035 * math.tanh(latent[step + 64])
            action[9] = self._gripper_delta(flags, phase)
            action[10] = 0.35 if IntentFlag.DRAWER in flags else 0.62
            if step == 0:
                action = [0.65 * a + 0.35 * d for a, d in zip(action, delayed)]
            rows.append(tuple(max(-1.0, min(1.0, a)) for a in action))

        mean_uncertainty = sum(intent.uncertainty[:3]) / 3.0
        stop_logits = (
            -1.0 + mean_uncertainty,
            0.4 if IntentFlag.RECOVERY in flags else -0.2,
            0.7 if IntentFlag.HANDOFF in flags else -0.4,
            0.9 if mean_uncertainty > 0.5 else -0.8,
        )
        margins = tuple(0.18 - 0.02 * idx - mean_uncertainty * 0.05 for idx in range(self.chunk_horizon))
        return ControllerOutput(action_chunk=tuple(rows), stop_logits=stop_logits, critic_margin=margins)

    def _delay_compensate(self, action_history: tuple[tuple[float, ...], ...]) -> tuple[float, ...]:
        if len(action_history) < 2:
            return (0.0,) * self.action_dim
        a0 = tuple(action_history[-1][: self.action_dim])
        a1 = tuple(action_history[-2][: self.action_dim])
        if len(a0) < self.action_dim or len(a1) < self.action_dim:
            return (0.0,) * self.action_dim
        return tuple(a0[i] + self.delay_steps * 0.35 * (a0[i] - a1[i]) for i in range(self.action_dim))

    @staticmethod
    def _gripper_delta(flags: IntentFlag, phase: float) -> float:
        if IntentFlag.HANDOFF in flags:
            return -0.12 if phase > 0.55 else 0.04
        if IntentFlag.TOOL in flags:
            return -0.08 if phase > 0.35 else 0.02
        return 0.0

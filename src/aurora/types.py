from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntFlag
import struct
import time
import zlib


class IntentFlag(IntFlag):
    """Semantic task flags emitted by System 2 and consumed by System 1."""

    NONE = 0
    HANDOFF = 1 << 0
    CLEAR = 1 << 1
    DRAWER = 1 << 2
    TOOL = 1 << 3
    RECOVERY = 1 << 4


def monotonic_ns() -> int:
    return time.monotonic_ns()


def _fixed(values: tuple[float, ...] | list[float] | None, length: int) -> tuple[float, ...]:
    if values is None:
        return (0.0,) * length
    clipped = tuple(float(v) for v in values[:length])
    if len(clipped) < length:
        clipped += (0.0,) * (length - len(clipped))
    return clipped


@dataclass(frozen=True)
class AuroraIntent:
    """Compact planner-controller intent record.

    The production system uses a larger fixed-size shared-memory record with
    object slots and affordance grids. This reference implementation keeps the
    same freshness and integrity contract while carrying the fields needed by
    the demo controller and tests.
    """

    seq: int = 0
    timestamp_ns: int = 0
    intent_flags: int = 0
    object_slot_count: int = 0
    semantic_latent: tuple[float, ...] = (0.0,) * 256
    goal_poses: tuple[float, ...] = (0.0,) * 42
    uncertainty: tuple[float, ...] = (0.0,) * 12
    peer_reachable_bloom: tuple[float, ...] = (0.0,) * 128
    safety_bounds: tuple[float, ...] = (0.0,) * 32
    ttl_ms: int = 420
    crc32: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "semantic_latent", _fixed(self.semantic_latent, 256))
        object.__setattr__(self, "goal_poses", _fixed(self.goal_poses, 42))
        object.__setattr__(self, "uncertainty", _fixed(self.uncertainty, 12))
        object.__setattr__(self, "peer_reachable_bloom", _fixed(self.peer_reachable_bloom, 128))
        object.__setattr__(self, "safety_bounds", _fixed(self.safety_bounds, 32))

    @property
    def flags(self) -> IntentFlag:
        return IntentFlag(self.intent_flags)

    def age_ms(self, now_ns: int | None = None) -> float:
        now = monotonic_ns() if now_ns is None else now_ns
        return max(0.0, (now - self.timestamp_ns) / 1_000_000.0)

    def is_fresh(self, now_ns: int | None = None) -> bool:
        return self.age_ms(now_ns) <= self.ttl_ms

    def payload_without_crc(self) -> bytes:
        header = struct.pack(
            "<QQIII",
            int(self.seq),
            int(self.timestamp_ns),
            int(self.intent_flags),
            int(self.object_slot_count),
            int(self.ttl_ms),
        )
        floats = (
            self.semantic_latent
            + self.goal_poses
            + self.uncertainty
            + self.peer_reachable_bloom
            + self.safety_bounds
        )
        return header + struct.pack(f"<{len(floats)}f", *floats)

    def computed_crc32(self) -> int:
        return zlib.crc32(self.payload_without_crc()) & 0xFFFFFFFF

    def with_crc(self) -> "AuroraIntent":
        return replace(self, crc32=self.computed_crc32())

    def validate_crc(self) -> bool:
        return self.crc32 == self.computed_crc32()

    def with_publish_metadata(
        self,
        *,
        seq: int,
        timestamp_ns: int | None = None,
        ttl_ms: int | None = None,
    ) -> "AuroraIntent":
        stamped = replace(
            self,
            seq=seq,
            timestamp_ns=monotonic_ns() if timestamp_ns is None else timestamp_ns,
            ttl_ms=self.ttl_ms if ttl_ms is None else ttl_ms,
            crc32=0,
        )
        return stamped.with_crc()

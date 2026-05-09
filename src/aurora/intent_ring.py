from __future__ import annotations

from dataclasses import dataclass
import threading

from aurora.types import AuroraIntent, monotonic_ns


@dataclass(frozen=True)
class IntentReadResult:
    intent: AuroraIntent | None
    reason: str


class IntentRing:
    """Small fixed-slot intent ring with production-like integrity checks."""

    def __init__(self, slots: int = 8, ttl_ms: int = 420) -> None:
        if slots < 2:
            raise ValueError("IntentRing requires at least two slots")
        self.slots = slots
        self.ttl_ms = ttl_ms
        self._records: list[AuroraIntent | None] = [None] * slots
        self._write_seq = 0
        self._lock = threading.Lock()

    @property
    def write_seq(self) -> int:
        return self._write_seq

    def publish(self, intent: AuroraIntent, timestamp_ns: int | None = None) -> AuroraIntent:
        with self._lock:
            self._write_seq += 1
            record = intent.with_publish_metadata(
                seq=self._write_seq,
                timestamp_ns=timestamp_ns,
                ttl_ms=self.ttl_ms,
            )
            self._records[self._write_seq % self.slots] = record
            return record

    def read_latest_result(self, now_ns: int | None = None) -> IntentReadResult:
        now = monotonic_ns() if now_ns is None else now_ns
        with self._lock:
            start_seq = self._write_seq
            records = list(self._records)

        if start_seq == 0:
            return IntentReadResult(None, "empty")

        saw_record = False
        for offset in range(min(self.slots, start_seq)):
            seq = start_seq - offset
            candidate = records[seq % self.slots]
            if candidate is None:
                continue
            saw_record = True
            if candidate.seq != seq:
                continue
            if not candidate.validate_crc():
                continue
            if not candidate.is_fresh(now):
                continue
            return IntentReadResult(candidate, "ok")

        if not saw_record:
            return IntentReadResult(None, "empty")
        return IntentReadResult(None, "no_valid_fresh_intent")

    def read_latest(self, now_ns: int | None = None) -> AuroraIntent | None:
        return self.read_latest_result(now_ns).intent

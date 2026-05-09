from __future__ import annotations

from dataclasses import dataclass
import math


HOST_STAMP_PENALTY_NS = 2_000_000


@dataclass(frozen=True)
class Frame:
    camera_id: str
    host_receipt_ns: int
    exposure_midpoint_ns: int
    sequence_id: int
    device_timestamp_ns: int | None = None


@dataclass(frozen=True)
class Timestamp:
    robot_time_ns: int
    uncertainty_ns: int


@dataclass(frozen=True)
class DelayEstimate:
    delay_ns: int
    sigma_ns: int


class USBDelayFilter:
    """EWMA delay estimator for host-stamped USB camera frames."""

    def __init__(self, alpha: float = 0.08, initial_sigma_ns: int = 8_000_000) -> None:
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        self.alpha = alpha
        self.mean_ns: float | None = None
        self.var_ns2 = float(initial_sigma_ns * initial_sigma_ns)
        self.last_sequence_id: int | None = None

    def estimate(
        self,
        host_receipt_ns: int,
        exposure_midpoint_ns: int,
        sequence_id: int,
    ) -> DelayEstimate:
        sample = max(0, host_receipt_ns - exposure_midpoint_ns)
        if self.mean_ns is None:
            self.mean_ns = float(sample)
        else:
            delta = float(sample) - self.mean_ns
            self.mean_ns += self.alpha * delta
            self.var_ns2 = (1.0 - self.alpha) * self.var_ns2 + self.alpha * delta * delta

        if self.last_sequence_id is not None and sequence_id <= self.last_sequence_id:
            self.var_ns2 *= 1.5
        self.last_sequence_id = sequence_id

        return DelayEstimate(int(self.mean_ns), int(math.sqrt(max(0.0, self.var_ns2))))


class CameraClockAligner:
    """Converts camera timestamps into robot-time estimates."""

    def __init__(self, device_to_robot_offset_ns: int = 0) -> None:
        self.device_to_robot_offset_ns = device_to_robot_offset_ns
        self._filters: dict[str, USBDelayFilter] = {}

    def stamp(self, frame: Frame) -> Timestamp:
        if frame.device_timestamp_ns is not None:
            return Timestamp(
                robot_time_ns=frame.device_timestamp_ns + self.device_to_robot_offset_ns,
                uncertainty_ns=500_000,
            )

        delay_filter = self._filters.setdefault(frame.camera_id, USBDelayFilter())
        estimate = delay_filter.estimate(
            frame.host_receipt_ns,
            frame.exposure_midpoint_ns,
            frame.sequence_id,
        )
        return Timestamp(
            robot_time_ns=frame.host_receipt_ns - estimate.delay_ns,
            uncertainty_ns=estimate.sigma_ns + HOST_STAMP_PENALTY_NS,
        )

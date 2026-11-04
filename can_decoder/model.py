from dataclasses import dataclass


@dataclass(frozen=True)
class CaptureContext:
    """Where a frame sits within a triggered capture segment."""

    segment_id: str
    label: str
    phase: str
    relative_ms: int


@dataclass(frozen=True)
class CanFrame:
    timestamp: float
    arbitration_id: int
    data: bytes
    bus: str = ""
    capture: CaptureContext | None = None


@dataclass(frozen=True)
class DecodedSignal:
    timestamp: float
    bus: str
    arbitration_id: int
    message_name: str
    signal_name: str
    value: float | int | str
    unit: str
    capture: CaptureContext | None = None

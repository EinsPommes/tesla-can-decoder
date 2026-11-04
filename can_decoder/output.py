import csv
from collections import Counter
from collections.abc import Iterable
from typing import TextIO

from can_decoder.decoding import DecodeStatistics
from can_decoder.model import CaptureContext, DecodedSignal

_CSV_HEADER = (
    "timestamp", "bus", "id", "message", "signal", "value", "unit",
    "segment", "label", "phase", "relative_ms",
)
_TOP_UNKNOWN_IDS = 10
_SIGNIFICANT_DIGITS = 10


def write_csv(signals: Iterable[DecodedSignal], target: TextIO) -> None:
    writer = csv.writer(target)
    writer.writerow(_CSV_HEADER)
    for signal in signals:
        writer.writerow(
            (
                f"{signal.timestamp:.6f}",
                signal.bus,
                f"0x{signal.arbitration_id:03X}",
                signal.message_name,
                signal.signal_name,
                _format_value(signal.value),
                signal.unit,
                *_capture_columns(signal.capture),
            )
        )


def write_text(signals: Iterable[DecodedSignal], target: TextIO) -> None:
    for signal in signals:
        unit = f" {signal.unit}" if signal.unit else ""
        target.write(
            f"{_capture_prefix(signal.capture)}{signal.timestamp:.6f} 0x{signal.arbitration_id:03X} "
            f"{signal.message_name}.{signal.signal_name} = {_format_value(signal.value)}{unit}\n"
        )


def write_summary(statistics: DecodeStatistics, target: TextIO) -> None:
    target.write(f"Decoded frames: {statistics.decoded_frames}\n")
    _write_id_counts("Unknown IDs (not in DBC)", statistics.unknown_ids, target)
    _write_id_counts("Failed to decode", statistics.failed_ids, target)


def _write_id_counts(title: str, counts: Counter[int], target: TextIO) -> None:
    if not counts:
        return
    target.write(f"{title}: {sum(counts.values())} frames, {len(counts)} IDs\n")
    for arbitration_id, count in counts.most_common(_TOP_UNKNOWN_IDS):
        target.write(f"  0x{arbitration_id:03X}: {count}\n")



def _format_value(value: float | int | str) -> str:
    # DBC scaling (raw * factor) 
    if isinstance(value, float):
        return f"{value:.{_SIGNIFICANT_DIGITS}g}"
    return str(value)


def _capture_columns(capture: CaptureContext | None) -> tuple[str, str, str, str]:
    if capture is None:
        return ("", "", "", "")
    return (capture.segment_id, capture.label, capture.phase, str(capture.relative_ms))


def _capture_prefix(capture: CaptureContext | None) -> str:
    if capture is None:
        return ""
    return f"[{capture.segment_id} {capture.label} {capture.relative_ms:+d}ms] "

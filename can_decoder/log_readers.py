import csv
import re
from collections.abc import Iterator
from pathlib import Path

from can_decoder.model import CanFrame, CaptureContext


_CANDUMP_LINE = re.compile(
    r"^\((?P<timestamp>[\d.]+)\)\s+(?P<bus>\S+)\s+(?P<id>[0-9A-Fa-f]+)#(?P<data>[0-9A-Fa-f]*)\s*$"
)

_CSV_TIMESTAMP_COLUMNS = ("timestamp", "time", "ts")
_CSV_ID_COLUMNS = ("id", "arbitration_id", "can_id", "msgid")
_CSV_DATA_COLUMNS = ("data", "payload", "bytes")
_CSV_BUS_COLUMNS = ("bus", "channel", "interface")
_RESEARCH_CAPTURE_COLUMNS = {"segment_id", "label", "phase", "relative_ms", "snapshot_uptime_ms", "physical_bus", "id", "raw"}


class LogFormatError(Exception):
    pass


def read_frames(log_path: Path) -> Iterator[CanFrame]:
    if log_path.suffix.lower() == ".csv":
        return read_csv(log_path)
    return read_candump(log_path)


def read_candump(log_path: Path) -> Iterator[CanFrame]:
    with log_path.open(encoding="utf-8") as log_file:
        for line_number, line in enumerate(log_file, start=1):
            if not line.strip():
                continue
            match = _CANDUMP_LINE.match(line.strip())
            if match is None:
                raise LogFormatError(f"{log_path}:{line_number}: not a candump line: {line.strip()!r}")
            yield CanFrame(
                timestamp=float(match["timestamp"]),
                arbitration_id=int(match["id"], 16),
                data=bytes.fromhex(match["data"]),
                bus=match["bus"],
            )


def read_csv(log_path: Path) -> Iterator[CanFrame]:
    if _is_research_capture(log_path):
        return read_research_capture(log_path)
    return read_generic_csv(log_path)


def read_research_capture(log_path: Path) -> Iterator[CanFrame]:
    """Read a segmented trigger capture; '#' lines are segment summaries without frame data."""
    with log_path.open(encoding="utf-8", newline="") as log_file:
        data_lines = (line for line in log_file if not line.startswith("#"))
        reader = csv.DictReader(data_lines)
        for row in reader:
            try:
                yield CanFrame(
                    timestamp=int(row["snapshot_uptime_ms"]) / 1000,
                    arbitration_id=_parse_hex_id(row["id"]),
                    data=_parse_hex_bytes(row["raw"]),
                    bus=row["physical_bus"],
                    capture=CaptureContext(
                        segment_id=row["segment_id"],
                        label=row["label"],
                        phase=row["phase"],
                        relative_ms=int(row["relative_ms"]),
                    ),
                )
            except (ValueError, KeyError) as error:
                raise LogFormatError(f"{log_path}: row {reader.line_num}: {error}") from error


def _is_research_capture(log_path: Path) -> bool:
    with log_path.open(encoding="utf-8", newline="") as log_file:
        header = next(csv.reader(log_file), [])
    return _RESEARCH_CAPTURE_COLUMNS.issubset(header)


def read_generic_csv(log_path: Path) -> Iterator[CanFrame]:
    """Read a CSV with timestamp, id (hex) and data (hex) columns; header names are matched loosely."""
    with log_path.open(encoding="utf-8", newline="") as log_file:
        reader = csv.DictReader(log_file)
        columns = _resolve_csv_columns(log_path, reader.fieldnames or [])
        for line_number, row in enumerate(reader, start=2):
            try:
                yield CanFrame(
                    timestamp=float(row[columns["timestamp"]]),
                    arbitration_id=_parse_hex_id(row[columns["id"]]),
                    data=_parse_hex_bytes(row[columns["data"]]),
                    bus=row[columns["bus"]] if columns["bus"] else "",
                )
            except ValueError as error:
                raise LogFormatError(f"{log_path}:{line_number}: {error}") from error


def _resolve_csv_columns(log_path: Path, header: list[str]) -> dict[str, str]:
    by_lower_name = {name.strip().lower(): name for name in header}

    def find(candidates: tuple[str, ...]) -> str:
        return next((by_lower_name[c] for c in candidates if c in by_lower_name), "")

    columns = {
        "timestamp": find(_CSV_TIMESTAMP_COLUMNS),
        "id": find(_CSV_ID_COLUMNS),
        "data": find(_CSV_DATA_COLUMNS),
        "bus": find(_CSV_BUS_COLUMNS),
    }
    missing = [role for role in ("timestamp", "id", "data") if not columns[role]]
    if missing:
        raise LogFormatError(f"{log_path}: missing CSV columns {missing}, header is {header}")
    return columns


def _parse_hex_id(text: str) -> int:
    return int(text.strip().removeprefix("0x").removeprefix("0X"), 16)


def _parse_hex_bytes(text: str) -> bytes:
    return bytes.fromhex(text.replace(" ", "").removeprefix("0x"))

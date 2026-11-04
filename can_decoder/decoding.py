from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import Protocol

from can_decoder.model import CanFrame, DecodedSignal


class UnknownMessageError(Exception):
    pass


class FrameDecodeError(Exception):
    pass


class MessageDecoder(Protocol):
    def decode(self, frame: CanFrame) -> list[DecodedSignal]:
        """Raise UnknownMessageError or FrameDecodeError when the frame cannot be decoded."""
        ...


@dataclass
class DecodeStatistics:
    decoded_frames: int = 0
    unknown_ids: Counter[int] = field(default_factory=Counter)
    failed_ids: Counter[int] = field(default_factory=Counter)


def decode_frames(
    frames: Iterable[CanFrame],
    decoder: MessageDecoder,
    statistics: DecodeStatistics,
    message_names: set[str] | None = None,
) -> Iterator[DecodedSignal]:
    """Yield decoded signals; undecodable frames are counted in `statistics` instead of aborting the run."""
    for frame in frames:
        try:
            signals = decoder.decode(frame)
        except UnknownMessageError:
            statistics.unknown_ids[frame.arbitration_id] += 1
            continue
        except FrameDecodeError:
            statistics.failed_ids[frame.arbitration_id] += 1
            continue

        statistics.decoded_frames += 1
        for signal in signals:
            if message_names is None or signal.message_name in message_names:
                yield signal

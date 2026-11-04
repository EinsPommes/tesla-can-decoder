from pathlib import Path

import cantools
from cantools.database.can import Database, Message
from cantools.database.errors import DecodeError

from can_decoder.decoding import FrameDecodeError, UnknownMessageError
from can_decoder.model import CanFrame, DecodedSignal


class DbcDecoder:
    """Adapter that hides cantools behind the MessageDecoder port."""

    def __init__(self, database: Database) -> None:
        self._database = database
        self._single_signal_cache: dict[int, list[Message]] = {}

    @classmethod
    def from_file(cls, dbc_path: Path) -> "DbcDecoder":
        # strict=False: DBCs rebuilt from MCU dumps often contain overlapping signals.
        database = cantools.database.load_file(str(dbc_path), strict=False)
        if not isinstance(database, Database):
            raise ValueError(f"{dbc_path} is not a CAN database")
        return cls(database)

    def decode(self, frame: CanFrame) -> list[DecodedSignal]:
        message = self._find_message(frame.arbitration_id)
        try:
            values = self._decode_values(message, frame.data)
        except (DecodeError, ValueError) as error:
            raise FrameDecodeError(f"0x{frame.arbitration_id:X}: {error}") from error

        return [
            DecodedSignal(
                timestamp=frame.timestamp,
                bus=frame.bus,
                arbitration_id=frame.arbitration_id,
                message_name=message.name,
                signal_name=name,
                value=_plain_value(value),
                unit=_unit_of(message, name),
                capture=frame.capture,
            )
            for name, value in values.items()
        ]

    def _decode_values(self, message: Message, data: bytes) -> dict[str, object]:
        try:
            return dict(message.decode(data, decode_choices=True, allow_truncated=True))
        except DecodeError:
            # Overlapping signals (common in rebuilt DBCs) break cantools' combined unpacking.
            # Multiplexed messages are excluded: their signals are only valid for one mux value.
            if message.is_multiplexed():
                raise
            return self._decode_signal_by_signal(message, data)

    def _decode_signal_by_signal(self, message: Message, data: bytes) -> dict[str, object]:
        values: dict[str, object] = {}
        for single_signal_message in self._single_signal_messages(message):
            values.update(single_signal_message.decode(data, decode_choices=True, allow_truncated=True))
        return values

    def _single_signal_messages(self, message: Message) -> list[Message]:
        if message.frame_id not in self._single_signal_cache:
            self._single_signal_cache[message.frame_id] = [
                Message(
                    frame_id=message.frame_id,
                    name=message.name,
                    length=message.length,
                    signals=[signal],
                    strict=False,
                )
                for signal in message.signals
            ]
        return self._single_signal_cache[message.frame_id]

    def _find_message(self, arbitration_id: int) -> Message:
        try:
            return self._database.get_message_by_frame_id(arbitration_id)
        except KeyError as error:
            raise UnknownMessageError(f"0x{arbitration_id:X}") from error


def _plain_value(value: object) -> float | int | str:
    if isinstance(value, (int, float)):
        return value
    return str(value)


def _unit_of(message: Message, signal_name: str) -> str:
    return message.get_signal_by_name(signal_name).unit or ""

import argparse
import sys
from pathlib import Path

from can_decoder.dbc_decoder import DbcDecoder
from can_decoder.decoding import DecodeStatistics, decode_frames
from can_decoder.log_readers import LogFormatError, read_frames
from can_decoder.output import write_csv, write_summary, write_text


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Decode CAN logs (candump or CSV) with a DBC file.")
    parser.add_argument("dbc", type=Path, help="DBC file, e.g. rebuilt from a Tesla MCU dump")
    parser.add_argument("log", type=Path, help="CAN log: candump .log or .csv (timestamp,id,data)")
    parser.add_argument("-o", "--output", type=Path, help="write decoded signals as CSV to this file")
    parser.add_argument(
        "-m", "--message", action="append", dest="messages", metavar="NAME",
        help="only show this message (repeatable)",
    )
    return parser.parse_args()


def run(arguments: argparse.Namespace) -> None:
    decoder = DbcDecoder.from_file(arguments.dbc)
    statistics = DecodeStatistics()
    message_filter = set(arguments.messages) if arguments.messages else None
    signals = decode_frames(read_frames(arguments.log), decoder, statistics, message_filter)

    if arguments.output:
        with arguments.output.open("w", encoding="utf-8", newline="") as output_file:
            write_csv(signals, output_file)
    else:
        write_text(signals, sys.stdout)

    write_summary(statistics, sys.stderr)


def main() -> int:
    arguments = parse_arguments()
    for path in (arguments.dbc, arguments.log):
        if not path.is_file():
            print(f"error: file not found: {path}", file=sys.stderr)
            return 2
    try:
        run(arguments)
    except LogFormatError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

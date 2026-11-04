<div align="center">

# tesla-can-decoder

**Decode raw Tesla CAN bus logs into physical signal values using a DBC file.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Built with cantools](https://img.shields.io/badge/built%20with-cantools-orange.svg)](https://github.com/cantools/cantools)

[Features](#features) •
[Installation](#installation) •
[Usage](#usage) •
[Log formats](#supported-log-formats)

</div>

---

## Overview

`tesla-can-decoder` is a small command-line tool that turns raw CAN frames (from `candump` or CSV captures) into human-readable signals such as vehicle speed, battery voltage or current. It is built for working with DBC files rebuilt from Tesla firmware, which often contain overlapping signal definitions that standard tools refuse to decode.

```text
$ python decode_can.py vehicle.dbc drive.log
1700000000.000000 0x257 DI_speed.DI_vehicleSpeed = -30.16 kph
1700000000.000000 0x257 DI_speed.DI_uiSpeedUnits = KPH
1700000000.010000 0x132 HVBattAmpVolt.BattVoltage132 = 400 V
1700000000.010000 0x132 HVBattAmpVolt.SmoothBattCurrent132 = -2.4 A
Decoded frames: 2
Unknown IDs (not in DBC): 1 frames, 1 IDs
  0x3FF: 1
```

## Features

- **Multiple input formats**: `candump` logs, generic CSV and segmented research captures
- **Robust decoding of rebuilt DBCs**: falls back to signal-by-signal decoding when overlapping signals break combined unpacking
- **Value tables**: enum values are shown by name (e.g. `KPH`, `ACTIVE`, `SNA`)
- **Truncated frames**: frames shorter than the DBC length are still decoded
- **Message filter**: limit output to specific messages
- **CSV export**: ready for pandas, Excel or plotting tools
- **Decode summary**: lists unknown and undecodable CAN IDs, sorted by frequency

## Installation

Requires **Python 3.10 or newer**.

```bash
git clone https://github.com/EinsPommes/tesla-can-decoder.git
cd tesla-can-decoder

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## Usage

```text
python decode_can.py <dbc> <log> [-o OUTPUT] [-m NAME ...]
```

| Argument | Description |
| --- | --- |
| `dbc` | DBC file with the message and signal definitions |
| `log` | CAN log file (`.log` for candump, `.csv` for CSV formats) |
| `-o`, `--output` | Write decoded signals to a CSV file instead of stdout |
| `-m`, `--message` | Only output this message; can be repeated |

The decode summary is always written to **stderr**, so it never ends up in redirected output.

### Examples

Print all decoded signals:

```bash
python decode_can.py vehicle.dbc drive.log
```

Show only selected messages:

```bash
python decode_can.py vehicle.dbc drive.log -m DI_speed -m HVBattAmpVolt
```

Export to CSV:

```bash
python decode_can.py vehicle.dbc drive.log -o decoded.csv
```

```csv
timestamp,bus,id,message,signal,value,unit,segment,label,phase,relative_ms
1700000000.000000,can0,0x257,DI_speed,DI_vehicleSpeed,-30.16,kph,,,,
1700000000.010000,can0,0x132,HVBattAmpVolt,BattVoltage132,400,V,,,,
```

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | Log file has an invalid format |
| `2` | DBC or log file not found |

## Supported log formats

The format is detected from the file extension and, for CSV files, from the header.

### candump (`.log`)

Output of `candump -l` from [can-utils](https://github.com/linux-can/can-utils):

```text
(1700000000.000000) can0 257#00B0070001000000
```

### Generic CSV (`.csv`)

Column names are matched case-insensitively against these aliases:

| Field | Accepted column names | Required |
| --- | --- | --- |
| Timestamp | `timestamp`, `time`, `ts` | yes |
| CAN ID | `id`, `arbitration_id`, `can_id`, `msgid` | yes |
| Payload | `data`, `payload`, `bytes` | yes |
| Bus | `bus`, `channel`, `interface` | no |

### Segmented research capture (`.csv`)

Event-triggered captures with the columns `segment_id`, `label`, `phase`, `relative_ms`, `snapshot_uptime_ms`, `physical_bus`, `id` and `raw`. Lines starting with `#` (segment summaries) are skipped. The segment context is kept in the output:

```text
[1 LEFT_SOFT -5000ms] 1167.928000 0x1E5 ...
```

## DBC files

No vehicle DBC is shipped with this project. Community-maintained Tesla DBCs are available for example in [commaai/opendbc](https://github.com/commaai/opendbc).

## Project structure

```text
tesla-can-decoder/
├── can_decoder/
│   ├── model.py         # Domain types: CanFrame, DecodedSignal, CaptureContext
│   ├── log_readers.py   # Parsers for candump, CSV and research captures
│   ├── decoding.py      # Decoding pipeline and statistics
│   ├── dbc_decoder.py   # cantools-based DBC decoder
│   └── output.py        # Text, CSV and summary writers
└── decode_can.py        # Command-line entry point
```

## Contributing

Contributions are welcome. Please open an issue first to discuss larger changes.

## Privacy

Real CAN captures can contain **personal data**, such as GPS positions (`UI_locationStatus`, ID `0x04F`) or the vehicle's VIN. Never publish raw captures. The included `.gitignore` excludes all `*.csv` files.

## Disclaimer

This project is not affiliated with, endorsed by or connected to Tesla, Inc. It is intended for research and educational purposes. Only read data from vehicles you own or are authorized to analyze, and never send frames to a vehicle's CAN bus based on this tool's output.

## License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.

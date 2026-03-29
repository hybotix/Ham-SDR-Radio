# Ham System Design Document

**Project:** Ham System — N7PKT Integrated Ham Radio Control Platform  
**Platform:** Raspberry Pi 5 / 8GB RAM ("hammer")  
**Callsign:** N7PKT  
**Author:** Dale — Hybrid RobotiX / The Accessibility Files  
**Status:** Pre-development — Design Phase  
**Version:** 0.1 (Draft)

---

## 1. Overview & Goals

### 1.1 Purpose

The Ham System is a Python-based integrated control platform for HF transceivers, designed to run on the Raspberry Pi 5 ("hammer") and serve as a fully featured mobile amateur radio station integrated with the My Chairiet wheelchair platform.

The system provides:
- Safe, automated CAT control of supported radios without triggering known hamlib bugs
- Digital mode operation (FT8, WSPR, CW keying)
- QSO logging and APRS position beaconing
- Integration with the My Chairiet MQTT message bus for telemetry and alerts
- Autonomous operation capability

### 1.2 Goals

- Replace ad-hoc radio control scripts with a coherent, documented system
- Provide a safe abstraction layer over radio CAT control, with per-radio guards against known bugs
- Support both attended and unattended operation
- Integrate cleanly with the broader My Chairiet platform
- Remain fully open source

### 1.3 Non-Goals

- This system does not implement its own FT8/WSPR decoder — it interfaces with WSJT-X via UDP
- This system does not replace the radio's physical head unit — physical controls remain primary for manual operation
- This system does not manage audio hardware directly beyond routing

### 1.4 Scripting Policy

**ALL scripts and automation are written in Python 3.14.3. No exceptions.**

- Bash, shell scripts, and other scripting languages are strictly prohibited
- Build automation, installation, system checks, and service management are all implemented in Python
- `subprocess` may be used where necessary to invoke external tools, but the invoking code is always Python
- This policy applies to every component of the Ham System without exception

### 1.5 File Naming Convention

All Python files must include a version number as a suffix in the filename.

**Format:** `filename-vX.Y.Z.py`

**Examples:**
- `rig_control-v0.0.1.py`
- `tx_guard-v0.0.1.py`
- `ham_system-v0.0.1.py`

- Versioning follows semantic versioning (MAJOR.MINOR.PATCH)
- All files start at `v0.0.1`
- Version in filename must match the version declared inside the file
- Version bumps are applied ONLY to the file(s) actually changed — never as a blanket project-wide bump
- No file is committed or deployed without a version suffix

---

## 2. Hardware & Constraints

### 2.1 Primary Hardware

| Component | Details |
|-----------|---------|
| Host | Raspberry Pi 5 / 8GB RAM ("hammer") |
| OS | Raspberry Pi OS Trixie (Debian 13), booting from USB |
| Python | 3.14.3 (built from source if not present) |
| OpenSSL | 4.1 (built from source) |
| Transceiver | See RADIOS list in settings |
| Antenna | Hamstick mobile (balcony / mobile proven) |
| Radio Connection | USB serial (device path configured per radio) |
| Radio Baud Rate | Configured per radio in RADIOS list |
| Radio Protocol | Configured per radio model |
| Power | LiFePO4 battery (wheelchair platform) |

### 2.2 Radio Head Unit

The radio head unit remains the primary manual control interface. The software system operates alongside it, not instead of it.

Control flow:
```
Radio Head Unit <---> Radio Body <---> Ham System (Python / CAT)
       |                                      |
  Manual Control                    Automated / Digital
```

### 2.3 Known Hardware Constraints

- The radio ACC port (DE-19 or equivalent) is available for auxiliary connections
- Audio I/O is via the radio's USB audio interface or ACC port
- Serial CAT control is via the radio's USB port
- The Pi 5 PCIe on "hammer" is confirmed good

### 2.4 Hardware Interface Configuration

The Ham System supports multiple audio/interface hardware options per radio via configuration. No separate software distribution or code change is required to switch interfaces or add radios.

**Supported interfaces (per radio):**

| Interface | Description |
|-----------|-------------|
| `de19` | ACC port (DE-19 connector) — initial hardware |
| `digirig` | DigiRig Mobile — clean isolated audio/serial interface |

Each radio instance has its own interface setting in `settings-v0.0.1.py`:

```python
RADIOS = [
    {
        "index":           1,
        "name":            "Radio name here",
        "model":           "g90",
        "port":            "/dev/ttyUSB0",
        "baud":            19200,
        "audio_interface": "de19",
        "audio_device":    "Radio audio device name",
    },
    # {
    #     "index":           2,
    #     "name":            "...",
    #     "model":           "...",
    #     "port":            "/dev/ttyUSB1",
    #     "baud":            ...,
    #     "audio_interface": "...",
    #     "audio_device":    "...",
    # },
]
```

Adding a second radio requires only adding an entry to `RADIOS` — no code changes. Each radio runs fully independently with its own CAT control thread, audio pipeline, and TX guard instance.

**DigiRig upgrade path:** Update `audio_interface` and `audio_device` for the relevant radio entry. The rest of the system is unaffected.

---

## 3. Software Architecture

### 3.1 Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.14.3 (required — built from source if not present) |
| CAT Control | Direct `pyserial` (see Known Bugs section) |
| SDR | SDR++ (always built from latest source) |
| Rig Control Daemon | FlRig (built from latest source if not present) |
| Digital Modes | WSJT-X (external), interfaced via UDP API |
| Audio | `pyaudio` / ALSA |
| Logging | SQLite via Python `sqlite3` |
| APRS | `aprslib` or direct AX.25 |
| MQTT | `paho-mqtt` (My Chairiet integration) |
| UI | TBD — touch-friendly, large buttons |

### 3.2 Module Structure (Planned)

```
ham_system/
├── core/
│   ├── radio_manager-v0.0.1.py      # Multi-radio lifecycle manager
│   ├── rig_control-v0.0.1.py        # Per-radio CAT abstraction (NO hamlib)
│   ├── tx_guard-v0.0.1.py           # Per-radio TX safety enforcement
│   └── state_machine-v0.0.1.py      # Per-radio state tracking
├── modes/
│   ├── ft8_interface-v0.0.1.py      # WSJT-X UDP API bridge (per radio)
│   ├── wspr_interface-v0.0.1.py     # WSPR interface (per radio)
│   └── cw_keyer-v0.0.1.py           # CW keying support (per radio)
├── logging/
│   ├── qso_log-v0.0.1.py            # SQLite QSO logging (radio index tagged)
│   └── adif_export-v0.0.1.py        # ADIF export for LoTW / QRZ
├── aprs/
│   └── beacon-v0.0.1.py             # APRS position beaconing
├── mqtt/
│   └── chairiet_bridge-v0.0.1.py    # My Chairiet MQTT integration (indexed topics)
├── ui/
│   └── main_ui-v0.0.1.py            # Touch UI — per-radio panels (TBD)
└── config/
    └── settings-v0.0.1.py           # System configuration (RADIOS list)
```

`radio_manager-v0.0.1.py` is the top-level orchestrator — it reads the `RADIOS` list from settings, instantiates one `rig_control`, `tx_guard`, and `state_machine` per entry, and manages their lifecycle. Adding a radio to the config automatically spawns a new set of instances at startup.

### 3.3 CAT Control Strategy

The Ham System will use **direct `pyserial` communication** with supported radios using raw CAT commands appropriate for each radio model. This completely bypasses hamlib and eliminates exposure to known hamlib bugs.

Each radio runs as a fully independent instance with its own:
- CAT control thread (`rig_control` instance)
- Audio pipeline
- TX guard instance
- MQTT publisher (indexed topic namespace)

The `rig_control.py` module will implement:
- Frequency read/set
- Mode read/set (USB/LSB/CW/AM/FM)
- S-meter polling
- TX/RX state monitoring
- **TX is NEVER commanded by software without explicit user action**

Polling interval: 250–500ms per radio, per instance. Radios operate fully independently — one radio transmitting does not block or affect another.

### 3.4 WSJT-X Integration

FT8 and WSPR decoding/encoding is handled by WSJT-X running as an external process. The Ham System interfaces via WSJT-X's UDP API (default port 2237) for:
- Frequency/mode synchronization
- Decoded message display
- TX macro triggering
- Log synchronization

### 3.5 MQTT Integration (My Chairiet)

Ham System publishes per-radio telemetry to the My Chairiet MQTT bus using indexed topics. Each radio instance publishes independently.

**Topic structure:** `console/radio/{index}/{parameter}`

```
console/radio/1/frequency   # Radio 1 operating frequency (Hz)
console/radio/1/mode        # Radio 1 mode (USB/LSB/CW/FT8/etc.)
console/radio/1/tx_state    # Radio 1 transmitting: true/false
console/radio/1/smeter      # Radio 1 S-meter reading
console/radio/2/frequency   # Radio 2 operating frequency (Hz)
console/radio/2/mode        # Radio 2 mode
console/radio/2/tx_state    # Radio 2 transmitting: true/false
console/radio/2/smeter      # Radio 2 S-meter reading

alerts/radio/1/tx_stuck     # ALERT: Radio 1 TX guard triggered
alerts/radio/2/tx_stuck     # ALERT: Radio 2 TX guard triggered
```

A subscriber can monitor all radios with `console/radio/#` or a single radio with `console/radio/1/#`.

---

## 4. Known Bugs & Workarounds

### 4.1 Hamlib Hard-Transmit Bug

**Symptom:** When hamlib is used to control certain radios, it causes the radio to enter a hard transmit state — keying the transmitter uncontrollably. This was discovered with the initial supported radio.

**Effect:** Uncontrolled RF transmission. On a 20W radio operating on a balcony, this is a regulatory and safety hazard.

**Root Cause:** Unknown. The bug appears to be in hamlib's radio driver or its CAT command sequencing. Whether this affects all radios or specific models has not been determined.

**Workaround:** **hamlib is not used in this project under any circumstances.** All rig control is implemented via direct `pyserial` CI-V commands. This is a hard architectural constraint, not optional.

**Impact on dependencies:** Any tool that requires hamlib for rig control (e.g., some logging software, some digital mode programs) must be evaluated carefully. If a tool requires hamlib and cannot be configured to use a virtual rig or dummy device, it will not be used.

### 4.2 TX Guard Design

Because of the hamlib bug and the general risks of uncontrolled transmission, the Ham System implements a TX guard layer:

- Software TX is only possible via explicit, confirmed user action
- TX state is polled continuously; unexpected TX triggers an alert
- Emergency TX cutoff is available as a hardware-level kill (planned — relay on ACC port or RTS line)
- The system logs all TX events with timestamps

---

## 5. Configuration & Settings

### 5.1 Configuration File

All system configuration is stored in a single versioned Python settings file (`settings-v0.0.1.py`). No external config formats (YAML, INI, JSON) are used — configuration is pure Python for consistency with the all-Python policy.

### 5.2 Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `RADIOS` | List of radio config dicts — one entry per radio | See settings file |
| `RADIOS[n].index` | Radio index (1-based) — used in MQTT topics | `1` |
| `RADIOS[n].port` | Serial port for CAT control | `/dev/ttyUSB0` |
| `RADIOS[n].baud` | CAT baud rate | `19200` |
| `RADIOS[n].audio_interface` | Interface type (`de19` or `digirig`) | `de19` |
| `RADIOS[n].audio_device` | ALSA audio device name | *(radio dependent)* |
| `RIG_POLL_INTERVAL` | CAT polling interval (seconds) | `0.25` |
| `WSJTX_UDP_HOST` | WSJT-X UDP interface host | `127.0.0.1` |
| `WSJTX_UDP_PORT` | WSJT-X UDP interface port | `2237` |
| `MQTT_HOST` | My Chairiet MQTT broker host | `localhost` |
| `MQTT_PORT` | MQTT broker port | `1883` |
| `CALLSIGN` | Station callsign | `N7PKT` |
| `GRID_SQUARE` | Maidenhead grid square | TBD |
| `LOG_DB_PATH` | Path to QSO SQLite database | `./logs/qso_log.db` |
| `APRS_ENABLE` | Enable APRS beaconing | `False` |
| `APRS_INTERVAL` | APRS beacon interval (seconds) | `600` |
| `TX_GUARD_ENABLE` | Enable TX guard layer | `True` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

### 5.3 Runtime Overrides

Command-line arguments may override any configuration parameter at runtime. The settings module provides a unified interface that merges file config with runtime overrides, with runtime values taking precedence.

---

## 6. Logging & QSO Database

### 6.1 Overview

All QSO (contact) records are stored in a local SQLite database. The logging module is responsible for writing, querying, and exporting records. No external database engine is required.

### 6.2 QSO Record Schema

```sql
CREATE TABLE qso (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,          -- ISO 8601 UTC
    callsign    TEXT NOT NULL,          -- Worked station callsign
    frequency   REAL NOT NULL,          -- Frequency in Hz
    mode        TEXT NOT NULL,          -- USB / LSB / CW / FT8 / WSPR
    rst_sent    TEXT,                   -- RST sent
    rst_recv    TEXT,                   -- RST received
    grid        TEXT,                   -- Worked station grid square
    name        TEXT,                   -- Operator name if known
    comment     TEXT,                   -- Free text notes
    adif_export INTEGER DEFAULT 0       -- 0 = not exported, 1 = exported
);
```

### 6.3 ADIF Export

QSO records are exportable to ADIF format for upload to LoTW, QRZ, and other logging services. The export module (`adif_export-v0.0.1.py`) supports:
- Full database export
- Export of un-exported records only (incremental)
- Date range export

### 6.4 TX Event Log

All transmit events are logged separately for safety auditing:

```sql
CREATE TABLE tx_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,          -- ISO 8601 UTC
    frequency   REAL NOT NULL,
    mode        TEXT NOT NULL,
    duration_ms INTEGER,                -- TX duration in milliseconds
    triggered_by TEXT,                  -- 'user' / 'ft8' / 'wspr' / 'guard_stop'
    notes       TEXT
);
```

---

## 7. APRS Integration

### 7.1 Overview

The APRS module provides automatic position beaconing over RF using the active radio. APRS is disabled by default and must be explicitly enabled in configuration.

### 7.2 Beacon Content

Each beacon transmits:
- Callsign: `N7PKT`
- Position: Derived from GPS or manually configured grid square
- Symbol: Wheelchair / mobile station
- Comment: Configurable — e.g. `Hybrid RobotiX Mobile Station`

### 7.3 Beacon Frequency

Standard APRS frequency for North America: **144.390 MHz**

The APRS module will command the radio to QSY to 144.390 MHz, transmit the beacon, then return to the prior operating frequency and mode. This QSY sequence is handled entirely within the TX guard framework.

### 7.4 Implementation

- APRS packet encoding implemented in Python (`beacon-v0.0.1.py`)
- No external APRS daemon required
- Beacon interval is configurable (default 10 minutes)
- GPS position updates beacon coordinates automatically when GPS is available
- All APRS TX events are logged to the TX event log

### 7.5 Constraints

- APRS beaconing is suspended during active FT8 / WSPR / CW operation
- APRS TX uses the same TX guard layer as all other transmit operations
- Beacon is suppressed if battery voltage drops below a configurable threshold (TBD)

---

## 8. CW Keyer

### 8.1 Overview

The CW keyer module (`cw_keyer-v0.0.1.py`) provides software-driven CW keying of the active radio via the ACC port or RTS/DTR lines on the CAT serial interface.

### 8.2 Keying Method

CW keying is achieved by asserting the RTS or DTR line on the radio's USB serial interface to key the transmitter, with timing controlled by the Python keyer. No external keyer hardware is required for basic operation.

### 8.3 Features

- Configurable WPM (words per minute)
- Iambic paddle input support (via GPIO or USB HID)
- Straight key input support
- Keyboard CW (type to send)
- Macro / message memory (stored in settings)
- Full QSK (break-in) support — the radio is polled between elements for incoming signals

### 8.4 CW Logging

All CW QSOs are logged to the QSO database with mode set to `CW`. RST sent/received is recorded manually or via macro.

### 8.5 Constraints

- CW keying is subject to the TX guard layer — no unintended keying
- WPM range: 5–40 WPM (configurable)
- Sidetone is provided by the radio hardware — no software sidetone required

---

## 9. Testing Strategy

### 9.1 Philosophy

All modules are tested in isolation before integration. No module is considered complete without passing its unit tests. Testing is Python-only — no shell-based test runners.

### 9.2 Test Framework

- **`unittest`** — Python standard library, no external dependencies required
- Test files follow the same versioned naming convention: `test_rig_control-v0.0.1.py`
- All tests live in a `tests/` directory mirroring the module structure

### 9.3 Test Structure

```
tests/
├── core/
│   ├── test_rig_control-v0.0.1.py
│   ├── test_tx_guard-v0.0.1.py
│   └── test_state_machine-v0.0.1.py
├── modes/
│   ├── test_ft8_interface-v0.0.1.py
│   └── test_cw_keyer-v0.0.1.py
├── logging/
│   ├── test_qso_log-v0.0.1.py
│   └── test_adif_export-v0.0.1.py
└── aprs/
    └── test_beacon-v0.0.1.py
```

### 9.4 Hardware-in-the-Loop Testing

Tests that require physical radio hardware are gated behind a `--hardware` flag. Without this flag, a mock serial interface is used so tests can run without the radio connected. This allows development and testing on any machine.

### 9.5 TX Guard Testing

The TX guard is tested exhaustively — it is safety-critical code. Tests cover:
- Normal TX/RX cycling
- Unexpected TX detection and alert
- Emergency cutoff triggering
- Guard behavior during mode transitions

---

## 10. Development Roadmap

### Phase 0 — Foundation (Current)
- [x] Design document drafted
- [x] GitHub repo created (`hybotix/Ham-SDR-Radio`)
- [ ] Python 3.14.3 build complete on "hammer"
- [ ] OpenSSL 4.1 build complete on "hammer"
- [ ] Repo structure scaffolded
- [ ] Settings module (`settings-v0.0.1.py`) implemented

### Phase 1 — Rig Control Core
- [ ] CAT serial interface (`rig_control-v0.0.1.py`) — read frequency, mode, S-meter
- [ ] TX guard layer (`tx_guard-v0.0.1.py`)
- [ ] Radio state machine (`state_machine-v0.0.1.py`)
- [ ] Unit tests passing with mock serial interface
- [ ] Hardware-in-the-loop tests passing with radio connected

### Phase 2 — Logging
- [ ] QSO database (`qso_log-v0.0.1.py`)
- [ ] ADIF export (`adif_export-v0.0.1.py`)
- [ ] TX event logging integrated into TX guard
- [ ] Unit tests passing

### Phase 3 — Digital Modes
- [ ] WSJT-X UDP bridge (`ft8_interface-v0.0.1.py`)
- [ ] WSPR interface (`wspr_interface-v0.0.1.py`)
- [ ] FT8 QSOs logging automatically
- [ ] Integration tests passing

### Phase 4 — CW Keyer
- [ ] CW keyer (`cw_keyer-v0.0.1.py`)
- [ ] Keyboard CW operational
- [ ] Iambic paddle input working
- [ ] Full QSK verified on radio
- [ ] CW QSOs logging correctly

### Phase 5 — APRS
- [ ] APRS beacon (`beacon-v0.0.1.py`)
- [ ] Position beaconing on 144.390 MHz
- [ ] QSY and return sequence verified safe
- [ ] Beacon suppression during active operation verified

### Phase 6 — My Chairiet Integration
- [ ] MQTT bridge (`chairiet_bridge-v0.0.1.py`)
- [ ] Radio telemetry publishing to MQTT bus
- [ ] TX stuck alert firing correctly
- [ ] Integration tested with My Chairiet MQTT broker

### Phase 7 — UI
- [ ] Touch UI design finalized
- [ ] Main UI (`main_ui-v0.0.1.py`) implemented
- [ ] Touchscreen tested on "hammer"
- [ ] Full system integration test

---

*Document is a living design artifact. Architecture evolves as development progresses.*  
*— Dale, N7PKT — Hybrid RobotiX / The Accessibility Files*  
*"I. WILL. NEVER. GIVE. UP. OR. SURRENDER."*

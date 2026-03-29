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

The Ham System is a Python-based integrated control platform for the Xiegu G90 HF transceiver, designed to run on the Raspberry Pi 5 ("hammer") and serve as a fully featured mobile amateur radio station integrated with the My Chairiet wheelchair platform.

The system provides:
- Safe, automated CAT control of the Xiegu G90 without triggering known hamlib bugs
- Digital mode operation (FT8, WSPR, CW keying)
- QSO logging and APRS position beaconing
- Integration with the My Chairiet MQTT message bus for telemetry and alerts
- Autonomous operation capability

### 1.2 Goals

- Replace ad-hoc radio control scripts with a coherent, documented system
- Provide a safe abstraction layer over G90 CAT control that guards against the hard-transmit bug
- Support both attended and unattended operation
- Integrate cleanly with the broader My Chairiet platform
- Remain fully open source

### 1.3 Non-Goals

- This system does not implement its own FT8/WSPR decoder — it interfaces with WSJT-X via UDP
- This system does not replace the G90 head unit — physical controls remain primary for manual operation
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
- `rig_control-v0.1.0.py`
- `tx_guard-v0.1.0.py`
- `ham_system-v0.1.0.py`

- Versioning follows semantic versioning (MAJOR.MINOR.PATCH)
- All files start at `v0.1.0`
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
| Transceiver | Xiegu G90 (HF, 20W) |
| Antenna | Hamstick mobile (balcony / mobile proven) |
| G90 Connection | USB serial (appears as `/dev/ttyUSB0` or similar) |
| G90 Baud Rate | 19200 |
| G90 Protocol | CI-V compatible |
| Power | LiFePO4 battery (wheelchair platform) |

### 2.2 G90 Head Unit

The G90 head unit is mounted on a wheelchair armrest and remains the primary manual control interface. The software system operates alongside it, not instead of it.

Control flow:
```
G90 Head Unit <---> G90 Body <---> Ham System (Python / CAT)
      |                                    |
 Manual Control                   Automated / Digital
```

### 2.3 Known Hardware Constraints

- The G90 ACC port (DE-19) is available for auxiliary connections
- Audio I/O is via the G90's USB audio interface or ACC port
- Serial CAT control is via the G90's USB port
- The Pi 5 PCIe on "hammer" is confirmed good

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
│   ├── rig_control-v0.1.0.py        # Safe CAT abstraction layer (NO hamlib)
│   ├── tx_guard-v0.1.0.py           # Transmit safety enforcement
│   └── state_machine-v0.1.0.py      # Radio state tracking
├── modes/
│   ├── ft8_interface-v0.1.0.py      # WSJT-X UDP API bridge
│   ├── wspr_interface-v0.1.0.py     # WSPR interface
│   └── cw_keyer-v0.1.0.py           # CW keying support
├── logging/
│   ├── qso_log-v0.1.0.py            # SQLite QSO logging
│   └── adif_export-v0.1.0.py        # ADIF export for LoTW / QRZ
├── aprs/
│   └── beacon-v0.1.0.py             # APRS position beaconing
├── mqtt/
│   └── chairiet_bridge-v0.1.0.py    # My Chairiet MQTT integration
├── ui/
│   └── main_ui-v0.1.0.py            # Touch UI (TBD)
└── config/
    └── settings-v0.1.0.py           # System configuration
```

### 3.3 CAT Control Strategy

The Ham System will use **direct `pyserial` communication** with the G90 using raw CI-V commands. This completely bypasses hamlib and eliminates exposure to the known hard-transmit bug.

The `rig_control.py` module will implement:
- Frequency read/set
- Mode read/set (USB/LSB/CW/AM/FM)
- S-meter polling
- TX/RX state monitoring
- **TX is NEVER commanded by software without explicit user action**

Polling interval: 250–500ms for state synchronization.

### 3.4 WSJT-X Integration

FT8 and WSPR decoding/encoding is handled by WSJT-X running as an external process. The Ham System interfaces via WSJT-X's UDP API (default port 2237) for:
- Frequency/mode synchronization
- Decoded message display
- TX macro triggering
- Log synchronization

### 3.5 MQTT Integration (My Chairiet)

Ham System publishes to the My Chairiet MQTT bus:

```
console/radio/frequency     # Current operating frequency
console/radio/mode          # Current mode (USB/LSB/CW/etc.)
console/radio/tx_state      # Transmitting: true/false
console/radio/smeter        # S-meter reading
alerts/radio/tx_stuck       # ALERT: TX guard triggered
```

---

## 4. Known Bugs & Workarounds

### 4.1 Hamlib Hard-Transmit Bug

**Symptom:** When hamlib is used to control the Xiegu G90, it causes the radio to enter a hard transmit state — keying the transmitter uncontrollably.

**Effect:** Uncontrolled RF transmission. On a 20W radio operating on a balcony, this is a regulatory and safety hazard.

**Root Cause:** Unknown. The bug appears to be in hamlib's G90 driver or its CI-V command sequencing. Scope of the issue (G90-specific vs. broader hamlib) has not been determined.

**Workaround:** **hamlib is not used in this project under any circumstances.** All rig control is implemented via direct `pyserial` CI-V commands. This is a hard architectural constraint, not optional.

**Impact on dependencies:** Any tool that requires hamlib for rig control (e.g., some logging software, some digital mode programs) must be evaluated carefully. If a tool requires hamlib and cannot be configured to use a virtual rig or dummy device, it will not be used.

### 4.2 TX Guard Design

Because of the hamlib bug and the general risks of uncontrolled transmission, the Ham System implements a TX guard layer:

- Software TX is only possible via explicit, confirmed user action
- TX state is polled continuously; unexpected TX triggers an alert
- Emergency TX cutoff is available as a hardware-level kill (planned — relay on ACC port or RTS line)
- The system logs all TX events with timestamps

---

*Document is a living design artifact. Architecture evolves as development progresses.*  
*— Dale, N7PKT — Hybrid RobotiX / The Accessibility Files*  
*"I. WILL. NEVER. GIVE. UP. OR. SURRENDER."*

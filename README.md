# Ham System — Integrated Ham Radio Control Platform

A Python-based integrated control platform for HF transceivers, designed for
mobile and fixed amateur radio stations. Built from the ground up for
reliability, extensibility, and full automation.

---

## Platform Support

**Debian-based systems ONLY.**

This system is designed and tested on:
- Debian (Trixie and later)
- Raspberry Pi OS (Trixie and later)
- Ubuntu 24.04 LTS and later

Any Debian-based distribution using `apt`/`dpkg` should work without
modification. Other systems are **not supported and will not be.**

---

## Hardware

- Any supported HF transceiver (see Radio Support below)
- Raspberry Pi 5 (primary development platform) or any compatible SBC/PC
- DE-19 ACC port interface or DigiRig Mobile (configured per radio in settings)
- USB serial CAT control

---

## Philosophy

- **Everything built from source into `/usr/local`** — system packages are irrelevant
- **All scripts written in Python** — no bash, no shell scripts, no exceptions
- **All configuration in JSON** — no Python config files, no YAML, no INI
- **Radio agnostic** — supports multiple radios simultaneously, fully independent operation
- **`/usr/local/bin` must be first in PATH** — enforced at runtime
- **Debian-based systems only** — enforced at runtime
- **hamlib is never used** — direct CAT control via `pyserial` only

---

## Prerequisites

Before running the initialization script, `/usr/local/bin` **must** be first
in your PATH. Add this to your shell RC file (`~/.bashrc`, `~/.zshrc`, etc.):

```
export PATH=/usr/local/bin:$PATH
```

The initialization script will detect your shell and offer to make this edit
automatically if it has not been done.

---

## Installation

### Prerequisites

On a fresh OS install, ensure `python3` and `git` are available:

```
sudo apt-get update
sudo apt-get install -y python3 git
```

The initialization script handles everything else automatically.

### Clone and run

```
mkdir -p ~/Repos/GitHub/hybotix
cd ~/Repos/GitHub/hybotix
git clone https://github.com/hybotix/Ham-SDR-Radio.git
cd Ham-SDR-Radio
python3 init-v0.0.1.py
```

The `~/Repos/GitHub/hybotix` directory will be created automatically if it does not exist.

Run the initialization script:

```
python3 init-v0.0.1.py
```

The initialization script handles everything in order:

| Step | Action |
|------|--------|
| Pre-flight | Verify Debian-based platform |
| Pre-flight | Verify `/usr/local/bin` is first in PATH |
| 0 | Install system build dependencies via apt |
| 1 | Build OpenSSL 3.4.x from source into `/usr/local` |
| 2 | Build Python 3.14.3 from source into `/usr/local` |
| 2.5 | Create Python virtual environment (`~/Virtual/Ham-SDR-Radio`) |
| 3 | Scaffold project directory structure |
| 4 | Build SDR++ from latest source |
| 5 | Build FlRig from latest source |
| 6 | Install Python dependencies into virtual environment |
| 7 | Verify radio serial port |
| 7.5 | Set all Python scripts executable |
| 8 | Generate startup script (`start-v0.0.1.py`) |
| 9 | Generate default settings file (`config/settings-v0.0.1.json`) |

All steps are safe to re-run — completed steps are automatically skipped.

---

## Starting the System

```
python3 start-v0.0.1.py
```

The startup script activates the virtual environment, changes into the repo
directory, and starts the Ham System. No manual `source` or `cd` required.

---

## Configuration

All configuration is stored in `config/settings-v0.0.1.json`. Edit this file
to match your hardware before starting the system.

Key settings:

```json
{
    "operator": {
        "callsign":    "YOUR_CALLSIGN",
        "grid_square": "YOUR_GRID"
    },
    "radios": [
        {
            "index":           1,
            "name":            "Radio name",
            "topic_name":      "hf_rig",
            "model":           "g90",
            "port":            "/dev/ttyUSB0",
            "baud":            19200,
            "audio_interface": "de19",
            "audio_device":    "your-audio-device"
        }
    ]
}
```

### Multiple Radios

Add additional entries to the `radios` list. Each radio operates fully
independently with its own CAT control thread, audio pipeline, and TX guard.
The `topic_name` field is used in all MQTT topics for that radio.

---

## Radio Support

| Model | Protocol | Status |
|-------|----------|--------|
| Xiegu G90 | CI-V (direct pyserial) | Supported |

> **Note:** hamlib is **never** used. All CAT control is implemented via direct
> `pyserial` CI-V commands. This is a hard architectural constraint due to
> known hamlib bugs that cause certain radios to enter uncontrolled transmit.

Adding support for additional radios requires adding an entry to `RADIO_PROFILES`
in `init-v0.0.1.py`.

---

## MQTT Integration

Ham System publishes per-radio telemetry to an MQTT broker for integration
with other systems (e.g. My Chairiet wheelchair platform).

Topic structure: `console/radio/{topic_name}/{parameter}`

```
console/radio/hf_rig/frequency
console/radio/hf_rig/mode
console/radio/hf_rig/tx_state
console/radio/hf_rig/smeter
alerts/radio/hf_rig/tx_stuck
```

---

## Project Structure

```
Ham-SDR-Radio/
├── init-v0.0.1.py          # Initialization script
├── start-v0.0.1.py         # Startup script (generated)
├── core/                   # Radio control core modules
├── modes/                  # Digital mode interfaces
├── logging/                # QSO logging
├── aprs/                   # APRS beaconing
├── mqtt/                   # MQTT integration
├── ui/                     # Touch UI
├── config/                 # Configuration files (JSON)
├── tests/                  # Unit tests
├── logs/                   # Log files
└── build/                  # Build workspace (generated)
```

---

## Virtual Environment

The Ham System runs inside a Python virtual environment located at
`~/Virtual/Ham-SDR-Radio`, created from Python 3.14.3. All dependencies
are installed into this environment. The startup script handles activation
automatically.

---

## Author

Dale — Hybrid RobotiX / The Accessibility Files

*"I. WILL. NEVER. GIVE. UP. OR. SURRENDER."*

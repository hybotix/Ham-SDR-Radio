#!/usr/bin/env python3
"""
init-v0.0.1.py — Ham System Initialization Script
Project: Ham System — N7PKT Integrated Ham Radio Control Platform
Author:  Dale — Hybrid RobotiX / The Accessibility Files
Version: 0.0.1

Prerequisite:
  - Python 3.14.3 (built from source, must be used to invoke this script)

This script handles:
  Step 1 — Verify Python 3.14.3
  Step 2 — Check/build OpenSSL 4.1 from source
  Step 3 — Scaffold Ham System directory structure
  Step 4 — Check/build SDR++ from latest source
  Step 5 — Check/build FlRig from latest source
  Step 6 — Install Python dependencies via pip
  Step 7 — Verify G90 serial port
  Step 8 — Create default settings file if not present

Safe to re-run — all steps are idempotent.
Aborts immediately with a clear error if any required build fails.
NO bash or shell scripts. Python only.
"""

VERSION = "0.0.1"

import os
import sys
import subprocess
import shutil
import logging
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
log_filename = LOG_DIR / f"init-{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_filename),
    ],
)
log = logging.getLogger("ham_init")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OPENSSL_VERSION  = "4.1"
OPENSSL_REPO     = "https://github.com/openssl/openssl.git"
OPENSSL_TAG      = "openssl-4.1"
OPENSSL_DIR      = Path("build") / "openssl"

SDRPP_REPO       = "https://github.com/AlexandreRouma/SDRPlusPlus.git"
SDRPP_DIR        = Path("build") / "SDRPlusPlus"

FLRIG_REPO       = "https://git.code.sf.net/p/fldigi/flrig"
FLRIG_DIR        = Path("build") / "flrig"

BUILD_DIR        = Path("build")
SETTINGS_PATH    = Path("config") / "settings-v0.0.1.py"

REQUIRED_PYTHON  = (3, 14, 3)

# Ham System directory structure
HAM_DIRS = [
    "core",
    "modes",
    "logging",
    "aprs",
    "mqtt",
    "ui",
    "config",
    "tests/core",
    "tests/modes",
    "tests/logging",
    "tests/aprs",
    "logs",
    "build",
]

# Required Python packages
PYTHON_DEPS = [
    "pyserial",
    "pyaudio",
    "paho-mqtt",
    "aprslib",
]

# G90 serial port candidates (checked in order)
G90_PORT_CANDIDATES = [
    "/dev/ttyUSB0",
    "/dev/ttyUSB1",
    "/dev/ttyUSB2",
    "/dev/ttyACM0",
]

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def banner():
    log.info("=" * 70)
    log.info("  Ham System Initialization Script")
    log.info("  N7PKT Integrated Ham Radio Control Platform")
    log.info(f"  Version {VERSION}")
    log.info("  Hybrid RobotiX / The Accessibility Files")
    log.info("  I. WILL. NEVER. GIVE. UP. OR. SURRENDER.")
    log.info("=" * 70)


def abort(message: str):
    """Log a fatal error and exit immediately."""
    log.error("")
    log.error("FATAL: " + message)
    log.error("Initialization aborted.")
    log.error("")
    sys.exit(1)


def run(args: list, cwd: Path = None, desc: str = "") -> subprocess.CompletedProcess:
    """
    Run an external command via subprocess.
    Aborts immediately on non-zero return code.
    """
    label = desc or " ".join(str(a) for a in args)
    log.info(f"  Running: {label}")
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log.error(f"  stdout: {result.stdout.strip()}")
        log.error(f"  stderr: {result.stderr.strip()}")
        abort(f"Command failed: {label}")
    return result


def check_command(cmd: str) -> bool:
    """Return True if a command is found on PATH."""
    return shutil.which(cmd) is not None


def require_commands(*cmds: str):
    """Abort if any required build-time commands are missing."""
    for cmd in cmds:
        if not check_command(cmd):
            abort(f"Required build tool '{cmd}' not found on PATH. Install it and re-run.")


def cpu_jobs() -> int:
    """Return a safe parallel job count for make."""
    return os.cpu_count() or 2


# ---------------------------------------------------------------------------
# Step 1 — Verify Python version
# ---------------------------------------------------------------------------

def check_python():
    log.info("")
    log.info("Step 1: Verifying Python version...")
    v = sys.version_info
    if (v.major, v.minor, v.micro) < REQUIRED_PYTHON:
        abort(
            f"Python {'.'.join(str(x) for x in REQUIRED_PYTHON)} is required. "
            f"Currently running {v.major}.{v.minor}.{v.micro}. "
            f"Build Python 3.14.3 from source and invoke this script with it."
        )
    log.info(f"  Python {v.major}.{v.minor}.{v.micro} — OK")


# ---------------------------------------------------------------------------
# Step 2 — Build OpenSSL 4.1 from source
# ---------------------------------------------------------------------------

def build_openssl():
    log.info("")
    log.info("Step 2: Checking OpenSSL 4.1...")

    result = subprocess.run(["openssl", "version"], capture_output=True, text=True)
    if result.returncode == 0:
        installed = result.stdout.strip()
        log.info(f"  Detected: {installed}")
        if f"OpenSSL {OPENSSL_VERSION}" in installed:
            log.info(f"  OpenSSL {OPENSSL_VERSION} already installed — skipping build")
            return
        log.info(f"  OpenSSL {OPENSSL_VERSION} not present — building from source...")
    else:
        log.info("  OpenSSL not found — building from source...")

    require_commands("git", "make", "perl")

    BUILD_DIR.mkdir(exist_ok=True)

    if OPENSSL_DIR.exists():
        log.info("  OpenSSL source already cloned — fetching latest tags...")
        run(["git", "fetch", "--tags"], cwd=OPENSSL_DIR, desc="git fetch openssl tags")
    else:
        log.info("  Cloning OpenSSL repository...")
        run(
            ["git", "clone", "--depth", "1", "--branch", OPENSSL_TAG,
             OPENSSL_REPO, str(OPENSSL_DIR)],
            desc=f"git clone openssl {OPENSSL_TAG}",
        )

    log.info(f"  Checking out tag {OPENSSL_TAG}...")
    run(["git", "checkout", OPENSSL_TAG], cwd=OPENSSL_DIR, desc=f"git checkout {OPENSSL_TAG}")

    log.info("  Configuring OpenSSL...")
    run(
        ["./Configure", "--prefix=/usr/local", "--openssldir=/usr/local/ssl", "linux-aarch64"],
        cwd=OPENSSL_DIR,
        desc="Configure OpenSSL",
    )

    log.info(f"  Building OpenSSL with {cpu_jobs()} jobs...")
    run(["make", f"-j{cpu_jobs()}"], cwd=OPENSSL_DIR, desc="make OpenSSL")

    log.info("  Installing OpenSSL...")
    run(["sudo", "make", "install"], cwd=OPENSSL_DIR, desc="make install OpenSSL")

    result = subprocess.run(["openssl", "version"], capture_output=True, text=True)
    if result.returncode != 0 or f"OpenSSL {OPENSSL_VERSION}" not in result.stdout:
        abort(
            f"OpenSSL build completed but OpenSSL {OPENSSL_VERSION} not detected. "
            f"Verify /usr/local/bin is on PATH and re-run."
        )
    log.info(f"  OpenSSL {OPENSSL_VERSION} built and installed — OK")


# ---------------------------------------------------------------------------
# Step 3 — Scaffold directory structure
# ---------------------------------------------------------------------------

def scaffold_directories():
    log.info("")
    log.info("Step 3: Scaffolding directory structure...")
    for d in HAM_DIRS:
        path = Path(d)
        if path.exists():
            log.info(f"  {d}/ — already exists, skipping")
        else:
            path.mkdir(parents=True, exist_ok=True)
            log.info(f"  {d}/ — created")


# ---------------------------------------------------------------------------
# Step 4 — Build SDR++ from latest source
# ---------------------------------------------------------------------------

def build_sdrpp():
    log.info("")
    log.info("Step 4: Checking SDR++...")

    if check_command("sdrpp"):
        log.info("  sdrpp found on PATH — skipping build")
        return

    log.info("  sdrpp not found — building from latest source...")
    require_commands("cmake", "git", "make")

    BUILD_DIR.mkdir(exist_ok=True)

    if SDRPP_DIR.exists():
        log.info("  SDR++ source already cloned — pulling latest...")
        run(["git", "pull"], cwd=SDRPP_DIR, desc="git pull SDR++")
    else:
        log.info("  Cloning SDR++ repository...")
        run(["git", "clone", SDRPP_REPO, str(SDRPP_DIR)], desc="git clone SDR++")

    build_output = SDRPP_DIR / "build"
    build_output.mkdir(exist_ok=True)

    log.info("  Running cmake...")
    run(
        ["cmake", "..", "-DOPT_BUILD_AUDIO_SINK=ON", "-DOPT_BUILD_SOAPY_SOURCE=OFF"],
        cwd=build_output,
        desc="cmake SDR++",
    )

    log.info(f"  Building SDR++ with {cpu_jobs()} jobs...")
    run(["make", f"-j{cpu_jobs()}"], cwd=build_output, desc="make SDR++")

    log.info("  Installing SDR++...")
    run(["sudo", "make", "install"], cwd=build_output, desc="make install SDR++")

    if not check_command("sdrpp"):
        abort("SDR++ build completed but 'sdrpp' still not found on PATH.")
    log.info("  SDR++ built and installed — OK")


# ---------------------------------------------------------------------------
# Step 5 — Build FlRig from latest source
# ---------------------------------------------------------------------------

def build_flrig():
    log.info("")
    log.info("Step 5: Checking FlRig...")

    if check_command("flrig"):
        log.info("  flrig found on PATH — skipping build")
        return

    log.info("  flrig not found — building from latest source...")
    require_commands("git", "make", "g++", "autoreconf")

    BUILD_DIR.mkdir(exist_ok=True)

    if FLRIG_DIR.exists():
        log.info("  FlRig source already cloned — pulling latest...")
        run(["git", "pull"], cwd=FLRIG_DIR, desc="git pull FlRig")
    else:
        log.info("  Cloning FlRig repository...")
        run(["git", "clone", FLRIG_REPO, str(FLRIG_DIR)], desc="git clone FlRig")

    log.info("  Running autoreconf...")
    run(["autoreconf", "-i"], cwd=FLRIG_DIR, desc="autoreconf FlRig")

    log.info("  Running configure...")
    run(["./configure"], cwd=FLRIG_DIR, desc="configure FlRig")

    log.info(f"  Building FlRig with {cpu_jobs()} jobs...")
    run(["make", f"-j{cpu_jobs()}"], cwd=FLRIG_DIR, desc="make FlRig")

    log.info("  Installing FlRig...")
    run(["sudo", "make", "install"], cwd=FLRIG_DIR, desc="make install FlRig")

    if not check_command("flrig"):
        abort("FlRig build completed but 'flrig' still not found on PATH.")
    log.info("  FlRig built and installed — OK")


# ---------------------------------------------------------------------------
# Step 6 — Install Python dependencies
# ---------------------------------------------------------------------------

def install_python_deps():
    log.info("")
    log.info("Step 6: Installing Python dependencies...")
    for package in PYTHON_DEPS:
        log.info(f"  Installing {package}...")
        run(
            [sys.executable, "-m", "pip", "install", "--upgrade", package],
            desc=f"pip install {package}",
        )
    log.info("  All Python dependencies installed — OK")


# ---------------------------------------------------------------------------
# Step 7 — Verify G90 serial port
# ---------------------------------------------------------------------------

def verify_g90_port():
    log.info("")
    log.info("Step 7: Verifying G90 serial port...")
    found = None
    for port in G90_PORT_CANDIDATES:
        if Path(port).exists():
            found = port
            break

    if found:
        log.info(f"  G90 serial port found: {found} — OK")
        log.info("  NOTE: Verify this is the G90 and update RIG_PORT in settings if needed.")
    else:
        log.warning("  WARNING: No G90 serial port detected on any candidate path:")
        for port in G90_PORT_CANDIDATES:
            log.warning(f"    {port}")
        log.warning("  The G90 may not be connected or may appear on a different port.")
        log.warning(f"  Update RIG_PORT in {SETTINGS_PATH} when the radio is connected.")
        log.warning("  Continuing — this is non-fatal.")


# ---------------------------------------------------------------------------
# Step 8 — Create default settings file
# ---------------------------------------------------------------------------

DEFAULT_SETTINGS = """\
\"\"\"
settings-v0.0.1.py -- Ham System Configuration
Project: Ham System -- N7PKT Integrated Ham Radio Control Platform
Version: 0.0.1

Edit this file to match your hardware and environment.
All settings can be overridden at runtime via command-line arguments.
\"\"\"

VERSION = "0.0.1"

# ---------------------------------------------------------------------------
# Operator
# ---------------------------------------------------------------------------

CALLSIGN    = "N7PKT"
GRID_SQUARE = ""                    # Maidenhead grid square -- set before operating

# ---------------------------------------------------------------------------
# Hardware Interface
# ---------------------------------------------------------------------------

# Select active interface: "de19" (G90 ACC port) or "digirig"
AUDIO_INTERFACE = "de19"

# ---------------------------------------------------------------------------
# G90 CAT Control
# ---------------------------------------------------------------------------

RIG_PORT          = "/dev/ttyUSB0"  # Serial port for G90 CAT control
RIG_BAUD          = 19200           # G90 baud rate -- do not change
RIG_POLL_INTERVAL = 0.25            # CAT polling interval in seconds

# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------

# ALSA device name -- update to match your interface
# de19:    typically "G90 Audio" or similar
# digirig: typically "DigiRig" or check via: python3 -m sounddevice
AUDIO_DEVICE = "G90 Audio"

# ---------------------------------------------------------------------------
# WSJT-X
# ---------------------------------------------------------------------------

WSJTX_UDP_HOST = "127.0.0.1"
WSJTX_UDP_PORT = 2237

# ---------------------------------------------------------------------------
# MQTT (My Chairiet integration)
# ---------------------------------------------------------------------------

MQTT_HOST    = "localhost"
MQTT_PORT    = 1883
MQTT_ENABLED = True

# ---------------------------------------------------------------------------
# QSO Logging
# ---------------------------------------------------------------------------

LOG_DB_PATH = "logs/qso_log.db"

# ---------------------------------------------------------------------------
# APRS
# ---------------------------------------------------------------------------

APRS_ENABLED  = False               # Disabled by default -- enable explicitly
APRS_INTERVAL = 600                 # Beacon interval in seconds (default 10 min)
APRS_COMMENT  = "Hybrid RobotiX Mobile Station"
APRS_FREQ_HZ  = 144_390_000         # 144.390 MHz -- North America APRS

# ---------------------------------------------------------------------------
# TX Guard
# ---------------------------------------------------------------------------

TX_GUARD_ENABLED = True             # Must remain True -- do not disable

# ---------------------------------------------------------------------------
# Logging verbosity
# ---------------------------------------------------------------------------

LOG_LEVEL = "INFO"                  # DEBUG / INFO / WARNING / ERROR
"""


def create_settings():
    log.info("")
    log.info("Step 8: Checking settings file...")
    if SETTINGS_PATH.exists():
        log.info(f"  {SETTINGS_PATH} already exists — skipping")
        return
    log.info(f"  Creating default settings file: {SETTINGS_PATH}")
    SETTINGS_PATH.write_text(DEFAULT_SETTINGS)
    log.info(f"  {SETTINGS_PATH} created — OK")
    log.info("  IMPORTANT: Review and edit settings before running Ham System.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    banner()

    check_python()
    build_openssl()
    scaffold_directories()
    build_sdrpp()
    build_flrig()
    install_python_deps()
    verify_g90_port()
    create_settings()

    log.info("")
    log.info("=" * 70)
    log.info("  Initialization complete.")
    log.info(f"  Review and edit {SETTINGS_PATH} before running Ham System.")
    log.info(f"  Full log saved to: {log_filename}")
    log.info("=" * 70)
    log.info("")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
init-v0.0.1.py — Ham System Initialization Script
Project: Ham System — N7PKT Integrated Ham Radio Control Platform
Author:  Dale — Hybrid RobotiX / The Accessibility Files
Version: 0.0.1

This script handles:
  Step 1 — Check/build OpenSSL 4.1 from source
  Step 2 — Check/build Python 3.14.3 from source
  Step 3 — Scaffold Ham System directory structure
  Step 4 — Check/build SDR++ from latest source
  Step 5 — Check/build FlRig from latest source
  Step 6 — Install Python dependencies via pip
  Step 7 — Verify G90 serial port
  Step 8 — Create default settings file if not present

Safe to re-run — all steps are idempotent.
Aborts immediately with a clear error if any required build fails.
NO bash or shell scripts. Python only.

REQUIRED: Before running this script, /usr/local/bin MUST be first in PATH.
          Add the following line to your shell RC file (~/.bashrc, ~/.zshrc,
          or equivalent) and reload it before proceeding:

              export PATH=/usr/local/bin:$PATH

          This script will abort if /usr/local/bin is not first in PATH.

NOTE: This script may be initially invoked with the system Python to bootstrap
      the build. Once Python 3.14.3 is built and installed, re-invoke with it.
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

LOCAL            = Path("/usr/local")
LOCAL_BIN        = LOCAL / "bin"

OPENSSL_VERSION  = "4.1"
OPENSSL_REPO     = "https://github.com/openssl/openssl.git"
OPENSSL_TAG      = "openssl-4.1"
OPENSSL_DIR      = Path("build") / "openssl"
OPENSSL_PREFIX   = LOCAL
OPENSSL_BIN      = LOCAL_BIN / "openssl"

PYTHON_VERSION   = "3.14.3"
PYTHON_TARBALL   = f"Python-{PYTHON_VERSION}.tar.xz"
PYTHON_URL       = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/{PYTHON_TARBALL}"
PYTHON_DIR       = Path("build") / f"Python-{PYTHON_VERSION}"
PYTHON_PREFIX    = LOCAL
PYTHON_BIN       = LOCAL_BIN / "python3.14"

SDRPP_REPO       = "https://github.com/AlexandreRouma/SDRPlusPlus.git"
SDRPP_DIR        = Path("build") / "SDRPlusPlus"
SDRPP_BIN        = LOCAL_BIN / "sdrpp"

FLRIG_REPO       = "https://git.code.sf.net/p/fldigi/flrig"
FLRIG_DIR        = Path("build") / "flrig"
FLRIG_BIN        = LOCAL_BIN / "flrig"

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
    log.info(f"  Invoked with: {sys.executable} ({sys.version.split()[0]})")
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


def in_local(cmd: str) -> bool:
    """Return True if a command exists in /usr/local/bin. Never checks system PATH."""
    return (LOCAL_BIN / cmd).exists()


def require_commands(*cmds: str):
    """Abort if any required build-time commands are missing from system PATH.
    These are build tools (cmake, gcc, etc.) that must be installed separately —
    they are NOT built by this script and may live anywhere on the system."""
    for cmd in cmds:
        if not __import__('shutil').which(cmd):
            abort(
                f"Required build tool '{cmd}' not found on PATH. "
                f"Install it (e.g. sudo apt install {cmd}) and re-run."
            )


def cpu_jobs() -> int:
    """Return a safe parallel job count for make."""
    return os.cpu_count() or 2


# ---------------------------------------------------------------------------
# Step 1 — Build OpenSSL 4.1 from source
# ---------------------------------------------------------------------------

def build_openssl():
    log.info("")
    log.info("Step 1: Checking OpenSSL 4.1...")

    if OPENSSL_BIN.exists():
        result = subprocess.run([str(OPENSSL_BIN), "version"], capture_output=True, text=True)
        installed = result.stdout.strip()
        log.info(f"  Detected: {installed}")
        if f"OpenSSL {OPENSSL_VERSION}" in installed:
            log.info(f"  OpenSSL {OPENSSL_VERSION} already in /usr/local — skipping build")
            return
        log.info(f"  OpenSSL {OPENSSL_VERSION} not present in /usr/local — building from source...")
    else:
        log.info("  /usr/local/bin/openssl not found — building from source...")

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
        ["./Configure",
         f"--prefix={OPENSSL_PREFIX}",
         f"--openssldir={OPENSSL_PREFIX}/ssl",
         "linux-aarch64"],
        cwd=OPENSSL_DIR,
        desc="Configure OpenSSL",
    )

    log.info(f"  Building OpenSSL with {cpu_jobs()} jobs...")
    run(["make", f"-j{cpu_jobs()}"], cwd=OPENSSL_DIR, desc="make OpenSSL")

    log.info("  Installing OpenSSL...")
    run(["sudo", "make", "install"], cwd=OPENSSL_DIR, desc="make install OpenSSL")

    if not OPENSSL_BIN.exists():
        abort(
            f"OpenSSL build completed but {OPENSSL_BIN} not found. "
            f"Check build output and re-run."
        )
    result = subprocess.run([str(OPENSSL_BIN), "version"], capture_output=True, text=True)
    if f"OpenSSL {OPENSSL_VERSION}" not in result.stdout:
        abort(
            f"OpenSSL build completed but version mismatch: {result.stdout.strip()}"
        )
    log.info(f"  OpenSSL {OPENSSL_VERSION} built and installed — OK")


# ---------------------------------------------------------------------------
# Step 2 — Build Python 3.14.3 from source
# ---------------------------------------------------------------------------

def build_python():
    log.info("")
    log.info("Step 2: Checking Python 3.14.3...")

    # Check if target Python binary already exists
    if PYTHON_BIN.exists():
        result = subprocess.run(
            [str(PYTHON_BIN), "--version"], capture_output=True, text=True
        )
        if PYTHON_VERSION in result.stdout + result.stderr:
            log.info(f"  Python {PYTHON_VERSION} already installed at {PYTHON_BIN} — skipping build")
            _warn_if_wrong_python()
            return

    log.info(f"  Python {PYTHON_VERSION} not found — building from source...")
    require_commands("make", "gcc", "wget")

    BUILD_DIR.mkdir(exist_ok=True)

    tarball_path = BUILD_DIR / PYTHON_TARBALL
    if not tarball_path.exists():
        log.info(f"  Downloading {PYTHON_TARBALL}...")
        run(
            ["wget", "-q", "-O", str(tarball_path), PYTHON_URL],
            desc=f"wget Python {PYTHON_VERSION}",
        )
    else:
        log.info(f"  {PYTHON_TARBALL} already downloaded — skipping download")

    if not PYTHON_DIR.exists():
        log.info(f"  Extracting {PYTHON_TARBALL}...")
        run(
            ["tar", "-xf", str(tarball_path), "-C", str(BUILD_DIR)],
            desc=f"tar extract Python {PYTHON_VERSION}",
        )
    else:
        log.info(f"  Python source already extracted — skipping extraction")

    log.info("  Configuring Python...")
    run(
        ["./configure",
         f"--prefix={PYTHON_PREFIX}",
         "--enable-optimizations",
         "--with-lto",
         f"--with-openssl={OPENSSL_PREFIX}"],
        cwd=PYTHON_DIR,
        desc=f"configure Python {PYTHON_VERSION}",
    )

    log.info(f"  Building Python with {cpu_jobs()} jobs (this will take a while)...")
    run(["make", f"-j{cpu_jobs()}"], cwd=PYTHON_DIR, desc=f"make Python {PYTHON_VERSION}")

    log.info("  Installing Python...")
    run(["sudo", "make", "altinstall"], cwd=PYTHON_DIR, desc="make altinstall Python")

    if not PYTHON_BIN.exists():
        abort(
            f"Python build completed but {PYTHON_BIN} not found. "
            f"Check build output and re-run."
        )
    log.info(f"  Python {PYTHON_VERSION} built and installed at {PYTHON_BIN} — OK")
    _warn_if_wrong_python()


def _warn_if_wrong_python():
    """Warn if this script is not being run with Python 3.14.3."""
    v = sys.version_info
    if (v.major, v.minor, v.micro) < REQUIRED_PYTHON:
        log.warning("")
        log.warning("  WARNING: This script is running under Python "
                    f"{v.major}.{v.minor}.{v.micro}.")
        log.warning(f"  Python {PYTHON_VERSION} is now installed at {PYTHON_BIN}.")
        log.warning(f"  Re-invoke this script with: {PYTHON_BIN} init-v0.0.1.py")
        log.warning("  Remaining steps will continue with the current interpreter.")
        log.warning("")


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

    if in_local("sdrpp"):
        log.info("  sdrpp found in /usr/local — skipping build")
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

    if not in_local("sdrpp"):
        abort(f"SDR++ build completed but {SDRPP_BIN} not found.")
    log.info("  SDR++ built and installed — OK")


# ---------------------------------------------------------------------------
# Step 5 — Build FlRig from latest source
# ---------------------------------------------------------------------------

def build_flrig():
    log.info("")
    log.info("Step 5: Checking FlRig...")

    if in_local("flrig"):
        log.info("  flrig found in /usr/local — skipping build")
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

    if not in_local("flrig"):
        abort(f"FlRig build completed but {FLRIG_BIN} not found.")
    log.info("  FlRig built and installed — OK")


# ---------------------------------------------------------------------------
# Step 6 — Install Python dependencies
# ---------------------------------------------------------------------------

def install_python_deps():
    log.info("")
    log.info("Step 6: Installing Python dependencies...")

    # Use the installed Python 3.14.3 binary if available, otherwise current
    pip_python = str(PYTHON_BIN) if PYTHON_BIN.exists() else sys.executable

    for package in PYTHON_DEPS:
        log.info(f"  Installing {package}...")
        run(
            [pip_python, "-m", "pip", "install", "--upgrade", package],
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
# digirig: typically "DigiRig" or check via: python3.14 -m sounddevice
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

def check_path():
    """Abort if /usr/local/bin is not the first entry in PATH.
    This is a REQUIRED system configuration — see module docstring.
    """
    log.info("")
    log.info("Pre-flight: Checking PATH configuration...")
    path_entries = os.environ.get("PATH", "").split(":")
    if not path_entries or path_entries[0] != "/usr/local/bin":
        first = path_entries[0] if path_entries else "(empty)"
        abort(
            "/usr/local/bin MUST be the first entry in PATH before running this script.\n"
            f"  Current first entry: {first}\n"
            "  Add the following to your shell RC file (~/.bashrc, ~/.zshrc, etc.)\n"
            "  and reload it (source ~/.bashrc) before re-running:\n\n"
            "      export PATH=/usr/local/bin:$PATH"
        )
    log.info("  /usr/local/bin is first in PATH — OK")


def main():
    banner()

    check_path()
    build_openssl()
    build_python()
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
    if PYTHON_BIN.exists():
        v = sys.version_info
        if (v.major, v.minor, v.micro) < REQUIRED_PYTHON:
            log.info("")
            log.info(f"  ACTION REQUIRED: Re-invoke this script with Python {PYTHON_VERSION}:")
            log.info(f"    {PYTHON_BIN} init-v0.0.1.py")
    log.info("=" * 70)
    log.info("")


if __name__ == "__main__":
    main()

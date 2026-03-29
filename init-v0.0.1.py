#!/usr/bin/env python3
"""
init-v0.0.1.py — Ham System Initialization Script
Project: Ham System — N7PKT Integrated Ham Radio Control Platform
Author:  Dale — Hybrid RobotiX / The Accessibility Files
Version: 0.0.1

This script handles:
  Step 0 — Install required system build dependencies via apt
  Step 1 — Check/build OpenSSL 4.1 from source
  Step 2 — Check/build Python 3.14.3 from source
  Step 3 — Scaffold Ham System directory structure
  Step 4 — Check/build SDR++ from latest source
  Step 5 — Check/build FlRig from latest source
  Step 6 — Install Python dependencies into venv
  Step 7 — Verify radio serial port(s)
  Step 7.5 — Set all Python scripts executable
  Step 8 — Create startup script (start-v0.0.1.py)
  Step 9 — Create default settings file if not present

Package manager: apt/dpkg (Debian/Raspberry Pi OS)

Virtual environment: ~/Virtual/Ham-SDR-Radio (created from Python 3.14.3)
Startup script:      start-v0.0.1.py (sources venv, cds into repo, starts system)

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
STARTUP_SCRIPT   = Path("start-v0.0.1.py")

REQUIRED_PYTHON  = (3, 14, 3)

REPO_NAME        = "Ham-SDR-Radio"
VIRTUAL_DIR      = Path.home() / "Virtual"
VENV_PATH        = VIRTUAL_DIR / REPO_NAME
VENV_PYTHON      = VENV_PATH / "bin" / "python3"
VENV_PIP         = VENV_PATH / "bin" / "pip"
VENV_ACTIVATE    = VENV_PATH / "bin" / "activate"

# ---------------------------------------------------------------------------
# System Build Dependencies (installed via apt)
# These are prerequisites for building OpenSSL, Python, SDR++, and FlRig.
# ---------------------------------------------------------------------------

APT_PACKAGES = [
    # Core build tools
    "build-essential",      # gcc, g++, make
    "cmake",                # SDR++ build system
    "git",                  # Source cloning
    "wget",                 # Python tarball download
    "perl",                 # OpenSSL configure
    "autoconf",             # FlRig build system
    "automake",             # FlRig build system
    "libtool",              # FlRig build system
    "pkg-config",           # General build support

    # Python build dependencies
    "libssl-dev",           # SSL support (pre-build system OpenSSL)
    "zlib1g-dev",           # zlib compression
    "libffi-dev",           # Foreign function interface
    "libreadline-dev",      # Readline support
    "libsqlite3-dev",       # SQLite support
    "libbz2-dev",           # bzip2 support
    "liblzma-dev",          # lzma/xz support
    "libncurses5-dev",      # ncurses support
    "libgdbm-dev",          # gdbm support
    "uuid-dev",             # UUID support
    "tk-dev",               # Tkinter support

    # SDR++ dependencies
    "libglfw3-dev",         # OpenGL windowing
    "libvolk-dev",          # Vector optimized math
    "libfftw3-dev",         # FFT library
    "librtlsdr-dev",        # RTL-SDR support

    # FlRig dependencies
    "libfltk1.3-dev",       # FLTK GUI toolkit
    "libxft-dev",           # Font rendering
    "libxinerama-dev",      # Multi-monitor support

    # Audio
    "libasound2-dev",       # ALSA audio
    "portaudio19-dev",      # PortAudio (for pyaudio)

    # Serial port
    "python3-serial",       # pyserial bootstrap (system level)
]

# ---------------------------------------------------------------------------
# Supported Radio Model Catalogue
# Defines available radio models and their default CAT parameters.
# This is the master catalogue of supported hardware — distinct from the
# RADIOS list in settings, which defines the user's actual connected radios.
# Add new models here as support is developed.
# ---------------------------------------------------------------------------

RADIO_PROFILES = {
    "1": {
        "name":        "Xiegu G90",      # Radio model name
        "model":       "g90",
        "protocol":    "CI-V",
        "baud":        19200,
        "port_hint":   "/dev/ttyUSB0",
        "notes":       "DO NOT use hamlib — hard-transmit bug. Use direct CI-V via pyserial.",
    },
    # Future radios go here:
    # "2": { "name": "Icom IC-7300", "model": "ic7300", ... },
    # "3": { "name": "Yaesu FT-891", "model": "ft891",  ... },
}

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

# Radio serial port candidates (checked in order)
RADIO_PORT_CANDIDATES = [
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
# Step 0 — Install system build dependencies via apt
# ---------------------------------------------------------------------------

def install_apt_deps():
    log.info("")
    log.info("Step 0: Installing system build dependencies via apt...")

    # Update package list first
    log.info("  Running apt-get update...")
    result = subprocess.run(
        ["sudo", "apt-get", "update", "-qq"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        abort(f"apt-get update failed:\n{result.stderr.strip()}")

    # Check which packages are already installed
    missing = []
    for pkg in APT_PACKAGES:
        result = subprocess.run(
            ["dpkg", "-s", pkg],
            capture_output=True, text=True,
        )
        if result.returncode != 0 or "Status: install ok installed" not in result.stdout:
            missing.append(pkg)

    if not missing:
        log.info("  All system build dependencies already installed — OK")
        return

    log.info(f"  Installing {len(missing)} missing package(s):")
    for pkg in missing:
        log.info(f"    {pkg}")

    result = subprocess.run(
        ["sudo", "apt-get", "install", "-y", "--no-install-recommends"] + missing,
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        log.error(f"  stdout: {result.stdout.strip()}")
        log.error(f"  stderr: {result.stderr.strip()}")
        abort("apt-get install failed. Check your network connection and apt sources.")

    log.info(f"  All system build dependencies installed — OK")


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
    # Explicitly set CFLAGS, LDFLAGS, and PKG_CONFIG_PATH so that
    # Python's configure finds our /usr/local OpenSSL 4.1 build and
    # not any older system OpenSSL. --with-openssl alone is not enough
    # on all systems — the linker and pkg-config must also be directed.
    openssl_inc = OPENSSL_PREFIX / "include"
    openssl_lib = OPENSSL_PREFIX / "lib"
    openssl_lib64 = OPENSSL_PREFIX / "lib64"
    openssl_pkgconfig = openssl_lib / "pkgconfig"
    openssl_pkgconfig64 = openssl_lib64 / "pkgconfig"

    # Use lib64 if lib doesn't exist (some builds install there)
    lib_path = str(openssl_lib64) if openssl_lib64.exists() and not openssl_lib.exists()                else str(openssl_lib)
    pkg_path = str(openssl_pkgconfig64) if openssl_pkgconfig64.exists() and not openssl_pkgconfig.exists()                else str(openssl_pkgconfig)

    env = os.environ.copy()
    env["CFLAGS"]         = f"-I{openssl_inc}"
    env["LDFLAGS"]        = f"-L{lib_path} -Wl,-rpath,{lib_path}"
    env["PKG_CONFIG_PATH"] = pkg_path

    result = subprocess.run(
        ["./configure",
         f"--prefix={PYTHON_PREFIX}",
         "--enable-optimizations",
         "--with-lto",
         f"--with-openssl={OPENSSL_PREFIX}",
         f"--with-openssl-rpath=auto"],
        cwd=PYTHON_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log.error(f"  stdout: {result.stdout.strip()}")
        log.error(f"  stderr: {result.stderr.strip()}")
        abort(f"Python configure failed — check OpenSSL 4.1 build at {OPENSSL_PREFIX}")
    log.info("  Python configure — OK")

    log.info(f"  Building Python with {cpu_jobs()} jobs (this will take a while)...")
    result = subprocess.run(
        ["make", f"-j{cpu_jobs()}"],
        cwd=PYTHON_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log.error(f"  stdout: {result.stdout.strip()}")
        log.error(f"  stderr: {result.stderr.strip()}")
        abort("Python build failed — see output above.")
    log.info("  Python build — OK")

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
# Step 6 — Install Python dependencies into venv
# ---------------------------------------------------------------------------

def install_python_deps():
    log.info("")
    log.info("Step 6: Installing Python dependencies into venv...")

    if not VENV_PIP.exists():
        abort(f"Venv pip not found at {VENV_PIP}. Ensure Step 2.5 completed successfully.")

    log.info("  Upgrading pip in venv...")
    run([str(VENV_PIP), "install", "--upgrade", "pip"], desc="pip upgrade")

    for package in PYTHON_DEPS:
        log.info(f"  Installing {package}...")
        run(
            [str(VENV_PIP), "install", "--upgrade", package],
            desc=f"pip install {package}",
        )
    log.info("  All Python dependencies installed into venv — OK")


# ---------------------------------------------------------------------------
# Step 7 — Verify radio serial port
# ---------------------------------------------------------------------------

def verify_g90_port():
    log.info("")
    log.info("Step 7: Verifying radio serial port...")
    found = None
    for port in RADIO_PORT_CANDIDATES:
        if Path(port).exists():
            found = port
            break

    if found:
        log.info(f"  Radio serial port found: {found} — OK")
        log.info("  NOTE: Verify this is the correct port and update the RADIOS list in settings if needed.")
    else:
        log.warning("  WARNING: No radio serial port detected on any candidate path:")
        for port in RADIO_PORT_CANDIDATES:
            log.warning(f"    {port}")
        log.warning("  The radio may not be connected or may appear on a different port.")
        log.warning(f"  Update the RADIOS list in {SETTINGS_PATH} when the radio is connected.")
        log.warning("  Continuing — this is non-fatal.")


# ---------------------------------------------------------------------------
# Step 9 — Create default settings file
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

# Select active interface: "de19" (ACC port / DE-19) or "digirig"
# ---------------------------------------------------------------------------
# Radio Configuration
# One dict per connected radio — each operates fully independently.
# Add additional radios by appending entries to this list.
# Radio index is used in MQTT topics: console/radio/{{index}}/...
# ---------------------------------------------------------------------------

RADIOS = [
    {{
        "index":           1,
        "name":            "{radio_name}",
        "model":           "{radio_model}",
        "port":            "{rig_port}",   # Serial port for CAT control
        "baud":            {rig_baud},     # CAT baud rate
        "poll_interval":   0.25,           # CAT polling interval in seconds
        "audio_interface": "de19",         # "de19" or "digirig"
        "audio_device":    "your-audio-device",  # Update to match radio audio device
    }},
    # Add additional radios here:
    # {{
    #     "index":           2,
    #     "name":            "...",
    #     "model":           "...",
    #     "port":            "/dev/ttyUSB1",
    #     "baud":            ...,
    #     "poll_interval":   0.25,
    #     "audio_interface": "...",
    #     "audio_device":    "...",
    # }},
]

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




# ---------------------------------------------------------------------------
# Step 7.5 - Set all Python scripts executable
# ---------------------------------------------------------------------------

def make_scripts_executable():
    log.info("")
    log.info("Step 7.5: Setting all Python scripts executable...")

    repo_path = Path(__file__).resolve().parent
    scripts = list(repo_path.rglob("*.py"))

    if not scripts:
        log.info("  No Python scripts found.")
        return

    for script in sorted(scripts):
        current = script.stat().st_mode
        new_mode = current | 0o755
        if current != new_mode:
            script.chmod(new_mode)
            log.info(f"  chmod +x {script.relative_to(repo_path)}")
        else:
            log.info(f"  already executable: {script.relative_to(repo_path)}")

    log.info(f"  {len(scripts)} script(s) set executable -- OK")

# ---------------------------------------------------------------------------
# Step 8 — Create startup script
# ---------------------------------------------------------------------------

def create_startup_script():
    log.info("")
    log.info("Step 8: Creating startup script...")

    if STARTUP_SCRIPT.exists():
        log.info(f"  {STARTUP_SCRIPT} already exists -- skipping")
        return

    repo_path = Path(__file__).resolve().parent

    lines = [
        '#!/usr/bin/env python3',
        '"""',
        'start-v0.0.1.py -- Ham System Startup Script',
        'Project: Ham System -- N7PKT Integrated Ham Radio Control Platform',
        'Author:  Dale -- Hybrid RobotiX / The Accessibility Files',
        'Version: 0.0.1',
        '',
        'Activates the Ham-SDR-Radio virtual environment, changes into the',
        'repo directory, and starts the Ham System.',
        '',
        'Usage: python3 start-v0.0.1.py',
        '"""',
        '',
        'VERSION = "0.0.1"',
        '',
        'import os',
        'import sys',
        'from pathlib import Path',
        '',
        f'REPO_PATH     = Path("{repo_path}")',
        f'VENV_PATH     = Path("{VENV_PATH}")',
        'VENV_PYTHON   = VENV_PATH / "bin" / "python3"',
        'VENV_ACTIVATE = VENV_PATH / "bin" / "activate"',
        '',
        '',
        'def main():',
        '    print("=" * 70)',
        '    print("  Ham System Startup")',
        '    print("  N7PKT Integrated Ham Radio Control Platform")',
        '    print(f"  Version {VERSION}")',
        '    print("  Hybrid RobotiX / The Accessibility Files")',
        '    print("  I. WILL. NEVER. GIVE. UP. OR. SURRENDER.")',
        '    print("=" * 70)',
        '    print()',
        '',
        '    if not VENV_PYTHON.exists():',
        '        print(f"FATAL: Virtual environment not found at {VENV_PATH}")',
        '        print( "       Run init-v0.0.1.py to initialize the system first.")',
        '        sys.exit(1)',
        '',
        '    if not REPO_PATH.exists():',
        '        print(f"FATAL: Repo not found at {REPO_PATH}")',
        '        sys.exit(1)',
        '',
        '    os.chdir(REPO_PATH)',
        '    print(f"  Working directory : {REPO_PATH}")',
        '    print(f"  Virtual env       : {VENV_PATH}")',
        '    print(f"  Python            : {VENV_PYTHON}")',
        '    print()',
        '',
        '    # Re-invoke under venv Python if not already running inside it',
        '    if Path(sys.executable).resolve() != Path(str(VENV_PYTHON)).resolve():',
        '        print("  Activating virtual environment...")',
        '        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON)] + sys.argv)',
        '',
        '    # Running inside venv from here',
        '    print("  Virtual environment active -- OK")',
        '    print()',
        '    print("  Ham System starting...")',
        '    print("  (Main entry point not yet implemented)")',
        '',
        '',
        'if __name__ == "__main__":',
        '    main()',
    ]

    STARTUP_SCRIPT.write_text("\n".join(lines) + "\n")
    STARTUP_SCRIPT.chmod(0o755)
    log.info(f"  {STARTUP_SCRIPT} created -- OK")
    log.info("")
    log.info("  To start the Ham System:")
    log.info(f"    python3 {STARTUP_SCRIPT}")
    log.info("")
    log.info("  To activate the venv manually:")
    log.info(f"    source {VENV_ACTIVATE}")
    log.info(f"    cd {repo_path}")

def create_settings(radio_profile: dict):
    log.info("")
    log.info("Step 9: Checking settings file...")
    if SETTINGS_PATH.exists():
        log.info(f"  {SETTINGS_PATH} already exists — skipping")
        log.info(f"  NOTE: If you changed radio selection, update the RADIOS list")
        log.info(f"        in {SETTINGS_PATH} manually.")
        return
    log.info(f"  Creating default settings file: {SETTINGS_PATH}")
    settings_content = DEFAULT_SETTINGS.format(
        radio_name  = radio_profile["name"],
        radio_model = radio_profile["model"],
        rig_baud    = radio_profile["baud"],
        rig_port    = radio_profile["port_hint"],
    )
    SETTINGS_PATH.write_text(settings_content)
    log.info(f"  {SETTINGS_PATH} created for {radio_profile['name']} — OK")
    log.info("  IMPORTANT: Review and edit settings before running Ham System.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def select_radio() -> dict:
    """
    Present the user with a menu of supported radio models and return the
    selected profile dict for use as the initial RADIOS entry in settings.
    Additional radios can be added manually to the RADIOS list in settings
    after initialization. Currently one radio model is supported.
    """
    log.info("")
    log.info("Radio Selection:")
    log.info("  The following radios are currently supported:")
    log.info("")
    for key, profile in RADIO_PROFILES.items():
        log.info(f"  [{key}] {profile['name']}")
        if profile.get("notes"):
            log.info(f"       Note: {profile['notes']}")
    log.info("")

    if len(RADIO_PROFILES) == 1:
        # Only one radio available — auto-select with confirmation
        key = next(iter(RADIO_PROFILES))
        profile = RADIO_PROFILES[key]
        log.info(f"  Only one radio currently supported: {profile['name']}")
        try:
            answer = input(f"  Use {profile['name']}? [Y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            log.info("")
            abort("Radio selection cancelled.")
        if answer in ("", "y"):
            log.info(f"  Selected: {profile['name']} — OK")
            return profile
        else:
            abort("No radio selected. Cannot continue without a supported radio.")
    else:
        # Multiple radios — present full menu
        while True:
            try:
                answer = input("  Enter selection: ").strip()
            except (EOFError, KeyboardInterrupt):
                log.info("")
                abort("Radio selection cancelled.")
            if answer in RADIO_PROFILES:
                profile = RADIO_PROFILES[answer]
                log.info(f"  Selected: {profile['name']} — OK")
                return profile
            log.warning(f"  Invalid selection '{answer}' — please choose from the list above.")


# Line appended to shell RC file if the user accepts
PATH_EXPORT_LINE = "export PATH=/usr/local/bin:$PATH"
FISH_PATH_LINE   = "fish_add_path /usr/local/bin"

# Known shell RC files in detection order
SHELL_RC_MAP = {
    "bash": Path.home() / ".bashrc",
    "zsh":  Path.home() / ".zshrc",
    "fish": Path.home() / ".config" / "fish" / "config.fish",
    "ksh":  Path.home() / ".kshrc",
    "dash": Path.home() / ".profile",
}


def detect_shell_rc():
    """
    Detect the user's current shell from the SHELL environment variable.
    Returns (shell_name, rc_path) or (None, None) if not detected.
    """
    shell_bin = os.environ.get("SHELL", "")
    shell_name = Path(shell_bin).name if shell_bin else None
    rc_path = SHELL_RC_MAP.get(shell_name)
    return shell_name, rc_path


def offer_rc_edit(rc_path, shell_name):
    """
    Offer to add the PATH export line to the user's shell RC file.
    Returns True if the line was added or was already present.
    Returns False if the user declined.
    """
    export_line = FISH_PATH_LINE if shell_name == "fish" else PATH_EXPORT_LINE

    if rc_path.exists():
        existing = rc_path.read_text()
        if "/usr/local/bin" in existing:
            log.info(f"  /usr/local/bin already referenced in {rc_path} — no edit needed")
            return True

    log.info(f"  Detected shell : {shell_name}")
    log.info(f"  RC file        : {rc_path}")
    log.info(f"  Line to add    : {export_line}")
    log.info("")

    try:
        answer = input(f"  Add this line to {rc_path}? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        log.info("")
        return False

    if answer == "y":
        with rc_path.open("a") as f:
            f.write(f"\n# Added by Ham System init-v0.0.1.py\n{export_line}\n")
        log.info(f"  Written to {rc_path} — OK")
        log.info(f"  Reload with: source {rc_path}")
        return True
    else:
        log.info("  Edit declined.")
        return False


def check_path():
    """
    Verify /usr/local/bin is first in PATH.
    If not, detect the user's shell and offer to edit the RC file automatically.
    Aborts with clear instructions to reload and re-run.
    """
    log.info("")
    log.info("Pre-flight: Checking PATH configuration...")
    path_entries = os.environ.get("PATH", "").split(":")

    if path_entries and path_entries[0] == "/usr/local/bin":
        log.info("  /usr/local/bin is first in PATH — OK")
        return

    first = path_entries[0] if path_entries else "(empty)"
    log.warning(f"  /usr/local/bin is NOT first in PATH (current first: {first})")
    log.warning("  This is a required configuration for the Ham System.")
    log.info("")

    shell_name, rc_path = detect_shell_rc()

    if shell_name and rc_path:
        edited = offer_rc_edit(rc_path, shell_name)
        if edited:
            abort(
                "PATH updated. Reload your shell RC file and re-run this script:\n"
                f"      source {rc_path}\n"
                f"      python3 init-v0.0.1.py"
            )
    else:
        log.warning(
            f"  Could not detect shell RC file "
            f"(SHELL={os.environ.get('SHELL', 'not set')})"
        )
        log.warning("  Manually add the following to your shell RC file:")
        log.warning(f"      {PATH_EXPORT_LINE}")

    abort(
        "/usr/local/bin must be first in PATH before running this script.\n"
        "  Edit your shell RC file, reload it, and re-run."
    )


def main():
    banner()

    check_path()
    install_apt_deps()
    radio_profile = select_radio()
    build_openssl()
    build_python()
    create_venv()
    scaffold_directories()
    build_sdrpp()
    build_flrig()
    install_python_deps()
    verify_g90_port()
    make_scripts_executable()
    create_startup_script()
    create_settings(radio_profile)

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

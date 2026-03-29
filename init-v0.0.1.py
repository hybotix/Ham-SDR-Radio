#!/usr/bin/env python3
"""
init-v0.0.1.py — Ham System Initialization Script
Project: Ham System — Ham System Integrated Ham Radio Control Platform
Author:  Dale — Hybrid RobotiX / The Accessibility Files
Version: 0.0.1

This script handles:
  Pre-flight — Verify Debian-based platform (dpkg required)
  Pre-flight — Validate operator license (MUST pass before anything else)
  Step 0 — Install required system build dependencies via apt
  Step 1 — Check/build OpenSSL 3.4.x from source
  Step 2 — Check/build Python 3.14.3 from source
  Step 3 — Scaffold Ham System directory structure
  Step 4 — Check/build SDR++ from latest source
  Step 5 — Check/build FlRig from latest source
  Step 6 — Install Python dependencies into venv
  Step 7 — Verify radio serial port(s)
  Step 7.5 — Set all Python scripts executable
  Step 8 — Create startup script (start-v0.0.1.py)
  Step 9 — Create default settings file if not present (JSON format)
  Step 9.5 — Run license advisor to verify callsign
  Step 10 — Create unversioned symlinks to current scripts

Package manager: apt/dpkg required. Debian-based systems ONLY.
                 (Debian, Raspberry Pi OS, Ubuntu, and derivatives)
                 Other systems are not supported and will not be.

Virtual environment: ~/Virtual/Ham-SDR-Radio (created from Python 3.14.3)
Startup script:      start-v0.0.1.py (sources venv, cds into repo, starts system)

Safe to re-run — completed steps are automatically skipped.
Aborts immediately with a clear error if any required build fails.
NO bash or shell scripts. Python only.

REQUIRED: /usr/local/bin must appear in PATH before any system directories
          (/usr/bin, /bin, etc.). User directories (~/bin, nvm, etc.) may
          appear before it. Add this to your shell RC file if needed:

              export PATH=/usr/local/bin:$PATH

          Place this line AFTER any other PATH-modifying tools (nvm, etc.)
          so it always wins over system directories.

NOTE: This script may be initially invoked with the system Python to bootstrap
      the build. Once Python 3.14.3 is built and installed, re-invoke with it.
"""

VERSION = "0.0.1"

import os
import sys
import subprocess
import shutil
import logging
import json
import re
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
log_filename = LOG_DIR / f"init-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.log"

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

OPENSSL_VERSION  = "3.4"
OPENSSL_REPO     = "https://github.com/openssl/openssl.git"
OPENSSL_TAG      = "openssl-3.4.1"
OPENSSL_DIR      = Path("build") / "openssl"
OPENSSL_PREFIX   = LOCAL
OPENSSL_BIN      = LOCAL_BIN / "openssl"  # openssl 3.4.x

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
SETTINGS_PATH    = Path("config") / "settings-v0.0.1.json"
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
    "libzstd-dev",          # Zstandard compression
    "librtlsdr-dev",        # RTL-SDR support
    "libairspy-dev",        # Airspy support
    "libairspyhf-dev",      # Airspy HF+ support
    "libhackrf-dev",        # HackRF support
    "libbladerf-dev",       # BladeRF support
    "liblimesuite-dev",     # LimeSDR support
    "libad9361-dev",        # PlutoSDR/AD9361 support
    "libiio-dev",           # Industrial I/O (PlutoSDR)
    "libusb-1.0-0-dev",     # USB support
    "libnng-dev",           # Networking (SDR++ network sink)
    "librtaudio-dev",       # RtAudio (SDR++ audio source)

    # FlRig dependencies
    "libfltk1.3-dev",       # FLTK GUI toolkit
    "libxft-dev",           # Font rendering
    "libxinerama-dev",      # Multi-monitor support
    "libudev-dev",          # udev support (FlRig HID/cmedia)

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
        "topic_name":  "radio_1",        # Used in MQTT topics — user should customize
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
    "certifi",          # CA certificates for SSL verification
    "requests",          # HTTP for license advisor API queries
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
    log.info("  Ham System Integrated Ham Radio Control Platform")
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


def _get_callsign_for_validation() -> str:
    """
    Get callsign for license validation.
    Reads from settings if present, otherwise prompts the user.
    """
    if SETTINGS_PATH.exists():
        try:
            settings = json.loads(SETTINGS_PATH.read_text())
            cs = settings.get("operator", {}).get("callsign", "")
            if cs and cs != "YOUR_CALLSIGN":
                log.info(f"  Using callsign from settings: {cs}")
                return cs
        except Exception:
            pass

    log.info("")
    log.info("  Enter your amateur radio callsign to begin.")
    log.info("  This will be validated against FCC/ISED/Ofcom databases.")
    log.info("")
    try:
        cs = input("  Callsign: ").strip().upper()
    except (EOFError, KeyboardInterrupt):
        log.info("")
        abort("Callsign entry cancelled.")
    if not cs:
        abort("No callsign entered. A valid callsign is required to proceed.")
    return cs


CALLOOK_API   = "https://callook.info/{callsign}/json"
LICENSE_CACHE = Path("config") / "license_cache-v0.0.1.json"

FCC_CLASS_MAP = {
    "T": "Technician",
    "G": "General",
    "A": "Advanced",
    "E": "Amateur Extra",
    "N": "Novice",
    "P": "Technician Plus",
}


def _detect_authority(callsign: str) -> str:
    cs = callsign.strip().upper()
    if re.match(r"^[AKNW]", cs):           return "FCC"
    if re.match(r"^V[AEY]|^VO", cs):       return "ISED"
    if re.match(r"^[GM2]", cs):            return "OFCOM"
    return None


def _lookup_fcc(callsign: str) -> dict:
    url = CALLOOK_API.format(callsign=callsign.upper())
    log.info("  Querying callook.info...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HamSystem/0.0.1"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        abort(f"Network error querying callook.info: {e}\n  Check your internet connection and re-run.")
    except json.JSONDecodeError as e:
        abort(f"Invalid response from callook.info: {e}")

    status = data.get("status", "").upper()
    if status == "INVALID":
        abort(
            f"Callsign '{callsign.upper()}' not found in FCC database.\n"
            f"  Verify the callsign is correct and the license is active.\n"
            f"  Check: https://wireless2.fcc.gov/UlsApp/UlsSearch/searchAmateur.jsp"
        )
    if status != "VALID":
        abort(f"Unexpected license status '{status}' for '{callsign.upper()}'. License may be expired or inactive.")

    raw_class = data.get("current", {}).get("operClass", "")
    import datetime as _dt
    return {
        "callsign":      data.get("current", {}).get("callsign", callsign.upper()),
        "authority":     "FCC",
        "license_class": FCC_CLASS_MAP.get(raw_class, f"Unknown ({raw_class})"),
        "status":        status,
        "expiry":        data.get("otherInfo", {}).get("expiryDate", ""),
        "grid_square":   data.get("location", {}).get("gridsquare", ""),
        "name":          data.get("name", ""),
        "last_verified": _dt.datetime.now(_dt.timezone.utc).isoformat(),
    }


def _infer_ofcom(callsign: str) -> dict:
    import datetime as _dt
    cs = callsign.strip().upper()
    if cs.startswith("2"):          lc = "Intermediate"
    elif re.match(r"^M[36]", cs):  lc = "Foundation"
    else:                           lc = "Full"
    return {
        "callsign": cs, "authority": "OFCOM", "license_class": lc,
        "status": "VALID", "expiry": "", "grid_square": "", "name": "",
        "last_verified": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "notes": "Licence class inferred from callsign structure.",
    }


def validate_license(callsign: str) -> dict:
    """
    Validate operator callsign. FIRST step -- nothing proceeds without this.
    Aborts if callsign is not found or cannot be verified.
    """
    log.info("")
    log.info("Step 0: Validating operator license...")
    log.info(f"  Callsign: {callsign.upper()}")

    authority = _detect_authority(callsign)
    if not authority:
        abort(
            f"Cannot determine licensing authority for '{callsign}'.\n"
            f"  Supported prefixes:\n"
            f"    US (FCC):      A, K, N, W\n"
            f"    Canada (ISED): VE, VA, VY, VO\n"
            f"    UK (Ofcom):    G, M, 2"
        )

    log.info(f"  Authority: {authority}")

    if authority == "FCC":
        license_data = _lookup_fcc(callsign)
    elif authority == "ISED":
        abort(
            "ISED (Canada) lookup requires the local ISED database cache.\n"
            "  Run license_advisor-v0.0.1.py standalone first, then re-run init."
        )
    else:
        license_data = _infer_ofcom(callsign)

    log.info(f"  Name         : {license_data.get('name', 'N/A')}")
    log.info(f"  Class        : {license_data['license_class']}")
    log.info(f"  Status       : {license_data['status']}")
    if license_data.get("expiry"):
        log.info(f"  Expiry       : {license_data['expiry']}")
    if license_data.get("grid_square"):
        log.info(f"  Grid Square  : {license_data['grid_square']}")

    LICENSE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    LICENSE_CACHE.write_text(json.dumps(license_data, indent=4) + "\n")
    log.info(f"  License cached to {LICENSE_CACHE}")
    log.info("  License validation -- OK")
    return license_data




def check_platform():
    """
    Abort immediately if not running on a Debian-based system.
    apt/dpkg is required. Other systems are not supported.
    """
    log.info("")
    log.info("Pre-flight: Checking platform...")

    if not Path("/usr/bin/dpkg").exists():
        abort(
            "This system does not appear to be Debian-based (dpkg not found).\n"
            "  Supported: Debian, Raspberry Pi OS, Ubuntu, and derivatives.\n"
            "  Unsupported systems are COMPLETELY ON THEIR OWN.\n"
            "  No support will be provided for non-Debian-based systems.\n"
            "  Do not open issues. Do not ask for help. This is final."
        )

    # Read /etc/os-release for display purposes
    os_release = {}
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                os_release[k] = v.strip('"')
    except Exception:
        pass

    name = os_release.get("PRETTY_NAME", "Unknown Debian-based system")
    log.info(f"  Platform: {name} — OK")



def validate_operator_license():
    """
    Validate the operator's callsign before any installation proceeds.
    Prompts for callsign if not already in settings, then invokes
    license_advisor-v0.0.1.py to verify against the appropriate authority.
    Aborts if the callsign is not found.
    """
    log.info("")
    log.info("Pre-flight: Validating operator license...")

    # Check if callsign is already configured
    callsign = None
    if SETTINGS_PATH.exists():
        try:
            settings = json.loads(SETTINGS_PATH.read_text())
            callsign = settings.get("operator", {}).get("callsign", "").strip()
            if callsign and callsign != "YOUR_CALLSIGN":
                log.info(f"  Using callsign from settings: {callsign}")
            else:
                callsign = None
        except Exception:
            callsign = None

    if not callsign:
        log.info("  No callsign configured yet.")
        try:
            callsign = input("  Enter your amateur radio callsign: ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            log.info("")
            abort("License validation cancelled.")

    if not callsign:
        abort("A valid callsign is required to proceed.")

    # Invoke license_advisor
    advisor = Path(__file__).resolve().parent / "license_advisor-v0.0.1.py"
    if not advisor.exists():
        abort(
            f"license_advisor-v0.0.1.py not found at {advisor}.\n"
            "  Cannot validate license. Ensure the file is present and re-run."
        )

    log.info(f"  Validating callsign: {callsign}")
    result = subprocess.run(
        [sys.executable, str(advisor), "--callsign", callsign],
        capture_output=False,  # Let output stream to console
        text=True,
    )
    if result.returncode != 0:
        abort(
            f"License validation failed for callsign '{callsign}'.\n"
            "  Cannot proceed without a valid amateur radio license."
        )
    log.info("  License validation passed — OK")

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



def _openssl_target() -> str:
    """
    Return the correct OpenSSL Configure target for the current architecture.
    Supports x86_64 (Linux/Ubuntu) and aarch64 (Raspberry Pi / ARM64).
    """
    import platform
    machine = platform.machine()
    targets = {
        "x86_64":  "linux-x86_64",
        "aarch64": "linux-aarch64",
        "armv7l":  "linux-armv4",
    }
    target = targets.get(machine)
    if not target:
        abort(
            f"Unsupported architecture '{machine}' for OpenSSL configure. "
            f"Add a target mapping to _openssl_target() and re-run."
        )
    log.info(f"  Detected architecture: {machine} -> OpenSSL target: {target}")
    return target


# ---------------------------------------------------------------------------
# Step 1 — Build OpenSSL 3.4.x from source
# ---------------------------------------------------------------------------

def build_openssl():
    log.info("")
    log.info("Step 1: Checking OpenSSL 3.4.x...")

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
         _openssl_target()],
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
    # Python's configure finds our /usr/local OpenSSL 3.4.x build and
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
        abort(f"Python configure failed — check OpenSSL 3.4.x build at {OPENSSL_PREFIX}")
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


# ---------------------------------------------------------------------------
# Step 2.5 - Create Python virtual environment
# ---------------------------------------------------------------------------

def create_venv():
    log.info("")
    log.info("Step 2.5: Checking Python virtual environment...")

    if not VIRTUAL_DIR.exists():
        log.info(f"  Creating {VIRTUAL_DIR}...")
        VIRTUAL_DIR.mkdir(parents=True, exist_ok=True)
        log.info(f"  {VIRTUAL_DIR} created -- OK")
    else:
        log.info(f"  {VIRTUAL_DIR} exists -- OK")

    if VENV_PYTHON.exists():
        result = subprocess.run(
            [str(VENV_PYTHON), "--version"],
            capture_output=True, text=True,
        )
        installed = result.stdout.strip() + result.stderr.strip()
        if PYTHON_VERSION in installed:
            log.info(f"  Venv already exists at {VENV_PATH} -- skipping")
            return
        log.warning(f"  Venv exists but is wrong Python version -- recreating...")
        import shutil as _shutil
        _shutil.rmtree(VENV_PATH)

    log.info(f"  Creating venv: {VENV_PATH}")
    run(
        [str(PYTHON_BIN), "-m", "venv", str(VENV_PATH)],
        desc=f"python3.14 -m venv {VENV_PATH}",
    )
    if not VENV_PYTHON.exists():
        abort(f"Venv creation completed but {VENV_PYTHON} not found.")
    log.info(f"  Venv created at {VENV_PATH} -- OK")
    log.info(f"  Activate with: source {VENV_ACTIVATE}")


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
    log.info("  Building SDR++ with ALL supported source modules enabled.")
    log.info("  This ensures SDR++ works with any supported SDR hardware,")
    log.info("  not just the primary radio used by this system.")
    run(
        ["cmake", "..",
         f"-DCMAKE_INSTALL_PREFIX={OPENSSL_PREFIX}",
         "-DOPT_BUILD_AUDIO_SINK=ON",
         "-DOPT_BUILD_SOAPY_SOURCE=OFF",
         "-DOPT_BUILD_AIRSPY_SOURCE=ON",
         "-DOPT_BUILD_AIRSPYHF_SOURCE=ON",
         "-DOPT_BUILD_BLADERF_SOURCE=ON",
         "-DOPT_BUILD_FILE_SOURCE=ON",
         "-DOPT_BUILD_HACKRF_SOURCE=ON",
         "-DOPT_BUILD_LIMESDR_SOURCE=ON",
         "-DOPT_BUILD_MIRISDR_SOURCE=OFF",
         "-DOPT_BUILD_PLUTOSDR_SOURCE=ON",
         "-DOPT_BUILD_RFSPACE_SOURCE=OFF",
         "-DOPT_BUILD_RTL_SDR_SOURCE=ON",
         "-DOPT_BUILD_RTL_TCP_SOURCE=ON",
         "-DOPT_BUILD_SPYSERVER_SOURCE=ON",
         "-DOPT_BUILD_USRP_SOURCE=OFF",
         ],
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

# ---------------------------------------------------------------------------
# Step 7.5 - Set shebang and make all Python scripts executable
# ---------------------------------------------------------------------------

SHEBANG = "#!/usr/bin/env python3"


def make_scripts_executable():
    """
    Ensure all Python scripts in the repo:
    1. Have #!/usr/bin/env python3 as the first line
    2. Are set executable (chmod +x)
    """
    log.info("")
    log.info("Step 7.5: Checking shebangs and setting scripts executable...")

    repo_path = Path(__file__).resolve().parent
    scripts = list(repo_path.rglob("*.py"))

    if not scripts:
        log.info("  No Python scripts found.")
        return

    for script in sorted(scripts):
        text = script.read_text(encoding="utf-8")
        if not text.startswith(SHEBANG):
            log.info(f"  Adding shebang: {script.relative_to(repo_path)}")
            script.write_text(SHEBANG + "\n" + text, encoding="utf-8")
        else:
            log.info(f"  Shebang OK: {script.relative_to(repo_path)}")

        current = script.stat().st_mode
        if not (current & 0o111):
            script.chmod(current | 0o755)
            log.info(f"  chmod +x: {script.relative_to(repo_path)}")

    log.info(f"  {len(scripts)} script(s) verified and set executable -- OK")


# ---------------------------------------------------------------------------
# Step 8 - Create startup script
# ---------------------------------------------------------------------------

def create_startup_script():
    log.info("")
    log.info("Step 8: Creating startup script...")

    if STARTUP_SCRIPT.exists():
        log.info(f"  {STARTUP_SCRIPT} already exists -- skipping")
        return

    repo_path = Path(__file__).resolve().parent

    lines = [
        "#!/usr/bin/env python3",
        '"""',
        "start-v0.0.1.py -- Ham System Startup Script",
        "Project: Ham System -- Integrated Ham Radio Control Platform",
        "Author:  Dale -- Hybrid RobotiX / The Accessibility Files",
        "Version: 0.0.1",
        "",
        "Activates the Ham-SDR-Radio virtual environment, changes into the",
        "repo directory, and starts the Ham System.",
        "",
        "Usage: python3 start-v0.0.1.py",
        '"""',
        "",
        'VERSION = "0.0.1"',
        "",
        "import os",
        "import sys",
        "from pathlib import Path",
        "",
        f'REPO_PATH     = Path("{repo_path}")',
        f'VENV_PATH     = Path("{VENV_PATH}")',
        'VENV_PYTHON   = VENV_PATH / "bin" / "python3"',
        'VENV_ACTIVATE = VENV_PATH / "bin" / "activate"',
        "",
        "",
        "def main():",
        '    print("=" * 70)',
        '    print("  Ham System Startup")',
        '    print("  Integrated Ham Radio Control Platform")',
        '    print(f"  Version {VERSION}")',
        '    print("  Hybrid RobotiX / The Accessibility Files")',
        '    print("  I. WILL. NEVER. GIVE. UP. OR. SURRENDER.")',
        '    print("=" * 70)',
        '    print()',
        "",
        "    if not VENV_PYTHON.exists():",
        '        print(f"FATAL: Virtual environment not found at {VENV_PATH}")',
        '        print( "       Run init-v0.0.1.py to initialize the system first.")',
        "        sys.exit(1)",
        "",
        "    if not REPO_PATH.exists():",
        '        print(f"FATAL: Repo not found at {REPO_PATH}")',
        "        sys.exit(1)",
        "",
        "    os.chdir(REPO_PATH)",
        '    print(f"  Working directory : {REPO_PATH}")',
        '    print(f"  Virtual env       : {VENV_PATH}")',
        '    print(f"  Python            : {VENV_PYTHON}")',
        '    print()',
        "",
        "    if Path(sys.executable).resolve() != Path(str(VENV_PYTHON)).resolve():",
        '        print("  Activating virtual environment...")',
        "        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON)] + sys.argv)",
        "",
        "    # Running inside venv from here",
        '    print("  Virtual environment active -- OK")',
        '    print()',
        '    print("  Ham System starting...")',
        '    print("  (Main entry point not yet implemented)")',
        "",
        "",
        'if __name__ == "__main__":',
        "    main()",
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



DEFAULT_SETTINGS = {
    "_version": "0.0.1",
    "_description": "Ham System Configuration — Ham System Integrated Ham Radio Control Platform",
    "operator": {
        "callsign":    "YOUR_CALLSIGN",
        "grid_square": ""
    },
    "radios": [
        {
            "index":           1,
            "name":            "{radio_name}",
            "topic_name":      "radio_1",
            "model":           "{radio_model}",
            "port":            "{rig_port}",
            "baud":            "{rig_baud}",
            "poll_interval":   0.25,
            "audio_interface": "de19",
            "audio_device":    "your-audio-device"
        }
    ],
    "wsjtx": {
        "udp_host": "127.0.0.1",
        "udp_port": 2237
    },
    "mqtt": {
        "host":    "localhost",
        "port":    1883,
        "enabled": True
    },
    "logging": {
        "db_path":   "logs/qso_log.db",
        "log_level": "INFO"
    },
    "aprs": {
        "enabled":   False,
        "interval":  600,
        "comment":   "Hybrid RobotiX Mobile Station",
        "freq_hz":   144390000
    },
    "tx_guard": {
        "enabled": True
    }
}


def create_settings(radio_profile: dict):
    log.info("")
    log.info("Step 9: Checking settings file...")

    if SETTINGS_PATH.exists():
        log.info(f"  {SETTINGS_PATH} already exists — skipping")
        log.info(f"  NOTE: If you changed radio selection, update the RADIOS list")
        log.info(f"        in {SETTINGS_PATH} manually.")
        return

    log.info(f"  Creating default settings file: {SETTINGS_PATH}")

    settings = json.loads(json.dumps(DEFAULT_SETTINGS))  # deep copy
    settings["radios"][0]["name"]       = radio_profile["name"]
    settings["radios"][0]["topic_name"] = radio_profile["topic_name"]
    settings["radios"][0]["model"]      = radio_profile["model"]
    settings["radios"][0]["port"]       = radio_profile["port_hint"]
    settings["radios"][0]["baud"]       = radio_profile["baud"]

    SETTINGS_PATH.write_text(json.dumps(settings, indent=4) + "\n")
    log.info(f"  {SETTINGS_PATH} created — OK")
    log.info("  IMPORTANT: Review and edit settings before running Ham System.")





# ---------------------------------------------------------------------------
# Step 9.5 - Run license advisor
# ---------------------------------------------------------------------------

def run_license_advisor():
    """
    Run the license advisor to verify the operator callsign and cache
    license data. Non-fatal if it fails -- license verification is
    optional and the system works without it.
    """
    log.info("")
    log.info("Step 9.5: Running license advisor...")

    advisor = Path("license_advisor-v0.0.1.py")
    if not advisor.exists():
        log.warning(f"  {advisor} not found -- skipping license verification")
        return

    # Read callsign from settings
    if not SETTINGS_PATH.exists():
        log.warning("  Settings file not found -- skipping license verification")
        return

    try:
        settings = json.loads(SETTINGS_PATH.read_text())
        callsign = settings.get("operator", {}).get("callsign", "")
    except Exception:
        callsign = ""

    if not callsign or callsign == "YOUR_CALLSIGN":
        log.warning("  No callsign set in settings -- skipping license verification")
        log.warning(f"  Update 'callsign' in {SETTINGS_PATH} and run:")
        log.warning(f"    python3 {advisor} YOUR_CALLSIGN")
        return

    log.info(f"  Verifying callsign: {callsign}")
    result = subprocess.run(
        [str(VENV_PYTHON), str(advisor), callsign],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        log.info("  License verification complete -- OK")
        for line in result.stdout.splitlines():
            if line.strip():
                log.info(f"  {line}")
    else:
        log.warning("  License verification failed (non-fatal):")
        log.warning(f"  {result.stderr.strip() or result.stdout.strip()}")
        log.warning(f"  Run manually: python3 {advisor} {callsign}")

# ---------------------------------------------------------------------------
# Step 10 - Create unversioned symlinks to current scripts
# ---------------------------------------------------------------------------

def create_symlinks():
    """
    Create unversioned symlinks pointing to the current versioned scripts.
    e.g. init -> init-v0.0.1.py
         start -> start-v0.0.1.py
    When a script is versioned up, only the symlink needs updating.
    """
    log.info("")
    log.info("Step 10: Creating unversioned symlinks...")

    repo_path = Path(__file__).resolve().parent
    version_pattern = re.compile(r"^(.+)-v[0-9]+[.][0-9]+[.][0-9]+[.]py$")

    scripts = [
        f for f in repo_path.iterdir()
        if f.is_file() and version_pattern.match(f.name)
    ]

    if not scripts:
        log.info("  No versioned scripts found.")
        return

    for script in sorted(scripts):
        match = version_pattern.match(script.name)
        if not match:
            continue
        base_name = match.group(1)
        symlink_path = repo_path / base_name

        if symlink_path.is_symlink():
            if symlink_path.resolve() == script.resolve():
                log.info(f"  {base_name} -> {script.name} -- already correct, skipping")
                continue
            symlink_path.unlink()
        elif symlink_path.exists():
            symlink_path.unlink()

        symlink_path.symlink_to(script.name)
        log.info(f"  {base_name} -> {script.name} -- created")

    log.info("  Symlinks created -- OK")

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
    Verify /usr/local/bin appears in PATH before any system directories
    (/usr/bin, /bin, etc.). Allows user directories (~/bin, nvm, etc.)
    to appear first — only system dirs must come after /usr/local/bin.
    If not satisfied, detect the user's shell and offer to edit the RC file.
    """
    log.info("")
    log.info("Pre-flight: Checking PATH configuration...")
    path_entries = os.environ.get("PATH", "").split(":")

    # System directories that must NOT appear before /usr/local/bin
    system_dirs = {"/usr/bin", "/bin", "/usr/sbin", "/sbin"}

    local_bin_idx = None
    blocking_dir = None

    for i, entry in enumerate(path_entries):
        if entry == "/usr/local/bin":
            local_bin_idx = i
            break
        if entry in system_dirs:
            blocking_dir = entry
            break

    if local_bin_idx is not None:
        log.info(f"  /usr/local/bin found at PATH position {local_bin_idx + 1} — OK")
        return

    if blocking_dir:
        log.warning(f"  /usr/local/bin is blocked by system directory '{blocking_dir}' in PATH")
    else:
        log.warning("  /usr/local/bin not found in PATH")
    log.warning("  /usr/local/bin must appear before system directories in PATH.")
    log.info("")

    shell_name, rc_path = detect_shell_rc()

    if shell_name and rc_path:
        edited = offer_rc_edit(rc_path, shell_name)
        if edited:
            abort(
                "PATH line added to RC file. Reload and re-run this script:\n"
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

    validate_operator_license()

    check_path()
    check_platform()
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
    run_license_advisor()
    create_symlinks()

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

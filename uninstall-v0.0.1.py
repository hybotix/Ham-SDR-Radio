#!/usr/bin/env python3
"""
uninstall-v0.0.1.py -- Ham System Uninstall Script
Project: Ham System -- Integrated Ham Radio Control Platform
Author:  Dale -- Hybrid RobotiX / The Accessibility Files
Version: 0.0.1

Removes everything installed by init-v0.0.1.py:
  Step 1  -- Remove symlinks
  Step 2  -- Remove virtual environment
  Step 3  -- Remove generated config files
  Step 4  -- Remove build directory
  Step 5  -- Remove FlRig from /usr/local
  Step 6  -- Remove SDR++ from /usr/local
  Step 7  -- Remove Python 3.14.3 from /usr/local
  Step 8  -- Remove OpenSSL from /usr/local

Warns and continues if any step fails -- nothing is fatal.
Does NOT remove apt packages installed during initialization.
Does NOT remove the repo directory itself.
"""

VERSION = "0.0.1"

import os
import sys
import subprocess
import shutil
import logging
from pathlib import Path
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
log_filename = LOG_DIR / f"uninstall-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_filename),
    ],
)
log = logging.getLogger("ham_uninstall")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LOCAL           = Path("/usr/local")
LOCAL_BIN       = LOCAL / "bin"
LOCAL_LIB       = LOCAL / "lib"
LOCAL_INC       = LOCAL / "include"
LOCAL_SHARE     = LOCAL / "share"

PYTHON_VERSION  = "3.14.3"
PYTHON_MAJ_MIN  = "3.14"
PYTHON_BIN      = LOCAL_BIN / "python3.14"

REPO_NAME       = "Ham-SDR-Radio"
VIRTUAL_DIR     = Path(os.environ.get("HAM_VENV_DIR", str(Path.home() / "Virtual")))
VENV_PATH       = VIRTUAL_DIR / REPO_NAME
BUILD_DIR       = Path(os.environ.get("HAM_BUILD_DIR", "build"))

CONFIG_FILES = [
    Path("config") / "settings-v0.0.1.json",
    Path("config") / "license_cache-v0.0.1.json",
    Path("config") / "ised_cache-v0.0.1.json",
    Path("config") / "ofcom_cache-v0.0.1.json",
]

# Symlinks created by init
SYMLINKS = [
    LOCAL_BIN / "python3",
    LOCAL_BIN / "pip3",
    Path("init"),
    Path("start"),
    Path("uninstall"),
]

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def banner():
    log.info("=" * 70)
    log.info("  Ham System Uninstall Script")
    log.info("  Integrated Ham Radio Control Platform")
    log.info(f"  Version {VERSION}")
    log.info("  Hybrid RobotiX / The Accessibility Files")
    log.info("=" * 70)


def warn(message: str):
    """Log a warning and continue -- nothing is fatal."""
    log.warning(f"  WARNING: {message}")


def run(args: list, cwd: Path = None, desc: str = "") -> bool:
    """Run a command. Returns True on success, False on failure."""
    label = desc or " ".join(str(a) for a in args)
    log.info(f"  Running: {label}")
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        warn(f"Command failed: {label}")
        if result.stderr.strip():
            log.warning(f"  stderr: {result.stderr.strip()}")
        return False
    return True


def confirm() -> bool:
    """Ask the user to confirm before proceeding."""
    log.info("")
    log.info("  This will remove:")
    log.info("    - OpenSSL from /usr/local")
    log.info("    - Python 3.14.3 from /usr/local")
    log.info("    - SDR++ from /usr/local")
    log.info("    - FlRig from /usr/local")
    log.info("    - Virtual environment")
    log.info("    - Generated config files")
    log.info("    - Build directory")
    log.info("    - Symlinks")
    log.info("")
    log.info("  The repo directory itself will NOT be removed.")
    log.info("  Apt packages installed during init will NOT be removed.")
    log.info("")
    try:
        answer = input("  Are you sure? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        log.info("")
        return False
    return answer == "y"


# ---------------------------------------------------------------------------
# Step 1 -- Remove symlinks
# ---------------------------------------------------------------------------

def remove_symlinks():
    log.info("")
    log.info("Step 1: Removing symlinks...")
    for link in SYMLINKS:
        if link.is_symlink():
            try:
                if str(link).startswith("/usr/local"):
                    run(["sudo", "rm", "-f", str(link)], desc=f"rm {link}")
                else:
                    link.unlink()
                log.info(f"  Removed: {link}")
            except Exception as e:
                warn(f"Could not remove {link}: {e}")
        else:
            log.info(f"  Not a symlink, skipping: {link}")


# ---------------------------------------------------------------------------
# Step 2 -- Remove virtual environment
# ---------------------------------------------------------------------------

def remove_venv():
    log.info("")
    log.info("Step 2: Removing virtual environment...")
    if VENV_PATH.exists():
        try:
            shutil.rmtree(VENV_PATH)
            log.info(f"  Removed: {VENV_PATH}")
        except Exception as e:
            warn(f"Could not remove venv at {VENV_PATH}: {e}")
    else:
        log.info(f"  Venv not found at {VENV_PATH} -- skipping")


# ---------------------------------------------------------------------------
# Step 3 -- Remove generated config files
# ---------------------------------------------------------------------------

def remove_config_files():
    log.info("")
    log.info("Step 3: Removing generated config files...")
    for f in CONFIG_FILES:
        if f.exists():
            try:
                f.unlink()
                log.info(f"  Removed: {f}")
            except Exception as e:
                warn(f"Could not remove {f}: {e}")
        else:
            log.info(f"  Not found, skipping: {f}")

    # Remove start script if generated
    start = Path("start-v0.0.1.py")
    if start.exists():
        try:
            start.unlink()
            log.info(f"  Removed: {start}")
        except Exception as e:
            warn(f"Could not remove {start}: {e}")


# ---------------------------------------------------------------------------
# Step 4 -- Remove build directory
# ---------------------------------------------------------------------------

def remove_build_dir():
    log.info("")
    log.info("Step 4: Removing build directory...")
    if BUILD_DIR.exists():
        try:
            shutil.rmtree(BUILD_DIR)
            log.info(f"  Removed: {BUILD_DIR}")
        except Exception as e:
            warn(f"Could not remove build directory: {e}")
    else:
        log.info(f"  Build directory not found -- skipping")


# ---------------------------------------------------------------------------
# Step 5 -- Remove FlRig
# ---------------------------------------------------------------------------

def remove_flrig():
    log.info("")
    log.info("Step 5: Removing FlRig from /usr/local...")
    flrig_bin = LOCAL_BIN / "flrig"
    if not flrig_bin.exists():
        log.info("  FlRig not found in /usr/local -- skipping")
        return

    # FlRig installs via make uninstall if source is available
    flrig_src = BUILD_DIR / "flrig"
    if flrig_src.exists():
        log.info("  Running make uninstall for FlRig...")
        run(["sudo", "make", "uninstall"], cwd=flrig_src, desc="make uninstall FlRig")
    else:
        # Manual removal of known FlRig files
        log.info("  Source not found -- removing FlRig files manually...")
        for f in [LOCAL_BIN / "flrig", LOCAL_BIN / "flrig_cat"]:
            if f.exists():
                run(["sudo", "rm", "-f", str(f)], desc=f"rm {f.name}")

    log.info("  FlRig removed -- OK")


# ---------------------------------------------------------------------------
# Step 6 -- Remove SDR++
# ---------------------------------------------------------------------------

def remove_sdrpp():
    log.info("")
    log.info("Step 6: Removing SDR++ from /usr/local...")
    sdrpp_bin = LOCAL_BIN / "sdrpp"
    if not sdrpp_bin.exists():
        log.info("  SDR++ not found in /usr/local -- skipping")
        return

    sdrpp_build = BUILD_DIR / "SDRPlusPlus" / "build"
    if sdrpp_build.exists():
        log.info("  Running make uninstall for SDR++...")
        run(["sudo", "make", "uninstall"], cwd=sdrpp_build, desc="make uninstall SDR++")
    else:
        log.info("  Source not found -- removing SDR++ binary manually...")
        run(["sudo", "rm", "-f", str(sdrpp_bin)], desc="rm sdrpp")
        sdrpp_share = LOCAL_SHARE / "sdrpp"
        if sdrpp_share.exists():
            run(["sudo", "rm", "-rf", str(sdrpp_share)], desc="rm sdrpp share")

    log.info("  SDR++ removed -- OK")


# ---------------------------------------------------------------------------
# Step 7 -- Remove Python 3.14.3
# ---------------------------------------------------------------------------

def remove_python():
    log.info("")
    log.info("Step 7: Removing Python 3.14.3 from /usr/local...")
    if not PYTHON_BIN.exists():
        log.info("  Python 3.14.3 not found in /usr/local -- skipping")
        return

    python_src = BUILD_DIR / f"Python-{PYTHON_VERSION}"
    if python_src.exists():
        log.info("  Running make uninstall for Python...")
        run(["sudo", "make", "uninstall"], cwd=python_src, desc="make uninstall Python")
    else:
        log.info("  Source not found -- removing Python files manually...")
        targets = [
            LOCAL_BIN / f"python{PYTHON_MAJ_MIN}",
            LOCAL_BIN / f"python{PYTHON_MAJ_MIN}-config",
            LOCAL_BIN / f"idle{PYTHON_MAJ_MIN}",
            LOCAL_BIN / f"pip{PYTHON_MAJ_MIN}",
            LOCAL_BIN / f"pydoc{PYTHON_MAJ_MIN}",
            LOCAL_LIB / f"python{PYTHON_MAJ_MIN}",
            LOCAL_LIB / f"libpython{PYTHON_MAJ_MIN}.a",
            LOCAL_LIB / f"libpython{PYTHON_MAJ_MIN}.so",
            LOCAL_INC / f"python{PYTHON_MAJ_MIN}",
            LOCAL_SHARE / f"man/man1/python{PYTHON_MAJ_MIN}.1",
        ]
        for t in targets:
            if t.exists():
                cmd = ["sudo", "rm", "-rf", str(t)]
                run(cmd, desc=f"rm {t.name}")

    log.info("  Python 3.14.3 removed -- OK")


# ---------------------------------------------------------------------------
# Step 8 -- Remove OpenSSL
# ---------------------------------------------------------------------------

def remove_openssl():
    log.info("")
    log.info("Step 8: Removing OpenSSL from /usr/local...")
    openssl_bin = LOCAL_BIN / "openssl"
    if not openssl_bin.exists():
        log.info("  OpenSSL not found in /usr/local -- skipping")
        return

    openssl_src = BUILD_DIR / "openssl"
    if openssl_src.exists():
        log.info("  Running make uninstall for OpenSSL...")
        run(["sudo", "make", "uninstall"], cwd=openssl_src, desc="make uninstall OpenSSL")
    else:
        log.info("  Source not found -- removing OpenSSL files manually...")
        targets = [
            LOCAL_BIN / "openssl",
            LOCAL_BIN / "c_rehash",
            LOCAL_LIB / "libssl.so",
            LOCAL_LIB / "libssl.a",
            LOCAL_LIB / "libcrypto.so",
            LOCAL_LIB / "libcrypto.a",
            LOCAL_INC / "openssl",
            LOCAL / "ssl",
        ]
        for t in targets:
            if t.exists():
                run(["sudo", "rm", "-rf", str(t)], desc=f"rm {t.name}")

    log.info("  OpenSSL removed -- OK")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    banner()

    if not confirm():
        log.info("")
        log.info("  Uninstall cancelled.")
        sys.exit(0)

    log.info("")
    log.info("  Proceeding with uninstall...")

    remove_symlinks()
    remove_venv()
    remove_config_files()
    remove_build_dir()
    remove_flrig()
    remove_sdrpp()
    remove_python()
    remove_openssl()

    log.info("")
    log.info("=" * 70)
    log.info("  Uninstall complete.")
    log.info("  The repo directory has NOT been removed.")
    log.info("  Apt packages have NOT been removed.")
    log.info(f"  Log saved to: {log_filename}")
    log.info("=" * 70)
    log.info("")


if __name__ == "__main__":
    main()

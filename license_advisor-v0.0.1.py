#!/usr/bin/env python3
"""
license_advisor-v0.0.1.py -- Ham System License Advisor
Project: Ham System -- Integrated Ham Radio Control Platform
Author:  Dale -- Hybrid RobotiX / The Accessibility Files
Version: 0.0.1

Looks up the operator's amateur radio license from the appropriate
licensing authority database and caches the result. Provides privilege
awareness to help operators stay within their legal limits.

PHILOSOPHY:
  This is a helper, not a gatekeeper.
  The operator is ALWAYS the responsible party.
  This system NEVER blocks any operation.
  It WARNS clearly when an action may exceed known privileges.
  Warnings are informational only -- the operator may proceed.

Supported authorities:
  FCC   (US)     -- Live API via callook.info
  ISED  (Canada) -- Local cache from ISED database ZIP
  Ofcom (UK)     -- Local cache from Ofcom open data

Usage:
  python3 license_advisor-v0.0.1.py <CALLSIGN>
  python3 license_advisor-v0.0.1.py --refresh <CALLSIGN>
"""

VERSION = "0.0.1"

import sys
import json
import re
import urllib.request
import urllib.error
import zipfile
import io
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("license_advisor")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONFIG_DIR          = Path("config")
CACHE_PATH          = CONFIG_DIR / "license_cache-v0.0.1.json"
SETTINGS_PATH       = CONFIG_DIR / "settings-v0.0.1.json"

CALLOOK_URL         = "https://callook.info/{callsign}/json"
ISED_ZIP_URL        = "https://apc-cap.ic.gc.ca/datafiles/amateur.zip"
ISED_CACHE_PATH     = CONFIG_DIR / "ised_cache-v0.0.1.json"
OFCOM_CACHE_PATH    = CONFIG_DIR / "ofcom_cache-v0.0.1.json"

CACHE_MAX_AGE_DAYS  = 1     # Live API cache refresh interval
DB_MAX_AGE_DAYS     = 7     # ISED/Ofcom local DB refresh interval
REQUEST_TIMEOUT     = 10    # HTTP timeout in seconds

# ---------------------------------------------------------------------------
# Callsign prefix -> authority detection
# ---------------------------------------------------------------------------

# US FCC prefixes (W, K, N, A + single digit + suffix)
FCC_PREFIXES    = re.compile(r"^[WKNA]\d", re.IGNORECASE)

# Canadian ISED prefixes
ISED_PREFIXES   = re.compile(r"^(VE|VA|VY|VO)\d", re.IGNORECASE)

# UK Ofcom prefixes
OFCOM_PREFIXES  = re.compile(r"^(G|M|2[EIWDJU])\d", re.IGNORECASE)


def detect_authority(callsign: str) -> str:
    """
    Detect the licensing authority from the callsign prefix.
    Returns 'FCC', 'ISED', 'OFCOM', or 'UNKNOWN'.
    """
    cs = callsign.upper().strip()
    if FCC_PREFIXES.match(cs):
        return "FCC"
    if ISED_PREFIXES.match(cs):
        return "ISED"
    if OFCOM_PREFIXES.match(cs):
        return "OFCOM"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# FCC lookup via callook.info
# ---------------------------------------------------------------------------

# FCC operator class codes from callook.info -> human readable
FCC_CLASS_MAP = {
    "T":  "Technician",
    "G":  "General",
    "A":  "Advanced",
    "E":  "Amateur Extra",
    "N":  "Novice",
    "P":  "Technician Plus",
}

# Privilege profiles by license class
FCC_PRIVILEGES = {
    "Technician": {
        "hf_bands":    ["10m"],
        "hf_phone":    False,
        "hf_cw":       True,
        "hf_digital":  True,
        "vhf_uhf":     True,
        "max_power_w": 200,
        "notes":       "HF limited to 10M CW/digital/SSB above 28.300 MHz. Full VHF/UHF.",
    },
    "General": {
        "hf_bands":    ["160m", "80m", "60m", "40m", "30m", "20m", "17m", "15m", "12m", "10m"],
        "hf_phone":    True,
        "hf_cw":       True,
        "hf_digital":  True,
        "vhf_uhf":     True,
        "max_power_w": 1500,
        "notes":       "HF with some band segment restrictions. Full VHF/UHF.",
    },
    "Advanced": {
        "hf_bands":    ["160m", "80m", "60m", "40m", "30m", "20m", "17m", "15m", "12m", "10m"],
        "hf_phone":    True,
        "hf_cw":       True,
        "hf_digital":  True,
        "vhf_uhf":     True,
        "max_power_w": 1500,
        "notes":       "Similar to General with some expanded HF segments.",
    },
    "Amateur Extra": {
        "hf_bands":    ["160m", "80m", "60m", "40m", "30m", "20m", "17m", "15m", "12m", "10m"],
        "hf_phone":    True,
        "hf_cw":       True,
        "hf_digital":  True,
        "vhf_uhf":     True,
        "max_power_w": 1500,
        "notes":       "Full HF privileges on all amateur bands.",
    },
    "Novice": {
        "hf_bands":    ["80m", "40m", "15m", "10m"],
        "hf_phone":    False,
        "hf_cw":       True,
        "hf_digital":  False,
        "vhf_uhf":     True,
        "max_power_w": 200,
        "notes":       "CW only on limited HF bands. Some VHF.",
    },
}


def lookup_fcc(callsign: str) -> dict:
    """
    Look up a US callsign via the callook.info API.
    Returns a normalized license record dict.
    """
    url = CALLOOK_URL.format(callsign=callsign.upper())
    log.info(f"  Querying callook.info for {callsign.upper()}...")

    try:
        with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        log.warning(f"  callook.info query failed: {e}")
        return None
    except json.JSONDecodeError as e:
        log.warning(f"  callook.info returned invalid JSON: {e}")
        return None

    status = data.get("status", "UNKNOWN")
    if status not in ("VALID", "INVALID"):
        log.warning(f"  callook.info returned status: {status}")
        return None

    current = data.get("current", {})
    other   = data.get("otherInfo", {})
    loc     = data.get("location", {})

    raw_class    = current.get("operClass", "")
    license_class = FCC_CLASS_MAP.get(raw_class, raw_class or "Unknown")
    privileges   = FCC_PRIVILEGES.get(license_class, {})

    return {
        "callsign":       current.get("callsign", callsign.upper()),
        "authority":      "FCC",
        "license_class":  license_class,
        "status":         status,
        "expiry":         other.get("expiryDate", ""),
        "grid_square":    loc.get("gridsquare", ""),
        "last_verified":  datetime.now(timezone.utc).isoformat(),
        "privileges":     privileges,
        "raw":            data,
    }


# ---------------------------------------------------------------------------
# Canada ISED lookup (local cache)
# ---------------------------------------------------------------------------

ISED_CLASS_MAP = {
    "A": "Advanced",
    "B": "Basic",
    "H": "Basic with Honours",
}

ISED_PRIVILEGES = {
    "Basic": {
        "hf_bands":    ["80m", "40m", "20m", "15m", "10m"],
        "hf_phone":    True,
        "hf_cw":       True,
        "hf_digital":  True,
        "vhf_uhf":     True,
        "max_power_w": 250,
        "notes":       "Basic privileges. HF with restrictions.",
    },
    "Basic with Honours": {
        "hf_bands":    ["160m", "80m", "60m", "40m", "30m", "20m", "17m", "15m", "12m", "10m"],
        "hf_phone":    True,
        "hf_cw":       True,
        "hf_digital":  True,
        "vhf_uhf":     True,
        "max_power_w": 1000,
        "notes":       "Full HF privileges below 30 MHz.",
    },
    "Advanced": {
        "hf_bands":    ["160m", "80m", "60m", "40m", "30m", "20m", "17m", "15m", "12m", "10m"],
        "hf_phone":    True,
        "hf_cw":       True,
        "hf_digital":  True,
        "vhf_uhf":     True,
        "max_power_w": 1000,
        "notes":       "Full privileges including building transmitters.",
    },
}


def refresh_ised_cache() -> bool:
    """Download and cache the ISED amateur database."""
    log.info("  Downloading ISED amateur database...")
    try:
        with urllib.request.urlopen(ISED_ZIP_URL, timeout=30) as resp:
            zip_data = resp.read()
    except urllib.error.URLError as e:
        log.warning(f"  ISED download failed: {e}")
        return False

    try:
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            # Find the amateur data file inside the ZIP
            names = zf.namelist()
            data_file = next((n for n in names if n.lower().endswith(".txt")), None)
            if not data_file:
                log.warning("  No .txt file found in ISED ZIP")
                return False
            raw = zf.read(data_file).decode("latin-1")
    except Exception as e:
        log.warning(f"  ISED ZIP extraction failed: {e}")
        return False

    # Parse the ISED data file into a dict keyed by callsign
    db = {}
    for line in raw.splitlines():
        parts = line.split(",")
        if len(parts) < 5:
            continue
        callsign = parts[0].strip().upper()
        if callsign:
            db[callsign] = {
                "callsign": callsign,
                "name":     parts[1].strip() if len(parts) > 1 else "",
                "class":    parts[4].strip() if len(parts) > 4 else "",
            }

    cache = {
        "downloaded": datetime.now(timezone.utc).isoformat(),
        "records":    db,
    }
    CONFIG_DIR.mkdir(exist_ok=True)
    ISED_CACHE_PATH.write_text(json.dumps(cache))
    log.info(f"  ISED cache saved — {len(db)} records")
    return True


def lookup_ised(callsign: str) -> dict:
    """Look up a Canadian callsign in the local ISED cache."""
    # Refresh cache if missing or stale
    needs_refresh = True
    if ISED_CACHE_PATH.exists():
        try:
            cache = json.loads(ISED_CACHE_PATH.read_text())
            downloaded = datetime.fromisoformat(cache.get("downloaded", "2000-01-01T00:00:00+00:00"))
            age = datetime.now(timezone.utc) - downloaded
            if age < timedelta(days=DB_MAX_AGE_DAYS):
                needs_refresh = False
        except Exception:
            pass

    if needs_refresh:
        if not refresh_ised_cache():
            log.warning("  ISED cache unavailable — cannot verify Canadian callsign")
            return None

    try:
        cache = json.loads(ISED_CACHE_PATH.read_text())
        records = cache.get("records", {})
    except Exception as e:
        log.warning(f"  Failed to read ISED cache: {e}")
        return None

    record = records.get(callsign.upper())
    if not record:
        log.warning(f"  {callsign.upper()} not found in ISED database")
        return None

    raw_class     = record.get("class", "")
    license_class = ISED_CLASS_MAP.get(raw_class, raw_class or "Basic")
    privileges    = ISED_PRIVILEGES.get(license_class, ISED_PRIVILEGES["Basic"])

    return {
        "callsign":      callsign.upper(),
        "authority":     "ISED",
        "license_class": license_class,
        "status":        "VALID",
        "expiry":        "",
        "grid_square":   "",
        "last_verified": datetime.now(timezone.utc).isoformat(),
        "privileges":    privileges,
    }


# ---------------------------------------------------------------------------
# UK Ofcom lookup (local cache)
# ---------------------------------------------------------------------------

OFCOM_PRIVILEGES = {
    "Foundation": {
        "hf_bands":    ["10m"],
        "hf_phone":    True,
        "hf_cw":       True,
        "hf_digital":  True,
        "vhf_uhf":     True,
        "max_power_w": 10,
        "notes":       "Limited bands, 10W maximum power.",
    },
    "Intermediate": {
        "hf_bands":    ["80m", "40m", "20m", "15m", "10m"],
        "hf_phone":    True,
        "hf_cw":       True,
        "hf_digital":  True,
        "vhf_uhf":     True,
        "max_power_w": 50,
        "notes":       "Extended band access, 50W maximum power.",
    },
    "Full": {
        "hf_bands":    ["160m", "80m", "60m", "40m", "30m", "20m", "17m", "15m", "12m", "10m"],
        "hf_phone":    True,
        "hf_cw":       True,
        "hf_digital":  True,
        "vhf_uhf":     True,
        "max_power_w": 400,
        "notes":       "Full privileges on all amateur bands.",
    },
}


def lookup_ofcom(callsign: str) -> dict:
    """
    Look up a UK callsign. Ofcom does not provide a live API.
    License class is inferred from callsign prefix structure.
    Foundation: 2E0xxx, 2W0xxx, M6xxx, 2E1xxx
    Intermediate: 2E0xxx (post-2003), M3xxx, M6xxx
    Full: G, M0, M1, M5, GW, GI, GM, GD etc.
    This is an approximation -- Ofcom open data is used where cached.
    """
    cs = callsign.upper().strip()

    # Infer class from callsign structure
    if re.match(r"^M6", cs) or re.match(r"^2E", cs) or re.match(r"^2W", cs):
        license_class = "Foundation"
    elif re.match(r"^M3", cs) or re.match(r"^2I", cs):
        license_class = "Intermediate"
    else:
        license_class = "Full"

    privileges = OFCOM_PRIVILEGES.get(license_class, OFCOM_PRIVILEGES["Full"])

    log.info(f"  UK callsign {cs} -- inferred class: {license_class}")
    log.info("  NOTE: Ofcom does not provide a live API. Class inferred from callsign prefix.")

    return {
        "callsign":      cs,
        "authority":     "OFCOM",
        "license_class": license_class,
        "status":        "VALID",
        "expiry":        "",
        "grid_square":   "",
        "last_verified": datetime.now(timezone.utc).isoformat(),
        "privileges":    privileges,
        "notes":         "License class inferred from callsign prefix. Manual verification recommended.",
    }


# ---------------------------------------------------------------------------
# Main lookup dispatcher
# ---------------------------------------------------------------------------

def lookup_license(callsign: str, force_refresh: bool = False) -> dict:
    """
    Look up a callsign and return a license record.
    Uses cached result if available and not stale.
    Returns None if lookup fails.
    """
    cs = callsign.upper().strip()

    # Check cache first
    if not force_refresh and CACHE_PATH.exists():
        try:
            cached = json.loads(CACHE_PATH.read_text())
            if cached.get("callsign", "").upper() == cs:
                verified = datetime.fromisoformat(cached.get("last_verified", "2000-01-01T00:00:00+00:00"))
                age = datetime.now(timezone.utc) - verified
                if age < timedelta(days=CACHE_MAX_AGE_DAYS):
                    log.info(f"  Using cached license data for {cs} (age: {age.seconds // 3600}h)")
                    return cached
        except Exception:
            pass

    # Detect authority
    authority = detect_authority(cs)
    log.info(f"  Callsign: {cs}  Authority: {authority}")

    if authority == "FCC":
        record = lookup_fcc(cs)
    elif authority == "ISED":
        record = lookup_ised(cs)
    elif authority == "OFCOM":
        record = lookup_ofcom(cs)
    else:
        log.warning(f"  Unknown callsign prefix — cannot determine licensing authority for {cs}")
        return None

    if record:
        CONFIG_DIR.mkdir(exist_ok=True)
        CACHE_PATH.write_text(json.dumps(record, indent=4))
        log.info(f"  License cache saved to {CACHE_PATH}")

    return record


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def display_license(record: dict):
    """Print a formatted license summary."""
    print()
    print("=" * 60)
    print("  License Advisor — License Summary")
    print("=" * 60)
    print(f"  Callsign      : {record.get('callsign', 'N/A')}")
    print(f"  Authority     : {record.get('authority', 'N/A')}")
    print(f"  License Class : {record.get('license_class', 'N/A')}")
    print(f"  Status        : {record.get('status', 'N/A')}")
    if record.get("expiry"):
        print(f"  Expiry        : {record.get('expiry')}")
    if record.get("grid_square"):
        print(f"  Grid Square   : {record.get('grid_square')}")
    print(f"  Last Verified : {record.get('last_verified', 'N/A')}")
    print()

    priv = record.get("privileges", {})
    if priv:
        print("  Privileges:")
        bands = priv.get("hf_bands", [])
        print(f"    HF Bands    : {', '.join(bands) if bands else 'None'}")
        print(f"    HF Phone    : {'Yes' if priv.get('hf_phone') else 'No'}")
        print(f"    HF CW       : {'Yes' if priv.get('hf_cw') else 'No'}")
        print(f"    HF Digital  : {'Yes' if priv.get('hf_digital') else 'No'}")
        print(f"    VHF/UHF     : {'Yes' if priv.get('vhf_uhf') else 'No'}")
        print(f"    Max Power   : {priv.get('max_power_w', 'N/A')}W")
        if priv.get("notes"):
            print(f"    Notes       : {priv.get('notes')}")

    if record.get("notes"):
        print()
        print(f"  NOTE: {record.get('notes')}")

    print()
    print("  I. WILL. NEVER. GIVE. UP. OR. SURRENDER.")
    print("=" * 60)
    print()


# ---------------------------------------------------------------------------
# Settings integration
# ---------------------------------------------------------------------------

def get_callsign_from_settings() -> str:
    """Read callsign from settings file if present."""
    if not SETTINGS_PATH.exists():
        return None
    try:
        settings = json.loads(SETTINGS_PATH.read_text())
        cs = settings.get("operator", {}).get("callsign", "")
        if cs and cs != "YOUR_CALLSIGN":
            return cs
    except Exception:
        pass
    return None


def update_settings_gridsquare(grid_square: str):
    """Update grid square in settings from license lookup if not already set."""
    if not SETTINGS_PATH.exists() or not grid_square:
        return
    try:
        settings = json.loads(SETTINGS_PATH.read_text())
        if not settings.get("operator", {}).get("grid_square"):
            settings["operator"]["grid_square"] = grid_square
            SETTINGS_PATH.write_text(json.dumps(settings, indent=4) + "\n")
            log.info(f"  Grid square {grid_square} saved to settings")
    except Exception as e:
        log.warning(f"  Could not update grid square in settings: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  Ham System License Advisor")
    print(f"  Version {VERSION}")
    print("  Hybrid RobotiX / The Accessibility Files")
    print("=" * 60)
    print()

    force_refresh = "--refresh" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    # Get callsign from args or settings
    if args:
        callsign = args[0]
    else:
        callsign = get_callsign_from_settings()
        if not callsign:
            print("Usage: python3 license_advisor-v0.0.1.py <CALLSIGN>")
            print("       python3 license_advisor-v0.0.1.py --refresh <CALLSIGN>")
            print()
            print("Or set your callsign in config/settings-v0.0.1.json")
            sys.exit(1)

    log.info(f"Looking up license for: {callsign.upper()}")
    if force_refresh:
        log.info("Force refresh requested -- bypassing cache")

    record = lookup_license(callsign, force_refresh=force_refresh)

    if not record:
        print(f"ERROR: Could not retrieve license data for {callsign.upper()}")
        print("  Check your callsign and network connection.")
        sys.exit(1)

    display_license(record)

    # Auto-populate grid square in settings if available
    if record.get("grid_square"):
        update_settings_gridsquare(record["grid_square"])


if __name__ == "__main__":
    main()

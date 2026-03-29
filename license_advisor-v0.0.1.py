#!/usr/bin/env python3
"""
license_advisor-v0.0.1.py -- Ham System License Advisor
Project: Ham System -- Integrated Ham Radio Control Platform
Author:  Dale -- Hybrid RobotiX / The Accessibility Files
Version: 0.0.1

Validates the operator's amateur radio license against the appropriate
licensing authority database and provides privilege-aware warnings.

This is a HELPER, not a GATEKEEPER.
- The operator is always the responsible party.
- The system will NEVER block any operation based on license class.
- The system WILL warn clearly if an action may exceed privileges.
- Warnings are informational only -- the operator may proceed.

Supported authorities:
  FCC   (US)     -- Live API via callook.info
  ISED  (Canada) -- Local cache from ISED ZIP database
  Ofcom (UK)     -- Licence class inferred from callsign structure

Usage:
  Standalone:  python3 license_advisor-v0.0.1.py <CALLSIGN>
  As module:   from license_advisor_v0_0_1 import LicenseAdvisor
"""

VERSION = "0.0.1"

import sys
import json
import ssl
import urllib.request
import urllib.error
import zipfile
import io
import re
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

log = logging.getLogger("license_advisor")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CACHE_PATH         = Path("config") / "license_cache-v0.0.1.json"
ISED_CACHE_PATH    = Path("config") / "ised_cache-v0.0.1.json"
CALLOOK_API        = "https://callook.info/{callsign}/json"
ISED_DB_URL        = "https://apc-cap.ic.gc.ca/datafiles/amateur.zip"
CACHE_MAX_AGE_DAYS = 7

# Callsign prefix -> authority
PREFIX_MAP = {
    "FCC":   re.compile(r"^[AKNW]", re.IGNORECASE),
    "ISED":  re.compile(r"^V[AEY]|^VO", re.IGNORECASE),
    "OFCOM": re.compile(r"^[GM2]", re.IGNORECASE),
}

# FCC operator class codes -> human readable
FCC_CLASS_MAP = {
    # Single letter codes (legacy API format)
    "T": "Technician",
    "G": "General",
    "A": "Advanced",
    "E": "Amateur Extra",
    "N": "Novice",
    "P": "Technician Plus",
    # Full word format (current callook.info API)
    "TECHNICIAN":     "Technician",
    "GENERAL":        "General",
    "ADVANCED":       "Advanced",
    "AMATEUR EXTRA":  "Amateur Extra",
    "EXTRA":          "Amateur Extra",
    "NOVICE":         "Novice",
    "TECHNICIAN PLUS":"Technician Plus",
}

# Privilege profiles -- used for warnings, NEVER for blocking
PRIVILEGE_PROFILES = {
    "FCC": {
        "Technician": {
            "hf_phone":    False,
            "hf_cw":       True,
            "hf_digital":  True,
            "vhf_uhf":     True,
            "max_power_w": 200,
            "hf_bands":    ["10m"],
            "notes":       "HF limited to 10M CW/digital only. No HF phone privileges.",
        },
        "General": {
            "hf_phone":    True,
            "hf_cw":       True,
            "hf_digital":  True,
            "vhf_uhf":     True,
            "max_power_w": 1500,
            "hf_bands":    ["160m","80m","40m","20m","17m","15m","12m","10m"],
            "notes":       "HF on most bands with some segment restrictions vs Extra.",
        },
        "Advanced": {
            "hf_phone":    True,
            "hf_cw":       True,
            "hf_digital":  True,
            "vhf_uhf":     True,
            "max_power_w": 1500,
            "hf_bands":    ["160m","80m","40m","20m","17m","15m","12m","10m"],
            "notes":       "Legacy class. Expanded privileges over General.",
        },
        "Amateur Extra": {
            "hf_phone":    True,
            "hf_cw":       True,
            "hf_digital":  True,
            "vhf_uhf":     True,
            "max_power_w": 1500,
            "hf_bands":    ["160m","80m","60m","40m","30m","20m","17m","15m","12m","10m","6m"],
            "notes":       "Full privileges on all amateur bands.",
        },
        "Novice": {
            "hf_phone":    False,
            "hf_cw":       True,
            "hf_digital":  False,
            "vhf_uhf":     True,
            "max_power_w": 200,
            "hf_bands":    ["80m","40m","15m","10m"],
            "notes":       "Legacy class. HF CW only on limited bands.",
        },
        "Technician Plus": {
            "hf_phone":    False,
            "hf_cw":       True,
            "hf_digital":  True,
            "vhf_uhf":     True,
            "max_power_w": 200,
            "hf_bands":    ["10m"],
            "notes":       "Legacy class. Equivalent to Technician.",
        },
    },
    "ISED": {
        "Basic": {
            "hf_phone":    True,
            "hf_cw":       True,
            "hf_digital":  True,
            "vhf_uhf":     True,
            "max_power_w": 560,
            "hf_bands":    ["80m","40m","20m","15m","10m"],
            "notes":       "Basic qualification. HF with band restrictions.",
        },
        "Basic with Honours": {
            "hf_phone":    True,
            "hf_cw":       True,
            "hf_digital":  True,
            "vhf_uhf":     True,
            "max_power_w": 1000,
            "hf_bands":    ["160m","80m","60m","40m","30m","20m","17m","15m","12m","10m"],
            "notes":       "Basic with Honours. Full HF below 30MHz.",
        },
        "Advanced": {
            "hf_phone":    True,
            "hf_cw":       True,
            "hf_digital":  True,
            "vhf_uhf":     True,
            "max_power_w": 1000,
            "hf_bands":    ["160m","80m","60m","40m","30m","20m","17m","15m","12m","10m","6m"],
            "notes":       "Advanced. Full privileges including building transmitters.",
        },
    },
    "OFCOM": {
        "Foundation": {
            "hf_phone":    True,
            "hf_cw":       True,
            "hf_digital":  True,
            "vhf_uhf":     True,
            "max_power_w": 10,
            "hf_bands":    ["80m","40m","20m","15m","10m"],
            "notes":       "Foundation licence. 10W maximum power.",
        },
        "Intermediate": {
            "hf_phone":    True,
            "hf_cw":       True,
            "hf_digital":  True,
            "vhf_uhf":     True,
            "max_power_w": 50,
            "hf_bands":    ["160m","80m","40m","20m","17m","15m","12m","10m","6m"],
            "notes":       "Intermediate licence. 50W maximum power.",
        },
        "Full": {
            "hf_phone":    True,
            "hf_cw":       True,
            "hf_digital":  True,
            "vhf_uhf":     True,
            "max_power_w": 400,
            "hf_bands":    ["160m","80m","60m","40m","30m","20m","17m","15m","12m","10m","6m"],
            "notes":       "Full licence. Maximum privileges.",
        },
    },
}


# ---------------------------------------------------------------------------
# Authority detection
# ---------------------------------------------------------------------------

def detect_authority(callsign: str) -> str:
    """Detect licensing authority from callsign prefix."""
    cs = callsign.strip().upper()
    for authority, pattern in PREFIX_MAP.items():
        if pattern.match(cs):
            return authority
    raise ValueError(
        f"Cannot determine licensing authority for '{callsign}'. "
        f"Supported: US (A/K/N/W), Canada (VE/VA/VY/VO), UK (G/M/2)."
    )


# ---------------------------------------------------------------------------
# FCC lookup via callook.info
# ---------------------------------------------------------------------------

def _ssl_context():
    """
    Return an SSL context using certifi's CA bundle if available,
    falling back to the system CA bundle.
    """
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    return ctx


def lookup_fcc(callsign: str) -> dict:
    """Query callook.info for FCC license data."""
    url = CALLOOK_API.format(callsign=callsign.upper())
    log.info(f"  Querying callook.info for {callsign.upper()}...")

    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "HamSystem/0.0.1"}
        )
        with urllib.request.urlopen(req, timeout=10, context=_ssl_context()) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise LookupError(f"Network error querying callook.info: {e}")
    except json.JSONDecodeError as e:
        raise LookupError(f"Invalid response from callook.info: {e}")

    status = data.get("status", "").upper()
    if status == "INVALID":
        raise LookupError(
            f"Callsign '{callsign.upper()}' not found in FCC database. "
            f"Verify the callsign is correct and the license is active."
        )
    if status != "VALID":
        raise LookupError(
            f"Unexpected status '{status}' for '{callsign.upper()}'. "
            f"License may be expired, cancelled, or inactive."
        )

    raw_class = data.get("current", {}).get("operClass", "")
    license_class = FCC_CLASS_MAP.get(raw_class) or FCC_CLASS_MAP.get(raw_class.upper(), raw_class.title())

    return {
        "callsign":      data.get("current", {}).get("callsign", callsign.upper()),
        "authority":     "FCC",
        "license_class": license_class,
        "status":        status,
        "expiry":        data.get("otherInfo", {}).get("expiryDate", ""),
        "grid_square":   data.get("location", {}).get("gridsquare", ""),
        "name":          data.get("name", ""),
        "last_verified": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# ISED lookup (Canada) -- local cache
# ---------------------------------------------------------------------------

def _load_ised_cache() -> dict:
    if not ISED_CACHE_PATH.exists():
        return {}
    try:
        data = json.loads(ISED_CACHE_PATH.read_text())
        cached_at = datetime.fromisoformat(
            data.get("_cached_at", "2000-01-01T00:00:00+00:00")
        )
        if datetime.now(timezone.utc) - cached_at > timedelta(days=CACHE_MAX_AGE_DAYS):
            log.info("  ISED cache is stale -- will refresh.")
            return {}
        return data
    except Exception:
        return {}


def _download_ised_db() -> dict:
    log.info(f"  Downloading ISED database...")
    try:
        req = urllib.request.Request(
            ISED_DB_URL, headers={"User-Agent": "HamSystem/0.0.1"}
        )
        with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as resp:
            zip_data = resp.read()
    except urllib.error.URLError as e:
        raise LookupError(f"Failed to download ISED database: {e}")

    records = {}
    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        for name in zf.namelist():
            if name.lower().endswith((".txt", ".csv")):
                with zf.open(name) as f:
                    for line in f:
                        try:
                            parts = line.decode("latin-1").strip().split("|")
                            if len(parts) >= 5:
                                cs = parts[1].strip().upper()
                                records[cs] = {
                                    "callsign":      cs,
                                    "name":          parts[0].strip(),
                                    "qualification": parts[4].strip(),
                                }
                        except Exception:
                            continue

    records["_cached_at"] = datetime.now(timezone.utc).isoformat()
    ISED_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ISED_CACHE_PATH.write_text(json.dumps(records, indent=2))
    log.info(f"  ISED database cached ({len(records)-1} records)")
    return records


def _ised_qual_to_class(qualification: str) -> str:
    q = qualification.upper()
    if "ADV" in q:
        return "Advanced"
    if "HON" in q:
        return "Basic with Honours"
    return "Basic"


def lookup_ised(callsign: str) -> dict:
    cache = _load_ised_cache()
    if not cache:
        cache = _download_ised_db()

    cs = callsign.strip().upper()
    record = cache.get(cs)
    if not record:
        raise LookupError(
            f"Callsign '{cs}' not found in ISED database. "
            f"Verify the callsign is correct and the certificate is active."
        )

    return {
        "callsign":      cs,
        "authority":     "ISED",
        "license_class": _ised_qual_to_class(record.get("qualification", "")),
        "status":        "VALID",
        "expiry":        "",
        "grid_square":   "",
        "name":          record.get("name", ""),
        "last_verified": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Ofcom lookup (UK) -- inferred from callsign structure
# ---------------------------------------------------------------------------

def lookup_ofcom(callsign: str) -> dict:
    """
    Determine UK licence class from callsign structure.
    Ofcom does not provide a live lookup API.
    """
    cs = callsign.strip().upper()
    log.info(f"  Inferring UK licence class from callsign structure...")

    if cs.startswith("2"):
        license_class = "Intermediate"
    elif re.match(r"^M[36]", cs):
        license_class = "Foundation"
    elif re.match(r"^[GM][0-9]", cs) or re.match(r"^G[3-9]", cs):
        license_class = "Full"
    else:
        license_class = "Full"

    return {
        "callsign":      cs,
        "authority":     "OFCOM",
        "license_class": license_class,
        "status":        "VALID",
        "expiry":        "",
        "grid_square":   "",
        "name":          "",
        "last_verified": datetime.now(timezone.utc).isoformat(),
        "notes":         "Licence class inferred from callsign structure. No live Ofcom API available.",
    }


# ---------------------------------------------------------------------------
# Main lookup dispatcher
# ---------------------------------------------------------------------------

def lookup_license(callsign: str) -> dict:
    """
    Look up a callsign. Returns normalized license dict.
    Raises LookupError or ValueError on failure.
    """
    authority = detect_authority(callsign)
    log.info(f"  Detected authority: {authority}")
    if authority == "FCC":
        return lookup_fcc(callsign)
    elif authority == "ISED":
        return lookup_ised(callsign)
    elif authority == "OFCOM":
        return lookup_ofcom(callsign)
    raise ValueError(f"Unknown authority: {authority}")


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------

def load_cached_license() -> dict | None:
    if not CACHE_PATH.exists():
        return None
    try:
        data = json.loads(CACHE_PATH.read_text())
        cached_at = datetime.fromisoformat(
            data.get("last_verified", "2000-01-01T00:00:00+00:00")
        )
        if datetime.now(timezone.utc) - cached_at > timedelta(days=CACHE_MAX_AGE_DAYS):
            log.info("  License cache is stale -- will re-verify.")
            return None
        return data
    except Exception:
        return None


def save_license_cache(license_data: dict):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(license_data, indent=4) + "\n")
    log.info(f"  License cached to {CACHE_PATH}")


# ---------------------------------------------------------------------------
# Privilege advisor
# ---------------------------------------------------------------------------

def get_privilege_profile(license_data: dict) -> dict | None:
    authority = license_data.get("authority", "")
    license_class = license_data.get("license_class", "")
    return PRIVILEGE_PROFILES.get(authority, {}).get(license_class)


def check_privilege(license_data: dict, operation: dict) -> list:
    """
    Check operation against privileges.
    Returns list of warning strings. Empty = no warnings.
    Operator may ALWAYS proceed -- warnings are advisory only.

    operation keys:
      frequency_hz -- frequency in Hz
      mode         -- mode string (SSB, CW, FT8, etc.)
      power_w      -- transmit power in watts
    """
    warnings = []
    profile = get_privilege_profile(license_data)
    if not profile:
        return warnings

    callsign = license_data.get("callsign", "")
    license_class = license_data.get("license_class", "")
    authority = license_data.get("authority", "")

    freq_hz = operation.get("frequency_hz", 0)
    mode = operation.get("mode", "").upper()
    power_w = operation.get("power_w", 0)

    # Power check
    max_power = profile.get("max_power_w", 9999)
    if power_w > max_power:
        warnings.append(
            f"WARNING [{callsign}]: Power {power_w}W exceeds {license_class} "
            f"maximum of {max_power}W under {authority} regulations. "
            f"You may proceed -- you are responsible for compliance."
        )

    # HF phone check
    voice_modes = {"SSB", "USB", "LSB", "AM", "FM", "PHONE"}
    if 0 < freq_hz < 30_000_000 and mode in voice_modes:
        if not profile.get("hf_phone"):
            warnings.append(
                f"WARNING [{callsign}]: HF phone ({mode}) is not within "
                f"{license_class} class {authority} privileges. "
                f"You may proceed -- you are responsible for compliance."
            )

    return warnings


# ---------------------------------------------------------------------------
# LicenseAdvisor class
# ---------------------------------------------------------------------------

class LicenseAdvisor:
    """License advisor. Validates callsign, provides privilege warnings."""

    def __init__(self, callsign: str):
        self.callsign = callsign.strip().upper()
        self.license_data = None

    def validate(self, use_cache: bool = True) -> dict:
        if use_cache:
            cached = load_cached_license()
            if cached and cached.get("callsign") == self.callsign:
                log.info(f"  Using cached license data for {self.callsign}")
                self.license_data = cached
                return cached
        self.license_data = lookup_license(self.callsign)
        save_license_cache(self.license_data)
        return self.license_data

    def warn(self, operation: dict) -> list:
        if not self.license_data:
            return []
        return check_privilege(self.license_data, operation)

    def summary(self) -> str:
        if not self.license_data:
            return "License not validated."
        d = self.license_data
        expiry = f" (expires {d['expiry']})" if d.get("expiry") else ""
        name = f" -- {d['name']}" if d.get("name") else ""
        return (
            f"{d['callsign']}{name} | "
            f"{d['authority']} {d['license_class']}{expiry} | "
            f"Status: {d['status']}"
        )


# ---------------------------------------------------------------------------
# Standalone CLI
# ---------------------------------------------------------------------------

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    if len(sys.argv) < 2:
        print(f"Usage: python3 license_advisor-v{VERSION}.py <CALLSIGN>")
        sys.exit(1)

    callsign = sys.argv[1].strip().upper()

    print("=" * 60)
    print("  Ham System License Advisor")
    print(f"  Version {VERSION}")
    print("=" * 60)
    print()

    advisor = LicenseAdvisor(callsign)

    try:
        data = advisor.validate(use_cache=False)
    except (LookupError, ValueError) as e:
        print(f"FATAL: {e}")
        print()
        print("License validation failed.")
        sys.exit(1)

    print(f"  Callsign     : {data['callsign']}")
    if data.get("name"):
        print(f"  Name         : {data['name']}")
    print(f"  Authority    : {data['authority']}")
    print(f"  Class        : {data['license_class']}")
    print(f"  Status       : {data['status']}")
    if data.get("expiry"):
        print(f"  Expiry       : {data['expiry']}")
    if data.get("grid_square"):
        print(f"  Grid Square  : {data['grid_square']}")
    if data.get("notes"):
        print(f"  Notes        : {data['notes']}")
    print()

    profile = get_privilege_profile(data)
    if profile:
        print("  Privileges:")
        print(f"    HF Phone   : {'Yes' if profile['hf_phone'] else 'No'}")
        print(f"    HF CW      : {'Yes' if profile['hf_cw'] else 'No'}")
        print(f"    HF Digital : {'Yes' if profile['hf_digital'] else 'No'}")
        print(f"    VHF/UHF    : {'Yes' if profile['vhf_uhf'] else 'No'}")
        print(f"    Max Power  : {profile['max_power_w']}W")
        print(f"    HF Bands   : {', '.join(profile['hf_bands'])}")
        if profile.get("notes"):
            print(f"    Notes      : {profile['notes']}")
    print()
    print(f"  Cached to: {CACHE_PATH}")
    print()


if __name__ == "__main__":
    main()

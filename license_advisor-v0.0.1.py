#!/usr/bin/env python3
"""
license_advisor-v0.0.1.py — Ham System License Advisor
Project: Ham System — Integrated Ham Radio Control Platform
Author:  Dale — Hybrid RobotiX / The Accessibility Files
Version: 0.0.1

Validates the operator's amateur radio license against the appropriate
licensing authority database. This is the FIRST step in initialization —
if the callsign cannot be verified, nothing else proceeds.

Philosophy:
  - This is a HELPER, not a gatekeeper
  - The operator is ALWAYS the responsible party
  - The system WARNS but NEVER BLOCKS based on license class
  - Warnings are informational only

Supported authorities:
  - FCC   (US)     — Live API via callook.info
  - ISED  (Canada) — Local cache from ISED database ZIP
  - Ofcom (UK)     — Local cache from Ofcom open data

Usage:
  python3 license_advisor-v0.0.1.py --callsign YOURCALL
  python3 license_advisor-v0.0.1.py --callsign YOURCALL --refresh
"""

VERSION = "0.0.1"

import sys
import json
import argparse
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

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

CONFIG_DIR         = Path("config")
CACHE_PATH         = CONFIG_DIR / "license_cache-v0.0.1.json"
ISED_CACHE_PATH    = CONFIG_DIR / "ised_db-v0.0.1.txt"
OFCOM_CACHE_PATH   = CONFIG_DIR / "ofcom_db-v0.0.1.csv"

CALLOOK_API        = "https://callook.info/{callsign}/json"
ISED_DB_URL        = "https://apc-cap.ic.gc.ca/datafiles/amateur.zip"
CACHE_MAX_AGE_DAYS = 7

# Callsign prefix → authority mapping
FCC_PREFIXES   = ("A", "K", "N", "W")
ISED_PREFIXES  = ("VE", "VA", "VY", "VO", "VB", "VC", "VG", "VX")
OFCOM_PREFIXES = ("G", "M", "2E", "2I", "2W", "2D", "2U")

# FCC operator class codes → human readable
FCC_CLASS_MAP = {
    "T":  "Technician",
    "G":  "General",
    "A":  "Advanced",
    "E":  "Amateur Extra",
    "N":  "Novice",
    "P":  "Technician Plus",
}

# ---------------------------------------------------------------------------
# Authority detection
# ---------------------------------------------------------------------------

def detect_authority(callsign: str) -> str:
    """
    Determine licensing authority from callsign prefix.
    Returns 'FCC', 'ISED', 'OFCOM', or 'UNKNOWN'.
    """
    cs = callsign.upper().strip()

    for prefix in ISED_PREFIXES:
        if cs.startswith(prefix):
            return "ISED"

    for prefix in OFCOM_PREFIXES:
        if cs.startswith(prefix):
            return "OFCOM"

    for prefix in FCC_PREFIXES:
        if cs.startswith(prefix):
            return "FCC"

    return "UNKNOWN"


# ---------------------------------------------------------------------------
# FCC lookup via callook.info
# ---------------------------------------------------------------------------

def lookup_fcc(callsign: str) -> dict:
    """
    Query callook.info for FCC callsign data.
    Returns a normalized license dict or raises an exception.
    """
    url = CALLOOK_API.format(callsign=callsign.upper())
    log.info(f"  Querying callook.info for {callsign.upper()}...")

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": f"HamSystem/{VERSION} license_advisor"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise ConnectionError(f"callook.info unreachable: {e}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from callook.info: {e}")

    status = data.get("status", "").upper()

    if status == "INVALID":
        return {
            "found":         False,
            "callsign":      callsign.upper(),
            "authority":     "FCC",
            "status":        "NOT_FOUND",
            "license_class": None,
            "expiry":        None,
            "grid_square":   None,
            "name":          None,
        }

    if status == "UPDATING":
        raise ConnectionError(
            "callook.info is currently updating its database (usually < 5 min). "
            "Please try again shortly."
        )

    raw_class = data.get("current", {}).get("operClass", "")
    license_class = FCC_CLASS_MAP.get(raw_class, raw_class or "Unknown")

    expiry = data.get("otherInfo", {}).get("expiryDate", "")
    grid   = data.get("location", {}).get("gridsquare", "")
    name   = data.get("name", "")

    # Check expiry
    license_status = "VALID"
    if expiry:
        try:
            exp_date = datetime.strptime(expiry, "%m/%d/%Y").date()
            if exp_date < datetime.now(timezone.utc).date():
                license_status = "EXPIRED"
        except ValueError:
            pass

    return {
        "found":         True,
        "callsign":      callsign.upper(),
        "authority":     "FCC",
        "status":        license_status,
        "license_class": license_class,
        "expiry":        expiry,
        "grid_square":   grid,
        "name":          name,
    }


# ---------------------------------------------------------------------------
# ISED (Canada) lookup
# ---------------------------------------------------------------------------

def lookup_ised(callsign: str) -> dict:
    """
    Look up a Canadian callsign from the locally cached ISED database.
    Downloads and caches the database if not present or stale.
    """
    import zipfile
    import io

    cs = callsign.upper().strip()

    # Download/refresh cache if needed
    if not ISED_CACHE_PATH.exists() or _cache_stale(ISED_CACHE_PATH):
        log.info("  Downloading ISED amateur radio database...")
        try:
            req = urllib.request.Request(
                ISED_DB_URL,
                headers={"User-Agent": f"HamSystem/{VERSION} license_advisor"}
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                zip_data = response.read()
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                # The ZIP contains a text file — extract the first .txt file
                txt_files = [f for f in zf.namelist() if f.endswith(".txt") or f.endswith(".TXT")]
                if not txt_files:
                    raise ValueError("No text file found in ISED ZIP")
                content = zf.read(txt_files[0]).decode("latin-1")
            CONFIG_DIR.mkdir(exist_ok=True)
            ISED_CACHE_PATH.write_text(content, encoding="utf-8")
            log.info(f"  ISED database cached at {ISED_CACHE_PATH}")
        except Exception as e:
            if ISED_CACHE_PATH.exists():
                log.warning(f"  Could not refresh ISED database: {e} — using stale cache")
            else:
                raise ConnectionError(f"Could not download ISED database: {e}")

    # Search the cached database
    log.info(f"  Searching ISED database for {cs}...")
    db_text = ISED_CACHE_PATH.read_text(encoding="utf-8")

    for line in db_text.splitlines():
        if cs in line.upper():
            # ISED format is pipe or comma delimited — parse basic fields
            parts = line.split("|") if "|" in line else line.split(",")
            if len(parts) >= 3:
                return {
                    "found":         True,
                    "callsign":      cs,
                    "authority":     "ISED",
                    "status":        "VALID",
                    "license_class": parts[2].strip() if len(parts) > 2 else "Unknown",
                    "expiry":        None,
                    "grid_square":   None,
                    "name":          parts[1].strip() if len(parts) > 1 else None,
                }

    return {
        "found":         False,
        "callsign":      cs,
        "authority":     "ISED",
        "status":        "NOT_FOUND",
        "license_class": None,
        "expiry":        None,
        "grid_square":   None,
        "name":          None,
    }


# ---------------------------------------------------------------------------
# Ofcom (UK) lookup
# ---------------------------------------------------------------------------

def lookup_ofcom(callsign: str) -> dict:
    """
    Look up a UK callsign from locally cached Ofcom open data.
    UK callsign prefix encodes the license class directly, so class can
    be inferred without a full database lookup if needed.
    """
    cs = callsign.upper().strip()

    # Infer class from callsign structure as fallback
    # Full: G, M prefix with 3-letter suffix e.g. G4xxx, M0xxx
    # Intermediate: 2E prefix e.g. 2E0xxx
    # Foundation: M3, M6 prefix
    inferred_class = _infer_ofcom_class(cs)

    # If we have a cached Ofcom database, search it
    if OFCOM_CACHE_PATH.exists() and not _cache_stale(OFCOM_CACHE_PATH):
        log.info(f"  Searching Ofcom database for {cs}...")
        try:
            db_text = OFCOM_CACHE_PATH.read_text(encoding="utf-8")
            for line in db_text.splitlines():
                if cs in line.upper():
                    return {
                        "found":         True,
                        "callsign":      cs,
                        "authority":     "OFCOM",
                        "status":        "VALID",
                        "license_class": inferred_class,
                        "expiry":        None,
                        "grid_square":   None,
                        "name":          None,
                    }
        except Exception:
            pass

    # Fall back to prefix-based inference
    if inferred_class:
        log.info(f"  UK callsign {cs} — class inferred from prefix: {inferred_class}")
        log.warning("  Note: Ofcom database not cached — class inferred from callsign prefix only.")
        log.warning("  Run with --refresh to download the Ofcom database for full verification.")
        return {
            "found":         True,
            "callsign":      cs,
            "authority":     "OFCOM",
            "status":        "INFERRED",
            "license_class": inferred_class,
            "expiry":        None,
            "grid_square":   None,
            "name":          None,
        }

    return {
        "found":         False,
        "callsign":      cs,
        "authority":     "OFCOM",
        "status":        "NOT_FOUND",
        "license_class": None,
        "expiry":        None,
        "grid_square":   None,
        "name":          None,
    }


def _infer_ofcom_class(callsign: str) -> str:
    """Infer UK license class from callsign prefix structure."""
    cs = callsign.upper()
    if cs.startswith("M3") or cs.startswith("M6"):
        return "Foundation"
    if cs.startswith("2E") or cs.startswith("2I") or cs.startswith("2W") or cs.startswith("2D"):
        return "Intermediate"
    if cs.startswith(("G", "M", "GW", "GM", "GI", "GD", "GU", "GJ")):
        return "Full"
    return None


# ---------------------------------------------------------------------------
# Cache utilities
# ---------------------------------------------------------------------------

def _cache_stale(path: Path) -> bool:
    """Return True if the cache file is older than CACHE_MAX_AGE_DAYS."""
    from datetime import timedelta
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    age = datetime.now(timezone.utc) - mtime
    return age > timedelta(days=CACHE_MAX_AGE_DAYS)


def save_cache(result: dict):
    """Save license lookup result to cache file."""
    CONFIG_DIR.mkdir(exist_ok=True)
    result["last_verified"] = datetime.now(timezone.utc).isoformat()
    CACHE_PATH.write_text(json.dumps(result, indent=4) + "\n")
    log.info(f"  License data cached at {CACHE_PATH}")


def load_cache() -> dict:
    """Load cached license data. Returns None if not present."""
    if not CACHE_PATH.exists():
        return None
    try:
        return json.loads(CACHE_PATH.read_text())
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main lookup entry point
# ---------------------------------------------------------------------------

def validate_license(callsign: str, refresh: bool = False) -> dict:
    """
    Validate a callsign against the appropriate licensing authority.
    Returns a license result dict. Aborts with sys.exit(1) if not found.
    """
    cs = callsign.upper().strip()

    # Check cache first unless refresh requested
    if not refresh:
        cached = load_cache()
        if cached and cached.get("callsign") == cs:
            age_note = ""
            if _cache_stale(CACHE_PATH):
                age_note = " (cache is stale — run with --refresh to update)"
            log.info(f"  Using cached license data for {cs}{age_note}")
            return cached

    authority = detect_authority(cs)
    log.info(f"  Callsign: {cs}")
    log.info(f"  Detected authority: {authority}")

    if authority == "UNKNOWN":
        log.warning(f"  Could not determine licensing authority for '{cs}'.")
        log.warning("  Callsign prefix not recognized as FCC, ISED, or Ofcom.")
        log.warning("  If this is a valid callsign, please report it as an issue.")
        sys.exit(1)

    # Perform lookup
    if authority == "FCC":
        result = lookup_fcc(cs)
    elif authority == "ISED":
        result = lookup_ised(cs)
    elif authority == "OFCOM":
        result = lookup_ofcom(cs)

    return result


def print_result(result: dict):
    """Display license lookup result to the operator."""
    log.info("")
    log.info("  ── License Verification Result ──────────────────────────────")
    log.info(f"  Callsign      : {result.get('callsign', 'N/A')}")
    log.info(f"  Authority     : {result.get('authority', 'N/A')}")
    log.info(f"  Status        : {result.get('status', 'N/A')}")
    log.info(f"  License Class : {result.get('license_class', 'N/A')}")
    if result.get('name'):
        log.info(f"  Name          : {result.get('name')}")
    if result.get('expiry'):
        log.info(f"  Expiry        : {result.get('expiry')}")
    if result.get('grid_square'):
        log.info(f"  Grid Square   : {result.get('grid_square')}")
    if result.get('status') == "INFERRED":
        log.warning("  NOTE: Class inferred from callsign prefix — not verified against database.")
    log.info("  ─────────────────────────────────────────────────────────────")
    log.info("")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Ham System License Advisor — validate callsign and license class"
    )
    parser.add_argument(
        "--callsign", "-c",
        required=True,
        help="Amateur radio callsign to validate"
    )
    parser.add_argument(
        "--refresh", "-r",
        action="store_true",
        help="Force refresh — bypass cache and re-query authority"
    )
    args = parser.parse_args()

    log.info("=" * 70)
    log.info("  Ham System License Advisor")
    log.info(f"  Version {VERSION}")
    log.info("  Hybrid RobotiX / The Accessibility Files")
    log.info("=" * 70)
    log.info("")
    log.info("Step 0: Validating license...")

    try:
        result = validate_license(args.callsign, refresh=args.refresh)
    except ConnectionError as e:
        log.error(f"  Network error: {e}")
        log.error("  Cannot validate license — check network connection.")
        sys.exit(1)
    except Exception as e:
        log.error(f"  Unexpected error during license lookup: {e}")
        sys.exit(1)

    print_result(result)

    if not result.get("found"):
        log.error(f"  CALLSIGN '{args.callsign.upper()}' NOT FOUND in {result.get('authority')} database.")
        log.error("  Please verify your callsign and try again.")
        log.error("  Initialization cannot proceed without a valid license.")
        sys.exit(1)

    if result.get("status") == "EXPIRED":
        log.warning(f"  WARNING: License for {result['callsign']} appears to be EXPIRED.")
        log.warning(f"  Expiry date: {result.get('expiry')}")
        log.warning("  Please renew your license. Proceeding with initialization.")
        log.warning("  The Ham System will warn you during operation.")

    # Save to cache
    save_cache(result)

    log.info(f"  License validated: {result['callsign']} — "
             f"{result.get('license_class', 'Unknown')} ({result.get('authority')})")
    log.info("  Initialization may proceed.")
    return result


if __name__ == "__main__":
    main()

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).parent
CACHE_DIR = BACKEND_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Load local project secrets first, then fallback to user home ~/.env if present.
load_dotenv(BACKEND_DIR / ".env", override=False)
load_dotenv(Path.home() / ".env", override=False)

SRTM_30M_NPZ = CACHE_DIR / "srtm_cajamarca_30m.npz"
EARTHDATA_CAJAMARCA_CACHE = CACHE_DIR / "earthdata_cajamarca.json"
MARKET_PRICES_CACHE_FILE = CACHE_DIR / "market_prices_cache.json"


def _nonempty(var_name: str) -> str:
    return os.getenv(var_name, "").strip()


def has_opentopography_key() -> bool:
    return bool(_nonempty("OPENTOPOGRAPHY_API_KEY"))


def get_opentopography_key() -> str:
    return _nonempty("OPENTOPOGRAPHY_API_KEY")


def has_earthdata_token() -> bool:
    return bool(_nonempty("EARTHDATA_TOKEN"))


def get_earthdata_token() -> str:
    return _nonempty("EARTHDATA_TOKEN")


def has_earthdata_login() -> bool:
    return bool(_nonempty("EARTHDATA_USERNAME") and _nonempty("EARTHDATA_PASSWORD"))


def get_earthdata_credentials() -> tuple[str, str]:
    return _nonempty("EARTHDATA_USERNAME"), _nonempty("EARTHDATA_PASSWORD")


def has_cdse_credentials() -> bool:
    return bool(_nonempty("CDSE_CLIENT_ID") and _nonempty("CDSE_CLIENT_SECRET"))


def get_cdse_credentials() -> tuple[str, str]:
    return _nonempty("CDSE_CLIENT_ID"), _nonempty("CDSE_CLIENT_SECRET")


def has_gemini_api_key() -> bool:
    return bool(_nonempty("GEMINI_API_KEY"))


def get_gemini_api_key() -> str:
    return _nonempty("GEMINI_API_KEY")


def get_gemini_model() -> str:
    return _nonempty("GEMINI_MODEL") or "gemini-3.5-flash-lite"


def get_integration_status() -> Dict[str, bool]:
    """Boolean-only status of Option A keys and pre-cached satellite files (never exposes values)."""
    return {
        "opentopography_key_present": has_opentopography_key(),
        "srtm_30m_cached": SRTM_30M_NPZ.exists(),
        "earthdata_token_present": has_earthdata_token(),
        "earthdata_login_present": has_earthdata_login(),
        "earthdata_cached": EARTHDATA_CAJAMARCA_CACHE.exists(),
        "cdse_credentials_present": has_cdse_credentials(),
        "gemini_key_present": has_gemini_api_key(),
        "midagri_prices_cached": MARKET_PRICES_CACHE_FILE.exists(),
    }

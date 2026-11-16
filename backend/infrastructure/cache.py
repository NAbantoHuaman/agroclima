"""Disk-backed JSON caches keyed by rounded lat/lon coordinates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from config import CACHE_DIR

CACHE_FILE = CACHE_DIR / "nasa_power_daily_cache.json"
ERA5_CACHE_FILE = CACHE_DIR / "era5_soil_cache.json"
SOILGRIDS_CACHE_FILE = CACHE_DIR / "soilgrids_isric_cache.json"
WEATHER_CACHE_FILE = CACHE_DIR / "live_weather_cache.json"


class JsonKeyedCache:
    """In-memory + persistent JSON disk cache keyed by rounded lat/lon."""

    def __init__(self, cache_path: Path) -> None:
        self.cache_path = cache_path
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._store: Dict[str, Dict[str, Any]] = {}
        self._load_disk()

    def _load_disk(self) -> None:
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self._store = data
            except Exception:
                self._store = {}

    def _save_disk(self) -> None:
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._store, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @staticmethod
    def _key(lat: float, lon: float) -> str:
        return f"{round(lat, 2):.2f},{round(lon, 2):.2f}"

    def get(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        return self._store.get(self._key(lat, lon))

    def set(self, lat: float, lon: float, payload: Dict[str, Any]) -> None:
        self._store[self._key(lat, lon)] = payload
        self._save_disk()


_POWER_CACHE = JsonKeyedCache(CACHE_FILE)
_ERA5_CACHE = JsonKeyedCache(ERA5_CACHE_FILE)
_SOILGRIDS_CACHE = JsonKeyedCache(SOILGRIDS_CACHE_FILE)

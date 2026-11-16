from __future__ import annotations

import asyncio
import json
import math
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
import numpy as np

from config import CACHE_DIR, get_cdse_credentials, has_cdse_credentials

CDSE_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
)
CDSE_STATS_URL = "https://sh.dataspace.copernicus.eu/statistics/v1"
SENTINEL2_CACHE_FILE = CACHE_DIR / "sentinel2_ndvi_cache.json"

_TOKEN_STATE: Dict[str, Any] = {"access_token": None, "expires_at": 0.0}

# Evalscript v3: excludes cloud/shadow/water via SCL and computes NDVI = (B08 - B04)/(B08 + B04)
_NDVI_EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B04", "B08", "SCL", "dataMask"] }],
    output: [
      { id: "ndvi", bands: 1, sampleType: "FLOAT32" },
      { id: "dataMask", bands: 1 }
    ]
  };
}
function evaluatePixel(samples) {
  let scl = samples.SCL;
  // Valid clear land pixels: 4=Vegetation, 5=Not vegetated, 6=Water (excluded below), 7=Unclassified
  let isClearLand = (scl === 4 || scl === 5 || scl === 7) && samples.dataMask === 1;
  let denom = samples.B08 + samples.B04;
  let ndviVal = denom > 0.0001 ? (samples.B08 - samples.B04) / denom : 0.0;
  return {
    ndvi: [ndviVal],
    dataMask: [isClearLand ? 1 : 0]
  };
}
"""


def _load_cache() -> Dict[str, Any]:
    if SENTINEL2_CACHE_FILE.exists():
        try:
            with open(SENTINEL2_CACHE_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return raw if isinstance(raw, dict) else {}
        except Exception:
            return {}
    return {}


def _save_cache(store: Dict[str, Any]) -> None:
    try:
        SENTINEL2_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SENTINEL2_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


async def _get_access_token(client: httpx.AsyncClient) -> Optional[str]:
    now = time.time()
    if _TOKEN_STATE["access_token"] and now < float(_TOKEN_STATE["expires_at"]) - 45.0:
        return str(_TOKEN_STATE["access_token"])

    client_id, client_secret = get_cdse_credentials()
    if not client_id or not client_secret:
        return None

    try:
        resp = await client.post(
            CDSE_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=12.0,
        )
        resp.raise_for_status()
        tok = resp.json()
        access_token = tok.get("access_token")
        expires_in = float(tok.get("expires_in", 600))
        if access_token:
            _TOKEN_STATE["access_token"] = access_token
            _TOKEN_STATE["expires_at"] = now + expires_in
            return str(access_token)
    except Exception:
        return None
    return None


def _build_crs84_bounds(
    lat: float,
    lon: float,
    polygon: Optional[List[List[float]]],
) -> Dict[str, Any]:
    props = {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"}
    if polygon and len(polygon) >= 3:
        # GeoJSON uses [lon, lat] and must close ring
        ring = [[round(float(p[1]), 6), round(float(p[0]), 6)] for p in polygon]
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        return {
            "geometry": {"type": "Polygon", "coordinates": [ring]},
            "properties": props,
        }

    # Small parcel neighborhood box (~220m x 220m) centered on point
    d = 0.001
    return {
        "bbox": [round(lon - d, 6), round(lat - d, 6), round(lon + d, 6), round(lat + d, 6)],
        "properties": props,
    }


def _build_s2_cache_key(
    lat: float,
    lon: float,
    polygon: Optional[List[List[float]]],
) -> str:
    base = f"{round(lat, 3):.3f},{round(lon, 3):.3f}"
    if polygon and len(polygon) >= 3:
        lats = [float(p[0]) for p in polygon]
        lons = [float(p[1]) for p in polygon]
        span_lat = round(max(lats) - min(lats), 4)
        span_lon = round(max(lons) - min(lons), 4)
        return f"{base}|p{len(polygon)}|{span_lat:.4f}x{span_lon:.4f}"
    return base


async def fetch_sentinel2_monthly_ndvi(
    lat: float,
    lon: float,
    polygon: Optional[List[List[float]]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Fetches real 10 m Sentinel-2 L2A monthly cloud-masked NDVI via Copernicus Data Space
    Statistical API when CDSE_CLIENT_ID & CDSE_CLIENT_SECRET are configured.
    """
    if not has_cdse_credentials():
        return None

    cache_key = _build_s2_cache_key(lat, lon, polygon)
    store = _load_cache()
    if (
        cache_key in store
        and isinstance(store[cache_key], dict)
        and "latest_observation_date" in store[cache_key]
    ):
        return {**store[cache_key], "mode": "guardado"}

    now_utc = datetime.now(timezone.utc)
    end_dt = now_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_dt = end_dt - timedelta(days=365)
    recent_start_dt = now_utc - timedelta(days=60)

    # Approximate 10 m in degrees around Cajamarca latitude (~7°S) so CRS84 bbox works natively
    deg_per_10m_lat = 10.0 / 110574.0
    deg_per_10m_lon = 10.0 / (111320.0 * math.cos(math.radians(lat)))
    bounds = _build_crs84_bounds(lat, lon, polygon)

    def _make_payload(t_from: datetime, t_to: datetime, interval_iso: str) -> Dict[str, Any]:
        return {
            "input": {
                "bounds": bounds,
                "data": [
                    {
                        "type": "sentinel-2-l2a",
                        "dataFilter": {"maxCloudCoverage": 60, "mosaickingOrder": "leastCC"},
                    }
                ],
            },
            "aggregation": {
                "timeRange": {
                    "from": t_from.strftime("%Y-%m-%dT00:00:00Z"),
                    "to": t_to.strftime("%Y-%m-%dT23:59:59Z"),
                },
                "aggregationInterval": {"of": interval_iso},
                "evalscript": _NDVI_EVALSCRIPT,
                "resx": round(deg_per_10m_lon, 7),
                "resy": round(deg_per_10m_lat, 7),
            },
        }

    payload = _make_payload(start_dt, end_dt, "P1M")
    recent_payload = _make_payload(recent_start_dt, now_utc, "P5D")

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            token = await _get_access_token(client)
            if not token:
                return None

            req_headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            resp, recent_resp = await asyncio.gather(
                client.post(CDSE_STATS_URL, headers=req_headers, json=payload),
                client.post(CDSE_STATS_URL, headers=req_headers, json=recent_payload),
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])
            recent_data = recent_resp.json().get("data", []) if recent_resp.status_code == 200 else []

        monthly_buckets: Dict[int, List[float]] = {m: [] for m in range(1, 13)}
        for item in data:
            interval_from = str(item.get("interval", {}).get("from", ""))
            if len(interval_from) < 7:
                continue
            month_num = int(interval_from[5:7])
            stats = (
                item.get("outputs", {})
                .get("ndvi", {})
                .get("bands", {})
                .get("B0", {})
                .get("stats", {})
            )
            mean_val = stats.get("mean")
            sample_count = int(stats.get("sampleCount", 0) or 0)
            no_data = int(stats.get("noDataCount", 0) or 0)
            if mean_val is not None and sample_count > no_data and -0.1 <= float(mean_val) <= 0.98:
                monthly_buckets[month_num].append(float(mean_val))

        valid_months = sum(1 for v in monthly_buckets.values() if v)
        if valid_months < 4:
            return None

        # Extract newest clear 5-day Sentinel-2 pass observation
        latest_ndvi: Optional[float] = None
        latest_obs_date: Optional[str] = None
        for item in sorted(
            recent_data,
            key=lambda x: str((x.get("interval") or {}).get("to", "")),
            reverse=True,
        ):
            stats = (
                item.get("outputs", {})
                .get("ndvi", {})
                .get("bands", {})
                .get("B0", {})
                .get("stats", {})
            )
            mean_val = stats.get("mean")
            sample_count = int(stats.get("sampleCount", 0) or 0)
            no_data = int(stats.get("noDataCount", 0) or 0)
            if mean_val is not None and sample_count > no_data and -0.1 <= float(mean_val) <= 0.98:
                latest_ndvi = round(float(np.clip(float(mean_val), 0.12, 0.92)), 3)
                latest_obs_date = str((item.get("interval") or {}).get("to", ""))[:10]
                break

        # Interpolate any persistently cloudy Andean wet-season months cleanly across neighbors
        raw_series = [
            float(np.mean(monthly_buckets[m])) if monthly_buckets[m] else np.nan
            for m in range(1, 13)
        ]
        arr = np.array(raw_series, dtype=float)
        idx_valid = np.where(~np.isnan(arr))[0]
        arr_interp = np.interp(np.arange(12), idx_valid, arr[idx_valid], period=12)
        ndvi_vals = [round(float(np.clip(v, 0.12, 0.88)), 3) for v in arr_interp]
        if latest_ndvi is None and ndvi_vals:
            latest_ndvi = ndvi_vals[max(0, min(11, now_utc.month - 1))]

        result = {
            "ndvi": ndvi_vals,
            "observed_months": valid_months,
            "latest_ndvi": latest_ndvi,
            "latest_observation_date": latest_obs_date or end_dt.strftime("%Y-%m-%d"),
            "source": "cdse_sentinel2_10m",
            "mode": "en_vivo",
        }
        store[cache_key] = result
        _save_cache(store)
        return result
    except Exception:
        return None

"""External weather & climatology API clients (NASA POWER Daily + Open-Meteo Forecast)."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
import numpy as np
import pandas as pd

from domain.catalog import DAYS_IN_MONTH, load_zones_data
from domain.climate import _build_yearly_series_from_monthly, _idw_fallback_power
from infrastructure.cache import WEATHER_CACHE_FILE, _POWER_CACHE

NASA_POWER_DAILY_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def _classify_wmo_weather(code: int, temp_c: float, precip_mm: float, cloud_cover: float) -> Tuple[str, str]:
    """Maps Open-Meteo WMO weather code + local temperature/rain to UI weather icon & Spanish condition."""
    if temp_c <= 2.5 or code in (71, 73, 75, 77, 85, 86):
        return ("frost", "Frío intenso / Helada")
    if precip_mm >= 0.4 or code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99):
        if code in (95, 96, 99):
            return ("rainy", "Tormenta y lluvia")
        if code in (51, 53, 55, 56, 57):
            return ("rainy", "Llovizna en chacra")
        return ("rainy", "Lluvia activa")
    if code in (45, 48):
        return ("cloudy", "Neblina densa")
    if code == 3 or cloud_cover >= 72.0:
        return ("cloudy", "Cielo nublado")
    if code in (1, 2) or cloud_cover >= 28.0:
        return ("partly_cloudy", "Parcialmente nublado")
    return ("sunny", "Cielo despejado")


async def fetch_live_current_weather(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Fetches real-time weather from Open-Meteo Forecast API with a short 15-minute coordinate cache."""
    cache_key = f"{round(lat, 2):.2f}_{round(lon, 2):.2f}"
    now_ts = datetime.now(timezone.utc).timestamp()

    try:
        if WEATHER_CACHE_FILE.exists():
            raw_cache = json.loads(WEATHER_CACHE_FILE.read_text(encoding="utf-8"))
            entry = raw_cache.get(cache_key)
            if (
                isinstance(entry, dict)
                and (now_ts - float(entry.get("fetched_ts", 0))) < 900.0
                and isinstance(entry.get("daily_forecast_7d"), list)
                and len(entry["daily_forecast_7d"]) >= 7
            ):
                return entry
    except Exception:
        pass

    params = {
        "latitude": round(float(lat), 4),
        "longitude": round(float(lon), 4),
        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,cloud_cover",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
        "timezone": "auto",
        "forecast_days": 7,
    }
    try:
        async with httpx.AsyncClient(timeout=7.5) as client:
            resp = await client.get(OPEN_METEO_FORECAST_URL, params=params)
            resp.raise_for_status()
            payload = resp.json()

        cur = payload.get("current") or {}
        daily = payload.get("daily") or {}
        temp_c = cur.get("temperature_2m")
        if temp_c is None:
            return None

        d_times = daily.get("time") or []
        t_max_list = daily.get("temperature_2m_max") or []
        t_min_list = daily.get("temperature_2m_min") or []
        p_sum_list = daily.get("precipitation_sum") or []
        d_code_list = daily.get("weather_code") or []

        w_code = int(cur.get("weather_code", 1) or 1)
        precip = float(cur.get("precipitation", 0.0) or 0.0)
        rh = float(cur.get("relative_humidity_2m", 65.0) or 65.0)
        cloud = float(cur.get("cloud_cover", 45.0) or 45.0)
        t_val = round(float(temp_c), 1)
        t_max = round(float(t_max_list[0]), 1) if t_max_list and t_max_list[0] is not None else round(t_val + 4.0, 1)
        t_min = round(float(t_min_list[0]), 1) if t_min_list and t_min_list[0] is not None else round(t_val - 5.0, 1)
        w_type, w_label = _classify_wmo_weather(w_code, t_val, precip, cloud)

        daily_forecast_7d: List[Dict[str, Any]] = []
        for idx, d_date in enumerate(d_times[:7]):
            d_tmax = round(float(t_max_list[idx]), 1) if idx < len(t_max_list) and t_max_list[idx] is not None else t_max
            d_tmin = round(float(t_min_list[idx]), 1) if idx < len(t_min_list) and t_min_list[idx] is not None else t_min
            d_prec = round(float(p_sum_list[idx]), 1) if idx < len(p_sum_list) and p_sum_list[idx] is not None else 0.0
            d_wcode = int(d_code_list[idx]) if idx < len(d_code_list) and d_code_list[idx] is not None else w_code
            d_wtype, d_wlabel = _classify_wmo_weather(d_wcode, d_tmin, d_prec, 60.0 if d_prec >= 2.0 else 30.0)
            daily_forecast_7d.append({
                "date": str(d_date),
                "temp_max_c": d_tmax,
                "temp_min_c": d_tmin,
                "precip_mm": d_prec,
                "weather_code": d_wcode,
                "weather_type": d_wtype,
                "weather_label": d_wlabel,
            })

        result = {
            "temp_c": t_val,
            "max_temp_c": t_max,
            "min_temp_c": t_min,
            "rh_pct": round(rh, 0),
            "precip_mm": round(precip, 2),
            "weather_code": w_code,
            "cloud_cover_pct": round(cloud, 0),
            "weather_type": w_type,
            "weather_label": w_label,
            "daily_forecast_7d": daily_forecast_7d,
            "grid_elevation_m": float(payload.get("elevation", 2700.0) or 2700.0),
            "source": "Open-Meteo Tiempo Real (7 días)",
            "fetched_ts": now_ts,
        }

        try:
            cache_obj: Dict[str, Any] = {}
            if WEATHER_CACHE_FILE.exists():
                cache_obj = json.loads(WEATHER_CACHE_FILE.read_text(encoding="utf-8"))
                if not isinstance(cache_obj, dict):
                    cache_obj = {}
            cache_obj[cache_key] = result
            if len(cache_obj) > 64:
                oldest_keys = sorted(cache_obj.keys(), key=lambda k: float(cache_obj[k].get("fetched_ts", 0)))[:16]
                for ok in oldest_keys:
                    cache_obj.pop(ok, None)
            WEATHER_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            WEATHER_CACHE_FILE.write_text(json.dumps(cache_obj), encoding="utf-8")
        except Exception:
            pass

        return result
    except Exception:
        return None


async def fetch_nasa_power_climatology(lat: float, lon: float) -> Dict[str, Any]:
    """
    Fetches 20-year real daily time series (2006–2025) from NASA POWER Daily API, including
    GWETTOP (0–5 cm top soil wetness), annual climatic trends, and heavy storm / frost day frequencies.
    Falls back gracefully to calibrated 20-year Cajamarca profiles when offline.
    """
    cached = _POWER_CACHE.get(lat, lon)
    if (
        cached is not None
        and int(cached.get("years_analyzed", 0)) >= 15
        and isinstance(cached.get("yearly_raw"), list)
        and len(cached["yearly_raw"]) >= 15
        and isinstance(cached.get("gwetroot"), list)
        and len(cached["gwetroot"]) == 12
    ):
        return {**cached, "cache_hit": True}

    params = {
        "parameters": "T2M,T2M_MIN,T2M_MAX,PRECTOTCORR,ALLSKY_SFC_SW_DWN,RH2M,GWETTOP,GWETROOT,TSOIL1",
        "community": "AG",
        "longitude": f"{lon:.4f}",
        "latitude": f"{lat:.4f}",
        "start": "20060101",
        "end": "20251231",
        "format": "JSON",
    }

    try:
        async with httpx.AsyncClient(timeout=22.0) as client:
            resp = await client.get(NASA_POWER_DAILY_URL, params=params)
            resp.raise_for_status()
            raw = resp.json()

        prop = raw.get("properties", {}).get("parameter", {})
        coords = raw.get("geometry", {}).get("coordinates", [lon, lat, 2850.0])
        grid_elev = float(coords[2]) if len(coords) >= 3 and coords[2] is not None else 2850.0

        # Build clean daily DataFrame indexed by YYYYMMDD
        t2m_dict = prop.get("T2M", {})
        if not t2m_dict:
            raise ValueError("Empty daily T2M in NASA POWER response")

        rows: List[Dict[str, Any]] = []
        for date_str in sorted(t2m_dict.keys()):
            if len(date_str) != 8:
                continue
            month_num = int(date_str[4:6])
            year_num = int(date_str[:4])

            def _clean(pname: str, default: float) -> float:
                val = prop.get(pname, {}).get(date_str, default)
                if val is None or float(val) <= -900:
                    return default
                return float(val)

            tsoil_raw = _clean("TSOIL1", 14.0)
            if tsoil_raw > 150.0:
                tsoil_raw -= 273.15

            rows.append({
                "year": year_num,
                "month": month_num,
                "T2M": _clean("T2M", 14.0),
                "T2M_MIN": _clean("T2M_MIN", 5.5),
                "T2M_MAX": _clean("T2M_MAX", 20.5),
                "PRECTOTCORR": max(0.0, _clean("PRECTOTCORR", 1.8)),
                "SOLAR": _clean("ALLSKY_SFC_SW_DWN", 18.0),
                "RH2M": _clean("RH2M", 70.0),
                "GWETTOP": float(np.clip(_clean("GWETTOP", 0.52), 0.05, 0.98)),
                "GWETROOT": float(np.clip(_clean("GWETROOT", _clean("GWETTOP", 0.52)), 0.05, 0.98)),
                "TSOIL1_C": tsoil_raw,
            })

        df_daily = pd.DataFrame(rows)
        n_years = max(1, int(df_daily["year"].nunique()))

        t2m_c: List[float] = []
        t2m_min_c: List[float] = []
        t2m_max_c: List[float] = []
        precip_monthly: List[float] = []
        solar_monthly: List[float] = []
        rh_monthly: List[float] = []
        gwettop_monthly: List[float] = []
        gwetroot_monthly: List[float] = []
        tsoil_monthly: List[float] = []
        storm_days_monthly: List[float] = []
        max_daily_rain_monthly: List[float] = []

        for m in range(1, 13):
            sub = df_daily[df_daily["month"] == m]
            t2m_c.append(round(float(sub["T2M"].mean()), 2))
            t2m_min_c.append(round(float(sub["T2M_MIN"].mean()), 2))
            t2m_max_c.append(round(float(sub["T2M_MAX"].mean()), 2))
            precip_monthly.append(round(float(sub["PRECTOTCORR"].mean() * DAYS_IN_MONTH[m - 1]), 2))
            solar_monthly.append(round(float(sub["SOLAR"].mean()), 2))
            rh_monthly.append(round(float(sub["RH2M"].mean()), 2))
            gwettop_monthly.append(round(float(sub["GWETTOP"].mean()), 3))
            gwetroot_monthly.append(round(float(sub["GWETROOT"].mean()), 3))
            tsoil_monthly.append(round(float(sub["TSOIL1_C"].mean()), 2))
            # Count actual intense daily rainfall events (>=12 mm/day) averaged per year
            intense_cnt = float((sub["PRECTOTCORR"] >= 12.0).sum()) / n_years
            storm_days_monthly.append(round(intense_cnt, 1))
            max_daily_rain_monthly.append(round(float(sub["PRECTOTCORR"].quantile(0.97)), 1))

        yearly_raw: List[Dict[str, Any]] = []
        for yr in sorted(df_daily["year"].unique()):
            ysub = df_daily[df_daily["year"] == yr]
            onset_sub = ysub[ysub["month"].isin([10, 11, 12])]
            cold_sub = ysub[ysub["month"].isin([5, 6, 7, 8])]
            yearly_raw.append({
                "year": int(yr),
                "precip_annual_mm": round(float(ysub["PRECTOTCORR"].sum()), 1),
                "onset_rain_mm": round(float(onset_sub["PRECTOTCORR"].sum()), 1),
                "t2m_mean_c": round(float(ysub["T2M"].mean()), 2),
                "t2m_min_c": round(float(cold_sub["T2M_MIN"].mean() if len(cold_sub) else ysub["T2M_MIN"].mean()), 2),
                "frost_days_raw": round(float((ysub["T2M_MIN"] <= 2.2).sum()), 1),
                "storm_days_12mm": round(float((ysub["PRECTOTCORR"] >= 12.0).sum()), 1),
                "gwettop_mean": round(float(ysub["GWETTOP"].mean()), 3),
            })

        payload = {
            "source": "live_nasa_power",
            "source_label": f"NASA POWER Diario 2006–2025 ({n_years} años En Vivo)",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "power_grid_elevation_m": round(grid_elev, 1),
            "t2m_c": t2m_c,
            "t2m_min_c": t2m_min_c,
            "t2m_max_c": t2m_max_c,
            "precip_mm": precip_monthly,
            "solar_mj_m2_day": solar_monthly,
            "rh2m_pct": rh_monthly,
            "gwettop": gwettop_monthly,
            "gwetroot": gwetroot_monthly,
            "tsoil1_c": tsoil_monthly,
            "storm_days_12mm": storm_days_monthly,
            "max_daily_precip_mm": max_daily_rain_monthly,
            "has_daily_metrics": True,
            "years_analyzed": n_years,
            "yearly_raw": yearly_raw,
            "cache_hit": False,
        }
        _POWER_CACHE.set(lat, lon, payload)
        return payload
    except Exception as exc:
        if cached is not None and cached.get("source") == "live_nasa_power":
            yearly_raw = cached.get("yearly_raw") or _build_yearly_series_from_monthly(
                cached.get("t2m_c", [14.0] * 12),
                cached.get("t2m_min_c", [5.0] * 12),
                cached.get("precip_mm", [60.0] * 12),
                cached.get("gwettop"),
            )
            return {
                **cached,
                "source_label": "NASA POWER Guardado (Serie 20 años real)",
                "years_analyzed": len(yearly_raw),
                "yearly_raw": yearly_raw,
                "cache_hit": True,
                "fallback_reason": str(exc)[:180],
            }
        beacons = load_zones_data()["beacon_parcels"]
        min_b_km = min(
            math.hypot((lat - b["lat"]) * 111.0, (lon - b["lon"]) * 110.0)
            for b in beacons
        )
        if min_b_km > 35.0:
            raise RuntimeError(
                f"NASA POWER no respondió y no hay caché satelital guardada para ({lat:.3f}, {lon:.3f})."
            ) from exc
        fallback = _idw_fallback_power(lat, lon)
        fallback["cache_hit"] = False
        fallback["fallback_reason"] = str(exc)[:180]
        return fallback

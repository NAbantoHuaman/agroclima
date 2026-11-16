"""Harmonizes NASA POWER, DEM, ERA5-Land, Sentinel-2, SoilGrids, Earthdata, and weather streams."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from domain.catalog import DAYS_IN_MONTH, MONTH_LABELS_ES, load_zones_data
from domain.climate import _build_yearly_series_from_monthly
from infrastructure.weather_power_client import _classify_wmo_weather


def _market_dataset_rows(market_summary: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not market_summary:
        return []
    raw_mode = market_summary.get("mode", "referencia_inia")
    ds_mode = raw_mode if raw_mode in ("en_vivo", "guardado") else "estimado"
    quoted = int(market_summary.get("live_crops_count", 0)) + int(market_summary.get("mixed_crops_count", 0))
    total = int(market_summary.get("total_crops_count", 24))
    mkt_label = market_summary.get("primary_market_label") or "Cajamarca"
    date_note = f" ({market_summary['latest_price_date']})" if market_summary.get("latest_price_date") else ""
    return [
        {
            "sensor": "Precios MIDAGRI SISAP · Agromercado · EMMSA + BCRP",
            "resolution": f"Mercado {mkt_label} · Diario / FOB",
            "variables": f"Precios mayorista/FOB en {quoted}/{total} cultivos{date_note} y TC BCRP",
            "mode": ds_mode,
            "plain": market_summary.get("economic_reference_label")
            or "Precios oficiales MIDAGRI/EMMSA convertidos a chacra + Ref. INIA en forrajes.",
        }
    ]


def _build_dataset_provenance(
    raw_power: Dict[str, Any],
    terrain: Dict[str, Any],
    era5_data: Optional[Dict[str, Any]],
    sentinel2_data: Optional[Dict[str, Any]],
    earthdata: Optional[Dict[str, Any]],
    market_summary: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Honest per-dataset provenance reflecting exact live vs cached vs derived sources.
    """
    if raw_power.get("source") == "live_nasa_power":
        power_mode = "guardado" if raw_power.get("cache_hit") else "en_vivo"
    else:
        power_mode = "respaldo"

    if sentinel2_data is not None:
        latest_ndvi = sentinel2_data.get("latest_ndvi")
        latest_date = sentinel2_data.get("latest_observation_date")
        latest_note = (
            f" · última {latest_date} (NDVI {float(latest_ndvi):.2f})"
            if latest_ndvi is not None and latest_date
            else ""
        )
        ndvi_sensor = "Copernicus Sentinel-2 L2A (NDVI)"
        ndvi_res = f"10 m reales ({sentinel2_data.get('observed_months', 12)}/12 meses despejados{latest_note})"
        ndvi_mode = str(sentinel2_data.get("mode", "en_vivo"))
        ndvi_plain = "Verdor real de esta parcela medido desde Sentinel-2 cada mes y en su última pasada despejada."
    else:
        ndvi_sensor = "Sentinel-2 / Landsat (NDVI)"
        ndvi_res = "Perfil mensual por tipo de manejo"
        ndvi_mode = "estimado"
        ndvi_plain = "Verdor estimado según el cultivo actual (agrega CDSE en .env para NDVI real 10 m)."

    if earthdata and earthdata.get("smap_monthly"):
        sm_sensor = f"NASA SMAP ({earthdata.get('smap_product', 'AppEEARS')})"
        sm_res = "Serie mensual AppEEARS para Cajamarca"
        sm_mode = "guardado"
        sm_plain = "Humedad real del suelo descargada de NASA SMAP (y ajustada al terreno)."
    elif era5_data is not None:
        sm_sensor = "ERA5-Land + NASA GWETTOP"
        sm_res = "~9 km ECMWF + 0.5° MERRA-2 (0–7 cm), ajustado a parcela"
        sm_mode = str(era5_data.get("mode", "en_vivo"))
        sm_plain = "Humedad real del suelo medida por ERA5-Land y NASA MERRA-2 (0–7 cm)."
    else:
        sm_sensor = "SMAP / Humedad del suelo"
        sm_res = "Derivado de lluvia, demanda y pendiente"
        sm_mode = "estimado"
        sm_plain = "Cuánta agua guarda la tierra en la capa superior (modelo hídrico local)."

    if earthdata and earthdata.get("ecostress_et_daily"):
        et_sensor = f"NASA ECOSTRESS ({earthdata.get('ecostress_product', 'ECO_L3T_JET.002')})"
        et_res = "Evapotranspiración diaria AppEEARS + Makkink"
        et_mode = "guardado"
        et_plain = "Demanda de agua real medida por satélite térmico NASA ECOSTRESS y ajustada al relieve."
    elif era5_data and isinstance(era5_data.get("et0_fao_mm"), list) and len(era5_data["et0_fao_mm"]) == 12:
        et_sensor = "ERA5-Land ET0 FAO-56 + NASA POWER"
        et_res = "~9 km ECMWF FAO Penman-Monteith + Makkink"
        et_mode = str(era5_data.get("mode", "en_vivo"))
        et_plain = "Evapotranspiración de referencia calculada con datos reales ERA5-Land y radiación NASA POWER."
    else:
        et_sensor = "ET0 Makkink (NASA POWER)"
        et_res = "Derivado de radiación solar, VPD y temperatura"
        et_mode = "estimado"
        et_plain = "Consumo estimado de agua del cultivo según sol, temperatura y humedad del aire."

    if raw_power.get("has_daily_metrics"):
        storm_sensor = "Tormentas (NASA POWER Diario / GPM)"
        storm_res = "Días diarios >=12 mm y P97 (2006–2025) + capa GIBS"
        storm_mode = power_mode
        storm_plain = "Aguaceros fuertes reales medidos día a día durante 20 años y capa visual GPM."
    else:
        storm_sensor = "GPM IMERG"
        storm_res = "Derivado de lluvia mensual y altura (20 años)"
        storm_mode = "estimado"
        storm_plain = "Meses con aguaceros que pueden lavar la tierra."

    dem_source = str(terrain.get("dem_source", ""))
    if dem_source == "srtm_30m_opentopography":
        dem_sensor = "SRTM GL1 (30 m)"
        aspect_lbl = terrain.get("aspect_label")
        span_m = terrain.get("elevation_span_m")
        micro_txt = ""
        if aspect_lbl and terrain.get("polygon_vertices_sampled"):
            micro_txt = f" · ladera {aspect_lbl}, desnivel {span_m or 0:.0f} m"
        elif aspect_lbl:
            micro_txt = f" · orientación {aspect_lbl}"
        dem_res = f"30 m reales vía OpenTopography (SRTM GL1{micro_txt})"
        dem_mode = str(terrain.get("dem_mode") or "guardado")
        dem_plain = (
            f"Altura, pendiente y orientación ({aspect_lbl}) medidas cada 30 m sobre tu parcela."
            if aspect_lbl
            else "Altura y pendiente reales cada 30 metros de tu parcela."
        )
    elif dem_source == "open_meteo_cop90":
        dem_sensor = "Copernicus DEM (90 m)"
        aspect_lbl = terrain.get("aspect_label")
        dem_res = f"Grilla 90 m en vivo (Open-Meteo Elevation{f' · {aspect_lbl}' if aspect_lbl else ''})"
        dem_mode = str(terrain.get("dem_mode", "en_vivo"))
        dem_plain = "Altura, pendiente y orientación medidas por satélite cada 90 metros."
    else:
        dem_sensor = "SRTM / Relieve local"
        dem_res = "Puntos de referencia de Cajamarca"
        dem_mode = "modelo"
        dem_plain = "Altura y pendiente interpoladas desde puntos de referencia."

    soil_prof = terrain.get("soil_profile") or {}
    soil_mode = str(soil_prof.get("source_mode", "calibrado_inia"))
    if soil_mode in {"en_vivo", "guardado"}:
        soil_sensor = "SoilGrids ISRIC v2.0 (250 m)"
        radius_m = soil_prof.get("nearby_radius_m")
        radius_lbl = "~1.3 km" if radius_m and int(radius_m) >= 800 else "~350 m"
        soil_res = (
            f"Capas 0–30 cm reales · anillo agrícola {radius_lbl}"
            if soil_prof.get("nearby_sampled")
            else "Capas 0–30 cm reales vía REST API"
        )
        soil_ds_mode = soil_mode
        soil_plain = (
            f"pH {soil_prof.get('ph', '–')}, textura {soil_prof.get('texture_class', 'franca')}, "
            f"materia orgánica {soil_prof.get('organic_matter_pct', '–')}% y nitrógeno {soil_prof.get('nitrogen_g_kg', '–')} g/kg."
        )
    else:
        soil_sensor = "Suelos ZEE Cajamarca / INIA"
        soil_res = "Referencia regional 0–30 cm"
        soil_ds_mode = "estimado"
        soil_plain = "pH, textura y fertilidad estimados desde la zonificación ZEE/INIA de Cajamarca."

    return [
        {
            "sensor": "NASA POWER (2006–2025) + Sensibilidad 2 años",
            "resolution": "20 años medidos (~0.5° / ~50 km con downscaling) → Sensibilidad 2026–2027",
            "variables": "T2M, T2M_MIN, T2M_MAX, PRECTOTCORR, SOLAR, RH2M, GWETTOP, GWETROOT",
            "mode": power_mode,
            "plain": "20 años históricos de clima y humedad bajados a la altura de tu chacra (sensibilidad a 2 campañas, no sustituye CMIP6).",
        },
        {
            "sensor": ndvi_sensor,
            "resolution": ndvi_res,
            "variables": "Verdor mensual y meses de tierra pelada (NDVI < 0.25)",
            "mode": ndvi_mode,
            "plain": ndvi_plain,
        },
        {
            "sensor": sm_sensor,
            "resolution": sm_res,
            "variables": "Humedad superficial (m³/m³) y anomalía estacional",
            "mode": sm_mode,
            "plain": sm_plain,
        },
        {
            "sensor": et_sensor,
            "resolution": et_res,
            "variables": "Evapotranspiración de referencia / ET diaria (mm)",
            "mode": et_mode,
            "plain": et_plain,
        },
        {
            "sensor": storm_sensor,
            "resolution": storm_res,
            "variables": "Frecuencia de tormentas erosivas y lluvia máxima diaria",
            "mode": storm_mode,
            "plain": storm_plain,
        },
        {
            "sensor": dem_sensor,
            "resolution": dem_res,
            "variables": "Altitud (m s.n.m.) y pendiente (%)",
            "mode": dem_mode,
            "plain": dem_plain,
        },
        {
            "sensor": soil_sensor,
            "resolution": soil_res,
            "variables": "pH, arcilla/arena/limo, carbono orgánico y nitrógeno",
            "mode": soil_ds_mode,
            "plain": soil_plain,
        },
        *_market_dataset_rows(market_summary),
    ]


def _build_20yr_historical_and_projection(
    terrain: Dict[str, Any],
    raw_power: Dict[str, Any],
    precip_mm: np.ndarray,
    t2m_downscaled: np.ndarray,
    tmin_downscaled: np.ndarray,
    et0_mm: np.ndarray,
    smap_moisture: np.ndarray,
) -> Dict[str, Any]:
    """
    Downscales 20-year NASA POWER annual series (2006-2025) to parcel elevation/slope,
    fits linear decadal climate trends via regression, and projects 2 campaigns ahead (2026-2027).
    """
    yearly_raw = raw_power.get("yearly_raw")
    if not isinstance(yearly_raw, list) or len(yearly_raw) < 5:
        yearly_raw = _build_yearly_series_from_monthly(
            raw_power.get("t2m_c", [14.0] * 12),
            raw_power.get("t2m_min_c", [5.0] * 12),
            raw_power.get("precip_mm", [60.0] * 12),
            raw_power.get("gwettop"),
        )

    elev = float(terrain["elevation_m"])
    slope = float(terrain["slope_pct"])
    parcel_annual_precip = max(180.0, float(np.sum(precip_mm)))
    parcel_onset_precip = max(40.0, float(precip_mm[9] + precip_mm[10] + precip_mm[11]))
    parcel_mean_t2m = float(np.mean(t2m_downscaled))
    parcel_cold_tmin = float(np.mean(tmin_downscaled[4:8]))
    parcel_annual_et0 = max(600.0, float(np.sum(et0_mm)))
    parcel_mean_smap = float(np.mean(smap_moisture))

    raw_ann_mean = max(150.0, float(np.mean([float(y.get("precip_annual_mm", parcel_annual_precip)) for y in yearly_raw])))
    raw_onset_mean = max(30.0, float(np.mean([float(y.get("onset_rain_mm", parcel_onset_precip)) for y in yearly_raw])))
    raw_t2m_mean = float(np.mean([float(y.get("t2m_mean_c", parcel_mean_t2m)) for y in yearly_raw]))
    raw_cold_tmin_mean = float(np.mean([float(y.get("t2m_min_c", parcel_cold_tmin)) for y in yearly_raw]))
    raw_gwet_mean = max(0.15, float(np.mean([float(y.get("gwettop_mean", 0.52)) for y in yearly_raw])))

    precip_scale = parcel_annual_precip / raw_ann_mean
    onset_scale = parcel_onset_precip / raw_onset_mean
    temp_offset = parcel_mean_t2m - raw_t2m_mean
    tmin_offset = parcel_cold_tmin - raw_cold_tmin_mean
    storm_oro_scale = float(np.clip(precip_scale, 0.85, 1.8))

    historical_series: List[Dict[str, Any]] = []
    for row in yearly_raw:
        yr = int(row["year"])
        p_ann = round(max(180.0, float(row["precip_annual_mm"]) * precip_scale), 1)
        p_onset = round(max(30.0, float(row["onset_rain_mm"]) * onset_scale), 1)
        t_mean = round(float(row["t2m_mean_c"]) + temp_offset, 2)
        t_cold_min = round(float(row["t2m_min_c"]) + tmin_offset, 2)

        # Estimate parcel-level frost nights from altitude/inversion cold minimum & raw variability
        raw_frost = float(row.get("frost_days_raw", 4.0))
        cold_severity = max(0.0, 2.8 - t_cold_min)
        frost_parcel = round(float(np.clip(raw_frost * 0.45 + cold_severity * 13.5, 0.0, 115.0)), 1)

        storm_days = round(float(np.clip(float(row.get("storm_days_12mm", 8.0)) * storm_oro_scale, 1.0, 60.0)), 1)
        gwet_ratio = float(row.get("gwettop_mean", raw_gwet_mean)) / raw_gwet_mean
        sm_yr = round(float(np.clip(parcel_mean_smap * (0.55 + 0.45 * gwet_ratio), 0.10, 0.44)), 3)
        et0_yr = round(parcel_annual_et0 * (1.0 + 0.045 * (t_mean - parcel_mean_t2m)), 1)
        wb_yr = round(p_ann - et0_yr, 1)

        historical_series.append({
            "year": yr,
            "precip_mm": p_ann,
            "onset_rain_mm": p_onset,
            "temp_c": t_mean,
            "cold_tmin_c": t_cold_min,
            "et0_mm": et0_yr,
            "water_balance_mm": wb_yr,
            "frost_days": frost_parcel,
            "storm_days_12mm": storm_days,
            "soil_moisture": sm_yr,
        })

    years_arr = np.array([h["year"] for h in historical_series], dtype=float)
    temp_arr = np.array([h["temp_c"] for h in historical_series], dtype=float)
    precip_arr = np.array([h["precip_mm"] for h in historical_series], dtype=float)
    onset_arr = np.array([h["onset_rain_mm"] for h in historical_series], dtype=float)
    storm_arr = np.array([h["storm_days_12mm"] for h in historical_series], dtype=float)
    frost_arr = np.array([h["frost_days"] for h in historical_series], dtype=float)

    slope_t = float(np.polyfit(years_arr, temp_arr, 1)[0])
    slope_p = float(np.polyfit(years_arr, precip_arr, 1)[0])
    slope_onset = float(np.polyfit(years_arr, onset_arr, 1)[0])
    slope_storm = float(np.polyfit(years_arr, storm_arr, 1)[0])
    slope_frost = float(np.polyfit(years_arr, frost_arr, 1)[0])

    temp_trend_c_per_decade = round(float(np.clip(slope_t * 10.0, 0.16, 0.52)), 2)
    mean_onset = max(40.0, float(np.mean(onset_arr)))
    mean_precip = max(220.0, float(np.mean(precip_arr)))
    precip_trend_pct_per_decade = round(
        float(np.clip((0.6 * (slope_onset / mean_onset) + 0.4 * (slope_p / mean_precip)) * 1000.0, -11.5, 7.5)),
        1,
    )
    storm_trend_pct_per_decade = round(
        float(np.clip((slope_storm * 10.0 / max(1.0, float(np.mean(storm_arr)))) * 100.0, -6.0, 22.0)),
        1,
    )
    frost_days_trend_per_decade = round(float(np.clip(slope_frost * 10.0, -5.5, 7.5)), 1)

    recent_slice = historical_series[-5:]
    base_temp_recent = float(np.mean([r["temp_c"] for r in recent_slice]))
    base_precip_recent = float(np.mean([r["precip_mm"] for r in recent_slice]))
    base_onset_recent = float(np.mean([r["onset_rain_mm"] for r in recent_slice]))
    base_frost_recent = float(np.mean([r["frost_days"] for r in recent_slice]))
    base_storm_recent = float(np.mean([r["storm_days_12mm"] for r in recent_slice]))
    hist_precip_std = float(np.std(precip_arr))

    projected_series: List[Dict[str, Any]] = []
    for yr in range(2026, 2028):
        years_ahead = yr - 2025
        decades_ahead = years_ahead / 10.0
        temp_proj = round(base_temp_recent + temp_trend_c_per_decade * decades_ahead, 2)
        precip_proj = round(
            max(200.0, base_precip_recent * (1.0 + (precip_trend_pct_per_decade / 100.0) * decades_ahead)),
            1,
        )
        onset_proj = round(
            max(35.0, base_onset_recent * (1.0 + (precip_trend_pct_per_decade / 100.0) * decades_ahead)),
            1,
        )
        unc_half = max(35.0, hist_precip_std * (0.75 + 0.15 * years_ahead))
        band_low = round(max(140.0, precip_proj - unc_half), 1)
        band_high = round(precip_proj + unc_half, 1)

        et0_proj = round(parcel_annual_et0 * (1.0 + 0.045 * (temp_proj - parcel_mean_t2m)), 1)
        wb_proj = round(precip_proj - et0_proj, 1)

        # Clear-sky radiative frost persists at high altitude / dry winters even as mean T warms
        frost_factor = 0.7 if elev >= 3150 else 0.9
        frost_proj = round(
            float(np.clip(base_frost_recent + frost_days_trend_per_decade * decades_ahead * frost_factor, 0.0, 120.0)),
            1,
        )
        storm_proj = round(
            float(np.clip(base_storm_recent * (1.0 + (storm_trend_pct_per_decade / 100.0) * decades_ahead), 1.0, 75.0)),
            1,
        )
        drought_risk_score = round(
            float(np.clip(50.0 + (-wb_proj / 320.0) * 32.0 + (temp_proj - parcel_mean_t2m) * 14.0 + (slope > 14.0) * 6.0, 8.0, 98.0)),
            1,
        )

        projected_series.append({
            "year": yr,
            "precip_mm": precip_proj,
            "precip_band_low_mm": band_low,
            "precip_band_high_mm": band_high,
            "onset_rain_mm": onset_proj,
            "temp_c": temp_proj,
            "et0_mm": et0_proj,
            "water_balance_mm": wb_proj,
            "frost_days": frost_proj,
            "storm_days_12mm": storm_proj,
            "drought_risk_score": drought_risk_score,
        })

    timeline_22yr: List[Dict[str, Any]] = []
    last_hist_year = historical_series[-1]["year"]
    for h in historical_series:
        is_bridge = h["year"] == last_hist_year
        timeline_22yr.append({
            "year": h["year"],
            "period_type": "historical",
            "precip_hist_mm": h["precip_mm"],
            "precip_proj_mm": h["precip_mm"] if is_bridge else None,
            "precip_band_low_mm": h["precip_mm"] if is_bridge else None,
            "precip_band_high_mm": h["precip_mm"] if is_bridge else None,
            "temp_hist_c": h["temp_c"],
            "temp_proj_c": h["temp_c"] if is_bridge else None,
            "water_balance_mm": h["water_balance_mm"],
            "frost_days": h["frost_days"],
            "storm_days_12mm": h["storm_days_12mm"],
        })
    for p in projected_series:
        timeline_22yr.append({
            "year": p["year"],
            "period_type": "projected",
            "precip_hist_mm": None,
            "precip_proj_mm": p["precip_mm"],
            "precip_band_low_mm": p["precip_band_low_mm"],
            "precip_band_high_mm": p["precip_band_high_mm"],
            "temp_hist_c": None,
            "temp_proj_c": p["temp_c"],
            "water_balance_mm": p["water_balance_mm"],
            "frost_days": p["frost_days"],
            "storm_days_12mm": p["storm_days_12mm"],
        })

    proj_2026 = projected_series[0]
    proj_2027 = projected_series[-1]
    return {
        "historical_years_count": len(historical_series),
        "historical_range": f"{historical_series[0]['year']}–{historical_series[-1]['year']}",
        "projection_years_count": len(projected_series),
        "projection_range": "2026–2027",
        "projection_method": "linear_regression_20yr_sensitivity",
        "method_disclaimer": (
            "Sensibilidad de corto plazo (2026–2027) por tendencia lineal de NASA POWER (2006–2025) "
            "ajustada por topografía. No sustituye ensambles climáticos CMIP6 / NASA NEX-GDDP-CMIP6 "
            "para proyecciones multidecadales (2035–2045)."
        ),
        "data_origin": raw_power.get("source", "calibrated_cajamarca_fallback"),
        "trends": {
            "temp_trend_c_per_decade": temp_trend_c_per_decade,
            "temp_delta_20yr_c": round(temp_trend_c_per_decade * 2.0, 2),
            "precip_trend_pct_per_decade": precip_trend_pct_per_decade,
            "precip_delta_20yr_pct": round(precip_trend_pct_per_decade * 2.0, 1),
            "storm_trend_pct_per_decade": storm_trend_pct_per_decade,
            "frost_days_trend_per_decade": frost_days_trend_per_decade,
        },
        "milestones": {
            "baseline_2025": {
                "temp_c": round(float(np.mean(temp_arr)), 1),
                "precip_mm": round(float(np.mean(precip_arr)), 0),
                "et0_mm": round(parcel_annual_et0, 0),
                "frost_days": round(float(np.mean(frost_arr)), 0),
            },
            "year_2026": {
                "temp_c": round(proj_2026["temp_c"], 1),
                "precip_mm": round(proj_2026["precip_mm"], 0),
                "et0_mm": round(proj_2026["et0_mm"], 0),
                "water_balance_mm": round(proj_2026["water_balance_mm"], 0),
                "frost_days": round(proj_2026["frost_days"], 0),
                "drought_risk_score": proj_2026["drought_risk_score"],
            },
            "year_2027": {
                "temp_c": round(proj_2027["temp_c"], 1),
                "precip_mm": round(proj_2027["precip_mm"], 0),
                "et0_mm": round(proj_2027["et0_mm"], 0),
                "water_balance_mm": round(proj_2027["water_balance_mm"], 0),
                "frost_days": round(proj_2027["frost_days"], 0),
                "drought_risk_score": proj_2027["drought_risk_score"],
            },
        },
        "historical_series": historical_series,
        "projected_series": projected_series,
        "timeline_22yr": timeline_22yr,
    }


def build_harmonized_biophysical_series(
    terrain: Dict[str, Any],
    raw_power: Dict[str, Any],
    current_crop: str = "papa_maiz",
    water_availability: str = "secano",
    farmer_soil: Optional[Dict[str, Any]] = None,
    era5_data: Optional[Dict[str, Any]] = None,
    sentinel2_data: Optional[Dict[str, Any]] = None,
    earthdata: Optional[Dict[str, Any]] = None,
    live_weather: Optional[Dict[str, Any]] = None,
    market_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Downscales NASA POWER observations to Cajamarca parcel scale using real DEM elevation/slope,
    and fuses Sentinel-2 L2A NDVI (if configured), ERA5-Land / SMAP soil moisture,
    NASA POWER daily heavy-rain frequencies, ECOSTRESS/FAO ET0, and farmer-reported soil notes.
    """
    farmer_soil = farmer_soil or {}
    elev = float(terrain["elevation_m"])
    slope = float(terrain["slope_pct"])
    lon = float(terrain["lon"])
    lat = float(terrain["lat"])

    zones_data = load_zones_data()
    beacons = zones_data["beacon_parcels"]
    weights = []
    min_beacon_dist_km = 1e9
    for b in beacons:
        d = max(0.05, math.hypot((lat - b["lat"]) * 111.0, (lon - b["lon"]) * 110.0))
        min_beacon_dist_km = min(min_beacon_dist_km, d)
        weights.append(1.0 / (d ** 2))
    w = np.array(weights, dtype=float)
    w /= np.sum(w)

    cal_precip = w @ np.array([b["calibrated_monthly"]["precip_mm"] for b in beacons], dtype=float)
    cal_tmin = w @ np.array([b["calibrated_monthly"]["t2m_min_c"] for b in beacons], dtype=float)
    cal_t2m = w @ np.array([b["calibrated_monthly"]["t2m_c"] for b in beacons], dtype=float)

    raw_t2m = np.array(raw_power["t2m_c"], dtype=float)
    raw_tmin = np.array(raw_power["t2m_min_c"], dtype=float)
    raw_precip = np.array(raw_power["precip_mm"], dtype=float)
    raw_solar = np.array(raw_power["solar_mj_m2_day"], dtype=float)
    raw_rh = np.array(raw_power["rh2m_pct"], dtype=float)

    grid_elev = float(raw_power.get("power_grid_elevation_m", 2850.0))

    if raw_power["source"] == "live_nasa_power":
        # Downscale real NASA POWER via moist adiabatic lapse rate (-0.0065 C/m from MERRA-2 grid elev to DEM elev).
        # Local Cajamarca beacon refinement applies ONLY within 8 km of validation plots; beyond 8 km it is 100% pure NASA POWER + DEM.
        cal_alpha = 0.22 * max(0.0, 1.0 - min_beacon_dist_km / 8.0)
        lapse_shift = float(np.clip(-0.0065 * (elev - grid_elev), -9.5, 9.5))
        t2m_nasa = raw_t2m + lapse_shift
        t2m_downscaled = np.clip((1.0 - cal_alpha) * t2m_nasa + cal_alpha * cal_t2m, -5.0, 35.0)

        valley_inversion = np.array([0.0, 0.0, 0.0, -0.3, -0.8, -1.4, -1.7, -1.4, -0.6, -0.2, 0.0, 0.0])
        if slope < 5.5 and elev >= 2000 and elev < 2850:
            tmin_nasa = raw_tmin + lapse_shift + valley_inversion
        else:
            tmin_nasa = raw_tmin + lapse_shift
        tmin_downscaled = np.clip((1.0 - cal_alpha) * tmin_nasa + cal_alpha * cal_tmin, -12.0, 27.0)

        elev_oro_boost = 1.0 + float(np.clip((elev - grid_elev) / 4800.0, -0.10, 0.16))
        precip_nasa = np.maximum(0.5, raw_precip * elev_oro_boost)
        precip_mm = np.clip((1.0 - cal_alpha) * precip_nasa + cal_alpha * cal_precip, 0.5, 520.0)

        solar_mj = np.clip(raw_solar * (1.0 + (elev - grid_elev) * 0.000035), 10.0, 28.0)
        rh2m = np.clip(raw_rh + (elev - grid_elev) * 0.004, 30.0, 96.0)
    else:
        t2m_downscaled = cal_t2m + (-0.0062 * (elev - float(np.dot(w, [b["elevation_m"] for b in beacons]))))
        tmin_downscaled = cal_tmin + (-0.0062 * (elev - float(np.dot(w, [b["elevation_m"] for b in beacons]))))
        precip_mm = cal_precip
        solar_mj = raw_solar
        rh2m = raw_rh

    if farmer_soil.get("local_frost_early"):
        early_drop = np.array([0.0, 0.0, 0.0, -0.5, -1.4, -1.2, -0.6, -0.3, -0.2, 0.0, 0.0, 0.0])
        tmin_downscaled = tmin_downscaled + early_drop

    # ET0 fusion: ECOSTRESS -> ERA5-Land FAO ET0 -> NASA POWER radiation/VPD Makkink proxy
    es = 0.6108 * np.exp((17.27 * t2m_downscaled) / (t2m_downscaled + 237.3))
    ea = es * (rh2m / 100.0)
    vpd = np.maximum(0.15, es - ea)
    delta_vp = (4098.0 * es) / ((t2m_downscaled + 237.3) ** 2)
    gamma = 0.0665 * math.exp(-elev / 8400.0)
    et0_makkink = np.clip((0.63 * (delta_vp / (delta_vp + gamma)) * (solar_mj / 2.45) + 0.42 * vpd) * DAYS_IN_MONTH, 65.0, 165.0)

    if earthdata and earthdata.get("ecostress_et_daily"):
        eco_monthly = np.array(earthdata["ecostress_et_daily"], dtype=float) * DAYS_IN_MONTH
        et0_mm = np.clip(0.65 * eco_monthly + 0.35 * et0_makkink, 60.0, 170.0)
    elif era5_data and isinstance(era5_data.get("et0_fao_mm"), list) and len(era5_data["et0_fao_mm"]) == 12:
        era_et = np.array(era5_data["et0_fao_mm"], dtype=float)
        et0_mm = np.clip(0.60 * era_et + 0.40 * et0_makkink, 60.0, 165.0)
    else:
        et0_mm = et0_makkink

    # NDVI fusion: Real Sentinel-2 10 m via CDSE if configured, else crop-conditioned estimate
    if sentinel2_data and isinstance(sentinel2_data.get("ndvi"), list) and len(sentinel2_data["ndvi"]) == 12:
        ndvi_mean = np.clip(np.array(sentinel2_data["ndvi"], dtype=float), 0.12, 0.88)
        ndvi_5yr_min = np.clip(ndvi_mean - 0.07, 0.10, 0.82)
        ndvi_5yr_max = np.clip(ndvi_mean + 0.08, 0.15, 0.92)
    else:
        crop_ndvi_base = {
            "sin_cultivo": np.array([0.24, 0.27, 0.26, 0.23, 0.19, 0.17, 0.16, 0.16, 0.18, 0.21, 0.23, 0.25]),
            "monocultivo_papa": np.array([0.68, 0.75, 0.64, 0.34, 0.20, 0.17, 0.15, 0.16, 0.21, 0.31, 0.48, 0.62]),
            "papa_maiz": np.array([0.70, 0.77, 0.72, 0.49, 0.24, 0.19, 0.17, 0.18, 0.22, 0.33, 0.50, 0.63]),
            "pastos_degradados": np.array([0.46, 0.50, 0.48, 0.41, 0.31, 0.24, 0.21, 0.20, 0.23, 0.30, 0.38, 0.43]),
            "cebada_trigo_continuo": np.array([0.63, 0.71, 0.69, 0.46, 0.23, 0.18, 0.16, 0.17, 0.21, 0.29, 0.44, 0.56]),
        }
        base_ndvi = crop_ndvi_base.get(current_crop, crop_ndvi_base["sin_cultivo"]).copy()
        rain_factor = np.clip(precip_mm / np.maximum(1.0, et0_mm), 0.15, 1.35)
        irrig_boost_map = {
            "secano": 0.0,
            "cosecha_agua_qocha": 0.035,
            "riego_deficitario": 0.045,
            "riego_gravedad": 0.06,
            "riego_melgas_surcos": 0.075,
            "riego_aspersion": 0.09,
            "riego_goteo": 0.11,
        }
        irrig_boost = 0.0 if current_crop == "sin_cultivo" else irrig_boost_map.get(water_availability, 0.0)
        dry_mask = np.array([0.0, 0.0, 0.0, 0.2, 0.5, 0.7, 0.8, 0.8, 0.6, 0.3, 0.1, 0.0])
        ndvi_mean = base_ndvi + (rain_factor - 0.65) * 0.05 + irrig_boost * (0.4 + 0.6 * dry_mask)
        if current_crop in ("monocultivo_papa", "papa_maiz", "cebada_trigo_continuo"):
            ndvi_mean[5:8] = np.minimum(ndvi_mean[5:8], 0.235)
        ndvi_mean = np.clip(ndvi_mean, 0.13, 0.84)
        ndvi_5yr_min = np.clip(ndvi_mean - np.array([0.06, 0.06, 0.07, 0.07, 0.05, 0.04, 0.03, 0.03, 0.05, 0.06, 0.07, 0.06]), 0.10, 0.80)
        ndvi_5yr_max = np.clip(ndvi_mean + np.array([0.07, 0.07, 0.08, 0.08, 0.06, 0.05, 0.05, 0.05, 0.06, 0.08, 0.08, 0.07]), 0.16, 0.90)

    # Soil Moisture fusion: SMAP AppEEARS -> ERA5-Land 0-7 cm + POWER GWETTOP -> local water_ratio proxy
    infiltration_factor = np.clip(1.0 - (slope - 4.0) * 0.011, 0.72, 1.05)
    tex_ovr = str(farmer_soil.get("texture_override", "auto"))
    cond_ovr = str(farmer_soil.get("compaction_or_drainage", "normal"))
    if tex_ovr in ("franco_arenoso", "pedregoso"):
        infiltration_factor *= 0.90
    elif tex_ovr == "arcilloso_pesado":
        infiltration_factor *= 1.08
    if cond_ovr == "duro_compactado":
        infiltration_factor *= 0.88
    elif cond_ovr == "se_encharca":
        infiltration_factor *= 1.12

    if earthdata and earthdata.get("smap_monthly"):
        base_sm = np.array(earthdata["smap_monthly"], dtype=float)
        # Preserve slope and farmer soil adjustment linearly around neutral 1.0
        farmer_adj = infiltration_factor / np.clip(1.0 - (slope - 4.0) * 0.011, 0.72, 1.05)
        smap_moisture = np.clip(base_sm * farmer_adj, 0.09, 0.44)
    elif era5_data and isinstance(era5_data.get("soil_moisture_0_to_7cm"), list) and len(era5_data["soil_moisture_0_to_7cm"]) == 12:
        era_sm = np.array(era5_data["soil_moisture_0_to_7cm"], dtype=float)
        if raw_power.get("gwetroot"):
            gwet_top = np.array(raw_power.get("gwettop", raw_power["gwetroot"]), dtype=float) * 0.42
            gwet_root = np.array(raw_power["gwetroot"], dtype=float) * 0.42
            base_sm = 0.60 * era_sm + 0.25 * gwet_top + 0.15 * gwet_root
        elif raw_power.get("gwettop"):
            # GWETTOP is relative saturation [0..1]; ~0.42 m3/m3 effective field porosity in Andes
            gwet_vol = np.array(raw_power["gwettop"], dtype=float) * 0.42
            base_sm = 0.70 * era_sm + 0.30 * gwet_vol
        else:
            base_sm = era_sm
        smap_moisture = np.clip(base_sm * infiltration_factor, 0.10, 0.42)
    elif raw_power.get("gwettop"):
        gwet_top = np.array(raw_power["gwettop"], dtype=float) * 0.42
        gwet_root = np.array(raw_power.get("gwetroot", raw_power["gwettop"]), dtype=float) * 0.42
        base_sm = 0.65 * gwet_top + 0.35 * gwet_root
        smap_moisture = np.clip(base_sm * infiltration_factor, 0.10, 0.42)
    else:
        water_ratio = precip_mm / np.maximum(1.0, et0_mm)
        smap_moisture = np.clip((0.12 + 0.18 * np.minimum(1.2, water_ratio)) * infiltration_factor, 0.10, 0.40)

    water_moisture_boost = {
        "secano": 0.0,
        "cosecha_agua_qocha": 0.025,
        "riego_deficitario": 0.035,
        "riego_gravedad": 0.048,
        "riego_melgas_surcos": 0.058,
        "riego_aspersion": 0.070,
        "riego_goteo": 0.085,
    }.get(str(water_availability or "secano"), 0.030)
    if water_moisture_boost > 0.0:
        dry_season_weights = np.array([0.5, 0.5, 0.5, 0.7, 1.0, 1.0, 1.0, 1.0, 1.0, 0.8, 0.5, 0.5])
        smap_moisture = smap_moisture + water_moisture_boost * dry_season_weights

    if tex_ovr == "arcilloso_pesado":
        smap_moisture = smap_moisture + 0.020
    elif tex_ovr in ("franco_arenoso", "pedregoso"):
        smap_moisture = smap_moisture - 0.022
    if cond_ovr == "duro_compactado":
        smap_moisture = smap_moisture - 0.018
    elif cond_ovr == "se_encharca":
        smap_moisture = smap_moisture + 0.032
    smap_moisture = np.clip(smap_moisture, 0.09, 0.48)
    smap_mean_yr = float(np.mean(smap_moisture))
    smap_std_yr = max(0.03, float(np.std(smap_moisture)))
    smap_anomaly_z = (smap_moisture - smap_mean_yr) / smap_std_yr

    # Intense storm frequency: real NASA POWER daily heavy-rain days (>=12 mm) scaled orographically to target elev
    if raw_power.get("has_daily_metrics") and raw_power.get("storm_days_12mm"):
        raw_annual = max(120.0, float(np.sum(raw_precip)))
        target_annual = float(np.sum(precip_mm))
        oro_scale = float(np.clip(target_annual / raw_annual, 0.85, 1.8))
        gpm_erosive_events = np.round(np.clip(np.array(raw_power["storm_days_12mm"], dtype=float) * oro_scale, 0.0, 8.0), 1)
        gpm_max_daily_mm = np.round(np.clip(np.array(raw_power["max_daily_precip_mm"], dtype=float) * math.sqrt(oro_scale), 3.0, 62.0), 1)
    else:
        gpm_erosive_events = np.round(np.clip((precip_mm / 34.0) * (1.0 + (elev - 2700.0) * 0.00025), 0.0, 6.0), 1)
        gpm_max_daily_mm = np.round(np.clip(precip_mm * 0.28 + 4.0, 4.0, 52.0), 1)

    bare_soil_flags = ndvi_mean < 0.25
    cover_exposure = np.clip((0.55 - ndvi_mean) / 0.42, 0.08, 1.0)
    slope_factor = np.clip(slope / 15.0, 0.25, 1.85)
    rain_erosivity = np.clip((precip_mm / 100.0) + (gpm_erosive_events / 5.0) * 0.55, 0.12, 1.65)
    monthly_erosion_risk = np.clip(cover_exposure * slope_factor * rain_erosivity * 58.0, 5.0, 98.0)

    df = pd.DataFrame({
        "month_idx": np.arange(1, 13),
        "month": MONTH_LABELS_ES,
        "t2m_c": np.round(t2m_downscaled, 1),
        "t2m_min_c": np.round(tmin_downscaled, 1),
        "precip_mm": np.round(precip_mm, 1),
        "et0_mm": np.round(et0_mm, 1),
        "water_balance_mm": np.round(precip_mm - et0_mm, 1),
        "solar_mj_m2_day": np.round(solar_mj, 1),
        "rh2m_pct": np.round(rh2m, 1),
        "ndvi": np.round(ndvi_mean, 3),
        "ndvi_5yr_min": np.round(ndvi_5yr_min, 3),
        "ndvi_5yr_max": np.round(ndvi_5yr_max, 3),
        "is_bare_soil": bare_soil_flags,
        "smap_moisture": np.round(smap_moisture, 3),
        "smap_anomaly": np.round(smap_anomaly_z, 2),
        "gpm_erosive_events": gpm_erosive_events,
        "gpm_max_daily_mm": gpm_max_daily_mm,
        "erosion_risk": np.round(monthly_erosion_risk, 1),
        "frost_risk": tmin_downscaled <= 2.2,
    })

    df["critical_erosion_window"] = (
        df["is_bare_soil"]
        | ((df["ndvi"] < 0.36) & (df["precip_mm"] >= 60.0) & (slope >= 8.0))
    )

    bare_months = df.loc[df["is_bare_soil"], "month"].tolist()
    critical_window_months = df.loc[df["critical_erosion_window"], "month"].tolist()
    frost_months = df.loc[df["frost_risk"], "month"].tolist()
    severe_dry_months = df.loc[df["smap_anomaly"] <= -0.75, "month"].tolist()
    erosive_storm_months = df.loc[df["gpm_erosive_events"] >= 2.5, "month"].tolist()

    annual_precip_mm = round(float(df["precip_mm"].sum()), 1)
    annual_et0_mm = round(float(df["et0_mm"].sum()), 1)
    min_temp_c = round(float(df["t2m_min_c"].min()), 1)
    min_temp_month = str(df.loc[df["t2m_min_c"].idxmin(), "month"])
    mean_temp_c = round(float(df["t2m_c"].mean()), 1)

    monthly_records = [
        {k: (v.item() if hasattr(v, "item") else v) for k, v in row.items()}
        for row in df.to_dict(orient="records")
    ]

    climate_20yr = _build_20yr_historical_and_projection(
        terrain=terrain,
        raw_power=raw_power,
        precip_mm=precip_mm,
        t2m_downscaled=t2m_downscaled,
        tmin_downscaled=tmin_downscaled,
        et0_mm=et0_mm,
        smap_moisture=smap_moisture,
    )

    parcel_elev = float(terrain.get("elevation_m", 2700.0) or 2700.0)
    cur_month_idx = max(0, min(11, datetime.now(timezone.utc).month - 1))
    fallback_temp = round(float(df["t2m_c"].iloc[cur_month_idx]), 1)
    fallback_min_temp = round(float(df["t2m_min_c"].iloc[cur_month_idx]), 1)
    fallback_max_temp = round(fallback_temp + max(4.2, (fallback_temp - fallback_min_temp) * 0.72), 1)
    fallback_precip = round(float(precip_mm[cur_month_idx]) / 30.0, 1)

    lapse_adj = 0.0
    if live_weather and isinstance(live_weather.get("temp_c"), (int, float)):
        grid_elev = float(live_weather.get("grid_elevation_m", parcel_elev) or parcel_elev)
        lapse_adj = float(np.clip(-0.0065 * (parcel_elev - grid_elev), -6.5, 6.5))
        current_temp_c = round(float(live_weather["temp_c"]) + lapse_adj, 1)
        current_max_temp_c = round(float(live_weather.get("max_temp_c", current_temp_c + 4.0)) + lapse_adj, 1)
        current_min_temp_c = round(float(live_weather.get("min_temp_c", fallback_min_temp)) + lapse_adj, 1)
        current_rh_pct = round(float(live_weather.get("rh_pct", 65.0)), 0)
        current_precip_mm = round(float(live_weather.get("precip_mm", 0.0)), 2)
        current_weather_code = int(live_weather.get("weather_code", 1))
        cloud_pct = float(live_weather.get("cloud_cover_pct", 45.0))
        current_weather_type, current_weather_label = _classify_wmo_weather(
            current_weather_code, current_temp_c, current_precip_mm, cloud_pct
        )
        current_weather_source = str(live_weather.get("source", "Open-Meteo Tiempo Real"))
    else:
        current_temp_c = fallback_temp
        current_max_temp_c = fallback_max_temp
        current_min_temp_c = fallback_min_temp
        current_rh_pct = 68.0
        current_precip_mm = fallback_precip
        current_weather_code = (
            71
            if current_min_temp_c <= 2.5
            else (61 if float(precip_mm[cur_month_idx]) >= 85.0 else (3 if float(precip_mm[cur_month_idx]) >= 45.0 else 1))
        )
        current_weather_type, current_weather_label = _classify_wmo_weather(
            current_weather_code,
            current_temp_c,
            1.0 if float(precip_mm[cur_month_idx]) >= 110.0 else 0.0,
            55.0 if float(precip_mm[cur_month_idx]) >= 45.0 else 25.0,
        )
        current_weather_source = "Climatología NASA POWER (mes actual)"

    forecast_7d: List[Dict[str, Any]] = []
    if live_weather and isinstance(live_weather.get("daily_forecast_7d"), list):
        for day in live_weather["daily_forecast_7d"][:7]:
            if not isinstance(day, dict) or not day.get("date"):
                continue
            d_tmax = round(float(day.get("temp_max_c", current_max_temp_c)) + lapse_adj, 1)
            d_tmin = round(float(day.get("temp_min_c", current_min_temp_c)) + lapse_adj, 1)
            d_prec = round(float(day.get("precip_mm", 0.0) or 0.0), 1)
            d_code = int(day.get("weather_code", current_weather_code) or current_weather_code)
            d_type, d_label = _classify_wmo_weather(d_code, d_tmin, d_prec, 60.0 if d_prec >= 2.0 else 30.0)
            forecast_7d.append({
                "date": str(day["date"]),
                "temp_max_c": d_tmax,
                "temp_min_c": d_tmin,
                "precip_mm": d_prec,
                "weather_code": d_code,
                "weather_type": d_type,
                "weather_label": d_label,
            })

    next_7d_precip_mm = round(sum(d["precip_mm"] for d in forecast_7d), 1) if forecast_7d else None
    next_7d_min_temp_c = round(min(d["temp_min_c"] for d in forecast_7d), 1) if forecast_7d else None
    frost_alert_7d = bool(next_7d_min_temp_c is not None and next_7d_min_temp_c <= 3.0)
    latest_ndvi_val = (
        round(float(sentinel2_data["latest_ndvi"]), 3)
        if sentinel2_data and sentinel2_data.get("latest_ndvi") is not None
        else round(float(df["ndvi"].iloc[cur_month_idx]), 3)
    )
    latest_ndvi_date = (
        str(sentinel2_data["latest_observation_date"])
        if sentinel2_data and sentinel2_data.get("latest_observation_date")
        else None
    )

    return {
        "monthly_series": monthly_records,
        "summary": {
            "annual_precip_mm": annual_precip_mm,
            "annual_et0_mm": annual_et0_mm,
            "annual_water_balance_mm": round(annual_precip_mm - annual_et0_mm, 1),
            "mean_temp_c": mean_temp_c,
            "min_temp_c": min_temp_c,
            "min_temp_month": min_temp_month,
            "current_temp_c": current_temp_c,
            "current_max_temp_c": current_max_temp_c,
            "current_min_temp_c": current_min_temp_c,
            "current_rh_pct": current_rh_pct,
            "current_precip_mm": current_precip_mm,
            "current_weather_code": current_weather_code,
            "current_weather_type": current_weather_type,
            "current_weather_label": current_weather_label,
            "current_weather_source": current_weather_source,
            "bare_soil_months": bare_months,
            "bare_soil_month_count": len(bare_months),
            "critical_erosion_months": critical_window_months,
            "frost_risk_months": frost_months,
            "frost_month_count": len(frost_months),
            "dry_anomaly_months": severe_dry_months,
            "erosive_storm_months": erosive_storm_months,
            "mean_erosion_risk": round(float(df["erosion_risk"].mean()), 1),
            "peak_erosion_risk": round(float(df["erosion_risk"].max()), 1),
            "mean_smap_moisture": round(float(df["smap_moisture"].mean()), 3),
            "latest_ndvi": latest_ndvi_val,
            "latest_ndvi_date": latest_ndvi_date,
            "next_7d_precip_mm": next_7d_precip_mm,
            "next_7d_min_temp_c": next_7d_min_temp_c,
            "frost_alert_7d": frost_alert_7d,
        },
        "forecast_7d": forecast_7d,
        "climate_20yr": climate_20yr,
        "provenance": {
            "nasa_power_source": raw_power["source"],
            "nasa_power_label": raw_power["source_label"],
            "nasa_power_cache_hit": bool(raw_power.get("cache_hit", False)),
            "nasa_power_grid_elev_m": raw_power.get("power_grid_elevation_m"),
            "fetched_at": raw_power["fetched_at"],
            "economic_reference_label": (
                market_summary.get("economic_reference_label")
                if market_summary and market_summary.get("economic_reference_label")
                else "Tablas referenciales MIDAGRI / INIA Cajamarca por campaña (sin cotización diaria en vivo disponible)."
            ),
            "market_summary": market_summary,
            "erosion_method_label": "Índice físico derivado (pendiente SRTM, agresividad pluvial diaria NASA POWER y cobertura NDVI).",
            "spatial_scale_hierarchy": [
                {
                    "tier": "poligono_parcela",
                    "resolution": "10–30 m",
                    "sensors": "Sentinel-2 L2A (10 m) · SRTM GL1 (30 m)",
                    "scope": "Muestrea geometría, vértices, orientación (aspecto) y desnivel real dentro del polígono de tu chacra.",
                },
                {
                    "tier": "perimetro_suelo",
                    "resolution": "250 m",
                    "sensors": "SoilGrids ISRIC v2.0 + campo",
                    "scope": "Propiedades edáficas 0–30 cm en la celda o anillo agrícola cercano, calibradas con tus notas en campo.",
                },
                {
                    "tier": "atmosferico_regional",
                    "resolution": "~9–50 km + downscaling",
                    "sensors": "ERA5-Land (~9 km) · NASA POWER (~0.5°)",
                    "scope": "Forzamiento climático regional de 20 años ajustado a la altitud (-6.5 °C/km), lluvia orográfica y ladera de la parcela.",
                },
            ],
            "harmonized_datasets": _build_dataset_provenance(
                raw_power=raw_power,
                terrain=terrain,
                era5_data=era5_data,
                sentinel2_data=sentinel2_data,
                earthdata=earthdata,
                market_summary=market_summary,
            ),
        },
    }

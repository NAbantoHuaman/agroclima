"""Terrain geometry, DEM/SoilGrids/ERA5-Land soil moisture, and Earthdata AppEEARS clients."""

from __future__ import annotations

import asyncio
import json
import math
from typing import Any, Dict, List, Optional, Tuple

import httpx
import numpy as np
import pandas as pd

from config import EARTHDATA_CAJAMARCA_CACHE
from domain.catalog import _CAJAMARCA_DEM_ANCHORS, _SOIL_OVERRIDE_LABELS, load_zones_data
from infrastructure.cache import _ERA5_CACHE, _SOILGRIDS_CACHE

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
SOILGRIDS_API_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"


def compute_polygon_metrics(polygon: Optional[List[List[float]]]) -> Optional[Dict[str, Any]]:
    """Computes centroid (lat, lon) and area (ha) from a list of [lat, lon] vertices."""
    if not polygon or len(polygon) < 3:
        return None
    pts = np.array(polygon, dtype=float)
    lats = pts[:, 0]
    lons = pts[:, 1]
    c_lat = float(np.mean(lats))
    c_lon = float(np.mean(lons))

    m_per_deg_lat = 110574.0
    m_per_deg_lon = 111320.0 * math.cos(math.radians(c_lat))
    x = (lons - c_lon) * m_per_deg_lon
    y = (lats - c_lat) * m_per_deg_lat

    area_m2 = 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))
    area_ha = max(0.25, round(area_m2 / 10000.0, 2))
    span_m = max(30.0, float(np.hypot(np.ptp(x), np.ptp(y))))
    return {
        "centroid_lat": round(c_lat, 5),
        "centroid_lon": round(c_lon, 5),
        "area_ha": area_ha,
        "span_m": span_m,
        "vertex_count": len(polygon),
    }


def _idw_terrain(lat: float, lon: float) -> Tuple[float, float, str, str]:
    weights = []
    for a_lat, a_lon, _, _, _, _, _ in _CAJAMARCA_DEM_ANCHORS:
        dist = math.hypot((lat - a_lat) * 111.0, (lon - a_lon) * 110.0)
        if dist < 0.35:
            idx = [i for i, a in enumerate(_CAJAMARCA_DEM_ANCHORS) if a[0] == a_lat and a[1] == a_lon][0]
            _, _, elev, slope, zlabel, soil, _ = _CAJAMARCA_DEM_ANCHORS[idx]
            return elev, slope, zlabel, soil
        weights.append(1.0 / (dist ** 2))

    w_arr = np.array(weights, dtype=float)
    w_norm = w_arr / np.sum(w_arr)
    elevs = np.array([a[2] for a in _CAJAMARCA_DEM_ANCHORS])
    slopes = np.array([a[3] for a in _CAJAMARCA_DEM_ANCHORS])

    elev = float(np.dot(w_norm, elevs))
    slope = float(np.dot(w_norm, slopes))

    closest_idx = int(np.argmax(w_arr))
    closest = _CAJAMARCA_DEM_ANCHORS[closest_idx]
    district_hint = closest[6]
    if elev < 1000:
        zlabel = f"Yunga Fluvial / Valle Cálido ({district_hint})"
    elif elev < 2100:
        zlabel = f"Selva Alta / Yunga Cafetalera ({district_hint})"
    elif elev < 2760:
        zlabel = f"Piso de Valle ({district_hint})"
    elif elev < 3180:
        zlabel = f"Ladera Media ({district_hint})"
    else:
        zlabel = f"Ladera Alta / Jalca ({district_hint})"

    return round(elev, 0), round(slope, 1), zlabel, closest[5]


def detect_cajamarca_agro_zone(lat: float, lon: float, elev: float) -> Dict[str, Any]:
    """Detecta distrito de referencia y piso ecológico Pulgar Vidal con cultivos reales MIDAGRI/INIA."""
    best_dist = 1e9
    nearest_district = "Cajamarca"
    for a_lat, a_lon, _, _, _, _, dist_name in _CAJAMARCA_DEM_ANCHORS:
        d_km = math.hypot((lat - a_lat) * 111.0, (lon - a_lon) * 110.0)
        if d_km < best_dist:
            best_dist = d_km
            nearest_district = dist_name

    if elev < 1000:
        belt = "Yunga Fluvial / Selva Alta Baja (< 1,000 m)"
        crops_local = ["Cacao", "Frijol", "Café de valle", "Maíz amarillo", "Palta Hass"]
    elif elev < 2100:
        belt = "Yunga Cafetalera / Flanco Montano (1,000–2,100 m)"
        crops_local = ["Café de altura", "Tuna + Cochinilla", "Tara / Taya", "Palta Hass", "Frijol", "Arracacha"]
    elif elev < 2800:
        belt = "Quechua — Valle Interandino y Condebamba (2,100–2,800 m)"
        crops_local = ["Tuna + Cochinilla", "Tomillo / Orégano", "Tara / Taya", "Palta Hass", "Arracacha", "Kiwicha", "Lenteja", "Maíz amiláceo", "Frijol", "Papa"]
    elif elev < 3400:
        belt = "Quechua Alta — Ladera Interandina (2,800–3,400 m)"
        crops_local = ["Papa", "Oca / Olluco / Mashua", "Tarwi / Chocho", "Quinua", "Tomillo / Aromáticas", "Lenteja", "Linaza", "Arveja", "Cebada", "Avena + Vicia"]
    else:
        belt = "Suni / Jalca Altoandina (≥ 3,400 m)"
        crops_local = ["Papa nativa", "Oca, Olluco y Mashua", "Quinua", "Tarwi / Chocho", "Linaza", "Cebada", "Avena + Vicia", "Ryegrass + Trébol"]

    return {
        "nearest_district": nearest_district,
        "agro_belt_name": belt,
        "traditional_local_crops": crops_local,
    }


def _build_soil_profile(
    elev: float,
    slope: float,
    farmer_soil: Dict[str, Any],
    soilgrids_data: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Combina SoilGrids REST v2.0 (ISRIC) con calibración local INIA Baños del Inca y reporte de chacra."""
    acid_rep = farmer_soil.get("soil_acidity") == "acido"
    tex_ovr = str(farmer_soil.get("texture_override", "auto"))

    if soilgrids_data and soilgrids_data.get("ph") is not None:
        profile = dict(soilgrids_data)
        if acid_rep and profile["ph"] > 5.6:
            profile["ph"] = round(profile["ph"] - 0.5, 2)
            profile["note"] = "Ajustado con acidez reportada en campo."
        return profile

    # Fallback calibrado según ZEE Cajamarca / INIA (por piso altitudinal y pendiente)
    if elev >= 3400:
        ph, clay, sand, silt, soc, nitro, tex = 5.2, 20.0, 46.0, 34.0, 32.0, 2.6, "Franco arenoso orgánico"
    elif elev >= 2850:
        ph, clay, sand, silt, soc, nitro, tex = 5.7, 25.0, 42.0, 33.0, 22.0, 1.9, "Franco arenoso de ladera" if slope >= 12 else "Franco"
    elif elev >= 2100:
        ph, clay, sand, silt, soc, nitro, tex = 6.3, 31.0, 34.0, 35.0, 19.0, 1.8, "Franco arcilloso"
    else:
        ph, clay, sand, silt, soc, nitro, tex = 5.8, 29.0, 38.0, 33.0, 20.5, 1.9, "Franco arcillo-arenoso"

    if acid_rep:
        ph = round(min(ph, 5.2), 2)
    if tex_ovr == "franco_arenoso":
        sand, clay, silt, tex = 58.0, 16.0, 26.0, "Franco arenoso"
    elif tex_ovr == "arcilloso_pesado":
        clay, sand, silt, tex = 44.0, 24.0, 32.0, "Arcilloso"

    return {
        "ph": ph,
        "clay_pct": clay,
        "sand_pct": sand,
        "silt_pct": silt,
        "soc_g_kg": soc,
        "organic_matter_pct": round(soc * 0.1724, 2),
        "nitrogen_g_kg": nitro,
        "texture_class": tex,
        "source_mode": "calibrado_inia",
        "source_label": "Referencia INIA Baños del Inca / ZEE Cajamarca (respaldo offline)",
    }


def estimate_srtm_terrain(
    lat: float,
    lon: float,
    polygon: Optional[List[List[float]]] = None,
    parcel_id: Optional[str] = None,
    farmer_soil: Optional[Dict[str, Any]] = None,
    dem_sample: Optional[Dict[str, Any]] = None,
    soilgrids_data: Optional[Dict[str, Any]] = None,
    custom_zone_label: Optional[str] = None,
) -> Dict[str, Any]:
    zones_data = load_zones_data()
    beacon_map = {z["id"]: z for z in zones_data["beacon_parcels"]}

    poly_info = compute_polygon_metrics(polygon)
    if poly_info is not None:
        lat = poly_info["centroid_lat"]
        lon = poly_info["centroid_lon"]

    farmer_soil = farmer_soil or {}
    tex_ovr = str(farmer_soil.get("texture_override", "auto"))
    local_frost_early = bool(farmer_soil.get("local_frost_early", False))

    if parcel_id and parcel_id in beacon_map and polygon is None:
        b = beacon_map[parcel_id]
        soil_txt = _SOIL_OVERRIDE_LABELS.get(tex_ovr, b["soil_texture"])
        frost_win = b["frost_risk_window"]
        if local_frost_early:
            frost_win = f"Mayo – Septiembre (helada temprana reportada en chacra; base: {frost_win.split('(')[0].strip()})"

        elev_val = float(b["elevation_m"])
        slope_val = float(b["slope_pct"])
        dem_src = "referencia_faro"
        dem_mode = "modelo"
        dem_label = "Referencia Parcela Faro"
        if dem_sample is not None:
            # Prefer real SRTM 30 m or Copernicus DEM 90 m elevation while safeguarding flat-parcel slope fidelity
            elev_val = float(dem_sample["elevation_m"])
            if dem_sample.get("source") == "srtm_30m_opentopography":
                slope_val = float(dem_sample["slope_pct"])
            dem_src = str(dem_sample.get("source", "open_meteo_cop90"))
            dem_mode = str(dem_sample.get("mode", "en_vivo"))
            dem_label = str(dem_sample.get("sensor_label", "DEM satelital"))

        zone_meta = detect_cajamarca_agro_zone(float(b["lat"]), float(b["lon"]), elev_val)
        soil_profile = _build_soil_profile(elev_val, slope_val, farmer_soil, soilgrids_data)
        micro_relief = {
            "elevation_min_m": dem_sample.get("elevation_min_m", elev_val) if dem_sample else elev_val,
            "elevation_max_m": dem_sample.get("elevation_max_m", elev_val) if dem_sample else elev_val,
            "elevation_span_m": dem_sample.get("elevation_span_m", 0.0) if dem_sample else 0.0,
            "slope_min_pct": dem_sample.get("slope_min_pct", slope_val) if dem_sample else slope_val,
            "slope_max_pct": dem_sample.get("slope_max_pct", slope_val) if dem_sample else slope_val,
            "aspect_deg": dem_sample.get("aspect_deg") if dem_sample else None,
            "aspect_label": (dem_sample.get("aspect_label") if dem_sample else None) or "Plano / Valle de referencia",
            "aspect_insolation_note": dem_sample.get("aspect_insolation_note") if dem_sample else None,
            "polygon_vertices_sampled": dem_sample.get("polygon_vertices_sampled", 0) if dem_sample else 0,
            "vertex_differential_risk": dem_sample.get("vertex_differential_risk") if dem_sample else None,
        }

        return {
            "lat": b["lat"],
            "lon": b["lon"],
            "elevation_m": elev_val,
            "slope_pct": slope_val,
            "area_ha": float(b["area_ha"]),
            "zone_name": b["name"],
            "zone_type": b["zone_type"],
            "soil_texture": soil_txt,
            "soil_source": "reportado_agricultor" if tex_ovr in _SOIL_OVERRIDE_LABELS else "referencia_zona",
            "frost_risk_window": frost_win,
            "primary_hazard": b["primary_hazard"],
            "is_beacon": True,
            "beacon_id": b["id"],
            "dem_source": dem_src,
            "dem_mode": dem_mode,
            "dem_label": dem_label,
            **micro_relief,
            "agro_belt_name": zone_meta["agro_belt_name"],
            "nearest_district": zone_meta["nearest_district"],
            "traditional_local_crops": zone_meta["traditional_local_crops"],
            "soil_profile": soil_profile,
        }

    elev, slope, zlabel, soil = _idw_terrain(lat, lon)
    dem_src = "modelo_idw_cajamarca"
    dem_mode = "modelo"
    dem_label = "Interpolación de puntos de referencia"
    poly_elev_min: Optional[float] = None
    poly_elev_max: Optional[float] = None
    poly_elev_span: Optional[float] = None
    poly_vertex_risk: Optional[str] = None

    if dem_sample is not None:
        elev = float(dem_sample["elevation_m"])
        slope = float(dem_sample["slope_pct"])
        dem_src = str(dem_sample.get("source", "open_meteo_cop90"))
        dem_mode = str(dem_sample.get("mode", "en_vivo"))
        dem_label = str(dem_sample.get("sensor_label", "DEM satelital"))
    elif poly_info is not None and polygon and len(polygon) >= 3:
        vert_elevs = [_idw_terrain(p[0], p[1])[0] for p in polygon]
        elev_diff = max(vert_elevs) - min(vert_elevs)
        poly_slope = (elev_diff / max(40.0, poly_info["span_m"])) * 100.0
        slope = round(min(38.0, max(1.8, 0.7 * slope + 0.3 * poly_slope)), 1)
        poly_elev_min = round(float(min(vert_elevs)), 1)
        poly_elev_max = round(float(max(vert_elevs)), 1)
        poly_elev_span = round(float(elev_diff), 1)
        poly_vertex_risk = (
            f"Desnivel estimado de {poly_elev_span:.0f} m entre vértices del polígono (modelo IDW; pendiente aprox. {slope:.1f}%)."
        )

    min_anchor_km = min(
        math.hypot((lat - a_lat) * 111.0, (lon - a_lon) * 110.0)
        for a_lat, a_lon, *_ in _CAJAMARCA_DEM_ANCHORS
    )

    if elev < 1000:
        zone_type = "Yunga Fluvial / Selva Alta Baja"
    elif elev < 2100:
        zone_type = "Yunga Cafetalera / Flanco Montano"
    elif elev < 2780:
        zone_type = "Piso de Valle Aluvial"
    elif elev < 3180:
        zone_type = "Ladera Media Interandina"
    else:
        zone_type = "Ladera Alta / Cabecera de Cuenca"

    if min_anchor_km > 35.0 and not custom_zone_label:
        zlabel = f"{zone_type} ({lat:.3f}, {lon:.3f})"

    area_ha: Optional[float] = float(poly_info["area_ha"]) if poly_info else None

    if elev < 1800:
        frost_window = "Sin riesgo de heladas (< 1,800 m; vigilar golpes de calor seco)"
    elif elev >= 3180:
        frost_window = "Mayo – Septiembre (riesgo severo por altitud >3,180 m)"
    elif slope < 5.5 and elev < 2780:
        frost_window = "Junio – Agosto (inversión térmica nocturna en piso de valle)"
    else:
        frost_window = "Junio – Agosto (heladas moderadas en madrugadas despejadas)"

    if local_frost_early and elev >= 1800:
        frost_window = "Mayo – Septiembre (helada temprana reportada directamente en campo)"

    if slope >= 15.0:
        primary_hazard = f"Erosión hídrica por escorrentía en pendiente ({slope:.1f}%) durante lluvias GPM"
    elif elev < 1800:
        primary_hazard = "Veranillos secos, golpes de calor y roya/broca si no hay sombra o cobertura"
    elif elev >= 3200:
        primary_hazard = "Estrés por heladas de altura y lavado superficial en ladera"
    else:
        primary_hazard = "Déficit hídrico en estiaje (mayo–septiembre) y heladas radiativas"

    zone_meta = detect_cajamarca_agro_zone(lat, lon, float(elev))
    soil_profile = _build_soil_profile(float(elev), float(slope), farmer_soil, soilgrids_data)

    if tex_ovr in _SOIL_OVERRIDE_LABELS:
        soil_txt = _SOIL_OVERRIDE_LABELS[tex_ovr]
        soil_src = "reportado_agricultor"
    elif soilgrids_data and soilgrids_data.get("ph") is not None:
        soil_txt = f"{soil_profile['texture_class']} (pH {soil_profile['ph']}, MO {soil_profile['organic_matter_pct']}%)"
        soil_src = "soilgrids_isric"
    else:
        soil_txt = soil
        soil_src = "referencia_zona"

    micro_relief_nonbeacon = {
        "elevation_min_m": dem_sample.get("elevation_min_m", poly_elev_min or float(elev)) if dem_sample else (poly_elev_min or float(elev)),
        "elevation_max_m": dem_sample.get("elevation_max_m", poly_elev_max or float(elev)) if dem_sample else (poly_elev_max or float(elev)),
        "elevation_span_m": dem_sample.get("elevation_span_m", poly_elev_span or 0.0) if dem_sample else (poly_elev_span or 0.0),
        "slope_min_pct": dem_sample.get("slope_min_pct", float(slope)) if dem_sample else float(slope),
        "slope_max_pct": dem_sample.get("slope_max_pct", float(slope)) if dem_sample else float(slope),
        "aspect_deg": dem_sample.get("aspect_deg") if dem_sample else None,
        "aspect_label": (dem_sample.get("aspect_label") if dem_sample else None) or ("Plano / Fondo de valle" if float(slope) < 2.0 else "Ladera local"),
        "aspect_insolation_note": dem_sample.get("aspect_insolation_note") if dem_sample else None,
        "polygon_vertices_sampled": dem_sample.get("polygon_vertices_sampled", len(polygon) if (polygon and len(polygon) >= 3) else 0) if dem_sample else (len(polygon) if (polygon and len(polygon) >= 3) else 0),
        "vertex_differential_risk": dem_sample.get("vertex_differential_risk", poly_vertex_risk) if dem_sample else poly_vertex_risk,
    }

    return {
        "lat": round(lat, 5),
        "lon": round(lon, 5),
        "elevation_m": float(elev),
        "slope_pct": float(slope),
        "area_ha": area_ha,
        "zone_name": custom_zone_label or zlabel,
        "zone_type": zone_type,
        "soil_texture": soil_txt,
        "soil_source": soil_src,
        "frost_risk_window": frost_window,
        "primary_hazard": primary_hazard,
        "is_beacon": False,
        "beacon_id": None,
        "dem_source": dem_src,
        "dem_mode": dem_mode,
        "dem_label": dem_label,
        **micro_relief_nonbeacon,
        "agro_belt_name": zone_meta["agro_belt_name"],
        "nearest_district": zone_meta["nearest_district"],
        "traditional_local_crops": zone_meta["traditional_local_crops"],
        "soil_profile": soil_profile,
    }


async def fetch_era5_soil_et0(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Zero-key live ERA5-Land historical soil moisture (0–7 cm, 7–28 cm) & FAO ET0 via Open-Meteo Archive.
    Covers the full 2025 hydrological calendar year and caches per grid cell.
    """
    cached = _ERA5_CACHE.get(lat, lon)
    if cached is not None:
        return {**cached, "cache_hit": True, "mode": "guardado"}

    params = {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "hourly": "soil_moisture_0_to_7cm,soil_moisture_7_to_28cm",
        "daily": "et0_fao_evapotranspiration,precipitation_sum,temperature_2m_min",
        "timezone": "America/Lima",
    }

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(OPEN_METEO_ARCHIVE_URL, params=params)
            resp.raise_for_status()
            raw = resp.json()

        hourly = raw.get("hourly", {})
        daily = raw.get("daily", {})
        h_times = hourly.get("time", [])
        sm_top = hourly.get("soil_moisture_0_to_7cm", [])
        sm_root = hourly.get("soil_moisture_7_to_28cm", [])

        d_times = daily.get("time", [])
        et0_vals = daily.get("et0_fao_evapotranspiration", [])
        if not h_times or not d_times:
            return None

        h_df = pd.DataFrame({
            "month": [int(t[5:7]) for t in h_times],
            "sm0_7": pd.to_numeric(sm_top, errors="coerce"),
            "sm7_28": pd.to_numeric(sm_root, errors="coerce"),
        })
        d_df = pd.DataFrame({
            "month": [int(t[5:7]) for t in d_times],
            "et0": pd.to_numeric(et0_vals, errors="coerce"),
        })

        sm0_monthly = [round(float(h_df.loc[h_df["month"] == m, "sm0_7"].mean()), 3) for m in range(1, 13)]
        sm_root_monthly = [round(float(h_df.loc[h_df["month"] == m, "sm7_28"].mean()), 3) for m in range(1, 13)]
        et0_monthly = [round(float(d_df.loc[d_df["month"] == m, "et0"].sum()), 1) for m in range(1, 13)]

        payload = {
            "source": "era5_land_open_meteo",
            "mode": "en_vivo",
            "cache_hit": False,
            "dem_elev_m": raw.get("elevation"),
            "soil_moisture_0_to_7cm": sm0_monthly,
            "soil_moisture_7_to_28cm": sm_root_monthly,
            "et0_fao_mm": et0_monthly,
        }
        _ERA5_CACHE.set(lat, lon, payload)
        return payload
    except Exception:
        return None


async def _query_soilgrids_point(
    client: httpx.AsyncClient,
    q_lat: float,
    q_lon: float,
) -> Tuple[Optional[Dict[str, float]], bool]:
    """Queries ISRIC SoilGrids REST v2.0 for a single coordinate and averages 0-30 cm layers.
    Returns (props, should_abort_ring) where should_abort_ring=True on HTTP 429/5xx or timeout.
    """
    params = [
        ("lon", f"{q_lon:.4f}"),
        ("lat", f"{q_lat:.4f}"),
        ("property", "phh2o"),
        ("property", "clay"),
        ("property", "sand"),
        ("property", "silt"),
        ("property", "soc"),
        ("property", "nitrogen"),
        ("depth", "0-5cm"),
        ("depth", "5-15cm"),
        ("depth", "15-30cm"),
        ("value", "mean"),
    ]
    try:
        resp = await client.get(SOILGRIDS_API_URL, params=params)
        if resp.status_code == 429 or resp.status_code >= 500:
            return None, True
        if resp.status_code != 200:
            return None, False
        data = resp.json()
        layers = ((data or {}).get("properties") or {}).get("layers") or []
        parsed_props: Dict[str, float] = {}
        # Ponderación estándar de capa arable 0-30 cm: 5 cm + 10 cm + 15 cm = 30 cm
        depth_weights = {"0-5cm": 5.0 / 30.0, "5-15cm": 10.0 / 30.0, "15-30cm": 15.0 / 30.0}

        for layer in layers:
            prop_name = layer.get("name")
            depths = layer.get("depths") or []
            weighted_sum = 0.0
            weight_acc = 0.0
            for d in depths:
                label = d.get("label")
                mean_val = (d.get("values") or {}).get("mean")
                w = depth_weights.get(label, 1.0 / max(1, len(depths)))
                if mean_val is not None:
                    weighted_sum += float(mean_val) * w
                    weight_acc += w
            if prop_name and weight_acc > 0:
                parsed_props[prop_name] = weighted_sum / weight_acc

        if not parsed_props or "phh2o" not in parsed_props:
            return None, False
        return parsed_props, False
    except Exception:
        return None, True


def _build_soilgrids_payload(
    parsed_props: Dict[str, float],
    *,
    source_label: str,
    nearby_sampled: bool,
    nearby_radius_m: Optional[int] = None,
) -> Dict[str, Any]:
    ph = round(parsed_props["phh2o"] / 10.0, 2)
    clay_pct = round(parsed_props.get("clay", 280.0) / 10.0, 1)
    sand_pct = round(parsed_props.get("sand", 360.0) / 10.0, 1)
    silt_pct = round(parsed_props.get("silt", 360.0) / 10.0, 1)
    soc_g_kg = round(parsed_props.get("soc", 210.0) / 10.0, 1)
    organic_matter_pct = round(soc_g_kg * 0.1724, 2)
    nitrogen_g_kg = round(parsed_props.get("nitrogen", 200.0) / 100.0, 2)

    return {
        "ph": ph,
        "clay_pct": clay_pct,
        "sand_pct": sand_pct,
        "silt_pct": silt_pct,
        "soc_g_kg": soc_g_kg,
        "organic_matter_pct": organic_matter_pct,
        "nitrogen_g_kg": nitrogen_g_kg,
        "texture_class": _classify_usda_texture(clay_pct, sand_pct, silt_pct),
        "source_mode": "en_vivo",
        "source_label": source_label,
        "nearby_sampled": nearby_sampled,
        "nearby_radius_m": nearby_radius_m,
    }


async def fetch_soilgrids_isric(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Consulta propiedades reales de suelo (0-30 cm) desde SoilGrids REST API v2.0 (ISRIC).
    Si el píxel exacto está enmascarado por zona urbana/agua, muestrea un par agrícola (~450 m).
    Falla rápido ante 429/5xx/timeout de ISRIC para no demorar la respuesta en paralelo.
    """
    cached = _SOILGRIDS_CACHE.get(lat, lon)
    if cached:
        return {**cached, "source_mode": "guardado"}

    try:
        async with httpx.AsyncClient(timeout=3.5) as client:
            center_props, hard_fail = await _query_soilgrids_point(client, lat, lon)
            if center_props is not None:
                payload = _build_soilgrids_payload(
                    center_props,
                    source_label="SoilGrids REST v2.0 (ISRIC 250 m, 0–30 cm)",
                    nearby_sampled=False,
                    nearby_radius_m=None,
                )
                _SOILGRIDS_CACHE.set(lat, lon, payload)
                return payload

            if hard_fail:
                return None

            # Urban / water masked center pixel (HTTP 200 without soil values): single fast ~450 m probe
            ring_coords = [(lat + 0.0040, lon), (lat, lon + 0.0040)]
            ring_results = await asyncio.gather(
                *[_query_soilgrids_point(client, r_lat, r_lon) for r_lat, r_lon in ring_coords]
            )
            valid_ring = [props for props, _ in ring_results if props is not None]
            if not valid_ring:
                return None
            avg_props: Dict[str, float] = {}
            for key in ("phh2o", "clay", "sand", "silt", "soc", "nitrogen"):
                vals = [r[key] for r in valid_ring if key in r]
                if vals:
                    avg_props[key] = float(np.mean(vals))
            if "phh2o" in avg_props:
                payload = _build_soilgrids_payload(
                    avg_props,
                    source_label="SoilGrids REST v2.0 (anillo agrícola ~450 m, ISRIC 250 m)",
                    nearby_sampled=True,
                    nearby_radius_m=450,
                )
                _SOILGRIDS_CACHE.set(lat, lon, payload)
                return payload
            return None
    except Exception:
        return None


def _classify_usda_texture(clay: float, sand: float, silt: float) -> str:
    """Clasificación simplificada USDA de textura del suelo para recomendación agronómica."""
    if clay >= 40.0:
        return "Arcilloso"
    if clay >= 27.0 and sand < 45.0:
        return "Franco arcilloso"
    if sand >= 65.0 and clay < 18.0:
        return "Franco arenoso"
    if silt >= 50.0 and clay < 27.0:
        return "Franco limoso"
    if clay < 20.0 and sand >= 45.0:
        return "Franco arenoso"
    return "Franco"


def load_earthdata_for_point(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Loads pre-fetched NASA AppEEARS SMAP & ECOSTRESS observations from backend/cache/earthdata_cajamarca.json
    and interpolates across Cajamarca points if available.
    """
    if not EARTHDATA_CAJAMARCA_CACHE.exists():
        return None
    try:
        with open(EARTHDATA_CAJAMARCA_CACHE, "r", encoding="utf-8") as f:
            doc = json.load(f)
        pts = list(doc.get("points", {}).values())
        if not pts:
            return None

        weights = []
        for p in pts:
            d = max(0.05, math.hypot((lat - float(p["lat"])) * 111.0, (lon - float(p["lon"])) * 110.0))
            weights.append(1.0 / (d ** 2))
        w = np.array(weights, dtype=float)
        w /= np.sum(w)

        def _interp_nullable(key: str) -> Optional[List[float]]:
            mat = []
            valid_w = []
            for idx, p in enumerate(pts):
                arr = p.get(key)
                if isinstance(arr, list) and len(arr) == 12 and sum(x is not None for x in arr) >= 4:
                    # Fill sparse months cleanly along annual cycle
                    s = pd.Series(arr, dtype=float).interpolate(method="linear", limit_direction="both")
                    mat.append(s.to_numpy())
                    valid_w.append(w[idx])
            if not mat:
                return None
            vw = np.array(valid_w, dtype=float)
            vw /= np.sum(vw)
            return [round(float(v), 3) for v in (vw @ np.array(mat))]

        return {
            "smap_monthly": _interp_nullable("smap_monthly"),
            "ecostress_et_daily": _interp_nullable("ecostress_et_monthly"),
            "smap_product": doc.get("smap_product"),
            "ecostress_product": doc.get("ecostress_product"),
            "fetched_at": doc.get("fetched_at"),
        }
    except Exception:
        return None

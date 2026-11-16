"""Application use cases for reference data, geocoding, parcel biophysical analysis, and recommendations."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from fastapi import HTTPException

from application.schemas import ParcelAnalyzeRequest, RecommendRequest
from config import get_integration_status
from copernicus_client import fetch_sentinel2_monthly_ndvi
from domain.catalog import _CAJAMARCA_LOCATIONS, load_crops_data, load_zones_data
from domain.rotation_engine import generate_rotation_recommendations
from infrastructure.biophysical_harmonizer import build_harmonized_biophysical_series
from infrastructure.geocoding_client import geocode_cajamarca_place
from infrastructure.market_prices_client import (
    apply_market_prices_to_crops,
    fetch_live_market_snapshot,
)
from infrastructure.soil_terrain_client import (
    compute_polygon_metrics,
    estimate_srtm_terrain,
    fetch_era5_soil_et0,
    fetch_soilgrids_isric,
    load_earthdata_for_point,
)
from infrastructure.weather_power_client import (
    fetch_live_current_weather,
    fetch_nasa_power_climatology,
)
from terrain_dem import resolve_real_dem_terrain


async def get_health_payload() -> Dict[str, Any]:
    """Verifica el estado del servidor y los catálogos calibrados de Cajamarca."""
    crops = load_crops_data()["crops"]
    zones = load_zones_data()["beacon_parcels"]
    return {
        "status": "ok",
        "service": "Cajamarca AgroClima NASA API",
        "crops_loaded": len(crops),
        "beacon_parcels_loaded": len(zones),
    }


async def get_reference_data_payload() -> Dict[str, Any]:
    """
    Devuelve las 3 Parcelas Faro preconfiguradas, capas GeoJSON de pisos agroecológicos de Cajamarca,
    la base de conocimiento de los 24 cultivos locales y el glosario del Traductor Científico.
    """
    zones = load_zones_data()
    crops = load_crops_data()
    market_snapshot = await fetch_live_market_snapshot()
    enriched_crops, market_summary = apply_market_prices_to_crops(
        crops.get("crops", []),
        market_snapshot,
    )
    crops_meta = dict(crops.get("metadata") or {})
    existing_sources = list(crops_meta.get("sources") or [])
    for src in (
        "MIDAGRI SISAP Precios de Ciudades (Cajamarca / Chota / Jaén)",
        "MIDAGRI Observatorio Agromercado (Quinua / Palta / Café / Cacao)",
        "EMMSA Gran Mercado Mayorista de Lima",
        "BCRP Tipo de Cambio Bancario Venta (PD04640PD)",
    ):
        if src not in existing_sources:
            existing_sources.append(src)
    crops_meta["sources"] = existing_sources
    crops_meta["market_summary"] = market_summary
    return {
        "map_center": zones["map_center"],
        "beacon_parcels": zones["beacon_parcels"],
        "known_locations": [
            {
                "label": loc["label"],
                "lat": float(loc["lat"]),
                "lon": float(loc["lon"]),
                "parcel_id": loc.get("parcel_id"),
            }
            for loc in _CAJAMARCA_LOCATIONS
        ],
        "agroecological_belts_geojson": zones["agroecological_belts_geojson"],
        "scientific_glossary": zones["scientific_glossary"],
        "crops": enriched_crops,
        "crops_metadata": crops_meta,
        "market_summary": market_summary,
        "current_crop_options": [
            {"id": "sin_cultivo", "label": "Terreno libre / Sin cultivo previo todavía"},
            {"id": "monocultivo_papa", "label": "Monocultivo de Papa (Solanum tuberosum)"},
            {"id": "papa_maiz", "label": "Rotación corta Papa – Maíz amiláceo"},
            {"id": "pastos_degradados", "label": "Pastos degradados / sobrepastoreo"},
            {"id": "cebada_trigo_continuo", "label": "Cebada / Trigo continuo sin leguminosas"},
        ],
        "water_options": [
            {"id": "secano", "label": "Solo lluvia (secano estricto)"},
            {"id": "cosecha_agua_qocha", "label": "Cosecha de agua / Qocha / Micro-reservorio"},
            {"id": "riego_deficitario", "label": "Riego por turnos / Riego de auxilio"},
            {"id": "riego_gravedad", "label": "Acequia / Riego por gravedad"},
            {"id": "riego_melgas_surcos", "label": "Surcos / Melgas en contorno (sin erosión)"},
            {"id": "riego_aspersion", "label": "Riego por aspersión"},
            {"id": "riego_goteo", "label": "Riego tecnificado por goteo / fertirriego"},
        ],
        "equipment_options": [
            {"id": "manual_yunta", "label": "Yunta, chaquitaclla o lampa (trabajo familiar)"},
            {"id": "tractor_compartido", "label": "Tractor o trilla alquilada por campañas"},
            {"id": "mecanizado", "label": "Maquinaria completa y fácil acceso vehicular"},
        ],
        "market_options": [
            {"id": "autoconsumo_feria", "label": "Comida de casa + venta en feria local"},
            {"id": "leche_forraje", "label": "Pasto y alimento para ganado / venta de leche"},
            {"id": "grano_comercial", "label": "Venta de cosecha al por mayor / grano seco"},
        ],
        "soil_texture_options": [
            {"id": "auto", "label": "Usar dato estimado de la zona"},
            {"id": "franco_arcilloso", "label": "Tierra negra / franca (suelta y pareja)"},
            {"id": "franco_arenoso", "label": "Tierra arenosa (chupa agua rápido)"},
            {"id": "arcilloso_pesado", "label": "Tierra barrosa / arcilla pesada"},
            {"id": "pedregoso", "label": "Tierra cascajosa / con bastante piedra"},
        ],
        "soil_acidity_options": [
            {"id": "normal", "label": "Tierra normal (produce alfalfa o haba sin problema)"},
            {"id": "acido", "label": "Tierra ácida o «chacra cansada» de altura"},
            {"id": "no_se", "label": "No estoy seguro (revisar en campo)"},
        ],
        "soil_condition_options": [
            {"id": "normal", "label": "Drena bien y no está dura"},
            {"id": "duro_compactado", "label": "Suelo duro o apretado al arar"},
            {"id": "se_encharca", "label": "Se empoza cuando llueve fuerte"},
        ],
        "field_status_options": [
            {"id": "auto", "label": "Automático según fecha de hoy"},
            {"id": "terreno_libre", "label": "Está libre / lista para sembrar"},
            {"id": "con_cultivo", "label": "Ya tiene cultivo sembrado ahora"},
        ],
    }


async def get_integrations_status_payload() -> Dict[str, Any]:
    """Devuelve únicamente indicadores booleanos de claves y cachés satelitales locales (sin exponer secretos)."""
    return {
        "status": "ok",
        "integrations": get_integration_status(),
    }


async def geocode_place_use_case(q: str) -> Dict[str, Any]:
    """Geocodifica en tiempo real un distrito, caserío o sector en todo el Perú."""
    query = q.strip()
    if len(query) < 2:
        raise HTTPException(status_code=400, detail="Escribe al menos 2 letras para buscar.")
    geo = await geocode_cajamarca_place(query)
    return {
        "query": query,
        "found": geo is not None,
        "result": geo,
    }


async def _run_parcel_biophysical_analysis(
    req: ParcelAnalyzeRequest,
    custom_zone_label: Optional[str] = None,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    farmer_soil_dict = req.farmer_soil.model_dump()
    poly_info = compute_polygon_metrics(req.polygon)
    target_lat = poly_info["centroid_lat"] if poly_info is not None else req.lat
    target_lon = poly_info["centroid_lon"] if poly_info is not None else req.lon

    dem_sample, raw_power, era5_data, sentinel2_data, soilgrids_data, live_weather, market_snapshot = await asyncio.gather(
        resolve_real_dem_terrain(target_lat, target_lon, polygon=req.polygon),
        fetch_nasa_power_climatology(target_lat, target_lon),
        fetch_era5_soil_et0(target_lat, target_lon),
        fetch_sentinel2_monthly_ndvi(target_lat, target_lon, polygon=req.polygon),
        fetch_soilgrids_isric(target_lat, target_lon),
        fetch_live_current_weather(target_lat, target_lon),
        fetch_live_market_snapshot(),
    )

    terrain = estimate_srtm_terrain(
        lat=req.lat,
        lon=req.lon,
        polygon=req.polygon,
        parcel_id=req.parcel_id,
        farmer_soil=farmer_soil_dict,
        dem_sample=dem_sample,
        soilgrids_data=soilgrids_data,
        custom_zone_label=custom_zone_label or req.custom_zone_label,
    )
    earthdata = load_earthdata_for_point(terrain["lat"], terrain["lon"])
    _, market_summary = apply_market_prices_to_crops(
        load_crops_data().get("crops", []),
        market_snapshot,
        lat=terrain["lat"],
        lon=terrain["lon"],
    )
    biophysical = build_harmonized_biophysical_series(
        terrain=terrain,
        raw_power=raw_power,
        current_crop=req.current_crop,
        water_availability=req.water_availability,
        farmer_soil=farmer_soil_dict,
        era5_data=era5_data,
        sentinel2_data=sentinel2_data,
        earthdata=earthdata,
        live_weather=live_weather,
        market_summary=market_summary,
    )
    return terrain, biophysical


async def analyze_parcel_use_case(req: ParcelAnalyzeRequest) -> Dict[str, Any]:
    """
    Consulta en paralelo NASA POWER Diario (+GWETTOP), Open-Meteo Copernicus DEM 90 m / SRTM 30 m,
    ERA5-Land suelo/ET0, Sentinel-2 L2A (si CDSE está configurado) y caché Earthdata SMAP/ECOSTRESS.
    """
    try:
        terrain, biophysical = await _run_parcel_biophysical_analysis(req)
        return {
            "terrain": terrain,
            "biophysical": biophysical,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error analizando parcela: {exc}")


async def recommend_rotations_use_case(req: RecommendRequest) -> Dict[str, Any]:
    """
    Ejecuta el análisis satelital multi-fuente + simulador de escenarios climáticos ('¿Qué pasaría si...?')
    + motor multicriterio MCDA generando las 3 estrategias comparativas a 24 meses con explicabilidad completa.
    """
    try:
        farmer_soil_dict = req.farmer_soil.model_dump()
        terrain, biophysical = await _run_parcel_biophysical_analysis(req)
        market_snapshot = await fetch_live_market_snapshot()
        enriched_crops, _ = apply_market_prices_to_crops(
            load_crops_data().get("crops", []),
            market_snapshot,
            lat=terrain["lat"],
            lon=terrain["lon"],
        )
        recommendation = generate_rotation_recommendations(
            terrain=terrain,
            biophysical=biophysical,
            current_crop=req.current_crop,
            water_availability=req.water_availability,
            priorities=req.priorities.model_dump(),
            climate_scenario=req.climate_scenario.model_dump(),
            equipment_access=req.equipment_access,
            market_preference=req.market_preference,
            farmer_soil=farmer_soil_dict,
            field_status=req.field_status,
            planning_month=req.planning_month,
            planning_year=req.planning_year,
            available_seeds=req.available_seeds,
            crops_override=enriched_crops,
        )
        return {
            "terrain": terrain,
            "biophysical": biophysical,
            **recommendation,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error generando recomendaciones: {exc}")

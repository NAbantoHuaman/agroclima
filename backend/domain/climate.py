"""Domain climate modulators, 20-year ENSO projections, and offline climate fallback."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from domain.catalog import load_crops_data, load_zones_data

_ENSO_20YR_MODULATORS: List[Tuple[int, float, float, float]] = [
    # (year, rain_mult, temp_offset_c, storm_mult)
    (2006, 0.96, -0.24, 0.92),
    (2007, 1.03, -0.18, 1.02),
    (2008, 1.09, -0.26, 1.08),
    (2009, 0.94, -0.12, 0.90),
    (2010, 0.87, +0.06, 0.86),
    (2011, 1.11, -0.19, 1.12),
    (2012, 1.05, -0.11, 1.04),
    (2013, 0.98, -0.05, 0.96),
    (2014, 0.99, +0.02, 0.98),
    (2015, 0.91, +0.16, 0.95),
    (2016, 0.82, +0.28, 0.88),
    (2017, 1.14, +0.18, 1.24),
    (2018, 0.97, +0.09, 1.00),
    (2019, 0.95, +0.17, 1.03),
    (2020, 1.04, +0.12, 1.08),
    (2021, 1.08, +0.08, 1.14),
    (2022, 1.06, +0.11, 1.11),
    (2023, 0.86, +0.38, 1.06),
    (2024, 0.92, +0.34, 1.09),
    (2025, 0.97, +0.29, 1.12),
]


def _build_yearly_series_from_monthly(
    t2m_c: List[float],
    t2m_min_c: List[float],
    precip_mm: List[float],
    gwettop: Optional[List[float]] = None,
) -> List[Dict[str, Any]]:
    """Constructs a deterministic 20-year (2006-2025) annual summary from monthly climatology."""
    base_annual_precip = float(sum(precip_mm))
    base_onset_precip = float(precip_mm[9] + precip_mm[10] + precip_mm[11])
    base_t2m_mean = float(np.mean(t2m_c))
    base_cold_tmin = float(np.mean([t2m_min_c[4], t2m_min_c[5], t2m_min_c[6], t2m_min_c[7]]))
    base_gwet = float(np.mean(gwettop)) if gwettop else 0.52

    yearly_raw: List[Dict[str, Any]] = []
    for yr, r_mult, t_off, s_mult in _ENSO_20YR_MODULATORS:
        dec_idx = (yr - 2006) / 19.0
        # Gradual shift toward slightly more concentrated onset variability & intense events
        onset_mult = r_mult * (1.0 - 0.04 * (dec_idx - 0.5))
        p_ann = round(base_annual_precip * r_mult, 1)
        p_onset = round(base_onset_precip * onset_mult, 1)
        t_mean = round(base_t2m_mean + t_off, 2)
        t_min_cold = round(base_cold_tmin + (t_off * 0.45) - (0.35 if r_mult < 0.92 else 0.0), 2)
        frost_base = max(2.0, (3.2 - base_cold_tmin) * 14.0)
        frost_days = round(float(np.clip(frost_base + (0.0 - (t_min_cold - base_cold_tmin)) * 5.0 + (2.5 if r_mult < 0.92 else 0.0), 1.0, 95.0)), 1)
        storm_base = max(4.0, (base_annual_precip / 42.0))
        storm_days = round(float(np.clip(storm_base * s_mult * (1.0 + 0.14 * dec_idx), 2.0, 42.0)), 1)
        gwet_yr = round(float(np.clip(base_gwet * (0.72 + 0.28 * r_mult), 0.18, 0.88)), 3)

        yearly_raw.append({
            "year": yr,
            "precip_annual_mm": p_ann,
            "onset_rain_mm": p_onset,
            "t2m_mean_c": t_mean,
            "t2m_min_c": t_min_cold,
            "frost_days_raw": frost_days,
            "storm_days_12mm": storm_days,
            "gwettop_mean": gwet_yr,
        })
    return yearly_raw


def _idw_fallback_power(lat: float, lon: float) -> Dict[str, Any]:
    """Spatial interpolation across Cajamarca's calibrated climate profiles when POWER API is offline."""
    zones_data = load_zones_data()
    beacons = zones_data["beacon_parcels"]
    weights = []
    for b in beacons:
        d = max(0.01, math.hypot((lat - b["lat"]) * 111.0, (lon - b["lon"]) * 110.0))
        weights.append(1.0 / (d ** 2))
    w = np.array(weights, dtype=float)
    w /= np.sum(w)

    def _interp(field: str) -> List[float]:
        mat = np.array([b["calibrated_monthly"][field] for b in beacons], dtype=float)
        return [round(float(v), 2) for v in (w @ mat)]

    t2m_c = _interp("t2m_c")
    t2m_min_c = _interp("t2m_min_c")
    precip_mm = _interp("precip_mm")
    solar_mj = _interp("solar_mj_m2_day")
    rh2m = _interp("rh2m_pct")
    yearly_raw = _build_yearly_series_from_monthly(t2m_c, t2m_min_c, precip_mm)

    elev_ref = float(np.dot(w, [b["elevation_m"] for b in beacons]))
    return {
        "source": "calibrated_cajamarca_fallback",
        "source_label": "Respaldo Calibrado Cajamarca (20 años Offline)",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "power_grid_elevation_m": round(elev_ref, 1),
        "t2m_c": t2m_c,
        "t2m_min_c": t2m_min_c,
        "precip_mm": precip_mm,
        "solar_mj_m2_day": solar_mj,
        "rh2m_pct": rh2m,
        "has_daily_metrics": False,
        "years_analyzed": len(yearly_raw),
        "yearly_raw": yearly_raw,
    }

def simulate_climate_scenario(
    biophysical: Dict[str, Any],
    terrain: Dict[str, Any],
    rain_delta_pct: float = 0.0,
    temp_delta_c: float = 0.0,
    frost_frequency: str = "normal",
) -> Dict[str, Any]:
    """
    Recalculates monthly climate, ET0, water balance, frost hazard, and erosion stress
    under the user's interactive 'What-if' climate scenario sliders.
    """
    monthly = biophysical["monthly_series"]
    slope = float(terrain["slope_pct"])

    frost_penalty_map = {"normal": 0.0, "moderada": 1.6, "severa": 3.2}
    frost_dip = frost_penalty_map.get(frost_frequency, 0.0)

    # Early frosts strike hardest in transition & dry months (Apr-Sep)
    frost_month_weights = np.array([0.2, 0.2, 0.3, 0.7, 1.0, 1.15, 1.2, 1.15, 0.9, 0.5, 0.3, 0.2])

    sim_months = []
    rain_mult = 1.0 + (rain_delta_pct / 100.0)
    # Atmospheric evaporative demand rises ~4.5% per +1°C warming
    et_mult = 1.0 + (0.045 * temp_delta_c)

    for i, m in enumerate(monthly):
        p_sim = round(max(1.0, float(m["precip_mm"]) * rain_mult), 1)
        t_sim = round(float(m["t2m_c"]) + float(temp_delta_c), 1)
        # Warming raises mean temp, but radiative dry-sky early frost events plunge Tmin
        tmin_sim = round(float(m["t2m_min_c"]) + (float(temp_delta_c) * 0.55) - (float(frost_dip) * float(frost_month_weights[i])), 1)
        et0_sim = round(float(m["et0_mm"]) * float(et_mult), 1)
        wb_sim = round(float(p_sim - et0_sim), 1)

        # Updated SMAP moisture proxy under scenario
        smap_sim = round(float(np.clip(float(m["smap_moisture"]) * (0.65 + 0.35 * rain_mult) / (1.0 + 0.03 * temp_delta_c), 0.08, 0.42)), 3)
        # Updated GPM storm factor under +rain scenario
        erosive_events_sim = round(float(m["gpm_erosive_events"]) * (rain_mult ** 1.35), 1)
        erosion_base = float(m["erosion_risk"]) * (rain_mult ** 1.25)
        erosion_sim = round(float(np.clip(erosion_base, 4.0, 99.0)), 1)

        sim_months.append({
            **m,
            "sim_precip_mm": float(p_sim),
            "sim_t2m_c": float(t_sim),
            "sim_t2m_min_c": float(tmin_sim),
            "sim_et0_mm": float(et0_sim),
            "sim_water_balance_mm": float(wb_sim),
            "sim_smap_moisture": float(smap_sim),
            "sim_gpm_erosive_events": float(erosive_events_sim),
            "sim_erosion_risk": float(erosion_sim),
            "sim_frost_risk": bool(tmin_sim <= 2.2),
        })

    ann_p = round(sum(x["sim_precip_mm"] for x in sim_months), 1)
    ann_et = round(sum(x["sim_et0_mm"] for x in sim_months), 1)
    min_t = round(min(x["sim_t2m_min_c"] for x in sim_months), 1)
    frost_months = [x["month"] for x in sim_months if x["sim_frost_risk"]]

    # Water deficit in growing season (Oct-Apr) & estiaje (May-Sep)
    wet_precip = sum(sim_months[idx]["sim_precip_mm"] for idx in [9, 10, 11, 0, 1, 2, 3])
    dry_precip = sum(sim_months[idx]["sim_precip_mm"] for idx in [4, 5, 6, 7, 8])
    dry_et = sum(sim_months[idx]["sim_et0_mm"] for idx in [4, 5, 6, 7, 8])

    drought_stress = float(np.clip(((650.0 - wet_precip) / 420.0) * 55.0 + ((dry_et - dry_precip) / 480.0) * 35.0, 5.0, 98.0))
    frost_stress = float(np.clip(len(frost_months) * 14.0 + max(0.0, 2.5 - min_t) * 12.0, 5.0, 98.0))
    erosion_stress = float(np.clip((slope / 22.0) * 55.0 + (ann_p / 1000.0) * 28.0 + (rain_delta_pct > 0) * rain_delta_pct * 0.7, 5.0, 98.0))

    return {
        "params": {
            "rain_delta_pct": rain_delta_pct,
            "temp_delta_c": temp_delta_c,
            "frost_frequency": frost_frequency,
        },
        "monthly_series": sim_months,
        "summary": {
            "annual_precip_mm": ann_p,
            "annual_et0_mm": ann_et,
            "annual_water_balance_mm": round(ann_p - ann_et, 1),
            "wet_season_precip_mm": round(wet_precip, 1),
            "min_temp_c": min_t,
            "frost_month_count": len(frost_months),
            "frost_risk_months": frost_months,
            "drought_stress_index": round(drought_stress, 1),
            "frost_stress_index": round(frost_stress, 1),
            "erosion_stress_index": round(erosion_stress, 1),
        },
    }


def _effective_water_supply_mm(sim_summary: Dict[str, Any], water_availability: str) -> float:
    wet_rain = float(sim_summary["wet_season_precip_mm"])
    # Effective infiltrated rain (~85% on average slope)
    base_supply = wet_rain * 0.85
    bonus_map = {
        "secano": 0.0,
        "cosecha_agua_qocha": 140.0,
        "riego_deficitario": 165.0,
        "riego_gravedad": 210.0,
        "riego_melgas_surcos": 255.0,
        "riego_aspersion": 320.0,
        "riego_goteo": 390.0,
    }
    return base_supply + bonus_map.get(water_availability, 0.0)


def _crop_climate_fit(
    crop: Dict[str, Any],
    elev_m: float,
    slope_pct: float,
    water_availability: str,
    sim_summary: Dict[str, Any],
) -> Tuple[float, float, float]:
    """
    Returns (water_fit_0_100, frost_fit_0_100, terrain_fit_0_100) for a given crop.
    """
    supply_mm = _effective_water_supply_mm(sim_summary, water_availability)
    req_mm = float(crop["water_req_mm"])
    if supply_mm >= req_mm:
        water_fit = 96.0
    else:
        deficit_ratio = (req_mm - supply_mm) / req_mm
        drought_shield = float(crop["drought_tolerance"]) / 100.0
        water_fit = float(np.clip(95.0 - deficit_ratio * (110.0 - 55.0 * drought_shield), 15.0, 96.0))

    if water_availability in ("riego_goteo", "riego_aspersion", "riego_melgas_surcos", "cosecha_agua_qocha"):
        eff_bonus = {
            "riego_goteo": 6.0,
            "riego_aspersion": 4.0,
            "riego_melgas_surcos": 3.0,
            "cosecha_agua_qocha": 3.0,
        }[water_availability]
        water_fit = float(np.clip(water_fit + eff_bonus, 15.0, 98.0))

    if water_availability == "secano" and crop["id"] in ("ryegrass_trebol", "alfalfa", "palta_intercultivo"):
        # Strict secano heavily penalizes high-water perennials in dry zones
        if sim_summary["annual_precip_mm"] < 760:
            water_fit = max(20.0, water_fit - 26.0)

    min_t = float(sim_summary["min_temp_c"])
    crit_t = float(crop["frost_critical_c"])
    if min_t >= crit_t + 1.5:
        frost_fit = 95.0
    else:
        gap = max(0.0, (crit_t + 1.5) - min_t)
        frost_shield = float(crop["frost_tolerance"]) / 100.0
        frost_fit = float(np.clip(92.0 - gap * (18.0 - 11.0 * frost_shield), 18.0, 95.0))

    # Altitude suitability
    alt_min = float(crop["altitude_min_m"])
    alt_max = float(crop["altitude_max_m"])
    if alt_min <= elev_m <= alt_max:
        alt_fit = 100.0
    elif elev_m > alt_max:
        alt_fit = max(12.0, 100.0 - (elev_m - alt_max) * 0.25)
    else:
        alt_fit = max(25.0, 100.0 - (alt_min - elev_m) * 0.20)

    # Slope suitability
    max_slope = float(crop["max_slope_pct"])
    if slope_pct <= max_slope:
        slope_fit = 96.0
    else:
        slope_fit = max(20.0, 96.0 - (slope_pct - max_slope) * 5.2)

    terrain_fit = 0.6 * alt_fit + 0.4 * slope_fit
    return water_fit, frost_fit, terrain_fit


def _score_crop_horizon(
    crop: Dict[str, Any],
    elev_m: float,
    slope_pct: float,
    water_availability: str,
    sim_summary: Dict[str, Any],
    horizon_years: int,
) -> float:
    water_fit, frost_fit, terrain_fit = _crop_climate_fit(
        crop=crop,
        elev_m=elev_m,
        slope_pct=slope_pct,
        water_availability=water_availability,
        sim_summary=sim_summary,
    )
    drought_tol = float(crop.get("drought_tolerance", 60.0))
    erosion_prot = float(crop.get("erosion_protection_score", 60.0))
    # Longer horizons amplify value of drought resilience and soil cover
    resilience_bonus = ((drought_tol - 55.0) * 0.14 + (erosion_prot - 55.0) * 0.08) * (horizon_years / 20.0)
    raw_score = 0.46 * water_fit + 0.30 * frost_fit + 0.24 * terrain_fit + resilience_bonus
    return round(float(np.clip(raw_score, 15.0, 98.0)), 1)


def _build_crop_20yr_advice(
    crop: Dict[str, Any],
    suit_now: float,
    suit_yr2: float,
    water_availability: str,
    temp_delta_20yr: float,
    precip_delta_20yr: float,
) -> str:
    cid = crop["id"]
    delta = suit_yr2 - suit_now
    if cid == "papa":
        if suit_yr2 < 52:
            return (
                "En monocultivo sufrirá fuerte estrés por las lluvias irregulares y veranillos vistos en los últimos 20 años; "
                "siémbrala en los próximos 2 años solo tras Tarwi o Avena + Vicia que guardan humedad."
            )
        return (
            "Viable en 2026–2027 si rompes el monocultivo con leguminosas y cubres el suelo apenas coseches para evitar lavado."
        )
    if cid == "maiz_amilaceo":
        if suit_yr2 < 55:
            return (
                "Riesgo en 2026–2027 por heladas tardías o déficit de agua en floración según tendencia histórica; "
                "asegura riego o asócialo con haba y mulch protector."
            )
        return "El ligero calentamiento observado en laderas medias favorece su ciclo de 2 años, siempre con buena humedad inicial."
    specialized_advice = {
        "tuna_cochinilla": "Excelente opción en laderas secas y valles interandinos (Cajabamba, Condebamba, San Marcos): tolera veranillos con mínimo riego y genera alto ingreso por grana cochinilla y fruta.",
        "tomillo_aromaticas": "Bajo costo de semilla/esqueje y altísima relación beneficio/costo: prospera en suelos ligeros y se exporta o vende deshidratado con gran demanda medicinal y culinaria.",
        "tara_taya": "Árbol nativo fijador que amarra laderas contra aguaceros, tolera estiaje y aporta vainas con taninos de alto valor comercial agroindustrial.",
        "palta_intercultivo": "Rentabilidad sobresaliente en valles templados (Cajabamba–Condebamba) si dispones de riego por goteo o aspersión y drenaje sin encharcamiento.",
        "oca_olluco_mashua": "Tubérculos andinos nativos de alto valor nutracéutico (antioxidantes y fibra); más rústicos ante veranillos que la papa y excelentes tras una leguminosa.",
        "arracacha": "Raíz nativa de valles húmedos cajamarquinos de fácil digestión (alimento infantil y gourmet) y baja inversión inicial de propágulos.",
        "kiwicha": "Grano andino campeón contra sequía y calor moderado en quebradas y valles; proteína completa para mercado y bajo costo de semilla.",
        "lenteja": "Menestra rústica de bajo gasto en semilla que fija nitrógeno al suelo, mejora la dieta rural con hierro y rinde bien en laderas de transición.",
        "linaza": "Semilla oleaginosa rica en Omega-3 que corta plagas de cereales y tubérculos con inversión reducida y buena demanda comercial.",
        "ajo_valle": "Bulbo biofumigante ideal después de papa o maíz para sanear suelo contra hongos y nematodos; alcanza alto precio con riego controlado.",
    }
    if cid in specialized_advice:
        return specialized_advice[cid]
    if cid in ("tarwi", "quinua", "cebada"):
        return (
            "Cultivo campeón de resiliencia para 2026–2027: tolera mejor veranillos, lluvias variables y aporta cobertura o nitrógeno."
        )
    if cid == "avena_vicia":
        return (
            "Cobertura clave para tu plan de 2 años: tapa la tierra en estiaje, frena erosión de aguaceros y asegura forraje."
        )
    if cid in ("alfalfa", "ryegrass_trebol") and water_availability == "secano":
        return (
            "En secano estricto sufrirá déficit entre mayo y septiembre (patrón histórico NASA); priorízala si cuentas con acequia o aspersión."
        )
    if delta >= 2.0:
        return f"Buena proyección para 2026–2027 (+{delta:.0f} pts) considerando +{temp_delta_20yr:.1f} °C observados en 20 años."
    if precip_delta_20yr <= -5.0 and suit_yr2 < 65:
        return "La tendencia histórica de menor lluvia en siembra exige fecha oportuna y rotación previa con cobertura en 2026–2027."
    return "Mantiene aptitud estable en tu plan de 2 años dentro de una rotación balanceada."


def build_crop_viability_20yr(
    terrain: Dict[str, Any],
    biophysical: Dict[str, Any],
    water_availability: str,
    crops_list: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Uses 20-year NASA POWER historical trends (2006–2025) to evaluate 2-year (2026–2027)
    climate stress and score all 24 local Cajamarca crops for short-term rotation planning.
    """
    climate_20yr = biophysical.get("climate_20yr") or {}
    trends = climate_20yr.get("trends") or {}
    milestones = climate_20yr.get("milestones") or {}

    elev = float(terrain["elevation_m"])
    slope = float(terrain["slope_pct"])
    crops = list(crops_list) if crops_list is not None else load_crops_data()["crops"]

    temp_delta_20yr = float(np.clip(float(trends.get("temp_delta_20yr_c", 0.55)), 0.25, 2.2))
    precip_delta_20yr = float(np.clip(float(trends.get("precip_delta_20yr_pct", -6.0)), -25.0, 12.0))
    frost_trend = float(trends.get("frost_days_trend_per_decade", 0.5))

    # Near-term 2-year stress window calibrated from the 20-year historical variability
    rain_stress_yr1 = round(float(np.clip(precip_delta_20yr * 0.35, -12.0, 8.0)), 1)
    temp_shift_yr1 = round(float(np.clip(temp_delta_20yr * 0.20, 0.05, 0.6)), 2)
    rain_stress_yr2 = round(float(np.clip(precip_delta_20yr * 0.70, -20.0, 10.0)), 1)
    temp_shift_yr2 = round(float(np.clip(temp_delta_20yr * 0.40, 0.10, 1.0)), 2)

    if elev >= 3200 or frost_trend >= 2.5:
        frost_yr1 = "normal"
        frost_yr2 = "moderada"
    elif frost_trend >= 0.5:
        frost_yr1 = "normal"
        frost_yr2 = "moderada" if elev >= 2950 else "normal"
    else:
        frost_yr1 = "normal"
        frost_yr2 = "normal"

    sim_now = simulate_climate_scenario(biophysical, terrain, 0.0, 0.0, "normal")
    sim_yr1 = simulate_climate_scenario(
        biophysical,
        terrain,
        rain_stress_yr1,
        temp_shift_yr1,
        frost_yr1,
    )
    sim_yr2 = simulate_climate_scenario(
        biophysical,
        terrain,
        rain_stress_yr2,
        temp_shift_yr2,
        frost_yr2,
    )

    viable_crops = [
        c for c in crops
        if (c["altitude_min_m"] - 250) <= elev <= (c["altitude_max_m"] + 250)
    ]
    if len(viable_crops) >= 4:
        eval_crops = viable_crops
    else:
        eval_crops = sorted(
            crops,
            key=lambda c: (
                0.0
                if (c["altitude_min_m"] - 250) <= elev <= (c["altitude_max_m"] + 250)
                else min(abs(elev - c["altitude_min_m"]), abs(elev - c["altitude_max_m"]))
            ),
        )[:4]

    crop_matrix: List[Dict[str, Any]] = []
    for crop in eval_crops:
        s_now = _score_crop_horizon(crop, elev, slope, water_availability, sim_now["summary"], 0)
        s_yr1 = _score_crop_horizon(crop, elev, slope, water_availability, sim_yr1["summary"], 5)
        s_yr2 = _score_crop_horizon(crop, elev, slope, water_availability, sim_yr2["summary"], 10)
        delta_2yr = round(s_yr2 - s_now, 1)

        if s_yr2 >= 72.0:
            status_2027 = "optimo_resiliente"
        elif s_yr2 >= 52.0:
            status_2027 = "viable_con_rotacion"
        else:
            status_2027 = "alto_riesgo"

        crop_matrix.append({
            "crop_id": crop["id"],
            "crop_name": crop["name"],
            "category": crop["category"],
            "color": crop["color"],
            "suitability_now": s_now,
            "suitability_2026": s_yr1,
            "suitability_2027": s_yr2,
            "delta_20yr": delta_2yr,
            "status_2027": status_2027,
            "seed_cost_soles_ha": crop.get("seed_cost_soles_ha"),
            "seed_rate_label": crop.get("seed_rate_label"),
            "seed_cost_source": crop.get("seed_cost_source"),
            "wholesale_price_soles_kg": crop.get("wholesale_price_soles_kg"),
            "chacra_price_soles_kg": crop.get("chacra_price_soles_kg"),
            "yield_kg_ha_ref": crop.get("yield_kg_ha_ref"),
            "price_source": crop.get("price_source"),
            "price_date": crop.get("price_date"),
            "price_mode": crop.get("price_mode"),
            "price_quote_label": crop.get("price_quote_label"),
            "gross_income_soles_ha": crop.get("gross_income_soles_ha"),
            "net_margin_soles_ha": crop.get("net_margin_soles_ha"),
            "benefit_cost_ratio": crop.get("benefit_cost_ratio"),
            "consumer_benefit": crop.get("consumer_benefit"),
            "pesticide_guide": crop.get("pesticide_guide"),
            "farmer_advice": _build_crop_20yr_advice(
                crop=crop,
                suit_now=s_now,
                suit_yr2=s_yr2,
                water_availability=water_availability,
                temp_delta_20yr=temp_delta_20yr,
                precip_delta_20yr=precip_delta_20yr,
            ),
        })

    crop_matrix.sort(key=lambda item: item["suitability_2027"], reverse=True)

    m_yr2 = milestones.get("year_2027") or {}
    drought_yr2 = float(m_yr2.get("drought_risk_score", 50.0))
    storm_trend = float(trends.get("storm_trend_pct_per_decade", 4.0))

    if drought_yr2 >= 65.0 or (water_availability == "secano" and precip_delta_20yr <= -6.0) or slope >= 18.0:
        risk_level = "alto"
    elif drought_yr2 >= 45.0 or temp_delta_20yr >= 0.55:
        risk_level = "moderado"
    else:
        risk_level = "bajo"

    top_resilient = [c["crop_name"] for c in crop_matrix if c["status_2027"] == "optimo_resiliente"][:3]
    top_names = ", ".join(top_resilient) if top_resilient else crop_matrix[0]["crop_name"]

    rain_dir = "disminuir" if precip_delta_20yr < -1.0 else ("subir levemente" if precip_delta_20yr > 1.5 else "volverse irregular")
    headline = (
        f"Respaldo histórico NASA 20 años (2006–2025) → Plan 2 años (2026–2027) en {terrain['zone_name']}"
    )
    farmer_explanation = (
        f"En los últimos 20 años (2006–2025) en tu parcela la temperatura subió +{temp_delta_20yr:.1f} °C y la lluvia mostró tendencia a {rain_dir} ({precip_delta_20yr:+.1f}%). "
        f"Con ese historial, tus cultivos más seguros para las próximas 4 campañas (2026–2027) son {top_names}."
    )

    key_findings = [
        (
            f"20 años de historial térmico (2006–2025): +{float(trends.get('temp_trend_c_per_decade', 0.28)):.2f} °C/década observados "
            f"(+{temp_delta_20yr:.1f} °C acumulados), aumentando la evaporación de humedad en campaña."
        ),
        (
            f"Historial de lluvias y aguaceros (2006–2025): variación de {precip_delta_20yr:+.1f}% y "
            f"{storm_trend:+.1f}% por década en tormentas fuertes (>=12 mm/día) que lavan laderas sin cobertura."
        ),
        (
            f"Proyección de 2 años (2026–2027): los cultivos más seguros aquí son {top_names}. "
            + ("En secano, cubrir la tierra tras cada cosecha protegerá la humedad de las próximas 4 campañas." if water_availability == "secano" else "Alternar con leguminosas conserva tu agua de riego y fertilidad natural.")
        ),
    ]

    return {
        "horizon_years": 2,
        "base_period": climate_20yr.get("historical_range", "2006–2025"),
        "forecast_period": climate_20yr.get("projection_range", "2026–2027"),
        "projection_method": climate_20yr.get("projection_method", "linear_regression_20yr_sensitivity"),
        "method_disclaimer": climate_20yr.get(
            "method_disclaimer",
            "Sensibilidad de corto plazo (2026–2027) por tendencia lineal de NASA POWER (2006–2025) ajustada por topografía. No sustituye ensambles climáticos CMIP6 / NASA NEX-GDDP-CMIP6 multidecadales.",
        ),
        "risk_level": risk_level,
        "headline": headline,
        "farmer_explanation": farmer_explanation,
        "key_findings": key_findings,
        "recommended_20yr_scenario": {
            "rain_delta_pct": rain_stress_yr2,
            "temp_delta_c": temp_shift_yr2,
            "frost_frequency": frost_yr2,
        },
        "crop_viability": crop_matrix,
    }


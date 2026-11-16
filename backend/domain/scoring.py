"""Multi-criteria agronomy suitability scoring, timeline expansion, and explainability builders."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from domain.catalog import (
    MONTHS_ES,
    SPECIAL_PHASE_STATES,
    _botanical_family,
)
from domain.climate import _crop_climate_fit, _effective_water_supply_mm


def _resolve_phase_visuals(
    cid: str,
    crops_map: Dict[str, Dict[str, Any]],
    is_cover_flag: bool = False,
) -> Tuple[str, str, str, str, bool]:
    """
    Returns (crop_name, scientific_name, color, status, is_bare) uniformly for
    any crop ID or SPECIAL_PHASE_STATES token.
    """
    if cid in SPECIAL_PHASE_STATES:
        sp = SPECIAL_PHASE_STATES[cid]
        return (
            sp["name"],
            sp["scientific_name"],
            sp["color"],
            sp["status"],
            bool(sp["is_bare"]),
        )
    crop_obj = crops_map[cid]
    return (
        crop_obj["name"],
        crop_obj["scientific_name"],
        crop_obj["color"],
        "cover" if is_cover_flag else "crop",
        False,
    )


def _build_24m_timeline(
    phases: List[Dict[str, Any]],
    crops_map: Dict[str, Dict[str, Any]],
    season_anchor: Dict[str, Any],
    tail_phase: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Expands the 4 chronological seasonal phases (+ optional tail chunk) across 24 consecutive
    calendar months starting from the reference date.
    """
    cal_24: List[Tuple[int, int]] = season_anchor["cal_24"]
    chunks: List[Dict[str, Any]] = season_anchor["chunks"]

    months_24: List[Dict[str, Any]] = []
    for m_idx, (yr, mo) in enumerate(cal_24):
        ph = phases[3]
        for ch_idx, ch in enumerate(chunks):
            if ch["start_idx"] <= m_idx <= ch["end_idx"]:
                if ch_idx < 4:
                    ph = phases[ch_idx]
                elif tail_phase is not None:
                    ph = tail_phase
                else:
                    ph = phases[ch_idx % 4]
                break

        cid = ph["crop_id"]
        name, _, color, status, is_bare = _resolve_phase_visuals(
            cid, crops_map, bool(ph.get("is_cover"))
        )
        short_yr = str(yr)[-2:]
        months_24.append({
            "index": m_idx + 1,
            "cal_month_idx": mo,
            "year": yr,
            "label": f"{MONTHS_ES[mo - 1]} '{short_yr}",
            "is_current_month": m_idx == 0,
            "phase_name": ph["phase_name"],
            "crop_id": cid,
            "crop_name": name,
            "color": color,
            "status": status,
            "is_bare": is_bare,
        })
    return months_24


def _farmer_constraints_fit(
    crop: Dict[str, Any],
    slope_pct: float,
    equipment_access: str,
    market_preference: str,
    farmer_soil: Dict[str, Any],
) -> float:
    """
    Adjusts crop suitability (centered around 0 delta, clamped [-28, +22]) using real farmer
    constraints requested by the challenge: equipment limitations, market preferences, and
    ground-truth soil acidity / drainage / compaction observed by the farmer.
    """
    cid = crop["id"]
    delta = 0.0

    # 1. Equipment & labor realities
    if equipment_access == "manual_yunta":
        if cid in ("papa", "maiz_amilaceo", "haba", "tarwi", "avena_vicia", "oca_olluco_mashua", "arracacha", "lenteja", "tuna_cochinilla", "tomillo_aromaticas", "tara_taya"):
            delta += 5.0
        elif cid in ("trigo", "quinua") and slope_pct >= 16.0:
            delta -= 6.0  # manual harvesting/threshing on steep slopes adds labor cost
    elif equipment_access == "mecanizado":
        if slope_pct >= 18.0:
            delta -= 8.0  # tractors cannot operate safely on steep Andean slopes
        elif cid in ("trigo", "cebada", "quinua", "avena_vicia", "linaza", "kiwicha"):
            delta += 6.0

    # 2. Market preference / destination of harvest & seed-cost efficiency
    if market_preference == "leche_forraje":
        if cid in ("alfalfa", "ryegrass_trebol", "avena_vicia", "maiz_amilaceo"):
            delta += 14.0
        elif cid in ("cebada", "haba"):
            delta += 3.0  # straw & stover feed value
        elif cid in ("papa", "quinua", "ajo_valle"):
            delta -= 7.0
    elif market_preference == "grano_comercial":
        if cid in ("tuna_cochinilla", "tomillo_aromaticas", "palta_intercultivo", "tara_taya", "kiwicha", "ajo_valle"):
            delta += 12.0
        elif cid in ("quinua", "haba", "trigo", "papa", "tarwi", "lenteja", "linaza"):
            delta += 9.0
        elif cid in ("ryegrass_trebol", "alfalfa"):
            delta -= 9.0
    else:  # autoconsumo_feria
        if cid in ("papa", "maiz_amilaceo", "haba", "tarwi", "cebada", "oca_olluco_mashua", "arracacha", "lenteja", "linaza"):
            delta += 7.0
        elif cid in ("tomillo_aromaticas", "kiwicha"):
            delta += 5.0

    # Low seed-cost / high B:C economy boost (favor affordable annual rotation seeds)
    seed_cost = float(crop.get("seed_cost_soles_ha", 700))
    bc_ratio = float(crop.get("benefit_cost_ratio", 1.7))
    if seed_cost <= 550 and bc_ratio >= 2.0:
        delta += 4.5
    elif bc_ratio >= 2.2:
        delta += 3.0

    # 3. Ground-truth farmer soil observations (pH / drainage / compaction / texture / local frost)
    acidity = str(farmer_soil.get("soil_acidity", "normal"))
    cond = str(farmer_soil.get("compaction_or_drainage", "normal"))
    tex = str(farmer_soil.get("texture_override", "auto"))
    frost_note = bool(farmer_soil.get("local_frost_early") or farmer_soil.get("frost_risk_note"))

    if acidity == "acido":
        if cid in ("tarwi", "papa", "avena_vicia", "quinua", "ryegrass_trebol", "oca_olluco_mashua", "linaza", "tomillo_aromaticas"):
            delta += 9.0
        elif cid in ("alfalfa", "cebada", "ajo_valle"):
            delta -= 18.0  # alfalfa & barley yield drops sharply below pH 5.5 without liming

    if cond == "duro_compactado":
        if crop["root_depth_cm"] >= 100:
            delta += 12.0  # tarwi, tara & alfalfa act as biological subsoilers
        elif cid in ("papa", "cebada", "ajo_valle"):
            delta -= 8.0
    elif cond == "se_encharca":
        if cid in ("ryegrass_trebol", "haba", "avena_vicia"):
            delta += 10.0
        elif cid in ("tarwi", "alfalfa", "palta_intercultivo", "tuna_cochinilla", "papa"):
            delta -= 15.0  # anthracnose & root rot risk in waterlogged soils

    if tex in ("franco_arenoso", "pedregoso"):
        if cid in ("tuna_cochinilla", "tara_taya", "tomillo_aromaticas", "quinua", "tarwi", "linaza"):
            delta += 7.5
        elif crop["drought_tolerance"] >= 75:
            delta += 5.0
        elif cid in ("papa", "alfalfa"):
            delta -= 8.0
    elif tex == "arcilloso_pesado":
        if cid in ("haba", "ryegrass_trebol", "avena_vicia", "maiz_amilaceo", "tarwi"):
            delta += 7.0
        elif cid in ("papa", "ajo_valle", "arracacha"):
            delta -= 8.5

    if frost_note:
        if cid in ("quinua", "tarwi", "cebada", "avena_vicia", "ryegrass_trebol", "oca_olluco_mashua"):
            delta += 8.0
        elif float(crop.get("frost_critical_c", 0.0)) >= 0.0:
            delta -= 10.5

    return float(np.clip(delta, -28.0, 24.0))


def _rotation_context_fit(
    cid: str,
    crop: Dict[str, Any],
    current_crop: str,
    water_availability: str,
    farmer_soil: Dict[str, Any],
    elev: float,
    slope: float,
    viable_seed_set: set[str],
    water_p: float,
) -> float:
    """
    Applies seasonal crop-rotation compatibility: keeps long-cycle woody/cactus perennials
    out of short seasonal campaign slots unless matching marginal rocky secano slopes or explicit seeds,
    and sharply differentiates candidates by previous crop, irrigation system, and field soil state.
    """
    delta = 0.0
    tex = str(farmer_soil.get("texture_override", "auto"))
    cond = str(farmer_soil.get("compaction_or_drainage", "normal"))
    acidity = str(farmer_soil.get("soil_acidity", "normal"))
    frost_note = bool(farmer_soil.get("local_frost_early") or farmer_soil.get("frost_risk_note"))

    # 1) Long-cycle woody trees / cactus / orchards should not dominate seasonal crop slots everywhere
    if cid not in viable_seed_set:
        if cid in ("tara_taya", "tuna_cochinilla"):
            marginal_slope = (water_availability == "secano") and (
                slope >= 14.0 or tex in ("pedregoso", "franco_arenoso") or water_p >= 88.0
            )
            if not marginal_slope:
                delta -= 26.0
            else:
                delta += 4.0
        elif cid in ("palta_intercultivo", "cafe", "cacao"):
            warm_irrig = elev < 2150.0 and water_availability in ("riego_goteo", "riego_aspersion", "riego_gravedad")
            if not warm_irrig:
                delta -= 24.0

    # 2) Strong agronomic succession from what the farmer grew previously
    if current_crop == "monocultivo_papa":
        if cid in ("avena_vicia", "tarwi", "haba", "quinua", "cebada", "ajo_valle", "arveja"):
            delta += 12.0
        elif cid == "papa" and cid not in viable_seed_set:
            delta -= 28.0
        elif cid == "oca_olluco_mashua":
            delta -= 6.0
    elif current_crop == "papa_maiz":
        if cid in ("tarwi", "haba", "arveja", "lenteja", "quinua", "linaza"):
            delta += 11.0
        elif cid in ("papa", "maiz_amilaceo") and cid not in viable_seed_set:
            delta -= 24.0
    elif current_crop == "cebada_trigo_continuo":
        if cid in ("haba", "tarwi", "arveja", "papa", "oca_olluco_mashua", "ryegrass_trebol", "lenteja"):
            delta += 12.5
        elif cid in ("cebada", "trigo") and cid not in viable_seed_set:
            delta -= 28.0
    elif current_crop == "pastos_degradados":
        if cid in ("papa", "maiz_amilaceo", "avena_vicia", "haba", "alfalfa", "ryegrass_trebol"):
            delta += 11.0
    else:  # sin_cultivo / terreno libre
        if cid in ("quinua", "haba", "tarwi", "arveja", "tomillo_aromaticas", "lenteja"):
            delta += 6.5

    # 3) Irrigation / water system specialization
    if water_availability == "secano":
        if cid in ("quinua", "tarwi", "cebada", "linaza", "kiwicha", "tuna_cochinilla", "tara_taya"):
            delta += 9.5
        elif cid in ("papa", "maiz_amilaceo", "ajo_valle", "alfalfa", "ryegrass_trebol"):
            delta -= 14.0
    elif water_availability in ("cosecha_agua_qocha", "riego_deficitario"):
        if cid in ("haba", "arveja", "maiz_amilaceo", "lenteja", "avena_vicia", "oca_olluco_mashua"):
            delta += 9.5
    elif water_availability in ("riego_gravedad", "riego_melgas_surcos"):
        if cid in ("maiz_amilaceo", "haba", "papa", "alfalfa", "ryegrass_trebol", "arracacha"):
            delta += 10.0
        if water_availability == "riego_melgas_surcos" and cid in ("papa", "maiz_amilaceo", "ajo_valle"):
            delta += 6.5
    elif water_availability == "riego_aspersion":
        if cid in ("ryegrass_trebol", "alfalfa", "arveja", "quinua", "haba", "ajo_valle"):
            delta += 11.0
    elif water_availability == "riego_goteo":
        if cid in ("ajo_valle", "tomillo_aromaticas", "frijol", "papa", "palta_intercultivo", "kiwicha", "arveja"):
            delta += 14.0

    # 4) Extra field observation interactions
    if frost_note:
        if cid in ("quinua", "tarwi", "cebada", "avena_vicia", "oca_olluco_mashua"):
            delta += 8.0
        elif float(crop.get("frost_critical_c", 0.0)) >= 0.0:
            delta -= 11.0
    if cond == "se_encharca" and cid in ("ryegrass_trebol", "haba", "avena_vicia"):
        delta += 7.0
    if acidity == "acido" and cid in ("tarwi", "avena_vicia", "oca_olluco_mashua", "papa"):
        delta += 6.0

    return delta


def _cost_efficiency_bonus(crop: Dict[str, Any]) -> float:
    """Reward low seed investment and high Benefit/Cost ratio across Cajamarca crops."""
    bc = float(crop.get("benefit_cost_ratio", 1.5))
    seed = float(crop.get("seed_cost_soles_ha", 600.0))
    bc_bonus = float(np.clip((bc - 1.5) * 6.5, -4.0, 12.0))
    seed_bonus = float(np.clip((700.0 - seed) / 140.0, -5.0, 4.5))
    return bc_bonus + seed_bonus


def _extract_priority_focus(priorities: Dict[str, float]) -> Dict[str, float]:
    """Compute signed contrast [-1.5..2.2] around mean priority; small <=7 pt spread stays neutral."""
    w = float(priorities.get("water_conservation", 70.0))
    s = float(priorities.get("soil_fertility", 70.0))
    e = float(priorities.get("erosion_control", 70.0))
    p = float(priorities.get("pest_break", 70.0))
    m = float(priorities.get("commercial_forage", 70.0))
    mean_val = (w + s + e + p + m) / 5.0

    def _c(val: float) -> float:
        diff = val - mean_val
        if abs(diff) <= 6.5:
            return 0.0
        return float(np.clip(diff / 12.0, -1.5, 2.2))

    return {
        "water": _c(w),
        "soil": _c(s),
        "erosion": _c(e),
        "pest": _c(p),
        "market": _c(m),
    }


def _crop_priority_bonus(
    cid: str,
    crop: Dict[str, Any],
    focus: Dict[str, float],
) -> float:
    """Score how strongly a candidate crop aligns with the farmer's active priority focus."""
    water_req = float(crop.get("water_req_mm", 450.0))
    drought = float(crop.get("drought_tolerance", 65.0))
    n_bal = float(crop.get("nitrogen_balance_kg_ha", 0.0))
    om_sc = float(crop.get("organic_matter_score", 50.0))
    eros = float(crop.get("erosion_protection_score", 65.0))
    pest = float(crop.get("pest_break_score", 78.0))
    comm = float(crop.get("commercial_forage_value_score", 78.0))
    net_margin = float(crop.get("gross_income_soles_ha", 4800.0)) - float(crop.get("total_cost_soles_ha", 2800.0))

    water_sig = float(np.clip((430.0 - water_req) / 160.0, -1.0, 1.3)) * 12.0 + ((drought - 68.0) / 30.0) * 12.0
    soil_sig = (n_bal / 90.0) * 16.0 + ((om_sc - 55.0) / 35.0) * 8.0
    erosion_sig = ((eros - 68.0) / 30.0) * 13.0
    pest_sig = ((pest - 80.0) / 14.0) * 18.0 + (9.0 if cid in ("ajo_valle", "tomillo_aromaticas", "oca_olluco_mashua", "linaza", "quinua") else 0.0)
    market_sig = float(np.clip((net_margin - 3600.0) / 4800.0, -0.6, 1.15)) * 11.5 + ((comm - 78.0) / 22.0) * 8.5

    return (
        focus["water"] * water_sig
        + focus["soil"] * soil_sig
        + focus["erosion"] * erosion_sig
        + focus["pest"] * pest_sig
        + focus["market"] * market_sig
    )


def _evaluate_strategy_metrics(
    strategy_id: str,
    title: str,
    subtitle: str,
    phases: List[Dict[str, Any]],
    crops_map: Dict[str, Dict[str, Any]],
    terrain: Dict[str, Any],
    biophysical: Dict[str, Any],
    sim_climate: Dict[str, Any],
    water_availability: str,
    priorities: Dict[str, float],
    current_crop: str,
    season_anchor: Dict[str, Any],
    tail_phase: Optional[Dict[str, Any]] = None,
    equipment_access: str = "manual_yunta",
    market_preference: str = "autoconsumo_feria",
    farmer_soil: Dict[str, Any] | None = None,
    baseline_metrics: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    farmer_soil = farmer_soil or {}
    elev = float(terrain["elevation_m"])
    slope = float(terrain["slope_pct"])
    sim_sum = sim_climate["summary"]

    months_24 = _build_24m_timeline(phases, crops_map, season_anchor=season_anchor, tail_phase=tail_phase)
    bare_months_24 = sum(1 for m in months_24 if m["is_bare"])

    # Compute agronomic balances across the 4 chronological phases
    active_crop_ids = [p["crop_id"] for p in phases if p["crop_id"] not in SPECIAL_PHASE_STATES]
    main_crop_ids = [
        p["crop_id"] for p in phases
        if not p.get("is_cover") and p["crop_id"] not in SPECIAL_PHASE_STATES
    ]

    # 1. Nitrogen balance over 24 months (kg/ha) & organic matter score
    n_balance = 0.0
    om_delta = 0.0
    for ph in phases:
        cid = ph["crop_id"]
        dur_factor = max(0.35, float(ph.get("duration_months", 6)) / 6.0)
        if cid in SPECIAL_PHASE_STATES:
            sp = SPECIAL_PHASE_STATES[cid]
            n_balance += float(sp["n_6m"]) * dur_factor
            om_delta += float(sp["om_6m"]) * dur_factor
        else:
            c = crops_map[cid]
            perennial_factor = 0.55 if ph.get("is_perennial_half") else 1.0
            n_balance += float(c["nitrogen_balance_kg_ha"]) * perennial_factor * dur_factor
            om_delta += float(c["organic_matter_score"]) * perennial_factor * dur_factor

    # 2. Water conservation & climate resilience fit
    water_fits = []
    frost_fits = []
    terrain_fits = []
    erosion_protections = []
    commercial_values = []
    pest_breaks = []
    constraint_deltas = []

    for ph in phases:
        cid = ph["crop_id"]
        if cid in SPECIAL_PHASE_STATES:
            sp = SPECIAL_PHASE_STATES[cid]
            erosion_protections.append(float(sp["erosion_prot"]))
            if not sp["is_bare"]:
                water_fits.append(float(sp["water_fit"]))
                frost_fits.append(float(sp["frost_fit"]))
                terrain_fits.append(float(sp["terrain_fit"]))
                commercial_values.append(float(sp["comm_val"]))
                pest_breaks.append(float(sp["pest_break"]))
            continue

        c = crops_map[cid]
        wf, ff, tf = _crop_climate_fit(c, elev, slope, water_availability, sim_sum)
        cf_delta = _farmer_constraints_fit(c, slope, equipment_access, market_preference, farmer_soil)
        constraint_deltas.append(cf_delta)
        water_fits.append(wf)
        frost_fits.append(ff)
        terrain_fits.append(tf)
        erosion_protections.append(float(c["erosion_protection_score"]))
        commercial_values.append(float(np.clip(float(c["commercial_forage_value_score"]) + cf_delta, 18.0, 98.0)))
        pest_breaks.append(float(c["pest_break_score"]))

    avg_constraint_delta = float(np.mean(constraint_deltas)) if constraint_deltas else 0.0

    avg_wf = float(np.mean(water_fits)) if water_fits else 40.0
    avg_ff = float(np.mean(frost_fits)) if frost_fits else 40.0
    avg_tf = float(np.mean(terrain_fits)) if terrain_fits else 50.0
    avg_er_prot = float(np.mean(erosion_protections)) if erosion_protections else 20.0
    avg_comm = float(np.mean(commercial_values)) if commercial_values else 45.0
    avg_pest = float(np.mean(pest_breaks)) if pest_breaks else 25.0

    # Family diversity bonus for pest break
    unique_crops = len(set(active_crop_ids))
    has_legume = any(
        cid in ("tarwi", "haba", "alfalfa", "avena_vicia", "ryegrass_trebol", "lenteja", "frijol", "arveja", "tara_taya")
        for cid in active_crop_ids
    )
    has_cover = any(p.get("is_cover") for p in phases)
    no_solanaceae_repeat = main_crop_ids.count("papa") <= 1

    # Dimension scores (0 - 100)
    acidity = str(farmer_soil.get("soil_acidity", "normal"))
    cond = str(farmer_soil.get("compaction_or_drainage", "normal"))
    tex = str(farmer_soil.get("texture_override", "auto"))
    frost_note = bool(farmer_soil.get("local_frost_early") or farmer_soil.get("frost_risk_note"))

    # 1) Water Conservation (reflects crop water needs + irrigation efficiency + soil water retention)
    water_req_avg = float(np.mean([crops_map[c]["water_req_mm"] for c in active_crop_ids])) if active_crop_ids else 550.0
    drought_tol_avg = float(np.mean([crops_map[c]["drought_tolerance"] for c in active_crop_ids])) if active_crop_ids else 35.0
    water_efficiency_bonus = np.clip((490.0 - water_req_avg) / 240.0 * 22.0, -20.0, 14.0)
    resilience_strategy_shield = 2.0 if strategy_id == "resilience" else 0.0
    irrig_water_delta = {
        "secano": -6.5,
        "cosecha_agua_qocha": -0.5,
        "riego_deficitario": 1.5,
        "riego_gravedad": 3.0,
        "riego_melgas_surcos": 4.5,
        "riego_aspersion": 6.5,
        "riego_goteo": 8.5,
    }.get(water_availability, 0.0)
    tex_water_delta = -5.5 if tex in ("franco_arenoso", "pedregoso") else (3.5 if tex == "arcilloso_pesado" else 0.0)
    cond_water_delta = -5.5 if cond == "duro_compactado" else (-2.5 if cond == "se_encharca" else 0.0)
    score_water = float(np.clip(
        0.34 * avg_wf + 0.30 * drought_tol_avg + 0.12 * avg_ff
        + water_efficiency_bonus + resilience_strategy_shield + irrig_water_delta
        + tex_water_delta + cond_water_delta + (3.0 if has_cover else -10.0),
        12.0, 92.0,
    ))

    # 2) Soil Fertility & Nitrogen (sensitive to legumes, previous exhaustion, acidity, drainage)
    n_norm = float(np.clip((n_balance + 200.0) / 440.0, 0.0, 1.0))
    om_norm = float(np.clip((om_delta + 35.0) / 125.0, 0.0, 1.0))
    history_fert_delta = {
        "monocultivo_papa": -8.5,
        "cebada_trigo_continuo": -7.5,
        "pastos_degradados": -5.0,
        "papa_maiz": -2.5,
        "sin_cultivo": 2.0,
    }.get(current_crop, 0.0)
    soil_fert_delta = (-8.5 if acidity == "acido" else 0.0) + (-7.5 if cond == "duro_compactado" else (-6.5 if cond == "se_encharca" else 0.0))
    if tex == "pedregoso":
        soil_fert_delta -= 6.5
    elif tex == "franco_arenoso":
        soil_fert_delta -= 3.5
    score_fertility = float(np.clip(12.0 + n_norm * 60.0 + om_norm * 16.0 + history_fert_delta + soil_fert_delta, 10.0, 91.0))

    # 3) Erosion Control (heavily penalized by bare soil months & steep slopes)
    bare_penalty = bare_months_24 * (3.6 + (slope / 12.0) * 2.4)
    rain_erosion_penalty = float(sim_sum["erosion_stress_index"]) * (0.28 if bare_months_24 > 2 else 0.08)
    irrig_erosion_bonus = {
        "riego_goteo": 6.0,
        "riego_aspersion": 4.5,
        "riego_melgas_surcos": 4.0,
        "cosecha_agua_qocha": 3.5,
    }.get(water_availability, 0.0)
    score_erosion = float(np.clip(avg_er_prot * 0.90 + (7.0 if has_cover else -5.0) + irrig_erosion_bonus - bare_penalty - rain_erosion_penalty * 0.35, 10.0, 93.0))

    # 4) Pest Cycle Break (sensitive to previous crop family continuity & drainage rot)
    prev_family_match = (
        (current_crop == "monocultivo_papa" and "papa" in main_crop_ids)
        or (current_crop == "papa_maiz" and any(c in ("papa", "maiz_amilaceo") for c in main_crop_ids))
        or (current_crop == "cebada_trigo_continuo" and any(c in ("cebada", "trigo") for c in main_crop_ids))
    )
    diversity_bonus = (unique_crops - 1) * 7.0 + (7.5 if no_solanaceae_repeat else -22.0) + (7.5 if has_legume else 0.0)
    if prev_family_match:
        diversity_bonus -= 18.0
    elif current_crop != "sin_cultivo" and strategy_id != "baseline":
        diversity_bonus += 4.5
    if cond == "se_encharca":
        diversity_bonus -= 8.0
    score_pest = float(np.clip(avg_pest * 0.74 + diversity_bonus, 8.0, 93.0))

    # 5) Commercial & Forage Value (adjusted by climate failure risk and local frost exposure)
    climate_survival_factor = float(np.clip((0.45 * avg_wf + 0.35 * avg_ff + 0.20 * avg_tf) / 100.0, 0.35, 1.0))
    cover_forage_bonus = 6.0 if "avena_vicia" in active_crop_ids else 0.0
    frost_comm_penalty = -5.5 if frost_note else 0.0
    score_commercial = float(np.clip(avg_comm * (0.52 + 0.48 * climate_survival_factor) + cover_forage_bonus + frost_comm_penalty, 18.0, 93.0))

    # 6) 2-Year Seed Costs, Net Margin, Benefit/Cost & Integrated Pest Management (IPM) Schedule
    seed_cost_2yr = 0.0
    total_cost_2yr = 0.0
    gross_income_2yr_raw = 0.0
    pesticide_schedule: List[Dict[str, Any]] = []
    seen_pest_crops = set()

    for ph in phases:
        cid = ph["crop_id"]
        if cid in SPECIAL_PHASE_STATES:
            sp = SPECIAL_PHASE_STATES[cid]
            if not sp.get("is_bare"):
                total_cost_2yr += 420.0 if cid == "pasto_degradado" else 260.0
                gross_income_2yr_raw += 680.0 if cid == "pasto_degradado" else 340.0
            else:
                total_cost_2yr += 150.0
            continue

        c = crops_map[cid]
        perennial_factor = 0.5 if ph.get("is_perennial_half") else 1.0
        seed_cost_2yr += float(c.get("seed_cost_soles_ha", 450.0)) * perennial_factor
        total_cost_2yr += float(c.get("total_cost_soles_ha", 2800.0)) * perennial_factor
        gross_income_2yr_raw += float(c.get("gross_income_soles_ha", 4800.0)) * perennial_factor

        pg = c.get("pesticide_guide") or {}
        if pg and cid not in seen_pest_crops:
            seen_pest_crops.add(cid)
            pesticide_schedule.append({
                "phase_name": ph["phase_name"],
                "period": ph["period"],
                "crop_id": cid,
                "crop_name": c["name"],
                "target_pests": pg.get("target_pests", ""),
                "bio_control": pg.get("bio_control", ""),
                "chemical_control": pg.get("chemical_control", ""),
                "when_to_apply": pg.get("when_to_apply", ""),
                "pre_harvest_interval_days": int(pg.get("pre_harvest_interval_days", 0)),
                "consumer_benefit": c.get("consumer_benefit", ""),
            })

    gross_income_2yr = gross_income_2yr_raw * (0.74 + 0.26 * climate_survival_factor)
    net_margin_2yr = gross_income_2yr - total_cost_2yr
    benefit_cost_ratio = round(gross_income_2yr / max(total_cost_2yr, 1.0), 2)

    # Refine commercial score with actual 2-year net margin performance
    margin_norm_score = float(np.clip(48.0 + (net_margin_2yr - 2500.0) / 360.0, 22.0, 96.0))
    if strategy_id != "baseline":
        score_commercial = float(np.clip(0.62 * score_commercial + 0.38 * margin_norm_score, 18.0, 95.0))

    # Normalized Priority Weights (non-linear contrast so dominant farmer priorities genuinely drive winner)
    w_raw = np.array([
        float(priorities.get("water_conservation", 70)),
        float(priorities.get("soil_fertility", 70)),
        float(priorities.get("erosion_control", 70)),
        float(priorities.get("pest_break", 70)),
        float(priorities.get("commercial_forage", 70)),
    ], dtype=float)
    if np.sum(w_raw) <= 0:
        w_norm = np.ones(5) / 5.0
    else:
        w_contrast = np.power(np.maximum(w_raw, 1.0), 2.5)
        w_norm = w_contrast / np.sum(w_contrast)

    dim_vec = np.array([score_water, score_fertility, score_erosion, score_pest, score_commercial], dtype=float)
    strategy_alignment_bonus = 0.0
    if strategy_id == "resilience" and w_raw[0] >= max(w_raw[1], w_raw[3], w_raw[4]) + 10.0:
        strategy_alignment_bonus = 2.8
    elif strategy_id == "regenerative" and max(w_raw[1], w_raw[3], w_raw[4]) >= w_raw[0] + 10.0:
        strategy_alignment_bonus = 3.2
    mcda_score = float(np.clip(np.dot(w_norm, dim_vec) * 0.96 + avg_constraint_delta * 0.22 + strategy_alignment_bonus, 12.0, 96.0))

    # Vulnerability score (0-100, higher = worse risk under simulated climate)
    climate_hazard_load = (
        0.40 * float(sim_sum["drought_stress_index"])
        + 0.32 * float(sim_sum["frost_stress_index"])
        + 0.28 * float(sim_sum["erosion_stress_index"])
    )
    resilience_capacity = 0.35 * score_water + 0.30 * score_erosion + 0.20 * score_fertility + 0.15 * avg_ff
    vulnerability_score = float(np.clip(0.55 * climate_hazard_load + 0.65 * (100.0 - resilience_capacity) - 10.0, 8.0, 96.0))

    # Quantified relative benefits vs Baseline
    if baseline_metrics is None:
        water_savings_pct = 0.0
        erosion_reduction_pct = 0.0
        bare_months_avoided = 0
        pest_reduction_pct = 0.0
    else:
        base_req = max(250.0, baseline_metrics["water_req_avg"])
        water_savings_pct = round(float(np.clip(((base_req - water_req_avg) / base_req) * 100.0 + (8.0 if has_cover else 0.0), 0.0, 48.0)), 1)
        base_erosion_vuln = max(15.0, 100.0 - baseline_metrics["score_erosion"])
        cur_erosion_vuln = max(2.0, 100.0 - score_erosion)
        erosion_reduction_pct = round(float(np.clip(((base_erosion_vuln - cur_erosion_vuln) / base_erosion_vuln) * 100.0, 0.0, 92.0)), 1)
        bare_months_avoided = max(0, int(baseline_metrics["bare_months_24"] - bare_months_24))
        pest_reduction_pct = round(float(np.clip(score_pest - baseline_metrics["score_pest"], 0.0, 88.0)), 1)

    # Generate 4 Mandatory Explainability Blocks
    explainability = _build_explainability_blocks(
        strategy_id=strategy_id,
        title=title,
        phases=phases,
        crops_map=crops_map,
        terrain=terrain,
        biophysical=biophysical,
        sim_climate=sim_climate,
        water_availability=water_availability,
        priorities=priorities,
        current_crop=current_crop,
        season_anchor=season_anchor,
        n_balance=n_balance,
        water_savings_pct=water_savings_pct,
        erosion_reduction_pct=erosion_reduction_pct,
        bare_months_avoided=bare_months_avoided,
        pest_reduction_pct=pest_reduction_pct,
        vulnerability_score=vulnerability_score,
        bare_months_24=bare_months_24,
        om_delta=om_delta,
        equipment_access=equipment_access,
        market_preference=market_preference,
        farmer_soil=farmer_soil,
    )

    serialized_phases = []
    for p in phases:
        cname, sciname, pcolor, _, _ = _resolve_phase_visuals(
            p["crop_id"], crops_map, bool(p.get("is_cover"))
        )
        serialized_phases.append({
            "phase_name": p["phase_name"],
            "period": p["period"],
            "crop_id": p["crop_id"],
            "crop_name": cname,
            "scientific_name": sciname,
            "role": p["role"],
            "is_cover": bool(p.get("is_cover", False)),
            "color": pcolor,
        })

    return {
        "id": strategy_id,
        "title": title,
        "subtitle": subtitle,
        "mcda_score": round(mcda_score, 1),
        "vulnerability_score": round(vulnerability_score, 1),
        "vulnerability_level": (
            "Crítica" if vulnerability_score >= 68
            else ("Moderada-Alta" if vulnerability_score >= 48
                  else ("Moderada-Baja" if vulnerability_score >= 30 else "Baja (Resiliente)"))
        ),
        "radar_scores": {
            "water_conservation": round(score_water, 1),
            "soil_fertility": round(score_fertility, 1),
            "erosion_control": round(score_erosion, 1),
            "pest_break": round(score_pest, 1),
            "commercial_forage": round(score_commercial, 1),
        },
        "metrics": {
            "nitrogen_balance_kg_ha": round(n_balance, 0),
            "organic_matter_score": round(om_delta, 0),
            "bare_soil_months_24m": bare_months_24,
            "water_savings_pct": water_savings_pct,
            "erosion_reduction_pct": erosion_reduction_pct,
            "bare_months_avoided": bare_months_avoided,
            "pest_break_improvement_pct": pest_reduction_pct,
            "water_req_avg_mm": round(water_req_avg, 0),
            "seed_cost_2yr_soles_ha": round(seed_cost_2yr, 0),
            "total_cost_2yr_soles_ha": round(total_cost_2yr, 0),
            "net_margin_2yr_soles_ha": round(net_margin_2yr, 0),
            "benefit_cost_ratio": benefit_cost_ratio,
        },
        "phases": serialized_phases,
        "pesticide_schedule": pesticide_schedule,
        "timeline_24m": months_24,
        "explainability": explainability,
        "_internal": {
            "water_req_avg": water_req_avg,
            "score_erosion": score_erosion,
            "score_pest": score_pest,
            "bare_months_24": bare_months_24,
        },
    }


def _build_explainability_blocks(
    strategy_id: str,
    title: str,
    phases: List[Dict[str, Any]],
    crops_map: Dict[str, Dict[str, Any]],
    terrain: Dict[str, Any],
    biophysical: Dict[str, Any],
    sim_climate: Dict[str, Any],
    water_availability: str,
    priorities: Dict[str, float],
    current_crop: str,
    season_anchor: Dict[str, Any],
    n_balance: float,
    water_savings_pct: float,
    erosion_reduction_pct: float,
    bare_months_avoided: int,
    pest_reduction_pct: float,
    vulnerability_score: float,
    bare_months_24: int,
    om_delta: float = 0.0,
    equipment_access: str = "manual_yunta",
    market_preference: str = "autoconsumo_feria",
    farmer_soil: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    farmer_soil = farmer_soil or {}
    bio_sum = biophysical["summary"]
    sim_sum = sim_climate["summary"]
    sim_p = sim_climate["params"]

    equip_lbl = {
        "manual_yunta": "yunta / trabajo familiar",
        "tractor_compartido": "tractor o trilla alquilada",
        "mecanizado": "maquinaria completa",
    }.get(equipment_access, equipment_access)
    market_lbl = {
        "autoconsumo_feria": "comida de casa y feria local",
        "leche_forraje": "pasto y venta de leche/ganado",
        "grano_comercial": "venta comercial de grano/tubérculo",
    }.get(market_preference, market_preference)

    soil_notes_parts: List[str] = []
    if terrain.get("soil_source") == "reportado_agricultor":
        soil_notes_parts.append(f"textura declarada en campo ({terrain['soil_texture']})")
    if farmer_soil.get("soil_acidity") == "acido":
        soil_notes_parts.append("suelo ácido reportado (se evita exigir alfalfa sin encalado)")
    if farmer_soil.get("compaction_or_drainage") == "duro_compactado":
        soil_notes_parts.append("suelo duro/compactado (prioridad a raíz profunda)")
    elif farmer_soil.get("compaction_or_drainage") == "se_encharca":
        soil_notes_parts.append("tendencia a empozarse en lluvia (se evita tarwi por antracnosis)")
    if farmer_soil.get("local_frost_early"):
        soil_notes_parts.append("helada temprana reportada desde mayo")
    soil_context_str = (
        f" Se ajustó además por lo que indicaste: {'; '.join(soil_notes_parts)}."
        if soil_notes_parts
        else ""
    )

    prio_labels = {
        "water_conservation": "Conservación de agua y resistencia a sequía",
        "soil_fertility": "Recuperación de fertilidad y nitrógeno",
        "erosion_control": "Control de erosión en pendiente",
        "pest_break": "Interrupción de ciclo de plagas",
        "commercial_forage": "Rentabilidad comercial / valor forrajero",
    }
    sorted_prios = sorted(priorities.items(), key=lambda kv: kv[1], reverse=True)
    top1 = f"{prio_labels.get(sorted_prios[0][0], sorted_prios[0][0])} ({int(sorted_prios[0][1])}%)"
    top2 = f"{prio_labels.get(sorted_prios[1][0], sorted_prios[1][0])} ({int(sorted_prios[1][1])}%)"

    water_lbl = {
        "secano": "secano (solo lluvia)",
        "cosecha_agua_qocha": "cosecha de agua (qochas / micro-reservorio)",
        "riego_deficitario": "riego de auxilio / deficitario por turnos",
        "riego_gravedad": "riego parcial por gravedad (acequia)",
        "riego_melgas_surcos": "riego controlado por melgas o surcos",
        "riego_aspersion": "riego por aspersión",
        "riego_goteo": "riego por goteo / fertirriego",
    }.get(water_availability, water_availability)

    main_crops = [
        _resolve_phase_visuals(p["crop_id"], crops_map, False)[0]
        for p in phases
        if not p.get("is_cover") and p["crop_id"] not in SPECIAL_PHASE_STATES
    ]
    cover_name = next(
        (_resolve_phase_visuals(p["crop_id"], crops_map, True)[0] for p in phases if p.get("is_cover") and p["crop_id"] not in SPECIAL_PHASE_STATES),
        "Avena forrajera + Vicia",
    )
    legume_name = next(
        (crops_map[p["crop_id"]]["name"] for p in phases if p["crop_id"] in ("tarwi", "haba", "alfalfa", "ryegrass_trebol", "lenteja", "frijol", "arveja", "tara_taya")),
        main_crops[0] if main_crops else "leguminosa andina",
    )
    main_pair = " y ".join(dict.fromkeys(main_crops)) if main_crops else "cultivos rústicos"
    followup_crop = main_crops[-1] if len(main_crops) >= 2 else (main_crops[0] if main_crops else cover_name)
    season_note = (
        f" Planificado desde {season_anchor['ref_month_label']} "
        f"({season_anchor['season_label'].lower()})."
    )

    bare_list_str = ", ".join(bio_sum["bare_soil_months"]) if bio_sum["bare_soil_months"] else "ninguno"
    frost_list_str = ", ".join(sim_sum["frost_risk_months"]) if sim_sum["frost_risk_months"] else "riesgo bajo"
    storm_list_str = ", ".join(bio_sum["erosive_storm_months"]) if bio_sum["erosive_storm_months"] else "moderadas"

    scenario_tag = ""
    if sim_p["rain_delta_pct"] != 0 or sim_p["temp_delta_c"] != 0 or sim_p["frost_frequency"] != "normal":
        scenario_tag = (
            f" Bajo el escenario simulado (lluvia {sim_p['rain_delta_pct']:+.0f}%, "
            f"temperatura +{sim_p['temp_delta_c']:.1f} °C, heladas '{sim_p['frost_frequency']}'), "
            f"el balance hídrico anual proyectado es {sim_sum['annual_water_balance_mm']:.0f} mm."
        )

    if strategy_id == "baseline":
        hist_label = (
            "terreno libre sin cultivo previo declarado"
            if current_crop == "sin_cultivo"
            else current_crop.replace("_", " ")
        )
        why = (
            f"Representa mantener el estado base ({hist_label}) bajo {water_lbl}.{season_note} "
            + (
                f"Dejar el terreno descubierto durante {bare_months_24} meses en 2 años desperdicia la ventana hídrica y expone la capa arable a erosión."
                if current_crop == "sin_cultivo"
                else (
                    f"Aunque responde a la costumbre comercial inmediata, entra en conflicto con sus dos prioridades principales: "
                    f"{top1} y {top2}, pues mantiene {bare_months_24} meses sin cobertura viva en 2 años y repite familias botánicas susceptibles."
                )
            )
        )
        nasa_ev = (
            f"Los datos climáticos (NASA POWER) registran mínimas de {bio_sum['min_temp_c']} °C en {bio_sum['min_temp_month']} "
            f"(riesgo de helada en {frost_list_str}) y lluvias de {bio_sum['annual_precip_mm']:.0f} mm al año frente a "
            f"un consumo natural de agua por sol y viento (ET0) de {bio_sum['annual_et0_mm']:.0f} mm. Además detecta {bio_sum['bare_soil_month_count']} meses "
            f"con tierra descubierta (NDVI < 0.25 en {bare_list_str}) sobre {terrain['elevation_m']:.0f} m s.n.m. con {terrain['slope_pct']:.1f}% "
            f"de inclinación expuesta a aguaceros ({storm_list_str}).{scenario_tag}"
        )
        benefits_summary = (
            f"Sin ahorro de agua respecto al manejo actual; pérdida estimada de nitrógeno ({n_balance:+.0f} kg/ha en 2 años) "
            f"y riesgo climático de {vulnerability_score:.0f}/100 por sequía, heladas y lavado de tierra fértil."
        )
    elif strategy_id == "resilience":
        why = (
            f"Pensada para priorizar {top1} y {top2} hacia {market_lbl} usando {equip_lbl}, con {water_lbl}.{season_note} "
            f"Combina cultivos resistentes que necesitan menos agua y soportan mejor el frío ({main_pair}), "
            f"e incluye {cover_name} en meses secos para proteger el suelo y dar forraje.{soil_context_str}"
        )
        nasa_ev = (
            f"Los registros satelitales muestran la tierra descubierta (NDVI < 0.25) durante {bare_list_str}, "
            f"baja humedad superficial en {', '.join(bio_sum['dry_anomaly_months']) or 'meses secos'} "
            f"y mínimas de {sim_sum['min_temp_c']} °C (NASA POWER, {frost_list_str}). "
            f"Con {terrain['slope_pct']:.1f}% de inclinación a {terrain['elevation_m']:.0f} m y lluvias fuertes ({storm_list_str}), "
            f"cubrir el terreno con {cover_name} evita que el agua lave la tierra fértil.{scenario_tag}"
        )
        benefits_summary = (
            f"Ahorro estimado de agua de {water_savings_pct:.0f}%, reducción de lavado de suelo en {erosion_reduction_pct:.0f}%, "
            f"{bare_months_avoided} meses más con el suelo cubierto y +{pest_reduction_pct:.0f} pts en corte de plagas."
        )
    else:
        why = (
            f"Equilibra {top1} y {top2} para {market_lbl} usando {equip_lbl}.{season_note} "
            f"Alterna una leguminosa andina que devuelve nitrógeno natural ({legume_name}) "
            f"con cobertura verde protectora ({cover_name}) para recuperar fertilidad, cortar plagas como el gorgojo de los Andes "
            f"y la rancha, y preparar el siguiente cultivo ({followup_crop}) con {water_lbl}.{soil_context_str}"
        )
        nasa_ev = (
            f"Según el clima local de NASA POWER ({bio_sum['annual_precip_mm']:.0f} mm/año, mín. {sim_sum['min_temp_c']} °C), "
            f"la altura y ladera ({terrain['elevation_m']:.0f} m s.n.m., {terrain['slope_pct']:.1f}% inclinación) y la bajada de humedad "
            f"entre mayo y septiembre, elegimos cultivos de tu piso altitudinal que aprovechan las lluvias "
            f"y protegen la tierra durante {bare_list_str} sin exigir agua extra.{scenario_tag}"
        )
        benefits_summary = (
            f"Ganancia estimada de +{max(0.0, n_balance):.0f} kg N/ha en el suelo, mejora de materia orgánica {om_delta:+.0f} pts, "
            f"ahorro de agua de {water_savings_pct:.0f}%, menos lavado de suelo ({erosion_reduction_pct:.0f}%) y corte de plagas +{pest_reduction_pct:.0f} pts."
        )

    equip_gap = (
        f"Disponibilidad operativa en campo ({equip_lbl}): verificar acceso a semilla certificada (quinua, vicia, tarwi, rye grass), "
        f"mano de obra familiar para cosecha/trilla{' o costo de tractor/trilladora comunal' if equipment_access != 'manual_yunta' else ' manual'} y turnos reales de acequia."
    )
    gaps = [
        "Propiedades químicas y físicas en profundidad: el satélite NO mide pH real del suelo (acidez/aluminio común sobre 3,200 m en Cajamarca), fósforo disponible ni compactación subsuperficial (pie de arado); valida con tu observación o análisis local.",
        f"Mercado local y destino ({market_lbl}): la rentabilidad real depende del precio semanal en ferias de Cajamarca, Baños del Inca o La Encañada, contratos lecheros y acceso a desamargado de tarwi.",
        equip_gap,
        "Microclima hiperlocal (escala < 10–30 m): bordes con cercos vivos de quinual/aliso, acequias de infiltración o hondonadas locales pueden cambiar el patrón real de heladas frente al promedio satelital.",
    ]

    return {
        "why_suggested": why,
        "nasa_evidence": nasa_ev,
        "quantified_benefits": {
            "summary": benefits_summary,
            "water_savings_pct": water_savings_pct,
            "nitrogen_balance_kg_ha": round(n_balance, 0),
            "organic_matter_score": round(om_delta, 0),
            "erosion_reduction_pct": erosion_reduction_pct,
            "bare_months_avoided": bare_months_avoided,
            "pest_break_improvement_pct": pest_reduction_pct,
        },
        "human_in_the_loop_gaps": gaps,
    }

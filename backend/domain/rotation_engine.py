"""24-month seasonal crop rotation planner and strategy comparator."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from domain.catalog import (
    LIMA_TZ,
    MONTHS_ES,
    MONTHS_FULL_ES,
    _botanical_family,
    _get_crops_map,
)
from domain.climate import (
    _crop_climate_fit,
    build_crop_viability_20yr,
    simulate_climate_scenario,
)
from domain.scoring import (
    _build_24m_timeline,
    _build_explainability_blocks,
    _cost_efficiency_bonus,
    _crop_priority_bonus,
    _evaluate_strategy_metrics,
    _extract_priority_focus,
    _farmer_constraints_fit,
    _resolve_phase_visuals,
    _rotation_context_fit,
)


def _format_chunk_period(chunk_ym: List[Tuple[int, int]]) -> str:
    y0, m0 = chunk_ym[0]
    y1, m1 = chunk_ym[-1]
    if len(chunk_ym) == 1:
        return f"{MONTHS_ES[m0 - 1]} {y0}"
    if y0 == y1:
        return f"{MONTHS_ES[m0 - 1]} – {MONTHS_ES[m1 - 1]} {y0}"
    return f"{MONTHS_ES[m0 - 1]} {y0} – {MONTHS_ES[m1 - 1]} {y1}"


def _build_seasonal_plan_anchor(
    planning_month: Optional[int],
    planning_year: Optional[int],
    field_status: str,
    water_availability: str,
) -> Dict[str, Any]:
    """
    Anchors the 24-month decision window to the real Peru date (or user-selected start month)
    and partitions the next 24 consecutive months into Cajamarca Wet (Oct-Mar) & Dry (Abr-Sep) blocks.
    """
    now_lima = datetime.now(LIMA_TZ)
    ref_month = int(planning_month) if planning_month is not None else now_lima.month
    ref_year = int(planning_year) if planning_year is not None else now_lima.year

    cal_24: List[Tuple[int, int]] = []
    y, m = ref_year, ref_month
    for _ in range(24):
        cal_24.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1

    def _season(month_num: int) -> str:
        return "W" if month_num in (10, 11, 12, 1, 2, 3) else "D"

    chunks: List[Dict[str, Any]] = []
    cur_ym: List[Tuple[int, int]] = []
    cur_season = _season(cal_24[0][1])
    start_idx = 0
    for idx, ym in enumerate(cal_24):
        s = _season(ym[1])
        if s != cur_season:
            chunks.append({
                "season": cur_season,
                "months": cur_ym,
                "start_idx": start_idx,
                "end_idx": idx - 1,
                "duration": len(cur_ym),
                "period": _format_chunk_period(cur_ym),
            })
            cur_ym = [ym]
            cur_season = s
            start_idx = idx
        else:
            cur_ym.append(ym)
    if cur_ym:
        chunks.append({
            "season": cur_season,
            "months": cur_ym,
            "start_idx": start_idx,
            "end_idx": 23,
            "duration": len(cur_ym),
            "period": _format_chunk_period(cur_ym),
        })

    if field_status in ("con_cultivo", "terreno_libre"):
        eff_status = field_status
    else:
        if ref_month in (10, 11, 4, 5):
            eff_status = "terreno_libre"
        elif ref_month in (12, 1, 2, 3):
            eff_status = "con_cultivo"
        else:
            eff_status = "terreno_libre"

    starts_in_wet = _season(ref_month) == "W"
    if ref_month in (10, 11):
        if eff_status == "terreno_libre":
            season_id = "inicio_lluvias"
            season_label = "Inicio de lluvias — Ventana abierta de siembra grande"
            action_kind = "sow_main"
        else:
            season_id = "campana_en_curso"
            season_label = "Campaña de lluvias en curso"
            action_kind = "keep_crop_prep_cover"
    elif ref_month == 12:
        if eff_status == "terreno_libre":
            season_id = "ventana_tardia"
            season_label = "Ventana tardía de lluvias (semilla precoz)"
            action_kind = "sow_main"
        else:
            season_id = "campana_en_curso"
            season_label = "Campaña de lluvias en curso"
            action_kind = "keep_crop_prep_cover"
    elif ref_month in (1, 2, 3):
        season_id = "cierre_lluvias"
        season_label = "Plena campaña / Salida de lluvias"
        action_kind = "sow_cover" if (eff_status == "terreno_libre" and ref_month in (2, 3)) else "keep_crop_prep_cover"
    elif ref_month in (4, 5):
        season_id = "salida_lluvias"
        season_label = "Cosecha y entrada a estiaje — Ventana de cobertura"
        action_kind = "keep_crop_prep_cover" if (eff_status == "con_cultivo" and ref_month == 4) else "sow_cover"
    elif ref_month in (6, 7):
        season_id = "estiaje_heladas"
        season_label = "Estiaje y heladas — Protección de suelo"
        action_kind = "sow_cover" if (water_availability != "secano" and eff_status != "con_cultivo") else "protect_mulch"
    else:  # 8, 9
        season_id = "presiembra"
        season_label = "Pre-siembra — Preparación para lluvias de octubre"
        action_kind = "protect_mulch"

    return {
        "reference_date_iso": now_lima.date().isoformat(),
        "is_live_clock": planning_month is None and planning_year is None,
        "ref_month": ref_month,
        "ref_year": ref_year,
        "ref_month_label": f"{MONTHS_FULL_ES[ref_month - 1]} {ref_year}",
        "cal_24": cal_24,
        "chunks": chunks,
        "starts_in_wet": starts_in_wet,
        "field_status_effective": eff_status,
        "season_id": season_id,
        "season_label": season_label,
        "action_kind": action_kind,
    }


def _build_baseline_phase_spec(
    chunk: Dict[str, Any],
    wet_ordinal: int,
    dry_ordinal: int,
    current_crop: str,
    elev: float,
) -> Dict[str, Any]:
    season = chunk["season"]
    period = chunk["period"]
    dur = int(chunk["duration"])
    c2_id = "maiz_amilaceo" if elev <= 3180 else "papa"
    lowland = elev < 2100

    if current_crop == "sin_cultivo":
        role = (
            "Terreno libre actual (sin cultivo previo declarado; expuesto a erosión por lluvias si sigue sin cobertura)"
            if season == "W"
            else "Terreno libre en estiaje (sin cobertura vegetal ni rastrojo que proteja humedad y suelo)"
        )
        return {
            "phase_name": f"{'Ventana Lluvias' if season == 'W' else 'Estiaje'} {wet_ordinal + 1 if season == 'W' else dry_ordinal + 1}",
            "period": period,
            "duration_months": dur,
            "crop_id": "suelo_desnudo",
            "role": role,
        }

    if current_crop == "pastos_degradados":
        role = (
            "Pasto envejecido con baja cobertura en estación húmeda"
            if season == "W"
            else "Sobre-pastoreo en estiaje y pérdida de materia orgánica"
        )
        return {
            "phase_name": f"{'Húmeda' if season == 'W' else 'Estiaje'} {wet_ordinal + 1 if season == 'W' else dry_ordinal + 1}",
            "period": period,
            "duration_months": dur,
            "crop_id": "pasto_degradado",
            "role": role,
        }

    if season == "W":
        if current_crop == "monocultivo_papa":
            cid = "maiz_amilaceo" if lowland else "papa"
            role = (
                "Repetición continua de maíz en ladera cálida sin leguminosa"
                if lowland
                else ("Repetición continua de papa (acumula gorgojo y rancha)" if wet_ordinal > 0 else "Papa en monocultivo extractivo")
            )
        elif current_crop == "cebada_trigo_continuo":
            cid = "maiz_amilaceo" if lowland else ("cebada" if wet_ordinal % 2 == 0 else "trigo")
            role = "Cereal continuo sin leguminosa ni descanso"
        else:  # papa_maiz
            first_crop = "frijol" if lowland else "papa"
            cid = first_crop if wet_ordinal % 2 == 0 else c2_id
            role = "Campaña extractiva sin reposición biológica de nitrógeno"
        return {
            "phase_name": f"Campaña Lluvias {wet_ordinal + 1}",
            "period": period,
            "duration_months": dur,
            "crop_id": cid,
            "role": role,
        }

    return {
        "phase_name": f"Estiaje / Barbecho {dry_ordinal + 1}",
        "period": period,
        "duration_months": dur,
        "crop_id": "suelo_desnudo",
        "role": "Parcela baldía expuesta a heladas, viento y lavado de tierra",
    }


def _build_immediate_dry_phase(
    chunk: Dict[str, Any],
    action_kind: str,
    water_availability: str,
    phase_label_prefix: str = "Ventana Actual",
    cover_crop_id: str = "avena_vicia",
) -> Dict[str, Any]:
    if action_kind == "sow_cover":
        note = (
            "Cobertura forrajera inmediata bajo riego durante estiaje"
            if water_availability != "secano" and chunk["months"][0][1] in (6, 7)
            else "Sembrar cobertura apenas coseches para tapar el suelo antes de las heladas"
        )
        return {
            "phase_name": f"{phase_label_prefix} (Cobertura)",
            "period": chunk["period"],
            "duration_months": int(chunk["duration"]),
            "crop_id": cover_crop_id,
            "is_cover": True,
            "role": note,
        }
    if action_kind == "keep_crop_prep_cover":
        return {
            "phase_name": f"{phase_label_prefix} (Cosecha)",
            "period": chunk["period"],
            "duration_months": int(chunk["duration"]),
            "crop_id": "cultivo_en_curso",
            "role": "Terminar cosecha actual sin quemar rastrojo y sembrar cobertura enseguida",
        }
    return {
        "phase_name": f"{phase_label_prefix} (Pre-siembra)",
        "period": chunk["period"],
        "duration_months": int(chunk["duration"]),
        "crop_id": "rastrojo_manejo",
        "is_cover": True,
        "role": "Dejar rastrojo sobre la tierra (sin quema), incorporar abono/cal y preparar semilla para octubre",
    }


def generate_rotation_recommendations(
    terrain: Dict[str, Any],
    biophysical: Dict[str, Any],
    current_crop: str,
    water_availability: str,
    priorities: Dict[str, float],
    climate_scenario: Dict[str, Any],
    equipment_access: str = "manual_yunta",
    market_preference: str = "autoconsumo_feria",
    farmer_soil: Dict[str, Any] | None = None,
    field_status: str = "auto",
    planning_month: Optional[int] = None,
    planning_year: Optional[int] = None,
    available_seeds: Optional[List[str]] = None,
    crops_override: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Runs the full Multi-Criteria Decision Analysis (MCDA) and Climate Scenario Simulation
    anchored to today's Peru calendar date (or a selected month), returning 3 side-by-side
    rotation strategies with chronological 24-month calendars and explainability.
    """
    farmer_soil = farmer_soil or {}
    crops_map = (
        {c["id"]: c for c in crops_override}
        if crops_override
        else _get_crops_map()
    )
    elev = float(terrain["elevation_m"])
    slope = float(terrain["slope_pct"])

    season_anchor = _build_seasonal_plan_anchor(
        planning_month=planning_month,
        planning_year=planning_year,
        field_status=field_status,
        water_availability=water_availability,
    )
    chunks = season_anchor["chunks"]

    sim_climate = simulate_climate_scenario(
        biophysical=biophysical,
        terrain=terrain,
        rain_delta_pct=float(climate_scenario.get("rain_delta_pct", 0.0)),
        temp_delta_c=float(climate_scenario.get("temp_delta_c", 0.0)),
        frost_frequency=str(climate_scenario.get("frost_frequency", "normal")),
    )
    sim_sum = sim_climate["summary"]

    # --- STRATEGY 1: BASELINE (PRACTICA ACTUAL) ---
    p1_all: List[Dict[str, Any]] = []
    wet_cnt = 0
    dry_cnt = 0
    for ch in chunks:
        p1_all.append(_build_baseline_phase_spec(ch, wet_cnt, dry_cnt, current_crop, elev))
        if ch["season"] == "W":
            wet_cnt += 1
        else:
            dry_cnt += 1
    p1_phases = p1_all[:4]
    p1_tail = p1_all[4] if len(p1_all) > 4 else None

    s1_sub_map = {
        "sin_cultivo": "Terreno libre / Sin cultivo previo (testigo si permanece sin cobertura)",
        "monocultivo_papa": "Monocultivo continuo de Papa + barbecho desnudo",
        "pastos_degradados": "Pastos degradados continuos sin renovación",
        "cebada_trigo_continuo": "Secuencia cerealera continua (Cebada – Trigo) sin cobertura",
        "papa_maiz": f"Secuencia tradicional {'Papa – Maíz' if elev <= 3180 else 'Papa continua'} con meses baldíos",
    }
    s1_sub = s1_sub_map.get(current_crop, "Manejo tradicional actual")

    strat1 = _evaluate_strategy_metrics(
        strategy_id="baseline",
        title="Estrategia 1 — Línea Base (Práctica Actual)",
        subtitle=s1_sub,
        phases=p1_phases,
        crops_map=crops_map,
        terrain=terrain,
        biophysical=biophysical,
        sim_climate=sim_climate,
        water_availability=water_availability,
        priorities=priorities,
        current_crop=current_crop,
        season_anchor=season_anchor,
        tail_phase=p1_tail,
        equipment_access=equipment_access,
        market_preference=market_preference,
        farmer_soil=farmer_soil,
        baseline_metrics=None,
    )
    base_internal = strat1["_internal"]

    # --- SEED INVENTORY & COVER CROP SELECTION (ALL 24 CROPS) ---
    soil_ph = float((terrain.get("soil_profile") or {}).get("ph", 6.2))
    acid_reported = farmer_soil.get("soil_acidity") == "acido" or soil_ph < 5.6
    requested_seeds = [str(s).strip() for s in (available_seeds or []) if str(s).strip() in crops_map]
    viable_seeds: List[str] = []
    unviable_seeds: List[Dict[str, str]] = []
    for sid in requested_seeds:
        if sid in viable_seeds:
            continue
        sc = crops_map[sid]
        wf_s, ff_s, tf_s = _crop_climate_fit(sc, elev, slope, water_availability, sim_sum)
        in_alt = (float(sc["altitude_min_m"]) - 90.0) <= elev <= (float(sc["altitude_max_m"]) + 90.0)
        if in_alt and ff_s >= 28.0 and tf_s >= 26.0:
            viable_seeds.append(sid)
        else:
            reasons = []
            if not in_alt:
                reasons.append(f"piso óptimo {sc['altitude_min_m']}–{sc['altitude_max_m']} m (parcela a {elev:.0f} m)")
            if ff_s < 28.0:
                reasons.append("alto riesgo de daño por helada")
            if tf_s < 26.0:
                reasons.append("temperatura fuera de rango óptimo")
            unviable_seeds.append({
                "crop_id": sid,
                "crop_name": sc.get("name", sid),
                "reason": ", ".join(reasons) or "fuera de rango bioclimático NASA",
            })
    viable_seed_set = set(viable_seeds)

    water_p_top = float(priorities.get("water_conservation", 70))
    prio_focus = _extract_priority_focus(priorities)
    cover_candidates = ["avena_vicia", "lenteja", "arveja", "frijol", "ryegrass_trebol"]
    scored_covers = []
    for cid in cover_candidates:
        c = crops_map[cid]
        if not ((float(c["altitude_min_m"]) - 80.0) <= elev <= (float(c["altitude_max_m"]) + 80.0)):
            continue
        wf, ff, tf = _crop_climate_fit(c, elev, slope, water_availability, sim_sum)
        cf_delta = _farmer_constraints_fit(c, slope, equipment_access, market_preference, farmer_soil)
        rot_ctx = _rotation_context_fit(cid, c, current_crop, water_availability, farmer_soil, elev, slope, viable_seed_set, water_p_top)
        p_bonus = _crop_priority_bonus(cid, c, prio_focus)
        cov_score = (
            0.30 * float(c["erosion_protection_score"])
            + 0.24 * wf
            + 0.20 * ff
            + 0.14 * max(0.0, float(c["nitrogen_balance_kg_ha"])) * 0.55
            + 0.10 * float(c["drought_tolerance"])
            + cf_delta * 0.60
            + rot_ctx * 0.55
            + _cost_efficiency_bonus(c) * 0.45
            + p_bonus * 0.35
            + (42.0 if cid in viable_seed_set else 0.0)
        )
        scored_covers.append((cov_score, cid))
    scored_covers.sort(reverse=True)
    cover_crop_id = scored_covers[0][1] if scored_covers else ("frijol" if elev < 2150 else "avena_vicia")
    cover_label = crops_map[cover_crop_id].get("name", cover_crop_id)

    # --- STRATEGY 2: RESILIENCIA HIDRICA Y PROTECCION DE SUELO (ALL 24 CROPS) ---
    scored_resilient = []
    pasture_ids = {"ryegrass_trebol", "alfalfa"}
    repeat_penalize = set()
    if current_crop == "monocultivo_papa":
        repeat_penalize.add("papa")
    elif current_crop == "papa_maiz":
        repeat_penalize.update({"papa", "maiz_amilaceo"})
    elif current_crop == "cebada_trigo_continuo":
        repeat_penalize.update({"cebada", "trigo"})

    for cid, c in crops_map.items():
        if not (float(c["altitude_min_m"]) <= elev <= float(c["altitude_max_m"])):
            continue
        if cid in pasture_ids and water_availability == "secano" and market_preference != "leche_forraje" and cid not in viable_seed_set:
            continue
        wf, ff, tf = _crop_climate_fit(c, elev, slope, water_availability, sim_sum)
        cf_delta = _farmer_constraints_fit(c, slope, equipment_access, market_preference, farmer_soil)
        rot_ctx = _rotation_context_fit(cid, c, current_crop, water_availability, farmer_soil, elev, slope, viable_seed_set, water_p_top)
        p_bonus = _crop_priority_bonus(cid, c, prio_focus)
        water_w = 0.24 + 0.14 * (water_p_top / 100.0)
        eros_w = 0.12 + 0.12 * (float(priorities.get("erosion_control", 70)) / 100.0)
        seed_boost = 58.0 if cid in viable_seed_set else (-8.0 if viable_seed_set else 0.0)
        rot_penalty = -20.0 if (cid in repeat_penalize and cid not in viable_seed_set) else 0.0
        r_score = (
            water_w * wf
            + 0.18 * float(c["drought_tolerance"])
            + 0.20 * ff
            + eros_w * float(c["erosion_protection_score"])
            + 0.08 * tf
            + cf_delta * 0.85
            + rot_ctx * 0.90
            + _cost_efficiency_bonus(c) * 0.65
            + p_bonus * 0.95
            + seed_boost
            + rot_penalty
        )
        scored_resilient.append((r_score, cid))
    scored_resilient.sort(reverse=True)
    default_r1 = "frijol" if elev < 2200 else "quinua"
    default_r2 = "maiz_amilaceo" if elev < 2200 else "tarwi"
    best_r1 = scored_resilient[0][1] if scored_resilient else default_r1

    fam_r1 = _botanical_family(best_r1)
    diff_family_r2 = [
        cid for _, cid in scored_resilient[1:]
        if _botanical_family(cid) != fam_r1
        and cid != best_r1
        and cid != cover_crop_id
    ]
    if not diff_family_r2:
        diff_family_r2 = [
            cid for _, cid in scored_resilient[1:]
            if _botanical_family(cid) != fam_r1 and cid != best_r1
        ]
    if viable_seed_set and len(viable_seeds) >= 2:
        seed_r2 = [cid for _, cid in scored_resilient if cid in viable_seed_set and cid != best_r1]
        best_r2 = seed_r2[0] if seed_r2 else (diff_family_r2[0] if diff_family_r2 else default_r2)
    else:
        best_r2 = diff_family_r2[0] if diff_family_r2 else (scored_resilient[1][1] if len(scored_resilient) > 1 else default_r2)

    if cover_crop_id in (best_r1, best_r2) and len(scored_covers) > 1:
        alt_cov_s2 = [cid for _, cid in scored_covers if cid not in (best_r1, best_r2)]
        if alt_cov_s2:
            cover_crop_id = alt_cov_s2[0]
            cover_label = crops_map[cover_crop_id].get("name", cover_crop_id)

    action_kind = season_anchor["action_kind"]
    starts_in_wet = season_anchor["starts_in_wet"]
    late_dec_note = " (usar variedad precoz por siembra tardía)" if season_anchor["ref_month"] == 12 else ""

    if starts_in_wet:
        if action_kind == "sow_main":
            p2_ch0 = {
                "phase_name": "Campaña Actual (Ahora)",
                "period": chunks[0]["period"],
                "duration_months": int(chunks[0]["duration"]),
                "crop_id": best_r1,
                "role": f"Cultivo rústico tolerante a estrés hídrico ({crops_map[best_r1]['water_req_mm']} mm){late_dec_note}",
            }
            p2_ch2_crop = best_r2
        elif action_kind == "sow_cover":
            p2_ch0 = {
                "phase_name": "Cobertura Temprana",
                "period": chunks[0]["period"],
                "duration_months": int(chunks[0]["duration"]),
                "crop_id": cover_crop_id,
                "is_cover": True,
                "role": f"Aprovecha últimas lluvias para implantar cobertura ({cover_label}) antes del estiaje",
            }
            p2_ch2_crop = best_r1
        else:
            p2_ch0 = {
                "phase_name": "Campaña en Curso",
                "period": chunks[0]["period"],
                "duration_months": int(chunks[0]["duration"]),
                "crop_id": "cultivo_en_curso",
                "role": f"Cuidar lo ya sembrado hasta cosecha (mar–abr) y preparar semilla de {cover_label}",
            }
            p2_ch2_crop = best_r1

        p2_phases = [
            p2_ch0,
            {
                "phase_name": "Cobertura Estiaje 1",
                "period": chunks[1]["period"],
                "duration_months": int(chunks[1]["duration"]),
                "crop_id": cover_crop_id,
                "is_cover": True,
                "role": f"Cobertura viva ({cover_label}) anti-erosión y retención de humedad en meses secos",
            },
            {
                "phase_name": "Próxima Campaña Grande",
                "period": chunks[2]["period"],
                "duration_months": int(chunks[2]["duration"]),
                "crop_id": p2_ch2_crop,
                "role": f"Rotación rústica adaptada al piso térmico ({crops_map[p2_ch2_crop]['water_req_mm']} mm)",
            },
            {
                "phase_name": "Cobertura Estiaje 2",
                "period": chunks[3]["period"],
                "duration_months": int(chunks[3]["duration"]),
                "crop_id": cover_crop_id,
                "is_cover": True,
                "role": f"Cobertura protectora ({cover_label}) para frenar radiación y lavado de suelo",
            },
        ]
        p2_tail = (
            {
                "phase_name": "Inicio Campaña Siguiente",
                "period": chunks[4]["period"],
                "duration_months": int(chunks[4]["duration"]),
                "crop_id": best_r2 if action_kind != "sow_main" else best_r1,
                "role": "Inicio de nueva campaña resiliente con lluvias",
            }
            if len(chunks) > 4
            else None
        )
    else:
        p2_phases = [
            _build_immediate_dry_phase(chunks[0], action_kind, water_availability, "Ahora", cover_crop_id),
            {
                "phase_name": "Campaña Grande 1",
                "period": chunks[1]["period"],
                "duration_months": int(chunks[1]["duration"]),
                "crop_id": best_r1,
                "role": f"Cultivo resiliente adaptado a lluvias y piso ({crops_map[best_r1]['water_req_mm']} mm)",
            },
            {
                "phase_name": "Cobertura Estiaje",
                "period": chunks[2]["period"],
                "duration_months": int(chunks[2]["duration"]),
                "crop_id": cover_crop_id,
                "is_cover": True,
                "role": f"Cobertura viva ({cover_label}) en meses baldíos y protección del suelo",
            },
            {
                "phase_name": "Campaña Grande 2",
                "period": chunks[3]["period"],
                "duration_months": int(chunks[3]["duration"]),
                "crop_id": best_r2,
                "role": "Rotación botánica de bajo consumo hídrico y protección de suelo",
            },
        ]
        p2_tail = (
            {
                "phase_name": "Cobertura Siguiente",
                "period": chunks[4]["period"],
                "duration_months": int(chunks[4]["duration"]),
                "crop_id": cover_crop_id,
                "is_cover": True,
                "role": "Cierre protector al término de cosecha",
            }
            if len(chunks) > 4
            else None
        )

    p2_route_names = " → ".join(
        _resolve_phase_visuals(ph["crop_id"], crops_map, bool(ph.get("is_cover")))[0]
        for ph in p2_phases
    )
    strat2 = _evaluate_strategy_metrics(
        strategy_id="resilience",
        title="Estrategia 2 — Resiliencia Hídrica y Protección de Suelo",
        subtitle=p2_route_names,
        phases=p2_phases,
        crops_map=crops_map,
        terrain=terrain,
        biophysical=biophysical,
        sim_climate=sim_climate,
        water_availability=water_availability,
        priorities=priorities,
        current_crop=current_crop,
        season_anchor=season_anchor,
        tail_phase=p2_tail,
        equipment_access=equipment_access,
        market_preference=market_preference,
        farmer_soil=farmer_soil,
        baseline_metrics=base_internal,
    )

    # --- STRATEGY 3: REGENERACION DE SUELOS Y RENTABILIDAD MIXTA (ALL 24 CROPS) ---
    legume_candidates = ["tarwi", "haba", "arveja", "frijol", "lenteja", "tara_taya", "avena_vicia", "ryegrass_trebol", "alfalfa"]
    scored_leg = []
    for cid in legume_candidates:
        c = crops_map[cid]
        if not (float(c["altitude_min_m"]) <= elev <= float(c["altitude_max_m"])):
            continue
        wf, ff, tf = _crop_climate_fit(c, elev, slope, water_availability, sim_sum)
        cf_delta = _farmer_constraints_fit(c, slope, equipment_access, market_preference, farmer_soil)
        rot_ctx = _rotation_context_fit(cid, c, current_crop, water_availability, farmer_soil, elev, slope, viable_seed_set, water_p_top)
        p_bonus = _crop_priority_bonus(cid, c, prio_focus)
        seed_boost = 54.0 if cid in viable_seed_set else 0.0
        div_bonus = 6.0 if cid not in (best_r1, best_r2) else -4.0
        cov_avoid = -6.0 if cid == cover_crop_id and cid not in viable_seed_set else 0.0
        l_score = (
            0.28 * float(c["nitrogen_balance_kg_ha"]) / 1.3
            + 0.24 * wf
            + 0.20 * ff
            + 0.14 * float(c["pest_break_score"])
            + 0.14 * float(c["commercial_forage_value_score"]) * (float(priorities.get("commercial_forage", 70)) / 100.0)
            + cf_delta * 0.85
            + rot_ctx * 0.85
            + _cost_efficiency_bonus(c) * 0.65
            + p_bonus * 0.90
            + seed_boost
            + div_bonus
            + cov_avoid
        )
        scored_leg.append((l_score, cid))
    scored_leg.sort(reverse=True)
    leg1 = scored_leg[0][1] if scored_leg else ("frijol" if elev < 2150 else "tarwi")

    cover_s3_id = cover_crop_id
    if cover_s3_id == leg1 and len(scored_covers) > 1:
        alt_cov = [cid for _, cid in scored_covers if cid != leg1]
        if alt_cov:
            cover_s3_id = alt_cov[0]
    cover_crop_id = cover_s3_id
    cover_label = crops_map[cover_crop_id].get("name", cover_crop_id)

    comm_p = float(priorities.get("commercial_forage", 70))
    erosion_p = float(priorities.get("erosion_control", 70))
    water_p = float(priorities.get("water_conservation", 70))

    has_non_pasture_seeds = any(s not in pasture_ids for s in viable_seed_set)
    use_dairy_perennial = (
        elev >= 2100
        and not has_non_pasture_seeds
        and (
            market_preference == "leche_forraje"
            or (current_crop == "pastos_degradados" and elev <= 3550 and sim_sum["annual_precip_mm"] >= 600)
        )
    )

    waterlogged_reported = farmer_soil.get("compaction_or_drainage") == "se_encharca"
    perennial_id = (
        "ryegrass_trebol"
        if (acid_reported or waterlogged_reported or water_availability != "secano" or sim_sum["annual_precip_mm"] >= 760 or elev > 3420 or "ryegrass_trebol" in viable_seed_set)
        else "alfalfa"
    )

    scored_c2 = []
    fam_leg1 = _botanical_family(leg1)
    for cid, c in crops_map.items():
        if cid == leg1 or cid == cover_crop_id:
            continue
        if not (float(c["altitude_min_m"]) <= elev <= float(c["altitude_max_m"])):
            continue
        if cid in pasture_ids and market_preference != "leche_forraje" and current_crop != "pastos_degradados" and cid not in viable_seed_set:
            continue
        wf, ff, tf = _crop_climate_fit(c, elev, slope, water_availability, sim_sum)
        cf_delta = _farmer_constraints_fit(c, slope, equipment_access, market_preference, farmer_soil)
        rot_ctx = _rotation_context_fit(cid, c, current_crop, water_availability, farmer_soil, elev, slope, viable_seed_set, water_p)
        p_bonus = _crop_priority_bonus(cid, c, prio_focus)
        seed_boost = 58.0 if cid in viable_seed_set else 0.0
        rot_penalty = -18.0 if (cid in repeat_penalize and cid not in viable_seed_set) else 0.0
        same_fam = _botanical_family(cid) == fam_leg1
        if prio_focus["pest"] > 0.65:
            fam_bonus = -22.0 if same_fam else 14.0
        elif prio_focus["soil"] > 0.85:
            fam_bonus = 6.0 if float(c["nitrogen_balance_kg_ha"]) >= 50.0 else 0.0
        else:
            fam_bonus = -18.0 if same_fam else 10.0
        alt_bonus = 8.0 if cid not in (best_r1, best_r2) else -5.0
        c2_score = (
            0.28 * float(c["commercial_forage_value_score"]) * (0.4 + 0.6 * comm_p / 100.0)
            + 0.26 * wf
            + 0.20 * ff
            + 0.20 * float(c["erosion_protection_score"]) * (0.4 + 0.6 * erosion_p / 100.0)
            + cf_delta * 0.90
            + rot_ctx * 0.95
            + _cost_efficiency_bonus(c) * 0.85
            + p_bonus * 1.15
            + (7.0 if (cid == "ajo_valle" and current_crop == "monocultivo_papa") else 0.0)
            - (15.0 if (cid == "papa" and water_p >= 80 and water_availability == "secano") else 0.0)
            + seed_boost
            + rot_penalty
            + fam_bonus
            + alt_bonus
        )
        scored_c2.append((c2_score, cid))
    scored_c2.sort(reverse=True)
    cash_c2 = scored_c2[0][1] if scored_c2 else ("cafe" if 900 <= elev < 2150 else ("cacao" if elev < 900 else "quinua"))

    if starts_in_wet:
        if action_kind == "sow_main":
            p3_ch0 = {
                "phase_name": "Campaña Actual (Ahora)",
                "period": chunks[0]["period"],
                "duration_months": int(chunks[0]["duration"]),
                "crop_id": leg1,
                "role": f"Leguminosa fijadora (+{crops_map[leg1]['nitrogen_balance_kg_ha']} kg N/ha) y ruptura de plagas{late_dec_note}",
            }
            if use_dairy_perennial:
                p3_tail_crop = perennial_id
                p3_phases = [
                    p3_ch0,
                    {
                        "phase_name": "Cobertura Intermedia",
                        "period": chunks[1]["period"],
                        "duration_months": int(chunks[1]["duration"]),
                        "crop_id": cover_crop_id,
                        "is_cover": True,
                        "role": f"Cobertura protectora ({cover_label}) e incorporación de materia orgánica",
                    },
                    {
                        "phase_name": "Sistema Lechero",
                        "period": chunks[2]["period"],
                        "duration_months": int(chunks[2]["duration"]),
                        "crop_id": perennial_id,
                        "is_perennial_half": True,
                        "role": "Asociación forrajera perenne de alto valor lechero y cobertura total",
                    },
                    {
                        "phase_name": "Consolidación Forrajera",
                        "period": chunks[3]["period"],
                        "duration_months": int(chunks[3]["duration"]),
                        "crop_id": perennial_id,
                        "is_perennial_half": True,
                        "role": "Sello anti-erosivo continuo y fijación simbiótica de nitrógeno",
                    },
                ]
            else:
                p3_tail_crop = leg1
                p3_phases = [
                    p3_ch0,
                    {
                        "phase_name": "Cobertura Intermedia",
                        "period": chunks[1]["period"],
                        "duration_months": int(chunks[1]["duration"]),
                        "crop_id": cover_crop_id,
                        "is_cover": True,
                        "role": f"Cobertura en ventana desnuda ({cover_label}) y protección de humedad",
                    },
                    {
                        "phase_name": "Campaña 2 (Cosecha Limpia)",
                        "period": chunks[2]["period"],
                        "duration_months": int(chunks[2]["duration"]),
                        "crop_id": cash_c2,
                        "role": "Aprovecha nitrógeno biológico fijado y lote con baja carga de plagas",
                    },
                    {
                        "phase_name": "Cierre Protector",
                        "period": chunks[3]["period"],
                        "duration_months": int(chunks[3]["duration"]),
                        "crop_id": cover_crop_id,
                        "is_cover": True,
                        "role": "Cierra el ciclo protegiendo el suelo del estiaje y lluvias de entrada",
                    },
                ]
        else:
            p3_ch0 = (
                {
                    "phase_name": "Cobertura Temprana",
                    "period": chunks[0]["period"],
                    "duration_months": int(chunks[0]["duration"]),
                    "crop_id": cover_crop_id,
                    "is_cover": True,
                    "role": f"Siembra inmediata de cobertura ({cover_label}) con humedad de salida de lluvias",
                }
                if action_kind == "sow_cover"
                else {
                    "phase_name": "Campaña en Curso",
                    "period": chunks[0]["period"],
                    "duration_months": int(chunks[0]["duration"]),
                    "crop_id": "cultivo_en_curso",
                    "role": "Terminar cosecha actual (mar–abr) y reservar semilla de cobertura y leguminosa",
                }
            )
            ch3_crop = perennial_id if use_dairy_perennial else cover_crop_id
            p3_tail_crop = perennial_id if use_dairy_perennial else cash_c2
            p3_phases = [
                p3_ch0,
                {
                    "phase_name": "Cobertura Estiaje 1",
                    "period": chunks[1]["period"],
                    "duration_months": int(chunks[1]["duration"]),
                    "crop_id": cover_crop_id,
                    "is_cover": True,
                    "role": f"Tapa la tierra pelada apenas cosechas ({cover_label}) y aporta materia orgánica",
                },
                {
                    "phase_name": "Campaña Regenerativa",
                    "period": chunks[2]["period"],
                    "duration_months": int(chunks[2]["duration"]),
                    "crop_id": leg1,
                    "role": f"Leguminosa fijadora (+{crops_map[leg1]['nitrogen_balance_kg_ha']} kg N/ha) que rompe ciclo de plagas",
                },
                {
                    "phase_name": "Consolidación Lechera" if use_dairy_perennial else "Cobertura Estiaje 2",
                    "period": chunks[3]["period"],
                    "duration_months": int(chunks[3]["duration"]),
                    "crop_id": ch3_crop,
                    "is_cover": not use_dairy_perennial,
                    "is_perennial_half": use_dairy_perennial,
                    "role": (
                        "Instala pastura asociada perenne sobre suelo enriquecido"
                        if use_dairy_perennial
                        else f"Mantiene el suelo protegido ({cover_label}) antes de la cosecha comercial"
                    ),
                },
            ]
        p3_tail = (
            {
                "phase_name": "Continuación",
                "period": chunks[4]["period"],
                "duration_months": int(chunks[4]["duration"]),
                "crop_id": p3_tail_crop,
                "is_perennial_half": use_dairy_perennial,
                "role": "Continuidad productiva en campaña siguiente",
            }
            if len(chunks) > 4
            else None
        )
    else:
        p3_ch0 = _build_immediate_dry_phase(chunks[0], action_kind, water_availability, "Ahora", cover_crop_id)
        if use_dairy_perennial:
            p3_phases = [
                p3_ch0,
                {
                    "phase_name": "Campaña 1 (Fijación N)",
                    "period": chunks[1]["period"],
                    "duration_months": int(chunks[1]["duration"]),
                    "crop_id": leg1,
                    "role": f"Leguminosa fijadora (+{crops_map[leg1]['nitrogen_balance_kg_ha']} kg N/ha) y corte sanitario",
                },
                {
                    "phase_name": "Siembra Sistema Lechero",
                    "period": chunks[2]["period"],
                    "duration_months": int(chunks[2]["duration"]),
                    "crop_id": perennial_id,
                    "is_perennial_half": True,
                    "role": "Asociación forrajera perenne sobre suelo enriquecido con nitrógeno",
                },
                {
                    "phase_name": "Consolidación Forrajera",
                    "period": chunks[3]["period"],
                    "duration_months": int(chunks[3]["duration"]),
                    "crop_id": perennial_id,
                    "is_perennial_half": True,
                    "role": "Cobertura total anti-erosión y producción sostenida de forraje",
                },
            ]
            p3_tail_crop = perennial_id
        else:
            p3_phases = [
                p3_ch0,
                {
                    "phase_name": "Campaña 1 (Fijación N)",
                    "period": chunks[1]["period"],
                    "duration_months": int(chunks[1]["duration"]),
                    "crop_id": leg1,
                    "role": f"Leguminosa fijadora (+{crops_map[leg1]['nitrogen_balance_kg_ha']} kg N/ha) que corta plagas",
                },
                {
                    "phase_name": "Cobertura Intermedia",
                    "period": chunks[2]["period"],
                    "duration_months": int(chunks[2]["duration"]),
                    "crop_id": cover_crop_id,
                    "is_cover": True,
                    "role": f"Protege el suelo en ventana seca ({cover_label}) y aporta cobertura viva",
                },
                {
                    "phase_name": "Campaña 2 (Cosecha Limpia)",
                    "period": chunks[3]["period"],
                    "duration_months": int(chunks[3]["duration"]),
                    "crop_id": cash_c2,
                    "role": "Aprovecha el nitrógeno fijado en lote libre de plagas",
                },
            ]
            p3_tail_crop = cover_crop_id

        p3_tail = (
            {
                "phase_name": "Cobertura Siguiente",
                "period": chunks[4]["period"],
                "duration_months": int(chunks[4]["duration"]),
                "crop_id": p3_tail_crop,
                "is_cover": not use_dairy_perennial,
                "is_perennial_half": use_dairy_perennial,
                "role": "Cierre protector al término de la segunda campaña",
            }
            if len(chunks) > 4
            else None
        )

    p3_route_names = " → ".join(
        _resolve_phase_visuals(ph["crop_id"], crops_map, bool(ph.get("is_cover")))[0]
        for ph in p3_phases
    )
    strat3 = _evaluate_strategy_metrics(
        strategy_id="regenerative",
        title="Estrategia 3 — Regeneración de Suelos y Rentabilidad Mixta",
        subtitle=p3_route_names,
        phases=p3_phases,
        crops_map=crops_map,
        terrain=terrain,
        biophysical=biophysical,
        sim_climate=sim_climate,
        water_availability=water_availability,
        priorities=priorities,
        current_crop=current_crop,
        season_anchor=season_anchor,
        tail_phase=p3_tail,
        equipment_access=equipment_access,
        market_preference=market_preference,
        farmer_soil=farmer_soil,
        baseline_metrics=base_internal,
    )

    strategies = [strat1, strat2, strat3]
    for s in strategies:
        s.pop("_internal", None)

    best_strategy = max(strategies, key=lambda s: s["mcda_score"])
    win_first = best_strategy["phases"][0]
    win_next = best_strategy["phases"][1]

    if action_kind == "sow_main":
        immediate_action = (
            f"Estás en ventana de siembra ({chunks[0]['period']}). "
            f"Puedes sembrar {win_first['crop_name']} desde este mes aprovechando las lluvias"
            + (" (usa semilla precoz por siembra tardía)." if season_anchor["ref_month"] == 12 else ".")
        )
        next_window = f"Ahora ({chunks[0]['period']})"
    elif action_kind == "sow_cover":
        immediate_action = (
            f"Momento clave para cobertura ({chunks[0]['period']}): "
            f"siembra {win_first['crop_name']} aprovechando la humedad antes de que aprieten las heladas de estiaje, "
            f"y prepara {win_next['crop_name']} para {chunks[1]['period']}."
        )
        next_window = f"Cobertura ahora ({chunks[0]['period']}) · Principal en {chunks[1]['period']}"
    elif action_kind == "keep_crop_prep_cover":
        immediate_action = (
            f"Tu parcela figura con campaña en marcha ({chunks[0]['period']}). "
            f"No levantes el cultivo actual: cuídalo hasta la cosecha y deja lista semilla de {win_next['crop_name']} "
            f"para cubrir la tierra en {chunks[1]['period']}."
        )
        next_window = f"{win_next['crop_name']} en {chunks[1]['period']}"
    else:
        immediate_action = (
            f"Época seca / pre-siembra ({chunks[0]['period']}): no quemes rastrojo ni dejes sobrepastorear a ras; "
            f"conserva mulch, incorpora guano o cal si tu tierra es ácida y alista semilla de {win_next['crop_name']} "
            f"para sembrar apenas arranquen las lluvias ({chunks[1]['period']})."
        )
        next_window = f"Siembra con lluvias en {chunks[1]['period']}"

    seasonal_context = {
        "reference_date_iso": season_anchor["reference_date_iso"],
        "is_live_clock": season_anchor["is_live_clock"],
        "reference_month": season_anchor["ref_month"],
        "reference_year": season_anchor["ref_year"],
        "reference_month_label": season_anchor["ref_month_label"],
        "field_status_effective": season_anchor["field_status_effective"],
        "season_id": season_anchor["season_id"],
        "season_label": season_anchor["season_label"],
        "immediate_action": immediate_action,
        "next_planting_window": next_window,
    }

    climate_outlook_20yr = build_crop_viability_20yr(
        terrain=terrain,
        biophysical=biophysical,
        water_availability=water_availability,
        crops_list=crops_override,
    )

    if unviable_seeds:
        seed_warn = "Semilla(s) limitada(s) por clima/altura NASA en tu parcela: " + "; ".join(
            f"{u['crop_name']} ({u['reason']})" for u in unviable_seeds
        )
        for st in (strat2, strat3):
            st["warnings"] = [seed_warn, *list(st.get("warnings") or [])][:4]

    seed_constraint_summary = {
        "requested": requested_seeds,
        "viable_used": viable_seeds,
        "unviable": unviable_seeds,
        "evaluated_catalog_count": len(crops_map),
    }

    return {
        "seasonal_context": seasonal_context,
        "simulated_climate": sim_climate,
        "climate_outlook_20yr": climate_outlook_20yr,
        "recommended_strategy_id": best_strategy["id"],
        "recommended_strategy_title": best_strategy["title"],
        "strategies": strategies,
        "seed_constraint_summary": seed_constraint_summary,
    }

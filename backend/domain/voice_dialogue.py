"""Pure domain NLU, 6-slot state dialogue manager, and grounded farmer response builders."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional

from domain.catalog import (
    _CAJAMARCA_LOCATIONS,
    _CROP_LABELS_BY_ID,
    _CURRENT_CROP_LABELS,
    _PERU_CROP_ALIASES,
    _VALID_CURRENT_CROPS,
    _VALID_WATER_MODES,
    _WATER_MODE_LABELS,
    load_crops_data,
)


def _normalize_text(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text or "")
    stripped = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", stripped.lower()).strip()


def _within_cajamarca(lat: Optional[float], lon: Optional[float]) -> bool:
    if lat is None or lon is None:
        return False
    return (-8.5 <= lat <= -4.5) and (-79.8 <= lon <= -77.3)


def _valid_world_coords(lat: Optional[float], lon: Optional[float]) -> bool:
    if lat is None or lon is None:
        return False
    return (-56.0 <= lat <= 56.0) and (-180.0 <= lon <= 180.0)


def extract_coordinates_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extracts decimal or DMS coordinates from complex voice or typed farmer messages."""
    raw = text or ""
    norm = _normalize_text(raw)

    spoken = re.sub(r"\bmenos\s+(?=\d)", "-", norm)
    spoken = re.sub(r"(\d)\s+(?:punto|coma)\s+(\d)", r"\1.\2", spoken)

    dms_matches = re.findall(
        r"(\d{1,3})\s*[°º]\s*(\d{1,2})\s*['’]\s*(\d{1,2}(?:\.\d+)?)\s*[\"”]?\s*([nseoow])",
        spoken,
        flags=re.IGNORECASE,
    )
    if len(dms_matches) >= 2:
        def _dms_to_deg(m_tuple: tuple[str, str, str, str]) -> float:
            d, mn, sec, hemi = m_tuple
            val = float(d) + float(mn) / 60.0 + float(sec) / 3600.0
            if hemi.lower() in ("s", "o", "w"):
                val = -abs(val)
            return val
        lat_d = _dms_to_deg(dms_matches[0])
        lon_d = _dms_to_deg(dms_matches[1])
        if _valid_world_coords(lat_d, lon_d):
            return {"lat": round(lat_d, 6), "lon": round(lon_d, 6)}

    lat_m = re.search(r"\b(?:lat|latitud)\s*[:=]?\s*(-?\d{1,2}\.\d{1,7})\s*([ns]?)", spoken)
    lon_m = re.search(r"\b(?:lon|lng|longitud)\s*[:=]?\s*(-?\d{1,3}\.\d{1,7})\s*([eow]?)", spoken)
    if lat_m and lon_m:
        lat_v = float(lat_m.group(1))
        lon_v = float(lon_m.group(1))
        if lat_m.group(2) == "s":
            lat_v = -abs(lat_v)
        if lon_m.group(2) in ("o", "w"):
            lon_v = -abs(lon_v)
        if _valid_world_coords(lat_v, lon_v):
            return {"lat": round(lat_v, 6), "lon": round(lon_v, 6)}

    pair_m = re.search(
        r"(?<![\d.])(-?\d{1,2}\.\d{2,7})\s*([ns])?\s*[,;\s/y]+\s*(-?\d{1,3}\.\d{2,7})\s*([eow])?(?![\d.])",
        spoken,
    )
    if pair_m:
        lat_v = float(pair_m.group(1))
        lon_v = float(pair_m.group(3))
        if pair_m.group(2) == "s":
            lat_v = -abs(lat_v)
        if pair_m.group(4) in ("o", "w"):
            lon_v = -abs(lon_v)
        if (-56.0 <= lat_v <= 56.0) and (-180.0 <= lon_v <= 180.0) and (abs(lat_v) >= 1.0 or abs(lon_v) >= 1.0):
            return {"lat": round(lat_v, 6), "lon": round(lon_v, 6)}

    return None


def _extract_candidate_place_phrase(norm: str) -> Optional[str]:
    cleaned = re.sub(r"-?\d{1,3}\.\d{2,7}", " ", norm)
    m = re.search(
        r"(?:cerca\s+de\s+la|cerca\s+del|cerca\s+de|cerca\s+a|estoy\s+en|estoy\s+por|vivo\s+en|ubicado\s+en|chacra\s+en|terreno\s+en|parcela\s+en|en\s+el\s+sector|en\s+la\s+comunidad|en\s+el\s+caserio|sector|comunidad|caserio|centro\s+poblado|distrito\s+de|distrito|provincia\s+de|valle\s+de|desde)\s+([a-z0-9\s]{3,48})",
        cleaned,
    )
    if m:
        raw_place = m.group(1)
    else:
        m2 = re.match(r"^(?:en\s+)?([a-z][a-z0-9\s]{2,28})$", cleaned.strip())
        if not m2:
            return None
        raw_place = m2.group(1)

    raw_place = re.split(
        r"\b(?:que\s+podria|que\s+puedo|que\s+siembro|que\s+cultivo|donde|tengo|solamente|solo|unicamente|cuento|para|con\s+lluvia|sin\s+riego|con\s+riego|no\s+he|no\s+sembre|y\s+tengo|a\s+\d+|en\s+latitud|coordenadas)\b",
        raw_place,
    )[0].strip(" ,.?!")
    ignore = {
        "aqui", "aca", "mi chacra", "mi parcela", "mi terreno", "esta parcela",
        "gps", "mi gps", "mi ubicacion", "todo", "blanco", "campo",
        "secano", "lluvia", "riego", "papa", "maiz", "quinua", "haba",
    }
    if len(raw_place) < 3 or raw_place in ignore:
        return None
    return raw_place


def _extract_seeds_and_no_crop(norm: str) -> Dict[str, Any]:
    """Separates farmer seed inventory constraints from past/current planted crop history."""
    has_no_prior_crop = any(
        k in norm
        for k in [
            "no he sembrado", "no sembre", "nunca he sembrado", "sin cultivo", "terreno nuevo",
            "terreno libre", "tierra nueva", "tierra virgen", "chacra libre", "chacra vacia",
            "nada todavia", "aun nada", "en blanco", "primera vez", "recien voy a sembrar",
            "esta vacio", "todavia nada", "mana tarpusqachu", "ningun cultivo", "ninguno",
            "descansando", "en descanso", "descanso", "barbecho", "purma", "terreno en descanso",
        ]
    )

    wants_all_catalog = any(
        k in norm
        for k in [
            "los 24 cultivos", "todos los cultivos", "todas las semillas", "cualquier semilla",
            "evaluar todo", "sin restriccion", "lo que mejor recomiendes", "no tengo preferencia",
            "no tengo semilla aun", "aun no compro semilla",
        ]
    )

    seed_clauses: List[str] = []
    for pat in (
        r"(?:solo|solamente|unicamente|apenas)\s+(?:tengo|cuento\s+con|dispongo\s+de|poseo)\s+(?:semillas?\s+de\s+)?([^.;!?]+)",
        r"(?:tengo|cuento\s+con|dispongo\s+de)\s+semillas?\s+(?:de\s+)?([^.;!?]+)",
        r"mis\s+semillas\s+(?:son|de)\s+([^.;!?]+)",
    ):
        for m in re.finditer(pat, norm):
            seed_clauses.append(m.group(1))

    filtered_clauses = [
        cl for cl in seed_clauses
        if not re.match(r"^(?:lluvia|agua|riego|pura\s+lluvia|secano)\b", cl.strip())
    ]

    found_seeds: List[str] = []
    if filtered_clauses:
        joined_clauses = " ".join(filtered_clauses)
        for crop_id, _crop_label, aliases in _PERU_CROP_ALIASES:
            if any(re.search(rf"\b{re.escape(al)}\b", joined_clauses) for al in aliases):
                if crop_id not in found_seeds:
                    found_seeds.append(crop_id)

    return {
        "has_no_prior_crop": has_no_prior_crop,
        "wants_all_catalog": wants_all_catalog,
        "available_seeds": found_seeds,
        "seed_clause_found": bool(filtered_clauses or wants_all_catalog),
        "norm_without_seeds": re.sub(
            r"(?:solo|solamente|unicamente)?\s*(?:tengo|cuento\s+con|dispongo\s+de)\s+semillas?\s+(?:de\s+)?[^.;!?]+",
            " ",
            norm,
        ),
    }


def parse_farmer_voice_command(
    transcript: str,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    current_state: Optional[Dict[str, Any]] = None,
    session_slots: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Complex multi-intent agronomic NLU + guided dialogue slot tracker tuned for Peruvian rural Spanish.
    Distinguishes real farmer statements from defaults so unstated crop or water is asked progressively.
    """
    state = dict(current_state or {})
    slots = dict(session_slots or {})
    norm = _normalize_text(transcript)

    lat = float(state.get("lat", -7.1725))
    lon = float(state.get("lon", -78.4630))
    parcel_id = state.get("parcel_id")
    current_crop = str(state.get("current_crop", "sin_cultivo"))
    water_availability = str(state.get("water_availability", "secano"))
    equipment_access = str(state.get("equipment_access", "manual_yunta"))
    market_preference = str(state.get("market_preference", "autoconsumo_feria"))
    farmer_soil = dict(state.get("farmer_soil") or {
        "texture_override": "auto",
        "soil_acidity": "normal",
        "compaction_or_drainage": "normal",
        "local_frost_early": False,
    })

    location_confirmed = bool(slots.get("location_confirmed", False))
    map_verified = bool(slots.get("map_verified", False))
    crop_confirmed = bool(slots.get("crop_confirmed", False))
    water_confirmed = bool(slots.get("water_confirmed", False))
    soil_confirmed = bool(slots.get("soil_confirmed", False))
    climate_risk_confirmed = bool(slots.get("climate_risk_confirmed", False))
    goal_confirmed = bool(slots.get("goal_confirmed", False))
    seeds_checked = bool(slots.get("seeds_checked", False))
    available_seeds: List[str] = [str(s) for s in (slots.get("available_seeds") or state.get("available_seeds") or [])]

    soil_detected_label: Optional[str] = slots.get("soil_label")
    climate_risk_detected_label: Optional[str] = slots.get("climate_risk_label")
    goal_detected_label: Optional[str] = slots.get("goal_label")

    if any(k in norm for k in ["confirmo este punto", "confirmo exactamente mi parcela", "confirmo mi parcela", "ya marque el mapa", "parcela confirmada"]):
        location_confirmed = True
        map_verified = True

    detected_location_label: Optional[str] = slots.get("location_label")
    location_changed_this_turn = False
    coords_matched = False
    use_browser_gps = False
    gps_out_of_region = False

    gps_phrases = [
        "aqui", "donde estoy", "mi ubicacion", "mi gps", "esta parcela",
        "mi chacra aqui", "estoy aca", "mi posicion", "kaypi", "chakraypi",
    ]
    wants_gps = any(p in norm for p in gps_phrases)

    parsed_coords = extract_coordinates_from_text(transcript)
    matched_place = None
    for place in _CAJAMARCA_LOCATIONS:
        if any(re.search(rf"\b{re.escape(kw)}\b", norm) for kw in place["keywords"]):
            matched_place = place
            break

    if parsed_coords is not None:
        lat = float(parsed_coords["lat"])
        lon = float(parsed_coords["lon"])
        parcel_id = None
        coords_matched = True
        location_confirmed = True
        location_changed_this_turn = True
        detected_location_label = f"Coordenadas {lat:.4f}, {lon:.4f}"
    elif matched_place is not None:
        lat = float(matched_place["lat"])
        lon = float(matched_place["lon"])
        parcel_id = matched_place["parcel_id"]
        location_confirmed = True
        location_changed_this_turn = True
        map_verified = False
        detected_location_label = str(matched_place["label"])
    elif wants_gps and gps_lat is not None and gps_lon is not None and _valid_world_coords(gps_lat, gps_lon):
        use_browser_gps = True
        lat = float(gps_lat)
        lon = float(gps_lon)
        parcel_id = None
        location_confirmed = True
        location_changed_this_turn = True
        map_verified = False
        detected_location_label = "Tu ubicación GPS actual"
    elif wants_gps:
        use_browser_gps = True
        gps_out_of_region = True

    seed_bundle = _extract_seeds_and_no_crop(norm)
    if seed_bundle["wants_all_catalog"]:
        available_seeds = []
        seeds_checked = True
    elif seed_bundle["available_seeds"]:
        available_seeds = seed_bundle["available_seeds"]
        seeds_checked = True

    crop_text = seed_bundle["norm_without_seeds"]
    crop_detected_label: Optional[str] = None
    prior_crop_detail: Optional[str] = slots.get("prior_crop_detail")

    if seed_bundle["has_no_prior_crop"]:
        current_crop = "sin_cultivo"
        crop_confirmed = True
        prior_crop_detail = "sin_cultivo"
        crop_detected_label = "Terreno libre (sin cultivo previo)"
    elif any(k in crop_text for k in ["pasto", "pastizal", "vaca", "ganado", "leche", "forraje", "alfalfa", "ryegrass", "trebol", "qachu", "q'achu", "qiwa"]):
        current_crop = "pastos_degradados"
        market_preference = "leche_forraje"
        crop_confirmed = True
        crop_detected_label = "Pastos / Ganadería lechera"
    elif any(k in crop_text for k in ["papa y maiz", "papa con maiz", "maiz", "choclo", "sara"]):
        if ("papa" in crop_text or "akshu" in crop_text) and ("maiz" not in crop_text and "sara" not in crop_text and "choclo" not in crop_text):
            current_crop = "monocultivo_papa"
            crop_detected_label = "Solo Papa antes"
        else:
            current_crop = "papa_maiz"
            crop_detected_label = "Papa y Maíz amiláceo"
        crop_confirmed = True
    elif any(k in crop_text for k in ["cebada", "trigo", "siwara", "triwu"]):
        current_crop = "cebada_trigo_continuo"
        crop_confirmed = True
        crop_detected_label = "Cebada o Trigo continuo"
    elif any(k in crop_text for k in ["papa", "monocultivo", "akshu"]):
        current_crop = "monocultivo_papa"
        crop_confirmed = True
        crop_detected_label = "Solo Papa (monocultivo)"
    else:
        has_history_verb = any(
            k in crop_text
            for k in ["sembre", "antes tuve", "tenia", "vengo de", "coseche", "cultivo anterior", "teniamos", "habia"]
        )
        if has_history_verb:
            for crop_id, c_label, aliases in _PERU_CROP_ALIASES:
                if any(re.search(rf"\b{re.escape(al)}\b", crop_text) for al in aliases):
                    prior_crop_detail = crop_id
                    crop_confirmed = True
                    crop_detected_label = f"Cultivo previo: {c_label}"
                    current_crop = "cebada_trigo_continuo" if crop_id in ("quinua", "kiwicha", "linaza", "avena_vicia") else "papa_maiz"
                    break

    water_detected_label: Optional[str] = None
    _water_rules = (
        ([
            "solo lluvia", "solo tengo lluvia", "solamente tengo lluvia", "solamente lluvia",
            "solo cuento con lluvia", "unicamente lluvia", "apenas lluvia", "apenas tengo lluvia",
            "pura lluvia", "agua de lluvia", "secano", "sin riego", "no tengo riego",
            "no cuento con riego", "no hay agua", "no tengo agua", "dependo de la lluvia",
            "solo dependo de la lluvia", "solo con lluvia", "tamya", "para yaku",
        ], "secano", "Solo lluvia (secano)"),
        (["goteo", "fertirriego", "cinta de riego"], "riego_goteo", "Riego por goteo / fertirriego"),
        (["qocha", "cocha", "cosecha de agua", "reservorio", "microreservorio", "albarrada"], "cosecha_agua_qocha", "Cosecha de agua (Qocha / Reservorio)"),
        (["melga", "surco", "inundacion controlada"], "riego_melgas_surcos", "Riego por melgas y surcos"),
        (["turno", "auxilio", "deficitario", "poquita agua", "poca agua"], "riego_deficitario", "Riego de auxilio / por turnos"),
        (["aspersion", "aspersor", "tecnificado"], "riego_aspersion", "Riego por aspersión"),
        (["acequia", "canal", "gravedad", "con riego", "tengo riego", "yarka"], "riego_gravedad", "Riego por acequia / gravedad"),
    )
    for kws, mode_id, mode_label in _water_rules:
        if any(k in norm for k in kws):
            water_availability = mode_id
            water_detected_label = mode_label
            water_confirmed = True
            break

    soil_notes_detected: List[str] = []
    sat_phrases = [
        "no lo se", "no se", "usa el dato del satelite", "usar dato del satelite",
        "usa el satelite", "lo del satelite", "dato satelital", "detectar automaticamente",
        "soilgrids", "dato de la nasa",
    ]
    said_use_satellite = any(p in norm for p in sat_phrases)

    if not said_use_satellite and any(k in norm for k in ["helada", "hiela", "frio", "escarcha", "cae hielo", "qasa", "chiri", "granizo", "granizada"]):
        farmer_soil["local_frost_early"] = True
        climate_risk_confirmed = True
        climate_risk_detected_label = "Heladas fuertes / tempranas (Qasa)"
        soil_notes_detected.append("Heladas tempranas (Qasa)")
    elif not said_use_satellite and any(k in norm for k in ["zona abrigada", "no cae helada", "sin helada", "templado", "clima normal"]):
        farmer_soil["local_frost_early"] = False
        climate_risk_confirmed = True
        climate_risk_detected_label = "Zona abrigada / sin heladas severas"
    elif not said_use_satellite and any(k in norm for k in ["bipolar", "dias que llueve", "dias que no llueve", "lluvias irregulares", "sequia", "veranillo"]):
        climate_risk_confirmed = True
        climate_risk_detected_label = "Lluvias irregulares / sequía"
        soil_notes_detected.append("Lluvias irregulares / sequía")

    if any(k in norm for k in ["acida", "cansada", "tierra cansada", "puchqu", "saykusqa"]):
        farmer_soil["soil_acidity"] = "acido"
        soil_confirmed = True
        soil_detected_label = "Suelo ácido / cansado"
        soil_notes_detected.append("Suelo ácido/cansado")
    if any(k in norm for k in ["dura", "compactada", "apretada", "sinchi"]):
        farmer_soil["compaction_or_drainage"] = "duro_compactado"
        soil_confirmed = True
        soil_detected_label = "Suelo duro / compactado"
        soil_notes_detected.append("Suelo duro/compactado")
    if any(k in norm for k in ["encharca", "empoza", "barro", "arcilla", "barrosa", "gredosa", "mitu", "turu"]):
        farmer_soil["texture_override"] = "arcilloso_pesado"
        if "encharca" in norm or "empoza" in norm:
            farmer_soil["compaction_or_drainage"] = "se_encharca"
        soil_confirmed = True
        soil_detected_label = "Tierra barrosa / se empoza"
        soil_notes_detected.append("Tierra barrosa / se empoza")
    elif any(k in norm for k in ["arenosa", "arena", "tiyu", "seca rapido"]):
        farmer_soil["texture_override"] = "franco_arenoso"
        soil_confirmed = True
        soil_detected_label = "Tierra arenosa"
        soil_notes_detected.append("Tierra arenosa")
    elif any(k in norm for k in ["piedra", "cascajo", "pedregosa", "rumi", "ranra"]):
        farmer_soil["texture_override"] = "pedregoso"
        soil_confirmed = True
        soil_detected_label = "Tierra cascajosa / con piedra"
        soil_notes_detected.append("Tierra cascajosa / con piedra")
    elif any(k in norm for k in ["tierra negra", "tierra suelta", "franca", "franco", "buena tierra"]):
        farmer_soil["texture_override"] = "franco_arcilloso"
        soil_confirmed = True
        soil_detected_label = "Tierra negra / franca suelta"
        soil_notes_detected.append("Tierra negra / franca")

    if said_use_satellite:
        matched_specific_sat = False
        if "suelo" in norm or "tierra" in norm or "soilgrids" in norm:
            soil_confirmed = True
            soil_detected_label = "Dato satelital SoilGrids + ERA5"
            matched_specific_sat = True
        if "helada" in norm or "clima" in norm or "nasa" in norm:
            climate_risk_confirmed = True
            climate_risk_detected_label = "Dato satelital NASA POWER + DEM"
            matched_specific_sat = True
        if not matched_specific_sat:
            if not soil_confirmed:
                soil_confirmed = True
                soil_detected_label = "Dato satelital SoilGrids + ERA5"
            elif not climate_risk_confirmed:
                climate_risk_confirmed = True
                climate_risk_detected_label = "Dato satelital NASA POWER + DEM"

    if any(k in norm for k in ["mecanizado", "tractor propio", "cosechadora"]):
        equipment_access = "mecanizado"
    elif any(k in norm for k in ["tractor", "maquina", "maquinaria"]):
        equipment_access = "tractor_compartido"
    elif any(k in norm for k in ["yunta", "lampa", "chaquitaclla", "a mano", "manual"]):
        equipment_access = "manual_yunta"

    if any(k in norm for k in ["vender", "mercado", "comercial", "mayorista", "maximizar ganancia", "maxima ganancia", "mas ganancia", "rentabilidad", "mayor ingreso"]):
        if current_crop != "pastos_degradados":
            market_preference = "grano_comercial"
        goal_confirmed = True
        seeds_checked = True
        goal_detected_label = "Venta en mercado / Maximizar ganancia"
    elif any(k in norm for k in ["casa", "autoconsumo", "familia", "feria", "gasto de la casa", "bajo costo"]):
        market_preference = "autoconsumo_feria"
        goal_confirmed = True
        seeds_checked = True
        goal_detected_label = "Consumo de casa y feria local"
    elif any(k in norm for k in ["ganado", "leche", "forraje", "pasto para vacas"]):
        market_preference = "leche_forraje"
        goal_confirmed = True
        seeds_checked = True
        goal_detected_label = "Pasto / Forraje y leche"

    if seeds_checked and not goal_confirmed:
        goal_confirmed = True
        goal_detected_label = goal_detected_label or (
            f"Semillas: {', '.join(available_seeds)}" if available_seeds else "Evaluar los 24 cultivos"
        )

    apply_20yr_projection = any(
        k in norm
        for k in [
            "20 anos", "veinte anos", "2 anos", "dos anos", "futuro", "pronostico",
            "sequia", "cambio climatico", "cambios climaticos", "bipolar",
            "dias que no llueve", "clima cambiante", "2026", "2027", "va a pasar",
        ]
    )

    wants_immediate_plan = any(
        k in norm
        for k in [
            "que cultivos me recomiendas", "que me recomiendas sembrar", "que cultivos quiero sembrar",
            "que cultivos sembrar", "recomiendame cultivos", "trazar todo el plan", "hazme el plan",
            "arma el plan", "dame el plan", "plan de rotacion", "rotacion completa",
        ]
    )
    priority_overrides: Dict[str, float] = {}
    if any(k in norm for k in ["ganancia", "rentab", "ingreso", "comercial", "vender"]):
        priority_overrides["commercial_forage"] = 96.0
    if any(k in norm for k in ["bipolar", "no llueve", "sequia", "cambio climatico", "cambios climaticos", "resistent", "helada"]):
        priority_overrides["water_conservation"] = 95.0
        priority_overrides["erosion_control"] = 85.0
    if any(k in norm for k in ["calidad del suelo", "suelo", "fertilidad", "rotacion"]):
        priority_overrides["soil_fertility"] = 92.0
        priority_overrides["pest_break"] = 86.0

    seed_names_label = [
        next((lbl for cid, lbl, _ in _PERU_CROP_ALIASES if cid == sid), sid)
        for sid in available_seeds
    ]

    return {
        "transcript": transcript,
        "location_matched": matched_place is not None or coords_matched,
        "coords_matched": coords_matched,
        "location_changed": location_changed_this_turn,
        "custom_zone_label": detected_location_label if (matched_place is not None or coords_matched) else None,
        "use_browser_gps": use_browser_gps,
        "gps_out_of_region": gps_out_of_region,
        "apply_20yr_projection": apply_20yr_projection,
        "wants_immediate_plan": wants_immediate_plan,
        "priority_overrides": priority_overrides,
        "climate_stress_concern": None,
        "confirmed_slots": {
            "location_confirmed": location_confirmed,
            "map_verified": map_verified,
            "crop_confirmed": crop_confirmed,
            "water_confirmed": water_confirmed,
            "soil_confirmed": soil_confirmed,
            "climate_risk_confirmed": climate_risk_confirmed,
            "goal_confirmed": goal_confirmed,
            "seeds_checked": seeds_checked,
            "available_seeds": available_seeds,
            "location_label": detected_location_label,
            "prior_crop_detail": prior_crop_detail,
            "crop_label": crop_detected_label or slots.get("crop_label"),
            "water_label": water_detected_label or slots.get("water_label"),
            "soil_label": soil_detected_label,
            "climate_risk_label": climate_risk_detected_label,
            "goal_label": goal_detected_label,
            "last_intent_mode": slots.get("last_intent_mode"),
        },
        "intent_mode": "rotation_planning",
        "direct_reply": "",
        "needs_parcel_data": True,
        "focused_crop_ids": [],
        "ai_location_query": None,
        "understood": {
            "location": detected_location_label or ("Ubicación pendiente de confirmar" if not location_confirmed else "Ubicación de sesión"),
            "crop": crop_detected_label or (str(slots.get("crop_label")) if crop_confirmed and slots.get("crop_label") else "Por confirmar con el agricultor"),
            "water": water_detected_label or (str(slots.get("water_label")) if water_confirmed and slots.get("water_label") else "Por confirmar con el agricultor"),
            "seeds": ", ".join(seed_names_label) if seed_names_label else ("Evaluar los 24 cultivos" if seeds_checked else "Por confirmar si tiene semillas"),
            "soil_notes": soil_notes_detected,
            "forecast_mode": "NASA POWER 20 años (2006–2025) + Copernicus/SRTM DEM",
        },
        "updated_params": {
            "lat": round(lat, 5),
            "lon": round(lon, 5),
            "parcel_id": parcel_id,
            "current_crop": current_crop,
            "water_availability": water_availability,
            "equipment_access": equipment_access,
            "market_preference": market_preference,
            "farmer_soil": farmer_soil,
            "available_seeds": available_seeds,
        },
    }


def build_default_1ha_square(lat: float, lon: float) -> List[List[float]]:
    """Generates a ~1 hectare (~100m x 100m) bounding box square centered on (lat, lon)."""
    d = 0.00045
    return [
        [round(lat - d, 6), round(lon - d, 6)],
        [round(lat - d, 6), round(lon + d, 6)],
        [round(lat + d, 6), round(lon + d, 6)],
        [round(lat + d, 6), round(lon - d, 6)],
    ]


def evaluate_voice_dialogue_state(
    parsed_intent: Dict[str, Any],
    terrain: Dict[str, Any],
    force_calculate: bool = False,
) -> Dict[str, Any]:
    """
    6-Slot State Agent & UI Tool-Calling Evaluator:
    1. poligono_parcela (location_confirmed + map_verified) -> triggers ABRIR_MAPA_CUADRADO if unverified
    2. sistema_riego (water_confirmed)
    3. cultivo_anterior (crop_confirmed)
    4. textura_y_drenaje (soil_confirmed, supports 'Usar dato del satélite SoilGrids')
    5. riesgo_climatico (climate_risk_confirmed, supports 'Usar dato del satélite NASA')
    6. objetivo_agricultor (goal_confirmed / seeds_checked)
    """
    intent_mode = str(parsed_intent.get("intent_mode") or "rotation_planning")
    c_slots = dict(parsed_intent.get("confirmed_slots") or {})
    upd = dict(parsed_intent.get("updated_params") or {})
    lat = float(upd.get("lat") or terrain.get("lat") or -7.163)
    lon = float(upd.get("lon") or terrain.get("lon") or -78.51)

    show_map_picker = bool(
        parsed_intent.get("location_matched")
        or parsed_intent.get("use_browser_gps")
        or (c_slots.get("location_confirmed") and not c_slots.get("map_verified"))
    )

    estado_parcela = {
        "ubicacion_texto": c_slots.get("location_label") or terrain.get("zone_name"),
        "lat": round(lat, 5),
        "lon": round(lon, 5),
        "poligono_confirmado": bool(c_slots.get("location_confirmed") and c_slots.get("map_verified")),
        "sistema_riego": upd.get("water_availability") if c_slots.get("water_confirmed") else None,
        "cultivo_anterior": (
            c_slots.get("prior_crop_detail") or upd.get("current_crop")
            if c_slots.get("crop_confirmed")
            else None
        ),
        "textura_y_drenaje": c_slots.get("soil_label") if c_slots.get("soil_confirmed") else None,
        "riesgo_climatico": c_slots.get("climate_risk_label") if c_slots.get("climate_risk_confirmed") else None,
        "objetivo_agricultor": c_slots.get("goal_label") if (c_slots.get("goal_confirmed") or c_slots.get("seeds_checked")) else None,
        "semillas_disponibles": c_slots.get("available_seeds") or [],
    }

    if intent_mode == "out_of_scope":
        return {
            "conversation_stage": "out_of_scope",
            "missing_fields": [],
            "next_question": None,
            "question_field": None,
            "question_chips": [],
            "show_map_picker": False,
            "assumed_provisional_fields": [],
            "estado_parcela": estado_parcela,
            "accion_ui": {"tipo": "NINGUNA", "parametros": {}},
            "listo_para_nasa": False,
        }

    if intent_mode == "app_help":
        return {
            "conversation_stage": "qa",
            "missing_fields": [],
            "next_question": None,
            "question_field": None,
            "question_chips": [],
            "show_map_picker": False,
            "assumed_provisional_fields": [],
            "estado_parcela": estado_parcela,
            "accion_ui": {"tipo": "NINGUNA", "parametros": {}},
            "listo_para_nasa": False,
        }

    if intent_mode == "parcel_qa" and not force_calculate:
        return {
            "conversation_stage": "qa",
            "missing_fields": [],
            "next_question": None,
            "question_field": None,
            "question_chips": [],
            "show_map_picker": show_map_picker,
            "assumed_provisional_fields": [],
            "estado_parcela": estado_parcela,
            "accion_ui": {
                "tipo": "ABRIR_MAPA_CUADRADO" if (c_slots.get("location_confirmed") and not c_slots.get("map_verified") and parsed_intent.get("location_changed")) else "NINGUNA",
                "parametros": {
                    "lat": round(lat, 5),
                    "lng": round(lon, 5),
                    "zoom": 16,
                    "default_polygon": build_default_1ha_square(lat, lon),
                } if show_map_picker else {},
            },
            "listo_para_nasa": False,
        }

    missing_fields: List[str] = []
    if not c_slots.get("location_confirmed"):
        missing_fields.append("location")
    elif not c_slots.get("map_verified"):
        missing_fields.append("map_polygon")
    if not c_slots.get("water_confirmed"):
        missing_fields.append("water_availability")
    if not c_slots.get("crop_confirmed"):
        missing_fields.append("current_crop")
    if not c_slots.get("soil_confirmed"):
        missing_fields.append("soil")
    if not c_slots.get("climate_risk_confirmed"):
        missing_fields.append("climate_risk")
    if not (c_slots.get("goal_confirmed") or c_slots.get("seeds_checked")):
        missing_fields.append("goal_and_seeds")

    all_six_confirmed = bool(
        c_slots.get("location_confirmed")
        and c_slots.get("map_verified")
        and c_slots.get("water_confirmed")
        and c_slots.get("crop_confirmed")
        and c_slots.get("soil_confirmed")
        and c_slots.get("climate_risk_confirmed")
        and (c_slots.get("goal_confirmed") or c_slots.get("seeds_checked"))
    )

    ready_to_calculate = bool(force_calculate or all_six_confirmed)

    next_question: Optional[str] = None
    question_field: Optional[str] = None
    question_chips: List[Dict[str, str]] = []
    zone_name = str(terrain.get("zone_name") or "tu sector")

    assumed_provisional_fields: List[str] = []
    if ready_to_calculate and not all_six_confirmed:
        if not c_slots.get("crop_confirmed"):
            assumed_provisional_fields.append("cultivo previo (terreno libre)")
        if not c_slots.get("water_confirmed"):
            assumed_provisional_fields.append("agua (secano / solo lluvia)")
        if not c_slots.get("soil_confirmed"):
            assumed_provisional_fields.append("suelo (dato satelital SoilGrids)")
        if not c_slots.get("climate_risk_confirmed"):
            assumed_provisional_fields.append("clima (dato satelital NASA)")

    accion_ui: Dict[str, Any] = {"tipo": "NINGUNA", "parametros": {}}

    if not ready_to_calculate:
        if not c_slots.get("location_confirmed"):
            question_field = "location"
            next_question = "¿En qué sector, distrito o coordenadas queda tu chacra? También puedes usar tu GPS."
            question_chips = [
                {"label": "Usar mi GPS actual", "value": "Usa mi GPS actual"},
                {"label": "Baños del Inca", "value": "Estoy en Baños del Inca"},
                {"label": "Porcón (Jalca)", "value": "Estoy en Porcón"},
                {"label": "Cajabamba", "value": "Estoy en Cajabamba"},
            ]
            accion_ui = {"tipo": "MOSTRAR_PREGUNTA_SLOT", "parametros": {"slot": "location"}}
        elif not c_slots.get("map_verified"):
            question_field = "map_polygon"
            next_question = f"He abierto el mapa en {zone_name}: mueve o ajusta el cuadrado sobre tu chacra y presiona 'Confirmar exactamente tu parcela'."
            question_chips = [
                {"label": "Confirmar este cuadrado de 1 ha", "value": "Confirmo exactamente mi parcela"},
            ]
            accion_ui = {
                "tipo": "ABRIR_MAPA_CUADRADO",
                "parametros": {
                    "lat": round(lat, 5),
                    "lng": round(lon, 5),
                    "zoom": 16,
                    "default_polygon": build_default_1ha_square(lat, lon),
                },
            }
        elif not c_slots.get("water_confirmed"):
            question_field = "water_availability"
            next_question = "¿Tu chacra depende solo de la lluvia o cuentas con acequia, reservorio/qocha o riego tecnificado?"
            question_chips = [
                {"label": "Solo lluvia (secano)", "value": "Solo tengo lluvia, sin riego"},
                {"label": "Acequia / Gravedad", "value": "Tengo riego por acequia / gravedad"},
                {"label": "Qocha / Reservorio", "value": "Uso cosecha de agua / qocha"},
                {"label": "Turnos / Poca agua", "value": "Riego por turnos con poca agua"},
                {"label": "Aspersión", "value": "Tengo riego por aspersión"},
                {"label": "Goteo", "value": "Tengo riego por goteo"},
            ]
            accion_ui = {"tipo": "MOSTRAR_PREGUNTA_SLOT", "parametros": {"slot": "water_availability"}}
        elif not c_slots.get("crop_confirmed"):
            question_field = "current_crop"
            next_question = f"Para cuidar tu tierra en {zone_name}, ¿qué fue lo último que cosechaste ahí la campaña pasada, o ha estado descansando?"
            question_chips = [
                {"label": "Estuvo en descanso / Terreno libre", "value": "No he sembrado nada, el terreno está libre"},
                {"label": "Solo Papa antes", "value": "Sembré solo papa antes"},
                {"label": "Papa y Maíz", "value": "Antes tuve papa y maíz"},
                {"label": "Cebada o Trigo", "value": "Sembré cebada o trigo continuo"},
                {"label": "Pastos / Ganado", "value": "Tengo pastos para ganado"},
            ]
            accion_ui = {"tipo": "MOSTRAR_PREGUNTA_SLOT", "parametros": {"slot": "current_crop"}}
        elif not c_slots.get("soil_confirmed"):
            question_field = "soil"
            next_question = "¿Tu tierra es más negra/franca, arenosa o barrosa que se empoza? (Si no estás seguro, usa el dato del satélite)"
            question_chips = [
                {"label": "No lo sé (Usar dato del satélite SoilGrids)", "value": "No sé cómo es mi suelo, usa el dato del satélite SoilGrids"},
                {"label": "Tierra negra / franca suelta", "value": "Mi tierra es negra y suelta"},
                {"label": "Tierra barrosa / se empoza", "value": "Mi tierra es barrosa y se empoza"},
                {"label": "Tierra arenosa (seca rápido)", "value": "Mi tierra es arenosa"},
                {"label": "Tierra cascajosa / con piedra", "value": "Mi tierra tiene piedra y cascajo"},
                {"label": "Tierra ácida / cansada", "value": "Mi tierra es ácida o cansada"},
            ]
            accion_ui = {"tipo": "MOSTRAR_PREGUNTA_SLOT", "parametros": {"slot": "soil"}}
        elif not c_slots.get("climate_risk_confirmed"):
            question_field = "climate_risk"
            next_question = "En esa parte de tu sector, ¿caen heladas fuertes o lluvias muy irregulares? (Si no estás seguro, usa el dato del satélite)"
            question_chips = [
                {"label": "No lo sé (Usar dato del satélite NASA)", "value": "No sé el riesgo de heladas, usa el dato del satélite NASA"},
                {"label": "Caen heladas fuertes (Qasa)", "value": "Aquí cae bastante helada en las madrugadas"},
                {"label": "Lluvias muy irregulares / sequía", "value": "El clima está bipolar con días secos y lluvias irregulares"},
                {"label": "Zona abrigada (poca helada)", "value": "Es zona abrigada sin heladas fuertes"},
            ]
            accion_ui = {"tipo": "MOSTRAR_PREGUNTA_SLOT", "parametros": {"slot": "climate_risk"}}
        else:
            question_field = "goal_and_seeds"
            next_question = "¿Buscas cultivos para vender en el mercado, para consumo de casa o forraje para ganado? ¿Tienes alguna semilla o evalúo las 24?"
            question_chips = [
                {"label": "Vender en mercado (Evaluar las 24)", "value": "Quiero cultivos para vender en el mercado y evalúa las 24 semillas"},
                {"label": "Consumo de casa y feria", "value": "Busco cultivos para consumo de la casa y feria"},
                {"label": "Pasto y forraje para ganado", "value": "Busco pasto y forraje para ganado lechero"},
                {"label": "Tengo semilla de Quinua y Haba", "value": "Quiero vender y tengo semilla de quinua y haba"},
                {"label": "Tengo semilla de Cebada y Tarwi", "value": "Tengo semilla de cebada y tarwi"},
            ]
            accion_ui = {"tipo": "MOSTRAR_PREGUNTA_SLOT", "parametros": {"slot": "goal_and_seeds"}}
    else:
        accion_ui = {
            "tipo": "MOSTRAR_TRES_ROTACIONES",
            "parametros": {"lat": round(lat, 5), "lng": round(lon, 5)},
        }

    return {
        "conversation_stage": "ready" if ready_to_calculate else "collecting_info",
        "missing_fields": missing_fields,
        "next_question": next_question,
        "question_field": question_field,
        "question_chips": question_chips,
        "show_map_picker": show_map_picker,
        "assumed_provisional_fields": assumed_provisional_fields,
        "estado_parcela": estado_parcela,
        "accion_ui": accion_ui,
        "listo_para_nasa": ready_to_calculate,
    }


def build_collecting_spoken_response(
    terrain: Dict[str, Any],
    biophysical: Dict[str, Any],
    parsed_intent: Dict[str, Any],
    dialogue_state: Dict[str, Any],
) -> Dict[str, Any]:
    """Builds a real NASA telemetry preview + guided follow-up question before strategy calculation."""
    elev = int(round(float(terrain["elevation_m"])))
    zone = str(terrain["zone_name"])
    belt = str(terrain.get("agro_belt_name") or terrain.get("zone_type") or "")
    bio_sum = biophysical.get("summary") or {}
    ann_rain = int(round(float(bio_sum.get("annual_precip_mm", 750.0))))
    t_mean = float(bio_sum.get("mean_temp_c", 12.0))
    frost_months = len(bio_sum.get("frost_risk_months") or [])
    next_q = str(dialogue_state.get("next_question") or "")

    map_hint = (
        "Abajo puedes abrir el mapa satelital para mover el punto exacto o dibujar tu parcela. "
        if dialogue_state.get("show_map_picker")
        else ""
    )
    spoken_text = (
        f"Ubiqué tu sector en {zone} a {elev} metros sobre el nivel del mar ({belt}). "
        f"Según datos reales de la NASA allí llueven {ann_rain} milímetros al año, temperatura media de {t_mean:.1f} grados "
        f"y {frost_months} meses con riesgo de helada. "
        f"{map_hint}{next_q}"
    ).strip()

    quick_cards = [
        {
            "title": "1. Lectura Satelital Real (NASA POWER + DEM)",
            "badge": f"{elev} m s.n.m. · {t_mean:.1f} °C",
            "body": (
                f"{zone} ({belt}). Precipitación NASA: {ann_rain} mm/año · "
                f"Pendiente: {terrain['slope_pct']:.1f}% · Heladas: {terrain.get('frost_risk_window', 'Según piso')}."
            ),
        },
        {
            "title": "2. Siguiente dato para tu rotación",
            "badge": f"Faltan {len(dialogue_state.get('missing_fields') or [])}",
            "body": next_q or "Listo para calcular estrategias con los 24 cultivos.",
        },
    ]
    return {
        "spoken_text": spoken_text,
        "quick_cards": quick_cards,
    }


def build_spoken_farmer_response(
    terrain: Dict[str, Any],
    biophysical: Dict[str, Any],
    recommendation: Dict[str, Any],
    parsed_intent: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generates a warm, clear spoken summary (~70 words) and 3 structured quick cards
    grounded in real NASA telemetry, confirmed farmer inputs, and the 24-crop selector.
    """
    rec_id = recommendation["recommended_strategy_id"]
    best = next(
        (s for s in recommendation["strategies"] if s["id"] == rec_id),
        recommendation["strategies"][0],
    )
    seasonal = recommendation.get("seasonal_context") or {}
    outlook = recommendation.get("climate_outlook_20yr") or {}
    seed_sum = recommendation.get("seed_constraint_summary") or {}
    c20 = biophysical.get("climate_20yr") or {}
    trends = c20.get("trends") or {}

    elev = int(round(float(terrain["elevation_m"])))
    zone = str(terrain["zone_name"])
    belt = str(terrain.get("agro_belt_name") or terrain.get("zone_type") or "")
    soil_prof = terrain.get("soil_profile") or {}
    soil_ph = soil_prof.get("ph")
    soil_tex = str(soil_prof.get("texture_class") or terrain.get("soil_texture") or "franco")
    temp_20 = float(trends.get("temp_delta_20yr_c", 0.5))
    precip_20 = float(trends.get("precip_delta_20yr_pct", -5.0))
    rain_word = "menos lluvia" if precip_20 < -1.0 else "lluvias más irregulares"

    phase_crops = [ph["crop_name"] for ph in best["phases"][:3]]
    route_spoken = ", luego ".join(phase_crops)

    optimal_list = [
        c["crop_name"]
        for c in outlook.get("crop_viability", [])
        if c.get("status_2027") == "optimo_resiliente"
    ]
    viable_list = [
        c["crop_name"]
        for c in outlook.get("crop_viability", [])
        if c.get("status_2027") == "viable_con_rotacion"
    ]
    combined_viable = (optimal_list + viable_list)[:4]
    local_midagri = [str(x) for x in (terrain.get("traditional_local_crops") or [])]
    resilient_str = (
        ", ".join(combined_viable)
        if combined_viable
        else (", ".join(local_midagri[:4]) if local_midagri else best["phases"][0]["crop_name"])
    )

    unviable = seed_sum.get("unviable") or []
    seed_note = ""
    if unviable:
        seed_note = f"Ojo: {unviable[0]['crop_name']} no resiste el clima a esta altura ({unviable[0]['reason']}). "
    elif seed_sum.get("viable_used"):
        seed_note = "Prioricé tus semillas disponibles. "

    soil_phrase = f" y suelo con pH {float(soil_ph):.1f}" if soil_ph is not None else ""
    immediate = str(seasonal.get("immediate_action", "Mantén cobertura vegetal para cuidar la humedad."))
    spoken_text = (
        f"Ubicado en {zone} a {elev} metros ({belt}{soil_phrase}). "
        f"El historial NASA de 20 años muestra +{temp_20:.1f} grados con {rain_word}. "
        f"{seed_note}"
        f"Con los 24 cultivos evaluados, tu mejor rotación para 2 años es: {route_spoken}. "
        f"Este mes: {immediate}"
    )

    benefits = best["explainability"]["quantified_benefits"]
    ph_badge = f" · pH {float(soil_ph):.1f}" if soil_ph is not None else ""
    quick_cards = [
        {
            "title": "1. Ubicación NASA y Suelo",
            "badge": f"{elev} m s.n.m.{ph_badge}",
            "body": (
                f"{zone} ({soil_tex}, pendiente {terrain['slope_pct']:.1f}%). "
                f"Historial 2006–2025: +{temp_20:.1f} °C y {precip_20:+.1f}% lluvia → proyección 2026–2027."
            ),
        },
        {
            "title": "2. Cultivos viables (Catálogo 24)",
            "badge": f"Riesgo {str(outlook.get('risk_level', 'moderado')).upper()}",
            "body": (
                (f"Alerta semilla: {unviable[0]['crop_name']} ({unviable[0]['reason']}). " if unviable else "")
                + f"Aptos en esta altura: {resilient_str}. "
                + f"Este mes: {immediate}"
            ),
        },
        {
            "title": "3. Rotación Recomendada (2 Años)",
            "badge": f"{best['mcda_score']:.0f}/100 pts",
            "body": (
                f"Secuencia: {' → '.join(phase_crops)}. "
                f"Ahorra {benefits['water_savings_pct']:.0f}% de agua, frena {benefits['erosion_reduction_pct']:.0f}% la erosión "
                f"y cubre {benefits['bare_months_avoided']} meses extra."
            ),
        },
    ]

    return {
        "spoken_text": spoken_text,
        "quick_cards": quick_cards,
    }


def _build_crop_catalog_prompt_index() -> str:
    crops = load_crops_data().get("crops") or []
    return ", ".join(f"{c['id']} ({c['name']})" for c in crops)


def _match_location_from_query(query_text: str) -> Optional[Dict[str, Any]]:
    norm_q = _normalize_text(query_text)
    if not norm_q:
        return None
    for place in _CAJAMARCA_LOCATIONS:
        if any(re.search(rf"\b{re.escape(kw)}\b", norm_q) for kw in place["keywords"]):
            return place
    return None


def merge_ai_understanding_with_deterministic(
    det_parsed: Dict[str, Any],
    ai_parsed: Optional[Dict[str, Any]],
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
) -> Dict[str, Any]:
    """Combines deterministic extraction with Gemini NLU structured understanding."""
    if not ai_parsed:
        return det_parsed

    valid_crop_ids = {str(c["id"]) for c in (load_crops_data().get("crops") or [])}
    c_slots = dict(det_parsed["confirmed_slots"])
    upd = dict(det_parsed["updated_params"])
    understood = dict(det_parsed["understood"])
    soil = dict(upd.get("farmer_soil") or {})
    soil_notes = list(understood.get("soil_notes") or [])

    intent_mode = str(ai_parsed.get("intent_mode") or "rotation_planning")
    if intent_mode not in {"out_of_scope", "app_help", "parcel_qa", "rotation_planning"}:
        intent_mode = "rotation_planning"

    det_parsed["intent_mode"] = intent_mode
    det_parsed["wants_immediate_plan"] = bool(
        ai_parsed.get("wants_immediate_plan") or det_parsed.get("wants_immediate_plan")
    )
    det_parsed["climate_stress_concern"] = str(ai_parsed.get("climate_stress_concern") or "").strip() or None
    det_parsed["direct_reply"] = str(ai_parsed.get("direct_reply") or "").strip()
    det_parsed["needs_parcel_data"] = bool(ai_parsed.get("needs_parcel_data", True))
    c_slots["last_intent_mode"] = intent_mode

    goals_prio = ai_parsed.get("goals_priority")
    if isinstance(goals_prio, dict):
        prio_map = dict(det_parsed.get("priority_overrides") or {})
        key_bridge = (
            ("commercial_profit", "commercial_forage"),
            ("drought_climate_resilience", "water_conservation"),
            ("soil_health", "soil_fertility"),
            ("erosion_control", "erosion_control"),
            ("pest_break", "pest_break"),
        )
        for src_k, dst_k in key_bridge:
            val = goals_prio.get(src_k)
            if val is not None and isinstance(val, (int, float)):
                prio_map[dst_k] = float(max(20.0, min(100.0, val)))
        det_parsed["priority_overrides"] = prio_map

    focused_raw = ai_parsed.get("focused_crop_ids") or []
    det_parsed["focused_crop_ids"] = [
        str(cid) for cid in focused_raw if str(cid) in valid_crop_ids
    ]

    if intent_mode in {"out_of_scope", "app_help"}:
        det_parsed["confirmed_slots"] = c_slots
        return det_parsed

    # 1. Location merge (only override if deterministic didn't already match explicit coords/place)
    ai_coords = ai_parsed.get("coords")
    ai_loc_q = str(ai_parsed.get("location_query") or "").strip()
    if not det_parsed.get("location_matched") and not det_parsed.get("use_browser_gps"):
        if isinstance(ai_coords, dict):
            clat = ai_coords.get("lat")
            clon = ai_coords.get("lon")
            if isinstance(clat, (int, float)) and isinstance(clon, (int, float)) and _valid_world_coords(float(clat), float(clon)):
                same_as_current = (
                    c_slots.get("location_confirmed")
                    and abs(float(clat) - float(upd["lat"])) < 0.002
                    and abs(float(clon) - float(upd["lon"])) < 0.002
                )
                if not same_as_current:
                    upd["lat"] = round(float(clat), 5)
                    upd["lon"] = round(float(clon), 5)
                    upd["parcel_id"] = None
                    det_parsed["coords_matched"] = True
                    det_parsed["location_matched"] = True
                    det_parsed["location_changed"] = True
                    c_slots["location_confirmed"] = True
                    c_slots["map_verified"] = False
                    lbl = f"Coordenadas {upd['lat']:.4f}, {upd['lon']:.4f}"
                    c_slots["location_label"] = lbl
                    understood["location"] = lbl
                    det_parsed["custom_zone_label"] = lbl
        elif ai_loc_q:
            matched = _match_location_from_query(ai_loc_q)
            if matched is not None:
                same_as_current = (
                    c_slots.get("location_confirmed")
                    and abs(float(matched["lat"]) - float(upd["lat"])) < 0.002
                    and abs(float(matched["lon"]) - float(upd["lon"])) < 0.002
                )
                if not same_as_current:
                    upd["lat"] = float(matched["lat"])
                    upd["lon"] = float(matched["lon"])
                    upd["parcel_id"] = matched["parcel_id"]
                    det_parsed["location_matched"] = True
                    det_parsed["location_changed"] = True
                    c_slots["location_confirmed"] = True
                    c_slots["map_verified"] = False
                    lbl = str(matched["label"])
                    c_slots["location_label"] = lbl
                    understood["location"] = lbl
                    det_parsed["custom_zone_label"] = lbl
            elif not c_slots.get("location_confirmed"):
                det_parsed["ai_location_query"] = ai_loc_q
        elif ai_parsed.get("use_gps") and not c_slots.get("location_confirmed"):
            det_parsed["use_browser_gps"] = True
            if gps_lat is not None and gps_lon is not None and _valid_world_coords(gps_lat, gps_lon):
                upd["lat"] = round(float(gps_lat), 5)
                upd["lon"] = round(float(gps_lon), 5)
                upd["parcel_id"] = None
                det_parsed["location_changed"] = True
                c_slots["location_confirmed"] = True
                c_slots["map_verified"] = False
                c_slots["location_label"] = "Tu ubicación GPS actual"
                understood["location"] = "Tu ubicación GPS actual"
            else:
                det_parsed["gps_out_of_region"] = True

    # 2. Crop history merge (do not let AI assume 'sin_cultivo' unless deterministic parser saw resting/free land keywords)
    ai_crop = ai_parsed.get("current_crop")
    if (
        ai_crop in _VALID_CURRENT_CROPS
        and ai_crop != "sin_cultivo"
        and (not c_slots.get("crop_confirmed") or ai_crop != upd.get("current_crop"))
    ):
        upd["current_crop"] = str(ai_crop)
        c_slots["crop_confirmed"] = True
        lbl = _CURRENT_CROP_LABELS.get(str(ai_crop), str(ai_crop))
        c_slots["crop_label"] = lbl
        understood["crop"] = lbl

    ai_prior_detail = ai_parsed.get("prior_crop_detail")
    if isinstance(ai_prior_detail, str) and ai_prior_detail in valid_crop_ids:
        c_slots["prior_crop_detail"] = ai_prior_detail
        if not c_slots.get("crop_confirmed"):
            c_slots["crop_confirmed"] = True
            crop_lbl = _CROP_LABELS_BY_ID.get(ai_prior_detail, ai_prior_detail)
            c_slots["crop_label"] = f"Cultivo previo: {crop_lbl}"
            understood["crop"] = c_slots["crop_label"]

    # 3. Water availability merge
    ai_water = ai_parsed.get("water_availability")
    if ai_water in _VALID_WATER_MODES:
        upd["water_availability"] = str(ai_water)
        c_slots["water_confirmed"] = True
        w_lbl = _WATER_MODE_LABELS.get(str(ai_water), str(ai_water))
        c_slots["water_label"] = w_lbl
        understood["water"] = w_lbl

    # 4. Seeds merge
    ai_seeds = ai_parsed.get("available_seeds")
    if ai_parsed.get("wants_all_catalog"):
        upd["available_seeds"] = []
        c_slots["available_seeds"] = []
        c_slots["seeds_checked"] = True
        c_slots["goal_confirmed"] = True
        c_slots["goal_label"] = c_slots.get("goal_label") or "Evaluar los 24 cultivos"
        understood["seeds"] = "Evaluar los 24 cultivos"
    elif isinstance(ai_seeds, list):
        clean_seeds = [str(s) for s in ai_seeds if str(s) in valid_crop_ids]
        if clean_seeds:
            upd["available_seeds"] = clean_seeds
            c_slots["available_seeds"] = clean_seeds
            c_slots["seeds_checked"] = True
            c_slots["goal_confirmed"] = True
            seeds_txt = ", ".join(
                _CROP_LABELS_BY_ID.get(s, s) for s in clean_seeds
            )
            c_slots["goal_label"] = c_slots.get("goal_label") or f"Semillas: {seeds_txt}"
            understood["seeds"] = seeds_txt

    # 5. Soil, frost, equipment, market & 20yr projection merge
    if ai_parsed.get("soil_texture") in {"franco_arcilloso", "franco_arenoso", "arcilloso_pesado", "pedregoso"}:
        soil["texture_override"] = str(ai_parsed["soil_texture"])
        c_slots["soil_confirmed"] = True
        note_map = {
            "arcilloso_pesado": "Tierra barrosa / arcilla pesada",
            "franco_arenoso": "Tierra arenosa",
            "pedregoso": "Tierra cascajosa / con piedra",
            "franco_arcilloso": "Tierra negra / franca",
        }
        txt_note = note_map[soil["texture_override"]]
        c_slots["soil_label"] = txt_note
        if txt_note not in soil_notes:
            soil_notes.append(txt_note)

    if ai_parsed.get("soil_acidity") in {"normal", "acido", "no_se"}:
        soil["soil_acidity"] = str(ai_parsed["soil_acidity"])
        if soil["soil_acidity"] == "acido":
            c_slots["soil_confirmed"] = True
            c_slots["soil_label"] = c_slots.get("soil_label") or "Suelo ácido / cansado"
            if "Suelo ácido/cansado" not in soil_notes:
                soil_notes.append("Suelo ácido/cansado")

    if ai_parsed.get("compaction_or_drainage") in {"normal", "duro_compactado", "se_encharca"}:
        soil["compaction_or_drainage"] = str(ai_parsed["compaction_or_drainage"])
        if soil["compaction_or_drainage"] == "duro_compactado":
            c_slots["soil_confirmed"] = True
            c_slots["soil_label"] = c_slots.get("soil_label") or "Suelo duro / compactado"
            if "Suelo duro/compactado" not in soil_notes:
                soil_notes.append("Suelo duro/compactado")
        elif soil["compaction_or_drainage"] == "se_encharca":
            c_slots["soil_confirmed"] = True
            c_slots["soil_label"] = c_slots.get("soil_label") or "Tierra se empoza"
            if "Tierra se empoza" not in soil_notes:
                soil_notes.append("Tierra se empoza")

    if c_slots.get("climate_risk_label") != "Dato satelital NASA POWER + DEM":
        if ai_parsed.get("local_frost_early") is True:
            soil["local_frost_early"] = True
            c_slots["climate_risk_confirmed"] = True
            c_slots["climate_risk_label"] = "Heladas tempranas (Qasa)"
            if "Heladas tempranas (Qasa)" not in soil_notes:
                soil_notes.append("Heladas tempranas (Qasa)")
        elif ai_parsed.get("local_frost_early") is False:
            soil["local_frost_early"] = False
            c_slots["climate_risk_confirmed"] = True
            c_slots["climate_risk_label"] = c_slots.get("climate_risk_label") or "Zona abrigada / sin helada fuerte"

    if det_parsed.get("climate_stress_concern"):
        c_slots["climate_risk_confirmed"] = True
        c_slots["climate_risk_label"] = det_parsed["climate_stress_concern"]

    if ai_parsed.get("equipment_access") in {"manual_yunta", "tractor_compartido", "mecanizado"}:
        upd["equipment_access"] = str(ai_parsed["equipment_access"])
    if ai_parsed.get("market_preference") in {"autoconsumo_feria", "leche_forraje", "grano_comercial"}:
        upd["market_preference"] = str(ai_parsed["market_preference"])
        c_slots["goal_confirmed"] = True
        c_slots["seeds_checked"] = True
        mkt_labels = {
            "grano_comercial": "Venta en mercado / Mayor ganancia",
            "autoconsumo_feria": "Consumo familiar y feria",
            "leche_forraje": "Forraje y leche",
        }
        c_slots["goal_label"] = mkt_labels.get(str(ai_parsed["market_preference"]))
    if c_slots.get("seeds_checked") and not c_slots.get("goal_confirmed"):
        c_slots["goal_confirmed"] = True
        c_slots["goal_label"] = understood.get("seeds")
    if ai_parsed.get("apply_20yr_projection"):
        det_parsed["apply_20yr_projection"] = True

    upd["farmer_soil"] = soil
    understood["soil_notes"] = soil_notes
    det_parsed["confirmed_slots"] = c_slots
    det_parsed["updated_params"] = upd
    det_parsed["understood"] = understood
    return det_parsed


def _build_focused_crops_context(
    crop_ids: List[str],
    terrain: Dict[str, Any],
    biophysical: Dict[str, Any],
    recommendation: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Builds exact agronomic specs + suitability notes for crops mentioned by the farmer."""
    all_crops = {str(c["id"]): c for c in (load_crops_data().get("crops") or [])}
    elev = float(terrain.get("elevation_m") or 2700.0)
    slope = float(terrain.get("slope_pct") or 5.0)
    bio_sum = biophysical.get("summary") or {}
    ann_rain = float(bio_sum.get("annual_precip_mm") or 750.0)
    min_temp = float(bio_sum.get("min_temp_c") or 5.0)
    soil_prof = terrain.get("soil_profile") or {}
    soil_tex = str(soil_prof.get("texture_class") or terrain.get("soil_texture") or "")

    viability_map: Dict[str, Dict[str, Any]] = {}
    if recommendation:
        for item in (recommendation.get("climate_outlook_20yr") or {}).get("crop_viability") or []:
            viability_map[str(item.get("crop_id"))] = item

    target_ids = list(dict.fromkeys(cid for cid in crop_ids if cid in all_crops))
    if not target_ids and viability_map:
        target_ids = [
            cid
            for cid, v in viability_map.items()
            if v.get("status_2027") in {"optimo_resiliente", "viable_con_rotacion"}
        ][:5]

    out: List[Dict[str, Any]] = []
    for cid in target_ids[:8]:
        c = all_crops[cid]
        alt_min = float(c.get("altitude_min_m", 0))
        alt_max = float(c.get("altitude_max_m", 4500))
        max_slope = float(c.get("max_slope_pct", 35))
        frost_crit = float(c.get("frost_critical_c", 0.0))
        w_min, w_max = c.get("water_req_range_mm", [300, 900])

        issues: List[str] = []
        if elev < alt_min:
            issues.append(f"Por debajo de su rango altitudinal ({int(elev)} m vs {int(alt_min)}–{int(alt_max)} m)")
        elif elev > alt_max:
            issues.append(f"Supera su altitud máxima ({int(elev)} m vs máx {int(alt_max)} m)")
        if slope > max_slope:
            issues.append(f"Pendiente exigente ({slope:.1f}% vs máx {int(max_slope)}%)")
        if min_temp < frost_crit:
            issues.append(f"Riesgo de daño por frío ({min_temp:.1f} °C mín. vs umbral {frost_crit:.1f} °C)")
        if ann_rain < w_min:
            issues.append(f"Lluvia anual ({int(ann_rain)} mm) menor a su requerimiento ({w_min}–{w_max} mm); necesita riego")

        viab = viability_map.get(cid)
        out.append(
            {
                "id": cid,
                "name": c["name"],
                "altitude_range_m": [int(alt_min), int(alt_max)],
                "water_req_mm": [int(w_min), int(w_max)],
                "frost_label": c.get("frost_label"),
                "drought_label": c.get("drought_label"),
                "cycle_months": c.get("cycle_months"),
                "nitrogen_balance_kg_ha": c.get("nitrogen_balance_kg_ha"),
                "breaks_pests": c.get("breaks_pests", []),
                "vulnerable_pests": c.get("vulnerable_pests", []),
                "farmer_tip": c.get("farmer_tip"),
                "market_note": c.get("market_note"),
                "parcel_fit_alerts": issues,
                "outlook_2027_status": viab.get("status_2027") if viab else None,
                "soil_context": soil_tex,
            }
        )
    return out


def build_deterministic_qa_response(
    terrain: Dict[str, Any],
    biophysical: Dict[str, Any],
    parsed_intent: Dict[str, Any],
    dialogue_state: Dict[str, Any],
) -> Dict[str, Any]:
    """Deterministic fallback for parcel_qa when Gemini is unavailable."""
    elev = int(round(float(terrain["elevation_m"])))
    zone = str(terrain["zone_name"])
    belt = str(terrain.get("agro_belt_name") or terrain.get("zone_type") or "")
    bio_sum = biophysical.get("summary") or {}
    ann_rain = int(round(float(bio_sum.get("annual_precip_mm", 750.0))))
    t_mean = float(bio_sum.get("mean_temp_c", 12.0))
    soil_prof = terrain.get("soil_profile") or {}
    ph_txt = f", pH {float(soil_prof['ph']):.1f}" if soil_prof.get("ph") is not None else ""
    tex = str(soil_prof.get("texture_class") or terrain.get("soil_texture") or "franco")
    local_crops = ", ".join((terrain.get("traditional_local_crops") or [])[:4]) or "papa, cebada, haba"

    map_hint = (
        " Abajo puedes abrir el mapa para ajustar el punto exacto de tu chacra."
        if dialogue_state.get("show_map_picker")
        else ""
    )
    spoken = (
        f"En {zone} estás a {elev} metros ({belt}), con {ann_rain} milímetros de lluvia al año, "
        f"temperatura media de {t_mean:.1f} grados y suelo {tex}{ph_txt}. "
        f"Cultivos típicos de este piso: {local_crops}.{map_hint}"
    )
    cards = [
        {
            "title": "1. Clima y Altitud NASA",
            "badge": f"{elev} m s.n.m. · {t_mean:.1f} °C",
            "body": f"{zone} ({belt}). Lluvia: {ann_rain} mm/año · Heladas: {terrain.get('frost_risk_window', 'Según piso')}.",
        },
        {
            "title": "2. Suelo y Cultivos de Zona",
            "badge": tex,
            "body": f"Textura {tex}{ph_txt}. Cultivos adaptados: {local_crops}.",
        },
    ]
    return {"spoken_text": spoken, "quick_cards": cards}

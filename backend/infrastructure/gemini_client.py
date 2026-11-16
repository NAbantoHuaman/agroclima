"""Gemini REST multimodal STT, structured NLU understanding, and grounded synthesis client."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Dict, List, Optional

import httpx

from config import get_gemini_api_key, get_gemini_model, has_gemini_api_key
from domain.catalog import load_crops_data
from domain.voice_dialogue import _build_crop_catalog_prompt_index, _build_focused_crops_context


async def _call_gemini_generate_content(
    parts: List[Dict[str, Any]],
    *,
    system_instruction: Optional[str] = None,
    response_json_schema: Optional[Dict[str, Any]] = None,
    thinking_level: str = "MINIMAL",
    temperature: float = 0.2,
    max_output_tokens: int = 900,
    timeout: float = 10.0,
) -> Optional[str]:
    """Calls Gemini REST generateContent using x-goog-api-key and the configured model."""
    api_key = get_gemini_api_key()
    if not api_key:
        return None

    model = get_gemini_model()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    gen_config: Dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": max_output_tokens,
        "thinkingConfig": {"thinkingLevel": thinking_level},
    }
    if response_json_schema is not None:
        gen_config["responseMimeType"] = "application/json"
        gen_config["responseJsonSchema"] = response_json_schema

    payload: Dict[str, Any] = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": gen_config,
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    url,
                    headers={
                        "x-goog-api-key": api_key,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
            break
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {429, 500, 502, 503, 504} and attempt == 0:
                await asyncio.sleep(0.35)
                continue
            print(f"[Gemini HTTP {exc.response.status_code}] {exc.response.text[:220]}", flush=True)
            return None
        except Exception as exc:
            if attempt == 0:
                await asyncio.sleep(0.25)
                continue
            print(f"[Gemini Error] {type(exc).__name__}: {exc}", flush=True)
            return None

    cand_parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts") or []
    text_chunks = [
        str(p.get("text", ""))
        for p in cand_parts
        if not p.get("thought") and p.get("text")
    ]
    joined = "".join(text_chunks).strip()
    return joined or None


async def ai_understand_farmer_turn(
    transcript: str,
    current_state: Dict[str, Any],
    session_slots: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Uses Gemini 3.5 Flash-Lite structured output to classify farmer intent
    (out_of_scope / app_help / parcel_qa / rotation_planning) and extract
    agronomic parameters without losing conversational context.
    """
    if not has_gemini_api_key() or not transcript.strip():
        return None

    crops_index = _build_crop_catalog_prompt_index()
    slots = dict(session_slots or {})
    hist_lines = []
    for item in (history or [])[-6:]:
        role = "Agricultor" if item.get("role") == "user" else "Ingeniero"
        txt = str(item.get("text") or "").strip()
        if txt:
            hist_lines.append(f"{role}: {txt[:220]}")
    hist_block = "\n".join(hist_lines) if hist_lines else "(inicio de conversación)"

    system_prompt = (
        "Eres el módulo de comprensión NLU de AgroRumbo Cajamarca (NASA Space Apps), una app móvil agrícola para Cajamarca y el Perú.\n"
        "Debes clasificar el mensaje del agricultor y extraer solo lo que el agricultor REALMENTE dijo (sin inventar ni asumir datos no mencionados).\n\n"
        "Modos de `intent_mode`:\n"
        "1. `out_of_scope`: preguntas totalmente ajenas a agricultura, clima, suelo, agua, cultivos, semillas o uso de la app (ej. deportes, chistes, política, dólar, recetas de cocina, programación).\n"
        "   - En este modo, llena `direct_reply` con una respuesta amable en español (<=50 palabras) diciendo que solo ayudas con temas agrícolas, clima, suelo y cultivos de su parcela.\n"
        "2. `app_help`: preguntas sobre cómo usar la app AgroRumbo (pestañas Inicio, Mapa, Plan, Semillas, dibujar polígono, simulador climático).\n"
        "   - Llena `direct_reply` explicando brevemente cómo usar esa función.\n"
        "3. `parcel_qa`: pregunta puntual informativa sin pedir armar plan todavía (ej. '¿cómo está el clima en Cajabamba?', 'tengo suelo arcilloso y semillas de quinua y palta en Cajabamba, ¿qué pasa si siembro eso?', '¿qué cultivo resiste heladas?').\n"
        "   - NO uses `parcel_qa` si pide explícitamente qué cultivos sembrar, maximizar ganancia, armar su plan o diseñar una rotación para su chacra.\n"
        "4. `rotation_planning`: pide recomendaciones de qué sembrar, cómo maximizar ganancia/resiliencia o armar un plan de rotación a 2 años según clima, suelo o altitud; o responde datos de su parcela.\n"
        "   - Pon `wants_immediate_plan = true` cuando el agricultor pide directamente recomendaciones de cultivos, rentabilidad, resistencia climática o trazar un plan completo en este turno (aunque no haya dicho qué sembró antes o su riego).\n"
        "   - Pon `wants_immediate_plan = false` si solo dio su ubicación o saludo ('estoy en Cajabamba', 'hola') o responde un dato suelto del cuestionario.\n"
        "   - Si el mensaje es solo confirmar un punto del mapa ('confirmo este punto exacto') y `last_intent_mode` era `parcel_qa`, mantén `parcel_qa`.\n\n"
        f"Catálogo válido de 24 `crop_id`: {crops_index}.\n"
        "Reglas estrictas:\n"
        "- NO confundas cultivo previo (`current_crop`) con semillas disponibles hoy (`available_seeds`).\n"
        "- Si dice 'terreno libre', 'nunca he sembrado', 'tierra nueva', `current_crop` = 'sin_cultivo'.\n"
        "- Si no mencionó cultivo previo ni dijo que está libre, deja `current_crop` = null.\n"
        "- Si no mencionó tipo de agua o riego concreto, deja `water_availability` = null (salvo que diga explícitamente 'solo dependo de la lluvia' / 'sin riego' -> 'secano').\n"
        "- Si dice 'clima bipolar', 'días que llueve y días que no', 'cambios climáticos', 'sequía', pon `apply_20yr_projection` = true y resume eso en `climate_stress_concern`.\n"
        "- Si dice 'maximizar ganancia', 'mayor rentabilidad' o 'para vender' (sin mencionar ganado/leche), pon `market_preference` = 'grano_comercial' y sube `goals_priority.commercial_profit` a 95-100.\n"
        "- Ajusta `goals_priority` (0-100) SOLO para los ejes que el agricultor enfatizó o pidió explícitamente (deja null en los ejes que NO mencionó para no pisar su configuración previa).\n"
        "- Si mencionó semillas específicas que tiene en casa, pon sus IDs en `available_seeds` y también en `focused_crop_ids`.\n"
        "- Si pregunta por cultivos específicos aunque no diga que son sus semillas, pon sus IDs en `focused_crop_ids`."
    )

    schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "intent_mode": {
                "type": "string",
                "enum": ["out_of_scope", "app_help", "parcel_qa", "rotation_planning"],
            },
            "wants_immediate_plan": {"type": "boolean"},
            "direct_reply": {"type": "string"},
            "needs_parcel_data": {"type": "boolean"},
            "climate_stress_concern": {"type": ["string", "null"]},
            "location_query": {"type": ["string", "null"]},
            "use_gps": {"type": "boolean"},
            "coords": {
                "type": ["object", "null"],
                "properties": {
                    "lat": {"type": "number"},
                    "lon": {"type": "number"},
                },
                "required": ["lat", "lon"],
            },
            "current_crop": {
                "type": ["string", "null"],
                "enum": [
                    "sin_cultivo",
                    "monocultivo_papa",
                    "papa_maiz",
                    "pastos_degradados",
                    "cebada_trigo_continuo",
                    None,
                ],
            },
            "prior_crop_detail": {"type": ["string", "null"]},
            "water_availability": {
                "type": ["string", "null"],
                "enum": [
                    "secano",
                    "cosecha_agua_qocha",
                    "riego_deficitario",
                    "riego_gravedad",
                    "riego_melgas_surcos",
                    "riego_aspersion",
                    "riego_goteo",
                    None,
                ],
            },
            "available_seeds": {
                "type": ["array", "null"],
                "items": {"type": "string"},
            },
            "wants_all_catalog": {"type": "boolean"},
            "focused_crop_ids": {
                "type": "array",
                "items": {"type": "string"},
            },
            "soil_texture": {
                "type": ["string", "null"],
                "enum": [
                    "franco_arcilloso",
                    "franco_arenoso",
                    "arcilloso_pesado",
                    "pedregoso",
                    None,
                ],
            },
            "soil_acidity": {
                "type": ["string", "null"],
                "enum": ["normal", "acido", "no_se", None],
            },
            "compaction_or_drainage": {
                "type": ["string", "null"],
                "enum": ["normal", "duro_compactado", "se_encharca", None],
            },
            "local_frost_early": {"type": ["boolean", "null"]},
            "equipment_access": {
                "type": ["string", "null"],
                "enum": ["manual_yunta", "tractor_compartido", "mecanizado", None],
            },
            "market_preference": {
                "type": ["string", "null"],
                "enum": ["autoconsumo_feria", "leche_forraje", "grano_comercial", None],
            },
            "apply_20yr_projection": {"type": "boolean"},
            "goals_priority": {
                "type": "object",
                "properties": {
                    "commercial_profit": {"type": ["integer", "null"]},
                    "drought_climate_resilience": {"type": ["integer", "null"]},
                    "soil_health": {"type": ["integer", "null"]},
                    "erosion_control": {"type": ["integer", "null"]},
                    "pest_break": {"type": ["integer", "null"]},
                },
                "required": [
                    "commercial_profit",
                    "drought_climate_resilience",
                    "soil_health",
                    "erosion_control",
                    "pest_break",
                ],
            },
        },
        "required": [
            "intent_mode",
            "wants_immediate_plan",
            "direct_reply",
            "needs_parcel_data",
            "climate_stress_concern",
            "location_query",
            "use_gps",
            "coords",
            "current_crop",
            "prior_crop_detail",
            "water_availability",
            "available_seeds",
            "wants_all_catalog",
            "focused_crop_ids",
            "soil_texture",
            "soil_acidity",
            "compaction_or_drainage",
            "local_frost_early",
            "equipment_access",
            "market_preference",
            "apply_20yr_projection",
            "goals_priority",
        ],
    }

    user_prompt = (
        f"Estado actual de la sesión:\n"
        f"- Ubicación confirmada: {slots.get('location_confirmed', False)} ({slots.get('location_label') or 'no definida'}, lat={current_state.get('lat')}, lon={current_state.get('lon')})\n"
        f"- Cultivo previo confirmado: {slots.get('crop_confirmed', False)} ({current_state.get('current_crop')})\n"
        f"- Agua confirmada: {slots.get('water_confirmed', False)} ({current_state.get('water_availability')})\n"
        f"- Semillas revisadas: {slots.get('seeds_checked', False)} ({slots.get('available_seeds') or []})\n"
        f"- Modo previo: {slots.get('last_intent_mode') or 'ninguno'}\n\n"
        f"Historial reciente:\n{hist_block}\n\n"
        f"Mensaje actual del agricultor:\n\"{transcript}\""
    )

    raw_json = await _call_gemini_generate_content(
        parts=[{"text": user_prompt}],
        system_instruction=system_prompt,
        response_json_schema=schema,
        thinking_level="MINIMAL",
        temperature=0.1,
        max_output_tokens=700,
        timeout=15.0,
    )
    if not raw_json:
        return None
    try:
        parsed_json = json.loads(raw_json)
        return parsed_json if isinstance(parsed_json, dict) else None
    except Exception:
        return None


async def build_ai_grounded_response(
    *,
    transcript: str,
    intent_mode: str,
    conversation_stage: str,
    terrain: Dict[str, Any],
    biophysical: Dict[str, Any],
    parsed_intent: Dict[str, Any],
    dialogue_state: Dict[str, Any],
    recommendation: Optional[Dict[str, Any]] = None,
    internal_viability_ref: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Generates a grounded, reasoning-driven spoken answer and quick cards using Gemini 3.5 Flash-Lite
    connected strictly to real NASA/DEM/SoilGrids/MCDA data from the backend.
    """
    if not has_gemini_api_key():
        return None

    bio_sum = biophysical.get("summary") or {}
    c20 = (biophysical.get("climate_20yr") or {}).get("trends") or {}
    soil_prof = terrain.get("soil_profile") or {}
    upd = parsed_intent.get("updated_params") or {}
    focused_ids = list(parsed_intent.get("focused_crop_ids") or []) + list(
        upd.get("available_seeds") or []
    )
    ref_for_crops = recommendation or internal_viability_ref
    crops_ctx = _build_focused_crops_context(
        crop_ids=focused_ids,
        terrain=terrain,
        biophysical=biophysical,
        recommendation=ref_for_crops,
    )

    all_crops_map = {str(c["id"]): c for c in (load_crops_data().get("crops") or [])}
    viability_summary: Dict[str, List[str]] = {"optimo_resiliente": [], "viable_con_rotacion": []}
    top_parcel_crops: List[Dict[str, Any]] = []
    if ref_for_crops:
        for item in (ref_for_crops.get("climate_outlook_20yr") or {}).get("crop_viability") or []:
            st = item.get("status_2027")
            if st in viability_summary and len(viability_summary[st]) < 6:
                viability_summary[st].append(str(item.get("crop_name")))
            cid = str(item.get("crop_id") or "")
            raw_c = all_crops_map.get(cid) or {}
            if len(top_parcel_crops) < 12:
                top_parcel_crops.append(
                    {
                        "id": cid,
                        "name": item.get("crop_name"),
                        "category": item.get("category"),
                        "suitability_now": item.get("suitability_now"),
                        "suitability_2yr_stress": item.get("suitability_2027"),
                        "status_2027": st,
                        "net_margin_soles_ha": item.get("net_margin_soles_ha") or raw_c.get("net_margin_soles_ha"),
                        "benefit_cost_ratio": item.get("benefit_cost_ratio") or raw_c.get("benefit_cost_ratio"),
                        "drought_tolerance": raw_c.get("drought_tolerance"),
                        "drought_label": raw_c.get("drought_label"),
                        "frost_label": raw_c.get("frost_label"),
                        "erosion_protection_score": raw_c.get("erosion_protection_score"),
                        "nitrogen_balance_kg_ha": raw_c.get("nitrogen_balance_kg_ha"),
                        "water_req_range_mm": raw_c.get("water_req_range_mm"),
                        "altitude_range_m": [raw_c.get("altitude_min_m"), raw_c.get("altitude_max_m")],
                        "market_note": raw_c.get("market_note"),
                        "farmer_tip": raw_c.get("farmer_tip"),
                    }
                )

    rec_ctx = None
    if recommendation and conversation_stage == "ready":
        best_id = recommendation.get("recommended_strategy_id")
        strategies = recommendation.get("strategies") or []
        best = next((s for s in strategies if s.get("id") == best_id), (strategies or [None])[0])
        alt_strategies = [
            {
                "id": s.get("id"),
                "title": s.get("title"),
                "subtitle": s.get("subtitle"),
                "mcda_score": s.get("mcda_score"),
                "vulnerability_level": s.get("vulnerability_level"),
                "net_margin_2yr_soles_ha": (s.get("metrics") or {}).get("net_margin_2yr_soles_ha"),
                "benefit_cost_ratio": (s.get("metrics") or {}).get("benefit_cost_ratio"),
                "water_savings_pct": (s.get("metrics") or {}).get("water_savings_pct"),
                "erosion_reduction_pct": (s.get("metrics") or {}).get("erosion_reduction_pct"),
            }
            for s in strategies
            if s.get("id") != "baseline" and s.get("id") != best_id
        ]
        if best:
            rec_ctx = {
                "recommended_strategy_name": best.get("title"),
                "route_summary": best.get("subtitle"),
                "mcda_score": best.get("mcda_score"),
                "vulnerability_level": best.get("vulnerability_level"),
                "radar_scores": best.get("radar_scores"),
                "metrics": best.get("metrics"),
                "phases": [
                    {
                        "phase_name": ph.get("phase_name"),
                        "period": ph.get("period"),
                        "crop": ph.get("crop_name"),
                        "is_cover": ph.get("is_cover"),
                        "role": ph.get("role"),
                    }
                    for ph in (best.get("phases") or [])[:5]
                ],
                "alternative_strategies": alt_strategies,
                "immediate_action": (recommendation.get("seasonal_context") or {}).get("immediate_action"),
                "next_planting_window": (recommendation.get("seasonal_context") or {}).get("next_planting_window"),
                "outlook_2yr_findings": (recommendation.get("climate_outlook_20yr") or {}).get("key_findings"),
                "seed_constraint_summary": recommendation.get("seed_constraint_summary"),
            }

    has_prior_assistant_turn = any(
        str(item.get("role") or "") == "assistant" for item in (history or [])
    )
    parcel_already_introduced = bool(
        has_prior_assistant_turn
        and not parsed_intent.get("location_changed")
        and (dialogue_state.get("estado_parcela") or {}).get("sector")
    )

    grounding_payload = {
        "intent_mode": intent_mode,
        "conversation_stage": conversation_stage,
        "parcel_already_introduced": parcel_already_introduced,
        "estado_parcela": dialogue_state.get("estado_parcela"),
        "accion_ui": dialogue_state.get("accion_ui"),
        "listo_para_nasa": dialogue_state.get("listo_para_nasa", False),
        "show_map_picker": dialogue_state.get("show_map_picker", False),
        "next_question_required": dialogue_state.get("next_question"),
        "question_field": dialogue_state.get("question_field"),
        "assumed_provisional_fields": dialogue_state.get("assumed_provisional_fields") or [],
        "climate_stress_concern": parsed_intent.get("climate_stress_concern"),
        "applied_priorities": parsed_intent.get("applied_priorities"),
        "farmer_input": transcript,
        "parcel_terrain": {
            "zone_name": terrain.get("zone_name"),
            "lat": terrain.get("lat"),
            "lon": terrain.get("lon"),
            "elevation_m": round(float(terrain.get("elevation_m") or 0)),
            "slope_pct": round(float(terrain.get("slope_pct") or 0), 1),
            "agro_belt": terrain.get("agro_belt_name") or terrain.get("zone_type"),
            "frost_risk_window": terrain.get("frost_risk_window"),
            "primary_hazard": terrain.get("primary_hazard"),
            "traditional_local_crops": terrain.get("traditional_local_crops") or [],
        },
        "soil": {
            "soilgrids_ph": soil_prof.get("ph"),
            "soilgrids_texture": soil_prof.get("texture_class") or terrain.get("soil_texture"),
            "organic_matter_pct": soil_prof.get("organic_matter_pct"),
            "clay_pct": soil_prof.get("clay_pct"),
            "farmer_reported_soil": upd.get("farmer_soil"),
        },
        "nasa_climate": {
            "annual_precip_mm": round(float(bio_sum.get("annual_precip_mm") or 0)),
            "annual_et0_mm": round(float(bio_sum.get("annual_et0_mm") or 0)),
            "annual_water_balance_mm": round(float(bio_sum.get("annual_water_balance_mm") or 0)),
            "mean_temp_c": round(float(bio_sum.get("mean_temp_c") or 0), 1),
            "min_temp_c": round(float(bio_sum.get("min_temp_c") or 0), 1),
            "min_temp_month": bio_sum.get("min_temp_month"),
            "frost_risk_months": bio_sum.get("frost_risk_months") or [],
            "dry_anomaly_months": bio_sum.get("dry_anomaly_months") or [],
            "current_weather": bio_sum.get("current_weather_label"),
            "current_temp_c": bio_sum.get("current_temp_c"),
            "trend_20yr_temp_delta_c": c20.get("temp_delta_20yr_c"),
            "trend_20yr_precip_delta_pct": c20.get("precip_delta_20yr_pct"),
        },
        "farmer_session": {
            "current_crop": upd.get("current_crop"),
            "water_availability": upd.get("water_availability"),
            "available_seeds": upd.get("available_seeds") or [],
        },
        "focused_crops_data": crops_ctx,
        "top_parcel_crops": top_parcel_crops,
        "zone_viable_crops": viability_summary,
        "rotation_recommendation": rec_ctx,
    }

    hist_lines = []
    for item in (history or [])[-4:]:
        role = "Agricultor" if item.get("role") == "user" else "Ingeniero"
        txt = str(item.get("text") or "").strip()
        if txt:
            hist_lines.append(f"{role}: {txt[:180]}")

    system_prompt = (
        "Eres un ingeniero agrónomo amable y cercano en Cajamarca, Perú, dentro de AgroConecta (usa datos satelitales NASA POWER, relieve SRTM, suelos SoilGrids y 24 cultivos locales).\n"
        "Reglas obligatorias:\n"
        "1. Usa ÚNICAMENTE los datos reales del JSON adjunto. NUNCA inventes cifras, precios, rendimientos ni cultivos fuera del JSON.\n"
        "2. `spoken_text` será leído en voz alta a un agricultor: español cálido, sencillo y natural, SIN asteriscos, SIN viñetas, SIN markdown y evitando jerga técnica pesada (no digas '0.5 grados', 'downscaling', 'ET0' ni 'índice MCDA'; di 'clima ajustado a tu altura', 'consumo de agua por sol y viento', 'compatibilidad').\n"
        "3. Adapta `spoken_text` exactamente a `conversation_stage`:\n"
        "   - Si `conversation_stage` == 'collecting_info':\n"
        "     * Si `parcel_already_introduced` es `false` (primer turno o cambió de lugar): saluda confirmando en lenguaje sencillo dónde queda su chacra, su altura y un resumen breve de su clima/lluvias reales; luego formula ÚNICAMENTE la pregunta de `next_question_required` (máx. 65 palabras).\n"
        "     * Si `parcel_already_introduced` es `true` (preguntas de seguimiento): PROHIBIDO volver a decir en qué ciudad/distrito está la parcela, su altura, lluvia anual o clima general que ya se dijo antes. Empieza confirmando muy breve lo que acaba de responder (por ejemplo: 'Anotado, trabajas con lluvia.' o 'Perfecto, para continuar...') y haz directo ÚNICAMENTE la pregunta de `next_question_required` en tono cercano (máx. 35 palabras en total).\n"
        "     * JAMÁS vuelvas a preguntar un dato que ya figure confirmado en `estado_parcela`.\n"
        "   - Si `conversation_stage` == 'ready': Construye un resumen claro y entusiasta (95 a 155 palabras): explica en palabras sencillas las condiciones de su chacra, las mejores rotaciones y la secuencia recomendada a 2 años (`recommended_strategy_name` y `phases` con sus periodos) con sus beneficios reales (`water_savings_pct`, `erosion_reduction_pct`, margen). TERMINA SIEMPRE con esta indicación clara en la última frase: 'Para ver en detalle las 3 opciones, el calendario mes a mes y las ganancias, presiona el botón verde de abajo que dice Aplicar este plan y ver mi rotación.'\n"
        "   - Si `conversation_stage` == 'qa': Responde SOLO lo que preguntó conectando clima, suelo, altura y cultivos reales del JSON (máx. 105 palabras) en lenguaje claro. NO hagas cuestionario de rotación. Si `show_map_picker` es true, menciona al final en 1 frase corta que abajo puede mover el punto exacto en el mapa.\n"
        "4. Genera 3 o 4 `quick_cards` con TÍTULOS y CONTENIDOS claros para el agricultor usando cifras reales del JSON y sin markdown."
    )

    resp_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "spoken_text": {"type": "string"},
            "quick_cards": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "badge": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    "required": ["title", "badge", "body"],
                },
            },
        },
        "required": ["spoken_text", "quick_cards"],
    }

    prompt_txt = (
        ("Historial reciente:\n" + "\n".join(hist_lines) + "\n\n" if hist_lines else "")
        + "Datos reales verificados de la parcela y consulta:\n"
        + json.dumps(grounding_payload, ensure_ascii=False)
    )

    raw_json = await _call_gemini_generate_content(
        parts=[{"text": prompt_txt}],
        system_instruction=system_prompt,
        response_json_schema=resp_schema,
        thinking_level="LOW",
        temperature=0.3,
        max_output_tokens=1350,
        timeout=15.0,
    )
    if not raw_json:
        return None
    try:
        obj = json.loads(raw_json)
        spoken = str(obj.get("spoken_text") or "").strip()
        cards = obj.get("quick_cards") or []
        if len(spoken) < 20 or not isinstance(cards, list):
            return None
        clean_cards = [
            {
                "title": str(c.get("title") or "Dato NASA"),
                "badge": str(c.get("badge") or ""),
                "body": str(c.get("body") or ""),
            }
            for c in cards[:4]
            if isinstance(c, dict) and c.get("body")
        ]
        return {
            "spoken_text": spoken,
            "quick_cards": clean_cards,
        }
    except Exception:
        return None


async def maybe_polish_spoken_with_gemini(spoken_text: str, transcript: str) -> str:
    """
    Optionally polishes the spoken farmer answer using Gemini if GEMINI_API_KEY is configured,
    with strict timeout and automatic fallback to the deterministic spoken_text.
    """
    if not has_gemini_api_key() or not transcript.strip():
        return spoken_text

    prompt = (
        "Eres un ingeniero agrónomo amable de Cajamarca, Perú. "
        "Reescribe este resumen para responder por voz a un agricultor que preguntó: "
        f"\"{transcript}\". Mantén EXACTAMENTE los mismos números, cultivos y recomendaciones del borrador, "
        "en español sencillo y cálido, máximo 70 palabras, sin asteriscos ni viñetas:\n\n"
        f"{spoken_text}"
    )
    cand = await _call_gemini_generate_content(
        parts=[{"text": prompt}],
        thinking_level="MINIMAL",
        temperature=0.3,
        max_output_tokens=220,
        timeout=5.0,
    )
    return cand if cand and len(cand) >= 25 else spoken_text


async def transcribe_farmer_audio_bytes(
    audio_bytes: bytes,
    audio_ext: str = "m4a",
    lang: str = "es",
) -> str:
    """
    Convierte audio grabado desde el teléfono (.m4a, .3gp, .webm, .wav) a texto en español/quechua.
    1. Si existe GEMINI_API_KEY, usa Gemini multimodal (gemini-3.5-flash-lite) para máxima precisión con topónimos andinos y quechua.
    2. Si no hay API key o falla, decodifica a WAV 16kHz PCM con imageio-ffmpeg y usa SpeechRecognition (es-PE).
    """
    import asyncio
    import base64
    import subprocess
    import tempfile
    from pathlib import Path

    if not audio_bytes or len(audio_bytes) < 512:
        raise ValueError("El audio grabado está vacío. Mantén presionado el botón mientras hablas.")

    safe_ext = re.sub(r"[^a-zA-Z0-9]", "", audio_ext or "m4a").lower() or "m4a"
    mime_map = {
        "m4a": "audio/mp4",
        "mp4": "audio/mp4",
        "3gp": "audio/3gpp",
        "aac": "audio/aac",
        "wav": "audio/wav",
        "webm": "audio/webm",
        "ogg": "audio/ogg",
    }
    mime_type = mime_map.get(safe_ext, "audio/mp4")

    # 1. Gemini Audio STT si GEMINI_API_KEY está configurado
    if has_gemini_api_key():
        b64_audio = base64.b64encode(audio_bytes).decode("ascii")
        prompt_stt = (
            "Transcribe EXACTAMENTE lo que dice este agricultor del Perú "
            "(puede mencionar distritos o caseríos de Cajamarca como Cajabamba, Porcón, Yanacocha, Combayo, Llacanora, "
            "coordenadas numéricas, y palabras en quechua como akshu, qasa, qocha, tarpuni, allpa). "
            "Devuelve SOLO la transcripción limpia en una sola línea, sin comillas ni explicaciones."
        )
        cand = await _call_gemini_generate_content(
            parts=[
                {"text": prompt_stt},
                {"inlineData": {"mimeType": mime_type, "data": b64_audio}},
            ],
            thinking_level="MINIMAL",
            temperature=0.0,
            max_output_tokens=240,
            timeout=14.0,
        )
        if cand:
            return cand.strip().strip('"“”')

    # 2. Motor gratuito sin API keys: imageio-ffmpeg -> WAV PCM 16kHz -> SpeechRecognition (es-PE)
    def _decode_and_recognize() -> str:
        import imageio_ffmpeg
        import speech_recognition as sr

        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = Path(tmpdir) / f"farmer.{safe_ext}"
            wav_path = Path(tmpdir) / "farmer_16k.wav"
            src_path.write_bytes(audio_bytes)

            if safe_ext == "wav":
                wav_input = src_path
            else:
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                proc = subprocess.run(
                    [
                        ffmpeg_exe,
                        "-y",
                        "-i",
                        str(src_path),
                        "-vn",
                        "-acodec",
                        "pcm_s16le",
                        "-ar",
                        "16000",
                        "-ac",
                        "1",
                        str(wav_path),
                    ],
                    capture_output=True,
                    timeout=15,
                )
                if proc.returncode != 0 or not wav_path.exists():
                    err_msg = proc.stderr.decode("utf-8", errors="ignore")[-240:]
                    raise RuntimeError(f"No se pudo decodificar el audio ({err_msg})")
                wav_input = wav_path

            recognizer = sr.Recognizer()
            with sr.AudioFile(str(wav_input)) as source:
                audio_data = recognizer.record(source)

            try:
                text = recognizer.recognize_google(audio_data, language="es-PE")
                return str(text).strip()
            except sr.UnknownValueError:
                raise ValueError(
                    "No entendí lo que dijiste. Por favor habla un poco más fuerte y cerca del micrófono."
                )
            except sr.RequestError as req_err:
                raise RuntimeError(
                    f"El servicio de transcripción por voz no respondió en este momento: {req_err}"
                )

    return await asyncio.to_thread(_decode_and_recognize)

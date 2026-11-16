"""Application use cases orchestrating the multimodal AI voice copilot conversation loop."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import HTTPException

from application.parcel_service import _run_parcel_biophysical_analysis
from application.schemas import (
    ClimateScenarioInput,
    FarmerSoilInput,
    ParcelAnalyzeRequest,
    PriorityWeights,
    RecommendRequest,
    VoiceAssistantRequest,
    VoiceAudioRequest,
)
from domain.rotation_engine import generate_rotation_recommendations
from domain.voice_dialogue import (
    build_collecting_spoken_response,
    build_deterministic_qa_response,
    build_spoken_farmer_response,
    evaluate_voice_dialogue_state,
    merge_ai_understanding_with_deterministic,
    parse_farmer_voice_command,
)
from infrastructure.gemini_client import (
    ai_understand_farmer_turn,
    build_ai_grounded_response,
    maybe_polish_spoken_with_gemini,
    transcribe_farmer_audio_bytes,
)
from infrastructure.geocoding_client import (
    geocode_cajamarca_place,
    reverse_geocode_coords,
)


async def process_voice_assistant_turn(req: VoiceAssistantRequest) -> Dict[str, Any]:
    """
    Interpreta consultas habladas o escritas complejas del agricultor (coordenadas exactas,
    sectores o caseríos, preguntas puntuales de clima/suelo/cultivos, consultas fuera de alcance,
    terreno libre vs cultivo previo, disponibilidad de agua y semillas disponibles),
    consulta telemetría NASA POWER + DEM + SoilGrids en tiempo real y guía paso a paso con mapa interactivo.
    """
    try:
        current_state = {
            "lat": req.lat,
            "lon": req.lon,
            "parcel_id": req.parcel_id,
            "current_crop": req.current_crop,
            "water_availability": req.water_availability,
            "equipment_access": req.equipment_access,
            "market_preference": req.market_preference,
            "farmer_soil": req.farmer_soil.model_dump(),
            "available_seeds": req.available_seeds,
        }
        det_parsed = parse_farmer_voice_command(
            transcript=req.transcript,
            gps_lat=req.gps_lat,
            gps_lon=req.gps_lon,
            current_state=current_state,
            session_slots=req.session_slots,
        )
        ai_raw = await ai_understand_farmer_turn(
            transcript=req.transcript,
            current_state=current_state,
            session_slots=req.session_slots,
            history=req.history,
        )
        parsed = merge_ai_understanding_with_deterministic(
            det_parsed=det_parsed,
            ai_parsed=ai_raw,
            gps_lat=req.gps_lat,
            gps_lon=req.gps_lon,
        )
        upd = parsed["updated_params"]
        intent_mode = str(parsed.get("intent_mode") or "rotation_planning")

        # Respuesta directa sin consultas NASA/MCDA cuando la pregunta está fuera de tema o es ayuda de la app
        if intent_mode in {"out_of_scope", "app_help"} and not req.force_calculate:
            stage = "out_of_scope" if intent_mode == "out_of_scope" else "qa"
            direct_txt = str(parsed.get("direct_reply") or "").strip()
            if not direct_txt:
                direct_txt = (
                    "Solo puedo ayudarte con temas agrícolas de tu chacra: clima de la NASA, suelo, agua y cultivos recomendados."
                    if intent_mode == "out_of_scope"
                    else "En AgroConecta puedes usar el micrófono para ubicarte, abrir el mapa para marcar tu chacra y revisar tu plan de rotación y catálogo de semillas."
                )
            helper_cards = (
                [
                    {
                        "title": "Cómo puedo ayudarte en AgroConecta",
                        "badge": "Asistente Agrícola",
                        "body": "Pregúntame por el clima, heladas o suelo de tu distrito (ej. Cajabamba), compara tus semillas o dime dónde está tu chacra para armar tu rotación.",
                    }
                ]
                if intent_mode == "out_of_scope"
                else [
                    {
                        "title": "Guía rápida de la app",
                        "badge": "AgroConecta",
                        "body": "Usa Inicio para ver alertas del tiempo, Mapa para marcar tu parcela, Plan para ver rotaciones a 24 meses y Semillas para explorar los 24 cultivos.",
                    }
                ]
            )
            return {
                "transcript": req.transcript,
                "intent_mode": intent_mode,
                "understood": parsed["understood"],
                "use_browser_gps": False,
                "gps_out_of_region": False,
                "conversation_stage": stage,
                "confirmed_slots": parsed["confirmed_slots"],
                "estado_parcela": None,
                "accion_ui": {"tipo": "NINGUNA", "parametros": {}},
                "listo_para_nasa": False,
                "missing_fields": [],
                "next_question": None,
                "question_field": None,
                "question_chips": [],
                "show_map_picker": False,
                "updated_params": {
                    **current_state,
                    "priorities": req.priorities.model_dump(),
                    "climate_scenario": req.climate_scenario.model_dump(),
                    "clear_polygon": False,
                },
                "spoken_response": direct_txt,
                "quick_cards": helper_cards,
                "preview_terrain": None,
                "preview_biophysical": None,
                "recommendation": None,
            }

        # Geocodificador abierto Perú (Open-Meteo + OSM Nominatim) para sectores o distritos no prelistados
        if (
            not parsed.get("location_matched")
            and not parsed.get("use_browser_gps")
            and (
                not parsed["confirmed_slots"].get("location_confirmed")
                or bool(parsed.get("ai_location_query"))
            )
        ):
            geo = await geocode_cajamarca_place(
                req.transcript,
                place_hint=parsed.get("ai_location_query"),
            )
            if geo is not None:
                upd["lat"] = geo["lat"]
                upd["lon"] = geo["lon"]
                upd["parcel_id"] = None
                parsed["location_matched"] = True
                parsed["location_changed"] = True
                parsed["confirmed_slots"]["location_confirmed"] = True
                parsed["confirmed_slots"]["map_verified"] = False
                parsed["confirmed_slots"]["location_label"] = geo["label"]
                parsed["understood"]["location"] = geo["label"]
                parsed["custom_zone_label"] = geo["label"]
        elif parsed.get("coords_matched") or (parsed.get("use_browser_gps") and parsed["confirmed_slots"].get("location_confirmed")):
            rev_label = await reverse_geocode_coords(float(upd["lat"]), float(upd["lon"]))
            if rev_label:
                full_lbl = f"{rev_label} ({float(upd['lat']):.4f}, {float(upd['lon']):.4f})"
                parsed["confirmed_slots"]["location_label"] = full_lbl
                parsed["understood"]["location"] = full_lbl
                parsed["custom_zone_label"] = full_lbl

        location_changed = bool(parsed.get("location_changed")) or (
            abs(float(upd["lat"]) - req.lat) > 0.0005
            or abs(float(upd["lon"]) - req.lon) > 0.0005
            or upd.get("parcel_id") != req.parcel_id
        )
        eff_polygon = None if location_changed else req.polygon

        prio_dict = req.priorities.model_dump()
        for pk, pv in (parsed.get("priority_overrides") or {}).items():
            if pk in prio_dict and isinstance(pv, (int, float)):
                prio_dict[pk] = round(float(max(0.0, min(100.0, pv))), 1)
        effective_priorities = PriorityWeights(**prio_dict)
        parsed["applied_priorities"] = effective_priorities.model_dump()

        effective_req = RecommendRequest(
            lat=float(upd["lat"]),
            lon=float(upd["lon"]),
            polygon=eff_polygon,
            parcel_id=upd.get("parcel_id"),
            current_crop=upd["current_crop"],
            water_availability=upd["water_availability"],
            equipment_access=upd["equipment_access"],
            market_preference=upd["market_preference"],
            farmer_soil=FarmerSoilInput(**upd["farmer_soil"]),
            priorities=effective_priorities,
            climate_scenario=req.climate_scenario,
            field_status=req.field_status,
            planning_month=req.planning_month,
            planning_year=req.planning_year,
            available_seeds=upd.get("available_seeds", []),
            custom_zone_label=parsed.get("custom_zone_label") or parsed["confirmed_slots"].get("location_label"),
        )

        terrain, biophysical = await _run_parcel_biophysical_analysis(
            effective_req,
            custom_zone_label=effective_req.custom_zone_label,
        )
        dialogue_state = evaluate_voice_dialogue_state(
            parsed_intent=parsed,
            terrain=terrain,
            force_calculate=req.force_calculate,
        )

        effective_scenario = req.climate_scenario.model_dump()
        recommendation_payload: Optional[Dict[str, Any]] = None
        stage = str(dialogue_state["conversation_stage"])

        if stage == "ready":
            recommendation = generate_rotation_recommendations(
                terrain=terrain,
                biophysical=biophysical,
                current_crop=effective_req.current_crop,
                water_availability=effective_req.water_availability,
                priorities=effective_req.priorities.model_dump(),
                climate_scenario=effective_scenario,
                equipment_access=effective_req.equipment_access,
                market_preference=effective_req.market_preference,
                farmer_soil=effective_req.farmer_soil.model_dump(),
                field_status=effective_req.field_status,
                planning_month=effective_req.planning_month,
                planning_year=effective_req.planning_year,
                available_seeds=effective_req.available_seeds,
            )

            if parsed["apply_20yr_projection"]:
                outlook_scen = recommendation.get("climate_outlook_20yr", {}).get("recommended_20yr_scenario")
                if isinstance(outlook_scen, dict):
                    effective_scenario = outlook_scen
                    recommendation = generate_rotation_recommendations(
                        terrain=terrain,
                        biophysical=biophysical,
                        current_crop=effective_req.current_crop,
                        water_availability=effective_req.water_availability,
                        priorities=effective_req.priorities.model_dump(),
                        climate_scenario=effective_scenario,
                        equipment_access=effective_req.equipment_access,
                        market_preference=effective_req.market_preference,
                        farmer_soil=effective_req.farmer_soil.model_dump(),
                        field_status=effective_req.field_status,
                        planning_month=effective_req.planning_month,
                        planning_year=effective_req.planning_year,
                        available_seeds=effective_req.available_seeds,
                    )

            ai_bundle = await build_ai_grounded_response(
                transcript=req.transcript,
                intent_mode=intent_mode,
                conversation_stage=stage,
                terrain=terrain,
                biophysical=biophysical,
                parsed_intent=parsed,
                dialogue_state=dialogue_state,
                recommendation=recommendation,
                history=req.history,
            )
            if ai_bundle is not None:
                spoken_bundle = ai_bundle
            else:
                spoken_bundle = build_spoken_farmer_response(
                    terrain=terrain,
                    biophysical=biophysical,
                    recommendation=recommendation,
                    parsed_intent=parsed,
                )
                spoken_bundle["spoken_text"] = await maybe_polish_spoken_with_gemini(
                    spoken_text=spoken_bundle["spoken_text"],
                    transcript=req.transcript,
                )

            recommendation_payload = {
                "terrain": terrain,
                "biophysical": biophysical,
                **recommendation,
            }
        elif stage == "qa":
            internal_rec = generate_rotation_recommendations(
                terrain=terrain,
                biophysical=biophysical,
                current_crop=effective_req.current_crop,
                water_availability=effective_req.water_availability,
                priorities=effective_req.priorities.model_dump(),
                climate_scenario=effective_scenario,
                equipment_access=effective_req.equipment_access,
                market_preference=effective_req.market_preference,
                farmer_soil=effective_req.farmer_soil.model_dump(),
                field_status=effective_req.field_status,
                planning_month=effective_req.planning_month,
                planning_year=effective_req.planning_year,
                available_seeds=effective_req.available_seeds,
            )
            ai_bundle = await build_ai_grounded_response(
                transcript=req.transcript,
                intent_mode=intent_mode,
                conversation_stage=stage,
                terrain=terrain,
                biophysical=biophysical,
                parsed_intent=parsed,
                dialogue_state=dialogue_state,
                internal_viability_ref=internal_rec,
                history=req.history,
            )
            spoken_bundle = ai_bundle or build_deterministic_qa_response(
                terrain=terrain,
                biophysical=biophysical,
                parsed_intent=parsed,
                dialogue_state=dialogue_state,
            )
        else:
            internal_rec = (
                generate_rotation_recommendations(
                    terrain=terrain,
                    biophysical=biophysical,
                    current_crop=effective_req.current_crop,
                    water_availability=effective_req.water_availability,
                    priorities=effective_req.priorities.model_dump(),
                    climate_scenario=effective_scenario,
                    equipment_access=effective_req.equipment_access,
                    market_preference=effective_req.market_preference,
                    farmer_soil=effective_req.farmer_soil.model_dump(),
                    field_status=effective_req.field_status,
                    planning_month=effective_req.planning_month,
                    planning_year=effective_req.planning_year,
                    available_seeds=effective_req.available_seeds,
                )
                if parsed["confirmed_slots"].get("location_confirmed")
                else None
            )
            ai_bundle = await build_ai_grounded_response(
                transcript=req.transcript,
                intent_mode=intent_mode,
                conversation_stage=stage,
                terrain=terrain,
                biophysical=biophysical,
                parsed_intent=parsed,
                dialogue_state=dialogue_state,
                internal_viability_ref=internal_rec,
                history=req.history,
            )
            spoken_bundle = ai_bundle or build_collecting_spoken_response(
                terrain=terrain,
                biophysical=biophysical,
                parsed_intent=parsed,
                dialogue_state=dialogue_state,
                history=req.history,
            )

        spoken_text = spoken_bundle["spoken_text"]

        return {
            "transcript": req.transcript,
            "intent_mode": intent_mode,
            "understood": parsed["understood"],
            "use_browser_gps": parsed["use_browser_gps"],
            "gps_out_of_region": parsed["gps_out_of_region"],
            "conversation_stage": stage,
            "confirmed_slots": parsed["confirmed_slots"],
            "missing_fields": dialogue_state["missing_fields"],
            "next_question": dialogue_state["next_question"],
            "question_field": dialogue_state["question_field"],
            "question_chips": dialogue_state["question_chips"],
            "show_map_picker": dialogue_state["show_map_picker"],
            "estado_parcela": dialogue_state.get("estado_parcela"),
            "accion_ui": dialogue_state.get("accion_ui"),
            "listo_para_nasa": dialogue_state.get("listo_para_nasa", stage == "ready"),
            "updated_params": {
                **upd,
                "priorities": effective_priorities.model_dump(),
                "climate_scenario": effective_scenario,
                "clear_polygon": location_changed,
            },
            "spoken_response": spoken_text,
            "quick_cards": spoken_bundle["quick_cards"],
            "preview_terrain": terrain,
            "preview_biophysical": biophysical,
            "recommendation": recommendation_payload,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error en copiloto de voz: {exc}")


async def process_voice_audio_turn(req: VoiceAudioRequest) -> Dict[str, Any]:
    """
    Recibe audio real grabado desde el teléfono en Expo Go, lo transcribe a texto
    y ejecuta el mismo motor satelital y agronómico de /api/voice-assistant.
    """
    import base64

    try:
        raw_audio = base64.b64decode(req.audio_base64)
        transcript = await transcribe_farmer_audio_bytes(
            audio_bytes=raw_audio,
            audio_ext=req.audio_ext,
            lang=req.lang,
        )
    except ValueError as user_err:
        raise HTTPException(status_code=422, detail=str(user_err))
    except Exception as stt_err:
        raise HTTPException(status_code=502, detail=f"Error procesando audio de voz: {stt_err}")

    text_req = VoiceAssistantRequest(
        **req.model_dump(exclude={"audio_base64", "audio_ext", "lang"}),
        transcript=transcript,
    )
    return await process_voice_assistant_turn(text_req)

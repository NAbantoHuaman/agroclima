"""Pydantic request/DTO schemas for parcel analysis, rotation recommendations, and voice assistant."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class PriorityWeights(BaseModel):
    water_conservation: float = Field(75.0, ge=0.0, le=100.0, description="Conservación de agua y resistencia a sequía")
    soil_fertility: float = Field(80.0, ge=0.0, le=100.0, description="Recuperación de fertilidad y nitrógeno")
    erosion_control: float = Field(75.0, ge=0.0, le=100.0, description="Control de erosión en pendiente")
    pest_break: float = Field(70.0, ge=0.0, le=100.0, description="Interrupción de ciclo de plagas")
    commercial_forage: float = Field(65.0, ge=0.0, le=100.0, description="Rentabilidad comercial / valor forrajero")


class ClimateScenarioInput(BaseModel):
    rain_delta_pct: float = Field(0.0, ge=-30.0, le=20.0, description="Variación de lluvias (%)")
    temp_delta_c: float = Field(0.0, ge=0.0, le=2.5, description="Incremento de temperatura (°C)")
    frost_frequency: Literal["normal", "moderada", "severa"] = Field(
        "normal", description="Frecuencia de heladas tempranas"
    )


class FarmerSoilInput(BaseModel):
    texture_override: Literal[
        "auto", "franco_arcilloso", "franco_arenoso", "arcilloso_pesado", "pedregoso"
    ] = Field("auto", description="Textura observada en campo por el agricultor")
    soil_acidity: Literal["normal", "acido", "no_se"] = Field(
        "normal", description="Acidez conocida del suelo (ej. tierra ácida de jalca)"
    )
    compaction_or_drainage: Literal["normal", "duro_compactado", "se_encharca"] = Field(
        "normal", description="Condición física observada al arar o llover"
    )
    local_frost_early: bool = Field(
        False, description="Si el agricultor reporta heladas tempranas desde mayo"
    )


class ParcelAnalyzeRequest(BaseModel):
    lat: float = Field(-7.1725, ge=-56.0, le=56.0, description="Latitud de la parcela (WGS84)")
    lon: float = Field(-78.4630, ge=-180.0, le=180.0, description="Longitud de la parcela (WGS84)")
    polygon: Optional[List[List[float]]] = Field(
        None, description="Lista opcional de vértices [[lat, lon], ...] dibujados en el mapa"
    )
    parcel_id: Optional[str] = Field(None, description="ID de Parcela Faro si aplica")
    current_crop: Literal[
        "sin_cultivo", "monocultivo_papa", "papa_maiz", "pastos_degradados", "cebada_trigo_continuo"
    ] = "sin_cultivo"
    available_seeds: List[str] = Field(
        default_factory=list,
        description="Lista opcional de cultivos/semillas disponibles en finca (ej. ['quinua', 'haba'])"
    )
    custom_zone_label: Optional[str] = Field(
        default=None,
        description="Nombre real geocodificado del lugar si fue resuelto por voz/GPS"
    )
    water_availability: Literal[
        "secano",
        "cosecha_agua_qocha",
        "riego_deficitario",
        "riego_gravedad",
        "riego_melgas_surcos",
        "riego_aspersion",
        "riego_goteo",
    ] = "riego_gravedad"
    equipment_access: Literal["manual_yunta", "tractor_compartido", "mecanizado"] = Field(
        "manual_yunta", description="Herramienta / maquinaria disponible en la parcela"
    )
    market_preference: Literal["autoconsumo_feria", "leche_forraje", "grano_comercial"] = Field(
        "autoconsumo_feria", description="Destino principal de la producción"
    )
    farmer_soil: FarmerSoilInput = Field(default_factory=FarmerSoilInput)


class RecommendRequest(ParcelAnalyzeRequest):
    priorities: PriorityWeights = Field(default_factory=PriorityWeights)
    climate_scenario: ClimateScenarioInput = Field(default_factory=ClimateScenarioInput)
    field_status: Literal["auto", "con_cultivo", "terreno_libre"] = Field(
        "auto", description="Estado actual de la chacra hoy (con cultivo o libre)"
    )
    planning_month: Optional[int] = Field(
        None, ge=1, le=12, description="Mes calendario opcional de inicio (1-12); por defecto hoy"
    )
    planning_year: Optional[int] = Field(
        None, ge=2024, le=2035, description="Año calendario opcional de inicio; por defecto hoy"
    )


class VoiceAssistantRequest(RecommendRequest):
    transcript: str = Field(..., min_length=1, description="Pregunta o comando hablado por el agricultor")
    gps_lat: Optional[float] = Field(None, description="Latitud real del navegador o celular si el usuario usó GPS")
    gps_lon: Optional[float] = Field(None, description="Longitud real del navegador o celular si el usuario usó GPS")
    session_slots: Optional[Dict[str, Any]] = Field(None, description="Slots confirmados en la conversación actual")
    history: List[Dict[str, str]] = Field(default_factory=list, description="Turnos recientes del chat para contexto")
    force_calculate: bool = Field(False, description="Si es True calcula estrategias sin pedir pasos opcionales")


class VoiceAudioRequest(RecommendRequest):
    audio_base64: str = Field(..., min_length=16, description="Audio grabado en base64 desde el celular")
    audio_ext: str = Field("m4a", description="Extensión del audio grabado (m4a, 3gp, wav, webm)")
    lang: str = Field("es", description="Idioma preferido del agricultor (es / qu)")
    gps_lat: Optional[float] = Field(None, description="Latitud real del dispositivo")
    gps_lon: Optional[float] = Field(None, description="Longitud real del dispositivo")
    session_slots: Optional[Dict[str, Any]] = Field(None, description="Slots confirmados en la conversación actual")
    history: List[Dict[str, str]] = Field(default_factory=list, description="Turnos recientes del chat para contexto")
    force_calculate: bool = Field(False, description="Si es True calcula estrategias sin pedir pasos opcionales")

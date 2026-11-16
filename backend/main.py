"""FastAPI application composition root & backward-compatible entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from application.parcel_service import (
    _run_parcel_biophysical_analysis,
    analyze_parcel_use_case as analyze_parcel,
    geocode_place_use_case as geocode_place,
    get_health_payload as health_check,
    get_integrations_status_payload as integrations_status,
    get_reference_data_payload as get_reference_data,
    recommend_rotations_use_case as recommend_rotations,
)
from application.schemas import (
    ClimateScenarioInput,
    FarmerSoilInput,
    ParcelAnalyzeRequest,
    PriorityWeights,
    RecommendRequest,
    VoiceAssistantRequest,
    VoiceAudioRequest,
)
from application.voice_service import (
    process_voice_assistant_turn as voice_assistant,
    process_voice_audio_turn as voice_audio_assistant,
)
from interfaces.api.parcel_routes import router as parcel_router
from interfaces.api.voice_routes import router as voice_router

app = FastAPI(
    title="AgroRumbo Cajamarca — NASA Earth Observation Agronomy API",
    description="Satellite-informed crop rotation planner using NASA POWER, SMAP, GPM & MODIS proxies",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(parcel_router)
app.include_router(voice_router)

__all__ = [
    "app",
    "PriorityWeights",
    "ClimateScenarioInput",
    "FarmerSoilInput",
    "ParcelAnalyzeRequest",
    "RecommendRequest",
    "VoiceAssistantRequest",
    "VoiceAudioRequest",
    "health_check",
    "get_reference_data",
    "integrations_status",
    "geocode_place",
    "_run_parcel_biophysical_analysis",
    "analyze_parcel",
    "recommend_rotations",
    "voice_assistant",
    "voice_audio_assistant",
]

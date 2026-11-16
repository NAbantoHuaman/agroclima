"""FastAPI routes for the voice assistant and base64 audio transcription turns."""

from __future__ import annotations

from fastapi import APIRouter

from application.schemas import VoiceAssistantRequest, VoiceAudioRequest
from application.voice_service import (
    process_voice_assistant_turn,
    process_voice_audio_turn,
)

router = APIRouter()


@router.post("/api/voice-assistant")
async def voice_assistant(req: VoiceAssistantRequest):
    return await process_voice_assistant_turn(req)


@router.post("/api/voice-audio")
async def voice_audio_assistant(req: VoiceAudioRequest):
    return await process_voice_audio_turn(req)

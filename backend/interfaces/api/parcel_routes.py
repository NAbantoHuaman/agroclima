"""FastAPI routes for reference data, geocoding, parcel biophysical analysis, and recommendations."""

from __future__ import annotations

from fastapi import APIRouter

from application.parcel_service import (
    analyze_parcel_use_case,
    geocode_place_use_case,
    get_health_payload,
    get_integrations_status_payload,
    get_reference_data_payload,
    recommend_rotations_use_case,
)
from application.schemas import ParcelAnalyzeRequest, RecommendRequest

router = APIRouter()


@router.get("/api/health")
async def health_check():
    return await get_health_payload()


@router.get("/api/reference-data")
async def get_reference_data():
    return await get_reference_data_payload()


@router.get("/api/integrations-status")
async def integrations_status():
    return await get_integrations_status_payload()


@router.get("/api/geocode")
async def geocode_place(q: str):
    return await geocode_place_use_case(q)


@router.post("/api/analyze-parcel")
async def analyze_parcel(req: ParcelAnalyzeRequest):
    return await analyze_parcel_use_case(req)


@router.post("/api/recommend")
async def recommend_rotations(req: RecommendRequest):
    return await recommend_rotations_use_case(req)

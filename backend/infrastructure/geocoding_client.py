"""Open-Meteo and OSM Nominatim geocoding / reverse-geocoding clients."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from domain.voice_dialogue import _extract_candidate_place_phrase, _normalize_text


async def reverse_geocode_coords(lat: float, lon: float) -> Optional[str]:
    """Looks up human-readable locality name for explicit spoken or map-pinned coordinates."""
    try:
        async with httpx.AsyncClient(timeout=2.8) as client:
            r = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": f"{lat:.5f}", "lon": f"{lon:.5f}", "format": "jsonv2", "zoom": 13},
                headers={"User-Agent": "AgroRumbo-NASA2026/1.0"},
            )
            if r.status_code == 200:
                data = r.json() or {}
                addr = data.get("address") or {}
                local = (
                    addr.get("hamlet")
                    or addr.get("village")
                    or addr.get("town")
                    or addr.get("city")
                    or addr.get("municipality")
                    or data.get("name")
                )
                region = addr.get("region") or addr.get("state") or ""
                if local:
                    return f"{local}, {region}" if region and region != local else str(local)
    except Exception:
        pass
    return None


async def geocode_cajamarca_place(
    transcript: str,
    place_hint: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Geocodificador abierto multi-región (Open-Meteo Geocoding + OSM Nominatim) para cualquier distrito, caserío o sector del Perú."""
    norm = _normalize_text(transcript)
    raw_place = _normalize_text(place_hint) if place_hint and place_hint.strip() else _extract_candidate_place_phrase(norm)
    if not raw_place or len(raw_place) < 2:
        return None

    async with httpx.AsyncClient(timeout=3.8) as client:
        try:
            r = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": raw_place, "count": 6, "language": "es", "countryCode": "PE"},
            )
            if r.status_code == 200:
                results = (r.json() or {}).get("results") or []
                caj_match = next(
                    (it for it in results if "cajamarca" in _normalize_text(str(it.get("admin1") or ""))),
                    None,
                )
                chosen = caj_match or (results[0] if results else None)
                if chosen and chosen.get("latitude") is not None and chosen.get("longitude") is not None:
                    admin1 = chosen.get("admin1") or "Perú"
                    elev_txt = f" ({int(chosen['elevation'])} m)" if chosen.get("elevation") else ""
                    return {
                        "lat": round(float(chosen["latitude"]), 5),
                        "lon": round(float(chosen["longitude"]), 5),
                        "label": f"{chosen.get('name', raw_place.title())} — {admin1}{elev_txt}",
                        "source": "open_meteo_geocoding",
                    }
        except Exception:
            pass

        for q_try in (f"{raw_place}, Cajamarca, Peru", f"{raw_place}, Peru"):
            try:
                r2 = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": q_try, "format": "json", "limit": 4, "countrycodes": "pe"},
                    headers={"User-Agent": "AgroRumbo-NASA2026/1.0"},
                )
                if r2.status_code == 200:
                    items = r2.json() or []
                    if items:
                        it = items[0]
                        cand_lat = float(it["lat"])
                        cand_lon = float(it["lon"])
                        short_name = str(it.get("name") or raw_place.title())
                        return {
                            "lat": round(cand_lat, 5),
                            "lon": round(cand_lon, 5),
                            "label": f"{short_name} (OSM Perú)",
                            "source": "osm_nominatim",
                        }
            except Exception:
                pass

    return None

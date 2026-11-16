from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
import numpy as np

from config import CACHE_DIR, SRTM_30M_NPZ, get_opentopography_key, has_opentopography_key

OPEN_METEO_ELEV_URL = "https://api.open-meteo.com/v1/elevation"
OPENTOPOGRAPHY_URL = "https://portal.opentopography.org/API/globaldem"
ELEVATION_CACHE_FILE = CACHE_DIR / "elevation_cache.json"
SRTM_TILES_DIR = CACHE_DIR / "srtm30_tiles"

_SRTM_CACHE_DATA: Optional[Dict[str, Any]] = None
_TILE_MEMORY_CACHE: Dict[str, Dict[str, Any]] = {}


class JsonDiskCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._store: Dict[str, Any] = {}
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    self._store = raw
            except Exception:
                self._store = {}

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        val = self._store.get(key)
        return val if isinstance(val, dict) else None

    def set(self, key: str, value: Dict[str, Any]) -> None:
        self._store[key] = value
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._store, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


_ELEV_CACHE = JsonDiskCache(ELEVATION_CACHE_FILE)


def parse_aaigrid_to_npz(asc_text: str, out_npz: Path = SRTM_30M_NPZ) -> Dict[str, Any]:
    """
    Parses an ESRI ASCII Grid (.asc) downloaded from OpenTopography into a fast compressed .npz.
    """
    lines = asc_text.splitlines()
    header: Dict[str, float] = {}
    data_start = 0
    for idx, line in enumerate(lines[:12]):
        parts = line.strip().split()
        if len(parts) == 2 and parts[0].lower() in (
            "ncols",
            "nrows",
            "xllcorner",
            "yllcorner",
            "xllcenter",
            "yllcenter",
            "cellsize",
            "nodata_value",
        ):
            header[parts[0].lower()] = float(parts[1])
            data_start = idx + 1
        else:
            break

    nrows = int(header["nrows"])
    ncols = int(header["ncols"])
    cellsize = float(header["cellsize"])
    if "xllcorner" in header:
        xll = float(header["xllcorner"])
    else:
        xll = float(header["xllcenter"]) - 0.5 * cellsize
    if "yllcorner" in header:
        yll = float(header["yllcorner"])
    else:
        yll = float(header["yllcenter"]) - 0.5 * cellsize
    nodata = float(header.get("nodata_value", -9999.0))

    grid = np.loadtxt(lines[data_start:], dtype=np.float32)
    if grid.shape != (nrows, ncols):
        grid = grid.reshape((nrows, ncols))

    out_npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out_npz,
        grid=grid,
        nrows=np.int32(nrows),
        ncols=np.int32(ncols),
        xllcorner=np.float64(xll),
        yllcorner=np.float64(yll),
        cellsize=np.float64(cellsize),
        nodata=np.float32(nodata),
    )
    global _SRTM_CACHE_DATA
    if out_npz == SRTM_30M_NPZ:
        _SRTM_CACHE_DATA = None
    return {"nrows": nrows, "ncols": ncols, "cellsize_deg": cellsize}


def _read_npz_dem(npz_path: Path) -> Optional[Dict[str, Any]]:
    if not npz_path.exists():
        return None
    try:
        z = np.load(npz_path)
        return {
            "grid": z["grid"],
            "nrows": int(z["nrows"]),
            "ncols": int(z["ncols"]),
            "xll": float(z["xllcorner"]),
            "yll": float(z["yllcorner"]),
            "cellsize": float(z["cellsize"]),
            "nodata": float(z["nodata"]),
        }
    except Exception:
        return None


def _load_srtm_npz() -> Optional[Dict[str, Any]]:
    global _SRTM_CACHE_DATA
    if _SRTM_CACHE_DATA is not None:
        return _SRTM_CACHE_DATA
    _SRTM_CACHE_DATA = _read_npz_dem(SRTM_30M_NPZ)
    return _SRTM_CACHE_DATA


def _aspect_from_grad(
    dz_dx: float,
    dz_dy: float,
    slope_pct: Optional[float] = None,
) -> Tuple[Optional[float], str, str]:
    """
    Computes downhill slope facing direction (aspect azimuth clockwise from North)
    and Andean (approx. 7 deg S) insolation/frost guidance from terrain gradients.
    """
    grad_pct = slope_pct if slope_pct is not None else math.hypot(dz_dx, dz_dy) * 100.0
    if grad_pct < 2.0 or (abs(dz_dx) < 1e-6 and abs(dz_dy) < 1e-6):
        return (
            None,
            "Plano / Fondo de valle",
            "Terreno casi plano; vigilar acumulación de aire frío (inversión térmica) o empozamiento en lluvias.",
        )

    # Downhill vector points opposite the uphill gradient (+x=East, +y=North)
    az_deg = (math.degrees(math.atan2(-dz_dx, -dz_dy)) + 360.0) % 360.0
    sectors = [
        ("Norte (N)", "Ladera hacia el Norte: recibe buena insolación en invierno austral; secado rápido tras lluvias."),
        ("Noreste (NE)", "Ladera Noreste: recibe sol de mañana temprano; ayuda a disipar escarcha y rocío matinal."),
        ("Este (E)", "Ladera hacia el Este: sol de mañana ayuda a reducir humedad foliar temprana (rancha/oidio)."),
        ("Sureste (SE)", "Ladera Sureste: exposición moderada-fría; retiene humedad más tiempo en estiaje."),
        ("Sur (S)", "Ladera hacia el Sur: menor sol directo en mayo–agosto; mayor retención de humedad y frío."),
        ("Suroeste (SO)", "Ladera Suroeste: menor radiación invernal y viento vespertino; priorizar cobertura viva."),
        ("Oeste (O)", "Ladera hacia el Oeste: mayor calentamiento en la tarde y sombra relativa en madrugadas."),
        ("Noroeste (NO)", "Ladera Noroeste: buena exposición solar vespertina y menor estancamiento de aire frío."),
    ]
    idx = int(((az_deg + 22.5) % 360.0) // 45.0)
    label, note = sectors[idx]
    return round(az_deg, 1), label, note


def _summarize_vertex_differential_risk(
    pt_elevs: List[float],
    pt_slopes: List[float],
    has_polygon: bool,
) -> Optional[str]:
    """
    Compares intra-parcel vertex elevation & slope spread to pinpoint cold-air pooling vs runoff corners.
    """
    if not pt_elevs or not has_polygon:
        return None
    elev_span = max(pt_elevs) - min(pt_elevs)
    slope_max = max(pt_slopes) if pt_slopes else 0.0
    slope_min = min(pt_slopes) if pt_slopes else 0.0
    parts: List[str] = []
    if elev_span >= 4.0:
        parts.append(
            f"Tu terreno tiene {elev_span:.0f} m de desnivel (entre {min(pt_elevs):.0f} y {max(pt_elevs):.0f} m): "
            "la parte baja junta más frío y humedad, y la parte alta escurre primero."
        )
    if slope_max >= 12.0 or (slope_max - slope_min) >= 3.5:
        parts.append(
            f"La zona más inclinada llega a {slope_max:.1f}% (frente a {slope_min:.1f}% en lo plano): "
            "conviene hacer surcos siguiendo la ladera y mantener cobertura verde para cuidar la tierra."
        )
    if not parts:
        parts.append(
            f"Terreno bastante parejo (entre {min(pt_elevs):.0f} y {max(pt_elevs):.0f} m, inclinación máx. {slope_max:.1f}%)."
        )
    return " ".join(parts)


def _sample_npz_grid(
    dem: Dict[str, Any],
    lat: float,
    lon: float,
    polygon: Optional[List[List[float]]] = None,
    *,
    mode: str = "guardado",
    resolution: str = "30 m reales en grilla Cajamarca",
) -> Optional[Dict[str, Any]]:
    """
    Samples real SRTM 30 m elevation, slope (%), aspect, and intra-parcel vertex variance
    from a loaded AAIGrid NPZ dict. Row 0 in AAIGrid is northernmost edge: y_top = yll + nrows * cellsize.
    """
    nrows = dem["nrows"]
    ncols = dem["ncols"]
    xll = dem["xll"]
    yll = dem["yll"]
    cs = dem["cellsize"]
    nodata = dem["nodata"]
    grid = dem["grid"]
    ytop = yll + nrows * cs

    def _at(la: float, lo: float) -> Optional[Tuple[float, int, int]]:
        col = int((lo - xll) / cs)
        row = int((ytop - la) / cs)
        if row < 1 or row >= nrows - 1 or col < 1 or col >= ncols - 1:
            return None
        val = float(grid[row, col])
        if abs(val - nodata) < 1e-3 or val < -100 or val > 6500:
            return None
        return val, row, col

    has_polygon = bool(polygon and len(polygon) >= 3)
    pts: List[Tuple[float, float]] = [(lat, lon)]
    if has_polygon and polygon is not None:
        pts.extend((float(p[0]), float(p[1])) for p in polygon[:12])

    elevs: List[float] = []
    slopes: List[float] = []
    gx_list: List[float] = []
    gy_list: List[float] = []
    dx_m = 2.0 * cs * 111320.0 * math.cos(math.radians(lat))
    dy_m = 2.0 * cs * 110574.0

    for la, lo in pts:
        res = _at(la, lo)
        if res is None:
            continue
        val, r, c = res
        elevs.append(val)
        z_e = float(grid[r, c + 1])
        z_w = float(grid[r, c - 1])
        z_n = float(grid[r - 1, c])
        z_s = float(grid[r + 1, c])
        if all(abs(v - nodata) > 1e-3 and v > -100 for v in (z_e, z_w, z_n, z_s)):
            dz_dx = (z_e - z_w) / max(1.0, dx_m)
            dz_dy = (z_n - z_s) / max(1.0, dy_m)
            slopes.append(math.hypot(dz_dx, dz_dy) * 100.0)
            gx_list.append(dz_dx)
            gy_list.append(dz_dy)

    if not elevs:
        return None

    mean_slope = round(float(np.clip(np.mean(slopes) if slopes else 4.0, 0.8, 45.0)), 1)
    slope_min = round(float(np.clip(min(slopes) if slopes else mean_slope, 0.5, 45.0)), 1)
    slope_max = round(float(np.clip(max(slopes) if slopes else mean_slope, 0.8, 55.0)), 1)
    elev_min = round(float(min(elevs)), 1)
    elev_max = round(float(max(elevs)), 1)
    elev_span = round(elev_max - elev_min, 1)
    mean_dx = float(np.mean(gx_list)) if gx_list else 0.0
    mean_dy = float(np.mean(gy_list)) if gy_list else 0.0
    aspect_deg, aspect_label, aspect_note = _aspect_from_grad(mean_dx, mean_dy, mean_slope)
    vertex_risk = _summarize_vertex_differential_risk(elevs, slopes, has_polygon)

    return {
        "elevation_m": round(float(np.mean(elevs)), 1),
        "elevation_min_m": elev_min,
        "elevation_max_m": elev_max,
        "elevation_span_m": elev_span,
        "slope_pct": mean_slope,
        "slope_min_pct": slope_min,
        "slope_max_pct": slope_max,
        "aspect_deg": aspect_deg,
        "aspect_label": aspect_label,
        "aspect_insolation_note": aspect_note,
        "polygon_vertices_sampled": max(0, len(elevs) - 1) if has_polygon else 0,
        "vertex_differential_risk": vertex_risk,
        "source": "srtm_30m_opentopography",
        "mode": mode,
        "sensor_label": "SRTM GL1 (30 m · OpenTopography)",
        "resolution": resolution,
    }


def sample_srtm_30m(
    lat: float,
    lon: float,
    polygon: Optional[List[List[float]]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Samples real SRTM 30 m elevation & terrain slope (%) from pre-cached OpenTopography grid.
    """
    dem = _load_srtm_npz()
    if dem is None:
        return None
    return _sample_npz_grid(
        dem,
        lat,
        lon,
        polygon=polygon,
        mode="guardado",
        resolution="30 m reales en grilla Cajamarca",
    )


async def fetch_opentopography_microtile_30m(
    lat: float,
    lon: float,
    polygon: Optional[List[List[float]]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Fetches & caches an on-demand 30 m SRTM GL1 micro-tile (~7x7 km) from OpenTopography
    for coordinates outside the main Cajamarca province cache (e.g., Jaén, Chota, Celendín, Cajabamba).
    """
    if not has_opentopography_key():
        return None

    tile_lat = round(round(lat / 0.05) * 0.05, 2)
    tile_lon = round(round(lon / 0.05) * 0.05, 2)
    tile_key = f"{tile_lat:.2f}_{tile_lon:.2f}"
    tile_path = SRTM_TILES_DIR / f"srtm30_{tile_key}.npz"

    cached_dem = _TILE_MEMORY_CACHE.get(tile_key)
    if cached_dem is not None:
        sampled = _sample_npz_grid(
            cached_dem,
            lat,
            lon,
            polygon=polygon,
            mode="guardado",
            resolution="30 m reales (tesela SRTM GL1)",
        )
        if sampled is not None:
            return sampled

    if tile_path.exists():
        disk_dem = _read_npz_dem(tile_path)
        if disk_dem is not None:
            if len(_TILE_MEMORY_CACHE) >= 24:
                _TILE_MEMORY_CACHE.pop(next(iter(_TILE_MEMORY_CACHE)), None)
            _TILE_MEMORY_CACHE[tile_key] = disk_dem
            sampled = _sample_npz_grid(
                disk_dem,
                lat,
                lon,
                polygon=polygon,
                mode="guardado",
                resolution="30 m reales (tesela SRTM GL1)",
            )
            if sampled is not None:
                return sampled

    half = 0.032
    params = {
        "demtype": "SRTMGL1",
        "south": round(tile_lat - half, 4),
        "north": round(tile_lat + half, 4),
        "west": round(tile_lon - half, 4),
        "east": round(tile_lon + half, 4),
        "outputFormat": "AAIGrid",
        "API_Key": get_opentopography_key(),
    }
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(OPENTOPOGRAPHY_URL, params=params)
            if resp.status_code != 200 or "ncols" not in resp.text[:200].lower():
                return None
        parse_aaigrid_to_npz(resp.text, out_npz=tile_path)
        live_dem = _read_npz_dem(tile_path)
        if live_dem is None:
            return None
        if len(_TILE_MEMORY_CACHE) >= 24:
            _TILE_MEMORY_CACHE.pop(next(iter(_TILE_MEMORY_CACHE)), None)
        _TILE_MEMORY_CACHE[tile_key] = live_dem
        return _sample_npz_grid(
            live_dem,
            lat,
            lon,
            polygon=polygon,
            mode="en_vivo",
            resolution="30 m reales (OpenTopography SRTM GL1)",
        )
    except Exception:
        return None


async def fetch_open_meteo_elevation(
    lat: float,
    lon: float,
    polygon: Optional[List[List[float]]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Zero-key live Copernicus DEM GLO-90 elevation + local slope estimate via Open-Meteo Elevation API.
    Samples center + ~180 m NSEW stencil (plus polygon vertices if provided).
    """
    cache_key = f"{round(lat, 3):.3f},{round(lon, 3):.3f},{len(polygon) if polygon else 0}"
    if not polygon:
        cached = _ELEV_CACHE.get(cache_key)
        if cached is not None:
            return {**cached, "mode": "guardado"}

    d_deg = 0.0016  # ~178 m spacing reduces 1 m quantization noise on 90 m DEM
    sample_pts: List[Tuple[float, float]] = [
        (lat, lon),
        (lat + d_deg, lon),
        (lat - d_deg, lon),
        (lat, lon + d_deg),
        (lat, lon - d_deg),
    ]
    if polygon and len(polygon) >= 3:
        sample_pts.extend((float(p[0]), float(p[1])) for p in polygon[:10])

    lat_str = ",".join(f"{p[0]:.5f}" for p in sample_pts)
    lon_str = ",".join(f"{p[1]:.5f}" for p in sample_pts)

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                OPEN_METEO_ELEV_URL,
                params={"latitude": lat_str, "longitude": lon_str},
            )
            resp.raise_for_status()
            elevs = resp.json().get("elevation", [])

        if not isinstance(elevs, list) or len(elevs) < 5:
            return None

        c_elev = float(elevs[0])
        z_n, z_s, z_e, z_w = [float(x) for x in elevs[1:5]]
        dy_m = 2.0 * d_deg * 110574.0
        dx_m = 2.0 * d_deg * 111320.0 * math.cos(math.radians(lat))
        dz_dx = (z_e - z_w) / dx_m
        dz_dy = (z_n - z_s) / dy_m
        stencil_slope = math.hypot(dz_dx, dz_dy) * 100.0

        has_polygon = bool(polygon and len(polygon) >= 3)
        poly_elevs = [float(x) for x in elevs[5:]] if len(elevs) > 5 else []
        all_elevs = ([c_elev] + poly_elevs) if poly_elevs else [c_elev]
        if poly_elevs:
            c_elev = float(np.mean(all_elevs))

        mean_slope = round(float(np.clip(stencil_slope, 1.0, 42.0)), 1)
        aspect_deg, aspect_label, aspect_note = _aspect_from_grad(dz_dx, dz_dy, mean_slope)
        elev_min = round(float(min(all_elevs)), 1)
        elev_max = round(float(max(all_elevs)), 1)
        vertex_risk = _summarize_vertex_differential_risk(
            all_elevs,
            [mean_slope],
            has_polygon and len(poly_elevs) >= 2,
        )

        payload = {
            "elevation_m": round(c_elev, 1),
            "elevation_min_m": elev_min,
            "elevation_max_m": elev_max,
            "elevation_span_m": round(elev_max - elev_min, 1),
            "slope_pct": mean_slope,
            "slope_min_pct": mean_slope,
            "slope_max_pct": mean_slope,
            "aspect_deg": aspect_deg,
            "aspect_label": aspect_label,
            "aspect_insolation_note": aspect_note,
            "polygon_vertices_sampled": len(poly_elevs),
            "vertex_differential_risk": vertex_risk,
            "source": "open_meteo_cop90",
            "mode": "en_vivo",
            "sensor_label": "Copernicus DEM GLO-90 (Open-Meteo)",
            "resolution": "~90 m en vivo (grilla local de pendiente)",
        }
        if not polygon:
            _ELEV_CACHE.set(cache_key, payload)
        return payload
    except Exception:
        return None


async def resolve_real_dem_terrain(
    lat: float,
    lon: float,
    polygon: Optional[List[List[float]]] = None,
) -> Optional[Dict[str, Any]]:
    """Resolves real terrain elevation & slope preferring SRTM 30 m (regional cache + on-demand OpenTopography) over live DEM 90 m."""
    srtm = sample_srtm_30m(lat, lon, polygon=polygon)
    if srtm is not None:
        return srtm
    srtm_tile = await fetch_opentopography_microtile_30m(lat, lon, polygon=polygon)
    if srtm_tile is not None:
        return srtm_tile
    return await fetch_open_meteo_elevation(lat, lon, polygon=polygon)

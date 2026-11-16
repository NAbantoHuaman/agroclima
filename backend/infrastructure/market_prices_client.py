"""Live Peruvian agricultural market price client (MIDAGRI SISAP, Agromercado, EMMSA, BCRP)."""

from __future__ import annotations

import asyncio
import copy
import html
import json
import math
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import httpx

from config import MARKET_PRICES_CACHE_FILE

LIMA_TZ = ZoneInfo("America/Lima")

SISAP_CIUDADES_URL = "http://sistemas.midagri.gob.pe/sisap/portal2/ciudades/"
SISAP_FILTRAR_REGION_URL = "http://sistemas.midagri.gob.pe/sisap/portal2/ciudades/generos/filtrarPorRegion"
SISAP_RESUMEN_URL = "http://sistemas.midagri.gob.pe/sisap/portal2/ciudades/resumenes/filtrar"
AGROMERCADO_API_URL = "https://observatorio.agromercado.gob.pe/api/productos"
EMMSA_CONTROLLER_URL = "https://rpdiarios.emmsa.com.pe/controller/precios.php"
BCRP_FX_URL = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD04640PD/json"
BCRP_IPC_URL = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN01313PM/json"

CACHE_TTL_SECONDS = 12 * 3600  # 12 horas por actualización diaria de mercados

_SISAP_MARKETS: List[Dict[str, Any]] = [
    {"code": "060000", "name": "Cajamarca", "lat": -7.1638, "lon": -78.5003},
    {"code": "060401", "name": "Chota", "lat": -6.5600, "lon": -78.6500},
    {"code": "060801", "name": "Jaén", "lat": -5.7080, "lon": -78.8080},
]

_TARGET_SISAP_GENUS_CODES = [
    "0102",  # Olluco
    "0104",  # Papa
    "0204",  # Ajo
    "0212",  # Cebolla
    "0301",  # Arveja grano verde
    "0303",  # Haba grano verde
    "0306",  # Tarhui (si hubiera registro)
    "0403",  # Choclo
    "0405",  # Quinua
    "0501",  # Frijol grano seco
    "0502",  # Garbanzo grano seco
    "0504",  # Lenteja grano seco
    "0626",  # Palta
]

_TARGET_EMMSA_KEYWORDS = (
    "PAPA",
    "ARVEJA",
    "HABA",
    "FREJOL",
    "FRIJOL",
    "LENTEJA",
    "AJO",
    "CEBOLLA",
    "OLLUCO",
    "MAIZ",
    "OREGANO",
    "ROMERO",
    "TUNA",
    "PALTA",
)

# Tabla explícita de conversión Mayorista/FOB -> Precio en chacra Cajamarca × Rinde regional (INIA/DRA)
_CROP_LIVE_SPECS: Dict[str, Dict[str, Any]] = {
    "papa": {
        "strategy": "sisap_then_emmsa",
        "sisap_names": ["Papa canchan", "Papa huayro", "Papa peruanita", "Papa yungay"],
        "sisap_agg": "mean",
        "emmsa_names": ["PAPA CANCHAN", "PAPA YUNGAY", "PAPA BLANCA/VALLE/OTROS", "PAPA HUAYRO"],
        "farmgate_factor": 0.62,
        "yield_kg_ha_ref": 11200,
        "quote_label": "Promedio papa blanca/color en mercado",
    },
    "maiz_amilaceo": {
        "strategy": "sisap_then_emmsa",
        "sisap_names": ["Choclo (tipo cusco)"],
        "emmsa_names": ["MAIZ MORADO FRESC/MOJAD/SARASO/SECO"],
        "farmgate_factor": 0.56,
        "yield_kg_ha_ref": 2500,
        "emmsa_farmgate_factor": 0.72,
        "emmsa_yield_kg_ha_ref": 2800,
        "quote_label": "Choclo tipo Cusco (equiv. comercial)",
        "emmsa_quote_label": "Maíz morado amiláceo (EMMSA)",
    },
    "quinua": {
        "strategy": "sisap_or_agromercado",
        "sisap_names": ["Quinua"],
        "agromercado_slug": "quinua",
        "prefer_metric": "mayorista",
        "farmgate_factor": 0.68,
        "yield_kg_ha_ref": 1300,
        "quote_label": "Quinua Blanca mayorista",
    },
    "arveja": {
        "strategy": "sisap_then_emmsa",
        "sisap_names": ["Arveja verde blanca serrana"],
        "emmsa_names": ["ARVEJA VERDE BLANCA SERRANA", "ARVEJA VERDE AMER/MEJ"],
        "farmgate_factor": 0.64,
        "yield_kg_ha_ref": 1800,
        "quote_label": "Arveja verde blanca serrana",
    },
    "haba": {
        "strategy": "sisap_then_emmsa",
        "sisap_names": ["Haba verde serrana"],
        "emmsa_names": ["HABA VERDE SERRANA"],
        "farmgate_factor": 0.65,
        "yield_kg_ha_ref": 2600,
        "quote_label": "Haba verde serrana",
    },
    "frijol": {
        "strategy": "sisap_then_emmsa",
        "sisap_names": ["Frijol canario", "Frijol castilla"],
        "emmsa_names": ["FREJOL VERDE CANARIO"],
        "farmgate_factor": 0.72,
        "yield_kg_ha_ref": 1200,
        "quote_label": "Frijol canario",
    },
    "lenteja": {
        "strategy": "sisap_only",
        "sisap_names": ["Lenteja", "Garbanzo"],
        "farmgate_factor": 0.70,
        "yield_kg_ha_ref": 1050,
        "quote_label": "Lenteja grano seco",
    },
    "oca_olluco_mashua": {
        "strategy": "sisap_then_emmsa",
        "sisap_names": ["Olluco largo", "Olluco redondo"],
        "emmsa_names": ["OLLUCO LARGO"],
        "farmgate_factor": 0.58,
        "yield_kg_ha_ref": 4000,
        "quote_label": "Olluco largo/redondo (ref. tubérculos)",
    },
    "ajo_valle": {
        "strategy": "sisap_then_emmsa",
        "sisap_names": ["Ajo criollo o napuri"],
        "emmsa_names": ["AJO CRIOLLO O NAPURI"],
        "farmgate_factor": 0.72,
        "yield_kg_ha_ref": 5800,
        "quote_label": "Ajo criollo o napurí",
    },
    "palta_intercultivo": {
        "strategy": "agromercado_or_sisap",
        "agromercado_slug": "palta",
        "prefer_metric": "mayorista",
        "sisap_names": ["Palta fuerte"],
        "emmsa_names": ["PALTA FUERTE"],
        "farmgate_factor": 0.65,
        "yield_kg_ha_ref": 6200,
        "quote_label": "Palta Hass / Fuerte mayorista",
    },
    "cafe": {
        "strategy": "agromercado_fob",
        "agromercado_slug": "cafe",
        "farmgate_factor": 0.56,  # Paridad FOB oro -> café pergamino seco en finca Jaén/San Ignacio
        "yield_kg_ha_ref": 1000,
        "quote_label": "Paridad FOB café verde → pergamino chacra",
    },
    "cacao": {
        "strategy": "agromercado_cacao",
        "agromercado_slug": "cacao",
        "farmgate_factor": 0.80,  # Paridad FOB grano seco -> cacao fermentado en chacra (o chacra directa)
        "yield_kg_ha_ref": 920,
        "quote_label": "Cacao grano seco (Agromercado FOB/chacra)",
    },
    "tuna_cochinilla": {
        "strategy": "emmsa_mixed_coproduct",
        "emmsa_names": ["TUNA HUAROCHIRI"],
        "farmgate_factor": 0.65,
        "yield_kg_ha_ref": 1500,
        "coproduct_ref_soles_ha": 4750,  # Aporte referencial de cochinilla carmín seca INIA/Sierra Exp.
        "quote_label": "Tuna fruta fresca (EMMSA) + cochinilla ref. INIA",
    },
    "tomillo_aromaticas": {
        "strategy": "emmsa_only",
        "emmsa_names": ["OREGANO SECO"],
        "farmgate_factor": 0.68,
        "yield_kg_ha_ref": 1350,
        "quote_label": "Hierba aromática seca (Orégano seco EMMSA)",
    },
}

_MEM_SNAPSHOT: Optional[Dict[str, Any]] = None
_MEM_LOADED_AT: float = 0.0
_FETCH_LOCK: Optional[asyncio.Lock] = None


def _get_lock() -> asyncio.Lock:
    global _FETCH_LOCK
    if _FETCH_LOCK is None:
        _FETCH_LOCK = asyncio.Lock()
    return _FETCH_LOCK


def _read_disk_cache() -> Optional[Dict[str, Any]]:
    path = Path(MARKET_PRICES_CACHE_FILE)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _write_disk_cache(payload: Dict[str, Any]) -> None:
    try:
        Path(MARKET_PRICES_CACHE_FILE).parent.mkdir(parents=True, exist_ok=True)
        Path(MARKET_PRICES_CACHE_FILE).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def _parse_sisap_ciudades_table(raw_html: str) -> Dict[str, Dict[str, Any]]:
    """Parses MIDAGRI SISAP Precios de Ciudades interval HTML table into normalized S/kg quotes."""
    if not raw_html or "<table" not in raw_html.lower():
        return {}
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", raw_html, flags=re.I | re.S)
    parsed: List[List[Tuple[int, str]]] = []
    for r in rows:
        row_cells: List[Tuple[int, str]] = []
        for m in re.finditer(r"<t[dh]([^>]*)>(.*?)</t[dh]>", r, flags=re.I | re.S):
            attrs, inner = m.group(1), m.group(2)
            cs = 1
            mc = re.search(r"colspan\s*=\s*[\"']?(\d+)", attrs, flags=re.I)
            if mc:
                cs = int(mc.group(1))
            txt = html.unescape(re.sub(r"<[^>]+>", "", inner))
            txt = re.sub(r"\s+", " ", txt).strip()
            row_cells.append((cs, txt))
        if row_cells:
            parsed.append(row_cells)

    if len(parsed) < 5:
        return {}

    product_headers = parsed[1]
    data_start_idx = next(
        (i for i, rw in enumerate(parsed) if rw and re.match(r"^\d{2}/\d{2}/\d{4}$", rw[0][1])),
        4,
    )
    data_rows = parsed[data_start_idx:]
    if not data_rows:
        return {}

    results: Dict[str, Dict[str, Any]] = {}
    col_cursor = 1
    for cs, pname in product_headers:
        width = max(1, int(cs))
        end_col = col_cursor + width
        latest_may: Optional[Dict[str, Any]] = None
        latest_min: Optional[Dict[str, Any]] = None

        for dr in reversed(data_rows):
            vals = [c[1] for c in dr]
            if not vals or not re.match(r"^\d{2}/\d{2}/\d{4}$", vals[0]):
                continue
            if end_col > len(vals):
                continue
            date_str = vals[0]
            block = vals[col_cursor:end_col]

            # Triplets: (unit, equiv_kg, price) for Mayorista (0..2) and Minorista (3..5)
            if len(block) >= 3 and latest_may is None and block[2]:
                parsed_q = _normalize_sisap_triplet(date_str, block[0], block[1], block[2])
                if parsed_q:
                    latest_may = parsed_q
            if len(block) >= 6 and latest_min is None and block[5]:
                parsed_q = _normalize_sisap_triplet(date_str, block[3], block[4], block[5])
                if parsed_q:
                    latest_min = parsed_q
            if latest_may and latest_min:
                break

        if latest_may or latest_min:
            results[pname] = {
                "product": pname,
                "mayorista": latest_may,
                "minorista": latest_min,
            }
        col_cursor = end_col

    return results


def _normalize_sisap_triplet(
    date_str: str,
    unit: str,
    equiv_raw: str,
    price_raw: str,
) -> Optional[Dict[str, Any]]:
    try:
        equiv = float(equiv_raw.replace(",", "")) if equiv_raw else 1.0
        price = float(price_raw.replace(",", ""))
    except ValueError:
        return None
    if equiv <= 0 or price <= 0:
        return None
    soles_kg = round(price / equiv, 2)
    if not (0.2 <= soles_kg <= 120.0):
        return None
    return {
        "date": date_str,
        "soles_kg": soles_kg,
        "unit": unit or "Kilogramo",
        "equiv_kg": round(equiv, 2),
        "raw_price": round(price, 2),
    }


async def _fetch_sisap_all_regions(client: httpx.AsyncClient) -> Dict[str, Any]:
    r_init = await client.get(SISAP_CIUDADES_URL)
    r_init.raise_for_status()
    m_post = re.search(r"name=[\"']?postID[\"']?\s+value=[\"']?([a-f0-9]+)", r_init.text, flags=re.I)
    postid = m_post.group(1) if m_post else ""
    now_lima = datetime.now(LIMA_TZ)
    desde = (now_lima - timedelta(days=14)).strftime("%d/%m/%Y")
    hasta = now_lima.strftime("%d/%m/%Y")

    async def _fetch_region(mkt: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        code = mkt["code"]
        hdrs = {"X-Requested-With": "XMLHttpRequest", "Referer": SISAP_CIUDADES_URL}
        rg = await client.post(
            SISAP_FILTRAR_REGION_URL,
            data={"region": code, "ajax": "true"},
            headers=hdrs,
        )
        rg.raise_for_status()
        avail = set(re.findall(r"value=[\"']?(\w+)[\"']?[^>]*type=checkbox", rg.text, flags=re.I))
        if not avail:
            avail = set(re.findall(r"<input value=(\w+) type=checkbox", rg.text, flags=re.I))
        selected = [c for c in _TARGET_SISAP_GENUS_CODES if c in avail]
        if not selected:
            return code, {"code": code, "name": mkt["name"], "products": {}}
        params: List[Tuple[str, str]] = [
            ("periodicidad", "intervalo"),
            ("desde", desde),
            ("hasta", hasta),
            ("region", code),
            ("variables[]", "may_precio_prom"),
            ("variables[]", "min_precio_prom"),
            ("postID", postid),
            ("ajax", "true"),
        ] + [("productos[]", c) for c in selected]
        rr = await client.get(SISAP_RESUMEN_URL, params=params, headers=hdrs)
        rr.raise_for_status()
        return code, {
            "code": code,
            "name": mkt["name"],
            "products": _parse_sisap_ciudades_table(rr.text),
        }

    pairs = await asyncio.gather(
        *[_fetch_region(m) for m in _SISAP_MARKETS],
        return_exceptions=True,
    )
    regions_out: Dict[str, Any] = {}
    for res in pairs:
        if isinstance(res, tuple):
            code, payload = res
            regions_out[code] = payload
    return regions_out


async def _fetch_agromercado(client: httpx.AsyncClient) -> Dict[str, Dict[str, Any]]:
    r = await client.get(AGROMERCADO_API_URL)
    r.raise_for_status()
    data = r.json()
    items = data if isinstance(data, list) else data.get("data", [])
    out: Dict[str, Dict[str, Any]] = {}
    if not isinstance(items, list):
        return out
    for it in items:
        if not isinstance(it, dict) or not it.get("slug"):
            continue
        slug = str(it["slug"]).strip().lower()
        parsed_slots: Dict[str, Dict[str, Any]] = {}
        for slot_key in ("precio1", "precio2"):
            slot = it.get(slot_key)
            if not isinstance(slot, dict) or not slot.get("valor"):
                continue
            try:
                val = float(str(slot["valor"]).replace(",", ""))
            except ValueError:
                continue
            titulo = str(slot.get("titulo", "")).strip()
            t_low = titulo.lower()
            kind = "fob_usd_kg" if "fob" in t_low else ("chacra_soles_kg" if "chacra" in t_low else "mayorista_soles_kg")
            parsed_slots[kind] = {
                "titulo": titulo,
                "serie_nombre": str(slot.get("serie_nombre", "")).strip(),
                "valor": round(val, 2),
                "etiqueta": str(slot.get("etiqueta", "")).strip(),
            }
        if parsed_slots:
            out[slug] = parsed_slots
    return out


def _format_emmsa_date(raw_date: str) -> str:
    # '2026/11/14' -> '14/11/2026'
    parts = raw_date.strip().split("/")
    if len(parts) == 3 and len(parts[0]) == 4:
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return raw_date.strip()


async def _fetch_emmsa(client: httpx.AsyncClient) -> Dict[str, Any]:
    r_fechas = await client.get(f"{EMMSA_CONTROLLER_URL}?op=listar_fechas")
    r_fechas.raise_for_status()
    fechas = r_fechas.json()
    if not isinstance(fechas, list) or not fechas:
        return {"date": None, "items": {}}
    latest = fechas[0]
    r_prods = await client.get(
        EMMSA_CONTROLLER_URL,
        params={
            "op": "listar_productos",
            "anoenc": latest["anoenc"],
            "mesenc": latest["mesenc"],
            "numero": latest["numero"],
        },
    )
    r_prods.raise_for_status()
    prods = r_prods.json()
    sel_codes = [
        str(p["codpro"])
        for p in prods
        if isinstance(p, dict)
        and p.get("codpro")
        and any(kw in str(p.get("producto", "")).upper() for kw in _TARGET_EMMSA_KEYWORDS)
    ]
    if not sel_codes:
        return {"date": _format_emmsa_date(str(latest.get("fecha", ""))), "items": {}}

    r_rows = await client.post(
        f"{EMMSA_CONTROLLER_URL}?op=consultar_precios",
        data={
            "anoenc": latest["anoenc"],
            "mesenc": latest["mesenc"],
            "numero": latest["numero"],
            "productos[]": sel_codes,
        },
    )
    r_rows.raise_for_status()
    body = r_rows.json()
    date_label = _format_emmsa_date(str(latest.get("fecha", "")))
    items: Dict[str, Dict[str, Any]] = {}
    for row in body.get("data", []) if isinstance(body, dict) else []:
        if not isinstance(row, dict):
            continue
        variedad = str(row.get("variedad", "")).strip()
        try:
            prom = float(str(row.get("precio_prom", "0")).replace(",", ""))
        except ValueError:
            continue
        # Filtra filas vendidas por bulto/ciento (> 35 S/) donde EMMSA JSON no incluye equiv. kg
        if 0.3 <= prom <= 30.0:
            items[variedad.upper()] = {
                "variedad": variedad,
                "producto": str(row.get("producto", "")).strip(),
                "soles_kg": round(prom, 2),
                "date": date_label,
            }
    return {"date": date_label, "items": items}


async def _fetch_bcrp_indicators(client: httpx.AsyncClient) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "usd_pen": None,
        "usd_pen_date": None,
        "ipc_food_pct": None,
        "ipc_food_date": None,
    }
    res_fx, res_ipc = await asyncio.gather(
        client.get(BCRP_FX_URL),
        client.get(BCRP_IPC_URL),
        return_exceptions=True,
    )
    if isinstance(res_fx, httpx.Response) and res_fx.status_code == 200:
        try:
            periods = (res_fx.json() or {}).get("periods") or []
            for p in reversed(periods):
                vals = p.get("values") or []
                if vals and vals[0] != "n.d.":
                    out["usd_pen"] = round(float(vals[0]), 3)
                    out["usd_pen_date"] = str(p.get("name", ""))
                    break
        except Exception:
            pass
    if isinstance(res_ipc, httpx.Response) and res_ipc.status_code == 200:
        try:
            periods = (res_ipc.json() or {}).get("periods") or []
            for p in reversed(periods):
                vals = p.get("values") or []
                if vals and vals[0] != "n.d.":
                    out["ipc_food_pct"] = round(float(vals[0]), 2)
                    out["ipc_food_date"] = str(p.get("name", ""))
                    break
        except Exception:
            pass
    return out


async def fetch_live_market_snapshot(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Fetches official live Peruvian market prices in parallel (MIDAGRI SISAP Cajamarca/Chota/Jaén,
    MIDAGRI Observatorio Agromercado, EMMSA Lima, BCRP FX/IPC) with 12h disk+memory cache.
    """
    global _MEM_SNAPSHOT, _MEM_LOADED_AT
    now_ts = time.time()

    if not force_refresh and _MEM_SNAPSHOT is not None and (now_ts - _MEM_LOADED_AT) < CACHE_TTL_SECONDS:
        return _MEM_SNAPSHOT

    async with _get_lock():
        now_ts = time.time()
        if not force_refresh and _MEM_SNAPSHOT is not None and (now_ts - _MEM_LOADED_AT) < CACHE_TTL_SECONDS:
            return _MEM_SNAPSHOT

        disk = None if force_refresh else _read_disk_cache()
        if disk and (now_ts - float(disk.get("fetched_epoch", 0.0))) < CACHE_TTL_SECONDS:
            snap = copy.deepcopy(disk)
            snap["cache_hit"] = True
            snap["mode"] = "guardado"
            _MEM_SNAPSHOT = snap
            _MEM_LOADED_AT = now_ts
            return snap

        try:
            async with httpx.AsyncClient(timeout=7.5, follow_redirects=True) as client:
                sisap_res, agro_res, emmsa_res, bcrp_res = await asyncio.gather(
                    _fetch_sisap_all_regions(client),
                    _fetch_agromercado(client),
                    _fetch_emmsa(client),
                    _fetch_bcrp_indicators(client),
                    return_exceptions=True,
                )

            sisap_regions = sisap_res if isinstance(sisap_res, dict) else {}
            agromercado = agro_res if isinstance(agro_res, dict) else {}
            emmsa = emmsa_res if isinstance(emmsa_res, dict) else {"date": None, "items": {}}
            bcrp = bcrp_res if isinstance(bcrp_res, dict) else {}

            has_any_live = bool(
                any((r or {}).get("products") for r in sisap_regions.values())
                or agromercado
                or emmsa.get("items")
            )

            if has_any_live:
                snap = {
                    "fetched_at": datetime.now(LIMA_TZ).isoformat(timespec="seconds"),
                    "fetched_epoch": time.time(),
                    "cache_hit": False,
                    "mode": "en_vivo",
                    "sisap_regions": sisap_regions,
                    "agromercado": agromercado,
                    "emmsa": emmsa,
                    "bcrp": bcrp,
                }
                _write_disk_cache(snap)
                _MEM_SNAPSHOT = snap
                _MEM_LOADED_AT = time.time()
                return snap
        except Exception:
            pass

        if disk:
            snap = copy.deepcopy(disk)
            snap["cache_hit"] = True
            snap["mode"] = "guardado"
            _MEM_SNAPSHOT = snap
            _MEM_LOADED_AT = time.time()
            return snap

        return {
            "fetched_at": datetime.now(LIMA_TZ).isoformat(timespec="seconds"),
            "fetched_epoch": 0.0,
            "cache_hit": False,
            "mode": "referencia_inia",
            "sisap_regions": {},
            "agromercado": {},
            "emmsa": {"date": None, "items": {}},
            "bcrp": {},
        }


def _ordered_sisap_markets(lat: Optional[float], lon: Optional[float]) -> List[Dict[str, Any]]:
    if lat is None or lon is None:
        return list(_SISAP_MARKETS)
    return sorted(
        _SISAP_MARKETS,
        key=lambda m: math.hypot(float(lat) - float(m["lat"]), float(lon) - float(m["lon"])),
    )


def _match_sisap_quote(
    sisap_regions: Dict[str, Any],
    ordered_mkts: List[Dict[str, Any]],
    candidate_names: List[str],
    agg: str = "first",
) -> Optional[Dict[str, Any]]:
    for mkt in ordered_mkts:
        reg = sisap_regions.get(mkt["code"]) or {}
        prods = reg.get("products") or {}
        if not prods:
            continue
        matches: List[Tuple[str, float, str]] = []
        for cname in candidate_names:
            c_low = cname.lower()
            entry = prods.get(cname) or next(
                (v for k, v in prods.items() if k.lower() == c_low or c_low in k.lower()),
                None,
            )
            if not entry:
                continue
            q = entry.get("mayorista") or (
                {
                    "date": entry["minorista"]["date"],
                    "soles_kg": round(float(entry["minorista"]["soles_kg"]) * 0.78, 2),
                }
                if entry.get("minorista")
                else None
            )
            if q:
                matches.append((entry["product"], float(q["soles_kg"]), str(q["date"])))
                if agg == "first":
                    break
        if matches:
            avg_price = round(sum(p for _, p, _ in matches) / len(matches), 2)
            latest_date = max(d for _, _, d in matches)
            matched_lbl = ", ".join(n for n, _, _ in matches[:3])
            return {
                "wholesale_soles_kg": avg_price,
                "source": f"MIDAGRI SISAP · {mkt['name']}",
                "date": latest_date,
                "matched_label": matched_lbl,
                "region_code": mkt["code"],
            }
    return None


def _match_emmsa_quote(emmsa: Dict[str, Any], candidate_names: List[str]) -> Optional[Dict[str, Any]]:
    items = (emmsa or {}).get("items") or {}
    if not items:
        return None
    matches: List[Tuple[str, float, str]] = []
    for cname in candidate_names:
        c_up = cname.upper()
        hit = items.get(c_up) or next(
            (v for k, v in items.items() if c_up in k),
            None,
        )
        if hit:
            matches.append((hit["variedad"], float(hit["soles_kg"]), str(hit["date"])))
    if not matches:
        return None
    avg_p = round(sum(p for _, p, _ in matches) / len(matches), 2)
    return {
        "wholesale_soles_kg": avg_p,
        "source": "EMMSA · Gran Mercado Lima",
        "date": matches[0][2],
        "matched_label": matches[0][0],
    }


def _match_agromercado_quote(
    agromercado: Dict[str, Any],
    slug: str,
    usd_pen: float,
    mode: str,
) -> Optional[Dict[str, Any]]:
    entry = agromercado.get(slug)
    if not entry:
        return None
    if mode == "fob":
        fob = entry.get("fob_usd_kg")
        if not fob:
            return None
        return {
            "wholesale_soles_kg": round(float(fob["valor"]) * usd_pen, 2),
            "source": "MIDAGRI Agromercado (FOB) + BCRP",
            "date": f"{fob.get('etiqueta', '')} {fob.get('serie_nombre', '')}".strip(),
            "matched_label": f"FOB US$ {fob['valor']:.2f}/kg",
            "is_direct_chacra": False,
        }
    if mode == "cacao":
        chacra = entry.get("chacra_soles_kg")
        fob = entry.get("fob_usd_kg")
        if chacra and fob:
            try:
                c_yr = int(re.findall(r"\d{4}", chacra.get("serie_nombre", "0"))[0])
            except Exception:
                c_yr = 0
            try:
                f_yr = int(re.findall(r"\d{4}", fob.get("serie_nombre", "0"))[0])
            except Exception:
                f_yr = 0
            if c_yr >= f_yr and c_yr > 0:
                return {
                    "wholesale_soles_kg": float(chacra["valor"]),
                    "source": "MIDAGRI Agromercado (Chacra)",
                    "date": f"{chacra.get('etiqueta', '')} {chacra.get('serie_nombre', '')}".strip(),
                    "matched_label": f"Chacra directa S/ {chacra['valor']:.2f}/kg",
                    "is_direct_chacra": True,
                }
        if fob:
            return {
                "wholesale_soles_kg": round(float(fob["valor"]) * usd_pen, 2),
                "source": "MIDAGRI Agromercado (FOB) + BCRP",
                "date": f"{fob.get('etiqueta', '')} {fob.get('serie_nombre', '')}".strip(),
                "matched_label": f"FOB US$ {fob['valor']:.2f}/kg",
                "is_direct_chacra": False,
            }
        if chacra:
            return {
                "wholesale_soles_kg": float(chacra["valor"]),
                "source": "MIDAGRI Agromercado (Chacra)",
                "date": f"{chacra.get('etiqueta', '')} {chacra.get('serie_nombre', '')}".strip(),
                "matched_label": "Precio en chacra",
                "is_direct_chacra": True,
            }
        return None

    may = entry.get("mayorista_soles_kg")
    if may:
        return {
            "wholesale_soles_kg": float(may["valor"]),
            "source": "MIDAGRI Agromercado",
            "date": str(may.get("etiqueta", "")).strip(),
            "matched_label": str(may.get("serie_nombre", "")).strip() or "Mayorista",
            "is_direct_chacra": False,
        }
    fob = entry.get("fob_usd_kg")
    if fob:
        return {
            "wholesale_soles_kg": round(float(fob["valor"]) * usd_pen, 2),
            "source": "MIDAGRI Agromercado (FOB) + BCRP",
            "date": f"{fob.get('etiqueta', '')} {fob.get('serie_nombre', '')}".strip(),
            "matched_label": f"FOB US$ {fob['valor']:.2f}/kg",
            "is_direct_chacra": False,
        }
    return None


def _resolve_crop_live_quote(
    cid: str,
    spec: Dict[str, Any],
    snapshot: Dict[str, Any],
    ordered_mkts: List[Dict[str, Any]],
    usd_pen: float,
) -> Optional[Dict[str, Any]]:
    sisap = snapshot.get("sisap_regions") or {}
    agro = snapshot.get("agromercado") or {}
    emmsa = snapshot.get("emmsa") or {}
    strat = spec["strategy"]

    if strat == "sisap_then_emmsa":
        q = _match_sisap_quote(sisap, ordered_mkts, spec["sisap_names"], spec.get("sisap_agg", "first"))
        if q:
            return {
                **q,
                "farmgate_factor": spec["farmgate_factor"],
                "yield_kg_ha_ref": spec["yield_kg_ha_ref"],
                "quote_label": spec["quote_label"],
                "price_mode": "en_vivo" if snapshot.get("mode") == "en_vivo" else "guardado",
            }
        qe = _match_emmsa_quote(emmsa, spec.get("emmsa_names", []))
        if qe:
            return {
                **qe,
                "farmgate_factor": spec.get("emmsa_farmgate_factor", spec["farmgate_factor"]),
                "yield_kg_ha_ref": spec.get("emmsa_yield_kg_ha_ref", spec["yield_kg_ha_ref"]),
                "quote_label": spec.get("emmsa_quote_label", spec["quote_label"]),
                "price_mode": "en_vivo" if snapshot.get("mode") == "en_vivo" else "guardado",
            }
        return None

    if strat == "sisap_only":
        q = _match_sisap_quote(sisap, ordered_mkts, spec["sisap_names"], spec.get("sisap_agg", "first"))
        if not q:
            return None
        return {
            **q,
            "farmgate_factor": spec["farmgate_factor"],
            "yield_kg_ha_ref": spec["yield_kg_ha_ref"],
            "quote_label": spec["quote_label"],
            "price_mode": "en_vivo" if snapshot.get("mode") == "en_vivo" else "guardado",
        }

    if strat == "sisap_or_agromercado":
        q = _match_sisap_quote(sisap, ordered_mkts, spec["sisap_names"])
        if not q:
            q = _match_agromercado_quote(agro, spec["agromercado_slug"], usd_pen, "mayorista")
        if not q:
            return None
        return {
            **q,
            "farmgate_factor": spec["farmgate_factor"],
            "yield_kg_ha_ref": spec["yield_kg_ha_ref"],
            "quote_label": spec["quote_label"],
            "price_mode": "en_vivo" if snapshot.get("mode") == "en_vivo" else "guardado",
        }

    if strat == "agromercado_or_sisap":
        qa = _match_agromercado_quote(agro, spec["agromercado_slug"], usd_pen, "mayorista")
        qs = _match_sisap_quote(sisap, ordered_mkts, spec.get("sisap_names", []))
        # Si el agricultor está en sierra/Cajamarca y SISAP tiene Palta Fuerte local razonable, o Hass nacional
        q = qs if (qs and ordered_mkts and ordered_mkts[0]["code"] in ("060000", "060401")) else (qa or qs)
        if not q:
            q = _match_emmsa_quote(emmsa, spec.get("emmsa_names", []))
        if not q:
            return None
        return {
            **q,
            "farmgate_factor": spec["farmgate_factor"],
            "yield_kg_ha_ref": spec["yield_kg_ha_ref"],
            "quote_label": spec["quote_label"],
            "price_mode": "en_vivo" if snapshot.get("mode") == "en_vivo" else "guardado",
        }

    if strat == "agromercado_fob":
        q = _match_agromercado_quote(agro, spec["agromercado_slug"], usd_pen, "fob")
        if not q:
            return None
        return {
            **q,
            "farmgate_factor": spec["farmgate_factor"],
            "yield_kg_ha_ref": spec["yield_kg_ha_ref"],
            "quote_label": spec["quote_label"],
            "price_mode": "en_vivo" if snapshot.get("mode") == "en_vivo" else "guardado",
        }

    if strat == "agromercado_cacao":
        q = _match_agromercado_quote(agro, spec["agromercado_slug"], usd_pen, "cacao")
        if not q:
            return None
        factor = 1.0 if q.get("is_direct_chacra") else spec["farmgate_factor"]
        return {
            **q,
            "farmgate_factor": factor,
            "yield_kg_ha_ref": spec["yield_kg_ha_ref"],
            "quote_label": spec["quote_label"],
            "price_mode": "en_vivo" if snapshot.get("mode") == "en_vivo" else "guardado",
        }

    if strat == "emmsa_mixed_coproduct":
        qe = _match_emmsa_quote(emmsa, spec.get("emmsa_names", []))
        if not qe:
            return None
        return {
            **qe,
            "source": f"{qe['source']} + Ref. INIA (cochinilla)",
            "farmgate_factor": spec["farmgate_factor"],
            "yield_kg_ha_ref": spec["yield_kg_ha_ref"],
            "coproduct_ref_soles_ha": spec.get("coproduct_ref_soles_ha", 0),
            "quote_label": spec["quote_label"],
            "price_mode": "mixto_en_vivo",
        }

    if strat == "emmsa_only":
        qe = _match_emmsa_quote(emmsa, spec.get("emmsa_names", []))
        if not qe:
            return None
        return {
            **qe,
            "farmgate_factor": spec["farmgate_factor"],
            "yield_kg_ha_ref": spec["yield_kg_ha_ref"],
            "quote_label": spec["quote_label"],
            "price_mode": "en_vivo" if snapshot.get("mode") == "en_vivo" else "guardado",
        }

    return None


def apply_market_prices_to_crops(
    crops: List[Dict[str, Any]],
    snapshot: Optional[Dict[str, Any]],
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Enriches crop catalog dicts with live Peruvian wholesale/chacra prices, dynamic gross income,
    net margin, B/C ratio, and explicit per-crop provenance/dates.
    """
    ordered_mkts = _ordered_sisap_markets(lat, lon)
    primary_mkt = ordered_mkts[0] if ordered_mkts else _SISAP_MARKETS[0]
    snap = snapshot or {}
    bcrp = snap.get("bcrp") or {}
    usd_pen = float(bcrp.get("usd_pen") or 3.41)
    usd_pen_date = str(bcrp.get("usd_pen_date") or "")
    ipc_food_pct = bcrp.get("ipc_food_pct")
    ipc_food_date = bcrp.get("ipc_food_date")

    enriched: List[Dict[str, Any]] = []
    live_count = 0
    mixed_count = 0
    inia_count = 0
    sources_seen: List[str] = []
    dates_seen: List[str] = []

    for orig in crops:
        crop = copy.deepcopy(orig)
        cid = str(crop["id"])
        crop["seed_cost_source"] = "Ref. campaña INIA / DRA Cajamarca"
        spec = _CROP_LIVE_SPECS.get(cid)
        resolved = (
            _resolve_crop_live_quote(cid, spec, snap, ordered_mkts, usd_pen)
            if spec and snap.get("mode") in ("en_vivo", "guardado")
            else None
        )

        if resolved:
            ws_price = float(resolved["wholesale_soles_kg"])
            factor = float(resolved["farmgate_factor"])
            chacra_price = round(ws_price * factor, 2)
            yield_kg = int(resolved["yield_kg_ha_ref"])
            coprod = int(resolved.get("coproduct_ref_soles_ha", 0) or 0)
            total_cost = int(crop.get("total_cost_soles_ha", 3200))
            gross_income = int(round(chacra_price * yield_kg + coprod))
            net_margin = int(gross_income - total_cost)
            bc_ratio = round(gross_income / max(total_cost, 1), 2)

            crop["wholesale_price_soles_kg"] = round(ws_price, 2)
            crop["chacra_price_soles_kg"] = chacra_price
            crop["farmgate_factor"] = round(factor, 2)
            crop["yield_kg_ha_ref"] = yield_kg
            crop["gross_income_soles_ha"] = gross_income
            crop["net_margin_soles_ha"] = net_margin
            crop["benefit_cost_ratio"] = bc_ratio
            crop["price_source"] = resolved["source"]
            crop["price_date"] = resolved["date"]
            crop["price_mode"] = resolved["price_mode"]
            crop["price_quote_label"] = resolved["quote_label"]

            if resolved["price_mode"] == "mixto_en_vivo":
                mixed_count += 1
            else:
                live_count += 1
            if resolved["source"] not in sources_seen:
                sources_seen.append(resolved["source"])
            if resolved["date"] and resolved["date"] not in dates_seen:
                dates_seen.append(resolved["date"])
        else:
            crop["price_source"] = "Ref. campaña INIA / DRA Cajamarca"
            crop["price_date"] = "Campaña 2025–2026"
            crop["price_mode"] = "referencia_inia"
            crop["price_quote_label"] = "Presupuesto regional por campaña (sin cotización diaria pública)"
            inia_count += 1

        enriched.append(crop)

    total_quoted = live_count + mixed_count
    latest_date = dates_seen[0] if dates_seen else None
    overall_mode = (
        str(snap.get("mode", "referencia_inia"))
        if total_quoted > 0
        else "referencia_inia"
    )
    if overall_mode == "en_vivo":
        status_tag = "en vivo"
    elif overall_mode == "guardado":
        status_tag = "guardado reciente"
    else:
        status_tag = "referencia"

    if total_quoted > 0:
        fx_note = f" · TC BCRP S/ {usd_pen:.3f}" if bcrp.get("usd_pen") else ""
        date_note = f" ({latest_date})" if latest_date else ""
        econ_label = (
            f"Precios oficiales {status_tag} en {total_quoted}/{len(enriched)} cultivos "
            f"(MIDAGRI SISAP {primary_mkt['name']}, Agromercado y EMMSA{date_note}{fx_note}) "
            f"ajustados a chacra × rinde INIA; {inia_count} forrajes/semillas en Ref. campaña INIA."
        )
    else:
        econ_label = (
            "Tablas referenciales MIDAGRI / INIA Cajamarca por campaña "
            "(sin respuesta de mercados en vivo en este momento)."
        )

    market_summary = {
        "mode": overall_mode,
        "primary_market_code": primary_mkt["code"],
        "primary_market_label": primary_mkt["name"],
        "usd_pen_rate": usd_pen if bcrp.get("usd_pen") else None,
        "usd_pen_date": usd_pen_date or None,
        "ipc_food_pct": ipc_food_pct,
        "ipc_food_date": ipc_food_date,
        "live_crops_count": live_count,
        "mixed_crops_count": mixed_count,
        "inia_fallback_crops_count": inia_count,
        "total_crops_count": len(enriched),
        "sources_used": sources_seen,
        "latest_price_date": latest_date,
        "fetched_at": snap.get("fetched_at"),
        "economic_reference_label": econ_label,
    }
    return enriched, market_summary

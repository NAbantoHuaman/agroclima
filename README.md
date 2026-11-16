# AgroConecta Cajamarca

Plataforma móvil Android y backend geoespacial para ayudar a agricultores y técnicos agrícolas de **Cajamarca, Perú** a planificar rotaciones de cultivos a 24 meses integrando observaciones de la Tierra de la NASA, datos satelitales de vegetación y clima local, precios referenciales MIDAGRI y un copiloto de voz bilingüe (**Español / Quechua**).

---

## Arquitectura del Proyecto

### `/backend` (Python · FastAPI · NumPy · Pandas · httpx)
- `main.py`: API REST documentada en `/docs` con los routers de parcelas y voz:
  - `GET /api/health`: Estado del servicio y catálogos cargados.
  - `GET /api/reference-data`: Parcelas de referencia, pisos altitudinales de Cajamarca, catálogo de cultivos y glosario agronómico.
  - `GET /api/integrations-status`: Estado de fuentes de datos e integraciones configuradas.
  - `GET /api/geocode`: Búsqueda geocodificada de sectores y distritos en Cajamarca.
  - `POST /api/analyze-parcel`: Análisis biofísico por parcela (NASA POWER, downscaling topográfico SRTM 30 m, Copernicus Sentinel-2 NDVI, ERA5/SoilGrids y clima actual Open-Meteo).
  - `POST /api/recommend`: Motor multicriterio **MCDA** con simulador de escenarios climáticos y estrategias comparativas a 24 meses.
  - `POST /api/voice-assistant` y `POST /api/voice-audio`: Asistente agronómico conversacional por texto y audio.
- `application/`, `domain/`, `infrastructure/`, `interfaces/`: Arquitectura por capas (servicios, motor agronómico/climático, clientes NASA/Copernicus/Open-Meteo/Gemini/MIDAGRI y rutas FastAPI).
- `data/`: Catálogos de cultivos y zonas de Cajamarca.
- `cache/`: Cachés locales pre-cargados (incluye grilla DEM SRTM 30 m y cachés JSON climáticos/de mercado).

### `/nasa-movil` (React Native · Expo · TypeScript)
- App móvil Android enfocada en uso en campo (`Español / Quechua`), con:
  - **Inicio (`FarmerHomeTab.tsx`):** Ubicación GPS/sector, clima local y pronóstico a 7 días, checklist de calibración de chacra y resumen hablado.
  - **Mapa (`InteractiveMapTab.tsx`):** Mapa interactivo Leaflet limpio con capas activables (humedad, salud vegetal NDVI, riesgo de heladas, altitud y sectores).
  - **Plan 24 meses (`RotationPlanTab.tsx`):** Comparador de estrategias, radar multicriterio, cronograma y explicación agronómica.
  - **Cultivos (`CropsCatalogTab.tsx`):** Catálogo de cultivos adaptados por piso altitudinal.
  - **Asistente de voz (`VoiceCopilotModal.tsx`):** Interacción por voz en lenguaje natural con detección automática de ubicación y parámetros de parcela.

---

## Ejecución Local

### 1. Backend (FastAPI)
1. Crea `backend/.env` tomando como plantilla `backend/.env.example`.
2. Inicia el servidor:
```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```
Documentación interactiva Swagger en `http://127.0.0.1:8000/docs`.

### 2. App Móvil (Expo / Android)
```powershell
cd nasa-movil
npm.cmd start
```

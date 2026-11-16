# AgroConecta Cajamarca — Android Mobile App
**2026 NASA Space Apps Challenge:** [*Field Shift: Adapting Farms with NASA Data*](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/)

**AgroConecta** is a **native Android mobile application** (backed by a cloud geospatial FastAPI server) built to help smallholder farmers and agricultural technicians in **Cajamarca, Peru** plan **24-month crop rotations**. It fuses NASA and partner Earth observations with local soil attributes, an Andean/valley catalog of 24 crops, farmer-defined priorities, and a bilingual (**Spanish & Quechua**) voice/AI copilot.

---

## Download & Test the Android App (`.apk`)

> **Important Note for Judges:** This project is a **standalone Android mobile app (`.apk`)**, not a web portal. It is pre-configured to connect automatically to our live cloud backend (`https://agroclima-fx55.onrender.com`), so no local server setup is required to evaluate it.

- **Download AgroConecta Android APK (Google Drive):**  
  👉 **[Download AgroConecta (.apk)](https://drive.google.com/file/d/1KQt2DYrc6DtFzzlZJWGhHbMwHmoXUW15/view?usp=sharing)**
- **Live Cloud API Documentation (Swagger / Render):** https://agroclima-fx55.onrender.com/docs

---

## Android Installation & Evaluation Guide

### 1. Download and Install the `.apk`
1. Open the Google Drive download link above on an Android phone:  
   `https://drive.google.com/file/d/1KQt2DYrc6DtFzzlZJWGhHbMwHmoXUW15/view?usp=sharing`
2. Download the `.apk` file and tap it to launch the Android package installer.
3. If Android asks permission to install apps outside Google Play (*"For your security, your phone isn't allowed to install unknown apps from this source"*), tap **Settings** and enable **Allow from this source**.

### 2. Google Play Protect Warning (Expected False Positive for Direct `.apk` Sideloading)
Because this `.apk` is distributed directly for hackathon evaluation rather than through the Google Play Store, **Google Play Protect** automatically displays a standard precautionary warning (e.g., *"Unrecognized app"* or *"Unsafe app blocked"*).

- **This is a normal false positive for sideloaded hackathon builds:** the APK is built and cryptographically signed via **Expo EAS Build** (`com.agrocajamarca.nasamovil`), contains zero malicious code, and only requests standard **GPS Location** (`ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION`) and **Microphone** (`RECORD_AUDIO`) permissions for parcel geolocation and voice queries.
- **How to proceed with installation:**
  1. On the **Google Play Protect** prompt, do **not** tap *OK / Got it*.
  2. Tap **More details** *(or the expand arrow)*.
  3. Tap **Install anyway** (if prompted to scan or confirm again, select **Install anyway**).

### 3. Quick Tip Before Testing (Free-Tier Cloud Cold Start)
Our backend runs on Render's free tier (`https://agroclima-fx55.onrender.com`), which spins down after **15 minutes of inactivity**.
- Before opening the app for your evaluation, you can visit https://agroclima-fx55.onrender.com/api/health in a browser **30–50 seconds beforehand** to wake up the server immediately, or simply wait a few seconds on the app's startup screen while it connects automatically.

### 4. 2-Minute Judge Walkthrough *(The UI is in Spanish & Quechua for local farmers)*
1. **Home (`Inicio` — Climate, GPS & 6-Step Calibration):**
   - Grant location permission and tap **`Usar mi GPS actual`** (*Use my GPS*), or tap **`Buscar mi sector`** (*Search sector*) to test real districts in Cajamarca (*Baños del Inca*, *La Encañada*, *Namora*, *Celendín*).
   - View elevation-adjusted current weather, annual rainfall, frost alert, and the **7-day forecast** (`Próximos 7 días`). Toggle **Spanish (`ES`) / Quechua (`QU`)** or tap the top-right **speaker icon** for an audio summary.
2. **AI Voice Copilot (Center green microphone button):**
   - Tap the center mic button to speak, type, or tap a sample farmer prompt (e.g., *"Estoy en Baños del Inca, solo lluvia, quiero ver qué rotar"* — *"I'm in Baños del Inca, rain-fed only, what should I rotate?"*).
   - Answer the progressive follow-up chips and tap the bottom green button **`Aplicar este plan y ver mi rotación`** (*Apply this plan & view my rotation*).
3. **Interactive Satellite Map (`Mapa`):**
   - Opens on a clean satellite basemap (`Vista Satelital Limpia`) so you can pinpoint or draw parcel boundaries.
   - Tap any of the 4 cards — **`Humedad Suelo`** (Soil Moisture), **`Salud Vegetal`** (Plant Health), **`Heladas y Plagas`** (Frost & Pests), **`Calidad de Suelo`** (Soil Quality) — to toggle live **NASA GIBS** satellite overlays (`SMAP`, `MODIS NDVI`, `GPM IMERG`) and topographic relief.
4. **24-Month Rotation Plan (`Plan` — 3 Strategies & Explainability):**
   - Compare **3 24-month rotation strategies** side by side (including the current baseline), inspect the 4-season timeline, water savings, erosion reduction, nitrogen balance, and the **`Dónde manda tu ojo y experiencia de agricultor`** (*Human-in-the-Loop: Where farmer judgment leads*) section.
5. **Crop Catalog (`Cultivos`):**
   - Browse **24 local Andean & valley crops** ranked by suitability for your parcel's altitude, climate, and regional market references.

---

## How AgroConecta Addresses *Field Shift: Adapting Farms with NASA Data*

### 1. Understanding Conditions & Multi-Scale Data Harmonization
- **Topographic Downscaling (`biophysical_harmonizer.py` + `terrain_dem.py`):** Harmonizes 20-year daily **NASA POWER (2006–2025)** meteorology with real **30 m NASA SRTM GL1** elevation using moist adiabatic lapse-rate scaling (`-0.0065 °C/m`), valley cold-air inversion, orographic rainfall scaling, and intra-parcel slope, aspect, and vertex elevation spread.
- **Satellite + Ground Data Fusion (`soil_terrain_client.py`):** Combines surface moisture (**ERA5-Land + NASA POWER `GWETTOP`/`GWETROOT`**), evapotranspiration (**ERA5-Land FAO `ET0` + Makkink**), 10 m cloud-masked vegetation vigor (**Copernicus Sentinel-2 L2A**), and soil properties (**ISRIC SoilGrids v2.0**), calibrated with direct farmer observations (soil texture, drainage/waterlogging, early local frost, irrigation method, equipment access, and seed inventory).
- **Accessible Science Translation:** Translates technical indicators (*NDVI*, *evapotranspiration `ET0`*, *moisture anomalies*, *water balance*, and *bare-soil windows `< 0.25`*) into plain-language guidance in Spanish and Quechua.

### 2. Comparing 3 Rotation Strategies & Explainable Decisions (*Human-in-the-Loop*)
- **24-Month Multi-Strategy Engine (`domain/rotation_engine.py` + `domain/scoring.py`):**
  1. **Regenerative / Balanced Strategy:** Alternates nitrogen-fixing Andean legumes (*Tarwi/Chocho*, *Fava Bean*, *Peas*, *Alfalfa*), staple/commercial crops, and protective covers to break pest cycles (*Andean potato weevil*, *late blight*), eliminate bare-soil months, and rebuild organic matter.
  2. **Climate-Resilient Strategy (Drought & Frost):** Prioritizes cold- and drought-hardy crops plus dry-season soil cover for extreme-weather resilience.
  3. **Baseline (Current Practice):** Quantifies the vulnerability (`0–100`), negative nitrogen balance, and erosion exposure of continuing monoculture or leaving soil bare.
- **Farmer-Weighted MCDA:** Dynamically scores rotations across **5 farmer priorities** (water conservation, soil fertility, erosion control, pest-cycle disruption, commercial/forage income), **7 irrigation systems** (from strict rain-fed and traditional *qochas* to drip irrigation), equipment access, and available seeds.
- **Explainability & Farmer Agency:** Every strategy surfaces why it was recommended, quantified benefits, supporting NASA evidence, and explicit **human-in-the-loop gaps** highlighting where local farmer inspection and agronomist expertise must validate satellite insights.

### 3. Geospatial Mapping & Climate Scenario Exploration
- Clean interactive Leaflet map with toggleable **NASA GIBS** satellite layers (**MODIS NDVI**, **SMAP Surface Soil Moisture**, **GPM IMERG Precipitation**), free-hand parcel polygon drawing, and exploration mode to test rotations across any location in Cajamarca.
- Evaluates 20-year historical climate trends (2006–2025) with 2-year near-term sensitivity (**2026–2027**) and interactive rainfall, temperature, and frost scenarios.

### 4. Farmer-Centered Design
- Bilingual **Spanish / Quechua** interface, text-to-speech audio readouts (`expo-speech`), and a conversational **AI Copilot (Gemini)** that captures parcel details progressively via voice or quick chips for users with limited geospatial background.

---

## NASA & Partner Datasets Used

- **NASA POWER** (`https://power.larc.nasa.gov/`): 20-year daily agroclimatology (`T2M`, `T2M_MIN`, `T2M_MAX`, `PRECTOTCORR`, `ALLSKY_SFC_SW_DWN`, `RH2M`, `GWETTOP`, `GWETROOT`).
- **NASA SRTM GL1 (30 m)** (`https://www.earthdata.nasa.gov/data/instruments/srtm`): 30 m elevation, slope, aspect, and intra-parcel relief (cached Cajamarca regional grid + on-demand OpenTopography micro-tiles).
- **NASA SMAP via GIBS** (`https://www.earthdata.nasa.gov/data/platforms/space-based-platforms/smap`): Live map overlay tiles (`SMAP_L4_Analyzed_Surface_Soil_Moisture`).
- **NASA GPM IMERG via GIBS** (`https://gpm.nasa.gov/data`): Live map overlay tiles (`IMERG_Precipitation_Rate`).
- **NASA MODIS via GIBS** (`https://lpdaac.usgs.gov/products/`): Live map overlay tiles (`MODIS_Terra_NDVI_8Day`).
- **Copernicus Sentinel-2 L2A (ESA)** (`https://dataspace.copernicus.eu/`): Cloud-masked 10 m monthly NDVI statistics via Copernicus Data Space Statistical API.
- **ERA5-Land (ECMWF Reanalysis)** (`https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview`): Volumetric soil moisture (`0–7 cm`) and FAO `ET0` via Open-Meteo Archive.
- **Additional Open Data Sources:** **ISRIC SoilGrids v2.0** (0–30 cm soil properties), **Open-Meteo** (live 7-day forecast & fallback Copernicus DEM GLO-90), and Peruvian **MIDAGRI / SIEA** regional crop price references.

---

## Architecture & Local Development

### `/nasa-movil` (Android Mobile App · React Native · Expo · TypeScript)
- `App.tsx`: Bottom-dock navigation (`Inicio`, `Mapa`, central voice trigger, `Plan`, `Cultivos`) and optional custom server URL modal.
- `src/components/FarmerHomeTab.tsx`: Weather/GPS header, 7-day forecast, spoken summary, and 6-point calibration checklist.
- `src/components/InteractiveMapTab.tsx` & `src/presentation/map/`: Clean Leaflet map, NASA GIBS overlays, parcel boundary drawing, and farmer-friendly satellite metrics.
- `src/components/VoiceCopilotModal.tsx`: Multimodal voice/text Gemini assistant with embedded map picker.
- `src/components/RotationPlanTab.tsx`: 3-strategy 24-month comparator, timeline, radar scores, pest guide, and human-in-the-loop gaps.
- `src/components/CropsCatalogTab.tsx`: 24-crop catalog filtered by elevation and climate compatibility.

### `/backend` (REST API · Python · FastAPI · NumPy · Pandas · httpx)
- `main.py`: FastAPI entrypoint (`/docs`) exposing `GET /api/health`, `GET /api/reference-data`, `GET /api/integrations-status`, `GET /api/geocode`, `POST /api/analyze-parcel`, `POST /api/recommend`, `POST /api/voice-assistant`, and `POST /api/voice-audio`.
- `application/`, `domain/`, `infrastructure/`, `interfaces/`, `data/`, `cache/`: Layered architecture + pre-warmed climate/DEM/price caches (including 30 m SRTM Cajamarca elevation grid).

### Running Locally (Optional)
```powershell
# 1. FastAPI Backend (copy backend/.env.example to backend/.env first)
cd backend
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000

# 2. Expo Mobile App
cd nasa-movil
npm.cmd install
npm.cmd start
```

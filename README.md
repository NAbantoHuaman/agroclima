# AgroConecta Cajamarca — App Móvil Android

**Aplicación móvil Android** y backend geoespacial para ayudar a agricultores y técnicos agrícolas de **Cajamarca, Perú** a planificar rotaciones de cultivos a 24 meses integrando observaciones de la Tierra de la NASA, datos satelitales de vegetación y clima local, precios referenciales MIDAGRI y un copiloto de voz bilingüe (**Español / Quechua**).

---

## Descargar e Instalar la App Android (`.apk`)

> **Importante para evaluadores / jurados:** Este proyecto es una **aplicación móvil nativa Android (`.apk`)**, no un portal web. Ya se encuentra conectada automáticamente al servidor backend en la nube (`https://agroclima-fx55.onrender.com`), por lo que puedes instalarla y probarla directamente en tu teléfono Android sin levantar ningún servidor local.

- **Descargar APK de AgroConecta (Google Drive):**  
  👉 **[Descargar AgroConecta (.apk)](https://drive.google.com/file/d/1KQt2DYrc6DtFzzlZJWGhHbMwHmoXUW15/view?usp=drive_link)**
- **API Backend en vivo (Render):** https://agroclima-fx55.onrender.com/docs

---

## Manual de Instalación y Prueba en Android

### 1. Descarga e instalación del `.apk`
1. Abre el enlace de descarga anterior desde tu teléfono Android:  
   `https://drive.google.com/file/d/1KQt2DYrc6DtFzzlZJWGhHbMwHmoXUW15/view?usp=drive_link`
2. Descarga el archivo `.apk` en tu dispositivo y tócalo para abrir el instalador de Android.
3. Si Android te pide habilitar instalaciones desde tu navegador o gestor de archivos (*“Por seguridad, tu teléfono no tiene permitido instalar apps desconocidas de esta fuente”*), pulsa **Configuración** y activa **Permitir desde esta fuente**.

### 2. Aviso de Google Play Protect (falso positivo normal en `.apk` directos)
Al instalar una aplicación Android directamente fuera de Google Play Store (*sideloading*), **Google Play Protect** muestra de forma automática una alerta preventiva como *“App no reconocida”* o *“El desarrollador no está verificado / Podría ser dañina”*.

- **Es un falso positivo esperado:** la app está compilada y firmada con keystore oficial mediante **Expo EAS Build** (`com.agrocajamarca.nasamovil`), no contiene software malicioso y únicamente solicita permisos estándar de **Ubicación GPS** (`ACCESS_FINE_LOCATION` / `ACCESS_COARSE_LOCATION`) y **Micrófono** (`RECORD_AUDIO`) para ubicar la chacra y escuchar consultas de voz.
- **Cómo continuar la instalación:**
  1. Cuando aparezca la ventana de **Google Play Protect**, **no** presiones *Cancelar / Entendido*.
  2. Toca en **Más detalles** *(o “Ver más” / flecha desplegable)*.
  3. Presiona **Instalar de todas formas** (y si solicita confirmar o enviar a analizar, vuelve a elegir **Instalar de todas formas**).

### 3. Nota rápida antes de probar (servidor gratuito en la nube)
El backend desplegado en el plan gratuito de Render (`https://agroclima-fx55.onrender.com`) entra en reposo tras **15 minutos de inactividad**. Si es la primera consulta en varios minutos:
- Puedes abrir primero https://agroclima-fx55.onrender.com/api/health en tu navegador **30–50 segundos antes** para despertarlo, **o** esperar unos segundos en la pantalla inicial de la app mientras se conecta automáticamente.

### 4. Guía rápida para probar AgroConecta paso a paso
1. **Inicio (Clima y Ubicación):**
   - Otorga el permiso de ubicación si estás en campo y pulsa **Usar mi GPS actual**, o toca **Buscar mi sector** para elegir un distrito/caserío de Cajamarca (por ejemplo *Baños del Inca*, *La Encañada* o *Namora*).
   - Revisa la temperatura actual, lluvia anual, alerta de heladas y pronóstico de **Próximos 7 días**; puedes alternar el idioma entre **Español (`ES`)** y **Quechua (`QU`)** o escuchar el resumen hablado arriba a la derecha.
2. **Asistente de Voz / IA (botón central con micrófono):**
   - Toca el botón verde del micrófono en la barra inferior. Puedes **hablar**, **escribir** o elegir una consulta rápida (por ejemplo: *"Estoy en Baños del Inca, solo lluvia, quiero ver qué rotar"*).
   - Responde las preguntas guiadas tocando las opciones rápidas o hablando; al finalizar pulsa **«Aplicar este plan y ver mi rotación»**.
3. **Mapa Satelital:**
   - Inicia en **Mapa Base limpio** para ubicar o dibujar con precisión los límites de tu parcela.
   - Toca cualquiera de las 4 tarjetas (**Humedad Suelo**, **Salud Vegetal**, **Heladas y Plagas**, **Calidad de Suelo**) para superponer en el mapa las capas satelitales reales de **NASA GIBS** (`SMAP`, `MODIS NDVI`, `GPM IMERG`) y **relieve**.
4. **Plan 24 meses:**
   - Compara las **3 estrategias** (*Regenerativa / Equilibrada*, *Resiliente ante sequía/helada* y *Línea base actual*), cronograma de 4 campañas (2 años), ahorro hídrico, control de erosión, rentabilidad estimada y resumen hablado.
5. **Cultivos:**
   - Explora los **24 cultivos locales y andinos** filtrados por compatibilidad con la altitud y clima de tu parcela, con fichas técnicas, tolerancia a heladas/sequía y precios referenciales.

---

## Datos Satelitales y Fuentes Abiertas Utilizadas

- **NASA POWER** (`https://power.larc.nasa.gov/`): Series climáticas diarias de 20 años (2006–2025: temperatura media/mínima/máxima, precipitación diaria `PRECTOTCORR`, radiación solar, humedad relativa y humedad del suelo `GWETTOP`/`GWETROOT`) con ajuste topográfico a la altura de la parcela.
- **NASA SRTM GL1 (30 m)** (`https://www.earthdata.nasa.gov/data/instruments/srtm`): Modelo digital de elevación a 30 m (grilla cacheada de Cajamarca + descarga bajo demanda por OpenTopography) para calcular altitud, pendiente, orientación de ladera y desnivel interno.
- **NASA SMAP vía GIBS** (`https://www.earthdata.nasa.gov/data/platforms/space-based-platforms/smap`): Capa satelital visual de humedad superficial del suelo (`SMAP_L4_Analyzed_Surface_Soil_Moisture`).
- **NASA GPM IMERG vía GIBS** (`https://gpm.nasa.gov/data`): Capa satelital visual de tasa de precipitación (`IMERG_Precipitation_Rate`).
- **NASA MODIS vía GIBS** (`https://lpdaac.usgs.gov/products/`): Capa satelital visual de verdor vegetal (`MODIS_Terra_NDVI_8Day`).
- **Copernicus Sentinel-2 L2A (ESA)** (`https://dataspace.copernicus.eu/`): Estadísticas mensuales reales de NDVI a 10 m con máscara de nubes vía Copernicus Data Space.
- **ERA5-Land (ECMWF Reanalysis)** (`https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview`): Reanálisis histórico de humedad de suelo (`0–7 cm`) y evapotranspiración de referencia `ET0` (vía Open-Meteo Archive).
- **Fuentes complementarias:** **ISRIC SoilGrids v2.0** (propiedades físicas/químicas de suelo 0–30 cm), **Open-Meteo** (pronóstico 7 días en tiempo real y Copernicus DEM GLO-90 auxiliar) y referencias **MIDAGRI / SIEA** (precios referenciales en Cajamarca).

---

## Arquitectura del Proyecto

### `/nasa-movil` (App Móvil Android · React Native · Expo · TypeScript)
- `App.tsx`: Shell de navegación móvil (`Inicio`, `Mapa`, botón central de voz, `Plan`, `Cultivos`) y selector opcional de servidor backend.
- `src/components/FarmerHomeTab.tsx`: Tarjeta de clima/GPS, pronóstico a 7 días, lectura de voz y guía interactiva de calibración de 6 puntos.
- `src/components/InteractiveMapTab.tsx` y `src/presentation/map/`: Mapa Leaflet interactivo limpio con capas activables NASA GIBS, dibujo libre de chacra y diagnóstico satelital en lenguaje claro.
- `src/components/VoiceCopilotModal.tsx`: Asistente conversacional de voz/texto conectado al backend + Gemini y editor integrado de ubicación en mapa.
- `src/components/RotationPlanTab.tsx`: Comparador de 3 estrategias a 24 meses, cronograma por campaña, gráfico radar y explicación agronómica.
- `src/components/CropsCatalogTab.tsx`: Catálogo de 24 cultivos adaptados por piso altitudinal.

### `/backend` (API REST · Python · FastAPI · NumPy · Pandas · httpx)
- `main.py`: API REST documentada en `/docs` con los routers de parcelas y voz:
  - `GET /api/health`: Estado del servicio y catálogos cargados.
  - `GET /api/reference-data`: Parcelas de referencia, pisos altitudinales de Cajamarca, catálogo de cultivos y glosario agronómico.
  - `GET /api/integrations-status`: Estado de fuentes de datos e integraciones configuradas.
  - `GET /api/geocode`: Búsqueda geocodificada de sectores y distritos en Cajamarca.
  - `POST /api/analyze-parcel`: Análisis biofísico por parcela (NASA POWER, SRTM 30 m, Sentinel-2 NDVI, ERA5/SoilGrids y clima actual).
  - `POST /api/recommend`: Motor multicriterio **MCDA** con simulador climático y estrategias comparativas a 24 meses.
  - `POST /api/voice-assistant` y `POST /api/voice-audio`: Asistente agronómico conversacional por texto y audio.
- `application/`, `domain/`, `infrastructure/`, `interfaces/`: Arquitectura por capas (servicios, motor agronómico/climático, clientes satelitales/Gemini/MIDAGRI y rutas FastAPI).
- `data/`: Catálogos de cultivos y zonas de Cajamarca.
- `cache/`: Cachés locales pre-cargados (incluye grilla DEM SRTM 30 m y cachés JSON climáticos/de mercado).

---

## Ejecución Local (Desarrollo)

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
npm.cmd install
npm.cmd start
```

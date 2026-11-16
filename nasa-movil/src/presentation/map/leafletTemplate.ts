export function buildInteractiveMapHtml(params: {
  initLat: number;
  initLon: number;
  initPoly: [number, number][];
  initStroke: string;
  initLayer?: "clean" | "ndvi" | "smap" | "frost" | "erosion";
}): string {
  const { initLat, initLon, initPoly, initStroke, initLayer = "clean" } = params;
  const initPolyJson = JSON.stringify(initPoly);
  return `<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body, #map {
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    background: #182F1B;
    touch-action: none;
    -ms-touch-action: none;
    overscroll-behavior: none;
  }
  .leaflet-control-attribution { display: none !important; }
</style>
</head>
<body>
<div id="map"></div>
<script>
  const map = L.map('map', {
    zoomControl: false,
    touchZoom: true,
    dragging: true,
    doubleClickZoom: true,
    boxZoom: false,
    bounceAtZoomLimits: false,
    tap: false
  }).setView([${initLat}, ${initLon}], 15);
  window.agroMap = map;
  window._lastTarget = [${initLat}, ${initLon}];
  function notifyMapInteract(active) {
    if (window.ReactNativeWebView && window.ReactNativeWebView.postMessage) {
      window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'interact', active: Boolean(active) }));
    }
  }
  const mapEl = document.getElementById('map');
  if (mapEl) {
    mapEl.addEventListener('touchstart', function() { notifyMapInteract(true); }, { passive: true });
    mapEl.addEventListener('touchend', function(ev) {
      if (!ev.touches || ev.touches.length === 0) notifyMapInteract(false);
    }, { passive: true });
    mapEl.addEventListener('touchcancel', function() { notifyMapInteract(false); }, { passive: true });
  }
  map.on('movestart zoomstart', function() { notifyMapInteract(true); });
  map.on('moveend zoomend', function() { notifyMapInteract(false); });
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 18
  }).addTo(map);
  const OVERLAY_TILES = {
    ndvi: {
      url: 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_NDVI_8Day/default/default/GoogleMapsCompatible_Level9/{z}/{y}/{x}.png',
      maxNativeZoom: 9,
      opacity: 0.62
    },
    smap: {
      url: 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/SMAP_L4_Analyzed_Surface_Soil_Moisture/default/default/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png',
      maxNativeZoom: 6,
      opacity: 0.62
    },
    frost: {
      url: 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/IMERG_Precipitation_Rate/default/default/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png',
      maxNativeZoom: 6,
      opacity: 0.60
    },
    erosion: {
      url: 'https://tile.opentopomap.org/{z}/{x}/{y}.png',
      maxNativeZoom: 17,
      opacity: 0.54
    }
  };
  let activeOverlayLayer = null;
  let currentOverlayKey = 'clean';
  function setSatelliteOverlay(layerKey) {
    const normalized = layerKey || 'clean';
    if (currentOverlayKey === normalized) return;
    const cfg = OVERLAY_TILES[normalized];
    if (!cfg || normalized === 'clean') {
      currentOverlayKey = 'clean';
      if (activeOverlayLayer) {
        map.removeLayer(activeOverlayLayer);
        activeOverlayLayer = null;
      }
      return;
    }
    currentOverlayKey = normalized;
    if (activeOverlayLayer) {
      map.removeLayer(activeOverlayLayer);
    }
    activeOverlayLayer = L.tileLayer(cfg.url, {
      maxZoom: 18,
      maxNativeZoom: cfg.maxNativeZoom,
      opacity: cfg.opacity
    }).addTo(map);
    if (activeOverlayLayer && activeOverlayLayer.setZIndex) {
      activeOverlayLayer.setZIndex(2);
    }
  }
  setSatelliteOverlay('${initLayer}');
  const sensorCircle = L.circle([${initLat}, ${initLon}], {
    radius: 135,
    color: '${initStroke}',
    weight: 2,
    dashArray: '5,5',
    fillColor: '${initStroke}',
    fillOpacity: ${initPoly.length >= 3 ? 0 : (initLayer === "clean" ? 0.08 : 0.22)},
    opacity: ${initPoly.length >= 3 ? 0 : 0.85}
  }).addTo(map);
  const marker = L.circleMarker([${initLat}, ${initLon}], {
    radius: 7,
    color: '#FFFFFF',
    weight: 2.5,
    fillColor: '#A3E635',
    fillOpacity: 0.95
  }).addTo(map);
  const poly = L.polygon(${initPolyJson.length > 2 && initPoly.length >= 3 ? initPolyJson : "[]"}, {
    color: '${initStroke}',
    weight: 3,
    fillColor: '${initStroke}',
    fillOpacity: ${initLayer === "clean" ? 0.1 : 0.36}
  }).addTo(map);
  const drawLine = L.polyline([], {
    color: '#FFFFFF',
    weight: 2.5,
    dashArray: '6,5'
  }).addTo(map);
  const vertexLayer = L.layerGroup().addTo(map);

  function renderVertices(pts, showAll) {
    vertexLayer.clearLayers();
    if (!Array.isArray(pts) || pts.length === 0) return;
    if (!showAll && pts.length < 3) return;
    pts.forEach(function(pt, idx) {
      L.circleMarker(pt, {
        radius: idx === 0 ? 7 : 5.5,
        color: '#142616',
        weight: 2.2,
        fillColor: idx === 0 ? '#A3E635' : '#FFFFFF',
        fillOpacity: 1
      }).addTo(vertexLayer);
    });
  }
  renderVertices(${initPolyJson}, false);

  window.updateMapState = function(next) {
    if (!next) return;
    marker.setLatLng([next.lat, next.lon]);
    marker.setStyle({
      fillOpacity: next.drawMode ? 0.35 : 0.95,
      opacity: next.drawMode ? 0.45 : 1
    });
    sensorCircle.setLatLng([next.lat, next.lon]);
    const pts = Array.isArray(next.poly) ? next.poly : [];
    const hasClosedPoly = pts.length >= 3;
    poly.setLatLngs(hasClosedPoly ? pts : []);
    drawLine.setLatLngs(next.drawMode && pts.length >= 2 ? pts : []);
    renderVertices(pts, Boolean(next.drawMode));
    if (next.layer) {
      setSatelliteOverlay(next.layer);
    }
    if (next.stroke || next.layer) {
      const targetLayer = next.layer || currentOverlayKey || 'clean';
      const isCleanLayer = targetLayer === 'clean';
      const polyStyle = { fillOpacity: isCleanLayer ? 0.1 : 0.36 };
      const circleStyle = {
        opacity: hasClosedPoly || next.drawMode ? 0 : 0.85,
        fillOpacity: hasClosedPoly || next.drawMode ? 0 : (isCleanLayer ? 0.08 : 0.22)
      };
      if (next.stroke) {
        polyStyle.color = next.stroke;
        polyStyle.fillColor = next.stroke;
        circleStyle.color = next.stroke;
        circleStyle.fillColor = next.stroke;
      }
      poly.setStyle(polyStyle);
      sensorCircle.setStyle(circleStyle);
    }
    const prev = window._lastTarget || [next.lat, next.lon];
    const moved = Math.abs(next.lat - prev[0]) > 1e-6 || Math.abs(next.lon - prev[1]) > 1e-6;
    if (moved && !next.drawMode) {
      window._lastTarget = [next.lat, next.lon];
      map.panTo([next.lat, next.lon], { animate: true });
    }
  };
  map.on('click', function(e) {
    window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'tap', lat: e.latlng.lat, lon: e.latlng.lng }));
  });
</script>
</body>
</html>`;
}

export function buildVoicePickerHtml(params: {
  initLat: number;
  initLon: number;
  markerLat: number;
  markerLon: number;
  initPoly: [number, number][];
}): string {
  const { initLat, initLon, markerLat, markerLon } = params;
  const initPoly = JSON.stringify(params.initPoly);
  return `<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body, #map { margin: 0; padding: 0; width: 100%; height: 100%; background: #142817; }
  .leaflet-control-attribution { display: none !important; }
</style>
</head>
<body>
<div id="map"></div>
<script>
  const map = L.map('map', { zoomControl: true }).setView([${initLat}, ${initLon}], 15);
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 18
  }).addTo(map);

  let pinMarker = L.circleMarker([${markerLat}, ${markerLon}], {
    radius: 9,
    color: '#FFFFFF',
    weight: 3,
    fillColor: '#74C344',
    fillOpacity: 1
  }).addTo(map);

  let polyLayer = L.polygon(${initPoly}, {
    color: '#BEF264',
    weight: 3,
    fillColor: '#74C344',
    fillOpacity: 0.36
  }).addTo(map);

  let drawLine = L.polyline([], {
    color: '#FFFFFF',
    weight: 2.5,
    dashArray: '6,5'
  }).addTo(map);

  let vertexLayer = L.layerGroup().addTo(map);
  function redrawVertices(poly) {
    vertexLayer.clearLayers();
    if (!Array.isArray(poly)) return;
    poly.forEach(function(pt, idx) {
      L.circleMarker(pt, {
        radius: idx === 0 ? 7 : 5.5,
        color: '#172C1A',
        weight: 2.2,
        fillColor: idx === 0 ? '#A3E635' : '#FFFFFF',
        fillOpacity: 1
      }).addTo(vertexLayer);
    });
  }
  redrawVertices(${initPoly});

  window.updateOverlay = function(lat, lon, poly, recenter) {
    pinMarker.setLatLng([lat, lon]);
    const pts = Array.isArray(poly) ? poly : [];
    polyLayer.setLatLngs(pts.length >= 3 ? pts : []);
    drawLine.setLatLngs(pts.length >= 2 ? pts : []);
    redrawVertices(pts);
    if (recenter) {
      map.setView([lat, lon], Math.max(map.getZoom(), 15), { animate: true });
    }
  };

  map.on('click', function(e) {
    window.ReactNativeWebView.postMessage(JSON.stringify({
      type: 'tap',
      lat: e.latlng.lat,
      lon: e.latlng.lng
    }));
  });
</script>
</body>
</html>`;
}

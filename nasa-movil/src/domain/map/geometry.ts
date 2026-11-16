export function buildDefault1HaSquare(
  lat: number,
  lon: number
): [number, number][] {
  const d = 0.00045;
  return [
    [Number((lat - d).toFixed(6)), Number((lon - d).toFixed(6))],
    [Number((lat - d).toFixed(6)), Number((lon + d).toFixed(6))],
    [Number((lat + d).toFixed(6)), Number((lon + d).toFixed(6))],
    [Number((lat + d).toFixed(6)), Number((lon - d).toFixed(6))],
  ];
}

export function computePolygonCentroid(poly: [number, number][]): {
  lat: number;
  lon: number;
} {
  const avgLat = poly.reduce((sum, p) => sum + p[0], 0) / poly.length;
  const avgLon = poly.reduce((sum, p) => sum + p[1], 0) / poly.length;
  return {
    lat: Number(avgLat.toFixed(5)),
    lon: Number(avgLon.toFixed(5)),
  };
}

export function estimatePolygonAreaHa(
  poly: [number, number][] | null | undefined,
  fallbackAreaHa?: number | null
): number | null {
  if (poly && poly.length >= 3) {
    let area = 0;
    for (let i = 0; i < poly.length; i++) {
      const [y1, x1] = poly[i];
      const [y2, x2] = poly[(i + 1) % poly.length];
      area += x1 * y2 - x2 * y1;
    }
    const degSq = Math.abs(area) / 2;
    const kmSq = degSq * 111.32 * 110.57;
    return Math.max(0.2, Math.min(600, Number((kmSq * 100).toFixed(1))));
  }
  return fallbackAreaHa ?? null;
}

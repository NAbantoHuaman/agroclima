import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { WebView } from "react-native-webview";
import {
  Check,
  ChevronDown,
  Compass,
  MapPin,
  Minus,
  Navigation,
  PenTool,
  Plus,
  RotateCcw,
  Search,
  Trash2,
} from "lucide-react-native";
import { requestRecommendations } from "../services/apiClient";
import {
  SATELLITE_LAYERS,
  WATER_OPTIONS_FALLBACK,
  type SatelliteLayerId,
} from "../domain/agronomy/constants";
import { estimatePolygonAreaHa } from "../domain/map/geometry";
import { translateCropText, type MobileUiDictionary } from "../i18n/translations";
import { buildInteractiveMapHtml } from "../presentation/map/leafletTemplate";
import { MapZonePickerModal } from "../presentation/map/MapZonePickerModal";
import { ParcelParametersModal } from "../presentation/map/ParcelParametersModal";
import { SatelliteMetricsGrid } from "../presentation/map/SatelliteMetricsGrid";
import { styles } from "../presentation/map/InteractiveMapTab.styles";
import { COLORS } from "../theme/tokens";
import type {
  AppLanguage,
  BeaconParcel,
  CurrentCropId,
  EquipmentAccess,
  FarmerSoilNotes,
  MarketPreference,
  PriorityWeights,
  RecommendResponse,
  ReferenceDataResponse,
  VoiceConfirmedSlots,
  WaterAvailability,
} from "../types";

const WebViewComponent = WebView as unknown as React.ComponentType<{
  ref?: React.Ref<unknown>;
  originWhitelist?: string[];
  source: { html: string };
  style?: object;
  javaScriptEnabled?: boolean;
  domStorageEnabled?: boolean;
  nestedScrollEnabled?: boolean;
  overScrollMode?: "always" | "content" | "never";
  onLoadEnd?: () => void;
  onMessage?: (ev: { nativeEvent: { data: string } }) => void;
}>;

interface InteractiveMapTabProps {
  t: MobileUiDictionary;
  lang: AppLanguage;
  activePoint: { lat: number; lon: number };
  customPolygon: [number, number][] | null;
  currentCrop: CurrentCropId;
  waterAvailability: WaterAvailability;
  priorities: PriorityWeights;
  farmerSoil: FarmerSoilNotes;
  equipmentAccess?: EquipmentAccess;
  marketPreference?: MarketPreference;
  onChangeEquipment?: (eq: EquipmentAccess) => void;
  farmerConfirmedInputs?: boolean;
  isPlanReady?: boolean;
  voiceSlots?: VoiceConfirmedSlots;
  completedChecklistCount?: number;
  onSelectChecklistOption?: (
    slotKey: "water" | "crop" | "soil" | "climate" | "goal",
    optionId: string,
    label: string
  ) => void;
  onGoToPlan?: () => void;
  onConfirmParcelPolygon?: (returnToHome?: boolean) => void;
  onSimulateExplorerPlan?: (simRes: RecommendResponse) => void;
  onSaveExploredAsMyChacra?: (
    lat: number,
    lon: number,
    label: string,
    simRes?: RecommendResponse | null
  ) => void;
  result: RecommendResponse | null;
  referenceData: ReferenceDataResponse | null;
  isAnalyzing: boolean;
  isLocatingGps?: boolean;
  onSelectPoint: (lat: number, lon: number, label?: string | null) => void;
  onSelectBeacon: (beacon: BeaconParcel) => void;
  onSetPolygon: (coords: [number, number][] | null) => void;
  onChangeCrop: (crop: CurrentCropId) => void;
  onChangeWater: (water: WaterAvailability) => void;
  onChangePriorities: (p: PriorityWeights) => void;
  onChangeFarmerSoil: (soil: FarmerSoilNotes) => void;
  onAnalyze: () => void;
  onRequestGps: () => void;
  onExplorerError?: (msg: string | null) => void;
}

export const InteractiveMapTab: React.FC<InteractiveMapTabProps> = ({
  lang,
  activePoint,
  customPolygon,
  currentCrop,
  waterAvailability,
  priorities,
  farmerSoil,
  equipmentAccess = "manual_yunta",
  marketPreference = "grano_comercial",
  onChangeEquipment,
  farmerConfirmedInputs: _farmerConfirmedInputs = false,
  isPlanReady = false,
  voiceSlots = {},
  completedChecklistCount = 0,
  onSelectChecklistOption,
  onGoToPlan,
  onConfirmParcelPolygon,
  onSimulateExplorerPlan,
  onSaveExploredAsMyChacra,
  result,
  referenceData,
  isAnalyzing,
  isLocatingGps = false,
  onSelectPoint,
  onSelectBeacon,
  onSetPolygon,
  onChangeCrop,
  onChangeWater,
  onChangeFarmerSoil,
  onRequestGps,
  onExplorerError,
}) => {
  const isQu = lang === "qu";
  const [mapMode, setMapMode] = useState<"chacra" | "explorar">("chacra");
  const [explorerPoint, setExplorerPoint] = useState<{
    lat: number;
    lon: number;
    label?: string;
  }>({ lat: activePoint.lat, lon: activePoint.lon });
  const [explorerResult, setExplorerResult] =
    useState<RecommendResponse | null>(null);
  const [isExploring, setIsExploring] = useState(false);

  const [activeLayer, setActiveLayer] = useState<SatelliteLayerId>("clean");
  const [drawMode, setDrawMode] = useState(false);
  const [draftPoly, setDraftPoly] = useState<[number, number][]>([]);
  const [zonePickerOpen, setZonePickerOpen] = useState(false);
  const [soilSheetOpen, setSoilSheetOpen] = useState(false);
  const [mapInteracting, setMapInteracting] = useState(false);

  const webRef = useRef<{ injectJavaScript?: (script: string) => void } | null>(
    null
  );
  const probeSeqRef = useRef(0);

  const displayedPoint =
    mapMode === "explorar" ? explorerPoint : activePoint;
  const displayedResult =
    mapMode === "explorar" ? explorerResult || result : result;

  const terrain = displayedResult?.terrain;
  const activeStrat =
    displayedResult?.strategies.find(
      (s) => s.id === displayedResult.recommended_strategy_id
    ) || displayedResult?.strategies[0];
  const currentLayerInfo =
    SATELLITE_LAYERS.find((l) => l.id === activeLayer) || SATELLITE_LAYERS[0];

  const zoneTitle =
    (mapMode === "explorar" && explorerPoint.label) ||
    terrain?.zone_name ||
    `${isQu ? "Chakra" : "Parcela"} (${displayedPoint.lat.toFixed(2)}, ${displayedPoint.lon.toFixed(2)})`;

  const runExplorerProbe = async (
    lat: number,
    lon: number,
    label?: string
  ) => {
    const seq = ++probeSeqRef.current;
    setExplorerPoint({ lat, lon, label });
    setIsExploring(true);
    onExplorerError?.(null);
    try {
      const res = await requestRecommendations({
        lat,
        lon,
        parcel_id: null,
        polygon: null,
        current_crop: "sin_cultivo",
        water_availability: "secano",
        priorities,
        climate_scenario: {
          temp_delta_c: 0,
          rain_delta_pct: 0,
          frost_frequency: "normal",
          apply_20yr_projection: false,
        },
        farmer_soil: {
          texture_override: "auto",
          soil_acidity: "normal",
          compaction_or_drainage: "normal",
          local_frost_early: false,
        },
        equipment_access: equipmentAccess,
        market_preference: marketPreference,
        field_status: "auto",
        available_seeds: [],
        custom_zone_label: label || null,
      });
      if (seq !== probeSeqRef.current) return;
      setExplorerResult(res.data);
    } catch (err) {
      if (seq !== probeSeqRef.current) return;
      onExplorerError?.(
        err instanceof Error ? err.message : "No se pudo consultar el punto seleccionado."
      );
    } finally {
      if (seq === probeSeqRef.current) {
        setIsExploring(false);
      }
    }
  };

  // Compute 4 Frosted Glass Indicators strictly from backend response
  const waterDepthPct = useMemo<number | null>(() => {
    const smap = displayedResult?.biophysical.summary.mean_smap_moisture;
    if (typeof smap !== "number") return null;
    return Math.round(smap * 100);
  }, [displayedResult]);

  const plantHealthPct = useMemo<number | null>(() => {
    const summaryLatest = displayedResult?.biophysical.summary.latest_ndvi;
    const months = displayedResult?.biophysical.monthly_series || [];
    const meanNdvi = months.length
      ? months.reduce((sum, m) => sum + m.ndvi, 0) / months.length
      : null;
    const ndviVal =
      typeof summaryLatest === "number" ? summaryLatest : meanNdvi;
    if (typeof ndviVal !== "number") return null;
    return Math.min(
      98,
      Math.max(12, Math.round(((ndviVal - 0.12) / (0.85 - 0.12)) * 86 + 12))
    );
  }, [displayedResult]);

  const soilQualityPct = useMemo<number | null>(() => {
    const sp = terrain?.soil_profile;
    if (!sp) return null;
    const phVal = typeof sp.ph === "number" ? sp.ph : 6.2;
    const phScore = Math.max(
      8,
      32 - Math.max(0, Math.abs(phVal - 6.4) - 0.5) * 14
    );
    const omScore = Math.min(
      34,
      Math.max(8, ((sp.organic_matter_pct ?? 2.5) / 4.5) * 34)
    );
    const nScore = Math.min(
      22,
      Math.max(6, ((sp.nitrogen_g_kg ?? 1.5) / 2.5) * 22)
    );
    const texLower = String(sp.texture_class || "").toLowerCase();
    const texBonus =
      texLower === "franco" || texLower === "franca"
        ? 12
        : texLower.includes("franco")
          ? 9
          : 6;
    const base = phScore + omScore + nScore + texBonus;
    const acidDelta = farmerSoil.soil_acidity === "acido" ? -9 : 0;
    const condDelta =
      farmerSoil.compaction_or_drainage === "duro_compactado"
        ? -8
        : farmerSoil.compaction_or_drainage === "se_encharca"
        ? -7
        : 0;
    const texDelta =
      farmerSoil.texture_override === "pedregoso"
        ? -6
        : farmerSoil.texture_override === "franco_arenoso"
        ? -3
        : 0;
    return Math.min(
      96,
      Math.max(10, Math.round(base + acidDelta + condDelta + texDelta))
    );
  }, [terrain?.soil_profile, farmerSoil]);

  const pestRiskPct = useMemo<number | null>(() => {
    const vuln = activeStrat?.vulnerability_score;
    const pestBreak = activeStrat?.radar_scores.pest_break;
    if (typeof vuln !== "number") return null;
    const breakPenalty = typeof pestBreak === "number" ? (100 - pestBreak) * 0.35 : 0;
    const waterlogAdd = farmerSoil.compaction_or_drainage === "se_encharca" ? 6 : 0;
    return Math.min(88, Math.max(5, Math.round(vuln * 0.32 + breakPenalty + waterlogAdd)));
  }, [activeStrat, farmerSoil.compaction_or_drainage]);

  const estimatedAreaHa = useMemo(
    () =>
      estimatePolygonAreaHa(
        draftPoly.length >= 3 ? draftPoly : customPolygon,
        terrain?.area_ha
      ),
    [customPolygon, draftPoly, terrain?.area_ha]
  );

  const activeLayerTelemetry = useMemo(() => {
    if (!displayedResult) {
      return isQu
        ? "Huk chakrapi ñitiy allpata qawanaykipaq."
        : "Selecciona un punto o parcela para ver lecturas satelitales.";
    }
    const bioSummary = displayedResult.biophysical.summary;
    const climateSummary = displayedResult.simulated_climate.summary;
    let raw = "";
    if (activeLayer === "clean") {
      const elevTxt =
        terrain?.elevation_m !== undefined && terrain?.elevation_m !== null
          ? `${Math.round(terrain.elevation_m)} msnm`
          : "--";
      const slopeTxt =
        terrain?.slope_pct !== undefined && terrain?.slope_pct !== null
          ? `${terrain.slope_pct.toFixed(1)}%`
          : "--";
      raw = `Parcela a ${elevTxt} · Pendiente ${slopeTxt} · Toca una tarjeta arriba para superponer una capa satelital`;
    } else if (activeLayer === "ndvi") {
      const months = displayedResult.biophysical.monthly_series || [];
      const avgNdvi = months.length
        ? (months.reduce((sum, m) => sum + m.ndvi, 0) / months.length).toFixed(2)
        : "--";
      const lastNdviTxt =
        typeof bioSummary.latest_ndvi === "number"
          ? bioSummary.latest_ndvi_date
            ? `Últ. ${bioSummary.latest_ndvi_date}: NDVI ${bioSummary.latest_ndvi.toFixed(2)} · `
            : `NDVI actual ${bioSummary.latest_ndvi.toFixed(2)} · `
          : "";
      raw = `${lastNdviTxt}prom. anual ${avgNdvi} · ${bioSummary.bare_soil_month_count} meses suelo desnudo`;
    } else if (activeLayer === "smap") {
      const smapTxt = waterDepthPct !== null ? `${waterDepthPct}%` : "--";
      raw = `Humedad radicular SMAP ${smapTxt} · Balance ${Math.round(
        bioSummary.annual_water_balance_mm
      )} mm/año`;
    } else if (activeLayer === "frost") {
      const win = terrain?.frost_risk_window || "Estacional";
      raw = `Mín. ${climateSummary.min_temp_c.toFixed(1)}°C · ${
        climateSummary.frost_month_count
      } meses con riesgo (${win})`;
    } else {
      const slopeTxt =
        terrain?.slope_pct !== undefined && terrain?.slope_pct !== null
          ? `${terrain.slope_pct.toFixed(1)}%`
          : "--";
      raw = `Pendiente ${slopeTxt} · Índice físico erosión ${Math.round(
        bioSummary.mean_erosion_risk
      )}/100 · ${bioSummary.erosive_storm_months.length} meses de tormenta`;
    }
    return translateCropText(raw, lang);
  }, [activeLayer, isQu, lang, displayedResult, terrain, waterDepthPct]);

  // Display all tapped vertices immediately (starting from point #1) while drawing, or committed polygon
  const activeFarmPolygon: [number, number][] = useMemo(() => {
    if (mapMode === "explorar") return [];
    if (drawMode) return draftPoly;
    if (draftPoly.length >= 1) return draftPoly;
    if (customPolygon && customPolygon.length >= 3) return customPolygon;
    return [];
  }, [mapMode, drawMode, customPolygon, draftPoly]);

  const handleToggleDrawMode = () => {
    if (mapMode === "explorar") {
      setMapMode("chacra");
    }
    if (drawMode) {
      setDrawMode(false);
      if (draftPoly.length >= 3) {
        const committed = draftPoly;
        setDraftPoly([]);
        onSetPolygon(committed);
      } else {
        setDraftPoly([]);
      }
    } else {
      setDraftPoly([]);
      setDrawMode(true);
    }
  };

  const handleUndoVertex = () => {
    setDraftPoly((prev) => prev.slice(0, -1));
  };

  const handleMapTapCoord = (lat: number, lon: number) => {
    if (mapMode === "explorar") {
      void runExplorerProbe(lat, lon);
      return;
    }
    if (drawMode) {
      setDraftPoly((prev) => [...prev, [lat, lon] as [number, number]]);
    } else {
      setDraftPoly([]);
      onSelectPoint(lat, lon);
    }
  };

  const handleZoomIn = () => {
    webRef.current?.injectJavaScript?.("if (window.agroMap) { window.agroMap.zoomIn(); } true;");
  };

  const handleZoomOut = () => {
    webRef.current?.injectJavaScript?.("if (window.agroMap) { window.agroMap.zoomOut(); } true;");
  };

  // Update Leaflet WebView smoothly without reloading tiles or panning away while drawing corners
  useEffect(() => {
    const payload = JSON.stringify({
      lat: displayedPoint.lat,
      lon: displayedPoint.lon,
      poly: activeFarmPolygon,
      stroke: currentLayerInfo.polyStroke,
      layer: activeLayer,
      drawMode,
    });
    webRef.current?.injectJavaScript?.(
      `if (window.updateMapState) { window.updateMapState(${payload}); } true;`
    );
  }, [displayedPoint.lat, displayedPoint.lon, activeFarmPolygon, currentLayerInfo.polyStroke, activeLayer, drawMode]);

  // HTML for live Esri Satellite + NASA GIBS WebView mode (initialized once)
  const initialCenterRef = useRef([activePoint.lat, activePoint.lon]);
  const initialPolyRef = useRef(activeFarmPolygon);
  const initialStrokeRef = useRef(currentLayerInfo.polyStroke);
  const initialLayerRef = useRef(activeLayer);
  const leafletHtml = useMemo(() => {
    const [initLat, initLon] = initialCenterRef.current;
    return buildInteractiveMapHtml({
      initLat,
      initLon,
      initPoly: initialPolyRef.current,
      initStroke: initialStrokeRef.current,
      initLayer: initialLayerRef.current,
    });
  }, []);

  const waterCatalog = referenceData?.water_options?.length
    ? referenceData.water_options
    : WATER_OPTIONS_FALLBACK;
  const activeWaterOption =
    waterCatalog.find((w) => w.id === waterAvailability) || waterCatalog[0];

  return (
    <View style={styles.container}>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
        scrollEnabled={!mapInteracting}
      >
        {/* DEDICATED TOP CONTROLS HEADER (ZERO OVERLAP WITH MAP IMAGERY) */}
        <View style={styles.mapTopControlsWrap}>
          {/* DUAL MODE SWITCHER: MI CHACRA vs EXPLORAR MAPA LIBRE */}
          <View style={styles.modeSwitchRow}>
            <TouchableOpacity
              onPress={() => setMapMode("chacra")}
              style={[
                styles.modeSwitchPill,
                mapMode === "chacra" && styles.modeSwitchPillActive,
              ]}
              activeOpacity={0.88}
            >
              <MapPin
                size={14}
                color={mapMode === "chacra" ? COLORS.forestDeep : "#E5E7EB"}
              />
              <Text
                style={[
                  styles.modeSwitchText,
                  mapMode === "chacra" && styles.modeSwitchTextActive,
                ]}
              >
                Mi Chacra
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              onPress={() => {
                setDrawMode(false);
                setMapMode("explorar");
              }}
              style={[
                styles.modeSwitchPill,
                mapMode === "explorar" && styles.modeSwitchPillActive,
              ]}
              activeOpacity={0.88}
            >
              <Compass
                size={14}
                color={mapMode === "explorar" ? COLORS.forestDeep : "#E5E7EB"}
              />
              <Text
                style={[
                  styles.modeSwitchText,
                  mapMode === "explorar" && styles.modeSwitchTextActive,
                ]}
              >
                Explorar Mapa Libre
              </Text>
            </TouchableOpacity>
          </View>

          {/* LOCATION SEARCH PILL + COMPACT GPS BUTTON */}
          <View style={styles.topSearchRow}>
            <TouchableOpacity
              onPress={() => setZonePickerOpen(true)}
              style={styles.whiteFarmDropdown}
              activeOpacity={0.9}
            >
              {isAnalyzing || isExploring ? (
                <ActivityIndicator size="small" color={COLORS.agroPrimary} />
              ) : (
                <Search size={15} color={COLORS.agroPrimary} />
              )}
              <Text style={styles.whiteFarmDropdownText} numberOfLines={1}>
                {isAnalyzing || isExploring
                  ? `${isQu ? "Maskachkan" : "Consultando satélite"} (${displayedPoint.lat.toFixed(3)}, ${displayedPoint.lon.toFixed(3)})...`
                  : translateCropText(zoneTitle, lang)}
              </Text>
              <View style={styles.dropdownChevronCircle}>
                <ChevronDown size={14} color={COLORS.agroPrimary} />
              </View>
            </TouchableOpacity>

            <TouchableOpacity
              onPress={onRequestGps}
              disabled={isLocatingGps}
              style={styles.topGpsCircleBtn}
              activeOpacity={0.85}
            >
              {isLocatingGps ? (
                <ActivityIndicator size="small" color={COLORS.agroPrimary} />
              ) : (
                <Navigation size={17} color={COLORS.agroPrimary} strokeWidth={2.3} />
              )}
            </TouchableOpacity>
          </View>
        </View>

        {/* CLEAN SATELLITE MAP CANVAS (ONLY COMPACT LEFT TOOLS + TINY BOTTOM COORDS PILL) */}
        <View
          style={styles.mapFrame}
          onTouchStart={() => setMapInteracting(true)}
          onTouchEnd={() => setMapInteracting(false)}
          onTouchCancel={() => setMapInteracting(false)}
        >
          <WebViewComponent
            ref={webRef}
            originWhitelist={["*"]}
            source={{ html: leafletHtml }}
            style={styles.webview}
            javaScriptEnabled
            domStorageEnabled
            nestedScrollEnabled={false}
            overScrollMode="never"
            onLoadEnd={() => {
              const payload = JSON.stringify({
                lat: displayedPoint.lat,
                lon: displayedPoint.lon,
                poly: activeFarmPolygon,
                stroke: currentLayerInfo.polyStroke,
                layer: activeLayer,
                drawMode,
              });
              webRef.current?.injectJavaScript?.(
                `if (window.updateMapState) { window.updateMapState(${payload}); } true;`
              );
            }}
            onMessage={(ev) => {
              try {
                const msg = JSON.parse(ev.nativeEvent.data);
                if (msg.type === "interact") {
                  setMapInteracting(Boolean(msg.active));
                } else if (msg.type === "tap") {
                  handleMapTapCoord(msg.lat, msg.lon);
                }
              } catch {
                // ignore
              }
            }}
          />

          {/* LEFT VERTICAL STACK OF COMPACT WHITE CIRCULAR TOOLS */}
          <View style={styles.leftToolsStack}>
            <View style={styles.toolItemWrap}>
              <TouchableOpacity
                onPress={handleZoomIn}
                style={styles.whiteCircleTool}
                activeOpacity={0.85}
              >
                <Plus size={17} color={COLORS.agroPrimary} strokeWidth={2.5} />
              </TouchableOpacity>
            </View>

            <View style={styles.toolItemWrap}>
              <TouchableOpacity
                onPress={handleZoomOut}
                style={styles.whiteCircleTool}
                activeOpacity={0.85}
              >
                <Minus size={17} color={COLORS.agroPrimary} strokeWidth={2.5} />
              </TouchableOpacity>
            </View>

            <View style={styles.toolItemWrap}>
              <TouchableOpacity
                onPress={handleToggleDrawMode}
                style={[
                  styles.whiteCircleTool,
                  drawMode && { backgroundColor: COLORS.limeAccent },
                ]}
                activeOpacity={0.85}
              >
                {drawMode && draftPoly.length >= 3 ? (
                  <Check size={16} color={COLORS.forestDeep} strokeWidth={2.6} />
                ) : (
                  <PenTool
                    size={15}
                    color={drawMode ? COLORS.forestDeep : COLORS.amberFinance}
                    strokeWidth={2.3}
                  />
                )}
              </TouchableOpacity>
              <Text style={styles.toolLabelText}>
                {drawMode
                  ? isQu
                    ? "Tukuchiy"
                    : "Listo"
                  : isQu
                  ? "Suyuchay"
                  : "Marcar"}
              </Text>
            </View>

            {drawMode && draftPoly.length > 0 && (
              <View style={styles.toolItemWrap}>
                <TouchableOpacity
                  onPress={handleUndoVertex}
                  style={styles.whiteCircleTool}
                  activeOpacity={0.85}
                >
                  <RotateCcw size={15} color={COLORS.inkPrimary} strokeWidth={2.3} />
                </TouchableOpacity>
                <Text style={styles.toolLabelText}>
                  {isQu ? "Qipaman" : "Atrás"}
                </Text>
              </View>
            )}

            {mapMode === "chacra" && (customPolygon || draftPoly.length > 0) && (
              <View style={styles.toolItemWrap}>
                <TouchableOpacity
                  onPress={() => {
                    setDraftPoly([]);
                    setDrawMode(false);
                    if (customPolygon) {
                      onSetPolygon(null);
                    }
                  }}
                  style={styles.whiteCircleTool}
                >
                  <Trash2 size={15} color={COLORS.crimsonRisk} />
                </TouchableOpacity>
                <Text style={styles.toolLabelText}>
                  {isQu ? "Pichay" : "Borrar"}
                </Text>
              </View>
            )}
          </View>

          {/* SINGLE COMPACT BOTTOM-RIGHT TELEMETRY PILL */}
          <View style={styles.compactAreaBadge} pointerEvents="none">
            <Text style={styles.compactAreaBadgeText}>
              {estimatedAreaHa !== null ? `${estimatedAreaHa} ha · ` : ""}
              {terrain?.elevation_m !== undefined && terrain?.elevation_m !== null
                ? `${Math.round(terrain.elevation_m)} m`
                : "--"}
              {terrain?.slope_pct !== undefined && terrain?.slope_pct !== null
                ? ` · ${terrain.slope_pct.toFixed(1)}%`
                : ""}
            </Text>
          </View>

          {/* STATUS / DRAWING HINT PILL */}
          {(drawMode || isAnalyzing || isExploring) && (
            <View style={styles.mapStatusPillWrap} pointerEvents="none">
              <View style={styles.mapStatusPill}>
                {(isAnalyzing || isExploring) && !drawMode ? (
                  <>
                    <ActivityIndicator size="small" color={COLORS.limeBright} />
                    <Text style={styles.mapStatusPillText}>
                      {isQu ? "Musuqyachichkan..." : "Leyendo satélite..."}
                    </Text>
                  </>
                ) : (
                  <>
                    <PenTool size={13} color={COLORS.limeBright} />
                    <Text style={styles.mapStatusPillText}>
                      Esquinas: {draftPoly.length} ·{" "}
                      {draftPoly.length >= 3
                        ? "Toca Listo para cerrar polígono"
                        : "Toca el mapa para marcar tu chacra"}
                    </Text>
                  </>
                )}
              </View>
            </View>
          )}
        </View>

        {/* PARCEL CONFIRMATION BAR (DOCKED CLEANLY BELOW MAP - ZERO OVERLAP) */}
        {mapMode === "chacra" &&
          voiceSlots.location_confirmed &&
          !voiceSlots.map_verified && (
            <View style={styles.confirmParcelDockedBar}>
              <View style={{ flex: 1 }}>
                <Text style={styles.confirmParcelTitle}>
                  Confirma exactamente tu parcela (1 ha)
                </Text>
                <Text style={styles.confirmParcelSub}>
                  Toca el mapa para mover el cuadrado o usa Marcar para dibujar tus esquinas.
                </Text>
              </View>
              <TouchableOpacity
                onPress={() => onConfirmParcelPolygon?.(false)}
                style={styles.confirmParcelBtn}
                activeOpacity={0.9}
              >
                <Check size={15} color={COLORS.forestDeep} strokeWidth={2.6} />
                <Text style={styles.confirmParcelBtnText}>Confirmar</Text>
              </TouchableOpacity>
            </View>
          )}

        {/* UNIFIED SATELLITE INSPECTOR CARD (4 CLICKABLE CUADRITOS + LIVE LAYER DIAGNOSTIC) */}
        <SatelliteMetricsGrid
          lang={lang}
          mapMode={mapMode}
          zoneTitle={zoneTitle}
          displayedPoint={displayedPoint}
          displayedResult={displayedResult}
          explorerResult={explorerResult}
          activeLayer={activeLayer}
          onChangeLayer={setActiveLayer}
          waterDepthPct={waterDepthPct}
          plantHealthPct={plantHealthPct}
          pestRiskPct={pestRiskPct}
          soilQualityPct={soilQualityPct}
          currentLayerInfo={currentLayerInfo}
          activeLayerTelemetry={activeLayerTelemetry}
          isPlanReady={isPlanReady}
          completedChecklistCount={completedChecklistCount}
          voiceSlots={voiceSlots}
          referenceData={referenceData}
          currentCrop={currentCrop}
          waterAvailability={waterAvailability}
          activeWaterOption={activeWaterOption}
          onSimulateExplorerPlan={onSimulateExplorerPlan}
          onSaveExploredAsMyChacra={onSaveExploredAsMyChacra}
          onSwitchToChacraMode={() => setMapMode("chacra")}
          onOpenSoilSheet={() => {
            setMapInteracting(false);
            setSoilSheetOpen(true);
          }}
          onGoToPlan={onGoToPlan}
        />
      </ScrollView>

      {/* MODAL 1: CONFIGURACIÓN COMPLETA DE LAS 6 PREGUNTAS DE MI CHACRA */}
      <ParcelParametersModal
        visible={soilSheetOpen}
        onClose={() => setSoilSheetOpen(false)}
        isQu={isQu}
        lang={lang}
        completedChecklistCount={completedChecklistCount}
        isPlanReady={isPlanReady}
        voiceSlots={voiceSlots}
        zoneTitle={zoneTitle}
        estimatedAreaHa={estimatedAreaHa}
        onConfirmParcelPolygon={onConfirmParcelPolygon}
        referenceData={referenceData}
        currentCrop={currentCrop}
        onSelectChecklistOption={onSelectChecklistOption}
        onChangeCrop={onChangeCrop}
        waterCatalog={waterCatalog}
        waterAvailability={waterAvailability}
        onChangeWater={onChangeWater}
        farmerSoil={farmerSoil}
        onChangeFarmerSoil={onChangeFarmerSoil}
        equipmentAccess={equipmentAccess}
        onChangeEquipment={onChangeEquipment}
        onGoToPlan={onGoToPlan}
      />

      {/* MODAL 2: SELECTOR DE DISTRITO / PARCELA EN CAJAMARCA */}
      <MapZonePickerModal
        visible={zonePickerOpen}
        onClose={() => setZonePickerOpen(false)}
        isQu={isQu}
        lang={lang}
        mapMode={mapMode}
        referenceData={referenceData}
        onRunExplorerProbe={runExplorerProbe}
        onSelectPoint={onSelectPoint}
        onSelectBeacon={onSelectBeacon}
      />
    </View>
  );
};

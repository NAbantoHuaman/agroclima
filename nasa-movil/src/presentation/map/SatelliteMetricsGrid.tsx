import React from "react";
import {
  ArrowRight,
  Check,
  CheckCircle2,
  Droplets,
  Layers,
  Sliders,
  Snowflake,
  Sprout,
} from "lucide-react-native";
import { Text, TouchableOpacity, View } from "react-native";
import {
  CURRENT_CROP_LABELS,
  SATELLITE_LAYERS,
  WATER_SHORT_LABELS,
  type SatelliteLayerId,
} from "../../domain/agronomy/constants";
import { translateCropText } from "../../i18n/translations";
import { COLORS } from "../../theme/tokens";
import type {
  AppLanguage,
  CurrentCropId,
  RecommendResponse,
  ReferenceDataResponse,
  VoiceConfirmedSlots,
  WaterAvailability,
} from "../../types";
import { styles } from "./InteractiveMapTab.styles";

interface SatelliteMetricsGridProps {
  lang: AppLanguage;
  mapMode: "chacra" | "explorar";
  zoneTitle: string;
  displayedPoint: { lat: number; lon: number };
  displayedResult: RecommendResponse | null;
  explorerResult: RecommendResponse | null;
  activeLayer: SatelliteLayerId;
  onChangeLayer: (layer: SatelliteLayerId) => void;
  waterDepthPct: number | null;
  plantHealthPct: number | null;
  pestRiskPct: number | null;
  soilQualityPct: number | null;
  currentLayerInfo: (typeof SATELLITE_LAYERS)[number];
  activeLayerTelemetry: string;
  isPlanReady: boolean;
  completedChecklistCount: number;
  voiceSlots: VoiceConfirmedSlots;
  referenceData: ReferenceDataResponse | null;
  currentCrop: CurrentCropId;
  waterAvailability: WaterAvailability;
  activeWaterOption: { id: WaterAvailability; label: string };
  onSimulateExplorerPlan?: (simRes: RecommendResponse) => void;
  onSaveExploredAsMyChacra?: (
    lat: number,
    lon: number,
    label: string,
    simRes?: RecommendResponse | null
  ) => void;
  onSwitchToChacraMode: () => void;
  onOpenSoilSheet: () => void;
  onGoToPlan?: () => void;
}

export const SatelliteMetricsGrid: React.FC<SatelliteMetricsGridProps> = ({
  lang,
  mapMode,
  zoneTitle,
  displayedPoint,
  displayedResult,
  explorerResult,
  activeLayer,
  onChangeLayer,
  waterDepthPct,
  plantHealthPct,
  pestRiskPct,
  soilQualityPct,
  currentLayerInfo,
  activeLayerTelemetry,
  isPlanReady,
  completedChecklistCount,
  voiceSlots,
  referenceData,
  currentCrop,
  waterAvailability,
  activeWaterOption,
  onSimulateExplorerPlan,
  onSaveExploredAsMyChacra,
  onSwitchToChacraMode,
  onOpenSoilSheet,
  onGoToPlan,
}) => {
  const datasets = displayedResult?.biophysical.provenance.harmonized_datasets || [];
  const findDs = (...needles: string[]) =>
    datasets.find((d) =>
      needles.some((needle) => d.sensor.toLowerCase().includes(needle.toLowerCase()))
    );

  const smapDs = findDs("smap", "era5-land + nasa gwettop");
  const ndviDs = findDs("sentinel-2", "ndvi");
  const powerDs = findDs("nasa power");
  const ecostressDs = findDs("ecostress", "et0");
  const soilDs = findDs("soilgrids", "suelos zee");
  const demDs = findDs("srtm", "copernicus dem");

  const getBadgeMeta = (mode?: string) => {
    if (mode === "en_vivo") {
      return {
        label: "En vivo",
        box: styles.modeBadgeLive,
        color: "#047857",
      };
    }
    if (mode === "guardado") {
      return {
        label: "Guardado",
        box: styles.modeBadgeSaved,
        color: "#1D4ED8",
      };
    }
    return {
      label: "Estimado",
      box: styles.modeBadgeEst,
      color: "#B45309",
    };
  };

  const smapLabel = smapDs?.sensor.includes("SMAP") && smapDs.mode !== "estimado"
    ? "NASA SMAP"
    : smapDs?.sensor.includes("ERA5")
      ? "ERA5 + GWETTOP"
      : "Humedad estimada";
  const smapBadge = getBadgeMeta(smapDs?.mode);

  const ndviLabel = ndviDs?.sensor.includes("Sentinel-2") && ndviDs.mode !== "estimado"
    ? "Sentinel-2 (10 m)"
    : "NDVI estimado";
  const ndviBadge = getBadgeMeta(ndviDs?.mode);

  const powerLabel = ecostressDs?.sensor.includes("ECOSTRESS")
    ? "POWER + ECOSTRESS"
    : "NASA POWER 20a";
  const powerBadge = getBadgeMeta(powerDs?.mode);

  const soilPart = soilDs?.sensor.includes("SoilGrids") ? "SoilGrids 250m" : "ZEE Soil";
  const demPart = demDs?.sensor.includes("30")
    ? "SRTM 30m"
    : demDs?.sensor.includes("90")
      ? "Cop 90m"
      : "DEM IDW";
  const combinedSoilMode =
    soilDs?.mode === "en_vivo" && (demDs?.mode === "en_vivo" || demDs?.mode === "guardado")
      ? "en_vivo"
      : soilDs?.mode === "estimado" || demDs?.mode === "modelo" || demDs?.mode === "estimado"
        ? "estimado"
        : soilDs?.mode || demDs?.mode;
  const soilDemBadge = getBadgeMeta(combinedSoilMode);

  const activeDsDetail =
    activeLayer === "clean"
      ? null
      : activeLayer === "smap"
        ? smapDs
        : activeLayer === "ndvi"
          ? ndviDs
          : activeLayer === "frost"
            ? powerDs
            : demDs || soilDs;

  return (
    <View style={styles.layerBarSection}>
      <View style={styles.inspectorHeaderRow}>
        <View style={{ flex: 1 }}>
          <Text style={styles.inspectorOverline}>
            {mapMode === "explorar"
              ? "LECTURA SATELITAL DEL PUNTO EXPLORADO"
              : "LECTURA SATELITAL DE MI CHACRA"}
          </Text>
          <Text style={styles.inspectorTitle} numberOfLines={1}>
            {translateCropText(zoneTitle, lang)}
          </Text>
        </View>
        <Text style={styles.inspectorCoords}>
          {displayedPoint.lat.toFixed(4)}, {displayedPoint.lon.toFixed(4)}
        </Text>
      </View>

      {/* UNIFIED 2x2 INTERACTIVE LAYER + METRIC CUADRITOS */}
      <View style={styles.unifiedTilesGrid}>
        <TouchableOpacity
          onPress={() => onChangeLayer(activeLayer === "smap" ? "clean" : "smap")}
          style={[
            styles.unifiedTileCard,
            activeLayer === "smap" && styles.unifiedTileCardActive,
          ]}
          activeOpacity={0.85}
        >
          <View style={styles.unifiedTileTop}>
            <Text style={styles.unifiedTileLabel}>Humedad Suelo</Text>
            <Droplets size={15} color="#0284C7" />
          </View>
          <Text style={styles.unifiedTileValue}>
            {waterDepthPct !== null ? `${waterDepthPct}%` : "--"}
          </Text>
          <View style={styles.tileFooterRow}>
            <Text style={styles.unifiedTileSource} numberOfLines={1}>
              {smapLabel}
            </Text>
            <View style={[styles.modeBadge, smapBadge.box]}>
              <Text style={[styles.modeBadgeText, { color: smapBadge.color }]}>
                {smapBadge.label}
              </Text>
            </View>
          </View>
        </TouchableOpacity>

        <TouchableOpacity
          onPress={() => onChangeLayer(activeLayer === "ndvi" ? "clean" : "ndvi")}
          style={[
            styles.unifiedTileCard,
            activeLayer === "ndvi" && styles.unifiedTileCardActive,
          ]}
          activeOpacity={0.85}
        >
          <View style={styles.unifiedTileTop}>
            <Text style={styles.unifiedTileLabel}>Salud Vegetal</Text>
            <Sprout size={15} color={COLORS.agroPrimary} />
          </View>
          <Text style={styles.unifiedTileValue}>
            {plantHealthPct !== null ? `${plantHealthPct}%` : "--"}
          </Text>
          <View style={styles.tileFooterRow}>
            <Text style={styles.unifiedTileSource} numberOfLines={1}>
              {ndviLabel}
            </Text>
            <View style={[styles.modeBadge, ndviBadge.box]}>
              <Text style={[styles.modeBadgeText, { color: ndviBadge.color }]}>
                {ndviBadge.label}
              </Text>
            </View>
          </View>
        </TouchableOpacity>

        <TouchableOpacity
          onPress={() => onChangeLayer(activeLayer === "frost" ? "clean" : "frost")}
          style={[
            styles.unifiedTileCard,
            activeLayer === "frost" && styles.unifiedTileCardActive,
          ]}
          activeOpacity={0.85}
        >
          <View style={styles.unifiedTileTop}>
            <Text style={styles.unifiedTileLabel}>Heladas y Plagas</Text>
            <Snowflake size={15} color="#D97706" />
          </View>
          <Text style={styles.unifiedTileValue}>
            {pestRiskPct !== null ? `${pestRiskPct}% riesgo` : "--"}
          </Text>
          <View style={styles.tileFooterRow}>
            <Text style={styles.unifiedTileSource} numberOfLines={1}>
              {powerLabel}
            </Text>
            <View style={[styles.modeBadge, powerBadge.box]}>
              <Text style={[styles.modeBadgeText, { color: powerBadge.color }]}>
                {powerBadge.label}
              </Text>
            </View>
          </View>
        </TouchableOpacity>

        <TouchableOpacity
          onPress={() => onChangeLayer(activeLayer === "erosion" ? "clean" : "erosion")}
          style={[
            styles.unifiedTileCard,
            activeLayer === "erosion" && styles.unifiedTileCardActive,
          ]}
          activeOpacity={0.85}
        >
          <View style={styles.unifiedTileTop}>
            <Text style={styles.unifiedTileLabel}>Calidad de Suelo</Text>
            <Layers size={15} color="#6D28D9" />
          </View>
          <Text style={styles.unifiedTileValue}>
            {soilQualityPct !== null ? `${soilQualityPct}%` : "--"}
          </Text>
          <View style={styles.tileFooterRow}>
            <Text style={styles.unifiedTileSource} numberOfLines={1}>
              {soilPart} + {demPart}
            </Text>
            <View style={[styles.modeBadge, soilDemBadge.box]}>
              <Text style={[styles.modeBadgeText, { color: soilDemBadge.color }]}>
                {soilDemBadge.label}
              </Text>
            </View>
          </View>
        </TouchableOpacity>
      </View>

      {/* DYNAMIC EXPLANATION FOR THE SELECTED CUADRITO */}
      <View style={styles.layerExplainBox}>
        <View style={styles.layerExplainTopRow}>
          <View style={styles.layerExplainTagRow}>
            <View
              style={[
                styles.layerColorDot,
                { backgroundColor: currentLayerInfo.polyStroke },
              ]}
            />
            <Text style={styles.layerExplainTag} numberOfLines={1}>
              {translateCropText(currentLayerInfo.label, lang)}
            </Text>
          </View>
          <View style={styles.layerExplainActionsRow}>
            {activeLayer !== "clean" && (
              <TouchableOpacity
                activeOpacity={0.8}
                onPress={() => onChangeLayer("clean")}
                style={styles.clearLayerChip}
              >
                <Text style={styles.clearLayerChipText}>
                  {translateCropText("Mapa limpio", lang)}
                </Text>
              </TouchableOpacity>
            )}
            <Text style={styles.layerMapActiveTag}>
              {translateCropText(currentLayerInfo.shortTag, lang)}
            </Text>
          </View>
        </View>
        <Text style={styles.layerTelemetryText}>{activeLayerTelemetry}</Text>
        <Text style={styles.layerExplainText}>
          {translateCropText(currentLayerInfo.explanation, lang)}
        </Text>
        {(displayedResult?.terrain?.aspect_label ||
          displayedResult?.terrain?.vertex_differential_risk) && (
          <Text style={styles.layerMethodNote}>
            Relieve:{" "}
            {[
              displayedResult.terrain.aspect_label,
              displayedResult.terrain.elevation_span_m &&
              displayedResult.terrain.elevation_span_m >= 3
                ? `desnivel ${displayedResult.terrain.elevation_span_m.toFixed(0)} m`
                : null,
              displayedResult.terrain.vertex_differential_risk,
            ]
              .filter(Boolean)
              .join(" · ")}
          </Text>
        )}
        {(activeDsDetail?.plain || displayedResult?.biophysical.provenance.erosion_method_label) && (
          <Text style={styles.layerMethodNote}>
            {activeLayer === "erosion" &&
            displayedResult?.biophysical.provenance.erosion_method_label
              ? displayedResult.biophysical.provenance.erosion_method_label
              : `${activeDsDetail?.sensor}: ${activeDsDetail?.resolution}`}
          </Text>
        )}
        {displayedResult?.biophysical.provenance.spatial_scale_hierarchy && (
          <View style={styles.scaleTierWrap}>
            {displayedResult.biophysical.provenance.spatial_scale_hierarchy.map(
              (tier) => (
                <View key={tier.tier} style={styles.scaleTierPill}>
                  <Text style={styles.scaleTierTitle}>
                    {tier.resolution} · {tier.sensors}
                  </Text>
                </View>
              )
            )}
          </View>
        )}
      </View>

      {/* CURRENT FIELD DATA SUMMARY & NAVIGATION TO ROTATION PLAN */}
      {mapMode === "explorar" ? (
        <View style={styles.explorerActionsBox}>
          <Text style={styles.explorerActionsHint}>
            Toca cualquier punto del mapa o busca un distrito arriba para
            inspeccionar sus indicadores satelitales sin modificar tu chacra
            guardada.
          </Text>
          <View style={styles.explorerBtnsRow}>
            {displayedResult && (
              <TouchableOpacity
                onPress={() => onSimulateExplorerPlan?.(displayedResult)}
                style={styles.explorerSimBtn}
                activeOpacity={0.88}
              >
                <Sprout size={15} color="#FFFFFF" />
                <Text style={styles.explorerSimBtnText}>
                  Simular rotación aquí
                </Text>
              </TouchableOpacity>
            )}
            <TouchableOpacity
              onPress={() => {
                onSaveExploredAsMyChacra?.(
                  displayedPoint.lat,
                  displayedPoint.lon,
                  zoneTitle,
                  explorerResult
                );
                onSwitchToChacraMode();
              }}
              style={styles.explorerSaveChacraBtn}
              activeOpacity={0.88}
            >
              <Check size={15} color={COLORS.forestDeep} />
              <Text style={styles.explorerSaveChacraBtnText}>
                Fijar como Mi Chacra
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      ) : (
        <View style={styles.myChacraActionsCol}>
          <View style={styles.currentParcelSummaryCard}>
            <View style={{ flex: 1 }}>
              <Text style={styles.currentParcelSummaryLabel}>
                {isPlanReady || completedChecklistCount >= 6
                  ? `Parámetros de Mi Chacra listos (${completedChecklistCount}/6)`
                  : `Configuración de Mi Chacra (${completedChecklistCount}/6 datos listos)`}
              </Text>
              <Text style={styles.currentParcelSummaryVal} numberOfLines={2}>
                {voiceSlots.crop_confirmed
                  ? translateCropText(
                      referenceData?.current_crop_options?.find(
                        (c) => c.id === currentCrop
                      )?.label || CURRENT_CROP_LABELS[currentCrop],
                      lang
                    )
                  : "Cultivo previo pendiente"}{" "}
                ·{" "}
                {voiceSlots.water_confirmed
                  ? translateCropText(
                      WATER_SHORT_LABELS[waterAvailability] ||
                        activeWaterOption.label,
                      lang
                    )
                  : "Agua pendiente"}
              </Text>
            </View>
            <TouchableOpacity
              onPress={onOpenSoilSheet}
              style={styles.adjustParcelOutlineBtn}
              activeOpacity={0.85}
            >
              <Sliders size={14} color={COLORS.agroPrimary} />
              <Text style={styles.adjustParcelOutlineText}>Ajustar</Text>
            </TouchableOpacity>
          </View>

          {completedChecklistCount >= 6 || isPlanReady ? (
            <TouchableOpacity
              onPress={() => onGoToPlan?.()}
              style={styles.goToPlanPrimaryBtn}
              activeOpacity={0.88}
            >
              <CheckCircle2
                size={17}
                color={COLORS.forestDeep}
                strokeWidth={2.4}
              />
              <Text style={styles.goToPlanPrimaryBtnText}>
                Pasar al Plan de Rotación
              </Text>
              <ArrowRight
                size={17}
                color={COLORS.forestDeep}
                strokeWidth={2.4}
              />
            </TouchableOpacity>
          ) : (
            <TouchableOpacity
              onPress={onOpenSoilSheet}
              style={styles.goToPlanPrimaryBtn}
              activeOpacity={0.88}
            >
              <Sliders size={17} color={COLORS.forestDeep} strokeWidth={2.4} />
              <Text style={styles.goToPlanPrimaryBtnText}>
                Ajustar los 6 parámetros ({completedChecklistCount}/6)
              </Text>
              <ArrowRight
                size={17}
                color={COLORS.forestDeep}
                strokeWidth={2.4}
              />
            </TouchableOpacity>
          )}
        </View>
      )}
    </View>
  );
};

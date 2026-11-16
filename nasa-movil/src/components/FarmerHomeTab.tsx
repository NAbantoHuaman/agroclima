import React, { useEffect, useState } from "react";
import * as Speech from "expo-speech";
import {
  ArrowRight,
  Calendar,
  ChevronDown,
  Coins,
  Droplets,
  Globe2,
  MapPin,
  Mic,
  Navigation,
  Search,
  ShieldAlert,
  ShieldCheck,
  Snowflake,
  Sparkles,
  Sprout,
  Volume2,
  VolumeX,
} from "lucide-react-native";
import {
  ActivityIndicator,
  ImageBackground,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { CropPlantImage } from "./CropPlantImage";
import {
  PRIORITY_PILLS,
  type PriorityPresetId,
} from "../domain/agronomy/constants";
import {
  translateCropText,
  type MobileUiDictionary,
} from "../i18n/translations";
import {
  FieldLandscapeSvg,
  WeatherCloudSvg,
} from "../presentation/home/HomeIllustrations";
import { HomeZonePickerModal } from "../presentation/home/HomeZonePickerModal";
import { ParcelCalibrationChecklist } from "../presentation/home/ParcelCalibrationChecklist";
import { styles } from "../presentation/home/FarmerHomeTab.styles";
import { COLORS } from "../theme/tokens";
import type {
  AppLanguage,
  BeaconParcel,
  EquipmentAccess,
  PriorityWeights,
  RecommendResponse,
  ReferenceDataResponse,
  VoiceConfirmedSlots,
} from "../types";

const HERO_WEATHER_BG = require("../../assets/home-weather-bg.jpg");

interface FarmerHomeTabProps {
  t: MobileUiDictionary;
  lang: AppLanguage;
  onToggleLang: () => void;
  activePoint: { lat: number; lon: number };
  result: RecommendResponse;
  referenceData: ReferenceDataResponse | null;
  priorities: PriorityWeights;
  equipmentAccess?: EquipmentAccess;
  onChangeEquipment?: (eq: EquipmentAccess) => void;
  isLocatingGps: boolean;
  isAnalyzing?: boolean;
  farmerConfirmedInputs?: boolean;
  hasLocatedParcel?: boolean;
  isPlanReady?: boolean;
  voiceSlots?: VoiceConfirmedSlots;
  completedChecklistCount?: number;
  onSelectChecklistOption?: (
    slotKey: "water" | "crop" | "soil" | "climate" | "goal",
    optionId: string,
    label: string
  ) => void;
  onForceCalculatePlan?: () => void;
  onRequestGps: () => void;
  onSelectBeacon: (beacon: BeaconParcel) => void;
  onSelectLocation: (
    lat: number,
    lon: number,
    parcelId: string | null,
    label?: string | null
  ) => void;
  onChangePriorities: (p: PriorityWeights) => void;
  onSelectPriorityPreset?: (presetId: string, weights: PriorityWeights) => void;
  onNavigateTab: (tab: "mapa" | "plan" | "semillas") => void;
  onOpenVoiceModal: () => void;
}

export const FarmerHomeTab: React.FC<FarmerHomeTabProps> = ({
  t: _t,
  lang,
  onToggleLang,
  activePoint,
  result,
  referenceData,
  priorities,
  equipmentAccess = "manual_yunta",
  onChangeEquipment,
  isLocatingGps,
  isAnalyzing = false,
  farmerConfirmedInputs = false,
  hasLocatedParcel = false,
  isPlanReady = false,
  voiceSlots = {},
  completedChecklistCount = 0,
  onSelectChecklistOption,
  onForceCalculatePlan,
  onRequestGps,
  onSelectBeacon,
  onSelectLocation,
  onChangePriorities,
  onSelectPriorityPreset,
  onNavigateTab,
  onOpenVoiceModal,
}) => {
  const [selectedPreset, setSelectedPreset] = useState<PriorityPresetId>("equilibrado");
  const [zoneModalOpen, setZoneModalOpen] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  useEffect(() => {
    let bestId: PriorityPresetId = "equilibrado";
    let bestDist = Infinity;
    for (const pill of PRIORITY_PILLS) {
      const pw = pill.weights;
      const dist =
        Math.abs(pw.water_conservation - priorities.water_conservation) +
        Math.abs(pw.soil_fertility - priorities.soil_fertility) +
        Math.abs(pw.erosion_control - priorities.erosion_control) +
        Math.abs(pw.pest_break - priorities.pest_break) +
        Math.abs(pw.commercial_forage - priorities.commercial_forage);
      if (dist < bestDist) {
        bestDist = dist;
        bestId = pill.id;
      }
    }
    setSelectedPreset(bestId);
  }, [priorities]);

  const terrain = result.terrain;
  const climateSummary = result.simulated_climate.summary;
  const bioSummary = result.biophysical.summary;
  const recommendedStrat =
    result.strategies.find((s) => s.id === result.recommended_strategy_id) ||
    result.strategies[0];
  const baselineStrat =
    result.strategies.find((s) => s.id === "baseline") || result.strategies[0];

  const isQu = lang === "qu";
  const zoneTitle =
    terrain?.zone_name ||
    `${isQu ? "Chakra" : "Parcela"} (${activePoint.lat.toFixed(2)}, ${activePoint.lon.toFixed(2)})`;

  const frostRiskLevel =
    climateSummary.frost_month_count >= 3
      ? "Alto"
      : climateSummary.frost_month_count >= 1
        ? "Medio"
        : "Bajo";

  const frostRiskLabel = isQu
    ? frostRiskLevel === "Alto"
      ? "Hatun"
      : frostRiskLevel === "Medio"
      ? "Chawpi"
      : "Pisi"
    : frostRiskLevel;

  const liveTempC =
    typeof bioSummary.current_temp_c === "number"
      ? bioSummary.current_temp_c
      : bioSummary.mean_temp_c;
  const liveMinTempC =
    typeof bioSummary.current_min_temp_c === "number"
      ? bioSummary.current_min_temp_c
      : climateSummary.min_temp_c;
  const liveWeatherLabel =
    bioSummary.current_weather_label ||
    result.seasonal_context?.season_label ||
    "Campaña Agrícola";
  const liveWeatherSource =
    bioSummary.current_weather_source ||
    result.biophysical.provenance?.nasa_power_label ||
    "Open-Meteo · NASA";

  // Humedad superficial directamente desde serie biofisica SMAP / ERA5 del backend
  const soilMoisturePct =
    typeof bioSummary.mean_smap_moisture === "number"
      ? Math.round(bioSummary.mean_smap_moisture * 100)
      : null;

  // Cultivos adaptados al piso altitudinal segun catalogo vivo del backend y matriz de viabilidad
  const elev = terrain?.elevation_m;
  const viabilityOrder = result.climate_outlook_20yr?.crop_viability || [];
  const rankMap = new Map(viabilityOrder.map((v, idx) => [v.crop_id, idx]));
  const backendCrops = referenceData?.crops || [];
  const suitedCrops = (
    elev !== undefined && elev !== null
      ? backendCrops.filter(
          (c) => elev >= c.altitude_min_m - 150 && elev <= c.altitude_max_m + 150
        )
      : backendCrops
  )
    .slice()
    .sort((a, b) => (rankMap.get(a.id) ?? 99) - (rankMap.get(b.id) ?? 99))
    .slice(0, 6);

  const handleListenHomeSummary = () => {
    if (isSpeaking) {
      Speech.stop();
      setIsSpeaking(false);
      return;
    }
    const cropsList = recommendedStrat.phases
      .filter((p) => p.crop_id !== "suelo_desnudo")
      .map((p) => translateCropText(p.crop_name, lang))
      .join(isQu ? ", qipanman " : ", luego ");

    const elevSpeech =
      terrain?.elevation_m !== undefined && terrain?.elevation_m !== null
        ? isQu
          ? `, ${Math.round(terrain.elevation_m)} metros sayayninpi`
          : `, a ${Math.round(terrain.elevation_m)} metros`
        : "";
    const marginSpeech =
      recommendedStrat.metrics.net_margin_2yr_soles_ha !== null &&
      recommendedStrat.metrics.net_margin_2yr_soles_ha !== undefined
        ? isQu
          ? ` Kay muyuywanqa ${recommendedStrat.metrics.net_margin_2yr_soles_ha} soles hectáreapi ganayta atinki.`
          : ` Con este plan puedes lograr un margen estimado de ${recommendedStrat.metrics.net_margin_2yr_soles_ha} soles por hectárea.`
        : "";

    const speechText = isQu
      ? `Allinllachu chakra ruraq. ${translateCropText(zoneTitle, lang)} suyupi${elevSpeech}, ` +
        `kunan pacha ruphayqa ${liveTempC.toFixed(1)} grado, wata tamyaqa ${climateSummary.annual_precip_mm} milímetro. ` +
        `Qasa chikiqa ${frostRiskLabel}. ` +
        `Iskay wata allpayki allin kananpaq kaykunata muyuchiy: ${cropsList}.` +
        marginSpeech
      : `Hola agricultor. En ${zoneTitle}${elevSpeech}, ` +
        `la temperatura actual es ${liveTempC.toFixed(1)} grados (${liveWeatherLabel}) y la lluvia anual es ${climateSummary.annual_precip_mm} milímetros. ` +
        `El riesgo de helada es ${frostRiskLevel}. ` +
        `Para cuidar tu tierra y tu bolsillo los próximos 2 años, te recomendamos rotar: ${cropsList}. ` +
        marginSpeech;

    setIsSpeaking(true);
    Speech.speak(speechText, {
      language: "es-PE",
      rate: 0.95,
      onDone: () => setIsSpeaking(false),
      onStopped: () => setIsSpeaking(false),
      onError: () => setIsSpeaking(false),
    });
  };

  return (
    <ScrollView
      style={styles.scroll}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      {/* CURVED DEEP FOREST HERO SECTION (Inspired by Image 1 Center Screen) */}
      <View style={styles.heroContainer}>
        {/* Top Greeting & Language / Audio Controls */}
        <View style={styles.greetingRow}>
          <View style={styles.farmerIdentity}>
            <View style={styles.avatarCircle}>
              <Sprout size={20} color={COLORS.limeBright} strokeWidth={2.3} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.greetingSmall}>
                {lang === "qu"
                  ? "Allinllachu, Chakra Ruraq"
                  : "Hola, compañero agricultor"}
              </Text>
              <Text style={styles.greetingTitle} numberOfLines={1}>
                {lang === "qu" ? "Chakrayki Yanapaq" : "Tu Chacra Inteligente"}
              </Text>
            </View>
          </View>

          <View style={styles.topRightActions}>
            <TouchableOpacity
              onPress={handleListenHomeSummary}
              style={[
                styles.circleActionBtn,
                isSpeaking && { backgroundColor: COLORS.crimsonRisk },
              ]}
              activeOpacity={0.8}
            >
              {isSpeaking ? (
                <VolumeX size={17} color="#FFFFFF" />
              ) : (
                <Volume2 size={17} color={COLORS.limeBright} />
              )}
            </TouchableOpacity>

            <TouchableOpacity
              onPress={onToggleLang}
              style={styles.langPill}
              activeOpacity={0.8}
            >
              <Globe2 size={14} color={COLORS.limeBright} />
              <Text style={styles.langPillText}>
                {lang === "es" ? "ES" : "QU"}
              </Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* FROSTED DARK GREEN WEATHER & FIELD CARD (Andean terrace background) */}
        <ImageBackground
          source={HERO_WEATHER_BG}
          resizeMode="cover"
          style={styles.weatherCard}
          imageStyle={styles.weatherCardBgImage}
        >
          <View style={styles.weatherCardScrim} pointerEvents="none" />
          {/* Location selector + Cloud SVG */}
          <View style={styles.weatherTopRow}>
            <TouchableOpacity
              onPress={() => setZoneModalOpen(true)}
              style={styles.locationSelectorPill}
              activeOpacity={0.8}
            >
              {isAnalyzing || isLocatingGps ? (
                <ActivityIndicator size="small" color={COLORS.limeBright} />
              ) : (
                <MapPin size={15} color={COLORS.limeBright} strokeWidth={2.3} />
              )}
              <Text style={styles.locationNameText} numberOfLines={1}>
                {!hasLocatedParcel
                  ? isQu
                    ? "Chakraykita tariy (Toca aquí)"
                    : "Ubica tu chacra (Toca aquí)"
                  : isAnalyzing
                    ? `${isQu ? "Maskachkan" : "Cargando"} (${activePoint.lat.toFixed(3)}, ${activePoint.lon.toFixed(3)})...`
                    : translateCropText(zoneTitle, lang)}
              </Text>
              <ChevronDown size={15} color={COLORS.inkOnDarkMuted} />
            </TouchableOpacity>

            {hasLocatedParcel && (
              <TouchableOpacity
                onPress={onRequestGps}
                disabled={isLocatingGps}
                style={styles.gpsMiniBtn}
                activeOpacity={0.8}
              >
                <Navigation size={13} color={COLORS.forestDeep} />
                <Text style={styles.gpsMiniText}>
                  {isLocatingGps ? "..." : isQu ? "GPS-niy" : "Mi GPS"}
                </Text>
              </TouchableOpacity>
            )}
          </View>

          {!hasLocatedParcel ? (
            <View style={styles.unlocatedHeroBox}>
              <Text style={styles.unlocatedHeroTitle}>
                {isQu
                  ? "Chakraykita tariy qallarinapaq"
                  : "Ubica tu chacra para consultar el satélite"}
              </Text>
              <Text style={styles.unlocatedHeroSub}>
                {isQu
                  ? "GPS-niykita ñitiy, llaqtaykita maskay utaq rimayllawan willaway."
                  : "Usa tu GPS, busca tu sector en el mapa o háblale al asistente agronómico para conectar el clima, la altitud y el suelo de tu parcela."}
              </Text>
              <View style={styles.unlocatedHeroActions}>
                <TouchableOpacity
                  onPress={onRequestGps}
                  disabled={isLocatingGps}
                  style={styles.unlocatedPrimaryBtn}
                  activeOpacity={0.88}
                >
                  <Navigation size={15} color={COLORS.forestDeep} />
                  <Text style={styles.unlocatedPrimaryBtnText}>
                    {isLocatingGps ? "Ubicando..." : "Usar mi GPS actual"}
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity
                  onPress={() => setZoneModalOpen(true)}
                  style={styles.unlocatedSecondaryBtn}
                  activeOpacity={0.88}
                >
                  <Search size={15} color={COLORS.limeBright} />
                  <Text style={styles.unlocatedSecondaryBtnText}>
                    Buscar mi sector
                  </Text>
                </TouchableOpacity>
              </View>
            </View>
          ) : (
            <>
              {/* Big Live Temperature + Cloud Illustration + Weather Condition */}
              <View style={styles.weatherCenterRow}>
                <View style={styles.tempBlock}>
                  <Text style={styles.bigTempText}>
                    {liveTempC.toFixed(0)}°C
                  </Text>
                  <Text style={styles.tempRangeText}>
                    {isQu ? "Pisi" : "Mín"} {liveMinTempC.toFixed(1)}°C ·{" "}
                    {isQu ? "Sayay" : "Altitud"} {Math.round(terrain.elevation_m)} m
                  </Text>
                </View>

                <View style={styles.weatherRightBlock}>
                  <WeatherCloudSvg
                    frostRisk={frostRiskLevel}
                    weatherType={bioSummary.current_weather_type}
                  />
                  <Text style={styles.weatherConditionText} numberOfLines={2}>
                    {translateCropText(liveWeatherLabel, lang)}
                  </Text>
                  <Text style={styles.nasaSourceSub} numberOfLines={2}>
                    {translateCropText(liveWeatherSource, lang)}
                  </Text>
                </View>
              </View>

              {/* 3-Column Bottom Strip: Humedad | Lluvia | Helada */}
              <View style={styles.weatherMetricsRow}>
                <View style={styles.weatherMetricCol}>
                  <Text style={styles.weatherMetricLabel}>
                    {lang === "qu" ? "Allpa Unu" : "Humedad Suelo"}
                  </Text>
                  <Text style={styles.weatherMetricVal}>
                    {soilMoisturePct !== null ? `${soilMoisturePct}%` : "--"}
                  </Text>
                </View>

                <View style={styles.weatherMetricDivider} />

                <View style={styles.weatherMetricCol}>
                  <Text style={styles.weatherMetricLabel}>
                    {lang === "qu" ? "Wata Para" : "Lluvia Anual"}
                  </Text>
                  <Text style={styles.weatherMetricVal}>
                    {climateSummary.annual_precip_mm} mm
                  </Text>
                </View>

                <View style={styles.weatherMetricDivider} />

                <View style={styles.weatherMetricCol}>
                  <Text style={styles.weatherMetricLabel}>
                    {lang === "qu" ? "Qasa Chiki" : "Riesgo Helada"}
                  </Text>
                  <Text
                    style={[
                      styles.weatherMetricVal,
                      frostRiskLevel === "Alto" && {
                        color: "#FCA5A5",
                      },
                    ]}
                  >
                    {frostRiskLabel}
                  </Text>
                </View>
              </View>

              {(result.biophysical.forecast_7d?.length ?? 0) > 0 && (
                <View style={styles.forecastStripWrap}>
                  <View style={styles.forecastStripHeader}>
                    <Text style={styles.forecastStripTitle}>
                      {isQu ? "Qhipa 7 p'unchaw · Open-Meteo" : "Próximos 7 días · Open-Meteo"}
                      {typeof bioSummary.next_7d_precip_mm === "number"
                        ? ` (${bioSummary.next_7d_precip_mm.toFixed(0)} mm)`
                        : ""}
                    </Text>
                    {bioSummary.frost_alert_7d && (
                      <View style={styles.forecastFrostPill}>
                        <Text style={styles.forecastFrostPillText}>
                          {isQu
                            ? `Qasa <= ${bioSummary.next_7d_min_temp_c?.toFixed(0) ?? 3}°C`
                            : `Alerta helada (${bioSummary.next_7d_min_temp_c?.toFixed(1) ?? "3.0"}°C)`}
                        </Text>
                      </View>
                    )}
                  </View>
                  <ScrollView
                    horizontal
                    showsHorizontalScrollIndicator={false}
                    contentContainerStyle={styles.forecastDaysRow}
                  >
                    {result.biophysical.forecast_7d!.map((day, idx) => {
                      const dNames = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
                      const dObj = new Date(`${day.date}T12:00:00Z`);
                      const dayLabel =
                        idx === 0
                          ? isQu ? "Kunan" : "Hoy"
                          : Number.isNaN(dObj.getTime())
                            ? day.date.slice(5)
                            : dNames[dObj.getUTCDay()];
                      const isDayFrost = day.temp_min_c <= 3.0;
                      return (
                        <View
                          key={day.date}
                          style={[
                            styles.forecastDayCell,
                            isDayFrost && styles.forecastDayCellFrost,
                          ]}
                        >
                          <Text style={styles.forecastDayName}>{dayLabel}</Text>
                          <Text style={styles.forecastDayTemp}>
                            {Math.round(day.temp_max_c)}° / {Math.round(day.temp_min_c)}°
                          </Text>
                          <Text style={styles.forecastDayRain}>
                            {day.precip_mm >= 0.5 ? `${day.precip_mm.toFixed(0)} mm` : "Seco"}
                          </Text>
                        </View>
                      );
                    })}
                  </ScrollView>
                </View>
              )}
            </>
          )}
        </ImageBackground>
      </View>

      {/* BODY CONTENT ON WARM SAGE CANVAS */}
      <View style={styles.bodyPadding}>
        {/* PROMINENT 1-TAP VOICE COMPANION CARD */}
        <TouchableOpacity
          onPress={onOpenVoiceModal}
          style={styles.voiceCompanionBanner}
          activeOpacity={0.88}
        >
          <View style={styles.voiceMicCircle}>
            <Mic size={22} color={COLORS.forestDeep} strokeWidth={2.5} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.voiceBannerTitle}>
              {lang === "qu"
                ? "¿Rimayllawanchu tapuyta munanki?"
                : "¿Prefieres hablar en vez de tocar botones?"}
            </Text>
            <Text style={styles.voiceBannerSub}>
              {lang === "qu"
                ? "Kayta ñit'iy hinaspa chakraykimanta willaway."
                : !farmerConfirmedInputs
                  ? "Toca aquí: dime dónde está tu chacra, si tienes riego o tus semillas."
                  : "Toca aquí para ajustar tu lugar, agua o semillas disponibles."}
            </Text>
          </View>
          <View style={styles.voiceArrowCircle}>
            <ArrowRight size={17} color={COLORS.limeBright} />
          </View>
        </TouchableOpacity>

        {/* 6-SLOT INTERACTIVE CALIBRATION GUIDE (ONLY FULL SLOTS ONCE PARCEL LOCATED) */}
        <ParcelCalibrationChecklist
          hasLocatedParcel={hasLocatedParcel}
          isPlanReady={isPlanReady}
          completedChecklistCount={completedChecklistCount}
          voiceSlots={voiceSlots}
          zoneTitle={zoneTitle}
          terrain={terrain}
          liveMinTempC={liveMinTempC}
          frostRiskLabel={frostRiskLabel}
          equipmentAccess={equipmentAccess}
          onChangeEquipment={onChangeEquipment}
          onNavigateTab={onNavigateTab}
          onSelectChecklistOption={onSelectChecklistOption}
          onForceCalculatePlan={onForceCalculatePlan}
        />

        {hasLocatedParcel && isPlanReady && (
        <>
        {/* FARMER PRIORITIES PILL BAR ("My Fields / Priorities" from Image 1) */}
        <View style={styles.sectionHeaderRow}>
          <Text style={styles.sectionTitle}>
            {lang === "qu"
              ? "¿Imatataq chakraykipaq maskanki?"
              : "¿Qué prioriza tu chacra hoy?"}
          </Text>
          <TouchableOpacity onPress={() => onNavigateTab("mapa")}>
            <Text style={styles.seeAllLink}>
              {isQu ? "Mapapi qhaway" : "Ver en Mapa"}
            </Text>
          </TouchableOpacity>
        </View>

        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.pillsScroll}
        >
          {PRIORITY_PILLS.map((pill) => {
            const active = selectedPreset === pill.id;
            return (
              <TouchableOpacity
                key={pill.id}
                onPress={() => {
                  setSelectedPreset(pill.id);
                  if (onSelectPriorityPreset) {
                    onSelectPriorityPreset(pill.id, pill.weights);
                  } else {
                    onChangePriorities(pill.weights);
                  }
                }}
                style={[styles.categoryPill, active && styles.categoryPillActive]}
                activeOpacity={0.8}
              >
                <Text
                  style={[
                    styles.categoryPillText,
                    active && styles.categoryPillTextActive,
                  ]}
                >
                  {lang === "qu" ? pill.labelQu : pill.labelEs}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>

        {/* MAIN VISUAL FEATURE CARD: RECOMMENDED 2-YEAR ROTATION */}
        <TouchableOpacity
          activeOpacity={0.92}
          onPress={() => onNavigateTab("plan")}
          style={styles.featuredFieldCard}
        >
          <View style={styles.featuredArtworkWrap}>
            <FieldLandscapeSvg accentColor={COLORS.limeAccent} />
            <View style={styles.featuredOverlayTop}>
              <View style={styles.featuredTagPill}>
                <Sparkles size={13} color={COLORS.forestDeep} />
                <Text style={styles.featuredTagText}>
                  {isQu ? "ALLIN PLAN 2026–2027" : "PLAN RECOMENDADO 2026–2027"}
                </Text>
              </View>
              <View style={styles.scoreBadge}>
                <Text style={styles.scoreBadgeText}>
                  {recommendedStrat.mcda_score.toFixed(0)}%{" "}
                  {isQu ? "Tupaq" : "Compatible"}
                </Text>
              </View>
            </View>
            <View style={styles.featuredOverlayBottom}>
              <Text style={styles.featuredCardHeroTitle}>
                {translateCropText(recommendedStrat.title, lang)}
              </Text>
            </View>
          </View>

          <View style={styles.featuredCardBody}>
            {isAnalyzing && (
              <View style={styles.recalcBanner}>
                <ActivityIndicator size="small" color={COLORS.agroPrimary} />
                <Text style={styles.recalcBannerText}>
                  {isQu
                    ? "Musuq prioridadwan wakichichkan..."
                    : "Actualizando rotación y cultivos según tu prioridad..."}
                </Text>
              </View>
            )}
            <Text style={styles.featuredDescription}>
              {translateCropText(recommendedStrat.subtitle, lang)}
            </Text>

            {/* 4-Campaign Visual Sequence */}
            <View style={styles.sequenceRow}>
              {recommendedStrat.phases.map((ph, idx) => (
                <View key={idx} style={styles.sequenceStep}>
                  <View
                    style={[styles.sequenceDot, { backgroundColor: ph.color }]}
                  />
                  <View style={{ flex: 1 }}>
                    <Text style={styles.sequencePeriod}>
                      {translateCropText(ph.period, lang)}
                    </Text>
                    <Text style={styles.sequenceCrop} numberOfLines={1}>
                      {translateCropText(ph.crop_name, lang)}
                    </Text>
                  </View>
                </View>
              ))}
            </View>

            {/* Pocketbook Economics + Comparison vs Monoculture */}
            <View style={styles.featuredMetricsStrip}>
              <View style={styles.featuredMetricBox}>
                <Coins size={15} color={COLORS.agroPrimary} />
                <View>
                  <Text style={styles.featuredMetricLbl}>
                    {isQu ? "2 Wata Ganancia" : "Ganancia 2 años"}
                  </Text>
                  <Text style={styles.featuredMetricVal}>
                    S/{" "}
                    {(
                      recommendedStrat.metrics.net_margin_2yr_soles_ha ?? 0
                    ).toLocaleString("es-PE")}
                    /ha
                  </Text>
                </View>
              </View>

              <View style={styles.featuredMetricBox}>
                <ShieldCheck size={15} color={COLORS.agroPrimary} />
                <View>
                  <Text style={styles.featuredMetricLbl}>
                    {isQu ? "Muhu Chanin" : "Costo Semilla"}
                  </Text>
                  <Text style={styles.featuredMetricVal}>
                    S/{" "}
                    {(
                      recommendedStrat.metrics.seed_cost_2yr_soles_ha ?? 0
                    ).toLocaleString("es-PE")}
                    /ha
                  </Text>
                </View>
              </View>
            </View>

            {/* CTA bar */}
            <View style={styles.greenCtaBar}>
              <View style={styles.greenCtaIconCircle}>
                <ArrowRight size={16} color="#FFFFFF" />
              </View>
              <Text style={styles.greenCtaText}>
                {lang === "qu"
                  ? "3 muyuy tarpuykunata qhaway"
                  : "Comparar las 3 opciones de rotación"}
              </Text>
              <Text style={styles.greenCtaChevrons}>{">>>"}</Text>
            </View>
          </View>
        </TouchableOpacity>

        {/* VULNERABILITY & IMMEDIATE SEASONAL ADVICE CARD */}
        {result.seasonal_context && (
          <View style={styles.adviceCard}>
            <View style={styles.adviceHeader}>
              <View style={styles.adviceIconWrap}>
                <Calendar size={18} color={COLORS.agroPrimary} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.adviceOverline}>
                  {isQu ? "KAY KILLA YUYAYCHAY · " : "CONSEJO PARA ESTE MES · "}
                  {translateCropText(
                    result.seasonal_context.reference_month_label,
                    lang
                  ).toUpperCase()}
                </Text>
                <Text style={styles.adviceTitle}>
                  {isQu
                    ? "¿Imatam kunan chakraykipi ruwanki?"
                    : "¿Qué hacer ahora en tu terreno?"}
                </Text>
              </View>
            </View>
            <Text style={styles.adviceBodyText}>
              {translateCropText(result.seasonal_context.immediate_action, lang)}
            </Text>

            {baselineStrat.vulnerability_score >= 50 && (
              <View style={styles.vulnAlertBox}>
                <ShieldAlert size={16} color={COLORS.amberFinance} />
                <Text style={styles.vulnAlertText}>
                  <Text style={{ fontWeight: "700" }}>
                    {isQu
                      ? "Kikin murullata sapa wata tarpuptiykiqa: "
                      : "Atención con repetir el mismo cultivo: "}
                  </Text>
                  {isQu
                    ? `Mana muyuptinqa chiki ${baselineStrat.vulnerability_score.toFixed(0)}/100 kasqanmi, allpa pisipan hinallataq kuru mirarin.`
                    : `Seguir sin rotar tiene una vulnerabilidad de ${baselineStrat.vulnerability_score.toFixed(0)}/100 por desgaste de nutrientes, plagas acumuladas y estrés de agua.`}
                </Text>
              </View>
            )}
          </View>
        )}
        </>
        )}

        {/* HORIZONTAL CROP CARDS WITH REAL PLANT IMAGES (ONLY ONCE PARCEL IS LOCATED) */}
        {hasLocatedParcel && (
        <>
        <View style={styles.sectionHeaderRow}>
          <Text style={styles.sectionTitle}>
            {lang === "qu"
              ? "Chakraykipaq Allin Muhukuna"
              : "Semillas recomendadas para tu altura"}
          </Text>
          <TouchableOpacity onPress={() => onNavigateTab("semillas")}>
            <Text style={styles.seeAllLink}>
              {isQu ? "Llapan 24 qhaway" : "Ver las 24"}
            </Text>
          </TouchableOpacity>
        </View>

        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.cropsCarousel}
        >
          {suitedCrops.map((crop) => (
            <TouchableOpacity
              key={crop.id}
              activeOpacity={0.88}
              onPress={() => onNavigateTab("semillas")}
              style={styles.cropVisualCard}
            >
              <View
                style={[
                  styles.cropVisualBanner,
                  { backgroundColor: crop.color || COLORS.agroPrimary },
                ]}
              >
                <View style={styles.cropCyclePill}>
                  <Text style={styles.cropCyclePillText}>
                    {crop.cycle_months} {isQu ? "killa" : "meses"}
                  </Text>
                </View>
                <CropPlantImage
                  cropId={crop.id}
                  accentColor={crop.color || COLORS.agroPrimary}
                  size={60}
                  borderRadius={14}
                />
              </View>

              <View style={styles.cropVisualBody}>
                <Text style={styles.cropVisualTitle} numberOfLines={1}>
                  {translateCropText(crop.name, lang)}
                </Text>
                <Text style={styles.cropVisualSub} numberOfLines={2}>
                  {translateCropText(
                    crop.consumer_benefit || crop.market_note,
                    lang
                  )}
                </Text>

                <View style={styles.cropMiniStats}>
                  <View style={styles.cropMiniChip}>
                    <Droplets size={12} color={COLORS.nasaCobalt} />
                    <Text style={styles.cropMiniText}>
                      {crop.water_req_mm} mm
                    </Text>
                  </View>
                  <View style={styles.cropMiniChip}>
                    <Snowflake size={12} color={COLORS.agroPrimary} />
                    <Text style={styles.cropMiniText}>
                      {crop.frost_critical_c}°C
                    </Text>
                  </View>
                </View>

                {crop.net_margin_soles_ha !== undefined && (
                  <Text style={styles.cropProfitTag}>
                    {isQu ? "Ganancia" : "Ganancia"}: S/{" "}
                    {crop.net_margin_soles_ha.toLocaleString("es-PE")}/ha
                  </Text>
                )}
              </View>
            </TouchableOpacity>
          ))}
        </ScrollView>
        </>
        )}
      </View>

      {/* MODAL DE SELECCIÓN DE CHACRA / LOCALIDAD */}
      <HomeZonePickerModal
        visible={zoneModalOpen}
        onClose={() => setZoneModalOpen(false)}
        lang={lang}
        referenceData={referenceData}
        onSelectBeacon={onSelectBeacon}
        onSelectLocation={onSelectLocation}
      />
    </ScrollView>
  );
};

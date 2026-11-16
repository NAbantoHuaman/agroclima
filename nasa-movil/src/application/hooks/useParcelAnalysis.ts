import { useCallback, useEffect, useRef, useState } from "react";
import * as Location from "expo-location";
import { Alert } from "react-native";
import { SafeHaptics as Haptics } from "../../utils/safeHaptics";
import {
  GOAL_MARKET_MAP,
  GOAL_PRIORITY_PRESETS,
  INITIAL_PARAMS,
} from "../../domain/agronomy/constants";
import {
  buildDefault1HaSquare,
  computePolygonCentroid,
} from "../../domain/map/geometry";
import {
  requestRecommendations,
  requestReferenceData,
} from "../../services/apiClient";
import type {
  BeaconParcel,
  ClimateScenario,
  CurrentCropId,
  EquipmentAccess,
  FarmerSoilNotes,
  MarketPreference,
  PriorityWeights,
  RecommendResponse,
  ReferenceDataResponse,
  VoiceConfirmedSlots,
  WaterAvailability,
} from "../../types";

export type AppTab = "inicio" | "mapa" | "plan" | "semillas";

export function useParcelAnalysis(onNavigateTab: (tab: AppTab) => void) {
  const [activePoint, setActivePoint] = useState({
    lat: INITIAL_PARAMS.lat,
    lon: INITIAL_PARAMS.lon,
  });
  const [parcelId, setParcelId] = useState<string | null>(
    INITIAL_PARAMS.parcelId
  );
  const [customPolygon, setCustomPolygon] = useState<[number, number][] | null>(
    null
  );
  const [currentCrop, setCurrentCrop] = useState<CurrentCropId>(
    INITIAL_PARAMS.currentCrop
  );
  const [waterAvailability, setWaterAvailability] = useState<WaterAvailability>(
    INITIAL_PARAMS.waterAvailability
  );
  const [priorities, setPriorities] = useState<PriorityWeights>(
    INITIAL_PARAMS.priorities
  );
  const [climateScenario, setClimateScenario] = useState<ClimateScenario>(
    INITIAL_PARAMS.climateScenario
  );
  const [farmerSoil, setFarmerSoil] = useState<FarmerSoilNotes>(
    INITIAL_PARAMS.farmerSoil
  );
  const [equipmentAccess, setEquipmentAccess] =
    useState<EquipmentAccess>("manual_yunta");
  const [marketPreference, setMarketPreference] =
    useState<MarketPreference>("autoconsumo_feria");
  const [availableSeeds, setAvailableSeeds] = useState<string[]>([]);
  const [customZoneLabel, setCustomZoneLabel] = useState<string | null>(null);
  const [gpsCoords, setGpsCoords] = useState<{ lat: number; lon: number } | null>(
    null
  );
  const [voiceSlots, setVoiceSlots] = useState<VoiceConfirmedSlots>({});
  const [farmerConfirmedInputs, setFarmerConfirmedInputs] = useState(false);

  const [result, setResult] = useState<RecommendResponse | null>(null);
  const [explorerPreviewResult, setExplorerPreviewResult] =
    useState<RecommendResponse | null>(null);
  const [referenceData, setReferenceData] =
    useState<ReferenceDataResponse | null>(null);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isLocatingGps, setIsLocatingGps] = useState(false);
  const analysisSeqRef = useRef(0);

  const hasLocatedParcel = Boolean(voiceSlots.location_confirmed);
  const completedChecklistCount = [
    Boolean(voiceSlots.location_confirmed && voiceSlots.map_verified),
    Boolean(voiceSlots.water_confirmed),
    Boolean(voiceSlots.crop_confirmed),
    Boolean(voiceSlots.soil_confirmed),
    Boolean(voiceSlots.climate_risk_confirmed),
    Boolean(voiceSlots.goal_confirmed || voiceSlots.seeds_checked),
  ].filter(Boolean).length;

  const runAnalysis = useCallback(
    async (overrides?: {
      lat?: number;
      lon?: number;
      parcelId?: string | null;
      polygon?: [number, number][] | null;
      currentCrop?: CurrentCropId;
      waterAvailability?: WaterAvailability;
      priorities?: PriorityWeights;
      climateScenario?: ClimateScenario;
      farmerSoil?: FarmerSoilNotes;
      equipmentAccess?: EquipmentAccess;
      marketPreference?: MarketPreference;
      availableSeeds?: string[];
      customZoneLabel?: string | null;
    }) => {
      const reqSeq = ++analysisSeqRef.current;
      setIsAnalyzing(true);
      const payload = {
        lat: overrides?.lat ?? activePoint.lat,
        lon: overrides?.lon ?? activePoint.lon,
        parcel_id:
          overrides !== undefined && "parcelId" in overrides
            ? overrides.parcelId
            : parcelId,
        polygon:
          overrides !== undefined && "polygon" in overrides
            ? overrides.polygon
            : customPolygon,
        current_crop: overrides?.currentCrop ?? currentCrop,
        water_availability: overrides?.waterAvailability ?? waterAvailability,
        priorities: overrides?.priorities ?? priorities,
        climate_scenario: overrides?.climateScenario ?? climateScenario,
        farmer_soil: overrides?.farmerSoil ?? farmerSoil,
        equipment_access: overrides?.equipmentAccess ?? equipmentAccess,
        market_preference: overrides?.marketPreference ?? marketPreference,
        field_status: "auto" as const,
        available_seeds:
          overrides !== undefined && "availableSeeds" in overrides
            ? overrides.availableSeeds
            : availableSeeds,
        custom_zone_label:
          overrides !== undefined && "customZoneLabel" in overrides
            ? overrides.customZoneLabel
            : customZoneLabel,
      };

      try {
        setBackendError(null);
        const res = await requestRecommendations(payload);
        if (reqSeq !== analysisSeqRef.current) return;
        setResult(res.data);
      } catch (err) {
        if (reqSeq !== analysisSeqRef.current) return;
        const msg =
          err instanceof Error ? err.message : "Sin conexión temporal.";
        setBackendError(msg);
      } finally {
        if (reqSeq === analysisSeqRef.current) {
          setIsAnalyzing(false);
        }
      }
    },
    [
      activePoint.lat,
      activePoint.lon,
      parcelId,
      customPolygon,
      currentCrop,
      waterAvailability,
      priorities,
      climateScenario,
      farmerSoil,
      equipmentAccess,
      marketPreference,
      availableSeeds,
      customZoneLabel,
    ]
  );

  const bootstrapBackendData = useCallback(async () => {
    setIsBootstrapping(true);
    setBackendError(null);
    try {
      let targetLat = activePoint.lat;
      let targetLon = activePoint.lon;
      try {
        const perm = await Location.getForegroundPermissionsAsync();
        if (perm.status === "granted") {
          const pos = await Location.getCurrentPositionAsync({
            accuracy: Location.Accuracy.Balanced,
          });
          const { latitude, longitude } = pos.coords;
          const inPeru =
            latitude <= 0.2 &&
            latitude >= -18.6 &&
            longitude >= -81.6 &&
            longitude <= -68.4;
          if (inPeru) {
            targetLat = latitude;
            targetLon = longitude;
            setGpsCoords({ lat: latitude, lon: longitude });
            setActivePoint({ lat: latitude, lon: longitude });
          }
        }
      } catch {
        // Keep selected point if GPS isn't available yet
      }

      const [refRes] = await Promise.all([
        requestReferenceData(),
        runAnalysis({
          lat: targetLat,
          lon: targetLon,
          parcelId,
          polygon: customPolygon,
          customZoneLabel,
        }),
      ]);
      setReferenceData(refRes.data);
    } catch {
      // Keep waiting cleanly without exposing technical messages while loading
    } finally {
      setIsBootstrapping(false);
    }
  }, []);

  useEffect(() => {
    void bootstrapBackendData();
  }, [bootstrapBackendData]);

  useEffect(() => {
    if (result || isBootstrapping || isAnalyzing) {
      return;
    }
    const timer = setTimeout(() => {
      void bootstrapBackendData();
    }, 2500);
    return () => clearTimeout(timer);
  }, [result, isBootstrapping, isAnalyzing, bootstrapBackendData]);

  const applyLocationSelection = (
    lat: number,
    lon: number,
    nextParcelId: string | null,
    label: string,
    opts?: { skipOpenMapConfirm?: boolean; markMapVerified?: boolean }
  ) => {
    const sq = buildDefault1HaSquare(lat, lon);
    setActivePoint({ lat, lon });
    setParcelId(nextParcelId);
    setCustomPolygon(sq);
    setCustomZoneLabel(label);
    setExplorerPreviewResult(null);
    setVoiceSlots((prev) => ({
      ...prev,
      location_confirmed: true,
      map_verified: Boolean(opts?.markMapVerified),
      location_label: label,
      lat,
      lon,
    }));
    void runAnalysis({
      lat,
      lon,
      parcelId: nextParcelId,
      polygon: sq,
      customZoneLabel: label,
    });
    if (!opts?.skipOpenMapConfirm) {
      onNavigateTab("mapa");
    }
  };

  const handleRequestGps = async () => {
    setIsLocatingGps(true);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    try {
      const perm = await Location.requestForegroundPermissionsAsync();
      if (perm.status !== "granted") {
        Alert.alert(
          "Permiso GPS",
          "Activa el permiso de ubicación para localizar tu chacra con precisión satelital."
        );
        return;
      }
      const pos = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });
      const { latitude, longitude } = pos.coords;
      const inPeru =
        latitude <= 0.2 &&
        latitude >= -18.6 &&
        longitude >= -81.6 &&
        longitude <= -68.4;
      if (!inPeru) {
        Alert.alert(
          "GPS fuera de cobertura Perú",
          `Tu ubicación actual (${latitude.toFixed(2)}, ${longitude.toFixed(
            2
          )}) está fuera del área agrícola soportada.`
        );
        return;
      }
      setGpsCoords({ lat: latitude, lon: longitude });
      applyLocationSelection(latitude, longitude, null, "Mi ubicación GPS");
    } catch {
      Alert.alert("GPS", "No se pudo obtener la ubicación del celular.");
    } finally {
      setIsLocatingGps(false);
    }
  };

  const handleSelectBeacon = (
    beacon: BeaconParcel,
    opts?: { skipOpenMapConfirm?: boolean }
  ) => {
    Haptics.selectionAsync();
    applyLocationSelection(beacon.lat, beacon.lon, beacon.id, beacon.name, opts);
  };

  const handleSelectLocation = (
    lat: number,
    lon: number,
    nextParcelId: string | null,
    nextCustomLabel?: string | null,
    opts?: { skipOpenMapConfirm?: boolean }
  ) => {
    Haptics.selectionAsync();
    const resolvedLabel =
      nextCustomLabel || `Parcela (${lat.toFixed(4)}, ${lon.toFixed(4)})`;
    applyLocationSelection(lat, lon, nextParcelId, resolvedLabel, opts);
  };

  const handleConfirmParcelPolygon = (returnToHome = true) => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    setVoiceSlots((prev) => ({
      ...prev,
      location_confirmed: true,
      map_verified: true,
      lat: activePoint.lat,
      lon: activePoint.lon,
    }));
    if (returnToHome) {
      onNavigateTab("inicio");
    }
  };

  const handleSelectChecklistOption = (
    slotKey: "water" | "crop" | "soil" | "climate" | "goal",
    optionId: string,
    label: string
  ) => {
    Haptics.selectionAsync();
    setExplorerPreviewResult(null);
    if (slotKey === "water") {
      const nextWater = optionId as WaterAvailability;
      setWaterAvailability(nextWater);
      setVoiceSlots((prev) => ({
        ...prev,
        water_confirmed: true,
        water_label: label,
      }));
      void runAnalysis({ waterAvailability: nextWater });
      return;
    }
    if (slotKey === "crop") {
      const nextCrop = optionId as CurrentCropId;
      setCurrentCrop(nextCrop);
      setVoiceSlots((prev) => ({
        ...prev,
        crop_confirmed: true,
        crop_label: label,
      }));
      void runAnalysis({ currentCrop: nextCrop });
      return;
    }
    if (slotKey === "soil") {
      const nextSoil: FarmerSoilNotes = {
        ...farmerSoil,
        texture_override:
          optionId === "satelite"
            ? "auto"
            : (optionId as FarmerSoilNotes["texture_override"]),
      };
      setFarmerSoil(nextSoil);
      setVoiceSlots((prev) => ({
        ...prev,
        soil_confirmed: true,
        soil_label: label,
      }));
      void runAnalysis({ farmerSoil: nextSoil });
      return;
    }
    if (slotKey === "climate") {
      const isFrost = optionId === "heladas";
      const nextSoil: FarmerSoilNotes = {
        ...farmerSoil,
        local_frost_early: isFrost,
      };
      const nextScenario: ClimateScenario =
        optionId === "irregular"
          ? {
              ...climateScenario,
              rain_delta_pct: Math.min(climateScenario.rain_delta_pct, -15),
              apply_20yr_projection: true,
            }
          : optionId === "heladas"
            ? {
                ...climateScenario,
                frost_frequency: "severa",
              }
            : climateScenario;
      setFarmerSoil(nextSoil);
      setClimateScenario(nextScenario);
      setVoiceSlots((prev) => ({
        ...prev,
        climate_risk_confirmed: true,
        climate_risk_label: label,
      }));
      void runAnalysis({
        farmerSoil: nextSoil,
        climateScenario: nextScenario,
      });
      return;
    }
    if (slotKey === "goal") {
      const nextPrio = GOAL_PRIORITY_PRESETS[optionId] ?? GOAL_PRIORITY_PRESETS.suelo;
      const nextMarket: MarketPreference =
        GOAL_MARKET_MAP[optionId] ?? "grano_comercial";
      setPriorities(nextPrio);
      setMarketPreference(nextMarket);
      setVoiceSlots((prev) => ({
        ...prev,
        goal_confirmed: true,
        seeds_checked: true,
        goal_label: label,
      }));
      void runAnalysis({ priorities: nextPrio, marketPreference: nextMarket });
    }
  };

  const handleForceCalculatePlan = () => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    setExplorerPreviewResult(null);
    setFarmerConfirmedInputs(true);
    void runAnalysis();
  };

  const handleSaveExploredAsMyChacra = (
    lat: number,
    lon: number,
    label: string,
    simRes?: RecommendResponse | null
  ) => {
    const sq = buildDefault1HaSquare(lat, lon);
    setActivePoint({ lat, lon });
    setParcelId(null);
    setCustomPolygon(sq);
    setCustomZoneLabel(label);
    setExplorerPreviewResult(null);
    if (simRes) {
      setResult(simRes);
    } else {
      void runAnalysis({
        lat,
        lon,
        parcelId: null,
        polygon: sq,
        customZoneLabel: label,
      });
    }
    setVoiceSlots((prev) => ({
      ...prev,
      location_confirmed: true,
      map_verified: true,
      location_label: label,
      lat,
      lon,
    }));
  };

  const handleSelectMapPoint = (
    lat: number,
    lon: number,
    label?: string | null
  ) => {
    const sq = buildDefault1HaSquare(lat, lon);
    const explicitLabel = label && label.trim() ? label.trim() : null;
    const slotLabel =
      explicitLabel || `Parcela (${lat.toFixed(4)}, ${lon.toFixed(4)})`;
    setExplorerPreviewResult(null);
    setActivePoint({ lat, lon });
    setParcelId(null);
    setCustomPolygon(sq);
    setCustomZoneLabel(explicitLabel);
    setVoiceSlots((prev) => ({
      ...prev,
      location_confirmed: true,
      location_label: slotLabel,
      lat,
      lon,
    }));
    void runAnalysis({
      lat,
      lon,
      parcelId: null,
      polygon: sq,
      customZoneLabel: explicitLabel,
    });
  };

  const handleSetPolygon = (poly: [number, number][] | null) => {
    setExplorerPreviewResult(null);
    setCustomPolygon(poly);
    if (poly && poly.length >= 3) {
      const { lat: cLat, lon: cLon } = computePolygonCentroid(poly);
      setActivePoint({ lat: cLat, lon: cLon });
      setParcelId(null);
      setVoiceSlots((prev) => ({
        ...prev,
        location_confirmed: true,
        map_verified: true,
        lat: cLat,
        lon: cLon,
      }));
      void runAnalysis({
        lat: cLat,
        lon: cLon,
        parcelId: null,
        polygon: poly,
        customZoneLabel,
      });
    } else {
      void runAnalysis({ polygon: poly });
    }
  };

  const handleChangeCrop = (c: CurrentCropId) => {
    setExplorerPreviewResult(null);
    setCurrentCrop(c);
    setVoiceSlots((prev) => ({
      ...prev,
      crop_confirmed: true,
      crop_label: c,
    }));
    void runAnalysis({ currentCrop: c });
  };

  const handleChangeWater = (w: WaterAvailability) => {
    Haptics.selectionAsync();
    setExplorerPreviewResult(null);
    setWaterAvailability(w);
    setVoiceSlots((prev) => ({
      ...prev,
      water_confirmed: true,
      water_label: w,
    }));
    void runAnalysis({ waterAvailability: w });
  };

  const handleChangePriorities = (
    p: PriorityWeights,
    opts?: { markGoalSlot?: boolean }
  ) => {
    Haptics.selectionAsync();
    setExplorerPreviewResult(null);
    setPriorities(p);
    if (opts?.markGoalSlot) {
      setVoiceSlots((prev) => ({
        ...prev,
        goal_confirmed: true,
        seeds_checked: true,
      }));
    }
    void runAnalysis({ priorities: p });
  };

  const handleChangeFarmerSoil = (s: FarmerSoilNotes) => {
    setExplorerPreviewResult(null);
    setFarmerSoil(s);
    setVoiceSlots((prev) => ({
      ...prev,
      soil_confirmed: true,
      climate_risk_confirmed: true,
      soil_label:
        s.texture_override === "auto"
          ? "Dato satelital SoilGrids"
          : s.texture_override,
      climate_risk_label: s.local_frost_early
        ? "Helada temprana"
        : "Dato satelital NASA",
    }));
    void runAnalysis({ farmerSoil: s });
  };

  const handleChangeScenario = (next: ClimateScenario) => {
    setClimateScenario(next);
    void runAnalysis({ climateScenario: next });
  };

  const handleChangeEquipment = (eq: EquipmentAccess) => {
    Haptics.selectionAsync();
    setExplorerPreviewResult(null);
    setEquipmentAccess(eq);
    void runAnalysis({ equipmentAccess: eq });
  };

  const handleSelectPriorityPreset = (
    presetId: string,
    weights: PriorityWeights
  ) => {
    Haptics.selectionAsync();
    setExplorerPreviewResult(null);
    setPriorities(weights);
    if (presetId === "mercado") {
      setMarketPreference("grano_comercial");
      setVoiceSlots((prev) => ({
        ...prev,
        goal_confirmed: true,
        seeds_checked: true,
        goal_label: "Venta en mercado / Mayor ganancia",
      }));
      void runAnalysis({ priorities: weights, marketPreference: "grano_comercial" });
      return;
    }
    void runAnalysis({ priorities: weights });
  };

  const zoneName =
    result?.terrain?.zone_name ||
    customZoneLabel ||
    `Parcela (${activePoint.lat.toFixed(3)}, ${activePoint.lon.toFixed(3)})`;

  return {
    activePoint,
    setActivePoint,
    gpsCoords,
    parcelId,
    setParcelId,
    customPolygon,
    setCustomPolygon,
    currentCrop,
    setCurrentCrop,
    waterAvailability,
    setWaterAvailability,
    priorities,
    setPriorities,
    climateScenario,
    farmerSoil,
    setFarmerSoil,
    equipmentAccess,
    setEquipmentAccess,
    marketPreference,
    setMarketPreference,
    availableSeeds,
    setAvailableSeeds,
    customZoneLabel,
    setCustomZoneLabel,
    voiceSlots,
    setVoiceSlots,
    farmerConfirmedInputs,
    setFarmerConfirmedInputs,
    result,
    setResult,
    explorerPreviewResult,
    setExplorerPreviewResult,
    referenceData,
    backendError,
    setBackendError,
    isAnalyzing,
    isLocatingGps,
    hasLocatedParcel,
    completedChecklistCount,
    zoneName,
    runAnalysis,
    handleRequestGps,
    handleSelectBeacon,
    handleSelectLocation,
    handleConfirmParcelPolygon,
    handleSelectChecklistOption,
    handleForceCalculatePlan,
    handleSaveExploredAsMyChacra,
    handleSelectMapPoint,
    handleSetPolygon,
    handleChangeCrop,
    handleChangeWater,
    handleChangePriorities,
    handleSelectPriorityPreset,
    handleChangeFarmerSoil,
    handleChangeScenario,
    handleChangeEquipment,
  };
}

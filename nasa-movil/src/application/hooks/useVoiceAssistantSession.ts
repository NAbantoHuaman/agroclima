import { useState } from "react";
import { SafeHaptics as Haptics } from "../../utils/safeHaptics";
import {
  requestVoiceAssistant,
  requestVoiceAudio,
} from "../../services/apiClient";
import type {
  AppLanguage,
  ClimateScenario,
  CurrentCropId,
  EquipmentAccess,
  FarmerSoilNotes,
  MarketPreference,
  PriorityWeights,
  RecommendResponse,
  VoiceAssistantResponse,
  VoiceConfirmedSlots,
  WaterAvailability,
} from "../../types";
import type { AppTab } from "./useParcelAnalysis";

interface UseVoiceSessionParams {
  lang: AppLanguage;
  activePoint: { lat: number; lon: number };
  gpsCoords: { lat: number; lon: number } | null;
  parcelId: string | null;
  customPolygon: [number, number][] | null;
  currentCrop: CurrentCropId;
  waterAvailability: WaterAvailability;
  priorities: PriorityWeights;
  climateScenario: ClimateScenario;
  farmerSoil: FarmerSoilNotes;
  equipmentAccess: EquipmentAccess;
  marketPreference: MarketPreference;
  availableSeeds: string[];
  customZoneLabel: string | null;
  voiceSlots: VoiceConfirmedSlots;
  setActivePoint: (pt: { lat: number; lon: number }) => void;
  setParcelId: (id: string | null) => void;
  setCustomPolygon: (poly: [number, number][] | null) => void;
  setCurrentCrop: (crop: CurrentCropId) => void;
  setWaterAvailability: (w: WaterAvailability) => void;
  setEquipmentAccess: (eq: EquipmentAccess) => void;
  setMarketPreference: (mkt: MarketPreference) => void;
  setFarmerSoil: (s: FarmerSoilNotes) => void;
  setPriorities: (p: PriorityWeights) => void;
  setAvailableSeeds: (seeds: string[]) => void;
  setCustomZoneLabel: (lbl: string | null) => void;
  setVoiceSlots: (slots: VoiceConfirmedSlots) => void;
  setFarmerConfirmedInputs: (confirmed: boolean) => void;
  setExplorerPreviewResult: (res: RecommendResponse | null) => void;
  setResult: (res: RecommendResponse) => void;
  runAnalysis: (overrides?: {
    lat?: number;
    lon?: number;
    parcelId?: string | null;
    polygon?: [number, number][] | null;
    currentCrop?: CurrentCropId;
    waterAvailability?: WaterAvailability;
    equipmentAccess?: EquipmentAccess;
    marketPreference?: MarketPreference;
    priorities?: PriorityWeights;
    climateScenario?: ClimateScenario;
    farmerSoil?: FarmerSoilNotes;
    availableSeeds?: string[];
    customZoneLabel?: string | null;
  }) => Promise<void>;
  onNavigateTab: (tab: AppTab) => void;
}

export function useVoiceAssistantSession(params: UseVoiceSessionParams) {
  const [voiceModalOpen, setVoiceModalOpen] = useState(false);
  const [isVoiceBusy, setIsVoiceBusy] = useState(false);
  const [voiceResponse, setVoiceResponse] =
    useState<VoiceAssistantResponse | null>(null);
  const [voiceHistory, setVoiceHistory] = useState<
    Array<{ role: "user" | "assistant"; text: string }>
  >([]);

  const syncVoiceState = (
    data: VoiceAssistantResponse,
    userUtterance?: string
  ) => {
    setVoiceResponse(data);
    const spokenUser = (userUtterance || data.transcript || "").trim();
    const replyText = (data.spoken_response || "").trim();
    if (spokenUser || replyText) {
      setVoiceHistory((prev) => {
        const next = [...prev];
        if (spokenUser) next.push({ role: "user", text: spokenUser });
        if (replyText) next.push({ role: "assistant", text: replyText });
        return next.slice(-6);
      });
    }
    if (data.confirmed_slots) {
      params.setVoiceSlots(data.confirmed_slots);
    }
    if (data.conversation_stage === "out_of_scope") {
      return;
    }
    if (data.updated_params) {
      params.setActivePoint({
        lat: data.updated_params.lat,
        lon: data.updated_params.lon,
      });
      params.setParcelId(data.updated_params.parcel_id);
      if (data.updated_params.clear_polygon) {
        params.setCustomPolygon(null);
      }
      if (data.confirmed_slots?.crop_confirmed) {
        params.setCurrentCrop(data.updated_params.current_crop);
      }
      if (data.confirmed_slots?.water_confirmed) {
        params.setWaterAvailability(data.updated_params.water_availability);
      }
      if (data.updated_params.equipment_access) {
        params.setEquipmentAccess(data.updated_params.equipment_access);
      }
      if (data.updated_params.market_preference) {
        params.setMarketPreference(data.updated_params.market_preference);
      }
      if (data.updated_params.farmer_soil) {
        params.setFarmerSoil(data.updated_params.farmer_soil);
      }
      if (data.updated_params.priorities) {
        params.setPriorities(data.updated_params.priorities);
      }
      if (Array.isArray(data.updated_params.available_seeds)) {
        params.setAvailableSeeds(data.updated_params.available_seeds);
      }
    }
    if (data.confirmed_slots?.location_label) {
      params.setCustomZoneLabel(data.confirmed_slots.location_label);
    }
    if (data.recommendation) {
      params.setExplorerPreviewResult(null);
      params.setResult(data.recommendation);
      params.setFarmerConfirmedInputs(true);
    }
  };

  const handleSubmitVoice = async (
    transcript: string,
    opts?: {
      forceCalculate?: boolean;
      overrideLat?: number;
      overrideLon?: number;
      overridePolygon?: [number, number][] | null;
      overrideSlots?: VoiceConfirmedSlots;
    }
  ) => {
    setIsVoiceBusy(true);
    try {
      const targetLat = opts?.overrideLat ?? params.activePoint.lat;
      const targetLon = opts?.overrideLon ?? params.activePoint.lon;
      const targetPoly =
        opts && "overridePolygon" in opts
          ? opts.overridePolygon ?? null
          : params.customPolygon;
      const activeSlots = opts?.overrideSlots ?? params.voiceSlots;
      const res = await requestVoiceAssistant({
        transcript,
        lat: targetLat,
        lon: targetLon,
        gps_lat: params.gpsCoords?.lat ?? null,
        gps_lon: params.gpsCoords?.lon ?? null,
        parcel_id: params.parcelId,
        polygon: targetPoly,
        current_crop: params.currentCrop,
        water_availability: params.waterAvailability,
        priorities: params.priorities,
        climate_scenario: params.climateScenario,
        farmer_soil: params.farmerSoil,
        equipment_access: params.equipmentAccess,
        market_preference: params.marketPreference,
        field_status: "auto",
        available_seeds: params.availableSeeds,
        custom_zone_label: activeSlots.location_label || params.customZoneLabel,
        session_slots: activeSlots,
        history: voiceHistory,
        force_calculate: opts?.forceCalculate ?? false,
      });
      syncVoiceState(res.data, transcript);
    } finally {
      setIsVoiceBusy(false);
    }
  };

  const handleSubmitAudio = async (audioBase64: string, ext: string) => {
    setIsVoiceBusy(true);
    try {
      const res = await requestVoiceAudio({
        audio_base64: audioBase64,
        audio_ext: ext,
        lang: params.lang,
        lat: params.activePoint.lat,
        lon: params.activePoint.lon,
        gps_lat: params.gpsCoords?.lat ?? null,
        gps_lon: params.gpsCoords?.lon ?? null,
        parcel_id: params.parcelId,
        polygon: params.customPolygon,
        current_crop: params.currentCrop,
        water_availability: params.waterAvailability,
        priorities: params.priorities,
        climate_scenario: params.climateScenario,
        farmer_soil: params.farmerSoil,
        equipment_access: params.equipmentAccess,
        market_preference: params.marketPreference,
        field_status: "auto",
        available_seeds: params.availableSeeds,
        custom_zone_label:
          params.voiceSlots.location_label || params.customZoneLabel,
        session_slots: params.voiceSlots,
        history: voiceHistory,
      });
      syncVoiceState(res.data);
    } finally {
      setIsVoiceBusy(false);
    }
  };

  const handleConfirmVoiceMapSelection = async (
    lat: number,
    lon: number,
    polygon: [number, number][] | null,
    zoneLabel?: string
  ) => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    const resolvedLabel =
      zoneLabel ||
      params.voiceSlots.location_label ||
      params.customZoneLabel ||
      `Parcela (${lat.toFixed(4)}, ${lon.toFixed(4)})`;
    params.setActivePoint({ lat, lon });
    params.setParcelId(null);
    params.setCustomPolygon(polygon);
    params.setCustomZoneLabel(resolvedLabel);

    const nextSlots: VoiceConfirmedSlots = {
      ...params.voiceSlots,
      location_confirmed: true,
      map_verified: true,
      location_label: resolvedLabel,
      lat,
      lon,
    };
    params.setVoiceSlots(nextSlots);

    await handleSubmitVoice("Confirmo este punto exacto", {
      overrideLat: lat,
      overrideLon: lon,
      overridePolygon: polygon,
      overrideSlots: nextSlots,
    });
  };

  const handleResetVoiceSession = () => {
    setVoiceResponse(null);
    params.setVoiceSlots({});
    setVoiceHistory([]);
    params.setAvailableSeeds([]);
    params.setFarmerConfirmedInputs(false);
    params.setExplorerPreviewResult(null);
  };

  const handleApplyVoice = (v: VoiceAssistantResponse) => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    params.setActivePoint({
      lat: v.updated_params.lat,
      lon: v.updated_params.lon,
    });
    params.setParcelId(v.updated_params.parcel_id);
    if (v.updated_params.clear_polygon) params.setCustomPolygon(null);
    params.setCurrentCrop(v.updated_params.current_crop);
    params.setWaterAvailability(v.updated_params.water_availability);
    if (v.updated_params.equipment_access) {
      params.setEquipmentAccess(v.updated_params.equipment_access);
    }
    if (v.updated_params.market_preference) {
      params.setMarketPreference(v.updated_params.market_preference);
    }
    params.setFarmerSoil(v.updated_params.farmer_soil);
    if (Array.isArray(v.updated_params.available_seeds)) {
      params.setAvailableSeeds(v.updated_params.available_seeds);
    }
    if (v.updated_params.priorities) {
      params.setPriorities(v.updated_params.priorities);
    }
    if (v.confirmed_slots?.location_label) {
      params.setCustomZoneLabel(v.confirmed_slots.location_label);
    }
    params.setExplorerPreviewResult(null);
    params.setFarmerConfirmedInputs(true);
    if (v.recommendation) {
      params.setResult(v.recommendation);
      params.onNavigateTab("plan");
    } else {
      void params.runAnalysis({
        lat: v.updated_params.lat,
        lon: v.updated_params.lon,
        parcelId: v.updated_params.parcel_id,
        currentCrop: v.updated_params.current_crop,
        waterAvailability: v.updated_params.water_availability,
        equipmentAccess: v.updated_params.equipment_access ?? params.equipmentAccess,
        marketPreference: v.updated_params.market_preference ?? params.marketPreference,
        farmerSoil: v.updated_params.farmer_soil,
        availableSeeds: v.updated_params.available_seeds || [],
        customZoneLabel:
          v.confirmed_slots?.location_label || params.customZoneLabel,
      });
      params.onNavigateTab("mapa");
    }
  };

  return {
    voiceModalOpen,
    setVoiceModalOpen,
    isVoiceBusy,
    voiceResponse,
    handleSubmitVoice,
    handleSubmitAudio,
    handleConfirmVoiceMapSelection,
    handleResetVoiceSession,
    handleApplyVoice,
  };
}

import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  RecordingPresets,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  useAudioRecorder,
  useAudioRecorderState,
} from "expo-audio";
import { File } from "expo-file-system";
import * as Location from "expo-location";
import * as Speech from "expo-speech";
import { SafeHaptics as Haptics } from "../utils/safeHaptics";
import {
  ActivityIndicator,
  Alert,
  Modal,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import {
  AlertTriangle,
  ArrowRight,
  Check,
  CheckCircle2,
  Compass,
  MapPin,
  Mic,
  RotateCcw,
  Send,
  Sparkles,
  Sprout,
  Square,
  Volume2,
  VolumeX,
  X,
} from "lucide-react-native";
import {
  buildDefault1HaSquare,
  estimatePolygonAreaHa,
} from "../domain/map/geometry";
import {
  FARMER_VOICE_PROMPTS_ES,
  FARMER_VOICE_PROMPTS_QU,
  WAVE_INDICES,
} from "../domain/voice/prompts";
import { translateCropText, type MobileUiDictionary } from "../i18n/translations";
import { styles } from "../presentation/voice/VoiceCopilotModal.styles";
import { VoiceMapPickerSheet } from "../presentation/voice/VoiceMapPickerSheet";
import { COLORS } from "../theme/tokens";
import type {
  AppLanguage,
  VoiceAssistantResponse,
  VoiceConfirmedSlots,
} from "../types";

interface VoiceCopilotModalProps {
  visible: boolean;
  onClose: () => void;
  t: MobileUiDictionary;
  lang: AppLanguage;
  zoneName: string;
  activeLat: number;
  activeLon: number;
  customPolygon: [number, number][] | null;
  gpsCoords: { lat: number; lon: number } | null;
  sessionSlots: VoiceConfirmedSlots;
  isProcessing: boolean;
  lastResponse: VoiceAssistantResponse | null;
  onSubmitTranscript: (
    text: string,
    opts?: { forceCalculate?: boolean }
  ) => Promise<void> | void;
  onSubmitAudio: (audioBase64: string, ext: string) => Promise<void>;
  onConfirmMapSelection: (
    lat: number,
    lon: number,
    polygon: [number, number][] | null,
    zoneLabel?: string
  ) => Promise<void>;
  onApplyRecommendation: (res: VoiceAssistantResponse) => void;
  onResetSession: () => void;
}

export const VoiceCopilotModal: React.FC<VoiceCopilotModalProps> = ({
  visible,
  onClose,
  lang,
  zoneName,
  activeLat,
  activeLon,
  customPolygon,
  gpsCoords,
  sessionSlots,
  isProcessing,
  lastResponse,
  onSubmitTranscript,
  onSubmitAudio,
  onConfirmMapSelection,
  onApplyRecommendation,
  onResetSession,
}) => {
  const [inputText, setInputText] = useState("");
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [isSendingAudio, setIsSendingAudio] = useState(false);
  const [pendingChoiceValue, setPendingChoiceValue] = useState<string | null>(null);
  const [pendingChoiceLabel, setPendingChoiceLabel] = useState<string | null>(null);

  // Embedded interactive map picker modal state
  const [mapPickerOpen, setMapPickerOpen] = useState(false);
  const [mapDraftLat, setMapDraftLat] = useState(activeLat);
  const [mapDraftLon, setMapDraftLon] = useState(activeLon);
  const [mapOpenCenter, setMapOpenCenter] = useState({
    lat: activeLat,
    lon: activeLon,
  });
  const [mapDrawMode, setMapDrawMode] = useState(false);
  const [mapDraftPolygon, setMapDraftPolygon] = useState<[number, number][]>(
    []
  );
  const [isGettingGps, setIsGettingGps] = useState(false);
  const [isSavingMap, setIsSavingMap] = useState(false);
  const mapWebRef = useRef<{ injectJavaScript?: (script: string) => void } | null>(
    null
  );

  const recorder = useAudioRecorder({
    ...RecordingPresets.HIGH_QUALITY,
    isMeteringEnabled: true,
  });
  const recorderState = useAudioRecorderState(recorder, 120);

  const prompts =
    lang === "qu" ? FARMER_VOICE_PROMPTS_QU : FARMER_VOICE_PROMPTS_ES;

  // Speak response aloud whenever a fresh response arrives while modal is open
  useEffect(() => {
    if (visible && lastResponse?.spoken_response) {
      Speech.stop();
      setIsSpeaking(true);
      void setAudioModeAsync({
        allowsRecording: false,
        playsInSilentMode: true,
      }).catch(() => { });
      Speech.speak(translateCropText(lastResponse.spoken_response, lang), {
        language: lang === "qu" ? "qu-PE" : "es-PE",
        rate: 0.94,
        onDone: () => setIsSpeaking(false),
        onStopped: () => setIsSpeaking(false),
        onError: () => setIsSpeaking(false),
      });
    }
    return () => {
      Speech.stop();
    };
  }, [lastResponse, visible, lang]);

  // Ensure recording stops cleanly if modal is closed mid-recording
  useEffect(() => {
    if (!visible && recorderState.isRecording) {
      void recorder.stop().catch(() => { });
    }
  }, [visible, recorderState.isRecording, recorder]);

  const handleToggleMicRecording = async () => {
    setVoiceError(null);

    if (recorderState.isRecording) {
      // Stop and transcribe audio
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
      setIsSendingAudio(true);
      try {
        await recorder.stop();
        await setAudioModeAsync({
          allowsRecording: false,
          playsInSilentMode: true,
        });
        const uri = recorder.uri || recorderState.url;
        if (!uri) {
          throw new Error(
            lang === "qu"
              ? "Audio mana waqaychakurqanchu."
              : "No se guardó el archivo de audio en el dispositivo."
          );
        }
        const file = new File(uri);
        const base64 = await file.base64();
        const ext = uri.split(".").pop()?.toLowerCase() || "m4a";
        await onSubmitAudio(base64, ext);
      } catch (err) {
        const msg =
          err instanceof Error
            ? err.message
            : lang === "qu"
              ? "Rimaynikita mana uyariyta atirqanchu. Hukmanta rimay."
              : "No se pudo procesar tu voz. Intenta nuevamente.";
        setVoiceError(msg);
      } finally {
        setIsSendingAudio(false);
      }
      return;
    }

    // Start recording real microphone audio
    try {
      Speech.stop();
      setIsSpeaking(false);

      const perm = await requestRecordingPermissionsAsync();
      if (!perm.granted) {
        Alert.alert(
          lang === "qu" ? "Micrófono kamachiy" : "Permiso de Micrófono",
          lang === "qu"
            ? "Rimaynikita uyarinapaq micrófono kamachiyta qowayku."
            : "Necesitamos permiso para usar tu micrófono y escucharte hablar."
        );
        return;
      }

      await setAudioModeAsync({
        allowsRecording: true,
        playsInSilentMode: true,
      });
      await recorder.prepareToRecordAsync();
      recorder.record();
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : lang === "qu"
            ? "Celularpa micrófonon mana llamk'anchu."
            : "No se pudo activar el micrófono del celular.";
      setVoiceError(msg);
    }
  };

  const handleSendText = () => {
    const trimmed = inputText.trim();
    if (!trimmed || isProcessing || isSendingAudio || isSavingMap) return;
    void sendTranscriptSafe(trimmed);
  };

  const toggleSpeech = (text: string) => {
    if (isSpeaking) {
      Speech.stop();
      setIsSpeaking(false);
      return;
    }
    setIsSpeaking(true);
    Speech.speak(text, {
      language: lang === "qu" ? "qu-PE" : "es-PE",
      rate: 0.94,
      onDone: () => setIsSpeaking(false),
      onStopped: () => setIsSpeaking(false),
      onError: () => setIsSpeaking(false),
    });
  };

  const busy = isProcessing || isSendingAudio || isSavingMap;
  const elapsedSec = Math.floor((recorderState.durationMillis || 0) / 1000);
  const meteringDb = recorderState.metering ?? -60;
  const normalizedLevel = Math.max(0.12, Math.min(1, (meteringDb + 55) / 50));

  const mergedSlots: VoiceConfirmedSlots = {
    ...sessionSlots,
    ...(lastResponse?.confirmed_slots || {}),
  };

  const previewTerrain =
    lastResponse?.preview_terrain || lastResponse?.recommendation?.terrain;
  const previewBio =
    lastResponse?.preview_biophysical ||
    lastResponse?.recommendation?.biophysical;

  const detectedLat =
    previewTerrain?.lat ?? lastResponse?.updated_params?.lat ?? activeLat;
  const detectedLon =
    previewTerrain?.lon ?? lastResponse?.updated_params?.lon ?? activeLon;
  const detectedZoneTitle =
    previewTerrain?.zone_name ||
    mergedSlots.location_label ||
    lastResponse?.understood.location ||
    zoneName;

  const lastAutoOpenedMapRef = useRef<string | null>(null);

  useEffect(() => {
    if (!visible || !lastResponse) return;
    if (lastResponse.accion_ui?.tipo === "ABRIR_MAPA_CUADRADO") {
      const targetLat =
        lastResponse.accion_ui.parametros?.lat ?? detectedLat;
      const targetLon =
        lastResponse.accion_ui.parametros?.lng ?? detectedLon;
      const sig = `${targetLat.toFixed(5)}_${targetLon.toFixed(5)}_${lastResponse.spoken_response.slice(0, 24)}`;
      if (lastAutoOpenedMapRef.current !== sig) {
        lastAutoOpenedMapRef.current = sig;
        const apiPoly = lastResponse.accion_ui.parametros?.default_polygon;
        const seedSquare: [number, number][] =
          Array.isArray(apiPoly) && apiPoly.length >= 3
            ? (apiPoly.map((p) => [Number(p[0]), Number(p[1])] as [number, number]))
            : customPolygon && customPolygon.length >= 3
              ? customPolygon
              : buildDefault1HaSquare(targetLat, targetLon);
        setMapDraftLat(targetLat);
        setMapDraftLon(targetLon);
        setMapOpenCenter({ lat: targetLat, lon: targetLon });
        setMapDraftPolygon(seedSquare);
        setMapDrawMode(false);
        setMapPickerOpen(true);
      }
    }
  }, [visible, lastResponse, detectedLat, detectedLon, customPolygon]);

  const draftAreaHa = useMemo(() => {
    if (mapDraftPolygon.length < 3) return null;
    return estimatePolygonAreaHa(mapDraftPolygon);
  }, [mapDraftPolygon]);

  useEffect(() => {
    if (!mapPickerOpen) return;
    const js = `window.updateOverlay(${mapDraftLat}, ${mapDraftLon}, ${JSON.stringify(
      mapDraftPolygon
    )}, false); true;`;
    mapWebRef.current?.injectJavaScript?.(js);
  }, [mapPickerOpen, mapDraftLat, mapDraftLon, mapDraftPolygon]);

  const handleOpenMapPicker = () => {
    Speech.stop();
    setIsSpeaking(false);
    const seedPoly =
      !lastResponse?.updated_params?.clear_polygon && customPolygon?.length
        ? customPolygon
        : buildDefault1HaSquare(detectedLat, detectedLon);
    setMapDraftLat(detectedLat);
    setMapDraftLon(detectedLon);
    setMapOpenCenter({ lat: detectedLat, lon: detectedLon });
    setMapDraftPolygon(seedPoly);
    setMapDrawMode(false);
    setMapPickerOpen(true);
  };

  const handleMapTap = (lat: number, lon: number) => {
    Haptics.selectionAsync();
    if (mapDrawMode) {
      setMapDraftPolygon((prev) => [...prev, [lat, lon] as [number, number]]);
    } else {
      setMapDraftLat(lat);
      setMapDraftLon(lon);
      setMapDraftPolygon(buildDefault1HaSquare(lat, lon));
    }
  };

  const handleMapUseGps = async () => {
    setIsGettingGps(true);
    try {
      let targetLat = gpsCoords?.lat ?? null;
      let targetLon = gpsCoords?.lon ?? null;
      const perm = await Location.requestForegroundPermissionsAsync();
      if (perm.status === "granted") {
        const pos = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
        });
        targetLat = pos.coords.latitude;
        targetLon = pos.coords.longitude;
      }
      if (targetLat !== null && targetLon !== null) {
        const sq = buildDefault1HaSquare(targetLat, targetLon);
        setMapDraftLat(targetLat);
        setMapDraftLon(targetLon);
        setMapDraftPolygon(sq);
        mapWebRef.current?.injectJavaScript?.(
          `window.updateOverlay(${targetLat}, ${targetLon}, ${JSON.stringify(
            sq
          )}, true); true;`
        );
      } else {
        Alert.alert(
          "Permiso GPS",
          "Activa la ubicación del teléfono para centrar el mapa en tu chacra."
        );
      }
    } catch {
      Alert.alert("GPS", "No se pudo obtener tu posición GPS actual.");
    } finally {
      setIsGettingGps(false);
    }
  };

  const sendTranscriptSafe = async (
    text: string,
    opts?: { forceCalculate?: boolean; displayLabel?: string }
  ) => {
    if (busy) return;
    Speech.stop();
    setIsSpeaking(false);
    Haptics.selectionAsync();
    setVoiceError(null);
    setPendingChoiceValue(text);
    setPendingChoiceLabel(opts?.displayLabel || text);
    try {
      await onSubmitTranscript(text, opts);
    } catch (err) {
      setVoiceError(
        err instanceof Error
          ? err.message
          : "No se pudo conectar al servidor. Verifica tu conexión."
      );
    } finally {
      setPendingChoiceValue(null);
      setPendingChoiceLabel(null);
    }
  };

  const renderQuestionChips = (
    chips: Array<{ label: string; value: string }>,
    busyVerb: string
  ) => (
    <>
      <View style={styles.chipsWrap}>
        {chips.map((chip, cidx) => {
          const isSelectedPending = busy && pendingChoiceValue === chip.value;
          return (
            <TouchableOpacity
              key={cidx}
              disabled={busy}
              activeOpacity={0.85}
              onPress={() =>
                void sendTranscriptSafe(chip.value, {
                  displayLabel: chip.label,
                })
              }
              style={[
                styles.answerChipBtn,
                isSelectedPending && styles.answerChipBtnSelected,
                busy && !isSelectedPending && { opacity: 0.45 },
              ]}
            >
              <View style={styles.answerChipInner}>
                {isSelectedPending && (
                  <ActivityIndicator size="small" color={COLORS.forestDeep} />
                )}
                <Text
                  style={[
                    styles.answerChipText,
                    isSelectedPending && styles.answerChipTextSelected,
                  ]}
                >
                  {chip.label}
                </Text>
              </View>
            </TouchableOpacity>
          );
        })}
      </View>
      {busy && (
        <View style={styles.guidedBusyRow}>
          <ActivityIndicator size="small" color={COLORS.limeBright} />
          <Text style={styles.guidedBusyText}>
            {pendingChoiceLabel
              ? `${busyVerb} “${pendingChoiceLabel}”...`
              : "Procesando tu respuesta..."}
          </Text>
        </View>
      )}
    </>
  );

  const handleSaveAndCloseMap = async () => {
    setIsSavingMap(true);
    try {
      const hasPoly = mapDraftPolygon.length >= 3;
      const finalLat = hasPoly
        ? mapDraftPolygon.reduce((s, p) => s + p[0], 0) / mapDraftPolygon.length
        : mapDraftLat;
      const finalLon = hasPoly
        ? mapDraftPolygon.reduce((s, p) => s + p[1], 0) / mapDraftPolygon.length
        : mapDraftLon;
      setMapPickerOpen(false);
      await onConfirmMapSelection(
        finalLat,
        finalLon,
        hasPoly ? mapDraftPolygon : null,
        detectedZoneTitle
      );
    } catch (err) {
      setVoiceError(
        err instanceof Error
          ? err.message
          : "No se pudo analizar la parcela marcada en el servidor."
      );
    } finally {
      setIsSavingMap(false);
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={() => {
        Speech.stop();
        onClose();
      }}
    >
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          {/* Top Forest Header */}
          <View style={styles.sheetHeader}>
            <View style={styles.headerLeft}>
              <View style={styles.micBadge}>
                <Mic size={22} color={COLORS.forestDeep} strokeWidth={2.4} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.headerTitle}>
                  {lang === "qu"
                    ? "Rimay Yanapaq (Voz)"
                    : "Acompañante por Voz"}
                </Text>
                <Text style={styles.headerSub} numberOfLines={1}>
                  {zoneName}
                </Text>
              </View>
            </View>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
              {lastResponse && (
                <Pressable
                  onPress={() => {
                    Speech.stop();
                    setIsSpeaking(false);
                    setInputText("");
                    onResetSession();
                  }}
                  style={styles.resetHeaderBtn}
                >
                  <RotateCcw size={14} color="#FFFFFF" />
                  <Text style={styles.resetHeaderText}>Nueva</Text>
                </Pressable>
              )}
              <Pressable
                onPress={() => {
                  Speech.stop();
                  onClose();
                }}
                style={styles.closeBtn}
              >
                <X size={20} color="#FFFFFF" />
              </Pressable>
            </View>
          </View>

          <ScrollView
            style={styles.body}
            contentContainerStyle={styles.bodyContent}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            {/* PRIMARY REAL VOICE MICROPHONE STUDIO */}
            <View style={styles.voiceHeroCard}>
              <Text style={styles.voiceHeroTitle}>
                {recorderState.isRecording
                  ? lang === "qu"
                    ? `Uyariykuyki... (${elapsedSec}s)`
                    : `Te estoy escuchando... ${elapsedSec}s`
                  : busy
                    ? lang === "qu"
                      ? "Rimaynikita t'aqwirishani..."
                      : "Entendiendo tu voz y consultando NASA..."
                    : lang === "qu"
                      ? "Kay botonta ñit'iy hinaspa rimaway"
                      : "Toca el micrófono y háblame como a un ingeniero"}
              </Text>

              <Text style={styles.voiceHeroHint}>
                {recorderState.isRecording
                  ? "Dime dónde está tu chacra, qué sembraste y cuánta agua tienes. Toca el cuadrado rojo para enviar."
                  : "Por ejemplo: “Estoy en Cajabamba, sembré papa y solo tengo agua de lluvia, ¿qué me recomiendas?”"}
              </Text>

              {/* Big Circular Voice Trigger Button */}
              <View style={styles.micCenterWrap}>
                <TouchableOpacity
                  onPress={() => void handleToggleMicRecording()}
                  disabled={busy}
                  activeOpacity={0.85}
                  style={[
                    styles.giantMicRing,
                    recorderState.isRecording && styles.giantMicRingActive,
                    busy && { opacity: 0.7 },
                  ]}
                >
                  <View
                    style={[
                      styles.giantMicCore,
                      recorderState.isRecording && styles.giantMicCoreActive,
                    ]}
                  >
                    {busy ? (
                      <ActivityIndicator size="large" color={COLORS.forestDeep} />
                    ) : recorderState.isRecording ? (
                      <Square size={30} color="#FFFFFF" fill="#FFFFFF" />
                    ) : (
                      <Mic size={36} color={COLORS.forestDeep} strokeWidth={2.5} />
                    )}
                  </View>
                </TouchableOpacity>

                <Text style={styles.micActionCaption}>
                  {busy
                    ? "Procesando audio..."
                    : recorderState.isRecording
                      ? "Toca aquí para terminar y enviar"
                      : "Toca aquí para hablar"}
                </Text>

                {/* Real-time Audio Waveform Bars */}
                {recorderState.isRecording && (
                  <View style={styles.waveformRow}>
                    {WAVE_INDICES.map((i) => {
                      const shape = 1 - Math.abs(i - 5.5) / 6.5;
                      const barH = Math.max(
                        8,
                        Math.round(10 + normalizedLevel * 28 * shape)
                      );
                      return (
                        <View
                          key={i}
                          style={[styles.waveBar, { height: barH }]}
                        />
                      );
                    })}
                  </View>
                )}
              </View>

              {voiceError && (
                <View style={styles.errorBanner}>
                  <Text style={styles.errorBannerText}>{voiceError}</Text>
                </View>
              )}

              {busy && (
                <View style={styles.processingPillRow}>
                  <ActivityIndicator size="small" color={COLORS.limeBright} />
                  <Text style={styles.processingPillText} numberOfLines={2}>
                    {isSendingAudio
                      ? "Escuchando y analizando tu audio..."
                      : isSavingMap
                        ? "Guardando ubicación de tu chacra..."
                        : pendingChoiceLabel
                          ? `Procesando “${pendingChoiceLabel}”...`
                          : "AgroConecta IA está pensando..."}
                  </Text>
                </View>
              )}
            </View>

            {/* SPOKEN & GUIDED INTERACTIVE RESPONSE RIGHT BELOW MIC */}
            {lastResponse && (
              <View style={styles.responseCard}>
                <View style={styles.responseTopRow}>
                  <View style={styles.responseBadge}>
                    <CheckCircle2 size={16} color="#FFFFFF" />
                    <Text style={styles.responseBadgeText}>
                      {lastResponse.conversation_stage === "collecting_info"
                        ? "Armando tu diagnóstico real"
                        : lastResponse.conversation_stage === "out_of_scope"
                          ? "Fuera de tema agrícola"
                          : lastResponse.conversation_stage === "qa"
                            ? lastResponse.intent_mode === "app_help"
                              ? "Ayuda AgroConecta"
                              : "Respuesta con datos NASA"
                            : lang === "qu"
                              ? "Chaskisqa"
                              : "Plan listo con datos NASA"}
                    </Text>
                  </View>

                  <TouchableOpacity
                    onPress={() => toggleSpeech(lastResponse.spoken_response)}
                    style={[
                      styles.listenBtn,
                      isSpeaking && { backgroundColor: COLORS.crimsonSoft },
                    ]}
                  >
                    {isSpeaking ? (
                      <VolumeX size={15} color={COLORS.crimsonRisk} />
                    ) : (
                      <Volume2 size={15} color={COLORS.agroPrimary} />
                    )}
                    <Text
                      style={[
                        styles.listenBtnText,
                        isSpeaking && { color: COLORS.crimsonRisk },
                      ]}
                    >
                      {isSpeaking ? "Detener" : "Escuchar otra vez"}
                    </Text>
                  </TouchableOpacity>
                </View>

                {lastResponse.transcript && (
                  <View style={styles.heardTranscriptBox}>
                    <Text style={styles.heardTranscriptLabel}>
                      Lo que escuché:
                    </Text>
                    <Text style={styles.heardTranscriptText}>
                      “{lastResponse.transcript}”
                    </Text>
                  </View>
                )}

                <Text style={styles.spokenResponseText}>
                  “{lastResponse.spoken_response}”
                </Text>

                {/* 6-SLOT CHECKLIST STATUS PILLS (SHARED WITH MANUAL FLOW) */}
                {lastResponse.conversation_stage !== "out_of_scope" && (
                  <View style={styles.understoodStrip}>
                    <View
                      style={[
                        styles.understoodItem,
                        mergedSlots.location_confirmed &&
                        mergedSlots.map_verified &&
                        styles.understoodItemConfirmed,
                      ]}
                    >
                      <Text style={styles.understoodLabel}>1. Parcela</Text>
                      <Text style={styles.understoodVal} numberOfLines={2}>
                        {mergedSlots.location_confirmed
                          ? mergedSlots.map_verified
                            ? `${detectedZoneTitle} (Verificada)`
                            : `${detectedZoneTitle} (Falta mapa)`
                          : "Por ubicar"}
                      </Text>
                    </View>

                    <View
                      style={[
                        styles.understoodItem,
                        mergedSlots.water_confirmed && styles.understoodItemConfirmed,
                      ]}
                    >
                      <Text style={styles.understoodLabel}>2. Agua / Riego</Text>
                      <Text style={styles.understoodVal} numberOfLines={2}>
                        {mergedSlots.water_confirmed
                          ? mergedSlots.water_label || lastResponse.understood.water
                          : "Pendiente"}
                      </Text>
                    </View>

                    <View
                      style={[
                        styles.understoodItem,
                        mergedSlots.crop_confirmed && styles.understoodItemConfirmed,
                      ]}
                    >
                      <Text style={styles.understoodLabel}>3. Cultivo previo</Text>
                      <Text style={styles.understoodVal} numberOfLines={2}>
                        {mergedSlots.crop_confirmed
                          ? mergedSlots.crop_label || lastResponse.understood.crop
                          : "Pendiente"}
                      </Text>
                    </View>

                    <View
                      style={[
                        styles.understoodItem,
                        mergedSlots.soil_confirmed && styles.understoodItemConfirmed,
                      ]}
                    >
                      <Text style={styles.understoodLabel}>4. Suelo</Text>
                      <Text style={styles.understoodVal} numberOfLines={2}>
                        {mergedSlots.soil_confirmed
                          ? mergedSlots.soil_label ||
                          lastResponse.estado_parcela?.textura_y_drenaje ||
                          "Dato satelital SoilGrids"
                          : "Pendiente"}
                      </Text>
                    </View>

                    <View
                      style={[
                        styles.understoodItem,
                        mergedSlots.climate_risk_confirmed &&
                        styles.understoodItemConfirmed,
                      ]}
                    >
                      <Text style={styles.understoodLabel}>5. Clima / Helada</Text>
                      <Text style={styles.understoodVal} numberOfLines={2}>
                        {mergedSlots.climate_risk_confirmed
                          ? mergedSlots.climate_risk_label ||
                          lastResponse.estado_parcela?.riesgo_climatico ||
                          "Dato satelital NASA"
                          : "Pendiente"}
                      </Text>
                    </View>

                    <View
                      style={[
                        styles.understoodItem,
                        (mergedSlots.goal_confirmed || mergedSlots.seeds_checked) &&
                        styles.understoodItemConfirmed,
                      ]}
                    >
                      <Text style={styles.understoodLabel}>6. Objetivo / Semillas</Text>
                      <Text style={styles.understoodVal} numberOfLines={2}>
                        {mergedSlots.goal_confirmed || mergedSlots.seeds_checked
                          ? mergedSlots.goal_label ||
                          lastResponse.understood.seeds ||
                          lastResponse.estado_parcela?.objetivo_agricultor ||
                          "Confirmado"
                          : "Pendiente"}
                      </Text>
                    </View>
                  </View>
                )}

                {/* EMBEDDED INTERACTIVE MAP CARD (OPEN TO PINPOINT OR DRAW PARCEL) */}
                {lastResponse.conversation_stage !== "out_of_scope" &&
                  (lastResponse.show_map_picker ||
                    Boolean(previewTerrain) ||
                    mergedSlots.location_confirmed) && (
                    <View style={styles.inlineMapCard}>
                      <View style={styles.inlineMapHeaderRow}>
                        <View style={styles.inlineMapTitleRow}>
                          <MapPin size={16} color={COLORS.limeBright} />
                          <Text style={styles.inlineMapTitle} numberOfLines={1}>
                            {detectedZoneTitle}
                          </Text>
                        </View>
                        <View
                          style={[
                            styles.mapStatusPill,
                            mergedSlots.map_verified && styles.mapStatusPillDone,
                          ]}
                        >
                          <Text
                            style={[
                              styles.mapStatusText,
                              mergedSlots.map_verified && {
                                color: COLORS.forestDeep,
                              },
                            ]}
                          >
                            {mergedSlots.map_verified
                              ? "Parcela fijada"
                              : "Ajustar punto"}
                          </Text>
                        </View>
                      </View>

                      <Text style={styles.inlineMapCoords}>
                        Coordenadas: {detectedLat.toFixed(4)}, {detectedLon.toFixed(4)}
                        {customPolygon && customPolygon.length >= 3
                          ? ` · Límites marcados (${customPolygon.length} puntos)`
                          : ""}
                      </Text>

                      {previewTerrain && previewBio && (
                        <View style={styles.nasaPreviewGrid}>
                          <View style={styles.nasaPreviewCell}>
                            <Text style={styles.nasaPreviewLabel}>Altitud</Text>
                            <Text style={styles.nasaPreviewVal}>
                              {Math.round(previewTerrain.elevation_m)} m
                            </Text>
                          </View>
                          <View style={styles.nasaPreviewCell}>
                            <Text style={styles.nasaPreviewLabel}>Temp. NASA</Text>
                            <Text style={styles.nasaPreviewVal}>
                              {previewBio.summary.mean_temp_c.toFixed(1)} °C
                            </Text>
                          </View>
                          <View style={styles.nasaPreviewCell}>
                            <Text style={styles.nasaPreviewLabel}>Lluvia anual</Text>
                            <Text style={styles.nasaPreviewVal}>
                              {Math.round(previewBio.summary.annual_precip_mm)} mm
                            </Text>
                          </View>
                        </View>
                      )}

                      <TouchableOpacity
                        onPress={handleOpenMapPicker}
                        style={styles.openMapPickerBtn}
                        activeOpacity={0.88}
                      >
                        <Compass size={17} color={COLORS.forestDeep} strokeWidth={2.4} />
                        <Text style={styles.openMapPickerBtnText}>
                          {mergedSlots.map_verified
                            ? "Editar ubicación o límites en el mapa"
                            : "Confirmar exactamente mi parcela en el mapa"}
                        </Text>
                      </TouchableOpacity>
                    </View>
                  )}

                {/* PROGRESSIVE GUIDED FOLLOW-UP QUESTION + QUICK CHIPS + VOICE */}
                {lastResponse.conversation_stage === "collecting_info" &&
                  lastResponse.next_question && (
                    <View style={styles.guidedQuestionCard}>
                      <View style={styles.guidedQuestionHeader}>
                        <Sprout size={16} color={COLORS.limeBright} />
                        <Text style={styles.guidedQuestionBadge}>
                          Siguiente pregunta del ingeniero
                        </Text>
                      </View>
                      <Text style={styles.guidedQuestionText}>
                        {lastResponse.next_question}
                      </Text>

                      {lastResponse.question_chips &&
                        lastResponse.question_chips.length > 0 &&
                        renderQuestionChips(
                          lastResponse.question_chips,
                          "Anotando"
                        )}

                      <Text style={styles.voiceReplyHint}>
                        Responde tocando una opción arriba o pulsa el micrófono para decirlo con tu voz.
                      </Text>

                      <TouchableOpacity
                        disabled={busy}
                        onPress={() =>
                          void sendTranscriptSafe("Evaluar estrategias ahora", {
                            forceCalculate: true,
                            displayLabel: "Calculando tus 3 rotaciones",
                          })
                        }
                        style={styles.forceCalcLinkBtn}
                        activeOpacity={0.8}
                      >
                        <Text style={styles.forceCalcLinkText}>
                          Calcular estrategias ahora con estos datos
                        </Text>
                        <ArrowRight size={14} color={COLORS.limeBright} />
                      </TouchableOpacity>
                    </View>
                  )}

                {/* SEED CONSTRAINT / VIABILITY WARNING CALLOUT */}
                {(() => {
                  const sc = lastResponse.recommendation?.seed_constraint_summary;
                  if (!sc || (sc.requested.length === 0 && !sc.note)) return null;
                  const text =
                    sc.note ||
                    (sc.unviable.length > 0
                      ? `Semillas descartadas por clima/altitud: ${sc.unviable
                        .map((u) => `${u.crop_name} (${u.reason})`)
                        .join("; ")}.`
                      : `Priorizando tus semillas viables (${sc.viable_used.length}) entre los ${sc.evaluated_catalog_count} cultivos evaluados.`);
                  return (
                    <View
                      style={[
                        styles.seedConstraintBanner,
                        sc.unviable.length > 0 && styles.seedConstraintBannerWarn,
                      ]}
                    >
                      {sc.unviable.length > 0 ? (
                        <AlertTriangle size={16} color="#FDE68A" />
                      ) : (
                        <Check size={16} color={COLORS.limeBright} />
                      )}
                      <Text style={styles.seedConstraintBannerText}>
                        {text}
                      </Text>
                    </View>
                  );
                })()}

                {/* QUICK RESULT CARDS & APPLY BUTTON WHEN STRATEGIES READY */}
                {lastResponse.quick_cards.length > 0 && (
                  <View style={styles.quickCardsWrap}>
                    {lastResponse.quick_cards.map((qc, idx) => (
                      <View key={idx} style={styles.quickCard}>
                        <View style={styles.quickCardHeader}>
                          <Text style={styles.quickCardTitle}>{qc.title}</Text>
                          <Text style={styles.quickCardBadge}>{qc.badge}</Text>
                        </View>
                        <Text style={styles.quickCardBody}>{qc.body}</Text>
                      </View>
                    ))}
                  </View>
                )}

                {lastResponse.recommendation && (
                  <TouchableOpacity
                    onPress={() => {
                      Speech.stop();
                      onApplyRecommendation(lastResponse);
                      onClose();
                    }}
                    style={styles.applyPlanBtn}
                    activeOpacity={0.85}
                  >
                    <Text style={styles.applyPlanText}>
                      {lang === "qu"
                        ? "Kay planta chakrayman churay"
                        : "Aplicar este plan y ver mi rotación"}
                    </Text>
                    <ArrowRight
                      size={18}
                      color={COLORS.forestDeep}
                      strokeWidth={2.5}
                    />
                  </TouchableOpacity>
                )}

                {lastResponse.conversation_stage === "ready" &&
                  lastResponse.next_question &&
                  lastResponse.question_chips &&
                  lastResponse.question_chips.length > 0 && (
                    <View style={[styles.guidedQuestionCard, { marginTop: 12 }]}>
                      <View style={styles.guidedQuestionHeader}>
                        <Sprout size={15} color={COLORS.limeBright} />
                        <Text style={styles.guidedQuestionBadge}>
                          ¿Quieres afinar este plan? (Opcional)
                        </Text>
                      </View>
                      <Text style={styles.guidedQuestionText}>
                        {lastResponse.next_question}
                      </Text>
                      {renderQuestionChips(
                        lastResponse.question_chips,
                        "Actualizando plan con"
                      )}
                    </View>
                  )}
              </View>
            )}

            {/* QUICK 1-TAP EXAMPLES */}
            <View style={styles.introCard}>
              <Text style={styles.introTitle}>
                {lang === "qu"
                  ? "Utaq huk tapuyta ñit'iy:"
                  : "O toca una pregunta frecuente de campo:"}
              </Text>

              <View style={styles.promptsGrid}>
                {prompts.map((item, idx) => (
                  <TouchableOpacity
                    key={idx}
                    style={styles.promptPill}
                    activeOpacity={0.8}
                    onPress={() => {
                      setInputText(item.query);
                      void sendTranscriptSafe(item.query);
                    }}
                  >
                    <Sparkles size={15} color={COLORS.agroPrimary} />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.promptLabel}>{item.label}</Text>
                      <Text style={styles.promptQuery} numberOfLines={2}>
                        “{item.query}”
                      </Text>
                    </View>
                  </TouchableOpacity>
                ))}
              </View>
            </View>

            {/* COMPACT OPTIONAL TEXT INPUT */}
            <View style={styles.inputCard}>
              <Text style={styles.inputLabel}>
                {lang === "qu"
                  ? "Qillqayta munaspaqa:"
                  : "¿Estás en un lugar con mucho viento? También puedes escribir:"}
              </Text>
              <View style={styles.inlineInputRow}>
                <TextInput
                  value={inputText}
                  onChangeText={setInputText}
                  placeholder={
                    lang === "qu"
                      ? "Chakraykimanta qillqay..."
                      : "Escribe aquí tu consulta..."
                  }
                  placeholderTextColor={COLORS.inkMuted}
                  style={styles.inlineInput}
                />
                <TouchableOpacity
                  onPress={handleSendText}
                  disabled={busy || !inputText.trim()}
                  style={[
                    styles.inlineSendBtn,
                    (!inputText.trim() || busy) && { opacity: 0.5 },
                  ]}
                >
                  <Send size={18} color={COLORS.forestDeep} />
                </TouchableOpacity>
              </View>
            </View>
          </ScrollView>
        </View>
      </View>

      {/* FULLSCREEN EMBEDDED SATELLITE MAP PICKER & POLYGON DRAWER */}
      <VoiceMapPickerSheet
        visible={mapPickerOpen}
        onClose={() => setMapPickerOpen(false)}
        detectedZoneTitle={detectedZoneTitle}
        mapOpenCenter={mapOpenCenter}
        mapDraftLat={mapDraftLat}
        mapDraftLon={mapDraftLon}
        mapDraftPolygon={mapDraftPolygon}
        draftAreaHa={draftAreaHa}
        mapDrawMode={mapDrawMode}
        onChangeDrawMode={setMapDrawMode}
        onChangeDraftPolygon={setMapDraftPolygon}
        isGettingGps={isGettingGps}
        isSavingMap={isSavingMap}
        mapWebRef={mapWebRef}
        onUseGps={() => void handleMapUseGps()}
        onMapTap={handleMapTap}
        onSaveAndClose={() => void handleSaveAndCloseMap()}
      />
    </Modal>
  );
};

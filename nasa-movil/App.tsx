import { useState } from "react";
import { StatusBar } from "expo-status-bar";
import { SafeHaptics as Haptics } from "./src/utils/safeHaptics";
import {
  AlertTriangle,
  Award,
  Home,
  Map,
  Mic,
  Sprout,
  X,
} from "lucide-react-native";
import {
  Modal,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import {
  getCustomApiBaseUrl,
  setCustomApiBaseUrl,
} from "./src/services/apiClient";
import {
  SafeAreaProvider,
  SafeAreaView,
  useSafeAreaInsets,
} from "react-native-safe-area-context";
import {
  type AppTab,
  useParcelAnalysis,
} from "./src/application/hooks/useParcelAnalysis";
import { useVoiceAssistantSession } from "./src/application/hooks/useVoiceAssistantSession";
import { CropsCatalogTab } from "./src/components/CropsCatalogTab";
import { FarmerHomeTab } from "./src/components/FarmerHomeTab";
import { GrowingPlantLoader } from "./src/components/GrowingPlantLoader";
import { InteractiveMapTab } from "./src/components/InteractiveMapTab";
import { RotationPlanTab } from "./src/components/RotationPlanTab";
import { VoiceCopilotModal } from "./src/components/VoiceCopilotModal";
import { MOBILE_TRANSLATIONS } from "./src/i18n/translations";
import { COLORS, DISPLAY_FONT } from "./src/theme/tokens";
import type { AppLanguage } from "./src/types";

function MainShell() {
  const insets = useSafeAreaInsets();
  const [lang, setLang] = useState<AppLanguage>("es");
  const [activeTab, setActiveTab] = useState<AppTab>("inicio");
  const [serverModalOpen, setServerModalOpen] = useState(false);
  const [serverUrlDraft, setServerUrlDraft] = useState(
    () => getCustomApiBaseUrl() ?? ""
  );

  const handleSaveServerUrl = () => {
    const trimmed = serverUrlDraft.trim();
    setCustomApiBaseUrl(trimmed.length > 0 ? trimmed : null);
    setServerModalOpen(false);
    void parcel.retryBootstrap();
  };

  const parcel = useParcelAnalysis(setActiveTab);
  const voice = useVoiceAssistantSession({
    lang,
    activePoint: parcel.activePoint,
    gpsCoords: parcel.gpsCoords,
    parcelId: parcel.parcelId,
    customPolygon: parcel.customPolygon,
    currentCrop: parcel.currentCrop,
    waterAvailability: parcel.waterAvailability,
    priorities: parcel.priorities,
    climateScenario: parcel.climateScenario,
    farmerSoil: parcel.farmerSoil,
    equipmentAccess: parcel.equipmentAccess,
    marketPreference: parcel.marketPreference,
    availableSeeds: parcel.availableSeeds,
    customZoneLabel: parcel.customZoneLabel,
    voiceSlots: parcel.voiceSlots,
    setActivePoint: parcel.setActivePoint,
    setParcelId: parcel.setParcelId,
    setCustomPolygon: parcel.setCustomPolygon,
    setCurrentCrop: parcel.setCurrentCrop,
    setWaterAvailability: parcel.setWaterAvailability,
    setEquipmentAccess: parcel.setEquipmentAccess,
    setMarketPreference: parcel.setMarketPreference,
    setFarmerSoil: parcel.setFarmerSoil,
    setPriorities: parcel.setPriorities,
    setAvailableSeeds: parcel.setAvailableSeeds,
    setCustomZoneLabel: parcel.setCustomZoneLabel,
    setVoiceSlots: parcel.setVoiceSlots,
    setFarmerConfirmedInputs: parcel.setFarmerConfirmedInputs,
    setExplorerPreviewResult: parcel.setExplorerPreviewResult,
    setResult: parcel.setResult,
    runAnalysis: parcel.runAnalysis,
    onNavigateTab: setActiveTab,
  });

  const t = MOBILE_TRANSLATIONS[lang];
  const isPlanReady =
    parcel.completedChecklistCount === 6 ||
    Boolean(voice.voiceResponse?.listo_para_nasa) ||
    parcel.farmerConfirmedInputs;
  const bottomInset = Math.max(insets.bottom, 8);

  const serverModal = (
    <Modal
      visible={serverModalOpen}
      transparent
      animationType="fade"
      onRequestClose={() => setServerModalOpen(false)}
    >
      <View style={styles.serverModalOverlay}>
        <View style={styles.serverModalCard}>
          <Text style={styles.serverModalTitle}>Servidor Backend AgroConecta</Text>
          <Text style={styles.serverModalHint}>
            Ingresa la URL pública HTTPS de tu backend (ej. Render) o déjalo vacío para detección local automática.
          </Text>
          <TextInput
            value={serverUrlDraft}
            onChangeText={setServerUrlDraft}
            placeholder="https://agroconecta-api.onrender.com"
            placeholderTextColor="#6E8072"
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
            style={styles.serverModalInput}
          />
          <View style={styles.serverModalActions}>
            <TouchableOpacity
              onPress={() => setServerModalOpen(false)}
              style={styles.serverModalCancelBtn}
            >
              <Text style={styles.serverModalCancelText}>Cancelar</Text>
            </TouchableOpacity>
            <TouchableOpacity
              onPress={handleSaveServerUrl}
              style={styles.serverModalSaveBtn}
            >
              <Text style={styles.serverModalSaveText}>Guardar y conectar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );

  if (!parcel.result) {
    return (
      <SafeAreaView style={styles.bootSafe} edges={["top", "bottom"]}>
        <StatusBar style="light" />
        <View style={styles.bootContainer}>
          <GrowingPlantLoader />
          {!parcel.isBootstrapping && (
            <View style={styles.bootRetryWrap}>
              <Text style={styles.bootRetryHint}>
                Sin conexión con el servidor backend
              </Text>
              <View style={styles.bootRetryActions}>
                <TouchableOpacity
                  onPress={() => void parcel.retryBootstrap()}
                  style={styles.bootRetryBtn}
                >
                  <Text style={styles.bootRetryBtnText}>Reintentar</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  onPress={() => setServerModalOpen(true)}
                  style={styles.bootServerBtn}
                >
                  <Text style={styles.bootServerBtnText}>Configurar URL</Text>
                </TouchableOpacity>
              </View>
            </View>
          )}
        </View>
        {serverModal}
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <StatusBar style="light" />
      {serverModal}

      {parcel.backendError && (
        <View style={styles.inlineErrorBanner}>
          <AlertTriangle size={15} color="#FECACA" />
          <Text style={styles.inlineErrorText} numberOfLines={2}>
            {lang === "qu" ? "Mana tinkiy kanchu" : parcel.backendError}
          </Text>
          <TouchableOpacity
            onPress={() => setServerModalOpen(true)}
            style={styles.inlineRetryPill}
          >
            <Text style={styles.inlineRetryText}>URL</Text>
          </TouchableOpacity>
          <TouchableOpacity
            onPress={() => void parcel.runAnalysis()}
            style={styles.inlineRetryPill}
          >
            <Text style={styles.inlineRetryText}>
              {lang === "qu" ? "Hukmanta ruway" : "Reintentar"}
            </Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => parcel.setBackendError(null)}>
            <X size={16} color="#FECACA" />
          </TouchableOpacity>
        </View>
      )}

      <View style={styles.body}>
        {activeTab === "inicio" && (
          <FarmerHomeTab
            t={t}
            lang={lang}
            onToggleLang={() => {
              Haptics.selectionAsync();
              setLang((prev) => (prev === "es" ? "qu" : "es"));
            }}
            activePoint={parcel.activePoint}
            result={parcel.result}
            referenceData={parcel.referenceData}
            priorities={parcel.priorities}
            equipmentAccess={parcel.equipmentAccess}
            onChangeEquipment={parcel.handleChangeEquipment}
            isLocatingGps={parcel.isLocatingGps}
            isAnalyzing={parcel.isAnalyzing}
            farmerConfirmedInputs={isPlanReady}
            hasLocatedParcel={parcel.hasLocatedParcel}
            isPlanReady={isPlanReady}
            voiceSlots={parcel.voiceSlots}
            completedChecklistCount={parcel.completedChecklistCount}
            onSelectChecklistOption={parcel.handleSelectChecklistOption}
            onForceCalculatePlan={parcel.handleForceCalculatePlan}
            onRequestGps={parcel.handleRequestGps}
            onSelectBeacon={parcel.handleSelectBeacon}
            onSelectLocation={parcel.handleSelectLocation}
            onChangePriorities={(p) => parcel.handleChangePriorities(p)}
            onSelectPriorityPreset={parcel.handleSelectPriorityPreset}
            onNavigateTab={(tab) => {
              Haptics.selectionAsync();
              setActiveTab(tab);
            }}
            onOpenVoiceModal={() => {
              Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
              voice.setVoiceModalOpen(true);
            }}
          />
        )}

        {activeTab === "mapa" && (
          <InteractiveMapTab
            t={t}
            lang={lang}
            activePoint={parcel.activePoint}
            customPolygon={parcel.customPolygon}
            currentCrop={parcel.currentCrop}
            waterAvailability={parcel.waterAvailability}
            priorities={parcel.priorities}
            farmerSoil={parcel.farmerSoil}
            equipmentAccess={parcel.equipmentAccess}
            marketPreference={parcel.marketPreference}
            onChangeEquipment={parcel.handleChangeEquipment}
            farmerConfirmedInputs={isPlanReady}
            isPlanReady={isPlanReady}
            voiceSlots={parcel.voiceSlots}
            completedChecklistCount={parcel.completedChecklistCount}
            onSelectChecklistOption={parcel.handleSelectChecklistOption}
            onGoToPlan={() => {
              parcel.handleForceCalculatePlan();
              setActiveTab("plan");
            }}
            onConfirmParcelPolygon={parcel.handleConfirmParcelPolygon}
            onSimulateExplorerPlan={(simRes) => {
              parcel.setExplorerPreviewResult(simRes);
              setActiveTab("plan");
            }}
            onSaveExploredAsMyChacra={parcel.handleSaveExploredAsMyChacra}
            referenceData={parcel.referenceData}
            result={parcel.result}
            isAnalyzing={parcel.isAnalyzing}
            isLocatingGps={parcel.isLocatingGps}
            onSelectPoint={parcel.handleSelectMapPoint}
            onSelectBeacon={(b) =>
              parcel.handleSelectBeacon(b, { skipOpenMapConfirm: true })
            }
            onSetPolygon={parcel.handleSetPolygon}
            onChangeCrop={parcel.handleChangeCrop}
            onChangeWater={parcel.handleChangeWater}
            onChangePriorities={(p) =>
              parcel.handleChangePriorities(p, { markGoalSlot: true })
            }
            onChangeFarmerSoil={parcel.handleChangeFarmerSoil}
            onAnalyze={() => void parcel.runAnalysis()}
            onRequestGps={parcel.handleRequestGps}
            onExplorerError={parcel.setBackendError}
          />
        )}

        {activeTab === "plan" && (
          <RotationPlanTab
            t={t}
            lang={lang}
            result={parcel.explorerPreviewResult || parcel.result}
            isPlanReady={Boolean(parcel.explorerPreviewResult) || isPlanReady}
            isExplorerSimulation={Boolean(parcel.explorerPreviewResult)}
            completedChecklistCount={parcel.completedChecklistCount}
            onClearExplorerSimulation={() =>
              parcel.setExplorerPreviewResult(null)
            }
            onGoToChecklist={() => setActiveTab("inicio")}
            onOpenVoiceModal={() => voice.setVoiceModalOpen(true)}
            onForceCalculatePlan={parcel.handleForceCalculatePlan}
          />
        )}

        {activeTab === "semillas" && (
          <CropsCatalogTab
            t={t}
            lang={lang}
            crops={parcel.referenceData?.crops || []}
            marketSummary={
              parcel.result?.biophysical?.provenance?.market_summary ??
              parcel.referenceData?.market_summary ??
              parcel.referenceData?.crops_metadata?.market_summary ??
              null
            }
            result={parcel.result}
            climateScenario={parcel.climateScenario}
            onChangeScenario={parcel.handleChangeScenario}
          />
        )}
      </View>

      {/* FLOATING ORGANIC PILL BOTTOM NAVIGATION BAR WITH CENTRAL VOICE COPILOT BUTTON */}
      <View
        style={[styles.floatingDockWrap, { bottom: bottomInset }]}
        pointerEvents="box-none"
      >
        <View style={styles.floatingDock}>
          <TouchableOpacity
            onPress={() => {
              Haptics.selectionAsync();
              setActiveTab("inicio");
            }}
            style={styles.dockTab}
            activeOpacity={0.85}
          >
            <View
              style={[
                styles.dockIconWrap,
                activeTab === "inicio" && styles.dockIconWrapActive,
              ]}
            >
              <Home
                size={20}
                color={
                  activeTab === "inicio"
                    ? COLORS.forestDeep
                    : COLORS.inkOnDarkMuted
                }
                strokeWidth={2.2}
              />
            </View>
            <Text
              style={[
                styles.dockLabel,
                activeTab === "inicio" && styles.dockLabelActive,
              ]}
            >
              {lang === "qu" ? "Qallariy" : "Inicio"}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            onPress={() => {
              Haptics.selectionAsync();
              setActiveTab("mapa");
            }}
            style={styles.dockTab}
            activeOpacity={0.85}
          >
            <View
              style={[
                styles.dockIconWrap,
                activeTab === "mapa" && styles.dockIconWrapActive,
              ]}
            >
              <Map
                size={20}
                color={
                  activeTab === "mapa"
                    ? COLORS.forestDeep
                    : COLORS.inkOnDarkMuted
                }
                strokeWidth={2.2}
              />
            </View>
            <Text
              style={[
                styles.dockLabel,
                activeTab === "mapa" && styles.dockLabelActive,
              ]}
            >
              {lang === "qu" ? t.tabs.parcela : "Mi Chacra"}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            onPress={() => {
              Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
              voice.setVoiceModalOpen(true);
            }}
            style={styles.centerVoiceButtonWrap}
            activeOpacity={0.9}
          >
            <View style={styles.centerVoiceCircle}>
              <Mic size={24} color={COLORS.forestDeep} strokeWidth={2.5} />
            </View>
            <Text style={styles.centerVoiceLabel}>
              {lang === "qu" ? "Rimay" : "Hablar"}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            onPress={() => {
              Haptics.selectionAsync();
              setActiveTab("plan");
            }}
            style={styles.dockTab}
            activeOpacity={0.85}
          >
            <View
              style={[
                styles.dockIconWrap,
                activeTab === "plan" && styles.dockIconWrapActive,
              ]}
            >
              <Award
                size={20}
                color={
                  activeTab === "plan"
                    ? COLORS.forestDeep
                    : COLORS.inkOnDarkMuted
                }
                strokeWidth={2.2}
              />
            </View>
            <Text
              style={[
                styles.dockLabel,
                activeTab === "plan" && styles.dockLabelActive,
              ]}
            >
              {lang === "qu" ? "Muyuy" : "Rotación"}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            onPress={() => {
              Haptics.selectionAsync();
              setActiveTab("semillas");
            }}
            style={styles.dockTab}
            activeOpacity={0.85}
          >
            <View
              style={[
                styles.dockIconWrap,
                activeTab === "semillas" && styles.dockIconWrapActive,
              ]}
            >
              <Sprout
                size={20}
                color={
                  activeTab === "semillas"
                    ? COLORS.forestDeep
                    : COLORS.inkOnDarkMuted
                }
                strokeWidth={2.2}
              />
            </View>
            <Text
              style={[
                styles.dockLabel,
                activeTab === "semillas" && styles.dockLabelActive,
              ]}
            >
              {lang === "qu" ? "Muhukuna" : "Semillas"}
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* ALWAYS-ACCESSIBLE VOICE COPILOT MODAL */}
      <VoiceCopilotModal
        visible={voice.voiceModalOpen}
        onClose={() => voice.setVoiceModalOpen(false)}
        t={t}
        lang={lang}
        zoneName={parcel.zoneName}
        activeLat={parcel.activePoint.lat}
        activeLon={parcel.activePoint.lon}
        customPolygon={parcel.customPolygon}
        gpsCoords={parcel.gpsCoords}
        sessionSlots={parcel.voiceSlots}
        isProcessing={voice.isVoiceBusy}
        lastResponse={voice.voiceResponse}
        onSubmitTranscript={voice.handleSubmitVoice}
        onSubmitAudio={voice.handleSubmitAudio}
        onConfirmMapSelection={voice.handleConfirmVoiceMapSelection}
        onApplyRecommendation={voice.handleApplyVoice}
        onResetSession={voice.handleResetVoiceSession}
      />
    </SafeAreaView>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <MainShell />
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: COLORS.forestMid,
  },
  body: {
    flex: 1,
    backgroundColor: COLORS.canvas,
  },
  floatingDockWrap: {
    position: "absolute",
    left: 14,
    right: 14,
    alignItems: "center",
  },
  floatingDock: {
    width: "100%",
    backgroundColor: "rgba(23, 44, 26, 0.96)",
    borderRadius: 34,
    paddingHorizontal: 10,
    paddingVertical: 7,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderWidth: 1,
    borderColor: "rgba(255, 255, 255, 0.16)",
    elevation: 12,
  },
  dockTab: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 2,
  },
  dockIconWrap: {
    width: 36,
    height: 30,
    borderRadius: 15,
    alignItems: "center",
    justifyContent: "center",
  },
  dockIconWrapActive: {
    backgroundColor: COLORS.limeAccent,
  },
  dockLabel: {
    fontFamily: DISPLAY_FONT,
    fontSize: 10.5,
    fontWeight: "600",
    color: COLORS.inkOnDarkMuted,
  },
  dockLabelActive: {
    color: COLORS.limeBright,
    fontWeight: "700",
  },
  centerVoiceButtonWrap: {
    alignItems: "center",
    justifyContent: "center",
    marginTop: -20,
    paddingHorizontal: 6,
  },
  centerVoiceCircle: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: COLORS.limeAccent,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 3.5,
    borderColor: COLORS.forestDeep,
    elevation: 8,
  },
  centerVoiceLabel: {
    fontFamily: DISPLAY_FONT,
    fontSize: 10.5,
    fontWeight: "700",
    color: COLORS.limeBright,
    marginTop: 2,
  },
  bootSafe: {
    flex: 1,
    backgroundColor: COLORS.forestDeep,
  },
  bootContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: COLORS.forestDeep,
  },
  inlineErrorBanner: {
    backgroundColor: COLORS.crimsonRisk,
    paddingHorizontal: 12,
    paddingVertical: 8,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  inlineErrorText: {
    flex: 1,
    fontSize: 12,
    fontWeight: "600",
    color: "#FFFFFF",
  },
  inlineRetryPill: {
    backgroundColor: "rgba(255,255,255,0.22)",
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
  },
  inlineRetryText: {
    fontSize: 11.5,
    fontWeight: "700",
    color: "#FFFFFF",
  },
  bootRetryWrap: {
    marginTop: 22,
    alignItems: "center",
    gap: 10,
    paddingHorizontal: 24,
  },
  bootRetryHint: {
    fontSize: 12.5,
    color: COLORS.inkOnDarkMuted,
    textAlign: "center",
  },
  bootRetryActions: {
    flexDirection: "row",
    gap: 10,
  },
  bootRetryBtn: {
    backgroundColor: COLORS.limeAccent,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 14,
  },
  bootRetryBtnText: {
    fontSize: 12.5,
    fontWeight: "800",
    color: COLORS.forestDeep,
  },
  bootServerBtn: {
    backgroundColor: "rgba(255,255,255,0.14)",
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.22)",
  },
  bootServerBtnText: {
    fontSize: 12.5,
    fontWeight: "700",
    color: "#FFFFFF",
  },
  serverModalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.6)",
    justifyContent: "center",
    padding: 20,
  },
  serverModalCard: {
    backgroundColor: COLORS.surface,
    borderRadius: 20,
    padding: 18,
    gap: 10,
  },
  serverModalTitle: {
    fontSize: 16,
    fontWeight: "800",
    color: COLORS.inkPrimary,
  },
  serverModalHint: {
    fontSize: 12.5,
    lineHeight: 18,
    color: COLORS.inkSecondary,
  },
  serverModalInput: {
    borderWidth: 1,
    borderColor: COLORS.borderStrong,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 13.5,
    color: COLORS.inkPrimary,
    backgroundColor: COLORS.surfaceSubtle,
  },
  serverModalActions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: 10,
    marginTop: 4,
  },
  serverModalCancelBtn: {
    paddingHorizontal: 14,
    paddingVertical: 9,
    borderRadius: 10,
    backgroundColor: COLORS.surfaceSubtle,
  },
  serverModalCancelText: {
    fontSize: 13,
    fontWeight: "700",
    color: COLORS.inkSecondary,
  },
  serverModalSaveBtn: {
    paddingHorizontal: 14,
    paddingVertical: 9,
    borderRadius: 10,
    backgroundColor: COLORS.agroPrimary,
  },
  serverModalSaveText: {
    fontSize: 13,
    fontWeight: "700",
    color: "#FFFFFF",
  },
});

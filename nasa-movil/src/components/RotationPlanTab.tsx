import React, { useEffect, useState } from "react";
import * as Speech from "expo-speech";
import {
  AlertTriangle,
  Bug,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Eye,
  Sparkles,
  Sprout,
  Volume2,
  VolumeX,
} from "lucide-react-native";
import { ScrollView, Text, TouchableOpacity, View } from "react-native";
import {
  translateCropText,
  type MobileUiDictionary,
} from "../i18n/translations";
import { PhaseTimelineSection } from "../presentation/plan/PhaseTimelineSection";
import { styles } from "../presentation/plan/RotationPlanTab.styles";
import {
  StrategyOverviewCard,
  StrategyPillTabs,
} from "../presentation/plan/StrategyComparisonSection";
import { COLORS } from "../theme/tokens";
import type { AppLanguage, RecommendResponse } from "../types";
import { RadarChartSvg } from "./RadarChartSvg";

interface RotationPlanTabProps {
  t: MobileUiDictionary;
  lang: AppLanguage;
  result: RecommendResponse | null;
  isPlanReady?: boolean;
  isExplorerSimulation?: boolean;
  completedChecklistCount?: number;
  onClearExplorerSimulation?: () => void;
  onGoToChecklist?: () => void;
  onOpenVoiceModal?: () => void;
  onForceCalculatePlan?: () => void;
}

export const RotationPlanTab: React.FC<RotationPlanTabProps> = ({
  lang,
  result,
  isPlanReady = true,
  isExplorerSimulation = false,
  completedChecklistCount = 0,
  onClearExplorerSimulation,
  onGoToChecklist,
  onOpenVoiceModal,
  onForceCalculatePlan,
}) => {
  const [selectedId, setSelectedId] = useState<
    "regenerative" | "resilience" | "baseline"
  >(result?.recommended_strategy_id || "regenerative");

  useEffect(() => {
    if (result?.recommended_strategy_id) {
      setSelectedId(result.recommended_strategy_id);
    }
  }, [result]);

  const [isSpeaking, setIsSpeaking] = useState(false);
  const [showPestGuide, setShowPestGuide] = useState(false);
  const [showRadar, setShowRadar] = useState(false);

  if (!result || !isPlanReady) {
    return (
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.heroHeader}>
          <Text style={styles.heroOverline}>
            PLANIFICACIÓN AGRONÓMICA
          </Text>
          <Text style={styles.heroTitle}>
            Configura tu parcela para ver tus rotaciones
          </Text>
          <Text style={styles.emptyPlanSub}>
            Completa los 6 datos básicos de tu terreno para generar tres estrategias de rotación adaptadas a tu clima, agua y tipo de suelo ({completedChecklistCount}/6 completados).
          </Text>
        </View>
        <View style={styles.bodyPadding}>
          <View style={styles.emptyPlanCard}>
            <Text style={styles.emptyPlanCardTitle}>
              ¿Cómo deseas ingresar los datos de tu terreno?
            </Text>
            <Text style={styles.emptyPlanCardBody}>
              Puedes contarnos por voz los detalles de tu chacra o completar las opciones en Inicio. Si desconoces un dato técnico como la textura del suelo o el riesgo de heladas, utiliza directamente la medición satelital.
            </Text>
            <TouchableOpacity
              onPress={onOpenVoiceModal}
              style={styles.emptyPrimaryBtn}
              activeOpacity={0.88}
            >
              <Sparkles size={16} color={COLORS.forestDeep} />
              <Text style={styles.emptyPrimaryBtnText}>
                Completar datos por voz
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              onPress={onGoToChecklist}
              style={styles.emptySecondaryBtn}
              activeOpacity={0.88}
            >
              <Sprout size={16} color={COLORS.agroPrimary} />
              <Text style={styles.emptySecondaryBtnText}>
                Ir a la guía en Inicio ({completedChecklistCount}/6)
              </Text>
            </TouchableOpacity>
            {completedChecklistCount >= 1 && (
              <TouchableOpacity
                onPress={onForceCalculatePlan}
                style={styles.emptySecondaryBtn}
                activeOpacity={0.88}
              >
                <CheckCircle2 size={16} color={COLORS.agroPrimary} />
                <Text style={styles.emptySecondaryBtnText}>
                  Calcular las 3 rotaciones con los datos actuales
                </Text>
              </TouchableOpacity>
            )}
          </View>
        </View>
      </ScrollView>
    );
  }

  const activeStrat =
    result.strategies.find((s) => s.id === selectedId) ||
    result.strategies.find((s) => s.id === result.recommended_strategy_id) ||
    result.strategies[0];
  const baselineStrat =
    result.strategies.find((s) => s.id === "baseline") || result.strategies[0];

  const handleToggleSpeech = () => {
    if (isSpeaking) {
      Speech.stop();
      setIsSpeaking(false);
      return;
    }
    const isQu = lang === "qu";
    const cropsSeq = activeStrat.phases
      .map((p) =>
        p.crop_id === "suelo_desnudo"
          ? isQu
            ? "Mana tarpusqa allpa samaypi"
            : "Tierra en descanso sin cobertura"
          : translateCropText(p.crop_name, lang)
      )
      .join(isQu ? ", chanta " : ", luego ");
    const msg = isQu
      ? `${translateCropText(activeStrat.title, lang)}. Qhipa 4 tarpuykunapi kaykunata tarpunki: ${cropsSeq}. ` +
        `Muhukunapi yaqa ${activeStrat.metrics.seed_cost_2yr_soles_ha ?? 0} solesta huk hectáreapi iskay watapi churanki, ` +
        `chanta qhispisqa gananciaykiqa yaqa ${activeStrat.metrics.net_margin_2yr_soles_ha ?? 0} soles kanqa. ` +
        `${translateCropText(activeStrat.explainability.why_suggested || "", lang)}`
      : `${activeStrat.title}. En las próximas 4 campañas sembrarás: ${cropsSeq}. ` +
        `En semillas invertirás aproximadamente ${activeStrat.metrics.seed_cost_2yr_soles_ha ?? 0
        } soles por hectárea en dos años, y tu ganancia libre estimada es de ${activeStrat.metrics.net_margin_2yr_soles_ha ?? 0
        } soles por hectárea. ` +
        `${activeStrat.explainability.why_suggested || ""}`;

    setIsSpeaking(true);
    Speech.speak(msg, {
      language: isQu ? "qu-PE" : "es-PE",
      rate: 0.92,
      onDone: () => setIsSpeaking(false),
      onStopped: () => setIsSpeaking(false),
      onError: () => setIsSpeaking(false),
    });
  };

  const marginDelta =
    (activeStrat.metrics.net_margin_2yr_soles_ha ?? 0) -
    (baselineStrat.metrics.net_margin_2yr_soles_ha ?? 0);

  const bareMonthsCount = activeStrat.timeline_24m.filter(
    (m) => m.crop_id === "suelo_desnudo"
  ).length;

  return (
    <ScrollView
      style={styles.scroll}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      {/* CURVED FOREST HERO HEADER */}
      <View style={styles.heroHeader}>
        {isExplorerSimulation && (
          <View style={styles.explorerSimBanner}>
            <Text style={styles.explorerSimBannerText}>
              Simulación en: {result.terrain.zone_name}
            </Text>
            <TouchableOpacity
              onPress={onClearExplorerSimulation}
              style={styles.explorerSimBackBtn}
            >
              <Text style={styles.explorerSimBackBtnText}>
                Volver a Mi Chacra
              </Text>
            </TouchableOpacity>
          </View>
        )}
        <View style={styles.heroTopRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.heroOverline}>
              {lang === "qu"
                ? "2 WATA TARPUY MUYUY (2026–2027)"
                : "ROTACIÓN DE CULTIVOS A 2 AÑOS"}
            </Text>
            <Text style={styles.heroTitle}>
              {lang === "qu"
                ? "3 Ñankuna Chakraykipaq"
                : "Elige el mejor camino para tu tierra"}
            </Text>
          </View>

          <TouchableOpacity
            onPress={handleToggleSpeech}
            style={[
              styles.listenHeroBtn,
              isSpeaking && { backgroundColor: COLORS.crimsonRisk },
            ]}
            activeOpacity={0.85}
          >
            {isSpeaking ? (
              <VolumeX size={16} color="#FFFFFF" />
            ) : (
              <Volume2 size={16} color={COLORS.forestDeep} />
            )}
            <Text
              style={[
                styles.listenHeroBtnText,
                isSpeaking && { color: "#FFFFFF" },
              ]}
            >
              {isSpeaking
                ? lang === "qu"
                  ? "Sayachiy"
                  : "Detener"
                : lang === "qu"
                  ? "Uyariy"
                  : "Escuchar"}
            </Text>
          </TouchableOpacity>
        </View>

        {/* 3 STRATEGY PILL TABS */}
        <StrategyPillTabs
          strategies={result.strategies}
          activeStrategyId={activeStrat.id}
          recommendedStrategyId={result.recommended_strategy_id}
          lang={lang}
          onSelectStrategy={setSelectedId}
        />
      </View>

      <View style={styles.bodyPadding}>
        {/* ACTIVE STRATEGY OVERVIEW CARD */}
        <StrategyOverviewCard
          activeStrat={activeStrat}
          seedConstraintSummary={result.seed_constraint_summary}
          bareMonthsCount={bareMonthsCount}
          lang={lang}
        />

        {/* PASO A PASO: LAS 4 CAMPAÑAS (2026–2027) + BOLSILLO A 2 AÑOS */}
        <PhaseTimelineSection
          activeStrat={activeStrat}
          marginDelta={marginDelta}
          lang={lang}
          economicReferenceLabel={result.biophysical.provenance.economic_reference_label}
        />

        {/* ¿POR QUÉ SE SUGIERE ESTE PLAN? (RESPALDO NASA + SUELO LOCAL) */}
        <View style={styles.card}>
          <View style={styles.iconHeadingRow}>
            <Sparkles size={18} color={COLORS.agroPrimary} />
            <Text style={styles.cardTitle}>
              {lang === "qu"
                ? "¿Imaraykutaq kay muyuy qampaq allin?"
                : "¿Por qué te conviene esta rotación?"}
            </Text>
          </View>

          <View style={styles.bulletGroup}>
            <View style={styles.bulletRow}>
              <CheckCircle2 size={16} color={COLORS.agroPrimary} />
              <Text style={styles.bulletText}>
                {translateCropText(activeStrat.explainability.why_suggested, lang)}
              </Text>
            </View>
            <View style={styles.bulletRow}>
              <CheckCircle2 size={16} color={COLORS.agroPrimary} />
              <Text style={styles.bulletText}>
                {translateCropText(
                  activeStrat.explainability.quantified_benefits.summary,
                  lang
                )}
              </Text>
            </View>
          </View>

          <View style={styles.nasaEvidenceBox}>
            <Text style={styles.nasaEvidenceTitle}>
              {lang === "qu"
                ? "Kitiypi satelitekuna rikusqanku:"
                : "Lo que vieron los satélites de la NASA en tu zona:"}
            </Text>
            <Text style={styles.nasaEvidenceItem}>
              • {translateCropText(activeStrat.explainability.nasa_evidence, lang)}
            </Text>
          </View>
        </View>

        {/* DÓNDE MANDA TU EXPERIENCIA LOCAL (REQUISITO CLAVE DEL RETO NASA) */}
        <View style={styles.humanWisdomCard}>
          <View style={styles.iconHeadingRow}>
            <Eye size={18} color={COLORS.amberFinance} />
            <Text style={styles.cardTitle}>
              {lang === "qu"
                ? "Ñawiyki chanta tarpuq yachayniyki kamachisqan"
                : "Dónde manda tu ojo y experiencia de agricultor"}
            </Text>
          </View>
          <Text style={styles.cardSub}>
            {lang === "qu"
              ? "Satelitekuna hanan pachamanta pachata qhawanku, ichaqa allpaykimanta yachasqaykita mana rantikunchu. Kayta chakraykipi qhaway:"
              : "Los satélites ven el clima desde el espacio, pero no reemplazan lo que tú conoces de tu tierra. Verifica esto en tu chacra:"}
          </Text>

          <View style={styles.bulletGroup}>
            {activeStrat.explainability.human_in_the_loop_gaps.map(
              (item: string, idx: number) => (
                <View key={idx} style={styles.bulletRow}>
                  <AlertTriangle size={15} color={COLORS.amberFinance} />
                  <Text style={styles.bulletText}>
                    {translateCropText(item, lang)}
                  </Text>
                </View>
              )
            )}
          </View>
        </View>

        {/* COLLAPSIBLE PESTICIDE & BIOCONTROL GUIDE */}
        {activeStrat.pesticide_schedule &&
          activeStrat.pesticide_schedule.length > 0 && (
            <View style={styles.card}>
              <TouchableOpacity
                onPress={() => setShowPestGuide((v) => !v)}
                style={styles.collapsibleHeader}
                activeOpacity={0.8}
              >
                <View style={styles.iconHeadingRow}>
                  <Bug size={18} color={COLORS.crimsonRisk} />
                  <View style={{ flex: 1 }}>
                    <Text style={styles.cardTitle}>
                      {lang === "qu"
                        ? "Kurukuna Hark'ay chanta Hampikuna (SENASA)"
                        : "Control de Plagas y Remedios (SENASA)"}
                    </Text>
                    <Text style={styles.cardSub}>
                      {lang === "qu"
                        ? "Hayk'aqmi pacha rikusqanmanhina hampina"
                        : "Cuándo curar con biocontrol o insumos según el clima"}
                    </Text>
                  </View>
                </View>
                {showPestGuide ? (
                  <ChevronUp size={20} color={COLORS.inkSecondary} />
                ) : (
                  <ChevronDown size={20} color={COLORS.inkSecondary} />
                )}
              </TouchableOpacity>

              {showPestGuide && (
                <View style={styles.pestList}>
                  {activeStrat.pesticide_schedule.map((item) => (
                    <View
                      key={`${item.crop_id}-${item.period}`}
                      style={styles.pestCard}
                    >
                      <View style={styles.pestTopRow}>
                        <Text style={styles.pestCropTitle}>
                          {translateCropText(item.crop_name, lang)} (
                          {translateCropText(item.period, lang)})
                        </Text>
                        <View style={styles.carenciaBadge}>
                          <Text style={styles.carenciaText}>
                            {lang === "qu" ? "Suyana" : "Carencia"}:{" "}
                            {item.pre_harvest_interval_days}{" "}
                            {lang === "qu" ? "p'unchaw" : "días"}
                          </Text>
                        </View>
                      </View>
                      <Text style={styles.pestLine}>
                        <Text style={styles.pestBold}>
                          {lang === "qu"
                            ? "Qhawana kurukuna: "
                            : "Plagas a vigilar: "}
                        </Text>
                        {translateCropText(item.target_pests, lang)}
                      </Text>
                      <Text style={styles.pestLine}>
                        <Text
                          style={[
                            styles.pestBold,
                            { color: COLORS.agroPrimary },
                          ]}
                        >
                          {lang === "qu"
                            ? "Pachamama hampi: "
                            : "Opción ecológica: "}
                        </Text>
                        {translateCropText(item.bio_control, lang)}
                      </Text>
                      <Text style={styles.pestLine}>
                        <Text
                          style={[
                            styles.pestBold,
                            { color: COLORS.crimsonRisk },
                          ]}
                        >
                          {lang === "qu" ? "Químico hampi: " : "Control químico: "}
                        </Text>
                        {translateCropText(item.chemical_control, lang)}
                      </Text>
                      <Text style={styles.pestTrigger}>
                        {lang === "qu" ? "Allin pacha: " : "Momento clave: "}
                        {translateCropText(item.when_to_apply, lang)}
                      </Text>
                    </View>
                  ))}
                </View>
              )}
            </View>
          )}

        {/* COLLAPSIBLE 5-AXIS BALANCE RADAR */}
        <View style={styles.card}>
          <TouchableOpacity
            onPress={() => setShowRadar((v) => !v)}
            style={styles.collapsibleHeader}
            activeOpacity={0.8}
          >
            <View style={styles.iconHeadingRow}>
              <Sprout size={18} color={COLORS.agroPrimary} />
              <View style={{ flex: 1 }}>
                <Text style={styles.cardTitle}>
                  {lang === "qu"
                    ? "Allpa chanta Yaku Kuskanchay Siq'i"
                    : "Gráfico de Equilibrio de Suelo y Agua"}
                </Text>
                <Text style={styles.cardSub}>
                  {lang === "qu"
                    ? "Mana muyuymanta qhawarina tupachiy"
                    : "Comparación visual frente a no rotar"}
                </Text>
              </View>
            </View>
            {showRadar ? (
              <ChevronUp size={20} color={COLORS.inkSecondary} />
            ) : (
              <ChevronDown size={20} color={COLORS.inkSecondary} />
            )}
          </TouchableOpacity>

          {showRadar && (
            <View style={{ alignItems: "center", paddingTop: 8 }}>
              <RadarChartSvg
                scores={activeStrat.radar_scores}
                baselineScores={baselineStrat.radar_scores}
                lang={lang}
              />
            </View>
          )}
        </View>
      </View>
    </ScrollView>
  );
};

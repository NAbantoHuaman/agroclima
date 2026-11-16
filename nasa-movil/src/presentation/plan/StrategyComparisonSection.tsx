import React from "react";
import {
  AlertTriangle,
  Award,
  ShieldCheck,
  Sparkles,
} from "lucide-react-native";
import { Text, TouchableOpacity, View } from "react-native";
import { translateCropText } from "../../i18n/translations";
import { COLORS } from "../../theme/tokens";
import type {
  AppLanguage,
  RecommendResponse,
  RotationStrategy,
} from "../../types";
import { styles } from "./RotationPlanTab.styles";

interface StrategyPillTabsProps {
  strategies: RotationStrategy[];
  activeStrategyId: string;
  recommendedStrategyId: string;
  lang: AppLanguage;
  onSelectStrategy: (id: "regenerative" | "resilience" | "baseline") => void;
}

export const StrategyPillTabs: React.FC<StrategyPillTabsProps> = ({
  strategies,
  activeStrategyId,
  recommendedStrategyId,
  lang,
  onSelectStrategy,
}) => (
  <View style={styles.strategyTabsRow}>
    {strategies.map((s) => {
      const active = s.id === activeStrategyId;
      const isRec = s.id === recommendedStrategyId;
      const friendlyLabel =
        s.id === "regenerative"
          ? lang === "qu"
            ? "Allpata Allichay"
            : "Sanar Tierra"
          : s.id === "resilience"
            ? lang === "qu"
              ? "Yakuta Waqaychay"
              : "Cuidar Agua"
            : lang === "qu"
              ? "Kikillan Qhipay"
              : "Seguir Igual";
      return (
        <TouchableOpacity
          key={s.id}
          onPress={() => onSelectStrategy(s.id)}
          style={[styles.stratPill, active && styles.stratPillActive]}
          activeOpacity={0.85}
        >
          {isRec && (
            <View style={styles.recTinyDot}>
              <Sparkles
                size={11}
                color={active ? COLORS.forestDeep : COLORS.limeBright}
              />
            </View>
          )}
          <Text
            style={[
              styles.stratPillTitle,
              active && styles.stratPillTitleActive,
            ]}
          >
            {friendlyLabel}
          </Text>
          <Text
            style={[
              styles.stratPillScore,
              active && styles.stratPillScoreActive,
            ]}
          >
            {s.mcda_score.toFixed(0)}% {lang === "qu" ? "allin" : "apto"}
          </Text>
        </TouchableOpacity>
      );
    })}
  </View>
);

interface StrategyOverviewCardProps {
  activeStrat: RotationStrategy;
  seedConstraintSummary?: RecommendResponse["seed_constraint_summary"];
  bareMonthsCount: number;
  lang: AppLanguage;
}

export const StrategyOverviewCard: React.FC<StrategyOverviewCardProps> = ({
  activeStrat,
  seedConstraintSummary,
  bareMonthsCount,
  lang,
}) => (
  <View style={styles.mainStratCard}>
    <View style={styles.stratBadgeRow}>
      <View style={styles.compatPill}>
        <Award size={15} color={COLORS.agroPrimary} />
        <Text style={styles.compatPillText}>
          {lang === "qu"
            ? "Allpa qhali kaynin chanta ganancia"
            : "Puntaje de salud y ganancia"}
          : {activeStrat.mcda_score.toFixed(0)}/100
        </Text>
      </View>
      {activeStrat.vulnerability_score >= 50 && (
        <View style={styles.riskPill}>
          <AlertTriangle size={14} color={COLORS.crimsonRisk} />
          <Text style={styles.riskPillText}>
            {lang === "qu" ? "Hatun Chiki" : "Riesgo Alto"}
          </Text>
        </View>
      )}
    </View>

    <Text style={styles.stratMainTitle}>
      {translateCropText(activeStrat.title, lang)}
    </Text>
    <Text style={styles.stratMainSub}>
      {translateCropText(activeStrat.subtitle, lang)}
    </Text>

    {(() => {
      const sc = seedConstraintSummary;
      if (!sc || (sc.requested.length === 0 && !sc.note)) return null;
      const text = sc.note
        ? translateCropText(sc.note, lang)
        : sc.unviable.length > 0
          ? lang === "qu"
            ? `Pachamama/altitud rayku wikch'usqa muhukuna: ${sc.unviable
                .map(
                  (u) =>
                    `${translateCropText(u.crop_name, lang)} (${translateCropText(u.reason, lang)})`
                )
                .join("; ")}.`
            : `Semillas descartadas por clima/altitud NASA: ${sc.unviable
                .map((u) => `${u.crop_name} (${u.reason})`)
                .join("; ")}.`
          : lang === "qu"
            ? `Muyuy yuyaychasqa ${sc.evaluated_catalog_count} qhawasqa tarpuykunamanta muhuykikunata ñawpaqchaspa.`
            : `Rotación calculada priorizando tus semillas disponibles entre los ${sc.evaluated_catalog_count} cultivos evaluados.`;
      return (
        <View
          style={[
            styles.seedNoteBox,
            sc.unviable.length > 0 && styles.seedNoteBoxWarn,
          ]}
        >
          <Text style={styles.seedNoteText}>{text}</Text>
        </View>
      );
    })()}

    {/* Highlight if field is left bare / baldío */}
    {bareMonthsCount > 0 ? (
      <View style={styles.bareWarningBanner}>
        <AlertTriangle size={16} color={COLORS.amberFinance} />
        <Text style={styles.bareWarningText}>
          <Text style={{ fontWeight: "700" }}>
            {lang === "qu"
              ? `Ch'usaq chakra willay (${bareMonthsCount} killa mana qhatayuq): `
              : `Alerta de campo baldío (${bareMonthsCount} meses sin cobertura): `}
          </Text>
          {lang === "qu"
            ? "Allpata q'alata saqiptiykiqa wayra, qasa chanta ñawpaq parakuna allpa kallpanta apakapun."
            : "Dejar la tierra desnuda expone tu chacra a que el viento, las heladas y las primeras lluvias laven los nutrientes."}
        </Text>
      </View>
    ) : (
      <View style={styles.coveredSuccessBanner}>
        <ShieldCheck size={16} color={COLORS.agroPrimary} />
        <Text style={styles.coveredSuccessText}>
          {lang === "qu"
            ? "Chakraykiqa kawsachkaq saphikunawan chanta qhataywan 24 killapi waqaychasqa kachkan."
            : "Tu chacra permanece protegida con raíces vivas y cobertura vegetal durante los 24 meses."}
        </Text>
      </View>
    )}
  </View>
);

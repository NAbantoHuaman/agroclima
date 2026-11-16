import React from "react";
import { Coins } from "lucide-react-native";
import { Text, View } from "react-native";
import { translateCropText } from "../../i18n/translations";
import { COLORS } from "../../theme/tokens";
import type { AppLanguage, RotationStrategy } from "../../types";
import { styles } from "./RotationPlanTab.styles";

interface PhaseTimelineSectionProps {
  activeStrat: RotationStrategy;
  marginDelta: number;
  lang: AppLanguage;
  economicReferenceLabel?: string;
}

export const PhaseTimelineSection: React.FC<PhaseTimelineSectionProps> = ({
  activeStrat,
  marginDelta,
  lang,
  economicReferenceLabel,
}) => (
  <>
    {/* PASO A PASO: LAS 4 CAMPAÑAS (2026–2027) */}
    <View style={styles.card}>
      <Text style={styles.cardTitle}>
        {lang === "qu"
          ? "4 Mita Tarpuy Ñan (2026–2027)"
          : "Paso a paso: tus 4 campañas (2026–2027)"}
      </Text>
      <Text style={styles.cardSub}>
        {lang === "qu"
          ? "Sapa tarpuy allpata wakichin chanta qhipa tarpuypaq kurukunata kuchun:"
          : "Cada cultivo prepara la tierra y corta las plagas para el siguiente:"}
      </Text>

      <View style={styles.phasesContainer}>
        {activeStrat.phases.map((ph, idx) => {
          const isBare = ph.crop_id === "suelo_desnudo";
          return (
            <View
              key={`${ph.period}-${idx}`}
              style={[
                styles.phaseStepCard,
                isBare && styles.phaseStepCardBare,
              ]}
            >
              <View
                style={[
                  styles.phaseNumberCircle,
                  { backgroundColor: ph.color || COLORS.agroPrimary },
                ]}
              >
                <Text style={styles.phaseNumberText}>{idx + 1}</Text>
              </View>

              <View style={{ flex: 1, gap: 3 }}>
                <View style={styles.phaseHeaderRow}>
                  <Text style={styles.phaseSeasonLabel}>
                    {translateCropText(ph.phase_name, lang)}
                  </Text>
                  <Text style={styles.phasePeriodBadge}>
                    {translateCropText(ph.period, lang)}
                  </Text>
                </View>

                <Text style={styles.phaseCropTitle}>
                  {translateCropText(ph.crop_name, lang)}
                </Text>
                <Text style={styles.phaseRoleDescription}>
                  {translateCropText(ph.role, lang)}
                </Text>
              </View>
            </View>
          );
        })}
      </View>
    </View>

    {/* TU BOLSILLO A 2 AÑOS (DARK GREEN FROSTED ECONOMICS CARD) */}
    <View style={styles.pocketCard}>
      <View style={styles.pocketTopRow}>
        <View style={styles.pocketTitleWrap}>
          <Coins size={18} color={COLORS.limeBright} />
          <Text style={styles.pocketTitle}>
            {lang === "qu"
              ? "2 Watapi Qullqiyki (huk hectáreapi)"
              : "Tu Bolsillo en 2 Años (por hectárea)"}
          </Text>
        </View>
        <View style={styles.bcPill}>
          <Text style={styles.bcPillText}>
            {activeStrat.metrics.benefit_cost_ratio != null
              ? `${lang === "qu" ? "Kutichiy" : "Retorno"} ${activeStrat.metrics.benefit_cost_ratio.toFixed(1)}x`
              : `${lang === "qu" ? "Kutichiy" : "Retorno"} --`}
          </Text>
        </View>
      </View>

      <View style={styles.pocketGrid}>
        <View style={styles.pocketCell}>
          <Text style={styles.pocketCellLabel}>
            {lang === "qu" ? "Qhispisqa Ganancia" : "Ganancia Libre"}
          </Text>
          <Text style={[styles.pocketCellVal, { color: COLORS.limeBright }]}>
            S/{" "}
            {(
              activeStrat.metrics.net_margin_2yr_soles_ha ?? 0
            ).toLocaleString("es-PE")}
          </Text>
          <Text style={styles.pocketCellHint}>
            {lang === "qu" ? "gastokunata qichuspa" : "descontando gastos"}
          </Text>
        </View>

        <View style={styles.pocketCell}>
          <Text style={styles.pocketCellLabel}>
            {lang === "qu" ? "Muhupi Gasto" : "Gasto en Semillas"}
          </Text>
          <Text style={styles.pocketCellVal}>
            S/{" "}
            {(
              activeStrat.metrics.seed_cost_2yr_soles_ha ?? 0
            ).toLocaleString("es-PE")}
          </Text>
          <Text style={styles.pocketCellHint}>
            {lang === "qu" ? "4 tarpuykunapi" : "las 4 campañas"}
          </Text>
        </View>

        <View style={styles.pocketCell}>
          <Text style={styles.pocketCellLabel}>
            {lang === "qu" ? "Llapan Churay" : "Inversión Total"}
          </Text>
          <Text style={styles.pocketCellVal}>
            S/{" "}
            {(
              activeStrat.metrics.total_cost_2yr_soles_ha ?? 0
            ).toLocaleString("es-PE")}
          </Text>
          <Text style={styles.pocketCellHint}>
            {lang === "qu" ? "muhu + llamk'aqkuna" : "semilla + jornales"}
          </Text>
        </View>

        <View style={styles.pocketCell}>
          <Text style={styles.pocketCellLabel}>
            {lang === "qu" ? "Allin Kay vs Mana Muyuy" : "Ventaja vs No Rotar"}
          </Text>
          <Text
            style={[
              styles.pocketCellVal,
              {
                color: marginDelta >= 0 ? "#86EFAC" : "#FCA5A5",
              },
            ]}
          >
            {marginDelta >= 0 ? "+" : ""}S/{" "}
            {Math.round(marginDelta).toLocaleString("es-PE")}
          </Text>
          <Text style={styles.pocketCellHint}>
            {lang === "qu"
              ? "sapa kuti hukllata tarpuymanta"
              : "frente a monocultivo"}
          </Text>
        </View>
      </View>

      <Text
        style={{
          fontSize: 10.5,
          lineHeight: 14,
          color: COLORS.inkOnDarkMuted,
        }}
      >
        {lang === "qu"
          ? "Qullqi chani: MIDAGRI SISAP, Agromercado, EMMSA chanta INIA Cajamarca tupuykunawan chacraman t'ikrasqa."
          : economicReferenceLabel ||
            "Precios oficiales MIDAGRI / EMMSA ajustados a chacra + Ref. campaña INIA Cajamarca."}
      </Text>
    </View>
  </>
);

import React, { useState } from "react";
import {
  Activity,
  AlertTriangle,
  CloudRain,
  Minus,
  Plus,
  RotateCcw,
  Snowflake,
  Thermometer,
} from "lucide-react-native";
import { Dimensions, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import Svg, { Line, Polyline, Rect, Text as SvgText } from "react-native-svg";
import { translateCropText, type MobileUiDictionary } from "../i18n/translations";
import { COLORS, DISPLAY_FONT, MONO_FONT } from "../theme/tokens";
import type {
  AppLanguage,
  ClimateScenario,
  FrostFrequency,
  RecommendResponse,
} from "../types";

interface ClimateOutlookTabProps {
  t: MobileUiDictionary;
  lang: AppLanguage;
  result: RecommendResponse | null;
  climateScenario: ClimateScenario;
  onChangeScenario: (next: ClimateScenario) => void;
}

const CHART_W = Math.min(360, Dimensions.get("window").width - 56);
const CHART_H = 175;

export const ClimateOutlookTab: React.FC<ClimateOutlookTabProps> = ({
  t,
  lang,
  result,
  climateScenario,
  onChangeScenario,
}) => {
  const [chartMode, setChartMode] = useState<"rain" | "temp">("rain");
  const [showAll, setShowAll] = useState(false);

  if (!result?.biophysical.climate_20yr || !result.climate_outlook_20yr) return null;

  const c20 = result.biophysical.climate_20yr;
  const out20 = result.climate_outlook_20yr;
  const timeline = c20.timeline_22yr;

  // Build SVG coordinates for 2006..2027 (22 points)
  const values = timeline.map((pt) =>
    chartMode === "rain"
      ? pt.precip_hist_mm ?? pt.precip_proj_mm ?? 0
      : pt.temp_hist_c ?? pt.temp_proj_c ?? 0
  );
  const minVal = Math.min(...values) * (chartMode === "rain" ? 0.86 : 0.94);
  const maxVal = Math.max(...values) * (chartMode === "rain" ? 1.12 : 1.06);
  const padL = 34;
  const padR = 10;
  const padT = 16;
  const padB = 22;
  const plotW = CHART_W - padL - padR;
  const plotH = CHART_H - padT - padB;

  const toX = (idx: number) => padL + (idx / Math.max(1, timeline.length - 1)) * plotW;
  const toY = (v: number) =>
    padT + plotH - ((v - minVal) / Math.max(0.1, maxVal - minVal)) * plotH;

  const histEndIdx = timeline.findIndex((pt) => pt.period_type === "projected");
  const splitIdx = histEndIdx > 0 ? histEndIdx - 1 : timeline.length - 3;

  const histPoints = timeline
    .slice(0, splitIdx + 1)
    .map((_pt, i) => `${toX(i).toFixed(1)},${toY(values[i]).toFixed(1)}`)
    .join(" ");

  const projPoints = timeline
    .slice(splitIdx)
    .map((_, offset) => {
      const i = splitIdx + offset;
      return `${toX(i).toFixed(1)},${toY(values[i]).toFixed(1)}`;
    })
    .join(" ");

  const visibleCrops = showAll ? out20.crop_viability : out20.crop_viability.slice(0, 8);

  const stepRain = (delta: number) =>
    onChangeScenario({
      ...climateScenario,
      rain_delta_pct: Math.max(-25, Math.min(15, climateScenario.rain_delta_pct + delta)),
    });

  const stepTemp = (delta: number) =>
    onChangeScenario({
      ...climateScenario,
      temp_delta_c: Number(
        Math.max(0, Math.min(2.0, climateScenario.temp_delta_c + delta)).toFixed(1)
      ),
    });

  return (
    <ScrollView
      style={styles.scroll}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      {/* 20YR -> 2YR CHART */}
      <View style={styles.card}>
        <Text style={styles.overline}>{t.climate.title20yr}</Text>
        <Text style={styles.subText}>{translateCropText(out20.headline, lang)}</Text>

        <View style={styles.modeSwitch}>
          <TouchableOpacity
            onPress={() => setChartMode("rain")}
            style={[styles.modeBtn, chartMode === "rain" && styles.modeBtnActive]}
          >
            <CloudRain size={13} color={chartMode === "rain" ? "#FFFFFF" : COLORS.nasaCobalt} />
            <Text style={[styles.modeBtnText, chartMode === "rain" && { color: "#FFFFFF" }]}>
              {t.climate.rainMode}
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            onPress={() => setChartMode("temp")}
            style={[styles.modeBtn, chartMode === "temp" && styles.modeBtnActive]}
          >
            <Thermometer size={13} color={chartMode === "temp" ? "#FFFFFF" : COLORS.amberFinance} />
            <Text style={[styles.modeBtnText, chartMode === "temp" && { color: "#FFFFFF" }]}>
              {t.climate.tempMode}
            </Text>
          </TouchableOpacity>
        </View>

        <View style={styles.chartContainer}>
          <Svg width={CHART_W} height={CHART_H}>
            {/* Projection background highlight */}
            <Rect
              x={toX(splitIdx)}
              y={padT}
              width={CHART_W - padR - toX(splitIdx)}
              height={plotH}
              fill="rgba(180, 83, 9, 0.08)"
            />

            {/* Grid lines */}
            {[0, 0.5, 1].map((frac) => {
              const y = padT + plotH * frac;
              const val = maxVal - (maxVal - minVal) * frac;
              return (
                <React.Fragment key={frac}>
                  <Line
                    x1={padL}
                    y1={y}
                    x2={CHART_W - padR}
                    y2={y}
                    stroke={COLORS.border}
                    strokeWidth={1}
                  />
                  <SvgText
                    x={padL - 4}
                    y={y + 3}
                    fontSize={9}
                    fill={COLORS.inkMuted}
                    textAnchor="end"
                  >
                    {chartMode === "rain" ? Math.round(val) : val.toFixed(1)}
                  </SvgText>
                </React.Fragment>
              );
            })}

            {/* Divider 2025 -> 2026-2027 */}
            <Line
              x1={toX(splitIdx)}
              y1={padT}
              x2={toX(splitIdx)}
              y2={padT + plotH}
              stroke={COLORS.amberFinance}
              strokeWidth={1.3}
              strokeDasharray="3,3"
            />

            {/* Historical polyline */}
            <Polyline
              points={histPoints}
              fill="none"
              stroke={chartMode === "rain" ? COLORS.nasaCobalt : COLORS.agroPrimary}
              strokeWidth={2.2}
            />

            {/* Projected polyline */}
            <Polyline
              points={projPoints}
              fill="none"
              stroke={COLORS.amberFinance}
              strokeWidth={2.4}
              strokeDasharray="4,3"
            />

            {/* X Labels */}
            {[0, Math.floor(splitIdx / 2), splitIdx, timeline.length - 1].map((idx) => (
              <SvgText
                key={idx}
                x={toX(idx)}
                y={CHART_H - 5}
                fontSize={9}
                fontWeight="700"
                fill={idx >= splitIdx ? COLORS.amberFinance : COLORS.inkMuted}
                textAnchor="middle"
              >
                {timeline[idx]?.year}
              </SvgText>
            ))}
          </Svg>
        </View>

        <View style={styles.trendsRow}>
          <View style={styles.trendBox}>
            <Text style={styles.trendLabel}>
              {lang === "qu" ? "20 WATA Q'UÑI" : "TENDENCIA 20A TERMICA"}
            </Text>
            <Text style={styles.trendVal}>
              +{c20.trends.temp_delta_20yr_c.toFixed(1)} C
            </Text>
          </View>
          <View style={styles.trendBox}>
            <Text style={styles.trendLabel}>
              {lang === "qu" ? "20 WATA PARA" : "TENDENCIA 20A LLUVIA"}
            </Text>
            <Text style={styles.trendVal}>
              {c20.trends.precip_delta_20yr_pct >= 0 ? "+" : ""}
              {c20.trends.precip_delta_20yr_pct.toFixed(1)}%
            </Text>
          </View>
          <View style={styles.trendBox}>
            <Text style={styles.trendLabel}>
              {lang === "qu" ? "CHIKI 2026-27" : "RIESGO 2026-27"}
            </Text>
            <Text style={[styles.trendVal, { color: COLORS.amberFinance }]}>
              {translateCropText(out20.risk_level, lang).toUpperCase()}
            </Text>
          </View>
        </View>

        <Text style={styles.explanationText}>
          {translateCropText(out20.farmer_explanation, lang)}
        </Text>
        {(c20.method_disclaimer || out20.method_disclaimer) && (
          <View style={styles.disclaimerBox}>
            <Text style={styles.disclaimerText}>
              {c20.method_disclaimer || out20.method_disclaimer}
            </Text>
          </View>
        )}
      </View>

      {/* WHAT-IF CLIMATE SIMULATOR */}
      <View style={styles.card}>
        <View style={styles.simHeader}>
          <Activity size={15} color={COLORS.nasaCobalt} />
          <Text style={[styles.overline, { color: COLORS.nasaCobalt }]}>
            {t.climate.simulatorTitle}
          </Text>
        </View>
        <Text style={styles.subText}>{t.climate.simulatorSub}</Text>

        {/* Rain delta control */}
        <View style={styles.controlRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.controlLabel}>{t.climate.rainDelta}</Text>
            <Text style={styles.controlValue}>
              {climateScenario.rain_delta_pct >= 0 ? "+" : ""}
              {climateScenario.rain_delta_pct}% ({result.simulated_climate.summary.annual_precip_mm} mm/{lang === "qu" ? "w" : "a"})
            </Text>
          </View>
          <View style={styles.stepperGroup}>
            <TouchableOpacity onPress={() => stepRain(-5)} style={styles.stepBtn}>
              <Minus size={14} color={COLORS.inkPrimary} />
            </TouchableOpacity>
            <TouchableOpacity onPress={() => stepRain(5)} style={styles.stepBtn}>
              <Plus size={14} color={COLORS.inkPrimary} />
            </TouchableOpacity>
          </View>
        </View>

        {/* Temp delta control */}
        <View style={styles.controlRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.controlLabel}>{t.climate.tempDelta}</Text>
            <Text style={styles.controlValue}>
              +{climateScenario.temp_delta_c.toFixed(1)} C ({lang === "qu" ? "Pisi" : "Min"}{" "}
              {result.simulated_climate.summary.min_temp_c.toFixed(1)} C)
            </Text>
          </View>
          <View style={styles.stepperGroup}>
            <TouchableOpacity onPress={() => stepTemp(-0.2)} style={styles.stepBtn}>
              <Minus size={14} color={COLORS.inkPrimary} />
            </TouchableOpacity>
            <TouchableOpacity onPress={() => stepTemp(0.2)} style={styles.stepBtn}>
              <Plus size={14} color={COLORS.inkPrimary} />
            </TouchableOpacity>
          </View>
        </View>

        {/* Frost frequency */}
        <View style={{ gap: 6 }}>
          <Text style={styles.controlLabel}>{t.climate.frostMode}</Text>
          <View style={styles.frostRow}>
            {(["normal", "moderada", "severa"] as FrostFrequency[]).map((f) => {
              const active = climateScenario.frost_frequency === f;
              const frostLbl =
                lang === "qu"
                  ? f === "normal"
                    ? "Kikin"
                    : f === "moderada"
                      ? "Chawpi"
                      : "Sinchiy"
                  : f;
              return (
                <TouchableOpacity
                  key={f}
                  onPress={() => onChangeScenario({ ...climateScenario, frost_frequency: f })}
                  style={[styles.frostBtn, active && styles.frostBtnActive]}
                >
                  <Snowflake size={12} color={active ? "#FFFFFF" : COLORS.nasaCobalt} />
                  <Text style={[styles.frostBtnText, active && { color: "#FFFFFF" }]}>
                    {frostLbl.toUpperCase()}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>
        </View>

        <View style={styles.simQuickActions}>
          <TouchableOpacity
            onPress={() => onChangeScenario(out20.recommended_20yr_scenario)}
            style={styles.simPrimaryBtn}
          >
            <AlertTriangle size={13} color="#FFFFFF" />
            <Text style={styles.simPrimaryText}>{t.climate.applyHistoryScenario}</Text>
          </TouchableOpacity>
          <TouchableOpacity
            onPress={() =>
              onChangeScenario({ rain_delta_pct: 0, temp_delta_c: 0, frost_frequency: "normal" })
            }
            style={styles.simResetBtn}
          >
            <RotateCcw size={13} color={COLORS.inkPrimary} />
            <Text style={styles.simResetText}>{t.climate.resetScenario}</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* CROP VIABILITY SEMAPHORE (2026-2027) */}
      <View style={styles.card}>
        <View style={styles.semHeader}>
          <Text style={styles.overline}>{t.climate.semaphoreTitle}</Text>
          <TouchableOpacity onPress={() => setShowAll((p) => !p)} style={styles.toggleAllBtn}>
            <Text style={styles.toggleAllText}>
              {showAll ? t.climate.showTop8 : t.climate.showAll(out20.crop_viability.length)}
            </Text>
          </TouchableOpacity>
        </View>

        <View style={styles.semList}>
          {visibleCrops.map((item) => {
            const statusColor =
              item.status_2027 === "optimo_resiliente"
                ? COLORS.agroPrimary
                : item.status_2027 === "viable_con_rotacion"
                ? COLORS.amberFinance
                : COLORS.crimsonRisk;
            const statusTag =
              item.status_2027 === "optimo_resiliente"
                ? lang === "qu"
                  ? "ALLINPUNI"
                  : "OPTIMO"
                : item.status_2027 === "viable_con_rotacion"
                  ? lang === "qu"
                    ? "MUYUYPI"
                    : "ROTACION"
                  : lang === "qu"
                    ? "CHIKI"
                    : "RIESGO";

            return (
              <View key={item.crop_id} style={styles.semItem}>
                <View style={styles.semTopRow}>
                  <View style={styles.semNameRow}>
                    <View style={[styles.colorBar, { backgroundColor: statusColor }]} />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.semCrop}>
                        {translateCropText(item.crop_name, lang)}
                      </Text>
                      <Text style={styles.semCat}>
                        {translateCropText(item.category, lang)}
                      </Text>
                    </View>
                  </View>
                  <View style={[styles.statusTag, { borderColor: statusColor }]}>
                    <Text style={[styles.statusTagText, { color: statusColor }]}>
                      {statusTag}
                    </Text>
                  </View>
                </View>

                <View style={styles.scoreTriplet}>
                  <View style={styles.triBox}>
                    <Text style={styles.triLbl}>
                      {lang === "qu" ? "20W ÑAWPA" : "BASE 20A"}
                    </Text>
                    <Text style={styles.triVal}>{item.suitability_now.toFixed(0)}/100</Text>
                  </View>
                  <View style={styles.triBox}>
                    <Text style={styles.triLbl}>2026</Text>
                    <Text style={styles.triVal}>{item.suitability_2026.toFixed(0)}/100</Text>
                  </View>
                  <View style={styles.triBox}>
                    <Text style={styles.triLbl}>2027</Text>
                    <Text style={[styles.triVal, { color: statusColor }]}>
                      {item.suitability_2027.toFixed(0)}/100
                    </Text>
                  </View>
                </View>

                <View style={styles.progressTrack}>
                  <View
                    style={[
                      styles.progressFill,
                      {
                        width: `${Math.min(100, Math.max(8, item.suitability_2027))}%`,
                        backgroundColor: statusColor,
                      },
                    ]}
                  />
                </View>

                {item.seed_cost_soles_ha !== undefined && (
                  <View style={styles.econPills}>
                    <Text style={styles.econPill}>
                      {lang === "qu" ? "Muhu" : "Semilla"} S/ {item.seed_cost_soles_ha.toLocaleString("es-PE")}/ha
                    </Text>
                    <Text style={styles.econPill}>
                      {lang === "qu" ? "Ganancia" : "Margen"} S/ {(item.net_margin_soles_ha ?? 0).toLocaleString("es-PE")}/ha
                    </Text>
                    <Text style={styles.econPill}>
                      {lang === "qu" ? "K/G" : "B/C"} {(item.benefit_cost_ratio ?? 1).toFixed(2)}x
                    </Text>
                    {item.chacra_price_soles_kg != null && (
                      <Text style={styles.econPill}>
                        {lang === "qu" ? "Chacra" : "Chacra est."} S/ {item.chacra_price_soles_kg.toFixed(2)}/kg
                      </Text>
                    )}
                    {item.price_source && (
                      <Text style={[styles.econPill, styles.econPillSource]}>
                        {item.price_source}
                        {item.price_date ? ` · ${item.price_date}` : ""}
                      </Text>
                    )}
                  </View>
                )}

                <Text style={styles.semAdvice}>
                  {translateCropText(item.farmer_advice, lang)}
                </Text>
              </View>
            );
          })}
        </View>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  scroll: { flex: 1, backgroundColor: COLORS.canvas },
  content: { padding: 14, gap: 12, paddingBottom: 28 },
  card: {
    backgroundColor: COLORS.surface,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: COLORS.border,
    padding: 14,
    gap: 10,
  },
  overline: {
    fontFamily: MONO_FONT,
    fontSize: 10.5,
    fontWeight: "700",
    color: COLORS.agroPrimary,
    letterSpacing: 0.7,
    flex: 1,
  },
  subText: { fontSize: 12, color: COLORS.inkSecondary, lineHeight: 17 },
  modeSwitch: { flexDirection: "row", gap: 8 },
  modeBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 8,
    borderRadius: 9,
    borderWidth: 1,
    borderColor: COLORS.border,
    backgroundColor: COLORS.surfaceSubtle,
  },
  modeBtnActive: { backgroundColor: COLORS.obsidian, borderColor: COLORS.obsidian },
  modeBtnText: { fontSize: 12, fontWeight: "700", color: COLORS.inkPrimary },
  chartContainer: {
    alignItems: "center",
    backgroundColor: COLORS.surfaceSubtle,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: COLORS.border,
    paddingVertical: 8,
  },
  trendsRow: { flexDirection: "row", gap: 8 },
  trendBox: {
    flex: 1,
    backgroundColor: COLORS.surfaceSubtle,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: COLORS.border,
    padding: 8,
  },
  trendLabel: { fontFamily: MONO_FONT, fontSize: 9, fontWeight: "700", color: COLORS.inkMuted },
  trendVal: { fontFamily: MONO_FONT, fontSize: 13.5, fontWeight: "700", color: COLORS.inkPrimary, marginTop: 2 },
  explanationText: { fontSize: 12.5, color: COLORS.inkPrimary, lineHeight: 18 },
  simHeader: { flexDirection: "row", alignItems: "center", gap: 6 },
  controlRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: COLORS.surfaceSubtle,
    borderRadius: 11,
    borderWidth: 1,
    borderColor: COLORS.border,
    padding: 10,
    gap: 8,
  },
  controlLabel: { fontFamily: MONO_FONT, fontSize: 10, fontWeight: "700", color: COLORS.inkMuted },
  controlValue: { fontFamily: MONO_FONT, fontSize: 13, fontWeight: "700", color: COLORS.inkPrimary, marginTop: 2 },
  stepperGroup: { flexDirection: "row", gap: 6 },
  stepBtn: {
    width: 34,
    height: 34,
    borderRadius: 8,
    backgroundColor: COLORS.surface,
    borderWidth: 1,
    borderColor: COLORS.borderStrong,
    alignItems: "center",
    justifyContent: "center",
  },
  frostRow: { flexDirection: "row", gap: 6 },
  frostBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 5,
    paddingVertical: 8,
    borderRadius: 9,
    borderWidth: 1,
    borderColor: COLORS.border,
    backgroundColor: COLORS.surfaceSubtle,
  },
  frostBtnActive: { backgroundColor: COLORS.nasaCobalt, borderColor: COLORS.nasaCobalt },
  frostBtnText: { fontFamily: MONO_FONT, fontSize: 10.5, fontWeight: "700", color: COLORS.inkPrimary },
  simQuickActions: { flexDirection: "row", gap: 8, marginTop: 2 },
  simPrimaryBtn: {
    flex: 1.4,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 5,
    backgroundColor: COLORS.amberFinance,
    borderRadius: 10,
    paddingVertical: 10,
  },
  simPrimaryText: { fontSize: 11.5, fontWeight: "700", color: "#FFFFFF" },
  simResetBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 5,
    backgroundColor: COLORS.surfaceSubtle,
    borderWidth: 1,
    borderColor: COLORS.borderStrong,
    borderRadius: 10,
    paddingVertical: 10,
  },
  simResetText: { fontSize: 11.5, fontWeight: "700", color: COLORS.inkPrimary },
  semHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8 },
  toggleAllBtn: {
    backgroundColor: COLORS.surfaceSubtle,
    borderWidth: 1,
    borderColor: COLORS.border,
    paddingHorizontal: 9,
    paddingVertical: 5,
    borderRadius: 8,
  },
  toggleAllText: { fontSize: 11, fontWeight: "700", color: COLORS.inkPrimary },
  semList: { gap: 10 },
  semItem: {
    backgroundColor: COLORS.surfaceSubtle,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: COLORS.border,
    padding: 11,
    gap: 8,
  },
  semTopRow: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", gap: 8 },
  semNameRow: { flex: 1, flexDirection: "row", alignItems: "center", gap: 8 },
  colorBar: { width: 4, height: 28, borderRadius: 2 },
  semCrop: { fontFamily: DISPLAY_FONT, fontSize: 13.5, fontWeight: "700", color: COLORS.inkPrimary },
  semCat: { fontSize: 11, color: COLORS.inkMuted },
  statusTag: { borderWidth: 1, borderRadius: 6, paddingHorizontal: 7, paddingVertical: 2 },
  statusTagText: { fontFamily: MONO_FONT, fontSize: 9.5, fontWeight: "700" },
  scoreTriplet: { flexDirection: "row", gap: 6 },
  triBox: {
    flex: 1,
    backgroundColor: COLORS.surface,
    borderRadius: 8,
    padding: 7,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  triLbl: { fontFamily: MONO_FONT, fontSize: 9, color: COLORS.inkMuted },
  triVal: { fontFamily: MONO_FONT, fontSize: 12.5, fontWeight: "700", color: COLORS.inkPrimary, marginTop: 1 },
  progressTrack: { height: 5, borderRadius: 3, backgroundColor: COLORS.border, overflow: "hidden" },
  progressFill: { height: "100%", borderRadius: 3 },
  econPills: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  econPill: {
    fontFamily: MONO_FONT,
    fontSize: 10,
    fontWeight: "700",
    color: COLORS.amberFinance,
    backgroundColor: COLORS.amberSoft,
    paddingHorizontal: 7,
    paddingVertical: 3,
    borderRadius: 6,
  },
  econPillSource: {
    color: COLORS.inkSecondary,
    backgroundColor: COLORS.surfaceSubtle,
  },
  semAdvice: { fontSize: 11.5, color: COLORS.inkSecondary, lineHeight: 16 },
  disclaimerBox: {
    backgroundColor: COLORS.surfaceSubtle,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: COLORS.border,
    padding: 9,
  },
  disclaimerText: { fontSize: 10.5, color: COLORS.inkMuted, lineHeight: 15 },
});

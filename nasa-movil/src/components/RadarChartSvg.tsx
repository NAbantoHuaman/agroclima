import React from "react";
import { StyleSheet, View } from "react-native";
import Svg, { Circle, Line, Polygon, Text as SvgText } from "react-native-svg";
import { COLORS } from "../theme/tokens";
import type { AppLanguage } from "../types";

interface RadarChartSvgProps {
  scores: {
    water_conservation: number;
    soil_fertility: number;
    erosion_control: number;
    pest_break: number;
    commercial_forage: number;
  };
  baselineScores?: {
    water_conservation: number;
    soil_fertility: number;
    erosion_control: number;
    pest_break: number;
    commercial_forage: number;
  };
  size?: number;
  lang?: AppLanguage;
}

const AXES_ES: Array<{ key: keyof RadarChartSvgProps["scores"]; label: string }> = [
  { key: "water_conservation", label: "AGUA" },
  { key: "soil_fertility", label: "SUELO / N" },
  { key: "erosion_control", label: "EROSION" },
  { key: "pest_break", label: "PLAGAS" },
  { key: "commercial_forage", label: "RENTA" },
];

const AXES_QU: Array<{ key: keyof RadarChartSvgProps["scores"]; label: string }> = [
  { key: "water_conservation", label: "YAKU" },
  { key: "soil_fertility", label: "ALLPA / N" },
  { key: "erosion_control", label: "APAKUY" },
  { key: "pest_break", label: "KURU" },
  { key: "commercial_forage", label: "GANANCIA" },
];

export const RadarChartSvg: React.FC<RadarChartSvgProps> = ({
  scores,
  baselineScores,
  size = 246,
  lang = "es",
}) => {
  const AXES = lang === "qu" ? AXES_QU : AXES_ES;
  const cx = size / 2;
  const cy = size / 2;
  const radius = size * 0.34;
  const rings = [25, 50, 75, 100];

  const polar = (idx: number, val: number) => {
    const angle = (Math.PI * 2 * idx) / AXES.length - Math.PI / 2;
    const r = (Math.max(0, Math.min(100, val)) / 100) * radius;
    return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)] as const;
  };

  const toPoints = (src: RadarChartSvgProps["scores"]) =>
    AXES.map((a, i) => polar(i, src[a.key]).join(",")).join(" ");

  return (
    <View style={styles.wrap}>
      <Svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {rings.map((ring) => (
          <Polygon
            key={ring}
            points={AXES.map((_, i) => polar(i, ring).join(",")).join(" ")}
            fill="none"
            stroke={COLORS.border}
            strokeWidth={1}
          />
        ))}

        {AXES.map((a, i) => {
          const [x2, y2] = polar(i, 100);
          const [lx, ly] = polar(i, 121);
          return (
            <React.Fragment key={a.key}>
              <Line
                x1={cx}
                y1={cy}
                x2={x2}
                y2={y2}
                stroke={COLORS.borderStrong}
                strokeWidth={1}
              />
              <SvgText
                x={lx}
                y={ly + 3}
                fontSize={9.5}
                fontWeight="700"
                fill={COLORS.inkSecondary}
                textAnchor="middle"
              >
                {a.label}
              </SvgText>
            </React.Fragment>
          );
        })}

        {baselineScores && (
          <Polygon
            points={toPoints(baselineScores)}
            fill="rgba(185, 28, 28, 0.1)"
            stroke={COLORS.crimsonRisk}
            strokeWidth={1.3}
            strokeDasharray="4,3"
          />
        )}

        <Polygon
          points={toPoints(scores)}
          fill="rgba(15, 83, 56, 0.22)"
          stroke={COLORS.agroPrimary}
          strokeWidth={2.2}
        />

        {AXES.map((a, i) => {
          const [px, py] = polar(i, scores[a.key]);
          return (
            <Circle
              key={`pt-${a.key}`}
              cx={px}
              cy={py}
              r={3.5}
              fill={COLORS.agroPrimary}
              stroke="#FFFFFF"
              strokeWidth={1.2}
            />
          );
        })}
      </Svg>
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: {
    alignItems: "center",
    justifyContent: "center",
  },
});

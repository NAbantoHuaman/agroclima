import React from "react";
import Svg, {
  Circle,
  Defs,
  G,
  LinearGradient,
  Path,
  Rect,
  Stop,
} from "react-native-svg";

/** Vector Weather Cloud & Sun illustration reflecting live condition */
export const WeatherCloudSvg: React.FC<{
  frostRisk: string;
  weatherType?: "sunny" | "partly_cloudy" | "cloudy" | "rainy" | "frost";
}> = ({ frostRisk, weatherType }) => {
  const effectiveType =
    weatherType || (frostRisk === "Alto" ? "frost" : "partly_cloudy");
  return (
    <Svg width={84} height={54} viewBox="0 0 84 54">
      <Defs>
        <LinearGradient id="sunGrad" x1="0" y1="0" x2="1" y2="1">
          <Stop offset="0%" stopColor="#FDE047" />
          <Stop offset="100%" stopColor="#F59E0B" />
        </LinearGradient>
        <LinearGradient id="cloudGrad" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0%" stopColor="#FFFFFF" />
          <Stop offset="100%" stopColor="#CBD5E1" />
        </LinearGradient>
      </Defs>
      {effectiveType === "sunny" ? (
        <G>
          <Circle cx="44" cy="26" r="15" fill="url(#sunGrad)" />
          <Circle cx="44" cy="26" r="20" fill="#FDE047" opacity={0.22} />
        </G>
      ) : (
        <>
          {(effectiveType === "partly_cloudy" || effectiveType === "frost") && (
            <Circle
              cx="56"
              cy="20"
              r="12"
              fill={effectiveType === "frost" ? "#BAE6FD" : "url(#sunGrad)"}
              opacity={0.92}
            />
          )}
          <Path
            d="M24 40 H60 C66.6 40 72 34.8 72 28.5 C72 22.8 67.6 18.1 61.8 17.3 C59.4 10.6 52.8 6 45 6 C35.1 6 27 13.8 26.8 23.5 C21.2 24.4 17 29.1 17 34.8 C17 37.9 19.8 40 24 40 Z"
            fill="url(#cloudGrad)"
            opacity={effectiveType === "cloudy" ? 0.96 : 1}
          />
          {effectiveType === "rainy" && (
            <G>
              <Path
                d="M31 43 L28 50 M42 43 L39 50 M53 43 L50 50 M62 43 L59 50"
                stroke="#60A5FA"
                strokeWidth="2.4"
                strokeLinecap="round"
              />
            </G>
          )}
          {effectiveType === "frost" && (
            <G>
              <Circle cx="32" cy="46" r="2.3" fill="#93C5FD" />
              <Circle cx="44" cy="48" r="2.3" fill="#BAE6FD" />
              <Circle cx="56" cy="46" r="2.3" fill="#93C5FD" />
            </G>
          )}
        </>
      )}
    </Svg>
  );
};

/** Decorative Andean Field Card Artwork */
export const FieldLandscapeSvg: React.FC<{ accentColor: string }> = ({
  accentColor,
}) => (
  <Svg
    width="100%"
    height={116}
    viewBox="0 0 320 116"
    preserveAspectRatio="none"
  >
    <Defs>
      <LinearGradient id="sky" x1="0" y1="0" x2="1" y2="1">
        <Stop offset="0%" stopColor="#1B3920" />
        <Stop offset="100%" stopColor="#2F5D34" />
      </LinearGradient>
      <LinearGradient id="hill1" x1="0" y1="0" x2="0" y2="1">
        <Stop offset="0%" stopColor="#467E3E" />
        <Stop offset="100%" stopColor="#274E2B" />
      </LinearGradient>
      <LinearGradient id="hill2" x1="0" y1="0" x2="1" y2="0">
        <Stop offset="0%" stopColor={accentColor} stopOpacity="0.85" />
        <Stop offset="100%" stopColor="#74C344" stopOpacity="0.9" />
      </LinearGradient>
    </Defs>
    <Rect x="0" y="0" width="320" height="116" fill="url(#sky)" />
    <Circle cx="268" cy="28" r="18" fill="#FDE047" opacity={0.22} />
    <Circle cx="268" cy="28" r="11" fill="#FACC15" opacity={0.45} />
    <Path
      d="M0 76 Q75 42 165 68 T320 54 L320 116 L0 116 Z"
      fill="url(#hill1)"
    />
    <Path
      d="M0 92 Q110 64 215 88 T320 76 L320 116 L0 116 Z"
      fill="url(#hill2)"
    />
    {/* Terrace furrow lines */}
    <Path
      d="M18 104 Q115 80 230 100"
      stroke="rgba(255,255,255,0.28)"
      strokeWidth="2"
      fill="none"
    />
    <Path
      d="M45 112 Q140 92 275 108"
      stroke="rgba(255,255,255,0.22)"
      strokeWidth="1.6"
      fill="none"
    />
  </Svg>
);

import React, { useEffect, useRef } from "react";
import { Animated, Easing, StyleSheet, Text, View } from "react-native";
import Svg, {
  Circle,
  Defs,
  Ellipse,
  G,
  LinearGradient,
  Path,
  Stop,
} from "react-native-svg";
import { Satellite } from "lucide-react-native";
import { COLORS, DISPLAY_FONT } from "../theme/tokens";

export const GrowingPlantLoader: React.FC = () => {
  const orbitSpin = useRef(new Animated.Value(0)).current;
  const pulseA = useRef(new Animated.Value(0)).current;
  const pulseB = useRef(new Animated.Value(0)).current;
  const sproutGrow = useRef(new Animated.Value(0.35)).current;
  const sway = useRef(new Animated.Value(0)).current;
  const dropletRise = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const orbitLoop = Animated.loop(
      Animated.timing(orbitSpin, {
        toValue: 1,
        duration: 9000,
        easing: Easing.linear,
        useNativeDriver: true,
      })
    );

    const pulseLoopA = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseA, {
          toValue: 1,
          duration: 2100,
          easing: Easing.out(Easing.quad),
          useNativeDriver: true,
        }),
        Animated.timing(pulseA, {
          toValue: 0,
          duration: 0,
          useNativeDriver: true,
        }),
      ])
    );

    const pulseLoopB = Animated.loop(
      Animated.sequence([
        Animated.delay(1050),
        Animated.timing(pulseB, {
          toValue: 1,
          duration: 2100,
          easing: Easing.out(Easing.quad),
          useNativeDriver: true,
        }),
        Animated.timing(pulseB, {
          toValue: 0,
          duration: 0,
          useNativeDriver: true,
        }),
      ])
    );

    const sproutLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(sproutGrow, {
          toValue: 1,
          duration: 1550,
          easing: Easing.out(Easing.back(1.25)),
          useNativeDriver: true,
        }),
        Animated.delay(550),
        Animated.timing(sproutGrow, {
          toValue: 0.72,
          duration: 1100,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
      ])
    );

    const swayLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(sway, {
          toValue: 1,
          duration: 1600,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
        Animated.timing(sway, {
          toValue: -1,
          duration: 1600,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
      ])
    );

    const dropletLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(dropletRise, {
          toValue: 1,
          duration: 1700,
          easing: Easing.out(Easing.cubic),
          useNativeDriver: true,
        }),
        Animated.timing(dropletRise, {
          toValue: 0,
          duration: 0,
          useNativeDriver: true,
        }),
      ])
    );

    orbitLoop.start();
    pulseLoopA.start();
    pulseLoopB.start();
    sproutLoop.start();
    swayLoop.start();
    dropletLoop.start();

    return () => {
      orbitLoop.stop();
      pulseLoopA.stop();
      pulseLoopB.stop();
      sproutLoop.stop();
      swayLoop.stop();
      dropletLoop.stop();
    };
  }, [dropletRise, orbitSpin, pulseA, pulseB, sproutGrow, sway]);

  const orbitRotate = orbitSpin.interpolate({
    inputRange: [0, 1],
    outputRange: ["0deg", "360deg"],
  });

  const counterRotate = orbitSpin.interpolate({
    inputRange: [0, 1],
    outputRange: ["0deg", "-360deg"],
  });

  const waveAScale = pulseA.interpolate({
    inputRange: [0, 1],
    outputRange: [0.66, 1.32],
  });
  const waveAOpacity = pulseA.interpolate({
    inputRange: [0, 0.25, 1],
    outputRange: [0, 0.55, 0],
  });

  const waveBScale = pulseB.interpolate({
    inputRange: [0, 1],
    outputRange: [0.66, 1.32],
  });
  const waveBOpacity = pulseB.interpolate({
    inputRange: [0, 0.25, 1],
    outputRange: [0, 0.5, 0],
  });

  const sproutScale = sproutGrow.interpolate({
    inputRange: [0.35, 1],
    outputRange: [0.72, 1.04],
  });
  const sproutTranslateY = sproutGrow.interpolate({
    inputRange: [0.35, 1],
    outputRange: [18, -3],
  });
  const swayRotate = sway.interpolate({
    inputRange: [-1, 1],
    outputRange: ["-3.2deg", "3.2deg"],
  });

  const dropTranslateY = dropletRise.interpolate({
    inputRange: [0, 1],
    outputRange: [15, -40],
  });
  const dropOpacity = dropletRise.interpolate({
    inputRange: [0, 0.3, 0.8, 1],
    outputRange: [0, 0.9, 0.65, 0],
  });

  return (
    <View style={styles.root}>
      {/* Main Orbital & Sprout Stage */}
      <View style={styles.stage}>
        {/* Expanding radar telemetry waves */}
        <Animated.View
          style={[
            styles.sonarRing,
            {
              opacity: waveAOpacity,
              transform: [{ scale: waveAScale }],
            },
          ]}
        />
        <Animated.View
          style={[
            styles.sonarRing,
            {
              opacity: waveBOpacity,
              transform: [{ scale: waveBScale }],
            },
          ]}
        />

        {/* Soft ambient glowing core */}
        <View style={styles.ambientCore} />

        {/* Rotating orbital satellite ring */}
        <Animated.View
          style={[
            styles.orbitLayer,
            { transform: [{ rotate: orbitRotate }] },
          ]}
        >
          <Svg width={286} height={286} viewBox="0 0 224 224">
            <Circle
              cx={112}
              cy={112}
              r={98}
              stroke="rgba(163, 230, 53, 0.32)"
              strokeWidth={1.5}
              strokeDasharray="6 8"
              fill="none"
            />
            <Circle
              cx={112}
              cy={14}
              r={4.5}
              fill={COLORS.limeBright}
            />
            <Circle
              cx={210}
              cy={112}
              r={3}
              fill="rgba(56, 189, 248, 0.85)"
            />
          </Svg>
          <Animated.View
            style={[
              styles.satelliteNode,
              { transform: [{ rotate: counterRotate }] },
            ]}
          >
            <Satellite size={18} color={COLORS.forestDeep} strokeWidth={2.4} />
          </Animated.View>
        </Animated.View>

        {/* Rising nutrient & moisture droplets */}
        <Animated.View
          style={[
            styles.dropletLayer,
            {
              opacity: dropOpacity,
              transform: [{ translateY: dropTranslateY }],
            },
          ]}
        >
          <Svg width={178} height={128} viewBox="0 0 140 100">
            <Circle cx={42} cy={72} r={3} fill="#38BDF8" />
            <Circle cx={98} cy={68} r={2.5} fill={COLORS.limeBright} />
            <Circle cx={70} cy={46} r={2.2} fill="#BAE6FD" />
          </Svg>
        </Animated.View>

        {/* Growing & breathing Andean crop */}
        <Animated.View
          style={[
            styles.plantLayer,
            {
              transform: [
                { translateY: sproutTranslateY },
                { scale: sproutScale },
                { rotate: swayRotate },
              ],
            },
          ]}
        >
          <Svg width={204} height={192} viewBox="0 0 160 150">
            <Defs>
              <LinearGradient id="leafLeft" x1="0" y1="1" x2="1" y2="0">
                <Stop offset="0" stopColor="#2F8E49" />
                <Stop offset="1" stopColor="#92EA54" />
              </LinearGradient>
              <LinearGradient id="leafRight" x1="0" y1="0" x2="1" y2="1">
                <Stop offset="0" stopColor="#A3E635" />
                <Stop offset="1" stopColor="#3DA357" />
              </LinearGradient>
            </Defs>
            {/* Central stalk */}
            <Path
              d="M80 120 C79 98, 80 76, 80 56"
              stroke="#7AD447"
              strokeWidth={6.5}
              strokeLinecap="round"
              fill="none"
            />
            <Path
              d="M80 116 C81 96, 80 78, 80 60"
              stroke="#C5F69B"
              strokeWidth={2}
              strokeLinecap="round"
              fill="none"
            />
            {/* Lower left leaf */}
            <Path
              d="M79 92 C52 90, 32 74, 34 55 C52 52, 73 66, 79 92 Z"
              fill="url(#leafLeft)"
            />
            <Path
              d="M76 89 C59 79, 46 69, 39 59"
              stroke="#D2F8B4"
              strokeWidth={1.8}
              strokeLinecap="round"
              fill="none"
            />
            {/* Upper right leaf */}
            <Path
              d="M81 84 C108 82, 128 65, 126 46 C108 43, 87 58, 81 84 Z"
              fill="url(#leafRight)"
            />
            <Path
              d="M84 81 C101 71, 114 61, 120 51"
              stroke="#DCF9C5"
              strokeWidth={1.8}
              strokeLinecap="round"
              fill="none"
            />
            {/* Fresh crown bud */}
            <Path
              d="M80 62 C68 46, 70 25, 80 15 C90 25, 92 46, 80 62 Z"
              fill="#B3F27C"
            />
            <G opacity={0.85}>
              <Circle cx={80} cy={38} r={2.3} fill="#FFFFFF" />
            </G>
          </Svg>
        </Animated.View>

        {/* Grounded Andean soil terrace mound */}
        <View style={styles.soilStage}>
          <Svg width={216} height={76} viewBox="0 0 170 60">
            <Ellipse cx={85} cy={43} rx={68} ry={13} fill="#2A1C10" />
            <Path
              d="M22 44 C44 20, 126 20, 148 44 C126 52, 44 52, 22 44 Z"
              fill="#5C3D24"
            />
            <Path
              d="M36 41 C58 27, 112 27, 134 41"
              stroke="#8B633F"
              strokeWidth={2.5}
              strokeLinecap="round"
              fill="none"
            />
            <Path
              d="M48 45 C68 38, 102 38, 122 45"
              stroke="rgba(163, 230, 53, 0.35)"
              strokeWidth={1.5}
              strokeLinecap="round"
              fill="none"
            />
          </Svg>
        </View>
      </View>

      {/* AgroConecta Branding */}
      <View style={styles.copyBlock}>
        <Text
          style={styles.brandTitle}
          numberOfLines={1}
          adjustsFontSizeToFit
        >
          Agro<Text style={styles.brandTitleAccent}>Conecta</Text>
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  root: {
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 24,
    gap: 18,
  },
  stage: {
    width: 300,
    height: 300,
    alignItems: "center",
    justifyContent: "center",
  },
  sonarRing: {
    position: "absolute",
    width: 226,
    height: 226,
    borderRadius: 113,
    borderWidth: 1.5,
    borderColor: "rgba(163, 230, 53, 0.55)",
    backgroundColor: "rgba(122, 212, 71, 0.05)",
  },
  ambientCore: {
    position: "absolute",
    width: 206,
    height: 206,
    borderRadius: 103,
    backgroundColor: "rgba(56, 142, 73, 0.24)",
    borderWidth: 1,
    borderColor: "rgba(165, 235, 110, 0.2)",
  },
  orbitLayer: {
    position: "absolute",
    width: 286,
    height: 286,
    alignItems: "center",
    justifyContent: "center",
  },
  satelliteNode: {
    position: "absolute",
    top: 2,
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: COLORS.limeAccent,
    alignItems: "center",
    justifyContent: "center",
    elevation: 4,
  },
  dropletLayer: {
    position: "absolute",
    bottom: 66,
    width: 178,
    height: 128,
    alignItems: "center",
  },
  plantLayer: {
    position: "absolute",
    bottom: 43,
    width: 204,
    height: 192,
    alignItems: "center",
  },
  soilStage: {
    position: "absolute",
    bottom: 22,
    width: 216,
    height: 76,
    alignItems: "center",
    justifyContent: "flex-end",
  },
  copyBlock: {
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 12,
  },
  brandTitle: {
    fontFamily: DISPLAY_FONT,
    fontSize: 40,
    fontWeight: "800",
    color: "#FFFFFF",
    letterSpacing: -0.6,
    textAlign: "center",
  },
  brandTitleAccent: {
    color: COLORS.limeAccent,
  },
});

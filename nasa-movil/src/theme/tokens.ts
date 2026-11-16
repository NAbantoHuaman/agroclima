import { Platform } from "react-native";

export const COLORS = {
  // Deep organic forest palette inspired by modern smart-farm companion UI
  obsidian: "#182F1B",
  obsidianCard: "#213E25",
  obsidianBorder: "#2E5433",
  forestDeep: "#162B19",
  forestMid: "#234227",
  forestLight: "#2D5432",
  forestGlass: "rgba(27, 50, 30, 0.86)",
  forestGlassLight: "rgba(38, 69, 42, 0.78)",
  forestGlassBorder: "rgba(255, 255, 255, 0.18)",

  // Bright leaf-lime primary action accent
  limeAccent: "#74C344",
  limeBright: "#85D354",
  limeDark: "#4E9626",
  limeSoft: "#E9F7E0",

  // Warm natural surfaces
  canvas: "#F3F6F1",
  surface: "#FFFFFF",
  surfaceSubtle: "#F7FAF5",
  border: "#E1E8DD",
  borderStrong: "#C8D5C2",

  // Readable human typography colors
  inkPrimary: "#162619",
  inkSecondary: "#435647",
  inkMuted: "#6E8072",
  inkOnDark: "#F7FAF7",
  inkOnDarkMuted: "#B7CBB9",

  // Semantic accents
  agroPrimary: "#265C30",
  agroAccent: "#56A832",
  agroSoft: "#E7F4E3",
  agroBorder: "#BBE0B0",

  nasaCobalt: "#1D5B9E",
  nasaSoft: "#E9F2FC",
  nasaBorder: "#BBD5F2",

  amberFinance: "#B85D14",
  amberSoft: "#FDF5EA",
  amberBorder: "#F3D7B0",

  crimsonRisk: "#BE2E2E",
  crimsonSoft: "#FDF1F1",
  crimsonBorder: "#F2C2C2",
} as const;

export const MONO_FONT = Platform.select({
  ios: "System",
  android: "sans-serif-medium",
  default: "System",
});

export const DISPLAY_FONT = Platform.select({
  ios: "System",
  android: "sans-serif-medium",
  default: "System",
});

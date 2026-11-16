import type {
  ClimateScenario,
  CurrentCropId,
  EquipmentAccess,
  FarmerSoilNotes,
  MarketPreference,
  PriorityWeights,
  WaterAvailability,
} from "../../types";

export const INITIAL_PARAMS: {
  lat: number;
  lon: number;
  parcelId: string | null;
  polygon: [number, number][] | null;
  currentCrop: CurrentCropId;
  waterAvailability: WaterAvailability;
  priorities: PriorityWeights;
  climateScenario: ClimateScenario;
  farmerSoil: FarmerSoilNotes;
} = {
  lat: -7.163,
  lon: -78.51,
  parcelId: null,
  polygon: null,
  currentCrop: "sin_cultivo",
  waterAvailability: "secano",
  priorities: {
    water_conservation: 72,
    soil_fertility: 85,
    erosion_control: 78,
    pest_break: 76,
    commercial_forage: 82,
  },
  climateScenario: {
    rain_delta_pct: 0,
    temp_delta_c: 0,
    frost_frequency: "normal",
  },
  farmerSoil: {
    texture_override: "auto",
    soil_acidity: "normal",
    compaction_or_drainage: "normal",
    local_frost_early: false,
  },
};

export type PriorityPresetId =
  | "equilibrado"
  | "agua"
  | "suelo"
  | "plagas"
  | "mercado";

export const PRIORITY_PILLS: Array<{
  id: PriorityPresetId;
  labelEs: string;
  labelQu: string;
  weights: PriorityWeights;
}> = [
  {
    id: "equilibrado",
    labelEs: "Todo Equilibrado",
    labelQu: "Tukuy Allin",
    weights: {
      water_conservation: 75,
      soil_fertility: 85,
      erosion_control: 78,
      pest_break: 78,
      commercial_forage: 80,
    },
  },
  {
    id: "agua",
    labelEs: "Cuidar el Agua",
    labelQu: "Unuta Waqaychay",
    weights: {
      water_conservation: 98,
      soil_fertility: 72,
      erosion_control: 76,
      pest_break: 68,
      commercial_forage: 60,
    },
  },
  {
    id: "suelo",
    labelEs: "Curar Tierra Cansada",
    labelQu: "Sayk'usqa Allpa",
    weights: {
      water_conservation: 72,
      soil_fertility: 98,
      erosion_control: 92,
      pest_break: 85,
      commercial_forage: 65,
    },
  },
  {
    id: "plagas",
    labelEs: "Cortar Plagas",
    labelQu: "Khurukunata Chinkachiy",
    weights: {
      water_conservation: 70,
      soil_fertility: 84,
      erosion_control: 74,
      pest_break: 98,
      commercial_forage: 72,
    },
  },
  {
    id: "mercado",
    labelEs: "Más Ganancia y Forraje",
    labelQu: "Qullqi & Q'achu",
    weights: {
      water_conservation: 65,
      soil_fertility: 74,
      erosion_control: 68,
      pest_break: 70,
      commercial_forage: 98,
    },
  },
];

export const GOAL_PRIORITY_PRESETS: Record<string, PriorityWeights> = {
  mercado: {
    water_conservation: 72,
    soil_fertility: 76,
    erosion_control: 70,
    pest_break: 78,
    commercial_forage: 98,
  },
  autoconsumo: {
    water_conservation: 85,
    soil_fertility: 88,
    erosion_control: 80,
    pest_break: 85,
    commercial_forage: 65,
  },
  forraje: {
    water_conservation: 78,
    soil_fertility: 84,
    erosion_control: 82,
    pest_break: 76,
    commercial_forage: 95,
  },
  suelo: {
    water_conservation: 88,
    soil_fertility: 98,
    erosion_control: 92,
    pest_break: 88,
    commercial_forage: 60,
  },
};

export const GOAL_MARKET_MAP: Record<string, MarketPreference> = {
  mercado: "grano_comercial",
  forraje: "leche_forraje",
  autoconsumo: "autoconsumo_feria",
  suelo: "autoconsumo_feria",
};

export const WATER_OPTIONS_FALLBACK: Array<{
  id: WaterAvailability;
  label: string;
}> = [
  { id: "secano", label: "Solo lluvia (secano estricto)" },
  {
    id: "cosecha_agua_qocha",
    label: "Cosecha de agua / Qocha / Micro-reservorio",
  },
  { id: "riego_deficitario", label: "Riego por turnos / Riego de auxilio" },
  { id: "riego_gravedad", label: "Acequia / Riego por gravedad" },
  {
    id: "riego_melgas_surcos",
    label: "Surcos / Melgas en contorno (sin erosión)",
  },
  { id: "riego_aspersion", label: "Riego por aspersión" },
  { id: "riego_goteo", label: "Riego tecnificado por goteo / fertirriego" },
];

export const WATER_SHORT_LABELS: Record<WaterAvailability, string> = {
  secano: "Solo lluvia (secano)",
  cosecha_agua_qocha: "Qocha / Reservorio",
  riego_deficitario: "Riego por turnos",
  riego_gravedad: "Riego por gravedad",
  riego_melgas_surcos: "Surcos en contorno",
  riego_aspersion: "Aspersión",
  riego_goteo: "Riego por goteo",
};

export const WATER_HINTS: Record<WaterAvailability, string> = {
  secano: "Depende 100% de la lluvia estacional",
  cosecha_agua_qocha: "Almacenamiento en reservorio o qocha",
  riego_deficitario: "Riego suplementario por turnos de agua",
  riego_gravedad: "Conducción por canal o acequia comunal",
  riego_melgas_surcos: "Surcos en contorno para frenar erosión",
  riego_aspersion: "Distribución uniforme a presión media",
  riego_goteo: "Máxima eficiencia hídrica y fertirriego",
};

export type SatelliteLayerId = "clean" | "ndvi" | "smap" | "frost" | "erosion";

export const SATELLITE_LAYERS: Array<{
  id: SatelliteLayerId;
  label: string;
  shortTag: string;
  polyFill: string;
  polyStroke: string;
  explanation: string;
}> = [
  {
    id: "clean",
    label: "Vista Satelital Limpia",
    shortTag: "Mapa Base",
    polyFill: "rgba(163, 230, 53, 0.14)",
    polyStroke: "#A3E635",
    explanation:
      "Mapa satelital limpio sin capas encima para ubicar y dibujar tu chacra con claridad. Toca Humedad, Salud Vegetal, Heladas o Calidad de Suelo para ver sus capas.",
  },
  {
    id: "ndvi",
    label: "Verdor y Salud de Plantas",
    shortTag: "Sentinel-2",
    polyFill: "rgba(92, 214, 92, 0.52)",
    polyStroke: "#86EFAC",
    explanation:
      "Muestra qué tan verde y fuerte crece la vegetación desde el satélite. Verde intenso significa buena cobertura vegetal.",
  },
  {
    id: "smap",
    label: "Humedad en el Suelo",
    shortTag: "NASA SMAP",
    polyFill: "rgba(56, 189, 248, 0.50)",
    polyStroke: "#7DD3FC",
    explanation:
      "Estima cuánta agua guarda la tierra cerca de las raíces para saber si aguantará días sin lluvia.",
  },
  {
    id: "frost",
    label: "Frío, Heladas y Calor",
    shortTag: "NASA / ECOSTRESS",
    polyFill: "rgba(251, 191, 36, 0.50)",
    polyStroke: "#FDE68A",
    explanation:
      "Avisa si la madrugada enfría mucho (riesgo de helada) o si hace demasiado calor al mediodía.",
  },
  {
    id: "erosion",
    label: "Inclinación y Cuidado del Suelo",
    shortTag: "Relieve NASA",
    polyFill: "rgba(167, 139, 250, 0.48)",
    polyStroke: "#DDD6FE",
    explanation:
      "Mide la inclinación de tu terreno para cuidar la tierra fértil y evitar que las lluvias fuertes la laven.",
  },
];

export const CURRENT_CROP_LABELS: Record<CurrentCropId, string> = {
  sin_cultivo: "Terreno libre (Sin cultivo previo)",
  monocultivo_papa: "Papa repetida (Monocultivo)",
  papa_maiz: "Rotación corta Papa – Maíz",
  pastos_degradados: "Pasto agotado (Ryegrass)",
  cebada_trigo_continuo: "Trigo / Cebada continua",
};

export const CHECKLIST_WATER_OPTIONS: Array<{
  id: WaterAvailability;
  label: string;
}> = [
  { id: "secano", label: "Solo lluvia (Secano)" },
  { id: "riego_gravedad", label: "Acequia / Canal" },
  { id: "riego_goteo", label: "Riego tecnificado" },
  { id: "cosecha_agua_qocha", label: "Qocha / Reservorio" },
];

export const CHECKLIST_CROP_OPTIONS: Array<{
  id: CurrentCropId;
  label: string;
}> = [
  { id: "sin_cultivo", label: "Estuvo en descanso / Libre" },
  { id: "monocultivo_papa", label: "Papa seguida" },
  { id: "papa_maiz", label: "Papa o Maíz" },
  { id: "cebada_trigo_continuo", label: "Cebada / Trigo" },
  { id: "pastos_degradados", label: "Pasto cansado" },
];

export const CHECKLIST_SOIL_OPTIONS: ReadonlyArray<{
  id: "satelite" | "franco_arcilloso" | "arcilloso_pesado" | "franco_arenoso" | "pedregoso";
  label: string;
  matchTex: FarmerSoilNotes["texture_override"];
  isSat: boolean;
}> = [
  {
    id: "satelite",
    label: "No lo sé · Usar dato del satélite",
    matchTex: "auto",
    isSat: true,
  },
  {
    id: "franco_arcilloso",
    label: "Tierra negra / franca",
    matchTex: "franco_arcilloso",
    isSat: false,
  },
  {
    id: "arcilloso_pesado",
    label: "Tierra barrosa / arcilla",
    matchTex: "arcilloso_pesado",
    isSat: false,
  },
  {
    id: "franco_arenoso",
    label: "Tierra arenosa / suelta",
    matchTex: "franco_arenoso",
    isSat: false,
  },
  {
    id: "pedregoso",
    label: "Ladera / con cascajo",
    matchTex: "pedregoso",
    isSat: false,
  },
];

export const CHECKLIST_CLIMATE_OPTIONS: ReadonlyArray<{
  id: "satelite" | "heladas" | "irregular" | "abrigado";
  label: string;
  isSat: boolean;
}> = [
  {
    id: "satelite",
    label: "No lo sé · Usar dato del satélite",
    isSat: true,
  },
  { id: "heladas", label: "Sí, caen heladas fuertes", isSat: false },
  { id: "irregular", label: "Lluvias muy irregulares", isSat: false },
  { id: "abrigado", label: "Zona abrigada / sin helada", isSat: false },
];

export const CHECKLIST_GOAL_OPTIONS: Array<{
  id: "mercado" | "autoconsumo" | "forraje" | "suelo";
  label: string;
}> = [
  { id: "mercado", label: "Para vender en el mercado" },
  { id: "autoconsumo", label: "Consumo familiar y feria" },
  { id: "forraje", label: "Forraje / Ganado lechero" },
  { id: "suelo", label: "Recuperar suelo a bajo costo" },
];

export const EQUIPMENT_OPTIONS: Array<{
  id: EquipmentAccess;
  label: string;
}> = [
  { id: "manual_yunta", label: "Manual / Yunta" },
  { id: "tractor_compartido", label: "Tractor compartido" },
  { id: "mecanizado", label: "Mecanizado propio" },
];

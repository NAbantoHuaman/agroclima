export type CurrentCropId =
  | "sin_cultivo"
  | "monocultivo_papa"
  | "papa_maiz"
  | "pastos_degradados"
  | "cebada_trigo_continuo";

export type WaterAvailability =
  | "secano"
  | "cosecha_agua_qocha"
  | "riego_deficitario"
  | "riego_gravedad"
  | "riego_melgas_surcos"
  | "riego_aspersion"
  | "riego_goteo";

export type EquipmentAccess = "manual_yunta" | "tractor_compartido" | "mecanizado";

export type MarketPreference = "autoconsumo_feria" | "leche_forraje" | "grano_comercial";

export type FieldStatus = "auto" | "con_cultivo" | "terreno_libre";

export type SoilTextureOverride =
  | "auto"
  | "franco_arcilloso"
  | "franco_arenoso"
  | "arcilloso_pesado"
  | "pedregoso";

export type SoilAcidity = "normal" | "acido" | "no_se";

export type SoilCondition = "normal" | "duro_compactado" | "se_encharca";

export interface FarmerSoilNotes {
  texture_override: SoilTextureOverride;
  soil_acidity: SoilAcidity;
  compaction_or_drainage: SoilCondition;
  local_frost_early: boolean;
}

export type FrostFrequency = "normal" | "moderada" | "severa";

export type AppLanguage = "es" | "qu";

export interface PriorityWeights {
  water_conservation: number;
  soil_fertility: number;
  erosion_control: number;
  pest_break: number;
  commercial_forage: number;
}

export interface ClimateScenario {
  rain_delta_pct: number;
  temp_delta_c: number;
  frost_frequency: FrostFrequency;
  apply_20yr_projection?: boolean;
}

export interface BeaconParcel {
  id: string;
  name: string;
  short_name: string;
  zone_type: string;
  lat: number;
  lon: number;
  elevation_m: number;
  slope_pct: number;
  area_ha: number;
  soil_texture: string;
  water_default: WaterAvailability;
  current_crop_default: CurrentCropId;
  frost_risk_window: string;
  primary_hazard: string;
  description: string;
  polygon: [number, number][];
  calibrated_monthly?: unknown;
}

export interface PesticideGuide {
  target_pests: string;
  bio_control: string;
  chemical_control: string;
  when_to_apply: string;
  pre_harvest_interval_days: number;
}

export interface StrategyPesticideItem extends PesticideGuide {
  phase_name: string;
  period: string;
  crop_id: string;
  crop_name: string;
  consumer_benefit?: string;
}

export interface CropInfo {
  id: string;
  name: string;
  scientific_name: string;
  category: string;
  color: string;
  water_req_mm: number;
  water_req_range_mm: [number, number];
  drought_tolerance: number;
  drought_label: string;
  frost_tolerance: number;
  frost_critical_c: number;
  frost_label: string;
  root_depth_cm: number;
  erosion_protection_score: number;
  nitrogen_balance_kg_ha: number;
  organic_matter_score: number;
  pest_break_score: number;
  breaks_pests: string[];
  vulnerable_pests: string[];
  cycle_months: number;
  altitude_min_m: number;
  altitude_max_m: number;
  max_slope_pct: number;
  commercial_forage_value_score: number;
  value_type: string;
  market_note: string;
  farmer_tip: string;
  seed_cost_soles_ha?: number;
  seed_cost_source?: string;
  seed_rate_label?: string;
  total_cost_soles_ha?: number;
  wholesale_price_soles_kg?: number;
  chacra_price_soles_kg?: number;
  farmgate_factor?: number;
  yield_kg_ha_ref?: number;
  gross_income_soles_ha?: number;
  net_margin_soles_ha?: number;
  benefit_cost_ratio?: number;
  price_source?: string;
  price_date?: string;
  price_mode?: CropPriceMode | string;
  price_quote_label?: string;
  consumer_benefit?: string;
  recommended_windows?: string[];
  pesticide_guide?: PesticideGuide;
}

export type CropPriceMode =
  | "en_vivo"
  | "guardado"
  | "mixto_en_vivo"
  | "referencia_inia";

export interface MarketPriceSummary {
  mode: CropPriceMode | string;
  primary_market_code?: string;
  primary_market_label?: string;
  usd_pen_rate?: number | null;
  usd_pen_date?: string | null;
  ipc_food_pct?: number | null;
  ipc_food_date?: string | null;
  live_crops_count: number;
  mixed_crops_count: number;
  inia_fallback_crops_count: number;
  total_crops_count: number;
  sources_used?: string[];
  latest_price_date?: string | null;
  fetched_at?: string | null;
  economic_reference_label: string;
}

export interface GlossaryItem {
  id: string;
  term: string;
  farmer_title: string;
  farmer_explanation: string;
  scientific_explanation: string;
}

export interface WaterOptionItem {
  id: WaterAvailability;
  label: string;
  shortLabel: string;
  effectiveMm: number;
  efficiencyLabel: string;
}

export interface ReferenceLocationItem {
  label: string;
  lat: number;
  lon: number;
  parcel_id?: string | null;
}

export interface ReferenceDataResponse {
  map_center: {
    lat: number;
    lon: number;
    zoom: number;
    label: string;
  };
  beacon_parcels: BeaconParcel[];
  known_locations?: ReferenceLocationItem[];
  agroecological_belts_geojson?: Record<string, unknown>;
  scientific_glossary: GlossaryItem[];
  crops: CropInfo[];
  crops_metadata: {
    region: string;
    altitude_range_m: string;
    sources: string[];
    market_summary?: MarketPriceSummary | null;
  };
  market_summary?: MarketPriceSummary | null;
  current_crop_options: { id: CurrentCropId; label: string }[];
  water_options: { id: WaterAvailability; label: string }[];
  equipment_options: { id: EquipmentAccess; label: string }[];
  market_options: { id: MarketPreference; label: string }[];
  soil_texture_options: { id: SoilTextureOverride; label: string }[];
  soil_acidity_options: { id: SoilAcidity; label: string }[];
  soil_condition_options: { id: SoilCondition; label: string }[];
  field_status_options?: { id: FieldStatus; label: string }[];
}

export interface SoilProfile {
  ph: number;
  clay_pct: number;
  sand_pct: number;
  silt_pct: number;
  soc_g_kg: number;
  organic_matter_pct: number;
  nitrogen_g_kg: number;
  texture_class: string;
  source_mode: string;
  source_label: string;
  note?: string;
}

export interface TerrainInfo {
  lat: number;
  lon: number;
  elevation_m: number;
  elevation_min_m?: number;
  elevation_max_m?: number;
  elevation_span_m?: number;
  slope_pct: number;
  slope_min_pct?: number;
  slope_max_pct?: number;
  aspect_deg?: number | null;
  aspect_label?: string;
  aspect_insolation_note?: string | null;
  polygon_vertices_sampled?: number;
  vertex_differential_risk?: string | null;
  area_ha: number | null;
  zone_name: string;
  zone_type: string;
  soil_texture: string;
  soil_source?: "reportado_agricultor" | "referencia_zona" | "soilgrids_isric";
  dem_source?: string;
  dem_mode?: string;
  dem_label?: string;
  agro_belt_name?: string;
  nearest_district?: string;
  traditional_local_crops?: string[];
  soil_profile?: SoilProfile;
  frost_risk_window: string;
  primary_hazard: string;
  is_beacon: boolean;
  beacon_id: string | null;
}

export interface MonthlyBiophysicalPoint {
  month_idx: number;
  month: string;
  t2m_c: number;
  t2m_min_c: number;
  precip_mm: number;
  et0_mm: number;
  water_balance_mm: number;
  solar_mj_m2_day: number;
  rh2m_pct: number;
  ndvi: number;
  ndvi_5yr_min: number;
  ndvi_5yr_max: number;
  is_bare_soil: boolean;
  smap_moisture: number;
  smap_anomaly: number;
  gpm_erosive_events: number;
  gpm_max_daily_mm: number;
  erosion_risk: number;
  frost_risk: boolean;
  critical_erosion_window: boolean;
  sim_precip_mm?: number;
  sim_t2m_c?: number;
  sim_t2m_min_c?: number;
  sim_et0_mm?: number;
  sim_water_balance_mm?: number;
  sim_smap_moisture?: number;
  sim_gpm_erosive_events?: number;
  sim_erosion_risk?: number;
  sim_frost_risk?: boolean;
}

export interface BiophysicalSummary {
  annual_precip_mm: number;
  annual_et0_mm: number;
  annual_water_balance_mm: number;
  mean_temp_c: number;
  min_temp_c: number;
  min_temp_month: string;
  current_temp_c?: number;
  current_max_temp_c?: number;
  current_min_temp_c?: number;
  current_rh_pct?: number;
  current_precip_mm?: number;
  current_weather_code?: number;
  current_weather_type?: "sunny" | "partly_cloudy" | "cloudy" | "rainy" | "frost";
  current_weather_label?: string;
  current_weather_source?: string;
  bare_soil_months: string[];
  bare_soil_month_count: number;
  critical_erosion_months: string[];
  frost_risk_months: string[];
  frost_month_count: number;
  dry_anomaly_months: string[];
  erosive_storm_months: string[];
  mean_erosion_risk: number;
  peak_erosion_risk: number;
  mean_smap_moisture: number;
  latest_ndvi?: number;
  latest_ndvi_date?: string | null;
  next_7d_precip_mm?: number | null;
  next_7d_min_temp_c?: number | null;
  frost_alert_7d?: boolean;
}

export interface ForecastDay7d {
  date: string;
  temp_max_c: number;
  temp_min_c: number;
  precip_mm: number;
  weather_code: number;
  weather_type: "sunny" | "partly_cloudy" | "cloudy" | "rainy" | "frost";
  weather_label: string;
}

export interface HistoricalYearPoint {
  year: number;
  precip_mm: number;
  onset_rain_mm: number;
  temp_c: number;
  cold_tmin_c: number;
  et0_mm: number;
  water_balance_mm: number;
  frost_days: number;
  storm_days_12mm: number;
  soil_moisture: number;
}

export interface ProjectedYearPoint {
  year: number;
  precip_mm: number;
  precip_band_low_mm: number;
  precip_band_high_mm: number;
  onset_rain_mm: number;
  temp_c: number;
  et0_mm: number;
  water_balance_mm: number;
  frost_days: number;
  storm_days_12mm: number;
  drought_risk_score: number;
}

export interface Timeline22YrPoint {
  year: number;
  period_type: "historical" | "projected";
  precip_hist_mm: number | null;
  precip_proj_mm: number | null;
  precip_band_low_mm: number | null;
  precip_band_high_mm: number | null;
  temp_hist_c: number | null;
  temp_proj_c: number | null;
  water_balance_mm: number;
  frost_days: number;
  storm_days_12mm: number;
}

export interface Climate20YrData {
  historical_years_count: number;
  historical_range: string;
  projection_years_count: number;
  projection_range: string;
  data_origin: string;
  trends: {
    temp_trend_c_per_decade: number;
    temp_delta_20yr_c: number;
    precip_trend_pct_per_decade: number;
    precip_delta_20yr_pct: number;
    storm_trend_pct_per_decade: number;
    frost_days_trend_per_decade: number;
  };
  milestones: {
    baseline_2025: {
      temp_c: number;
      precip_mm: number;
      et0_mm: number;
      frost_days: number;
    };
    year_2026: {
      temp_c: number;
      precip_mm: number;
      et0_mm: number;
      water_balance_mm: number;
      frost_days: number;
      drought_risk_score: number;
    };
    year_2027: {
      temp_c: number;
      precip_mm: number;
      et0_mm: number;
      water_balance_mm: number;
      frost_days: number;
      drought_risk_score: number;
    };
  };
  historical_series: HistoricalYearPoint[];
  projected_series: ProjectedYearPoint[];
  projection_method?: string;
  method_disclaimer?: string;
  timeline_22yr: Timeline22YrPoint[];
}

export interface CropViability20YrItem {
  crop_id: string;
  crop_name: string;
  category: string;
  color: string;
  suitability_now: number;
  suitability_2026: number;
  suitability_2027: number;
  delta_20yr: number;
  status_2027: "optimo_resiliente" | "viable_con_rotacion" | "alto_riesgo";
  seed_cost_soles_ha?: number;
  seed_cost_source?: string;
  seed_rate_label?: string;
  wholesale_price_soles_kg?: number;
  chacra_price_soles_kg?: number;
  yield_kg_ha_ref?: number;
  gross_income_soles_ha?: number;
  net_margin_soles_ha?: number;
  benefit_cost_ratio?: number;
  price_source?: string;
  price_date?: string;
  price_mode?: CropPriceMode | string;
  price_quote_label?: string;
  consumer_benefit?: string;
  pesticide_guide?: PesticideGuide;
  farmer_advice: string;
}

export interface ClimateOutlook20Yr {
  horizon_years: number;
  base_period: string;
  forecast_period: string;
  projection_method?: string;
  method_disclaimer?: string;
  risk_level: "bajo" | "moderado" | "alto";
  headline: string;
  farmer_explanation: string;
  key_findings: string[];
  recommended_20yr_scenario: ClimateScenario;
  crop_viability: CropViability20YrItem[];
}

export interface SpatialScaleTier {
  tier: string;
  resolution: string;
  sensors: string;
  scope: string;
}

export interface BiophysicalData {
  monthly_series: MonthlyBiophysicalPoint[];
  summary: BiophysicalSummary;
  forecast_7d?: ForecastDay7d[];
  climate_20yr?: Climate20YrData;
  provenance: {
    nasa_power_source: string;
    nasa_power_label: string;
    nasa_power_cache_hit: boolean;
    nasa_power_grid_elev_m: number;
    fetched_at: string;
    economic_reference_label?: string;
    market_summary?: MarketPriceSummary | null;
    erosion_method_label?: string;
    spatial_scale_hierarchy?: SpatialScaleTier[];
    harmonized_datasets: {
      sensor: string;
      resolution: string;
      variables: string;
      mode?: "en_vivo" | "guardado" | "respaldo" | "estimado" | "modelo";
      plain?: string;
    }[];
  };
}

export interface StrategyPhase {
  phase_name: string;
  period: string;
  crop_id: string;
  crop_name: string;
  scientific_name: string;
  role: string;
  is_cover: boolean;
  color: string;
}

export interface StrategyTimelineMonth {
  index: number;
  cal_month_idx: number;
  year?: number;
  label: string;
  is_current_month?: boolean;
  phase_name: string;
  crop_id: string;
  crop_name: string;
  color: string;
  status: "crop" | "cover" | "bare" | "degraded";
  is_bare: boolean;
}

export interface RotationStrategy {
  id: "baseline" | "resilience" | "regenerative";
  title: string;
  subtitle: string;
  mcda_score: number;
  vulnerability_score: number;
  vulnerability_level: string;
  radar_scores: {
    water_conservation: number;
    soil_fertility: number;
    erosion_control: number;
    pest_break: number;
    commercial_forage: number;
  };
  metrics: {
    nitrogen_balance_kg_ha: number;
    organic_matter_score?: number;
    bare_soil_months_24m: number;
    water_savings_pct: number;
    erosion_reduction_pct: number;
    bare_months_avoided: number;
    pest_break_improvement_pct: number;
    water_req_avg_mm: number;
    seed_cost_2yr_soles_ha?: number;
    total_cost_2yr_soles_ha?: number;
    net_margin_2yr_soles_ha?: number;
    benefit_cost_ratio?: number;
  };
  phases: StrategyPhase[];
  pesticide_schedule?: StrategyPesticideItem[];
  timeline_24m: StrategyTimelineMonth[];
  explainability: {
    why_suggested: string;
    nasa_evidence: string;
    quantified_benefits: {
      summary: string;
      water_savings_pct: number;
      nitrogen_balance_kg_ha: number;
      organic_matter_score?: number;
      erosion_reduction_pct: number;
      bare_months_avoided: number;
      pest_break_improvement_pct: number;
    };
    human_in_the_loop_gaps: string[];
  };
}

export interface SimulatedClimate {
  params: ClimateScenario;
  monthly_series: MonthlyBiophysicalPoint[];
  summary: {
    annual_precip_mm: number;
    annual_et0_mm: number;
    annual_water_balance_mm: number;
    wet_season_precip_mm: number;
    min_temp_c: number;
    frost_month_count: number;
    frost_risk_months: string[];
    drought_stress_index: number;
    frost_stress_index: number;
    erosion_stress_index: number;
  };
}

export interface SeasonalContext {
  reference_date_iso: string;
  is_live_clock: boolean;
  reference_month: number;
  reference_year: number;
  reference_month_label: string;
  field_status_effective: "con_cultivo" | "terreno_libre";
  season_id: string;
  season_label: string;
  immediate_action: string;
  next_planting_window: string;
}

export interface SeedConstraintSummary {
  requested: string[];
  viable_used: string[];
  unviable: { crop_id: string; crop_name: string; reason: string }[];
  evaluated_catalog_count: number;
  note?: string | null;
}

export interface RecommendResponse {
  terrain: TerrainInfo;
  biophysical: BiophysicalData;
  seasonal_context: SeasonalContext;
  simulated_climate: SimulatedClimate;
  climate_outlook_20yr?: ClimateOutlook20Yr;
  recommended_strategy_id: "baseline" | "resilience" | "regenerative";
  recommended_strategy_title: string;
  strategies: RotationStrategy[];
  seed_constraint_summary?: SeedConstraintSummary;
}

export interface VoiceChatTurn {
  role: "user" | "assistant";
  text: string;
}

export interface VoiceConfirmedSlots {
  location_confirmed?: boolean;
  map_verified?: boolean;
  crop_confirmed?: boolean;
  water_confirmed?: boolean;
  soil_confirmed?: boolean;
  climate_risk_confirmed?: boolean;
  goal_confirmed?: boolean;
  seeds_checked?: boolean;
  available_seeds?: string[];
  location_label?: string | null;
  prior_crop_detail?: string | null;
  crop_label?: string | null;
  water_label?: string | null;
  soil_label?: string | null;
  climate_risk_label?: string | null;
  goal_label?: string | null;
  last_intent_mode?: string;
  lat?: number;
  lon?: number;
}

export interface EstadoParcela {
  ubicacion_texto?: string | null;
  poligono_confirmado: boolean;
  sistema_riego?: string | null;
  cultivo_anterior?: string | null;
  textura_y_drenaje?: string | null;
  riesgo_climatico?: string | null;
  objetivo_agricultor?: string | null;
  semillas_disponibles?: string[];
}

export interface AccionUi {
  tipo:
    | "ABRIR_MAPA_CUADRADO"
    | "MOSTRAR_PREGUNTA_SLOT"
    | "MOSTRAR_TRES_ROTACIONES"
    | "NINGUNA";
  parametros: {
    lat?: number;
    lng?: number;
    zoom?: number;
    default_polygon?: number[][];
    titulo?: string;
    campo?: string;
    recommended_strategy_id?: string;
  };
}

export interface VoiceQuestionChip {
  label: string;
  value: string;
}

export interface RecommendRequestPayload {
  lat: number;
  lon: number;
  polygon?: [number, number][] | null;
  parcel_id?: string | null;
  current_crop: CurrentCropId;
  water_availability: WaterAvailability;
  equipment_access?: EquipmentAccess;
  market_preference?: MarketPreference;
  farmer_soil?: FarmerSoilNotes;
  priorities: PriorityWeights;
  climate_scenario: ClimateScenario;
  field_status?: FieldStatus;
  planning_month?: number | null;
  planning_year?: number | null;
  available_seeds?: string[];
  custom_zone_label?: string | null;
}

export interface VoiceAssistantRequestPayload extends RecommendRequestPayload {
  transcript: string;
  gps_lat?: number | null;
  gps_lon?: number | null;
  session_slots?: VoiceConfirmedSlots | null;
  history?: VoiceChatTurn[];
  force_calculate?: boolean;
}

export interface VoiceAudioRequestPayload extends RecommendRequestPayload {
  audio_base64: string;
  audio_ext?: string;
  lang?: AppLanguage;
  gps_lat?: number | null;
  gps_lon?: number | null;
  session_slots?: VoiceConfirmedSlots | null;
  history?: VoiceChatTurn[];
  force_calculate?: boolean;
}

export interface VoiceQuickCard {
  title: string;
  badge: string;
  body: string;
}

export interface VoiceAssistantResponse {
  transcript?: string;
  understood: {
    location: string;
    crop: string;
    water: string;
    seeds?: string;
    soil_notes: string[];
    forecast_mode: string;
  };
  use_browser_gps: boolean;
  gps_out_of_region: boolean;
  intent_mode?: "out_of_scope" | "app_help" | "parcel_qa" | "rotation_planning";
  conversation_stage?: "collecting_info" | "ready" | "qa" | "out_of_scope";
  confirmed_slots?: VoiceConfirmedSlots;
  estado_parcela?: EstadoParcela;
  accion_ui?: AccionUi;
  listo_para_nasa?: boolean;
  missing_fields?: string[];
  next_question?: string | null;
  question_field?: string | null;
  question_chips?: VoiceQuestionChip[];
  show_map_picker?: boolean;
  updated_params: {
    lat: number;
    lon: number;
    parcel_id: string | null;
    current_crop: CurrentCropId;
    water_availability: WaterAvailability;
    equipment_access: EquipmentAccess;
    market_preference: MarketPreference;
    farmer_soil: FarmerSoilNotes;
    priorities?: PriorityWeights;
    climate_scenario: ClimateScenario;
    clear_polygon: boolean;
    available_seeds?: string[];
  };
  spoken_response: string;
  quick_cards: VoiceQuickCard[];
  preview_terrain?: TerrainInfo;
  preview_biophysical?: BiophysicalData;
  recommendation: RecommendResponse | null;
}

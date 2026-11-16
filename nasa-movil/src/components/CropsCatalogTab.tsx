import React, { useMemo, useState } from "react";
import {
  Bug,
  ChevronDown,
  ChevronUp,
  CloudRain,
  Coins,
  Droplets,
  Mountain,
  Search,
  Snowflake,
  Sprout,
} from "lucide-react-native";
import {
  FlatList,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { CropPlantImage } from "./CropPlantImage";
import {
  translateCropText,
  type MobileUiDictionary,
} from "../i18n/translations";
import { COLORS, DISPLAY_FONT } from "../theme/tokens";
import type {
  AppLanguage,
  ClimateScenario,
  CropInfo,
  MarketPriceSummary,
  RecommendResponse,
} from "../types";
import { ClimateOutlookTab } from "./ClimateOutlookTab";

interface CropsCatalogTabProps {
  t: MobileUiDictionary;
  lang: AppLanguage;
  crops: CropInfo[];
  marketSummary?: MarketPriceSummary | null;
  result?: RecommendResponse | null;
  climateScenario?: ClimateScenario;
  onChangeScenario?: (next: ClimateScenario) => void;
}

type CatalogFilter =
  | "all"
  | "profitable"
  | "valleys"
  | "nitrogen"
  | "resilient"
  | "forage";

export const CropsCatalogTab: React.FC<CropsCatalogTabProps> = ({
  t,
  lang,
  crops,
  marketSummary,
  result,
  climateScenario,
  onChangeScenario,
}) => {
  const [subView, setSubView] = useState<"semillas" | "clima">("semillas");
  const [filter, setFilter] = useState<CatalogFilter>("all");
  const [query, setQuery] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return crops.filter((c) => {
      if (filter === "profitable" && (c.benefit_cost_ratio ?? 0) < 2.0)
        return false;
      if (filter === "valleys" && c.altitude_min_m > 2200) return false;
      if (filter === "nitrogen" && c.nitrogen_balance_kg_ha <= 0) return false;
      if (
        filter === "resilient" &&
        (c.drought_tolerance < 75 || c.frost_tolerance < 68)
      )
        return false;
      if (filter === "forage" && !c.value_type.toLowerCase().includes("forraj"))
        return false;
      if (q) {
        const hay = `${c.name} ${c.scientific_name} ${c.market_note} ${
          c.consumer_benefit ?? ""
        } ${c.pesticide_guide?.target_pests ?? ""}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [crops, filter, query]);

  const isQu = lang === "qu";
  const filterChips: Array<{ id: CatalogFilter; label: string }> = [
    { id: "all", label: `${isQu ? "Llapan" : "Todos"} (${crops.length})` },
    { id: "profitable", label: isQu ? "Hatun Ganancia" : "Más Rentables" },
    { id: "nitrogen", label: isQu ? "Allpa Kallpachaq" : "Abonan la Tierra" },
    { id: "resilient", label: isQu ? "Ch'aki + Qasa" : "Aguantan Helada/Sequía" },
    { id: "valleys", label: isQu ? "Wayq'u / Qura" : "Valles y Aromáticas" },
    { id: "forage", label: isQu ? "Uywa Q'achu" : "Forraje Ganado" },
  ];

  return (
    <View style={styles.container}>
      {/* CURVED FOREST HERO HEADER */}
      <View style={styles.heroHeader}>
        <View style={styles.topSwitchRow}>
          <TouchableOpacity
            onPress={() => setSubView("semillas")}
            style={[
              styles.subViewBtn,
              subView === "semillas" && styles.subViewBtnActive,
            ]}
            activeOpacity={0.85}
          >
            <Sprout
              size={16}
              color={subView === "semillas" ? COLORS.forestDeep : "#FFFFFF"}
            />
            <Text
              style={[
                styles.subViewBtnText,
                subView === "semillas" && styles.subViewBtnTextActive,
              ]}
            >
              {isQu ? "24 Muhukuna wan Kuru" : "24 Semillas y Plagas"}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            onPress={() => setSubView("clima")}
            style={[
              styles.subViewBtn,
              subView === "clima" && styles.subViewBtnActive,
            ]}
            activeOpacity={0.85}
          >
            <CloudRain
              size={16}
              color={subView === "clima" ? COLORS.forestDeep : "#FFFFFF"}
            />
            <Text
              style={[
                styles.subViewBtnText,
                subView === "clima" && styles.subViewBtnTextActive,
              ]}
            >
              {isQu ? "20 Wata Pacha" : "Clima 20 Años"}
            </Text>
          </TouchableOpacity>
        </View>

        {subView === "semillas" && (
          <>
            <View style={styles.searchWrap}>
              <Search size={16} color={COLORS.inkMuted} />
              <TextInput
                value={query}
                onChangeText={setQuery}
                placeholder={
                  isQu
                    ? "Akshu, tarwi, tomillo, kinwa maskay..."
                    : "Buscar papa, tarwi, tomillo, cochinilla, quinua..."
                }
                placeholderTextColor={COLORS.inkMuted}
                style={styles.searchInput}
              />
            </View>

            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.filterRow}
            >
              {filterChips.map((f) => {
                const active = filter === f.id;
                return (
                  <TouchableOpacity
                    key={f.id}
                    onPress={() => setFilter(f.id)}
                    style={[
                      styles.filterChip,
                      active && styles.filterChipActive,
                    ]}
                  >
                    <Text
                      style={[
                        styles.filterText,
                        active && styles.filterTextActive,
                      ]}
                    >
                      {f.label}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </ScrollView>
          </>
        )}
      </View>

      {subView === "clima" && result && climateScenario && onChangeScenario ? (
        <ClimateOutlookTab
          t={t}
          lang={lang}
          result={result}
          climateScenario={climateScenario}
          onChangeScenario={onChangeScenario}
        />
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
          ListFooterComponent={
            <Text
              style={{
                fontSize: 11,
                lineHeight: 15,
                color: COLORS.inkMuted,
                textAlign: "center",
                paddingHorizontal: 14,
                paddingTop: 6,
                paddingBottom: 16,
              }}
            >
              {isQu
                ? "Muhu chani chanta gananciaqa MIDAGRI SISAP, Agromercado, EMMSA (chacraman t'ikrasqa) chanta INIA Cajamarca tupuykunam."
                : marketSummary?.economic_reference_label ||
                  "Precios oficiales MIDAGRI SISAP / Agromercado / EMMSA ajustados a chacra + Ref. campaña INIA en forrajes."}
            </Text>
          }
          renderItem={({ item: crop }) => {
            const isExpanded = expandedId === crop.id;
            return (
              <View style={styles.cropCard}>
                {/* Visual Top Banner with Real Crop Plant Photo */}
                <View style={styles.cropTopRow}>
                  <CropPlantImage
                    cropId={crop.id}
                    accentColor={crop.color || COLORS.agroPrimary}
                    size={56}
                    borderRadius={16}
                  />

                  <View style={{ flex: 1 }}>
                    <Text style={styles.cropName}>
                      {translateCropText(crop.name, lang)}
                    </Text>
                    <Text style={styles.cropRole} numberOfLines={1}>
                      {translateCropText(crop.value_type, lang)}
                    </Text>
                  </View>

                  <View style={styles.cyclePill}>
                    <Text style={styles.cycleText}>
                      {crop.cycle_months} {isQu ? "killa" : "meses"}
                    </Text>
                  </View>
                </View>

                {/* Plain-language benefit */}
                {crop.consumer_benefit && (
                  <Text style={styles.benefitParagraph}>
                    {translateCropText(crop.consumer_benefit, lang)}
                  </Text>
                )}

                {/* 4 Friendly Specs */}
                <View style={styles.specGrid}>
                  <View style={styles.specBox}>
                    <Droplets size={13} color={COLORS.nasaCobalt} />
                    <Text style={styles.specVal}>{crop.water_req_mm} mm</Text>
                    <Text style={styles.specLbl}>{isQu ? "Yaku" : "Agua"}</Text>
                  </View>
                  <View style={styles.specBox}>
                    <Snowflake size={13} color="#0284C7" />
                    <Text style={styles.specVal}>{crop.frost_critical_c}°C</Text>
                    <Text style={styles.specLbl}>
                      {isQu ? "Qasa chiki" : "Helada mín"}
                    </Text>
                  </View>
                  <View style={styles.specBox}>
                    <Mountain size={13} color={COLORS.agroPrimary} />
                    <Text style={styles.specVal}>
                      {crop.altitude_min_m}-{crop.altitude_max_m}m
                    </Text>
                    <Text style={styles.specLbl}>{isQu ? "Sayaynin" : "Altura"}</Text>
                  </View>
                  <View style={styles.specBox}>
                    <Text
                      style={[
                        styles.specVal,
                        {
                          color:
                            crop.nitrogen_balance_kg_ha >= 0
                              ? COLORS.agroPrimary
                              : COLORS.amberFinance,
                        },
                      ]}
                    >
                      {crop.nitrogen_balance_kg_ha >= 0
                        ? isQu
                          ? "Kallpachan"
                          : "Abona"
                        : isQu
                        ? "Mikun"
                        : "Consume"}
                    </Text>
                    <Text style={styles.specLbl}>
                      {crop.nitrogen_balance_kg_ha >= 0 ? "+" : ""}
                      {crop.nitrogen_balance_kg_ha} kg N
                    </Text>
                  </View>
                </View>

                {/* Seed Cost & Expected Net Profit */}
                {crop.seed_cost_soles_ha !== undefined && (
                  <View style={styles.econBanner}>
                    <View style={styles.econLeft}>
                      <Coins size={15} color={COLORS.agroPrimary} />
                      <View style={{ flex: 1 }}>
                        <Text style={styles.econSeedText}>
                          {isQu ? "Muhu" : "Semilla"}: S/{" "}
                          {crop.seed_cost_soles_ha.toLocaleString("es-PE")}/ha (
                          {translateCropText(crop.seed_rate_label || "", lang)})
                        </Text>
                        <Text style={styles.econProfitText}>
                          {isQu ? "Qullqi ganancia" : "Ganancia libre"}: S/{" "}
                          {(crop.net_margin_soles_ha ?? 0).toLocaleString(
                            "es-PE"
                          )}
                          /ha
                        </Text>
                        {crop.chacra_price_soles_kg != null && (
                          <Text style={styles.econSourceText}>
                            {isQu ? "Chacra chanin" : "Chacra est."}: S/{" "}
                            {crop.chacra_price_soles_kg.toFixed(2)}/kg
                            {crop.wholesale_price_soles_kg != null
                              ? ` (${isQu ? "Qhatu" : "Mayorista"} S/ ${crop.wholesale_price_soles_kg.toFixed(2)})`
                              : ""}
                          </Text>
                        )}
                        {crop.price_source && (
                          <Text style={styles.econMetaText}>
                            {crop.price_mode === "en_vivo"
                              ? "● En vivo"
                              : crop.price_mode === "mixto_en_vivo"
                              ? "◐ En vivo + ref."
                              : crop.price_mode === "guardado"
                              ? "● Guardado"
                              : "○ Referencia"}{" "}
                            · {crop.price_source}
                            {crop.price_date ? ` · ${crop.price_date}` : ""}
                          </Text>
                        )}
                      </View>
                    </View>
                    <View style={styles.bcBadge}>
                      <Text style={styles.bcBadgeText}>
                        {crop.benefit_cost_ratio != null
                          ? `${crop.benefit_cost_ratio.toFixed(1)}x`
                          : "--"}
                      </Text>
                    </View>
                  </View>
                )}

                {/* Collapsible SENASA Pest & Biocontrol Guide */}
                {crop.pesticide_guide && (
                  <View style={styles.pestSection}>
                    <TouchableOpacity
                      onPress={() =>
                        setExpandedId(isExpanded ? null : crop.id)
                      }
                      style={styles.pestToggleBtn}
                      activeOpacity={0.8}
                    >
                      <View style={styles.pestToggleLeft}>
                        <Bug size={15} color={COLORS.crimsonRisk} />
                        <Text style={styles.pestToggleText}>
                          {isQu
                            ? `Kurukunawan hampin (${translateCropText(crop.pesticide_guide.target_pests, lang)})`
                            : `Ver plagas y cómo curar (${crop.pesticide_guide.target_pests})`}
                        </Text>
                      </View>
                      {isExpanded ? (
                        <ChevronUp size={17} color={COLORS.inkSecondary} />
                      ) : (
                        <ChevronDown size={17} color={COLORS.inkSecondary} />
                      )}
                    </TouchableOpacity>

                    {isExpanded && (
                      <View style={styles.pestDetailsBox}>
                        <Text style={styles.pestDetailLine}>
                          <Text
                            style={{
                              fontWeight: "700",
                              color: COLORS.agroPrimary,
                            }}
                          >
                            {isQu ? "Pacha hampi: " : "Control ecológico: "}
                          </Text>
                          {translateCropText(crop.pesticide_guide.bio_control, lang)}
                        </Text>
                        <Text style={styles.pestDetailLine}>
                          <Text
                            style={{
                              fontWeight: "700",
                              color: COLORS.crimsonRisk,
                            }}
                          >
                            {isQu ? "SENASA hampi: " : "Insumo químico: "}
                          </Text>
                          {translateCropText(crop.pesticide_guide.chemical_control, lang)}
                        </Text>
                        <Text style={styles.pestDetailLine}>
                          <Text style={{ fontWeight: "700" }}>
                            {isQu ? "Hayk'aq churana: " : "Cuándo aplicar: "}
                          </Text>
                          {translateCropText(crop.pesticide_guide.when_to_apply, lang)}
                        </Text>
                        <Text style={styles.carenciaNote}>
                          {isQu
                            ? `Pallaymanta ñawpaqta ${crop.pesticide_guide.pre_harvest_interval_days} punchaw suyay.`
                            : `Esperar ${crop.pesticide_guide.pre_harvest_interval_days} días antes de cosechar.`}
                        </Text>
                      </View>
                    )}
                  </View>
                )}
              </View>
            );
          }}
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.canvas,
  },
  heroHeader: {
    backgroundColor: COLORS.forestMid,
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 18,
    borderBottomLeftRadius: 30,
    borderBottomRightRadius: 30,
    gap: 12,
  },
  topSwitchRow: {
    flexDirection: "row",
    backgroundColor: COLORS.forestDeep,
    borderRadius: 22,
    padding: 4,
    gap: 6,
  },
  subViewBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 10,
    borderRadius: 18,
  },
  subViewBtnActive: {
    backgroundColor: COLORS.limeAccent,
  },
  subViewBtnText: {
    fontSize: 13,
    fontWeight: "700",
    color: "#FFFFFF",
  },
  subViewBtnTextActive: {
    color: COLORS.forestDeep,
  },
  searchWrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  searchInput: {
    flex: 1,
    fontSize: 13.5,
    color: COLORS.inkPrimary,
    paddingVertical: 0,
  },
  filterRow: {
    gap: 8,
  },
  filterChip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 18,
    backgroundColor: "rgba(255,255,255,0.14)",
  },
  filterChipActive: {
    backgroundColor: COLORS.limeAccent,
  },
  filterText: {
    fontSize: 12.5,
    fontWeight: "600",
    color: "#FFFFFF",
  },
  filterTextActive: {
    color: COLORS.forestDeep,
    fontWeight: "700",
  },
  listContent: {
    padding: 16,
    gap: 14,
    paddingBottom: 112,
  },
  cropCard: {
    backgroundColor: COLORS.surface,
    borderRadius: 24,
    padding: 16,
    gap: 12,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  cropTopRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  cropIconBadge: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
  },
  cropName: {
    fontFamily: DISPLAY_FONT,
    fontSize: 16.5,
    fontWeight: "700",
    color: COLORS.inkPrimary,
  },
  cropRole: {
    fontSize: 12.5,
    color: COLORS.inkSecondary,
    marginTop: 1,
  },
  cyclePill: {
    backgroundColor: COLORS.agroSoft,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 14,
  },
  cycleText: {
    fontSize: 11.5,
    fontWeight: "700",
    color: COLORS.agroPrimary,
  },
  benefitParagraph: {
    fontSize: 13,
    color: COLORS.inkSecondary,
    lineHeight: 19,
  },
  specGrid: {
    flexDirection: "row",
    gap: 8,
  },
  specBox: {
    flex: 1,
    backgroundColor: COLORS.surfaceSubtle,
    borderRadius: 14,
    paddingVertical: 9,
    paddingHorizontal: 6,
    alignItems: "center",
    gap: 2,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  specVal: {
    fontSize: 12.5,
    fontWeight: "700",
    color: COLORS.inkPrimary,
  },
  specLbl: {
    fontSize: 10.5,
    color: COLORS.inkMuted,
  },
  econBanner: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: COLORS.agroSoft,
    borderRadius: 16,
    padding: 12,
    gap: 8,
  },
  econLeft: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  econSeedText: {
    fontSize: 12.5,
    fontWeight: "700",
    color: COLORS.inkPrimary,
  },
  econProfitText: {
    fontSize: 12,
    color: COLORS.agroPrimary,
    fontWeight: "600",
    marginTop: 2,
  },
  bcBadge: {
    backgroundColor: COLORS.agroPrimary,
    paddingHorizontal: 9,
    paddingVertical: 5,
    borderRadius: 12,
  },
  bcBadgeText: {
    fontSize: 11.5,
    fontWeight: "700",
    color: "#FFFFFF",
  },
  pestSection: {
    borderTopWidth: 1,
    borderTopColor: COLORS.border,
    paddingTop: 10,
    gap: 8,
  },
  pestToggleBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
  },
  pestToggleLeft: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  pestToggleText: {
    flex: 1,
    fontSize: 12.5,
    fontWeight: "700",
    color: COLORS.crimsonRisk,
  },
  pestDetailsBox: {
    backgroundColor: COLORS.crimsonSoft,
    borderRadius: 14,
    padding: 12,
    gap: 5,
  },
  pestDetailLine: {
    fontSize: 12.5,
    color: COLORS.inkPrimary,
    lineHeight: 18,
  },
  carenciaNote: {
    fontSize: 11.5,
    fontWeight: "700",
    color: COLORS.crimsonRisk,
    marginTop: 2,
  },
  econSourceText: {
    fontSize: 11.5,
    fontWeight: "700",
    color: COLORS.inkPrimary,
    marginTop: 2,
  },
  econMetaText: {
    fontSize: 10.5,
    color: COLORS.inkMuted,
    marginTop: 1,
    lineHeight: 14,
  },
});

import React from "react";
import {
  ArrowRight,
  Check,
  CheckCircle2,
  Clock,
  CloudRain,
  Droplets,
  Layers,
  MapPin,
  Satellite,
  Sprout,
  Target,
  Waves,
  X,
} from "lucide-react-native";
import {
  Modal,
  Pressable,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import {
  CHECKLIST_CLIMATE_OPTIONS,
  CHECKLIST_GOAL_OPTIONS,
  CHECKLIST_SOIL_OPTIONS,
  CURRENT_CROP_LABELS,
  EQUIPMENT_OPTIONS,
  WATER_HINTS,
  WATER_SHORT_LABELS,
} from "../../domain/agronomy/constants";
import { translateCropText } from "../../i18n/translations";
import { COLORS } from "../../theme/tokens";
import type {
  AppLanguage,
  CurrentCropId,
  EquipmentAccess,
  FarmerSoilNotes,
  ReferenceDataResponse,
  VoiceConfirmedSlots,
  WaterAvailability,
} from "../../types";
import { styles } from "./InteractiveMapTab.styles";

const WATER_ICONS: Record<
  WaterAvailability,
  React.ComponentType<{ size?: number; color?: string }>
> = {
  secano: CloudRain,
  cosecha_agua_qocha: Waves,
  riego_deficitario: Clock,
  riego_gravedad: Droplets,
  riego_melgas_surcos: Layers,
  riego_aspersion: Sprout,
  riego_goteo: Target,
};

interface ParcelParametersModalProps {
  visible: boolean;
  onClose: () => void;
  isQu: boolean;
  lang: AppLanguage;
  completedChecklistCount: number;
  isPlanReady: boolean;
  voiceSlots: VoiceConfirmedSlots;
  zoneTitle: string;
  estimatedAreaHa: number | null;
  onConfirmParcelPolygon?: (returnToHome?: boolean) => void;
  referenceData: ReferenceDataResponse | null;
  currentCrop: CurrentCropId;
  onSelectChecklistOption?: (
    slotKey: "water" | "crop" | "soil" | "climate" | "goal",
    optionId: string,
    label: string
  ) => void;
  onChangeCrop: (crop: CurrentCropId) => void;
  waterCatalog: Array<{ id: WaterAvailability; label: string }>;
  waterAvailability: WaterAvailability;
  onChangeWater: (water: WaterAvailability) => void;
  farmerSoil: FarmerSoilNotes;
  onChangeFarmerSoil: (soil: FarmerSoilNotes) => void;
  equipmentAccess?: EquipmentAccess;
  onChangeEquipment?: (eq: EquipmentAccess) => void;
  onGoToPlan?: () => void;
}

export const ParcelParametersModal: React.FC<ParcelParametersModalProps> = ({
  visible,
  onClose,
  isQu,
  lang,
  completedChecklistCount,
  isPlanReady,
  voiceSlots,
  zoneTitle,
  estimatedAreaHa,
  onConfirmParcelPolygon,
  referenceData,
  currentCrop,
  onSelectChecklistOption,
  onChangeCrop,
  waterCatalog,
  waterAvailability,
  onChangeWater,
  farmerSoil,
  onChangeFarmerSoil,
  equipmentAccess = "manual_yunta",
  onChangeEquipment,
  onGoToPlan,
}) => {
  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onClose}
    >
      <View style={styles.modalBackdrop}>
        <View style={styles.modalSheet}>
          <View style={styles.modalHeader}>
            <View style={{ flex: 1 }}>
              <Text style={styles.modalOverline}>
                {isQu
                  ? `CHAKRAYKIPA WILLAYNIN (${completedChecklistCount}/6)`
                  : `PARÁMETROS DE MI CHACRA (${completedChecklistCount}/6 LISTOS)`}
              </Text>
              <Text style={styles.modalTitle}>
                {isQu
                  ? "Imaynam chakraykita llamkanki"
                  : "Completa los 6 datos antes de pasar al Plan"}
              </Text>
            </View>
            <Pressable onPress={onClose} style={styles.modalCloseBtn}>
              <X size={18} color={COLORS.inkPrimary} />
            </Pressable>
          </View>

          <ScrollView
            contentContainerStyle={styles.sheetScrollContent}
            showsVerticalScrollIndicator={false}
          >
            {/* 1. Polígono */}
            <View style={styles.sheetSlotHeader}>
              <Text style={styles.sheetSectionTitle}>
                1. Ubicación y polígono en el mapa
              </Text>
              <Text
                style={[
                  styles.sheetStatusTag,
                  voiceSlots.map_verified && styles.sheetStatusTagDone,
                ]}
              >
                {voiceSlots.map_verified ? "Confirmado" : "Pendiente"}
              </Text>
            </View>
            {voiceSlots.map_verified ? (
              <View style={styles.sheetConfirmedRow}>
                <CheckCircle2 size={16} color={COLORS.agroPrimary} />
                <Text style={styles.sheetConfirmedText}>
                  {zoneTitle} ·{" "}
                  {estimatedAreaHa !== null
                    ? `${estimatedAreaHa.toFixed(1)} ha`
                    : "1.0 ha"}
                </Text>
              </View>
            ) : (
              <TouchableOpacity
                onPress={() => onConfirmParcelPolygon?.(false)}
                style={styles.sheetConfirmPolyBtn}
              >
                <MapPin size={15} color="#FFFFFF" />
                <Text style={styles.sheetConfirmPolyBtnText}>
                  Confirmar parcela actual en el mapa (
                  {estimatedAreaHa !== null
                    ? `${estimatedAreaHa.toFixed(1)} ha`
                    : "1.0 ha"}
                  )
                </Text>
              </TouchableOpacity>
            )}

            {/* 2. Cultivo anterior */}
            <View style={styles.sheetSlotHeader}>
              <Text style={styles.sheetSectionTitle}>
                {isQu
                  ? "2. ¿Imatam qipa tarpuypi tarpurqanki?"
                  : "2. ¿Qué sembraste en la última campaña?"}
              </Text>
              <Text
                style={[
                  styles.sheetStatusTag,
                  voiceSlots.crop_confirmed && styles.sheetStatusTagDone,
                ]}
              >
                {voiceSlots.crop_confirmed ? "Listo" : "Pendiente"}
              </Text>
            </View>
            <View style={styles.optionsList}>
              {(referenceData?.current_crop_options?.length
                ? referenceData.current_crop_options
                : (Object.keys(CURRENT_CROP_LABELS) as CurrentCropId[]).map(
                    (id) => ({
                      id,
                      label: CURRENT_CROP_LABELS[id],
                    })
                  )
              ).map((item) => {
                const active =
                  voiceSlots.crop_confirmed && currentCrop === item.id;
                return (
                  <TouchableOpacity
                    key={item.id}
                    onPress={() => {
                      if (onSelectChecklistOption) {
                        onSelectChecklistOption("crop", item.id, item.label);
                      } else {
                        onChangeCrop(item.id);
                      }
                    }}
                    style={[
                      styles.optionCard,
                      active && styles.optionCardActive,
                    ]}
                  >
                    <Sprout
                      size={18}
                      color={active ? COLORS.agroPrimary : COLORS.inkMuted}
                    />
                    <Text
                      style={[
                        styles.optionCardText,
                        active && styles.optionCardTextActive,
                      ]}
                    >
                      {translateCropText(item.label, lang)}
                    </Text>
                    {active && <Check size={18} color={COLORS.agroPrimary} />}
                  </TouchableOpacity>
                );
              })}
            </View>

            {/* 3. Agua / Riego */}
            <View style={styles.sheetSlotHeader}>
              <Text style={styles.sheetSectionTitle}>
                {isQu
                  ? `3. ¿Ima yakuwantaq qarpanki? (${waterCatalog.length})`
                  : "3. ¿Con qué agua cuentas para regar?"}
              </Text>
              <Text
                style={[
                  styles.sheetStatusTag,
                  voiceSlots.water_confirmed && styles.sheetStatusTagDone,
                ]}
              >
                {voiceSlots.water_confirmed ? "Listo" : "Pendiente"}
              </Text>
            </View>
            <View style={styles.optionsList}>
              {waterCatalog.map((w) => {
                const active =
                  voiceSlots.water_confirmed && waterAvailability === w.id;
                const IconComp = WATER_ICONS[w.id] || Droplets;
                return (
                  <TouchableOpacity
                    key={w.id}
                    onPress={() => {
                      if (onSelectChecklistOption) {
                        onSelectChecklistOption(
                          "water",
                          w.id,
                          WATER_SHORT_LABELS[w.id] || w.label
                        );
                      } else {
                        onChangeWater(w.id);
                      }
                    }}
                    style={[
                      styles.optionCard,
                      active && styles.optionCardActive,
                    ]}
                  >
                    <IconComp
                      size={18}
                      color={active ? COLORS.agroPrimary : COLORS.inkMuted}
                    />
                    <View style={{ flex: 1 }}>
                      <Text
                        style={[
                          styles.optionCardText,
                          active && styles.optionCardTextActive,
                        ]}
                      >
                        {translateCropText(w.label, lang)}
                      </Text>
                      <Text style={styles.optionSubText}>
                        {translateCropText(WATER_HINTS[w.id] || w.label, lang)}
                      </Text>
                    </View>
                    {active && <Check size={18} color={COLORS.agroPrimary} />}
                  </TouchableOpacity>
                );
              })}
            </View>

            {/* 4. Textura de suelo (con opción Satélite) */}
            <View style={styles.sheetSlotHeader}>
              <Text style={styles.sheetSectionTitle}>
                {isQu
                  ? "4. ¿Imaynam allpayki llamkachkaptiyki?"
                  : "4. Textura de tierra y pendiente"}
              </Text>
              <Text
                style={[
                  styles.sheetStatusTag,
                  voiceSlots.soil_confirmed && styles.sheetStatusTagDone,
                ]}
              >
                {voiceSlots.soil_confirmed ? "Listo" : "Pendiente"}
              </Text>
            </View>
            <View style={styles.soilChipsGrid}>
              {CHECKLIST_SOIL_OPTIONS.map((item) => {
                const active =
                  voiceSlots.soil_confirmed &&
                  farmerSoil.texture_override === item.matchTex;
                return (
                  <TouchableOpacity
                    key={item.id}
                    onPress={() => {
                      if (onSelectChecklistOption) {
                        onSelectChecklistOption("soil", item.id, item.label);
                      } else {
                        onChangeFarmerSoil({
                          ...farmerSoil,
                          texture_override: item.matchTex,
                        });
                      }
                    }}
                    style={[
                      styles.soilChipBtn,
                      item.isSat && styles.satChipBtn,
                      active && styles.soilChipBtnActive,
                    ]}
                  >
                    {item.isSat && (
                      <Satellite
                        size={13}
                        color={active ? COLORS.forestDeep : COLORS.agroPrimary}
                      />
                    )}
                    <Text
                      style={[
                        styles.soilChipText,
                        item.isSat && styles.satChipText,
                        active && styles.soilChipTextActive,
                      ]}
                    >
                      {item.label}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>

            {/* Opcional: Acidez y Drenaje */}
            <View style={styles.soilChipsGrid}>
              {(
                [
                  {
                    id: "normal",
                    label: isQu ? "Miski allpa (Normal)" : "Suelo dulce / normal",
                  },
                  {
                    id: "acido",
                    label: isQu ? "Puchqu allpa (Jalca)" : "Suelo ácido (jalca)",
                  },
                ] as const
              ).map((item) => {
                const active = farmerSoil.soil_acidity === item.id;
                return (
                  <TouchableOpacity
                    key={item.id}
                    onPress={() =>
                      onChangeFarmerSoil({
                        ...farmerSoil,
                        soil_acidity: item.id,
                      })
                    }
                    style={[
                      styles.soilChipBtn,
                      active && styles.soilChipBtnActive,
                    ]}
                  >
                    <Text
                      style={[
                        styles.soilChipText,
                        active && styles.soilChipTextActive,
                      ]}
                    >
                      {item.label}
                    </Text>
                  </TouchableOpacity>
                );
              })}
              {(
                [
                  {
                    id: "duro_compactado",
                    label: isQu ? "Sinchi takasqa" : "Tierra compactada",
                  },
                  {
                    id: "se_encharca",
                    label: isQu ? "Yaku quchakun" : "Se encharca en lluvia",
                  },
                ] as const
              ).map((item) => {
                const active = farmerSoil.compaction_or_drainage === item.id;
                return (
                  <TouchableOpacity
                    key={item.id}
                    onPress={() =>
                      onChangeFarmerSoil({
                        ...farmerSoil,
                        compaction_or_drainage: active ? "normal" : item.id,
                      })
                    }
                    style={[
                      styles.soilChipBtn,
                      active && styles.soilChipBtnActive,
                    ]}
                  >
                    <Text
                      style={[
                        styles.soilChipText,
                        active && styles.soilChipTextActive,
                      ]}
                    >
                      {item.label}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>

            {/* 5. Riesgo climático local (con opción Satélite) */}
            <View style={styles.sheetSlotHeader}>
              <Text style={styles.sheetSectionTitle}>
                5. Riesgo climático local (Heladas / Lluvias)
              </Text>
              <Text
                style={[
                  styles.sheetStatusTag,
                  voiceSlots.climate_risk_confirmed &&
                    styles.sheetStatusTagDone,
                ]}
              >
                {voiceSlots.climate_risk_confirmed ? "Listo" : "Pendiente"}
              </Text>
            </View>
            <View style={styles.soilChipsGrid}>
              {CHECKLIST_CLIMATE_OPTIONS.map((item) => {
                const active =
                  voiceSlots.climate_risk_confirmed &&
                  voiceSlots.climate_risk_label === item.label;
                return (
                  <TouchableOpacity
                    key={item.id}
                    onPress={() => {
                      if (onSelectChecklistOption) {
                        onSelectChecklistOption("climate", item.id, item.label);
                      } else {
                        onChangeFarmerSoil({
                          ...farmerSoil,
                          local_frost_early: item.id === "heladas",
                        });
                      }
                    }}
                    style={[
                      styles.soilChipBtn,
                      item.isSat && styles.satChipBtn,
                      active && styles.soilChipBtnActive,
                    ]}
                  >
                    {item.isSat && (
                      <Satellite
                        size={13}
                        color={active ? COLORS.forestDeep : COLORS.agroPrimary}
                      />
                    )}
                    <Text
                      style={[
                        styles.soilChipText,
                        item.isSat && styles.satChipText,
                        active && styles.soilChipTextActive,
                      ]}
                    >
                      {item.label}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>

            {/* 6. Objetivo de la campaña */}
            <View style={styles.sheetSlotHeader}>
              <Text style={styles.sheetSectionTitle}>
                6. Objetivo principal de la campaña
              </Text>
              <Text
                style={[
                  styles.sheetStatusTag,
                  voiceSlots.goal_confirmed && styles.sheetStatusTagDone,
                ]}
              >
                {voiceSlots.goal_confirmed ? "Listo" : "Pendiente"}
              </Text>
            </View>
            <View style={styles.soilChipsGrid}>
              {CHECKLIST_GOAL_OPTIONS.map((opt) => {
                const active =
                  voiceSlots.goal_confirmed &&
                  voiceSlots.goal_label === opt.label;
                return (
                  <TouchableOpacity
                    key={opt.id}
                    onPress={() =>
                      onSelectChecklistOption?.("goal", opt.id, opt.label)
                    }
                    style={[
                      styles.soilChipBtn,
                      active && styles.soilChipBtnActive,
                    ]}
                  >
                    <Text
                      style={[
                        styles.soilChipText,
                        active && styles.soilChipTextActive,
                      ]}
                    >
                      {opt.label}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>

            {/* 7. Labranza y equipo disponible */}
            {onChangeEquipment && (
              <>
                <View style={styles.sheetSlotHeader}>
                  <Text style={styles.sheetSectionTitle}>
                    7. Labranza y acceso a equipo
                  </Text>
                </View>
                <View style={styles.soilChipsGrid}>
                  {EQUIPMENT_OPTIONS.map((opt) => {
                    const active = equipmentAccess === opt.id;
                    return (
                      <TouchableOpacity
                        key={opt.id}
                        onPress={() => onChangeEquipment(opt.id)}
                        style={[
                          styles.soilChipBtn,
                          active && styles.soilChipBtnActive,
                        ]}
                      >
                        <Text
                          style={[
                            styles.soilChipText,
                            active && styles.soilChipTextActive,
                          ]}
                        >
                          {opt.label}
                        </Text>
                      </TouchableOpacity>
                    );
                  })}
                </View>
              </>
            )}

            {completedChecklistCount >= 6 || isPlanReady ? (
              <>
                <TouchableOpacity
                  onPress={() => {
                    onClose();
                    onGoToPlan?.();
                  }}
                  style={styles.doneAndGoPlanBtn}
                >
                  <CheckCircle2 size={17} color={COLORS.forestDeep} />
                  <Text style={styles.doneAndGoPlanBtnText}>
                    Pasar al Plan de Rotación
                  </Text>
                  <ArrowRight size={16} color={COLORS.forestDeep} />
                </TouchableOpacity>
                <TouchableOpacity
                  onPress={onClose}
                  style={styles.secondarySheetOutlineBtn}
                >
                  <Text style={styles.secondarySheetOutlineBtnText}>
                    Seguir explorando Mi Chacra
                  </Text>
                </TouchableOpacity>
              </>
            ) : (
              <>
                <TouchableOpacity onPress={onClose} style={styles.doneSheetBtn}>
                  <Text style={styles.doneSheetBtnText}>
                    Guardar avance ({completedChecklistCount}/6 listos)
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  onPress={() => {
                    onClose();
                    onGoToPlan?.();
                  }}
                  style={styles.secondarySheetOutlineBtn}
                >
                  <Text style={styles.secondarySheetOutlineBtnText}>
                    Calcular y pasar al Plan de Rotación
                  </Text>
                  <ArrowRight size={15} color={COLORS.agroPrimary} />
                </TouchableOpacity>
              </>
            )}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
};

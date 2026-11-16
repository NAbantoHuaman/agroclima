import React from "react";
import {
  ArrowRight,
  Check,
  CheckCircle2,
  Compass,
  Layers,
  MapPin,
  Satellite,
  Sparkles,
} from "lucide-react-native";
import { Text, TouchableOpacity, View } from "react-native";
import {
  CHECKLIST_CLIMATE_OPTIONS,
  CHECKLIST_CROP_OPTIONS,
  CHECKLIST_GOAL_OPTIONS,
  CHECKLIST_SOIL_OPTIONS,
  CHECKLIST_WATER_OPTIONS,
  EQUIPMENT_OPTIONS,
} from "../../domain/agronomy/constants";
import { COLORS } from "../../theme/tokens";
import type {
  EquipmentAccess,
  RecommendResponse,
  VoiceConfirmedSlots,
} from "../../types";
import { styles } from "./FarmerHomeTab.styles";

interface ParcelCalibrationChecklistProps {
  hasLocatedParcel: boolean;
  isPlanReady: boolean;
  completedChecklistCount: number;
  voiceSlots: VoiceConfirmedSlots;
  zoneTitle: string;
  terrain: RecommendResponse["terrain"];
  liveMinTempC: number;
  frostRiskLabel: string;
  equipmentAccess?: EquipmentAccess;
  onChangeEquipment?: (eq: EquipmentAccess) => void;
  onNavigateTab: (tab: "mapa" | "plan" | "semillas") => void;
  onSelectChecklistOption?: (
    slotKey: "water" | "crop" | "soil" | "climate" | "goal",
    optionId: string,
    label: string
  ) => void;
  onForceCalculatePlan?: () => void;
}

export const ParcelCalibrationChecklist: React.FC<
  ParcelCalibrationChecklistProps
> = ({
  hasLocatedParcel,
  isPlanReady,
  completedChecklistCount,
  voiceSlots,
  zoneTitle,
  terrain,
  liveMinTempC,
  frostRiskLabel,
  equipmentAccess = "manual_yunta",
  onChangeEquipment,
  onNavigateTab,
  onSelectChecklistOption,
  onForceCalculatePlan,
}) => {
  if (!hasLocatedParcel) {
    return (
      <View style={styles.checklistCard}>
        <View style={styles.checklistHeaderRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.checklistOverline}>GUÍA DE INICIO RÁPIDO</Text>
            <Text style={styles.checklistTitle}>
              Cómo preparamos tu plan de rotación
            </Text>
          </View>
        </View>
        <View style={styles.guideStepsList}>
          <View style={styles.guideStepRow}>
            <View style={styles.guideStepNumCircle}>
              <MapPin size={15} color={COLORS.agroPrimary} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.guideStepTitle}>1. Ubica tu chacra</Text>
              <Text style={styles.guideStepDesc}>
                Presiona GPS o Buscar sector arriba, o dile por voz al asistente
                dónde queda tu parcela.
              </Text>
            </View>
          </View>
          <View style={styles.guideStepRow}>
            <View style={styles.guideStepNumCircle}>
              <Compass size={15} color={COLORS.agroPrimary} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.guideStepTitle}>
                2. Confirma el polígono en el mapa
              </Text>
              <Text style={styles.guideStepDesc}>
                Ajusta el cuadrado de 1 hectárea sobre tu terreno para leer
                altura, suelo y lluvia exactos.
              </Text>
            </View>
          </View>
          <View style={styles.guideStepRow}>
            <View style={styles.guideStepNumCircle}>
              <Layers size={15} color={COLORS.agroPrimary} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.guideStepTitle}>3. Calibra tus 6 datos</Text>
              <Text style={styles.guideStepDesc}>
                Responde sobre agua, cultivo previo y objetivo. Para suelo y
                clima puedes usar los datos satelitales directos.
              </Text>
            </View>
          </View>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.checklistCard}>
      <View style={styles.checklistHeaderRow}>
        <View style={{ flex: 1 }}>
          <Text style={styles.checklistOverline}>
            CALIBRACIÓN SATÉLITE + PARCELA
          </Text>
          <Text style={styles.checklistTitle}>
            {isPlanReady
              ? "Diagnóstico calibrado (6 puntos)"
              : "Completa los 6 puntos para trazar tus 3 rotaciones"}
          </Text>
        </View>
        <View
          style={[
            styles.checklistBadgePill,
            isPlanReady && styles.checklistBadgePillDone,
          ]}
        >
          <Text
            style={[
              styles.checklistBadgeText,
              isPlanReady && { color: COLORS.forestDeep },
            ]}
          >
            {completedChecklistCount}/6 listos
          </Text>
        </View>
      </View>

      <Text style={styles.checklistSubText}>
        Lo que cuentes por voz al asistente agronómico (lugar, agua o semillas)
        se marcará automáticamente aquí.
      </Text>

      {/* Slot 1: Parcel Polygon */}
      <View style={styles.slotBlock}>
        <View style={styles.slotHeaderRow}>
          <Text style={styles.slotTitleText}>
            1. Límites exactos de tu chacra en el mapa
          </Text>
          <Text
            style={[
              styles.slotStatusTag,
              voiceSlots.map_verified && styles.slotStatusTagDone,
            ]}
          >
            {voiceSlots.map_verified
              ? `${zoneTitle} (Confirmada)`
              : "Falta confirmar mapa"}
          </Text>
        </View>
        {!voiceSlots.map_verified && (
          <View style={styles.slotChipsWrap}>
            <TouchableOpacity
              onPress={() => onNavigateTab("mapa")}
              style={[styles.slotChipBtn, styles.slotChipBtnSatellite]}
              activeOpacity={0.85}
            >
              <Compass size={14} color={COLORS.agroPrimary} />
              <Text style={styles.slotChipBtnTextSatellite}>
                Confirmar exactamente mi parcela en el mapa
              </Text>
            </TouchableOpacity>
          </View>
        )}
      </View>

      {/* Slot 2: Water / Irrigation */}
      <View style={styles.slotBlock}>
        <View style={styles.slotHeaderRow}>
          <Text style={styles.slotTitleText}>2. Agua / Sistema de riego</Text>
          <Text
            style={[
              styles.slotStatusTag,
              voiceSlots.water_confirmed && styles.slotStatusTagDone,
            ]}
          >
            {voiceSlots.water_confirmed
              ? voiceSlots.water_label || "Confirmado"
              : "Pendiente"}
          </Text>
        </View>
        <View style={styles.slotChipsWrap}>
          {CHECKLIST_WATER_OPTIONS.map((opt) => {
            const active =
              voiceSlots.water_confirmed &&
              voiceSlots.water_label === opt.label;
            return (
              <TouchableOpacity
                key={opt.id}
                onPress={() =>
                  onSelectChecklistOption?.("water", opt.id, opt.label)
                }
                style={[
                  styles.slotChipBtn,
                  active && styles.slotChipBtnActive,
                ]}
              >
                {active && <Check size={13} color="#FFFFFF" />}
                <Text
                  style={[
                    styles.slotChipBtnText,
                    active && styles.slotChipBtnTextActive,
                  ]}
                >
                  {opt.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </View>

      {/* Slot 3: Previous crop */}
      <View style={styles.slotBlock}>
        <View style={styles.slotHeaderRow}>
          <Text style={styles.slotTitleText}>
            3. ¿Qué sembraste la campaña pasada?
          </Text>
          <Text
            style={[
              styles.slotStatusTag,
              voiceSlots.crop_confirmed && styles.slotStatusTagDone,
            ]}
          >
            {voiceSlots.crop_confirmed
              ? voiceSlots.crop_label || "Confirmado"
              : "Pendiente"}
          </Text>
        </View>
        <View style={styles.slotChipsWrap}>
          {CHECKLIST_CROP_OPTIONS.map((opt) => {
            const active =
              voiceSlots.crop_confirmed && voiceSlots.crop_label === opt.label;
            return (
              <TouchableOpacity
                key={opt.id}
                onPress={() =>
                  onSelectChecklistOption?.("crop", opt.id, opt.label)
                }
                style={[
                  styles.slotChipBtn,
                  active && styles.slotChipBtnActive,
                ]}
              >
                {active && <Check size={13} color="#FFFFFF" />}
                <Text
                  style={[
                    styles.slotChipBtnText,
                    active && styles.slotChipBtnTextActive,
                  ]}
                >
                  {opt.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </View>

      {/* Slot 4: Soil texture & slope */}
      <View style={styles.slotBlock}>
        <View style={styles.slotHeaderRow}>
          <Text style={styles.slotTitleText}>
            4. Textura de tierra y pendiente
          </Text>
          <Text
            style={[
              styles.slotStatusTag,
              voiceSlots.soil_confirmed && styles.slotStatusTagDone,
            ]}
          >
            {voiceSlots.soil_confirmed
              ? voiceSlots.soil_label || "Confirmado"
              : "Pendiente"}
          </Text>
        </View>
        <Text style={styles.slotSatelliteHint}>
          Dato satélite SoilGrids:{" "}
          {terrain.soil_profile?.texture_class || terrain.soil_texture} · pH{" "}
          {terrain.soil_profile?.ph ?? "--"} · Pendiente{" "}
          {terrain.slope_pct?.toFixed(1)}%
        </Text>
        <View style={styles.slotChipsWrap}>
          {CHECKLIST_SOIL_OPTIONS.map((opt) => {
            const active =
              voiceSlots.soil_confirmed && voiceSlots.soil_label === opt.label;
            return (
              <TouchableOpacity
                key={opt.id}
                onPress={() =>
                  onSelectChecklistOption?.("soil", opt.id, opt.label)
                }
                style={[
                  styles.slotChipBtn,
                  opt.isSat && styles.slotChipBtnSatellite,
                  active && styles.slotChipBtnActive,
                ]}
              >
                {opt.isSat ? (
                  <Satellite
                    size={13}
                    color={active ? "#FFFFFF" : COLORS.agroPrimary}
                  />
                ) : active ? (
                  <Check size={13} color="#FFFFFF" />
                ) : null}
                <Text
                  style={[
                    styles.slotChipBtnText,
                    opt.isSat && styles.slotChipBtnTextSatellite,
                    active && styles.slotChipBtnTextActive,
                  ]}
                >
                  {opt.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </View>

      {/* Slot 5: Local climate risk */}
      <View style={styles.slotBlock}>
        <View style={styles.slotHeaderRow}>
          <Text style={styles.slotTitleText}>
            5. Riesgo climático local (Heladas / Lluvias)
          </Text>
          <Text
            style={[
              styles.slotStatusTag,
              voiceSlots.climate_risk_confirmed && styles.slotStatusTagDone,
            ]}
          >
            {voiceSlots.climate_risk_confirmed
              ? voiceSlots.climate_risk_label || "Confirmado"
              : "Pendiente"}
          </Text>
        </View>
        <Text style={styles.slotSatelliteHint}>
          Dato satélite NASA POWER: Mín. {liveMinTempC.toFixed(1)}°C · Riesgo
          helada {frostRiskLabel}
        </Text>
        <View style={styles.slotChipsWrap}>
          {CHECKLIST_CLIMATE_OPTIONS.map((opt) => {
            const active =
              voiceSlots.climate_risk_confirmed &&
              voiceSlots.climate_risk_label === opt.label;
            return (
              <TouchableOpacity
                key={opt.id}
                onPress={() =>
                  onSelectChecklistOption?.("climate", opt.id, opt.label)
                }
                style={[
                  styles.slotChipBtn,
                  opt.isSat && styles.slotChipBtnSatellite,
                  active && styles.slotChipBtnActive,
                ]}
              >
                {opt.isSat ? (
                  <Satellite
                    size={13}
                    color={active ? "#FFFFFF" : COLORS.agroPrimary}
                  />
                ) : active ? (
                  <Check size={13} color="#FFFFFF" />
                ) : null}
                <Text
                  style={[
                    styles.slotChipBtnText,
                    opt.isSat && styles.slotChipBtnTextSatellite,
                    active && styles.slotChipBtnTextActive,
                  ]}
                >
                  {opt.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </View>

      {/* Slot 6: Farmer Goal & Seeds */}
      <View style={styles.slotBlock}>
        <View style={styles.slotHeaderRow}>
          <Text style={styles.slotTitleText}>
            6. Objetivo de la campaña / Semillas
          </Text>
          <Text
            style={[
              styles.slotStatusTag,
              (voiceSlots.goal_confirmed || voiceSlots.seeds_checked) &&
                styles.slotStatusTagDone,
            ]}
          >
            {voiceSlots.goal_confirmed || voiceSlots.seeds_checked
              ? voiceSlots.goal_label || "Confirmado"
              : "Pendiente"}
          </Text>
        </View>
        <View style={styles.slotChipsWrap}>
          {CHECKLIST_GOAL_OPTIONS.map((opt) => {
            const active =
              voiceSlots.goal_confirmed && voiceSlots.goal_label === opt.label;
            return (
              <TouchableOpacity
                key={opt.id}
                onPress={() =>
                  onSelectChecklistOption?.("goal", opt.id, opt.label)
                }
                style={[
                  styles.slotChipBtn,
                  active && styles.slotChipBtnActive,
                ]}
              >
                {active && <Check size={13} color="#FFFFFF" />}
                <Text
                  style={[
                    styles.slotChipBtnText,
                    active && styles.slotChipBtnTextActive,
                  ]}
                >
                  {opt.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
        {onChangeEquipment && (
          <View style={{ marginTop: 8, gap: 6 }}>
            <Text style={styles.slotSatelliteHint}>Herramienta / labranza:</Text>
            <View style={styles.slotChipsWrap}>
              {EQUIPMENT_OPTIONS.map((eq) => {
                const active = equipmentAccess === eq.id;
                return (
                  <TouchableOpacity
                    key={eq.id}
                    onPress={() => onChangeEquipment(eq.id)}
                    style={[
                      styles.slotChipBtn,
                      active && styles.slotChipBtnActive,
                    ]}
                  >
                    {active && <Check size={13} color="#FFFFFF" />}
                    <Text
                      style={[
                        styles.slotChipBtnText,
                        active && styles.slotChipBtnTextActive,
                      ]}
                    >
                      {eq.label}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>
        )}
      </View>

      {!isPlanReady ? (
        <TouchableOpacity
          onPress={onForceCalculatePlan}
          style={styles.forceCalcBtn}
          activeOpacity={0.88}
        >
          <Sparkles size={15} color={COLORS.forestDeep} />
          <Text style={styles.forceCalcBtnText}>
            Calcular las 3 rotaciones con los datos actuales
          </Text>
        </TouchableOpacity>
      ) : (
        <TouchableOpacity
          onPress={() => onNavigateTab("plan")}
          style={styles.forceCalcBtn}
          activeOpacity={0.88}
        >
          <CheckCircle2 size={15} color={COLORS.forestDeep} />
          <Text style={styles.forceCalcBtnText}>
            Ver Plan y Comparar las 3 Rotaciones
          </Text>
          <ArrowRight size={15} color={COLORS.forestDeep} />
        </TouchableOpacity>
      )}
    </View>
  );
};

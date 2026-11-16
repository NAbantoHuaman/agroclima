import React, { useState } from "react";
import { MapPin, Search, X } from "lucide-react-native";
import {
  ActivityIndicator,
  FlatList,
  Modal,
  Pressable,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { translateCropText } from "../../i18n/translations";
import { requestGeocodePlace } from "../../services/apiClient";
import { COLORS } from "../../theme/tokens";
import type {
  AppLanguage,
  BeaconParcel,
  ReferenceDataResponse,
} from "../../types";
import { styles } from "./FarmerHomeTab.styles";

interface HomeZonePickerModalProps {
  visible: boolean;
  onClose: () => void;
  lang: AppLanguage;
  referenceData: ReferenceDataResponse | null;
  onSelectBeacon: (beacon: BeaconParcel) => void;
  onSelectLocation: (
    lat: number,
    lon: number,
    parcelId: string | null,
    label?: string | null
  ) => void;
}

export const HomeZonePickerModal: React.FC<HomeZonePickerModalProps> = ({
  visible,
  onClose,
  lang,
  referenceData,
  onSelectBeacon,
  onSelectLocation,
}) => {
  const [zoneQuery, setZoneQuery] = useState("");
  const [isSearchingZone, setIsSearchingZone] = useState(false);
  const [zoneSearchError, setZoneSearchError] = useState<string | null>(null);
  const isQu = lang === "qu";

  const handleSearchZone = async () => {
    const q = zoneQuery.trim();
    if (q.length < 2) return;
    setIsSearchingZone(true);
    setZoneSearchError(null);
    try {
      const geo = await requestGeocodePlace(q);
      if (geo.data.found && geo.data.result) {
        onSelectLocation(
          geo.data.result.lat,
          geo.data.result.lon,
          null,
          geo.data.result.label
        );
        onClose();
      } else {
        setZoneSearchError(
          isQu
            ? "Chay llaqtaqa manam tarisqachu. Huk sutiwan maskay."
            : "No se encontró ese lugar. Prueba otro nombre o toca el mapa."
        );
      }
    } catch (err) {
      setZoneSearchError(
        isQu
          ? "Mana maskayta atikunchu kunan."
          : err instanceof Error
          ? err.message
          : "Error buscando lugar."
      );
    } finally {
      setIsSearchingZone(false);
    }
  };

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
                {isQu ? "CHAKRAYKIPA TIYAYNIN" : "UBICACIÓN DE TU CHACRA"}
              </Text>
              <Text style={styles.modalTitle}>
                {isQu
                  ? "Llaqtata maskay utaq hukta akllay"
                  : "Busca cualquier sector o elige referencia"}
              </Text>
            </View>
            <Pressable onPress={onClose} style={styles.modalCloseBtn}>
              <X size={18} color={COLORS.inkPrimary} />
            </Pressable>
          </View>

          <View style={styles.zoneSearchRow}>
            <TextInput
              value={zoneQuery}
              onChangeText={(txt) => {
                setZoneQuery(txt);
                setZoneSearchError(null);
              }}
              placeholder={
                isQu
                  ? "Llaqtata utaq distrituta maskay (Porcon, Jaen)..."
                  : "Buscar caserío o distrito (ej. Porcón, Jaén)..."
              }
              placeholderTextColor={COLORS.inkMuted}
              style={styles.zoneSearchInput}
              onSubmitEditing={handleSearchZone}
            />
            <TouchableOpacity
              disabled={isSearchingZone || zoneQuery.trim().length < 2}
              onPress={handleSearchZone}
              style={styles.zoneSearchBtn}
            >
              {isSearchingZone ? (
                <ActivityIndicator size="small" color={COLORS.forestDeep} />
              ) : (
                <Search size={17} color={COLORS.forestDeep} />
              )}
            </TouchableOpacity>
          </View>
          {zoneSearchError && (
            <Text style={styles.zoneSearchErr}>{zoneSearchError}</Text>
          )}

          <FlatList
            data={[
              ...(referenceData?.beacon_parcels || []).map((b) => ({
                key: b.id,
                title: b.name,
                sub: `${translateCropText(b.zone_type, lang)} · ${b.elevation_m} m s.n.m. · ${isQu ? "Kinray" : "Pendiente"} ${b.slope_pct}%`,
                lat: b.lat,
                lon: b.lon,
                beacon: b,
                parcelId: b.id,
              })),
              ...(referenceData?.known_locations || []).map((l, idx) => ({
                key: `loc-${idx}`,
                title: l.label,
                sub: `${isQu ? "Suyu" : "Sector"} (${l.lat.toFixed(3)}, ${l.lon.toFixed(3)})`,
                lat: l.lat,
                lon: l.lon,
                beacon: undefined,
                parcelId: l.parcel_id ?? null,
              })),
            ]}
            keyExtractor={(item) => item.key}
            renderItem={({ item }) => (
              <TouchableOpacity
                style={styles.zoneItem}
                onPress={() => {
                  if (item.beacon) {
                    onSelectBeacon(item.beacon);
                  } else {
                    onSelectLocation(
                      item.lat,
                      item.lon,
                      item.parcelId ?? null,
                      item.title
                    );
                  }
                  onClose();
                }}
              >
                <View style={styles.zonePinCircle}>
                  <MapPin size={16} color={COLORS.agroPrimary} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.zoneItemTitle}>{item.title}</Text>
                  <Text style={styles.zoneItemSub}>{item.sub}</Text>
                </View>
              </TouchableOpacity>
            )}
          />
        </View>
      </View>
    </Modal>
  );
};

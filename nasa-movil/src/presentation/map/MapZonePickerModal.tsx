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
import { styles } from "./InteractiveMapTab.styles";

interface MapZonePickerModalProps {
  visible: boolean;
  onClose: () => void;
  isQu: boolean;
  lang: AppLanguage;
  mapMode: "chacra" | "explorar";
  referenceData: ReferenceDataResponse | null;
  onRunExplorerProbe: (
    lat: number,
    lon: number,
    label?: string
  ) => Promise<void>;
  onSelectPoint: (lat: number, lon: number, label?: string | null) => void;
  onSelectBeacon: (beacon: BeaconParcel) => void;
}

export const MapZonePickerModal: React.FC<MapZonePickerModalProps> = ({
  visible,
  onClose,
  isQu,
  lang,
  mapMode,
  referenceData,
  onRunExplorerProbe,
  onSelectPoint,
  onSelectBeacon,
}) => {
  const [zoneQuery, setZoneQuery] = useState("");
  const [isSearchingZone, setIsSearchingZone] = useState(false);
  const [zoneSearchError, setZoneSearchError] = useState<string | null>(null);

  const handleSearch = async () => {
    const q = zoneQuery.trim();
    if (q.length < 2 || isSearchingZone) return;
    setIsSearchingZone(true);
    setZoneSearchError(null);
    try {
      const geo = await requestGeocodePlace(q);
      if (geo.data.found && geo.data.result) {
        if (mapMode === "explorar") {
          void onRunExplorerProbe(
            geo.data.result.lat,
            geo.data.result.lon,
            geo.data.result.label
          );
        } else {
          onSelectPoint(
            geo.data.result.lat,
            geo.data.result.lon,
            geo.data.result.label
          );
        }
        onClose();
      } else {
        setZoneSearchError(
          isQu
            ? "Chay llaqtaqa manam tarisqachu. Huk sutiwan maskay utaq mapapi ñitiy."
            : "No se encontró ese lugar. Prueba otro nombre o toca el mapa."
        );
      }
    } catch (err) {
      setZoneSearchError(
        isQu
          ? "Mana maskayta atikunchu kunanpacha."
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
            <View>
              <Text style={styles.modalOverline}>
                {isQu ? "CHAKRATA / SUYUTA TIKRAY" : "CAMBIAR CHACRA / ZONA"}
              </Text>
              <Text style={styles.modalTitle}>
                {isQu ? "Llaqtata utaq suyuta maskay" : "Buscar lugar o sector"}
              </Text>
            </View>
            <Pressable onPress={onClose} style={styles.modalCloseBtn}>
              <X size={18} color={COLORS.inkPrimary} />
            </Pressable>
          </View>

          <View style={styles.zoneSearchRow}>
            <TextInput
              value={zoneQuery}
              onChangeText={setZoneQuery}
              placeholder={
                isQu
                  ? "Distrito utaq llaqtata maskay..."
                  : "Buscar distrito, centro poblado o zona..."
              }
              placeholderTextColor={COLORS.inkMuted}
              style={styles.zoneSearchInput}
              returnKeyType="search"
              onSubmitEditing={handleSearch}
            />
            <TouchableOpacity
              disabled={isSearchingZone || zoneQuery.trim().length < 2}
              onPress={handleSearch}
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
                sub: `${translateCropText(b.zone_type, lang)} · ${b.elevation_m} m s.n.m.`,
                lat: b.lat,
                lon: b.lon,
                beacon: b,
              })),
              ...(referenceData?.known_locations || []).map((l, idx) => ({
                key: `loc-${idx}`,
                title: l.label,
                sub: `${isQu ? "Tiyaynin" : "Coordenadas"}: ${l.lat.toFixed(3)}, ${l.lon.toFixed(3)}`,
                lat: l.lat,
                lon: l.lon,
                beacon: undefined,
              })),
            ]}
            keyExtractor={(item) => item.key}
            renderItem={({ item }) => (
              <TouchableOpacity
                style={styles.zoneRow}
                onPress={() => {
                  if (mapMode === "explorar") {
                    void onRunExplorerProbe(item.lat, item.lon, item.title);
                  } else if (item.beacon) {
                    onSelectBeacon(item.beacon);
                  } else {
                    onSelectPoint(item.lat, item.lon, item.title);
                  }
                  onClose();
                }}
              >
                <MapPin size={17} color={COLORS.agroPrimary} />
                <View style={{ flex: 1 }}>
                  <Text style={styles.zoneRowTitle}>{item.title}</Text>
                  <Text style={styles.zoneRowSub}>{item.sub}</Text>
                </View>
              </TouchableOpacity>
            )}
          />
        </View>
      </View>
    </Modal>
  );
};

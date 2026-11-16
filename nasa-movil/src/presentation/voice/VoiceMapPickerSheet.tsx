import React, { useMemo } from "react";
import {
  CheckCircle2,
  MapPin,
  Navigation,
  PenTool,
  Trash2,
  X,
} from "lucide-react-native";
import {
  ActivityIndicator,
  Modal,
  Pressable,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { WebView } from "react-native-webview";
import { buildDefault1HaSquare } from "../../domain/map/geometry";
import { COLORS } from "../../theme/tokens";
import { buildVoicePickerHtml } from "./voiceLeafletTemplate";
import { styles } from "./VoiceCopilotModal.styles";

const WebViewComponent = WebView as unknown as React.ComponentType<{
  ref?: React.Ref<unknown>;
  originWhitelist?: string[];
  source: { html: string };
  style?: object;
  javaScriptEnabled?: boolean;
  domStorageEnabled?: boolean;
  onMessage?: (ev: { nativeEvent: { data: string } }) => void;
}>;

interface VoiceMapPickerSheetProps {
  visible: boolean;
  onClose: () => void;
  detectedZoneTitle: string;
  mapOpenCenter: { lat: number; lon: number };
  mapDraftLat: number;
  mapDraftLon: number;
  mapDraftPolygon: [number, number][];
  draftAreaHa: number | null;
  mapDrawMode: boolean;
  onChangeDrawMode: (drawMode: boolean) => void;
  onChangeDraftPolygon: (poly: [number, number][]) => void;
  isGettingGps: boolean;
  isSavingMap: boolean;
  mapWebRef: React.MutableRefObject<{
    injectJavaScript?: (script: string) => void;
  } | null>;
  onUseGps: () => void;
  onMapTap: (lat: number, lon: number) => void;
  onSaveAndClose: () => void;
}

export const VoiceMapPickerSheet: React.FC<VoiceMapPickerSheetProps> = ({
  visible,
  onClose,
  detectedZoneTitle,
  mapOpenCenter,
  mapDraftLat,
  mapDraftLon,
  mapDraftPolygon,
  draftAreaHa,
  mapDrawMode,
  onChangeDrawMode,
  onChangeDraftPolygon,
  isGettingGps,
  isSavingMap,
  mapWebRef,
  onUseGps,
  onMapTap,
  onSaveAndClose,
}) => {
  const pickerHtml = useMemo(() => {
    return buildVoicePickerHtml({
      initLat: mapOpenCenter.lat,
      initLon: mapOpenCenter.lon,
      markerLat: mapDraftLat,
      markerLon: mapDraftLon,
      initPoly: mapDraftPolygon,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible, mapOpenCenter.lat, mapOpenCenter.lon]);

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={styles.mapModalRoot}>
        <View style={styles.mapModalHeader}>
          <View style={{ flex: 1 }}>
            <Text style={styles.mapModalTitle} numberOfLines={1}>
              Confirma exactamente tu parcela · {detectedZoneTitle}
            </Text>
            <Text style={styles.mapModalSub}>
              {mapDrawMode
                ? `Toca las esquinas de tu parcela (${mapDraftPolygon.length} puntos)`
                : "Toca donde está tu chacra para encuadrar tu parcela (1 ha)"}
            </Text>
          </View>
          <TouchableOpacity
            onPress={onUseGps}
            disabled={isGettingGps}
            style={styles.mapGpsHeaderBtn}
            activeOpacity={0.85}
          >
            <Navigation size={15} color={COLORS.forestDeep} />
            <Text style={styles.mapGpsHeaderText}>
              {isGettingGps ? "..." : "Mi GPS"}
            </Text>
          </TouchableOpacity>
          <Pressable onPress={onClose} style={styles.mapCloseBtn}>
            <X size={20} color="#FFFFFF" />
          </Pressable>
        </View>

        <View style={styles.mapWebWrap}>
          <WebViewComponent
            ref={mapWebRef}
            originWhitelist={["*"]}
            source={{ html: pickerHtml }}
            style={styles.mapWebView}
            javaScriptEnabled
            domStorageEnabled
            onMessage={(ev) => {
              try {
                const msg = JSON.parse(ev.nativeEvent.data);
                if (msg.type === "tap") {
                  onMapTap(msg.lat, msg.lon);
                }
              } catch {
                // ignore malformed messages
              }
            }}
          />

          <View style={styles.mapOverlayCoordsPill}>
            <Text style={styles.mapOverlayCoordsText}>
              {mapDraftLat.toFixed(4)}, {mapDraftLon.toFixed(4)}
              {draftAreaHa ? ` · ${draftAreaHa} ha aprox.` : ""}
            </Text>
          </View>
        </View>

        <View style={styles.mapModalFooter}>
          <View style={styles.mapModeRow}>
            <TouchableOpacity
              onPress={() => onChangeDrawMode(false)}
              style={[
                styles.mapModeBtn,
                !mapDrawMode && styles.mapModeBtnActive,
              ]}
            >
              <MapPin
                size={15}
                color={!mapDrawMode ? COLORS.forestDeep : "#FFFFFF"}
              />
              <Text
                style={[
                  styles.mapModeBtnText,
                  !mapDrawMode && styles.mapModeBtnTextActive,
                ]}
              >
                Mover cuadrado (1 ha)
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              onPress={() => {
                onChangeDrawMode(true);
                onChangeDraftPolygon([]);
              }}
              style={[
                styles.mapModeBtn,
                mapDrawMode && styles.mapModeBtnActive,
              ]}
            >
              <PenTool
                size={15}
                color={mapDrawMode ? COLORS.forestDeep : "#FFFFFF"}
              />
              <Text
                style={[
                  styles.mapModeBtnText,
                  mapDrawMode && styles.mapModeBtnTextActive,
                ]}
              >
                Dibujar esquinas
              </Text>
            </TouchableOpacity>

            {mapDraftPolygon.length > 0 && (
              <TouchableOpacity
                onPress={() =>
                  onChangeDraftPolygon(
                    mapDrawMode
                      ? []
                      : buildDefault1HaSquare(mapDraftLat, mapDraftLon)
                  )
                }
                style={styles.mapClearBtn}
              >
                <Trash2 size={15} color="#FCA5A5" />
              </TouchableOpacity>
            )}
          </View>

          <TouchableOpacity
            onPress={onSaveAndClose}
            disabled={isSavingMap}
            style={styles.mapSaveCloseBtn}
            activeOpacity={0.88}
          >
            {isSavingMap ? (
              <ActivityIndicator size="small" color={COLORS.forestDeep} />
            ) : (
              <CheckCircle2
                size={19}
                color={COLORS.forestDeep}
                strokeWidth={2.5}
              />
            )}
            <Text style={styles.mapSaveCloseText}>
              Confirmar exactamente mi parcela
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
};

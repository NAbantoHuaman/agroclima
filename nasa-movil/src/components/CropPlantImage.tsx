import React from "react";
import { Image, ImageSourcePropType, StyleSheet, View } from "react-native";
import { Sprout } from "lucide-react-native";

const CROP_IMAGE_ASSETS: Record<string, ImageSourcePropType> = {
  papa: require("../../assets/crops/papa.jpg"),
  maiz_amilaceo: require("../../assets/crops/maiz_amilaceo.jpg"),
  cebada: require("../../assets/crops/cebada.jpg"),
  trigo: require("../../assets/crops/trigo.jpg"),
  quinua: require("../../assets/crops/quinua.jpg"),
  tarwi: require("../../assets/crops/tarwi.jpg"),
  haba: require("../../assets/crops/haba.jpg"),
  alfalfa: require("../../assets/crops/alfalfa.jpg"),
  avena_vicia: require("../../assets/crops/avena_vicia.jpg"),
  ryegrass_trebol: require("../../assets/crops/ryegrass_trebol.jpg"),
  frijol: require("../../assets/crops/frijol.jpg"),
  arveja: require("../../assets/crops/arveja.jpg"),
  cafe: require("../../assets/crops/cafe.jpg"),
  cacao: require("../../assets/crops/cacao.jpg"),
  tuna_cochinilla: require("../../assets/crops/tuna_cochinilla.jpg"),
  tomillo_aromaticas: require("../../assets/crops/tomillo_aromaticas.jpg"),
  tara_taya: require("../../assets/crops/tara_taya.jpg"),
  palta_intercultivo: require("../../assets/crops/palta_intercultivo.jpg"),
  oca_olluco_mashua: require("../../assets/crops/oca_olluco_mashua.jpg"),
  arracacha: require("../../assets/crops/arracacha.jpg"),
  kiwicha: require("../../assets/crops/kiwicha.jpg"),
  lenteja: require("../../assets/crops/lenteja.png"),
  linaza: require("../../assets/crops/linaza.jpg"),
  ajo_valle: require("../../assets/crops/ajo_valle.jpg"),
};

interface CropPlantImageProps {
  cropId: string;
  accentColor?: string;
  size?: number;
  borderRadius?: number;
}

export const CropPlantImage: React.FC<CropPlantImageProps> = ({
  cropId,
  accentColor = "#2E6F2D",
  size = 48,
  borderRadius = 14,
}) => {
  const source = CROP_IMAGE_ASSETS[cropId];

  return (
    <View
      style={[
        styles.frame,
        {
          width: size,
          height: size,
          borderRadius,
          backgroundColor: `${accentColor}1E`,
          borderColor: `${accentColor}44`,
        },
      ]}
    >
      {source ? (
        <Image source={source} style={styles.photo} resizeMode="cover" />
      ) : (
        <Sprout size={Math.round(size * 0.45)} color={accentColor} strokeWidth={2.2} />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  frame: {
    overflow: "hidden",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
  },
  photo: {
    width: "100%",
    height: "100%",
  },
});

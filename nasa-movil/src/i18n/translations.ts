import type { AppLanguage, CurrentCropId, WaterAvailability } from "../types";

export interface MobileUiDictionary {
  langLabel: string;
  telemetryHeader: {
    brand: string;
    subtitle: string;
    gpsBtn: string;
    locating: string;
    changeZone: string;
    elevUnit: string;
    slopeUnit: string;
  };
  tabs: {
    parcela: string;
    plan: string;
    clima: string;
    cultivos: string;
    copiloto: string;
  };
  parcela: {
    mapTitle: string;
    mapHint: string;
    layerSat: string;
    layerTopo: string;
    drawPolyStart: string;
    drawPolyFinish: string;
    clearPoly: string;
    gpsMe: string;
    fieldConfigTitle: string;
    cropHistoryLabel: string;
    priorityLabel: string;
    waterLabel: string;
    soilNotesLabel: string;
    analyzeBtn: string;
    analyzingBtn: string;
    telemetryTitle: string;
    soilGridsTitle: string;
    cropButtons: Record<CurrentCropId, string>;
    waterButtons: Record<WaterAvailability, string>;
    priorities: {
      agua: string;
      suelo: string;
      mercado: string;
    };
  };
  plan: {
    immediateAction: string;
    strategySelector: string;
    listenSummary: string;
    stopAudio: string;
    mcdaLabel: string;
    vulnLabel: string;
    timelineTitle: string;
    radarTitle: string;
    economicsTitle: string;
    seedCostLabel: string;
    totalCostLabel: string;
    netMarginLabel: string;
    bcRatioLabel: string;
    deltaVsBaseLabel: string;
    pesticidesTitle: string;
    pesticidesSub: string;
    carenciaLabel: string;
    pestsLabel: string;
    whenApplyLabel: string;
    bioControlLabel: string;
    chemControlLabel: string;
    consumerBenefitLabel: string;
    explainTitle: string;
    humanCheckTitle: string;
  };
  climate: {
    title20yr: string;
    sub20yr: string;
    rainMode: string;
    tempMode: string;
    simulatorTitle: string;
    simulatorSub: string;
    rainDelta: string;
    tempDelta: string;
    frostMode: string;
    applyHistoryScenario: string;
    resetScenario: string;
    semaphoreTitle: string;
    showTop8: string;
    showAll: (n: number) => string;
  };
  catalog: {
    title: string;
    subtitle: string;
    searchPlaceholder: string;
    filters: {
      all: string;
      profitable: string;
      valleys: string;
      nitrogen: string;
      resilient: string;
      forage: string;
    };
  };
  copilot: {
    title: string;
    subtitle: string;
    inputPlaceholder: string;
    sendBtn: string;
    listenBtn: string;
    applyPlanBtn: string;
    understoodTitle: string;
    examplesTitle: string;
  };
}

export const MOBILE_TRANSLATIONS: Record<AppLanguage, MobileUiDictionary> = {
  es: {
    langLabel: "ES",
    telemetryHeader: {
      brand: "AGROCLIMA NASA CAJAMARCA",
      subtitle: "MOTOR SATELITAL MULTICRITERIO",
      gpsBtn: "GPS",
      locating: "...",
      changeZone: "ZONA",
      elevUnit: "m s.n.m.",
      slopeUnit: "pend.",
    },
    tabs: {
      parcela: "Parcela",
      plan: "Plan 2A",
      clima: "Clima 20A",
      cultivos: "Cultivos",
      copiloto: "Copiloto",
    },
    parcela: {
      mapTitle: "DELIMITACION SATELITAL DE PARCELA",
      mapHint: "Toca el mapa para mover el punto o traza el poligono real de tu chacra.",
      layerSat: "Satelite",
      layerTopo: "Topografico",
      drawPolyStart: "Trazar Poligono",
      drawPolyFinish: "Cerrar Poligono",
      clearPoly: "Limpiar",
      gpsMe: "Mi GPS",
      fieldConfigTitle: "PARAMETROS AGRONOMICOS Y SISTEMA HIDRICO",
      cropHistoryLabel: "Historial / Cultivo Base Actual",
      priorityLabel: "Objetivo Principal de Campana",
      waterLabel: "Modalidad de Riego Disponible (7 Sistemas)",
      soilNotesLabel: "Observacion Directa en Campo",
      analyzeBtn: "RECALCULAR ROTACION NASA",
      analyzingBtn: "PROCESANDO TELEMETRIA...",
      telemetryTitle: "DIAGNOSTICO BIOPARAMETRICO SATELITAL",
      soilGridsTitle: "PERFIL EDAFICO SOILGRIDS / CAMPO",
      cropButtons: {
        sin_cultivo: "Terreno libre / Sin cultivo previo",
        monocultivo_papa: "Solo Papa (Monocultivo)",
        papa_maiz: "Papa y Maiz Amilaceo",
        pastos_degradados: "Pastos / Ganaderia",
        cebada_trigo_continuo: "Cebada / Trigo Continuo",
      },
      waterButtons: {
        secano: "Solo Lluvia (Secano)",
        cosecha_agua_qocha: "Qocha / Cosecha Agua",
        riego_deficitario: "Turnos / Auxilio",
        riego_gravedad: "Acequia / Gravedad",
        riego_melgas_surcos: "Melgas y Surcos",
        riego_aspersion: "Aspersion",
        riego_goteo: "Goteo / Fertirriego",
      },
      priorities: {
        agua: "Ahorrar Agua",
        suelo: "Recuperar Suelo",
        mercado: "Mayor Rentabilidad",
      },
    },
    plan: {
      immediateAction: "ACCION AGRONOMICA INMEDIATA",
      strategySelector: "ESTRATEGIAS COMPARATIVAS (2026-2027)",
      listenSummary: "Escuchar Plan",
      stopAudio: "Detener Audio",
      mcdaLabel: "INDICE MCDA",
      vulnLabel: "VULNERABILIDAD",
      timelineTitle: "SECUENCIA DE ROTACION EN 4 CAMPANAS (24 MESES)",
      radarTitle: "BALANCE MULTICRITERIO DE ESTRATEGIA",
      economicsTitle: "ECONOMIA DE SEMILLAS Y RENTABILIDAD (2 ANOS / HA)",
      seedCostLabel: "Costo Semillas",
      totalCostLabel: "Costo Total",
      netMarginLabel: "Margen Neto",
      bcRatioLabel: "Retorno B/C",
      deltaVsBaseLabel: "Mejora vs Base",
      pesticidesTitle: "CONTROL FITOSANITARIO SENASA Y VENTANA NASA",
      pesticidesSub: "Aplicar unicamente al verificarse el umbral climatico satelital.",
      carenciaLabel: "CARENCIA",
      pestsLabel: "Plagas clave",
      whenApplyLabel: "Cuando aplicar (NASA)",
      bioControlLabel: "Biocontrol ecologico",
      chemControlLabel: "Quimico SENASA",
      consumerBenefitLabel: "Beneficio al consumidor",
      explainTitle: "JUSTIFICACION Y EVIDENCIA SATELITAL",
      humanCheckTitle: "VALIDACION LOCAL CON EL AGRICULTOR",
    },
    climate: {
      title20yr: "RESPALDO HISTORICO NASA (20 ANOS) Y PROYECCION 2026-2027",
      sub20yr: "Serie 2006-2025 para calibrar las proximas 4 campanas agricolas",
      rainMode: "Lluvia Anual (mm)",
      tempMode: "Temperatura Media (C)",
      simulatorTitle: "SIMULADOR CLIMATICO DE ESTRES",
      simulatorSub: "Ajusta lluvia, calor o heladas para medir resistencia de tu rotacion",
      rainDelta: "Variacion de Lluvia",
      tempDelta: "Aumento Termico",
      frostMode: "Frecuencia de Heladas",
      applyHistoryScenario: "Aplicar Tendencia 20 Anos",
      resetScenario: "Clima Normal",
      semaphoreTitle: "SEMAFORO TECNICO DE CULTIVOS (2026-2027)",
      showTop8: "Ver Top 8",
      showAll: (n) => `Ver los ${n} cultivos`,
    },
    catalog: {
      title: "BASE AGRONOMICA CAJAMARCA",
      subtitle: "Parametros reales de 300 a 3,950 m s.n.m.: costos de semilla, B/C y sanidad",
      searchPlaceholder: "Buscar cultivo, distrito, plaga o uso...",
      filters: {
        all: "Todos",
        profitable: "Alta Renta B/C >= 2x",
        valleys: "Valles / Cajabamba",
        nitrogen: "Fijadores N",
        resilient: "Sequia + Helada",
        forage: "Forrajeros",
      },
    },
    copilot: {
      title: "COPILOTO AGRONOMICO BILINGUE",
      subtitle: "Consulta por distrito o centro poblado en Espanol o Quechua Cajamarquino",
      inputPlaceholder: "Ej: Estoy en Cajabamba, quiero sembrar tomillo y cochinilla con riego por goteo...",
      sendBtn: "ANALIZAR CONSULTA",
      listenBtn: "Leer Respuesta",
      applyPlanBtn: "Cargar en Mi Parcela",
      understoodTitle: "PARAMETROS EXTRAIDOS",
      examplesTitle: "CONSULTAS DE REFERENCIA",
    },
  },
  qu: {
    langLabel: "QU",
    telemetryHeader: {
      brand: "AGROCLIMA NASA KASHAMARKA",
      subtitle: "HANAN PACHA ALLPA QHAWAQ",
      gpsBtn: "GPS",
      locating: "...",
      changeZone: "LLAQTA",
      elevUnit: "m s.n.m.",
      slopeUnit: "kinray",
    },
    tabs: {
      parcela: "Chakra",
      plan: "2 Wata",
      clima: "Pacha 20W",
      cultivos: "Murukuna",
      copiloto: "Yanapaq",
    },
    parcela: {
      mapTitle: "CHAKRA SATELITEWAN QHAWAY",
      mapHint: "Mapapi ñit'iy chakraykita maskanapaq utaq muyunta siq'iy.",
      layerSat: "Satelite",
      layerTopo: "Urqukuna",
      drawPolyStart: "Muyunta Siq'iy",
      drawPolyFinish: "Tukuy",
      clearPoly: "Pichay",
      gpsMe: "GPS-niy",
      fieldConfigTitle: "CHAKRAPA YAKUNPAS TARPUYNINPAS",
      cropHistoryLabel: "Kunan Tarpusqa Muru",
      priorityLabel: "Ima Munayta Maskanki",
      waterLabel: "Yaku Chayay (7 Parqoykuna)",
      soilNotesLabel: "Allpa Rikuy",
      analyzeBtn: "MUYUY TARPUYTA YUPAY",
      analyzingBtn: "NASA YUPASHANMI...",
      telemetryTitle: "SATELITE YAKUWAN QASA WILLAKUY",
      soilGridsTitle: "ALLPA KALLPA SOILGRIDS",
      cropButtons: {
        sin_cultivo: "Ch'usaq allpa (Mana tarpusqa)",
        monocultivo_papa: "Akshulla (Papa)",
        papa_maiz: "Akshuwan Sara",
        pastos_degradados: "Q'achu / Waka",
        cebada_trigo_continuo: "Siwara / Triwu",
      },
      waterButtons: {
        secano: "Tamya Yakulla",
        cosecha_agua_qocha: "Qucha / Yaku Huñuy",
        riego_deficitario: "Turnokuna Yaku",
        riego_gravedad: "Yarka / Acequia",
        riego_melgas_surcos: "Surcokunapi Parqoy",
        riego_aspersion: "Aspersion",
        riego_goteo: "Sutuy (Goteo)",
      },
      priorities: {
        agua: "Yakuta Waqaychay",
        suelo: "Allpata Kallpachay",
        mercado: "Aswan Qullqi",
      },
    },
    plan: {
      immediateAction: "KUNAN KILLA RURANAPAQ",
      strategySelector: "3 TARPUY ÑANKUNA (2026-2027)",
      listenSummary: "Uyariy",
      stopAudio: "Upallay",
      mcdaLabel: "ALLIN KAQ",
      vulnLabel: "PELIGRO",
      timelineTitle: "24 KILLA MUYUY TARPUY (4 KAMPANA)",
      radarTitle: "PICHQA KALLPA TUPUY",
      economicsTitle: "MURU CHANINWAN QULLQI GANANCIA (2 WATA / HA)",
      seedCostLabel: "Muru Chanin",
      totalCostLabel: "Llapan Gasto",
      netMarginLabel: "Ganancia",
      bcRatioLabel: "Kutiq B/C",
      deltaVsBaseLabel: "Aswan Allin",
      pesticidesTitle: "KURU PICHAY SENASA WAN NASA PACHA",
      pesticidesSub: "Satelite willaptillan hampita churay.",
      carenciaLabel: "SUYAY",
      pestsLabel: "Kuru / Unquy",
      whenApplyLabel: "Hayk'aq churana (NASA)",
      bioControlLabel: "Pacha hampi",
      chemControlLabel: "SENASA hampi",
      consumerBenefitLabel: "Mikuqpaq allin",
      explainTitle: "IMARAYKU KAY TARPUY ALLIN",
      humanCheckTitle: "CHAKRA RUNA QHAWARINANPAQ",
    },
    climate: {
      title20yr: "NASA 20 WATA WILLAKUY -> 2 WATA HAMUQ (2026-2027)",
      sub20yr: "2006-2025 watakunawan qhawaspa hamuq 2 watata wakichiy",
      rainMode: "Tamya (mm)",
      tempMode: "Ruphay (C)",
      simulatorTitle: "CH'AKI WAN QASA SIMULADOR",
      simulatorSub: "Tamya pisiyaptin utaq ruphay wichaptin qhaway",
      rainDelta: "Tamya Tikray",
      tempDelta: "Ruphay Wichay",
      frostMode: "Qasa Hamuy",
      applyHistoryScenario: "20 Wata Tikrayta Churay",
      resetScenario: "Normal Pacha",
      semaphoreTitle: "24 MURUKUNA SEMAFORON (2026-2027)",
      showTop8: "8 Allinkunata",
      showAll: (n) => `Llapan ${n} murukuna`,
    },
    catalog: {
      title: "KASHAMARKA MURUKUNA",
      subtitle: "24 murukuna (300 - 3,950 m s.n.m.) chaninwan hampinwan",
      searchPlaceholder: "Muruta utaq llaqtata maskay...",
      filters: {
        all: "Llapan",
        profitable: "Hatun Ganancia",
        valleys: "Wayq'u / Cajabamba",
        nitrogen: "Allpa Kallpachaq",
        resilient: "Ch'aki + Qasa",
        forage: "Uywa Q'achu",
      },
    },
    copilot: {
      title: "YUYAYCHAQ YANAPAQ",
      subtitle: "Kashamarka rimaypi utaq Kastillanupi tapuy",
      inputPlaceholder: "Kayhinata qillqay: Cajabamba llaqtapi kashani, tomillo tarpuyta munani...",
      sendBtn: "TAPUYTA KACHAY",
      listenBtn: "Uyariy",
      applyPlanBtn: "Chakrayman Churay",
      understoodTitle: "RIKSISQA WILLAKUY",
      examplesTitle: "TAPUY RIKUCHINAKUNA",
    },
  },
};

const CROP_QU_PHRASES: Array<[RegExp, string]> = [
  // Crop names (24 crops + special states)
  [/Avena forrajera \+ Vicia/gi, "Awina + Vicia (Q'achu p'istuq)"],
  [/Avena \/ Vicia/gi, "Awina / Vicia"],
  [/Rye grass \+ Tr[eé]bol blanco/gi, "Rye grass + Trebol (Lichi q'achu)"],
  [/Rye grass \+ Tr[eé]bol/gi, "Rye grass + Trebol"],
  [/Ma[ií]z amil[aá]ceo/gi, "Sara (Maiz amilaceo)"],
  [/\bMa[ií]z\b/gi, "Sara"],
  [/Tarwi \/ Chocho/gi, "Tarwi (Chocho — Allpa kallpachaq)"],
  [/Papa nativa/gi, "Akshu (Papa nativa)"],
  [/\bPapa\b/g, "Akshu (Papa)"],
  [/\bpapa\b/g, "akshu"],
  [/\bQuinua\b/gi, "Kinwa (Quinua)"],
  [/\bCebada\b/gi, "Siwara (Cebada)"],
  [/\bTrigo\b/gi, "Triwu (Trigo)"],
  [/Arveja grano verde/gi, "Alwirja (Arveja)"],
  [/\bArveja\b/gi, "Alwirja (Arveja)"],
  [/Frijol canario \/ bayo/gi, "Purutu (Frijol)"],
  [/\bFrijol\b/gi, "Purutu (Frijol)"],
  [/Haba seca\/verde/gi, "Hawas (Haba)"],
  [/Haba verde\/seca/gi, "Hawas (Haba)"],
  [/\bHaba\b/gi, "Hawas (Haba)"],
  [/Caf[eé] de altura \(bajo sombra\)/gi, "Kaphiy (Cafe de altura)"],
  [/\bCaf[eé]\b/gi, "Kaphiy"],
  [/Cacao fino de aroma/gi, "Kakaw (Cacao)"],
  [/\bCacao\b/gi, "Kakaw"],
  [/Alfalfa dormante/gi, "Alhalha (Alfalfa)"],
  [/\bAlfalfa\b/gi, "Alhalha"],
  [/Tuna \+ Cochinilla del Carm[ií]n/gi, "Tuna + Cochinilla (Puka millwa)"],
  [/Tuna y Cochinilla del Carm[ií]n/gi, "Tuna + Cochinilla (Puka millwa)"],
  [/Tomillo \/ Or[eé]gano y Arom[aá]ticas/gi, "Tomillo / Oregano (Hampi qura)"],
  [/Tomillo y Arom[aá]ticas \(Or[eé]gano \/ Romero\)/gi, "Tomillo / Oregano (Hampi qura)"],
  [/Tomillo y Arom[aá]ticas/gi, "Tomillo / Oregano"],
  [/Tara \/ Taya \(Agroforester[ií]a nativa\)/gi, "Tara / Taya (Allpa q'imichiq)"],
  [/Tara \/ Taya \(Vaina agroforestal\)/gi, "Tara / Taya (Allpa q'imichiq)"],
  [/Palta Hass \/ Fuerte \(en rotaci[oó]n o franjas\)/gi, "Palta (Wayq'u Yunga)"],
  [/Palta en intercultivo/gi, "Palta (Wayq'u Yunga)"],
  [/Oca \/ Olluco \/ Mashua nativa/gi, "Uqa / Ulluku / Mashwa"],
  [/Oca \/ Olluco \/ Mashua/gi, "Uqa / Ulluku / Mashwa"],
  [/Arracacha \/ Racacha nativa/gi, "Rakacha / Laquchu"],
  [/\bArracacha\b/gi, "Rakacha"],
  [/Kiwicha \(Amaranto andino\)/gi, "Kiwicha (Qoyllur muru)"],
  [/Lenteja \/ Garbanzo serrano/gi, "Lintija / Garbanzo"],
  [/\bLenteja\b/gi, "Lintija"],
  [/Linaza andina/gi, "Linasa muru"],
  [/\bLinaza\b/gi, "Linasa"],
  [/Ajo \/ Cebolla biofumigante/gi, "Ahus / Sibulla (Allpa pichaq)"],
  [/Ajo de valle/gi, "Ahus (Wayq'u)"],
  [/Barbecho Estacional/gi, "Samay allpa (Ch'usaq)"],
  [/Barbecho \/ Rastrojo/gi, "Samay allpa / Chala"],
  [/\bBarbecho\b/gi, "Samay allpa"],
  [/Pasto Degradado/gi, "Mawkayasqa Q'achu"],
  [/Cultivo en Curso/gi, "Kunan Tarpuy"],

  // Live weather conditions
  [/Cielo despejado/gi, "Ch'uya pacha"],
  [/Parcialmente nublado/gi, "Puyuwan intiwan"],
  [/Cielo nublado/gi, "Puyusqa pacha"],
  [/Neblina densa/gi, "Raku puyu"],
  [/Tormenta y lluvia/gi, "Rayuwan hatun tamya"],
  [/Llovizna en chacra/gi, "Iphuyachkan chakrapi"],
  [/Lluvia activa/gi, "Tamya chayamuchkan"],
  [/Fr[ií]o intenso \/ Helada/gi, "Sinchi chiri / Qasa"],
  [/Open-Meteo Tiempo Real/gi, "Kunan pacha willay"],
  [/Climatolog[ií]a NASA POWER \(mes actual\)/gi, "Kunan killa pacha willay"],

  // Strategy & phase titles / water / crop history / map telemetry
  [/Manejo Tradicional Actual/gi, "Kunan Ñawpaq Llamkay"],
  [/Plan Tradicional/gi, "Ñawpaq Tarpuy"],
  [/Resiliencia H[ií]drica y Protecci[oó]n de Suelo/gi, "Yakuwan Allpa Amachay Tarpuy"],
  [/Cosecha Segura \(Resiliencia\)/gi, "Allin Yakuwan Tarpuy"],
  [/Resiliencia h[ií]drica/gi, "Yaku amachay"],
  [/Regeneraci[oó]n de Suelos y Rentabilidad Mixta/gi, "Allpa Kallpachay Qullqiwan"],
  [/Suelo F[eé]rtil y Rentable/gi, "Kallpasapa Allin Ganancia"],
  [/Campaña Actual \(Ahora\)/gi, "Kunan Tarpuy (Kunan)"],
  [/Campaña Actual/gi, "Kunan Tarpuy"],
  [/Cobertura Temprana/gi, "Ñawpaq Allpa P'istuy"],
  [/Cobertura Intermedia/gi, "Chawpi Allpa P'istuy"],
  [/Cobertura Estiaje 1/gi, "Ch'aki Pacha P'istuy 1"],
  [/Cobertura Estiaje 2/gi, "Ch'aki Pacha P'istuy 2"],
  [/Campaña 2 \(Cosecha Limpia\)/gi, "Iskay Tarpuy (Allin Pallay)"],
  [/Campaña Regenerativa/gi, "Allpa Kallpachaq Tarpuy"],
  [/Campaña en Curso/gi, "Kunan Tarpuy"],
  [/Sistema Lechero/gi, "Lichi Uywa Q'achu"],
  [/Consolidaci[oó]n Forrajera/gi, "Q'achu Sinchiyay"],
  [/Consolidaci[oó]n Lechera/gi, "Lichi Q'achu Sinchiyay"],
  [/Cierre Protector/gi, "P'istuy Tukuy"],
  [/Continuaci[oó]n/gi, "Qatiq Tarpuy"],

  // Zones, soil, water options, map layers
  [/Piso de Valle \(Cajamarca\)/gi, "Kashamarka Wayq'u"],
  [/Piso de Valle/gi, "Wayq'u Suyu"],
  [/Ladera Media/gi, "Chawpi Kinray"],
  [/Jalca \/ Puna H[uú]meda/gi, "Halka / Chiri Urqu"],
  [/Solo lluvia \(secano estricto\)/gi, "Tamyallawan (Mana qarpuyniyuq)"],
  [/Solo lluvia \(secano\)/gi, "Tamyallawan"],
  [/Cosecha de agua \/ Qocha \/ Micro-reservorio/gi, "Yaku huñuy / Qucha"],
  [/Qocha \/ Reservorio/gi, "Qucha / Yaku taqi"],
  [/Riego por turnos \/ Riego de auxilio/gi, "Mitawan qarpuy"],
  [/Riego por turnos/gi, "Mitawan qarpuy"],
  [/Acequia \/ Riego por gravedad/gi, "Sikya / Yaku puriy qarpuy"],
  [/Riego por gravedad/gi, "Sikya qarpuy"],
  [/Surcos \/ Melgas en contorno \(sin erosi[oó]n\)/gi, "Kinray wachu qarpuy"],
  [/Surcos en contorno/gi, "Kinray wachu"],
  [/Riego por aspersi[oó]n/gi, "Ch'allaywan qarpuy"],
  [/Aspersi[oó]n/gi, "Ch'allay qarpuy"],
  [/Riego tecnificado por goteo \/ fertirriego/gi, "Sutuy-sutuy qarpuy"],
  [/Riego por goteo/gi, "Sutuy qarpuy"],
  [/Terreno libre \(Sin cultivo previo\)/gi, "Ch'usaq allpa (Mana tarpusqa)"],
  [/Monocultivo de Papa \(Solanum tuberosum\)/gi, "Sapa wata Akshulla tarpuy"],
  [/Papa repetida \(Monocultivo\)/gi, "Akshulla sapa wata"],
  [/Rotaci[oó]n corta Papa – Ma[ií]z amil[aá]ceo/gi, "Akshu – Sara muyuy"],
  [/Rotaci[oó]n corta Papa – Ma[ií]z/gi, "Akshu – Sara muyuy"],
  [/Pastos degradados \/ sobrepastoreo/gi, "Mawkayasqa q'achu"],
  [/Pasto agotado \(Ryegrass\)/gi, "Mawkayasqa q'achu"],
  [/Cebada \/ Trigo continuo sin leguminosas/gi, "Sapa wata Siwara / Triwu"],
  [/Trigo \/ Cebada continua/gi, "Triwu / Siwara sapa wata"],
  [/Depende 100% de la lluvia estacional/gi, "Tamya chayamuptillan wiñan"],
  [/Almacenamiento en reservorio o qocha/gi, "Quchapi waqaychasqa yakuwan"],
  [/Riego suplementario por turnos de agua/gi, "Yaku mita chayamuptin qarpunapaq"],
  [/Conducci[oó]n por canal o acequia comunal/gi, "Llaqta sikyanta hamuq yaku"],
  [/Surcos en contorno para frenar erosi[oó]n/gi, "Kinray wachu allpa ama apakunanpaq"],
  [/Distribuci[oó]n uniforme a presi[oó]n media/gi, "Pampasqa ch'allay yaku"],
  [/M[aá]xima eficiencia h[ií]drica y fertirriego/gi, "Aswan pisi yakuwan allin puquchiq"],

  // Map satellite layer labels & telemetry
  [/Vista Satelital Limpia/gi, "Chuya Satelite Qhaway"],
  [/Mapa Base/gi, "Qallariy Mapa"],
  [/Mapa limpio/gi, "Chuya mapa"],
  [/Toca una tarjeta arriba para superponer una capa satelital\.?/gi, "Hanaqpi huk tarjetata ñitiy satelite qatata qhawanapaq."],
  [/NDVI · Salud Vegetal/gi, "NDVI · Yura Allin kaynin"],
  [/Humedad de Suelo \(SMAP\)/gi, "Allpa Uqu kaynin (SMAP)"],
  [/Heladas y Calor \(ECOSTRESS\)/gi, "Qasa wan Ruphay (ECOSTRESS)"],
  [/Pendiente y Erosi[oó]n \(SRTM\)/gi, "Kinray wan Allpa Apakuy (SRTM)"],
  [/NDVI promedio/gi, "NDVI chawpi tupuy"],
  [/meses de suelo desnudo al a[nñ]o/gi, "killa q'ala allpa watapi"],
  [/Humedad radicular SMAP/gi, "Saphi uqu kaynin SMAP"],
  [/meses con riesgo/gi, "killa chikiyuq"],
  [/meses de tormenta/gi, "killa hatun tamyayuq"],
  [/Erosi[oó]n media/gi, "Chawpi allpa apakuy"],
  [/Mide el verdor y vigor de las plantas desde el espacio\. El color verde intenso indica buena cobertura vegetal\./gi,
    "Hanaq pachamanta yurapa q'umir kallpanta tupun. Q'umir kaptinqa allin p'istusqa allpam."],
  [/Mide cu[aá]nta agua guarda la tierra en la zona de las ra[ií]ces para saber si resistir[aá] d[ií]as sin lluvia\./gi,
    "Saphikunapi hayka yaku waqaychasqata tupun ch'aki punchawkunata aguantananpaq."],
  [/Detecta enfriamiento nocturno \(riesgo de helada en madrugada\) y estr[eé]s por calor al mediod[ií]a\./gi,
    "Tuta chiriyayta (tutapay qasa chikita) hinallataq chawpi punchaw ruphayta qawan."],
  [/Eval[uú]a la inclinaci[oó]n de tu terreno para evitar que las lluvias fuertes laven la capa f[eé]rtil del suelo\./gi,
    "Chakrapa kinrayninta qawan hatun tamya allin allpata ama apananpaq."],

  // Common explainability & climate advisory phrases
  [/usar variedad precoz por siembra tard[ií]a/gi, "utqay puquq muhuta akllay qipa tarpuypi"],
  [/Leguminosa fijadora/gi, "Allpa kallpachaq leguminosa"],
  [/ruptura de plagas/gi, "kurukunapa muyuyninta pakin"],
  [/que rompe ciclo de plagas/gi, "kurukunapa unquyninta pakin"],
  [/Cobertura protectora/gi, "Allpa p'istuq q'achu"],
  [/Cobertura en ventana desnuda/gi, "Q'ala allpa p'istuy"],
  [/incorporaci[oó]n de materia org[aá]nica/gi, "wanu allpaman churay"],
  [/protecci[oó]n de humedad/gi, "yaku waqaychay"],
  [/Aprovecha nitr[oó]geno biol[oó]gico fijado y lote con baja carga de plagas/gi,
    "Allpapi waqaychasqa kallpata chaskispa mana kuruyuq chakrata qichun"],
  [/Cierra el ciclo protegiendo el suelo del estiaje y lluvias de entrada/gi,
    "Allpata p'istuspa ch'aki pachamanta ñawpaq tamyamantapas amachan"],
  [/Instala pastura asociada perenne sobre suelo enriquecido/gi,
    "Kallpachasqa allpapi wiñaypaq q'achuta churan"],
  [/Continuidad productiva en campa[nñ]a siguiente/gi, "Qatiq tarpuypi hinalla puqunanpaq"],
  [/Sin suelo desnudo:/gi, "Mana q'ala allpayuq:"],
  [/meses con riesgo de helada/gi, "killa qasa chikiyuq"],
  [/Escenario normal/gi, "Normal pacha"],
  [/Sequ[ií]a severa/gi, "Sinchi ch'aki pacha"],
  [/Precipitaci[oó]n anual/gi, "Wata tamya"],
  [/Balance h[ií]drico/gi, "Yaku tupuy"],
];

const CROP_QU_WORD_MAP: Array<[RegExp, string]> = [
  [/\bprecauc[ií]on\b/gi, "yuyaywan"],
  [/\bprecipitaci[oó]n\b/gi, "tamya"],
  [/\blluvias\b/gi, "tamyakuna"],
  [/\blluvia\b/gi, "tamya"],
  [/\bheladas\b/gi, "qasakuna"],
  [/\bhelada\b/gi, "qasa"],
  [/\bsequ[ií]a\b/gi, "ch'aki"],
  [/\bhumedad\b/gi, "uqu kay"],
  [/\bnitr[oó]geno\b/gi, "allpa kallpa (N)"],
  [/\bplagas\b/gi, "kurukuna"],
  [/\bplaga\b/gi, "kuru"],
  [/\benfermedad(es)?\b/gi, "unquy"],
  [/\berosi[oó]n\b/gi, "allpa apakuy"],
  [/\bsuelo desnudo\b/gi, "q'ala allpa"],
  [/\bsuelos\b/gi, "allpakuna"],
  [/\bsuelo\b/gi, "allpa"],
  [/\btierra\b/gi, "allpa"],
  [/\bagua\b/gi, "yaku"],
  [/\briego\b/gi, "qarpuy"],
  [/\bcultivos\b/gi, "murukuna"],
  [/\bcultivo\b/gi, "muru"],
  [/\bsemillas\b/gi, "muhukuna"],
  [/\bsemilla\b/gi, "muhu"],
  [/\bsiembra\b/gi, "tarpuy"],
  [/\bsembrar\b/gi, "tarpuy"],
  [/\bcosecha\b/gi, "pallay"],
  [/\bpendiente\b/gi, "kinray"],
  [/\baltitud\b/gi, "sayaynin"],
  [/\btemperatura\b/gi, "ruphay / chiri"],
  [/\bcalor\b/gi, "ruphay"],
  [/\bmeses\b/gi, "killa"],
  [/\bmes\b/gi, "killa"],
  [/\baños\b/gi, "wata"],
  [/\baño\b/gi, "wata"],
  [/\bestiaje\b/gi, "ch'aki pacha"],
  [/\bra[ií]ces\b/gi, "saphikuna"],
  [/\bra[ií]z\b/gi, "saphi"],
  [/\bparcela\b/gi, "chakra"],
  [/\bchacra\b/gi, "chakra"],
  [/\belevaci[oó]n\b/gi, "sayaynin"],
  [/\briesgo\b/gi, "chiki"],
  [/\bprotecci[oó]n\b/gi, "amachay"],
  [/\bfijaci[oó]n\b/gi, "churay"],
  [/\bcobertura\b/gi, "allpa p'istuy"],
  [/\bforrajera\b/gi, "uywa q'achu"],
  [/\bmateria org[aá]nica\b/gi, "wanu"],
  [/\brendimiento\b/gi, "puquy"],
  [/\bahorro de agua\b/gi, "yaku waqaychay"],
  [/\bestabilidad\b/gi, "sinchi kaynin"],
  [/\breducido\b/gi, "pisiyachisqa"],
  [/\baumenta\b/gi, "wicharin"],
  [/\bevitar\b/gi, "ama kananpaq"],
  [/\bpara\b/gi, "-paq"],
  [/\bcon\b/gi, "-wan"],
  [/\bsin\b/gi, "mana"],
  [/\by\b/gi, "hinaspa"],
  [/\bEstacional\b/gi, "Mitampi"],
  [/\bBalance\b/gi, "Tupuy"],
  [/\bPendiente\b/gi, "Kinray"],
  [/\bAlto\b/gi, "Hatun"],
  [/\bModerado\b/gi, "Chawpi"],
  [/\bBajo\b/gi, "Pisi"],
];

export function translateCropText(text: string, lang: AppLanguage): string {
  if (lang === "es" || !text) return text;
  let out = text;
  for (const [pattern, replacement] of CROP_QU_PHRASES) {
    out = out.replace(pattern, replacement);
  }
  for (const [pattern, replacement] of CROP_QU_WORD_MAP) {
    out = out.replace(pattern, replacement);
  }
  return out;
}

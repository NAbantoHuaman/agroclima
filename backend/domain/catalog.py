"""Domain agricultural catalogs, reference zones, crop economics/IPM, and Cajamarca lookup tables."""

from __future__ import annotations

from datetime import timedelta, timezone
import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

MONTH_LABELS_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
DAYS_IN_MONTH = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31], dtype=float)

_CROP_ECONOMICS_AND_IPM: Dict[str, Dict[str, Any]] = {
    "papa": {
        "seed_cost_soles_ha": 3600,
        "seed_rate_label": "1,600 kg/ha tubérculo-semilla",
        "total_cost_soles_ha": 10500,
        "gross_income_soles_ha": 15200,
        "net_margin_soles_ha": 4700,
        "benefit_cost_ratio": 1.45,
        "consumer_benefit": "Alimento energético base; cuidar límite de fungicidas respetando días de carencia.",
        "pesticide_guide": {
            "target_pests": "Rancha (Phytophthora infestans) y Gorgojo de los Andes",
            "bio_control": "Caldo bordelés preventivo + Beauveria bassiana y trampas con feromona/cebo al aporque",
            "chemical_control": "Cimoxanil + Mancozeb (solo rotación preventiva) o Clorantraniliprol focalizado",
            "when_to_apply": "Aplicar preventivo solo cuando HR NASA > 80% y lluvia semanal > 25 mm; cortar químicos 14 días antes de cosecha",
            "pre_harvest_interval_days": 14,
        },
    },
    "maiz_amilaceo": {
        "seed_cost_soles_ha": 420,
        "seed_rate_label": "40 kg/ha grano seleccionado",
        "total_cost_soles_ha": 4600,
        "gross_income_soles_ha": 7900,
        "net_margin_soles_ha": 3300,
        "benefit_cost_ratio": 1.72,
        "consumer_benefit": "Mote, cancha y choclo tradicional libre de residuos + chala limpia para vacas lecheras.",
        "pesticide_guide": {
            "target_pests": "Gusano cogollero (Spodoptera frugiperda) y mazorquero",
            "bio_control": "Aceite de neem / Bacillus thuringiensis (Bt) directo al cogollo o arena+ceniza al 5%",
            "chemical_control": "Spinosad o Emamectina benzoato en dosis mínima si el daño supera 20% de plantas",
            "when_to_apply": "Vigilar en veranillos secos (SMAP bajo o Tmax > 22 °C en fase V4–V8); no aplicar tras floración",
            "pre_harvest_interval_days": 14,
        },
    },
    "cebada": {
        "seed_cost_soles_ha": 360,
        "seed_rate_label": "110 kg/ha semilla",
        "total_cost_soles_ha": 2450,
        "gross_income_soles_ha": 4300,
        "net_margin_soles_ha": 1850,
        "benefit_cost_ratio": 1.76,
        "consumer_benefit": "Cereal integral rico en fibra soluble (machica/morón) con mínima carga química.",
        "pesticide_guide": {
            "target_pests": "Roya amarilla y pulgón de la espiga",
            "bio_control": "Variedades resistentes INIA + control con mariquitas y jabón potásico en focos",
            "chemical_control": "Tebuconazol (solo si supera 15% de severidad foliar antes de embuche)",
            "when_to_apply": "Solo ante neblina persistente (HR > 82% por 5+ días); generalmente no requiere insecticida",
            "pre_harvest_interval_days": 21,
        },
    },
    "trigo": {
        "seed_cost_soles_ha": 420,
        "seed_rate_label": "120 kg/ha semilla certificada",
        "total_cost_soles_ha": 2700,
        "gross_income_soles_ha": 4850,
        "net_margin_soles_ha": 2150,
        "benefit_cost_ratio": 1.80,
        "consumer_benefit": "Harina regional entera de alto valor proteico y bajo costo familiar.",
        "pesticide_guide": {
            "target_pests": "Roya del tallo/hoja y carbón volador",
            "bio_control": "Desinfección de semilla con Trichoderma + rotación fuera de gramíneas continuas",
            "chemical_control": "Azoxistrobina + Ciproconazol si aparece roya temprana en hoja bandera",
            "when_to_apply": "Revisar tras lluvias cálidas (febrero–marzo); no aplicar después de grano lechoso",
            "pre_harvest_interval_days": 28,
        },
    },
    "quinua": {
        "seed_cost_soles_ha": 190,
        "seed_rate_label": "10 kg/ha (bajísimo costo/ha)",
        "total_cost_soles_ha": 3400,
        "gross_income_soles_ha": 7900,
        "net_margin_soles_ha": 4500,
        "benefit_cost_ratio": 2.32,
        "consumer_benefit": "Superalimento completo (9 aminoácidos esenciales); altísima rentabilidad frente al gasto mínimo en semilla.",
        "pesticide_guide": {
            "target_pests": "Mildiu (Peronospora variabilis) y Kcona-kcona (Eurysacca quinoae)",
            "bio_control": "Extracto de cola de caballo / caldo sulfocálcico para mildiu; Bt + trampas de luz para polilla",
            "chemical_control": "Metalaxil-M (solo en mildiu severo temprano) o Spinetoram en llenado si supera umbral",
            "when_to_apply": "Vigilar mildiu cuando lluvia semanal NASA > 30 mm; kcona-kcona en veranillos secos de panoja",
            "pre_harvest_interval_days": 21,
        },
    },
    "tarwi": {
        "seed_cost_soles_ha": 460,
        "seed_rate_label": "75 kg/ha semilla",
        "total_cost_soles_ha": 3200,
        "gross_income_soles_ha": 6900,
        "net_margin_soles_ha": 3700,
        "benefit_cost_ratio": 2.16,
        "consumer_benefit": "42% de proteína vegetal y calcio natural; además regala hasta +115 kg N/ha al suelo sin urea química.",
        "pesticide_guide": {
            "target_pests": "Antracnosis del tallo y barrenador menor",
            "bio_control": "Sus propios alcaloides repelen plagas y nematodos; usar Trichoderma en semilla si hubo encharcamiento",
            "chemical_control": "Cobre oxicloruro preventivo únicamente en lluvias continuas sobre suelos pesados",
            "when_to_apply": "Casi no requiere pesticidas; prevenir drenaje antes de lluvias GPM intensas",
            "pre_harvest_interval_days": 15,
        },
    },
    "haba": {
        "seed_cost_soles_ha": 680,
        "seed_rate_label": "90 kg/ha grano semilla",
        "total_cost_soles_ha": 3600,
        "gross_income_soles_ha": 7100,
        "net_margin_soles_ha": 3500,
        "benefit_cost_ratio": 1.97,
        "consumer_benefit": "Vaina verde y grano proteico de rápida cocción y aporte de hierro en dieta familiar.",
        "pesticide_guide": {
            "target_pests": "Mancha chocolate (Botrytis fabae) y pulgón negro",
            "bio_control": "Poda sanitaria/aireación + jabón potásico con neem para pulgón; caldo bordelés 0.5%",
            "chemical_control": "Carbendazim o Pirimetanil focalizado solo en brote húmedo de Botrytis",
            "when_to_apply": "Controlar pulgón al inicio de veranillos secos; Botrytis si HR > 85% por 4 días seguidos",
            "pre_harvest_interval_days": 10,
        },
    },
    "alfalfa": {
        "seed_cost_soles_ha": 780,
        "seed_rate_label": "20 kg/ha semilla inoculada",
        "total_cost_soles_ha": 3900,
        "gross_income_soles_ha": 8400,
        "net_margin_soles_ha": 4500,
        "benefit_cost_ratio": 2.15,
        "consumer_benefit": "Mejora calidad proteica de leche y queso artesanal sin residuos tóxicos en pastura.",
        "pesticide_guide": {
            "target_pests": "Pulgón azul/verde y oídio en estiaje",
            "bio_control": "Azufre mojable en polvo para oídio + corte oportuno al 10% de floración para cortar pulgones",
            "chemical_control": "Evitar insecticidas sintéticos para proteger abejas polinizadoras y ganado lechero",
            "when_to_apply": "Preferir corte mecánico/hoz temprano ante plagas; respetar 21 días antes de pastoreo si se aplicó azufre",
            "pre_harvest_interval_days": 14,
        },
    },
    "avena_vicia": {
        "seed_cost_soles_ha": 540,
        "seed_rate_label": "80 kg avena + 30 kg vicia/ha",
        "total_cost_soles_ha": 2350,
        "gross_income_soles_ha": 4950,
        "net_margin_soles_ha": 2600,
        "benefit_cost_ratio": 2.11,
        "consumer_benefit": "Ensilaje y heno saludable para invierno seco que evita caída de leche sin concentrados caros.",
        "pesticide_guide": {
            "target_pests": "Casi libre de plagas críticas por asociación gramínea-leguminosa",
            "bio_control": "Control cultural completo: la mezcla densa ahoga malezas sin herbicidas",
            "chemical_control": "No requiere pesticidas químicos de rutina en Cajamarca",
            "when_to_apply": "Solo vigilancia de roya si hay exceso de nitrógeno en primavera húmeda",
            "pre_harvest_interval_days": 7,
        },
    },
    "ryegrass_trebol": {
        "seed_cost_soles_ha": 890,
        "seed_rate_label": "25 kg ryegrass + 4 kg trébol/ha",
        "total_cost_soles_ha": 4200,
        "gross_income_soles_ha": 9800,
        "net_margin_soles_ha": 5600,
        "benefit_cost_ratio": 2.33,
        "consumer_benefit": "Leche fresca rica en omega-3 y beta-carotenos con mínimo uso de agroquímicos.",
        "pesticide_guide": {
            "target_pests": "Gusano de tierra al establecimiento y roya en pastura pasada",
            "bio_control": "Rotación de potreros cada 30–35 días + aplicación biológica de Trichoderma",
            "chemical_control": "No aplicar químicos sobre pradera en pastoreo activo",
            "when_to_apply": "Solo revisar suelo al mes de siembra; tras cierre de tapiz no necesita pesticidas",
            "pre_harvest_interval_days": 15,
        },
    },
    "frijol": {
        "seed_cost_soles_ha": 590,
        "seed_rate_label": "65 kg/ha semilla",
        "total_cost_soles_ha": 3350,
        "gross_income_soles_ha": 6950,
        "net_margin_soles_ha": 3600,
        "benefit_cost_ratio": 2.07,
        "consumer_benefit": "Menestra de alta proteína, fibra y hierro de bajo costo y cocción limpia.",
        "pesticide_guide": {
            "target_pests": "Mosca blanca, lorito verde y antracnosis",
            "bio_control": "Trampas amarillas + extracto de ajo/neem; Trichoderma en siembra contra pudrición radicular",
            "chemical_control": "Azoxistrobina (antracnosis) o Imidacloprid solo pre-floración si hay vector viral severo",
            "when_to_apply": "Monitorear mosca blanca en días secos/cálidos (>24 °C); cortar químicos en llenado de vaina",
            "pre_harvest_interval_days": 14,
        },
    },
    "arveja": {
        "seed_cost_soles_ha": 640,
        "seed_rate_label": "70 kg/ha semilla",
        "total_cost_soles_ha": 3800,
        "gross_income_soles_ha": 7900,
        "net_margin_soles_ha": 4100,
        "benefit_cost_ratio": 2.08,
        "consumer_benefit": "Vaina fresca rica en proteína vegetal y vitaminas, muy apreciada en canasta familiar.",
        "pesticide_guide": {
            "target_pests": "Oídio (cenicilla) y mosca minadora",
            "bio_control": "Azufre micronizado al inicio de cenicilla + aceite de neem",
            "chemical_control": "Difenoconazol o Abamectina focalizada solo antes de cuajado de vainas",
            "when_to_apply": "Oídio aparece en cambio seco/soleado con noches frías (abril–junio); respetar carencia para cosecha verde",
            "pre_harvest_interval_days": 7,
        },
    },
    "cafe": {
        "seed_cost_soles_ha": 2400,
        "seed_rate_label": "3,000 plantones bajo sombra/ha (amort. campaña)",
        "total_cost_soles_ha": 7200,
        "gross_income_soles_ha": 16500,
        "net_margin_soles_ha": 9300,
        "benefit_cost_ratio": 2.29,
        "consumer_benefit": "Café especial orgánico de altura con trazabilidad y cero residuos en taza.",
        "pesticide_guide": {
            "target_pests": "Roya amarilla (Hemileia vastatrix) y Broca del café",
            "bio_control": "Caldo bordelés/oxicloruro de cobre orgánico + Beauveria bassiana y trampas alcohólicas para broca",
            "chemical_control": "Evitar sistémicos si exportas orgánico; usar ciproconazol únicamente en renovación fuera de cosecha",
            "when_to_apply": "Aplicar Beauveria al 60–90 día post-floración con humedad > 75%; cobre al inicio de lluvias",
            "pre_harvest_interval_days": 30,
        },
    },
    "cacao": {
        "seed_cost_soles_ha": 2200,
        "seed_rate_label": "1,100 plantones injertados/ha (amort. campaña)",
        "total_cost_soles_ha": 6400,
        "gross_income_soles_ha": 14800,
        "net_margin_soles_ha": 8400,
        "benefit_cost_ratio": 2.31,
        "consumer_benefit": "Cacao fino de aroma rico en flavonoides y antioxidantes libre de cadmio y pesticidas.",
        "pesticide_guide": {
            "target_pests": "Moniliasis (Moniliophthora roreri) y escoba de bruja",
            "bio_control": "Recolección semanal de frutos enfermos + podas de luz + Trichoderma asperellum",
            "chemical_control": "Hidróxido de cobre preventivo en picos de lluvia; no necesita insecticidas sintéticos",
            "when_to_apply": "Rondas sanitarias cada 7 días cuando lluvia mensual > 130 mm (diciembre–abril)",
            "pre_harvest_interval_days": 14,
        },
    },
    "tuna_cochinilla": {
        "seed_cost_soles_ha": 1450,
        "seed_rate_label": "2,500 pencas + 15 kg cochinilla madre/ha",
        "total_cost_soles_ha": 3600,
        "gross_income_soles_ha": 10600,
        "net_margin_soles_ha": 7000,
        "benefit_cost_ratio": 2.94,
        "consumer_benefit": "Fruta antioxidante sin químicos + colorante carmín natural seguro para alimentos frente a tintes sintéticos.",
        "pesticide_guide": {
            "target_pests": "Pudrición bacteriana en pencas y hormigas depredadoras de cochinilla",
            "bio_control": "PROHIBIDO usar insecticidas químicos si crías cochinilla (matarían el insecto productivo); usar ceniza/cal en cortes",
            "chemical_control": "Solo pasta bordelesa en heridas de poda; nunca pulverizar insecticida sobre pencas",
            "when_to_apply": "Infestar con cochinilla al terminar lluvias fuertes (abril–mayo) cuando GPM marca tormentas bajas",
            "pre_harvest_interval_days": 0,
        },
    },
    "tomillo_aromaticas": {
        "seed_cost_soles_ha": 1350,
        "seed_rate_label": "28,000 esquejes enraizados/ha (rebrota 3 años)",
        "total_cost_soles_ha": 4300,
        "gross_income_soles_ha": 12200,
        "net_margin_soles_ha": 7900,
        "benefit_cost_ratio": 2.84,
        "consumer_benefit": "Hierba aromática y medicinal libre de residuos (aceites esenciales puros para cocina e infusiones).",
        "pesticide_guide": {
            "target_pests": "Oídio en exceso de humedad y arañita roja en sequía seca",
            "bio_control": "Azufre elemental ligero o bicarbonato de potasio; extracción de focos antes de cada corte",
            "chemical_control": "Evitar pesticidas sintéticos (rechazo en mercado de aromáticas/exportación por LMR)",
            "when_to_apply": "Cortar al iniciar botón floral en época seca; vigilar drenaje si lluvias GPM superan 140 mm/mes",
            "pre_harvest_interval_days": 14,
        },
    },
    "tara_taya": {
        "seed_cost_soles_ha": 1200,
        "seed_rate_label": "700 plantones/ha en linderos/curvas (perenne)",
        "total_cost_soles_ha": 2900,
        "gross_income_soles_ha": 7800,
        "net_margin_soles_ha": 4900,
        "benefit_cost_ratio": 2.69,
        "consumer_benefit": "Goma y taninos naturales no tóxicos para industria alimentaria/farmacéutica, protegiendo cuencas limpias.",
        "pesticide_guide": {
            "target_pests": "Pulgón negro en brotes tiernos y oídio en neblina",
            "bio_control": "Jabón potásico + caldo sulfocálcico al 1% en plantones jóvenes",
            "chemical_control": "Generalmente no requiere plaguicidas químicos una vez establecida",
            "when_to_apply": "Solo vigilar brotamiento al inicio de lluvias (octubre–diciembre)",
            "pre_harvest_interval_days": 20,
        },
    },
    "palta_intercultivo": {
        "seed_cost_soles_ha": 3200,
        "seed_rate_label": "350 plantones injertados/ha + semilla frijol en calles",
        "total_cost_soles_ha": 8600,
        "gross_income_soles_ha": 21500,
        "net_margin_soles_ha": 12900,
        "benefit_cost_ratio": 2.50,
        "consumer_benefit": "Fruta rica en grasas saludables (ácido oleico), potasio y vitamina E con trazabilidad de exportación.",
        "pesticide_guide": {
            "target_pests": "Tristeza del palto (Phytophthora), queresas y trips de flor",
            "bio_control": "Trichoderma al cuello + mulch grueso + aceite agrícola vegetal para queresas",
            "chemical_control": "Fosfito de potasio en drenche y abamectina solo en umbral de trips post-cuajado",
            "when_to_apply": "Aplicar fosfito/Trichoderma al inicio de lluvias y evitar empozamiento en raíz (riego por goteo ideal)",
            "pre_harvest_interval_days": 21,
        },
    },
    "oca_olluco_mashua": {
        "seed_cost_soles_ha": 1400,
        "seed_rate_label": "950 kg/ha tuberculillos nativos (60% menos que papa)",
        "total_cost_soles_ha": 4800,
        "gross_income_soles_ha": 9800,
        "net_margin_soles_ha": 5000,
        "benefit_cost_ratio": 2.04,
        "consumer_benefit": "Tubérculos nativos ricos en antocianinas, vitamina C y bajo índice glucémico casi libres de pesticidas.",
        "pesticide_guide": {
            "target_pests": "Gusanos de suelo menores y pudrición si se encharca",
            "bio_control": "La mashua libera isotiocianatos biofumigantes naturales que limpian nematodos sin químicos",
            "chemical_control": "No suele requerir fungicidas ni insecticidas sintéticos en altura",
            "when_to_apply": "Realizar buen aporque a los 60 días aprovechando lluvias de enero–febrero para drenar exceso de agua",
            "pre_harvest_interval_days": 15,
        },
    },
    "arracacha": {
        "seed_cost_soles_ha": 750,
        "seed_rate_label": "16,000 hijuelos propios/ha (bajo gasto efectivo)",
        "total_cost_soles_ha": 3900,
        "gross_income_soles_ha": 8600,
        "net_margin_soles_ha": 4700,
        "benefit_cost_ratio": 2.21,
        "consumer_benefit": "Raíz de altísima digestibilidad, calcio y vitamina A ideal para niños y adultos mayores, cultivada sin químicos.",
        "pesticide_guide": {
            "target_pests": "Pudrición húmeda de corona en suelos pesados",
            "bio_control": "Desinfección de hijuelos en ceniza o Trichoderma + camellones altos",
            "chemical_control": "No requiere aplicación de pesticidas en follaje",
            "when_to_apply": "Cuidado preventivo único al momento de preparar hijuelos antes de plantar",
            "pre_harvest_interval_days": 15,
        },
    },
    "kiwicha": {
        "seed_cost_soles_ha": 140,
        "seed_rate_label": "5 kg/ha (la semilla más barata del catálogo)",
        "total_cost_soles_ha": 2950,
        "gross_income_soles_ha": 7400,
        "net_margin_soles_ha": 4450,
        "benefit_cost_ratio": 2.51,
        "consumer_benefit": "Grano rico en lisina, calcio e hierro con relación ganancia/costo de semilla imbatible.",
        "pesticide_guide": {
            "target_pests": "Gusano cortador en plántula y lorito verde (Diabrotica)",
            "bio_control": "Trampas pegantes amarillas + Bacillus thuringiensis (Bt) en primeros 30 días",
            "chemical_control": "Cipermetrina focalizada únicamente si corta más de 15% en emergencia temprana",
            "when_to_apply": "Vigilar únicamente primeros 25 días tras siembra; luego la planta lignifica y no necesita pulverizaciones",
            "pre_harvest_interval_days": 21,
        },
    },
    "lenteja": {
        "seed_cost_soles_ha": 480,
        "seed_rate_label": "55 kg/ha grano semilla",
        "total_cost_soles_ha": 2400,
        "gross_income_soles_ha": 5200,
        "net_margin_soles_ha": 2800,
        "benefit_cost_ratio": 2.17,
        "consumer_benefit": "Legumbre de rápida cocción, alta en hierro y folato, con bajísima huella hídrica.",
        "pesticide_guide": {
            "target_pests": "Pulgón negro en veranillos y gorgojo de grano en almacén",
            "bio_control": "Jabón potásico + aceite de neem en campo; hojas de muña/eucalipto o bolsa hermética en almacén",
            "chemical_control": "Acetamiprid mínimo solo ante brote fuerte pre-floración",
            "when_to_apply": "Revisar envés de brotes si NASA marca 10+ días secos consecutivos en floración",
            "pre_harvest_interval_days": 14,
        },
    },
    "linaza": {
        "seed_cost_soles_ha": 320,
        "seed_rate_label": "40 kg/ha semilla",
        "total_cost_soles_ha": 2300,
        "gross_income_soles_ha": 5100,
        "net_margin_soles_ha": 2800,
        "benefit_cost_ratio": 2.22,
        "consumer_benefit": "Semilla medicinal rica en ácidos grasos Omega-3 y lignanos con bajísima necesidad de agroquímicos.",
        "pesticide_guide": {
            "target_pests": "Marchitez vascular si se siembra linaza continua",
            "bio_control": "Rotación cada 3–4 campañas fuera de lino + semilla limpia tratada con Trichoderma",
            "chemical_control": "No requiere fungicidas ni insecticidas foliares en rotación normal",
            "when_to_apply": "Prevención 100% por rotación; evitar repetir en lotes húmedos",
            "pre_harvest_interval_days": 15,
        },
    },
    "ajo_valle": {
        "seed_cost_soles_ha": 4200,
        "seed_rate_label": "700 kg/ha dientes-semilla seleccionados",
        "total_cost_soles_ha": 9800,
        "gross_income_soles_ha": 22400,
        "net_margin_soles_ha": 12600,
        "benefit_cost_ratio": 2.29,
        "consumer_benefit": "Condimento medicinal rico en alicina que además biofumiga y limpia el suelo de hongos para la siguiente campaña.",
        "pesticide_guide": {
            "target_pests": "Trips de la cebolla y mildeu velloso / mancha púrpura",
            "bio_control": "Trampas azules pegantes para trips + caldo bordelés preventivo + riego por goteo para no mojar hoja",
            "chemical_control": "Spinetoram para trips o Mancozeb/Azoxistrobina alternado si hay neblina húmeda sostenida",
            "when_to_apply": "Aplicar preventivo cuando HR NASA > 78%; suspender cualquier químico 21 días antes de cosecha",
            "pre_harvest_interval_days": 21,
        },
    },
}


def load_zones_data() -> Dict[str, Any]:
    with open(DATA_DIR / "cajamarca_zones.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_crops_data() -> Dict[str, Any]:
    with open(DATA_DIR / "crops_cajamarca.json", "r", encoding="utf-8") as f:
        doc = json.load(f)
    for crop in doc.get("crops", []):
        econ = _CROP_ECONOMICS_AND_IPM.get(crop["id"])
        if econ:
            crop.update(econ)
        else:
            crop.setdefault("seed_cost_soles_ha", 600)
            crop.setdefault("seed_rate_label", "Semilla seleccionada local")
            crop.setdefault("total_cost_soles_ha", 3200)
            crop.setdefault("gross_income_soles_ha", 5800)
            crop.setdefault("net_margin_soles_ha", 2600)
            crop.setdefault("benefit_cost_ratio", 1.81)
            crop.setdefault("consumer_benefit", "Alimento regional fresco en rotación sostenible.")
            crop.setdefault("pesticide_guide", {
                "target_pests": ", ".join(crop.get("vulnerable_pests") or ["Plagas locales"]),
                "bio_control": "Rotación botánica + Trichoderma/Beauveria y control cultural",
                "chemical_control": "Solo aplicación focalizada registrada SENASA si supera umbral económico",
                "when_to_apply": "Monitorear humedad foliar cuando HR NASA > 80%",
                "pre_harvest_interval_days": 14,
            })
    return doc


_CAJAMARCA_DEM_ANCHORS = [
    (-7.1638, -78.5003, 2720.0, 4.0, "Valle de Cajamarca (Centro)", "Franco arcilloso de valle", "Cajamarca"),
    (-7.1725, -78.4630, 2675.0, 3.2, "Piso de Valle — Baños del Inca / Llacanora", "Franco arcilloso aluvial", "Baños del Inca"),
    (-7.0850, -78.3420, 3360.0, 21.5, "Ladera Interandina — La Encañada / Combayo", "Franco arenoso superficial en ladera", "La Encañada"),
    (-7.2050, -78.3210, 2845.0, 9.4, "Zona de Secano Sur — Namora / Matara", "Franco limoso con baja retención hídrica", "Namora"),
    (-7.0400, -78.6300, 3510.0, 19.0, "Cabecera Jalca — Porcón / Huambocancha Alta", "Franco orgánico ácido de jalca", "Porcón"),
    (-7.2450, -78.4100, 2570.0, 6.5, "Valle Sur — Jesús / Chuco", "Franco aluvial de terraza", "Jesús"),
    (-7.1150, -78.5600, 3180.0, 17.5, "Ladera Oeste — Chetilla / Cumbemayo", "Franco arenoso pedregoso", "Chetilla"),
    (-7.1200, -78.4200, 3040.0, 14.0, "Ladera Norte — Otuzco / Tres Molinos", "Franco arcillo-arenoso", "Otuzco"),
    (-5.7080, -78.8080, 740.0, 8.5, "Yunga Fluvial — Jaén / Chamaya", "Franco arcillo-arenoso tropical", "Jaén"),
    (-5.1460, -79.0010, 1320.0, 16.0, "Selva Alta Cafetalera — San Ignacio", "Franco arcilloso ligeramente ácido", "San Ignacio"),
    (-7.2220, -78.8380, 920.0, 11.0, "Valle Cálido — Chilete / Magdalena", "Franco aluvial de quebrada", "Chilete / Magdalena"),
    (-7.3670, -78.8050, 2670.0, 15.5, "Ladera Suroeste — Contumazá", "Franco arenoso de ladera", "Contumazá"),
    (-7.3350, -78.1700, 2290.0, 8.0, "Valle Templado — San Marcos / Cajabamba", "Franco arcilloso profundo", "San Marcos"),
    (-6.8660, -78.1460, 2625.0, 10.5, "Valle Este — Celendín", "Franco arcilloso interandino", "Celendín"),
    (-6.5600, -78.6500, 2390.0, 13.5, "Cuenca Central — Chota / Bambamarca", "Franco limo-arcilloso", "Chota"),
    (-6.3780, -78.8180, 2645.0, 14.5, "Sierra Norte — Cutervo", "Franco arcilloso de altura media", "Cutervo"),
    (-6.9920, -78.5180, 3640.0, 18.5, "Cabecera Jalca — Entorno Mina Yanacocha / La Quinua", "Franco orgánico ácido de jalca", "Yanacocha / La Encañada"),
    (-6.7580, -78.6180, 3580.0, 21.0, "Cabecera Altoandina — Hualgayoc / Cerro Corona / Tantahuatay", "Franco orgánico ácido altoandino", "Hualgayoc"),
    (-7.0320, -78.3310, 3490.0, 19.5, "Jalca Oriental — Michiquillay / Quinuamayo", "Franco arenoso ácido de jalca", "La Encañada / Michiquillay"),
    (-6.6780, -78.5220, 2580.0, 11.5, "Valle del Llaucano — Bambamarca", "Franco arcilloso interandino", "Bambamarca"),
    (-7.6190, -78.0460, 2650.0, 9.5, "Valle de Condebamba — Cajabamba / Shahuindo", "Franco aluvial templado", "Cajabamba"),
]


_SOIL_OVERRIDE_LABELS = {
    "franco_arcilloso": "Tierra negra / franca (reportada por el agricultor)",
    "franco_arenoso": "Tierra arenosa de drenaje rápido (reportada por el agricultor)",
    "arcilloso_pesado": "Tierra barrosa / arcilla pesada (reportada por el agricultor)",
    "pedregoso": "Tierra cascajosa / pedregosa (reportada por el agricultor)",
}

LIMA_TZ = timezone(timedelta(hours=-5))
MONTHS_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
MONTHS_FULL_ES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

SPECIAL_PHASE_STATES: Dict[str, Dict[str, Any]] = {
    "suelo_desnudo": {
        "name": "Barbecho / Suelo desnudo",
        "scientific_name": "Sin cobertura viva",
        "color": "#DC2626",
        "status": "bare",
        "is_bare": True,
        "n_6m": -14.0,
        "om_6m": -10.0,
        "erosion_prot": 10.0,
    },
    "barbecho": {
        "name": "Barbecho / Suelo desnudo",
        "scientific_name": "Sin cobertura viva",
        "color": "#DC2626",
        "status": "bare",
        "is_bare": True,
        "n_6m": -14.0,
        "om_6m": -10.0,
        "erosion_prot": 10.0,
    },
    "pasto_degradado": {
        "name": "Pasto degradado (baja cobertura)",
        "scientific_name": "Pradera sobrepastoreada",
        "color": "#D97706",
        "status": "degraded",
        "is_bare": False,
        "n_6m": -25.0,
        "om_6m": -6.0,
        "erosion_prot": 36.0,
        "water_fit": 48.0,
        "frost_fit": 55.0,
        "terrain_fit": 62.0,
        "comm_val": 34.0,
        "pest_break": 38.0,
    },
    "rastrojo_manejo": {
        "name": "Rastrojo protector / Mulch (sin quema)",
        "scientific_name": "Cobertura muerta y preparación de suelo",
        "color": "#0F766E",
        "status": "cover",
        "is_bare": False,
        "n_6m": 4.0,
        "om_6m": 8.0,
        "erosion_prot": 74.0,
        "water_fit": 82.0,
        "frost_fit": 88.0,
        "terrain_fit": 88.0,
        "comm_val": 42.0,
        "pest_break": 66.0,
    },
    "cultivo_en_curso": {
        "name": "Cultivo actual en curso (hasta cosecha)",
        "scientific_name": "Campaña ya instalada en campo",
        "color": "#CA8A04",
        "status": "crop",
        "is_bare": False,
        "n_6m": -12.0,
        "om_6m": -3.0,
        "erosion_prot": 58.0,
        "water_fit": 62.0,
        "frost_fit": 65.0,
        "terrain_fit": 70.0,
        "comm_val": 60.0,
        "pest_break": 45.0,
    },
}


def _get_crops_map() -> Dict[str, Dict[str, Any]]:
    data = load_crops_data()
    return {c["id"]: c for c in data["crops"]}


def _botanical_family(cid: str) -> str:
    """Group Cajamarca crops into true botanical families to enforce multi-family rotation breaks."""
    if cid in ("tarwi", "haba", "lenteja", "arveja", "frijol", "alfalfa", "tara_taya"):
        return "fabaceae"
    if cid in ("papa", "oca_olluco_mashua", "arracacha"):
        return "tuber_root"
    if cid in ("avena_vicia", "ryegrass_trebol", "cebada", "trigo", "maiz_amilaceo"):
        return "poaceae_mix"
    if cid in ("quinua", "kiwicha"):
        return "amaranthaceae"
    return cid

_CAJAMARCA_LOCATIONS: List[Dict[str, Any]] = [
    {
        "keywords": [
            "mina yanacocha", "yanacocha", "la quinua", "carachugo",
            "maqui maqui", "pampa larga", "san jose yanacocha",
        ],
        "label": "Cabecera Jalca — Entorno Mina Yanacocha / La Quinua",
        "lat": -6.9920,
        "lon": -78.5180,
        "parcel_id": None,
        "default_water": "secano",
        "default_acidity": "acido",
        "default_frost": True,
    },
    {
        "keywords": ["hualgayoc", "cerro corona", "tantahuatay", "coimolache"],
        "label": "Cabecera Altoandina — Hualgayoc / Tantahuatay",
        "lat": -6.7580,
        "lon": -78.6180,
        "parcel_id": None,
        "default_water": "secano",
        "default_acidity": "acido",
        "default_frost": True,
    },
    {
        "keywords": ["michiquillay", "quinuamayo", "conga", "perol"],
        "label": "Jalca Oriental — Michiquillay / Quinuamayo",
        "lat": -7.0320,
        "lon": -78.3310,
        "parcel_id": None,
        "default_water": "secano",
        "default_acidity": "acido",
        "default_frost": True,
    },
    {
        "keywords": ["granja porcon", "porcon", "huambocancha", "tumbaden"],
        "label": "Cabecera Jalca — Porcón / Huambocancha Alta",
        "lat": -7.0400,
        "lon": -78.6300,
        "parcel_id": None,
        "default_water": "secano",
        "default_acidity": "acido",
        "default_frost": True,
    },
    {
        "keywords": ["banos del inca", "banos", "llacanora", "shaullo", "piso de valle"],
        "label": "Baños del Inca / Llacanora",
        "lat": -7.1725,
        "lon": -78.4630,
        "parcel_id": "banos_inca_llacanora",
    },
    {
        "keywords": ["la encanada", "encanada", "combayo", "polloc", "polloq", "yanacancha", "chanta"],
        "label": "La Encañada / Combayo",
        "lat": -7.0850,
        "lon": -78.3420,
        "parcel_id": "encanada_combayo",
    },
    {
        "keywords": ["namora", "matara", "san nicolas", "gregorio pita"],
        "label": "Namora / Matara",
        "lat": -7.2050,
        "lon": -78.3210,
        "parcel_id": "namora_matara",
    },
    {
        "keywords": ["jaen", "chamaya", "bellavista", "pucara", "colahuay"],
        "label": "Yunga Fluvial — Jaén / Chamaya",
        "lat": -5.7080,
        "lon": -78.8080,
        "parcel_id": None,
    },
    {
        "keywords": ["san ignacio", "chirinos", "namballe", "tabaconas"],
        "label": "Selva Alta Cafetalera — San Ignacio",
        "lat": -5.1460,
        "lon": -79.0010,
        "parcel_id": None,
    },
    {
        "keywords": ["chilete", "magdalena", "tembladera", "yonan", "jequetepeque"],
        "label": "Valle Cálido — Chilete / Magdalena",
        "lat": -7.2220,
        "lon": -78.8380,
        "parcel_id": None,
    },
    {
        "keywords": ["bambamarca", "llaucano"],
        "label": "Valle del Llaucano — Bambamarca",
        "lat": -6.6780,
        "lon": -78.5220,
        "parcel_id": None,
    },
    {
        "keywords": ["chota", "lajas", "cuyumalca"],
        "label": "Cuenca Central — Chota / Lajas",
        "lat": -6.5600,
        "lon": -78.6500,
        "parcel_id": None,
    },
    {
        "keywords": ["cutervo", "socota", "querocotillo"],
        "label": "Sierra Norte — Cutervo",
        "lat": -6.3780,
        "lon": -78.8180,
        "parcel_id": None,
    },
    {
        "keywords": ["celendin", "sorochuco", "oxamarca", "sucre"],
        "label": "Valle Este — Celendín",
        "lat": -6.8660,
        "lon": -78.1460,
        "parcel_id": None,
    },
    {
        "keywords": ["san marcos", "ichocan", "pedro galvez", "chancay"],
        "label": "Valle Templado — San Marcos",
        "lat": -7.3350,
        "lon": -78.1700,
        "parcel_id": None,
    },
    {
        "keywords": ["cajabamba", "condebamba", "shahuindo", "cachachi"],
        "label": "Valle de Condebamba — Cajabamba / Shahuindo",
        "lat": -7.6190,
        "lon": -78.0460,
        "parcel_id": None,
    },
    {
        "keywords": ["contumaza", "cascas", "guzmango", "chilete alto"],
        "label": "Ladera Suroeste — Contumazá",
        "lat": -7.3670,
        "lon": -78.8050,
        "parcel_id": None,
    },
    {
        "keywords": ["san pablo", "san miguel", "santa cruz", "kuntur wasi"],
        "label": "Sierra Occidental — San Pablo / San Miguel",
        "lat": -7.1180,
        "lon": -78.8250,
        "parcel_id": None,
    },
    {
        "keywords": ["jesus", "chuco", "cospan", "asuncion"],
        "label": "Jesús / Chuco",
        "lat": -7.2450,
        "lon": -78.4100,
        "parcel_id": None,
    },
    {
        "keywords": ["chetilla", "cumbemayo", "chamis"],
        "label": "Chetilla / Cumbemayo",
        "lat": -7.1150,
        "lon": -78.5600,
        "parcel_id": None,
    },
    {
        "keywords": ["otuzco", "tres molinos"],
        "label": "Otuzco / Tres Molinos",
        "lat": -7.1200,
        "lon": -78.4200,
        "parcel_id": None,
    },
    {
        "keywords": ["valle de cajamarca", "cajamarca"],
        "label": "Valle de Cajamarca (Centro)",
        "lat": -7.1638,
        "lon": -78.5003,
        "parcel_id": None,
    },
]


_PERU_CROP_ALIASES: List[tuple[str, str, List[str]]] = [
    ("papa", "Papa", ["papa", "papas", "akshu", "chacra de papa", "yungay", "huayro", "amarilla"]),
    ("maiz_amilaceo", "Maíz amiláceo", ["maiz amilaceo", "maiz", "choclo", "sara"]),
    ("quinua", "Quinua", ["quinua", "quinoa", "kinwa"]),
    ("cebada", "Cebada", ["cebada", "siwara"]),
    ("trigo", "Trigo", ["trigo", "triwu"]),
    ("arveja", "Arveja verde", ["arveja", "alverja", "arverja", "alberja", "guisante"]),
    ("haba", "Haba", ["haba", "habas", "hawas"]),
    ("tarwi", "Tarwi / Chocho", ["tarwi", "tarhui", "chocho", "lupino", "tawri"]),
    ("lenteja", "Lenteja", ["lenteja", "lentejas", "garbanzo"]),
    ("frijol", "Frijol", ["frijol", "frejol", "frijoles", "poroto", "pushpo"]),
    ("avena_vicia", "Avena + Vicia", ["avena", "vicia", "avena vicia", "avena con vicia", "forraje avena"]),
    ("ryegrass_trebol", "Ryegrass + Trébol", ["ryegrass", "rye grass", "trebol", "pasto asociado"]),
    ("alfalfa", "Alfalfa", ["alfalfa"]),
    ("oca_olluco_mashua", "Oca / Olluco / Mashua", ["oca", "olluco", "ulluco", "ulluku", "mashua", "mashwa", "tuberculos andinos"]),
    ("arracacha", "Arracacha", ["arracacha", "racacha"]),
    ("kiwicha", "Kiwicha / Amaranto", ["kiwicha", "amaranto", "coimi"]),
    ("linaza", "Linaza", ["linaza", "lino"]),
    ("tomillo_aromaticas", "Tomillo / Aromáticas", ["tomillo", "oregano", "romero", "manzanilla", "muna", "aromatica", "aromaticas"]),
    ("ajo_valle", "Ajo / Cebolla", ["ajo", "ajos", "cebolla"]),
    ("tuna_cochinilla", "Tuna + Cochinilla", ["tuna", "cochinilla", "nopal"]),
    ("tara_taya", "Tara / Taya", ["tara", "taya"]),
    ("palta_intercultivo", "Palta Hass / Fuerte", ["palta", "aguacate", "hass"]),
    ("cafe", "Café", ["cafe", "cafetal"]),
    ("cacao", "Cacao", ["cacao", "cacaotal"]),
]


_CROP_LABELS_BY_ID: Dict[str, str] = {cid: lbl for cid, lbl, _ in _PERU_CROP_ALIASES}
_VALID_CURRENT_CROPS = {
    "sin_cultivo",
    "monocultivo_papa",
    "papa_maiz",
    "pastos_degradados",
    "cebada_trigo_continuo",
}
_CURRENT_CROP_LABELS: Dict[str, str] = {
    "sin_cultivo": "Terreno libre (sin cultivo previo)",
    "monocultivo_papa": "Solo Papa (monocultivo)",
    "papa_maiz": "Papa y Maíz amiláceo",
    "pastos_degradados": "Pastos / Ganadería lechera",
    "cebada_trigo_continuo": "Cebada o Trigo continuo",
}
_VALID_WATER_MODES = {
    "secano",
    "cosecha_agua_qocha",
    "riego_deficitario",
    "riego_gravedad",
    "riego_melgas_surcos",
    "riego_aspersion",
    "riego_goteo",
}
_WATER_MODE_LABELS: Dict[str, str] = {
    "secano": "Solo lluvia (secano)",
    "cosecha_agua_qocha": "Cosecha de agua (Qocha / Reservorio)",
    "riego_deficitario": "Riego de auxilio / por turnos",
    "riego_gravedad": "Riego por acequia / gravedad",
    "riego_melgas_surcos": "Riego por melgas y surcos",
    "riego_aspersion": "Riego por aspersión",
    "riego_goteo": "Riego por goteo / fertirriego",
}


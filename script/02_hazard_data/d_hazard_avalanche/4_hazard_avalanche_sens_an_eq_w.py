# ============================================================
# AVALANCHE HAZARD
# Equal-weight stress test
#
# Baseline weights:
# P4 = 4
# P3 = 3
# P2 = 2
# P1 = 1
#
# Equal-weight scenario:
# P4 = P3 = P2 = P1 = 1
#
# Purpose:
# Assess how strongly the municipal ranking depends on the
# adopted hazard-class weighting structure.
# ============================================================

from qgis.core import QgsProject
from collections import defaultdict
import math
import csv
import os
import tempfile


# ============================================================
# 1. INPUT PARAMETERS
# ============================================================

HAZARD_LAYER_NAME = (
    "un_layer_com_un_per_pos_ispra_e_dissesti_poligonali_lomb_valanghe"
)

COMUNI_LAYER_NAME = "Comuni_correnti_poligonali"

ID_FIELD = "COD_ISTATN"
CLASS_FIELD = "per_fr_ita"
COMUNE_AREA_FIELD = "SHAPE_AREA"


# ============================================================
# 2. HAZARD CLASS MAPPING
# ============================================================
#
# Convert the original textual labels into simplified class
# codes used throughout the analysis.
#

CLASS_MAPPING = {
    "MOLTO ELEVATA P4": "P4",
    "ELEVATA P3": "P3",
    "MEDIA P2": "P2",
    "MODERATA P1": "P1"
}


# ============================================================
# 3. BASELINE AND EQUAL WEIGHTS
# ============================================================

BASELINE_WEIGHTS = {
    "P4": 4.0,
    "P3": 3.0,
    "P2": 2.0,
    "P1": 1.0
}

EQUAL_WEIGHTS = {
    "P4": 1.0,
    "P3": 1.0,
    "P2": 1.0,
    "P1": 1.0
}


# ============================================================
# 4. NORMALIZATION PARAMETERS
# ============================================================

EPSILON = 0.01
POSITIVE_MIN = 0.02
NORMALIZED_MAX = 0.99


# ============================================================
# 5. RETRIEVE LAYERS
# ============================================================

project = QgsProject.instance()

hazard_layers = project.mapLayersByName(
    HAZARD_LAYER_NAME
)

if not hazard_layers:
    raise Exception(
        "Layer not found: " + HAZARD_LAYER_NAME
    )

hazard_layer = hazard_layers[0]


comuni_layers = project.mapLayersByName(
    COMUNI_LAYER_NAME
)

if not comuni_layers:
    raise Exception(
        "Layer not found: " + COMUNI_LAYER_NAME
    )

comuni_layer = comuni_layers[0]


print("==========================================")
print("AVALANCHE EQUAL-WEIGHT STRESS TEST")
print("==========================================")

print(
    "Hazard layer:",
    hazard_layer.name()
)

print(
    "Municipal layer:",
    comuni_layer.name()
)


# ============================================================
# 6. MUNICIPAL AREAS
# ============================================================

area_comuni = {}

for feature in comuni_layer.getFeatures():

    comune = feature[ID_FIELD]
    area = feature[COMUNE_AREA_FIELD]

    if comune is None or area is None:
        continue

    area_comuni[comune] = float(area)


print(
    "Municipalities retrieved:",
    len(area_comuni)
)


# ============================================================
# 7. AGGREGATE HAZARD AREAS
# ============================================================

areas = defaultdict(
    lambda: {
        "P4": 0.0,
        "P3": 0.0,
        "P2": 0.0,
        "P1": 0.0
    }
)


for feature in hazard_layer.getFeatures():

    comune = feature[ID_FIELD]
    scenario = feature[CLASS_FIELD]

    if comune is None or scenario is None:
        continue

    # Standardize the original class label.
    scenario_text = str(
        scenario
    ).strip().upper()

    # Convert textual label to P1-P4.
    scenario_code = CLASS_MAPPING.get(
        scenario_text
    )

    # Ignore values not belonging to the four classes.
    if scenario_code is None:
        continue


    geometry = feature.geometry()

    if geometry is None or geometry.isEmpty():
        continue


    areas[comune][scenario_code] += (
        geometry.area()
    )


print(
    "Municipalities with avalanche hazard:",
    len(areas)
)


# ============================================================
# 8. CALCULATE RAW INDICATOR
# ============================================================

def calculate_raw(weights):

    raw_values = {}

    for comune, area_tot in area_comuni.items():

        if area_tot <= 0:

            raw_values[comune] = 0.0
            continue


        data = areas.get(comune)

        if not data:

            raw_values[comune] = 0.0
            continue


        numerator = (

            data["P4"] * weights["P4"]

            +

            data["P3"] * weights["P3"]

            +

            data["P2"] * weights["P2"]

            +

            data["P1"] * weights["P1"]

        )


        raw_values[comune] = (
            numerator
            /
            area_tot
        )


    return raw_values


# ============================================================
# 9. NORMALIZE
# ============================================================

def normalize_values(raw_values):

    positive_values = [

        value

        for value in raw_values.values()

        if value > 0

    ]


    normalized = {}


    if not positive_values:

        for comune in raw_values:

            normalized[comune] = EPSILON

        return normalized


    min_value = min(
        positive_values
    )

    max_value = max(
        positive_values
    )


    for comune, value in raw_values.items():

        if value == 0:

            normalized[comune] = EPSILON


        elif max_value == min_value:

            normalized[comune] = (
                NORMALIZED_MAX
            )


        else:

            normalized[comune] = (

                POSITIVE_MIN

                +

                (
                    (value - min_value)
                    /
                    (max_value - min_value)
                )

                *

                (
                    NORMALIZED_MAX
                    -
                    POSITIVE_MIN
                )

            )


    return normalized


# ============================================================
# 10. STATISTICAL FUNCTIONS
# ============================================================

def mean(values):

    if not values:
        return 0.0

    return (
        sum(values)
        /
        len(values)
    )


def rank_values(values):

    indexed = list(
        enumerate(values)
    )

    indexed.sort(
        key=lambda x: x[1]
    )


    ranks = [
        0.0
    ] * len(values)


    i = 0


    while i < len(indexed):

        j = i


        while (

            j + 1 < len(indexed)

            and

            indexed[j + 1][1]
            ==
            indexed[i][1]

        ):

            j += 1


        average_rank = (

            (i + j)
            /
            2.0

            +

            1

        )


        for k in range(
            i,
            j + 1
        ):

            original_index = (
                indexed[k][0]
            )

            ranks[
                original_index
            ] = average_rank


        i = j + 1


    return ranks


def pearson(x, y):

    if len(x) != len(y):
        return 0.0

    if len(x) < 2:
        return 0.0


    mx = mean(x)
    my = mean(y)


    numerator = sum(

        (a - mx)
        *
        (b - my)

        for a, b
        in zip(x, y)

    )


    denominator_x = math.sqrt(

        sum(

            (a - mx) ** 2

            for a in x

        )

    )


    denominator_y = math.sqrt(

        sum(

            (b - my) ** 2

            for b in y

        )

    )


    denominator = (

        denominator_x
        *
        denominator_y

    )


    if denominator == 0:
        return 0.0


    return (
        numerator
        /
        denominator
    )


def spearman(x, y):

    return pearson(

        rank_values(x),

        rank_values(y)

    )


# ============================================================
# 11. CALCULATE BASELINE AND EQUAL-WEIGHT SCENARIOS
# ============================================================

baseline_raw = calculate_raw(
    BASELINE_WEIGHTS
)

equal_raw = calculate_raw(
    EQUAL_WEIGHTS
)


baseline = normalize_values(
    baseline_raw
)

equal_scenario = normalize_values(
    equal_raw
)


municipality_ids = list(
    area_comuni.keys()
)


baseline_vector = [

    baseline[comune]

    for comune in municipality_ids

]


equal_vector = [

    equal_scenario[comune]

    for comune in municipality_ids

]


# ============================================================
# 12. GLOBAL COMPARISON
# ============================================================

rho = spearman(
    baseline_vector,
    equal_vector
)


absolute_differences = [

    abs(
        baseline[comune]
        -
        equal_scenario[comune]
    )

    for comune in municipality_ids

]


mad = mean(
    absolute_differences
)


print("")
print("==========================================")
print("GLOBAL RESULTS")
print("==========================================")

print(
    "Spearman baseline vs equal weights:",
    round(
        rho,
        6
    )
)

print(
    "Mean absolute difference:",
    round(
        mad,
        6
    )
)


# ============================================================
# 13. EXPORT MUNICIPAL RESULTS
# ============================================================

output_folder = (
    QgsProject.instance().homePath()
)

if not output_folder:

    output_folder = (
        tempfile.gettempdir()
    )


output_file = os.path.join(

    output_folder,

    "equal_weights_avalanche.csv"

)


with open(

    output_file,

    "w",

    newline="",

    encoding="utf-8"

) as csvfile:


    writer = csv.writer(
        csvfile,
        delimiter=";"
    )


    writer.writerow([

        "COD_ISTATN",

        "BASELINE",

        "EQUAL_WEIGHTS",

        "ABS_DIFF"

    ])


    for comune in municipality_ids:

        writer.writerow([

            comune,

            baseline[
                comune
            ],

            equal_scenario[
                comune
            ],

            abs(
                baseline[
                    comune
                ]
                -
                equal_scenario[
                    comune
                ]
            )

        ])


print("")
print(
    "Results saved to:",
    output_file
)
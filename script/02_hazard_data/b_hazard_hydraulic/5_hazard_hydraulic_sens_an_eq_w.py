# ============================================================
# HYDRAULIC HAZARD
# Equal-weight stress test
#
# Baseline weights:
# H = 1.00
# M = 0.25
# L = 0.10
#
# Equal-weight scenario:
# H = M = L = 1
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

HAZARD_LAYER_NAME = "prove_sensitività"
COMUNI_LAYER_NAME = "Comuni_correnti_poligonali"

ID_FIELD = "COD_ISTATN"
CLASS_FIELD = "CODSCENAR"
COMUNE_AREA_FIELD = "SHAPE_AREA"


# ============================================================
# 2. BASELINE AND EQUAL WEIGHTS
# ============================================================

BASELINE_WEIGHTS = {
    "H": 1.00,
    "M": 0.25,
    "L": 0.10
}

EQUAL_WEIGHTS = {
    "H": 1.00,
    "M": 1.00,
    "L": 1.00
}


# ============================================================
# 3. NORMALIZATION PARAMETERS
# ============================================================

EPSILON = 0.01
POSITIVE_MIN = 0.02
NORMALIZED_MAX = 0.99


# ============================================================
# 4. RETRIEVE LAYERS
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
print("HYDRAULIC EQUAL-WEIGHT STRESS TEST")
print("==========================================")


# ============================================================
# 5. MUNICIPAL AREAS
# ============================================================

area_comuni = {}

for feature in comuni_layer.getFeatures():

    comune = feature[ID_FIELD]
    area = feature[COMUNE_AREA_FIELD]

    if comune is None or area is None:
        continue

    area_comuni[comune] = float(area)


# ============================================================
# 6. AGGREGATE HAZARD AREAS
# ============================================================

areas = defaultdict(
    lambda: {
        "H": 0.0,
        "M": 0.0,
        "L": 0.0
    }
)


for feature in hazard_layer.getFeatures():

    comune = feature[ID_FIELD]
    scenario = feature[CLASS_FIELD]

    if comune is None or scenario is None:
        continue

    scenario = str(scenario).strip().upper()

    if scenario not in [
        "H",
        "M",
        "L"
    ]:
        continue

    geometry = feature.geometry()

    if geometry is None or geometry.isEmpty():
        continue

    areas[comune][scenario] += geometry.area()


# ============================================================
# 7. CALCULATE RAW INDICATOR
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

            data["H"]
            *
            weights["H"]

            +

            data["M"]
            *
            weights["M"]

            +

            data["L"]
            *
            weights["L"]

        )


        raw_values[comune] = (
            numerator / area_tot
        )

    return raw_values


# ============================================================
# 8. NORMALIZE
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


    min_value = min(positive_values)
    max_value = max(positive_values)


    for comune, value in raw_values.items():

        if value == 0:

            normalized[comune] = EPSILON


        elif max_value == min_value:

            normalized[comune] = NORMALIZED_MAX


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
# 9. STATISTICAL FUNCTIONS
# ============================================================

def mean(values):

    if not values:
        return 0.0

    return sum(values) / len(values)


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
            / 2.0
            + 1
        )

        for k in range(
            i,
            j + 1
        ):

            original_index = indexed[k][0]
            ranks[original_index] = average_rank

        i = j + 1

    return ranks


def pearson(x, y):

    mx = mean(x)
    my = mean(y)

    numerator = sum(
        (a - mx)
        *
        (b - my)
        for a, b in zip(x, y)
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

    return numerator / denominator


def spearman(x, y):

    return pearson(
        rank_values(x),
        rank_values(y)
    )


# ============================================================
# 10. CALCULATE BOTH SCENARIOS
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
# 11. GLOBAL COMPARISON
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
    round(rho, 6)
)

print(
    "Mean absolute difference:",
    round(mad, 6)
)


# ============================================================
# 12. EXPORT MUNICIPAL RESULTS
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
    "equal_weights_hydraulic.csv"
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
            baseline[comune],
            equal_scenario[comune],
            abs(
                baseline[comune]
                -
                equal_scenario[comune]
            )
        ])


print("")
print(
    "Results saved to:",
    output_file
)
# ============================================================
# Supplementary Material
#
# This script accompanies the manuscript:
#
# "Municipal Integrated Risk Index for Lombardy:
# A GIS-based framework for multi-hazard assessment
# supporting Civil Protection planning."
# ============================================================

# ============================================================
# HYDROGEOLOGICAL HAZARD
#
# Monte Carlo sensitivity analysis
# ============================================================
#
# Purpose
# -------
# Evaluate the robustness of the municipal hydrogeological
# hazard indicator with respect to the weights assigned to the
# ISPRA landslide-hazard classes.
#
# The highest class (P4) is retained as the reference value,
# while the P3, P2, and P1 weights are randomly varied by ±20%.
# Only configurations preserving P4 > P3 > P2 > P1 are accepted.
# For each valid simulation, the municipal hazard indicator is
# recalculated and normalized using the baseline procedure.
#
# Input
# -----
# - Landslide-hazard polygon layer containing municipal codes,
#   ISPRA hazard classes, and polygon areas.
# - Municipal boundary layer containing total municipal areas.
#
# Output
# ------
# - CSV file containing municipal simulation statistics.
# - Console summary of rank stability, variability, and the
#   effective ranges of the simulated weights.
#
# The original input layers are not modified.
# ============================================================

from qgis.core import QgsProject
from collections import defaultdict
import random
import math
import csv
import os
import tempfile



# ============================================================
# 1. INPUT PARAMETERS
# ============================================================
# Define input layers, field names, and the number of simulations.

HAZARD_LAYER_NAME = (
    "un_layer_com_un_per_pos_ispra_e_dissesti_poligonali_lomb_frane"
)

COMUNI_LAYER_NAME = "Comuni_correnti_poligonali"

ID_FIELD = "COD_ISTATN"

CLASS_FIELD = "per_fr_ita"

POLYGON_AREA_FIELD = "area_frana"

COMUNE_AREA_FIELD = "SHAPE_AREA"


N_SIMULATIONS = 1000



# ============================================================
# 2. BASELINE WEIGHTS
# ============================================================
# Set the reference weights adopted in the main analysis.

W_P4_BASE = 4.0
W_P3_BASE = 3.0
W_P2_BASE = 2.0
W_P1_BASE = 1.0



# ============================================================
# 3. WEIGHT VARIATION
# ============================================================
# Define the ±20% uncertainty range applied to P3, P2, and P1.

VARIATION = 0.20



# ============================================================
# 4. NORMALIZATION PARAMETERS
# ============================================================
# Define the values used for zero-hazard and positive-hazard municipalities.

EPSILON = 0.01

POSITIVE_MIN = 0.02

NORMALIZED_MAX = 0.99



# ============================================================
# 5. REPRODUCIBILITY
# ============================================================
# Set a fixed random seed to reproduce the same simulated configurations.

RANDOM_SEED = 42

random.seed(RANDOM_SEED)



# ============================================================
# 6. RETRIEVE INPUT LAYERS
# ============================================================
# Retrieve the hazard and municipal layers from the current QGIS project.

project = QgsProject.instance()


hazard_layers = project.mapLayersByName(
    HAZARD_LAYER_NAME
)

if not hazard_layers:

    raise Exception(
        "Hazard layer not found: "
        + HAZARD_LAYER_NAME
    )

hazard_layer = hazard_layers[0]


comuni_layers = project.mapLayersByName(
    COMUNI_LAYER_NAME
)

if not comuni_layers:

    raise Exception(
        "Municipal layer not found: "
        + COMUNI_LAYER_NAME
    )

comuni_layer = comuni_layers[0]


print("")
print("=" * 60)
print("GLOBAL SENSITIVITY ANALYSIS")
print("HYDROGEOLOGICAL HAZARD")
print("=" * 60)

print(
    "Hazard layer:",
    hazard_layer.name()
)

print(
    "Municipal layer:",
    comuni_layer.name()
)



# ============================================================
# 7. VALIDATE REQUIRED FIELDS
# ============================================================
# Verify that all required fields are available before processing.

hazard_fields = [
    field.name()
    for field in hazard_layer.fields()
]

comuni_fields = [
    field.name()
    for field in comuni_layer.fields()
]


for required_field in [
    ID_FIELD,
    CLASS_FIELD,
    POLYGON_AREA_FIELD
]:

    if required_field not in hazard_fields:

        raise Exception(
            "Field '{}' not found in the hazard layer.".format(
                required_field
            )
        )


for required_field in [
    ID_FIELD,
    COMUNE_AREA_FIELD
]:

    if required_field not in comuni_fields:

        raise Exception(
            "Field '{}' not found in the municipal layer.".format(
                required_field
            )
        )



# ============================================================
# 8. RETRIEVE MUNICIPAL AREAS
# ============================================================
# Store total municipal areas using the municipal identifier as key.

area_comuni = {}


for feature in comuni_layer.getFeatures():

    comune = feature[ID_FIELD]

    area = feature[COMUNE_AREA_FIELD]

    if comune is None:
        continue

    if area is None:
        continue

    try:

        area = float(area)

    except:

        continue

    if area <= 0:
        continue

    area_comuni[comune] = area


print("")
print(
    "Municipalities retrieved:",
    len(area_comuni)
)



# ============================================================
# 9. AGGREGATE HAZARD AREAS BY CLASS
# ============================================================
# Aggregate landslide-polygon areas by municipality and ISPRA hazard class.

areas = defaultdict(
    lambda: {
        "Molto elevata P4": 0.0,
        "Elevata P3": 0.0,
        "Media P2": 0.0,
        "Moderata P1": 0.0
    }
)


valid_classes = {
    "Molto elevata P4",
    "Elevata P3",
    "Media P2",
    "Moderata P1"
}


n_valid_polygons = 0
n_invalid_classes = 0


for feature in hazard_layer.getFeatures():

    comune = feature[ID_FIELD]

    scenario = feature[CLASS_FIELD]

    polygon_area = feature[
        POLYGON_AREA_FIELD
    ]


    if comune is None:
        continue

    if scenario is None:
        continue

    if polygon_area is None:
        continue



    scenario = str(
        scenario
    ).strip()


    if scenario not in valid_classes:

        n_invalid_classes += 1

        continue


    try:

        polygon_area = float(
            polygon_area
        )

    except:

        continue


    if polygon_area < 0:
        continue


    areas[comune][scenario] += (
        polygon_area
    )


    n_valid_polygons += 1


print(
    "Valid polygons used:",
    n_valid_polygons
)

print(
    "Records with unrecognized classes:",
    n_invalid_classes
)

print(
    "Municipalities with at least one hazard polygon:",
    len(areas)
)



# ============================================================
# 10. CHECK AVAILABLE HAZARD CLASSES
# ============================================================
# List the class values found in the input field for diagnostic purposes.

classes_found = set()


for feature in hazard_layer.getFeatures():

    value = feature[CLASS_FIELD]

    if value is not None:

        classes_found.add(
            str(value).strip()
        )


print("")
print(
    "Classes found in field",
    CLASS_FIELD,
    ":"
)

for value in sorted(
    classes_found
):

    print(
        " -",
        repr(value)
    )



# ============================================================
# 11. CALCULATE THE RAW HAZARD INDICATOR
# ============================================================
# Compute the weighted municipal hazard value before normalization.

def calculate_raw(
    weight_P4,
    weight_P3,
    weight_P2,
    weight_P1
):


    raw_values = {}


    for comune, area_tot in area_comuni.items():


        if area_tot <= 0:

            raw_values[
                comune
            ] = 0.0

            continue


        data = areas.get(
            comune
        )


        if not data:

            raw_values[
                comune
            ] = 0.0

            continue


        numerator = (

            data["Molto elevata P4"]
            * weight_P4

            +

            data["Elevata P3"]
            * weight_P3

            +

            data["Media P2"]
            * weight_P2

            +

            data["Moderata P1"]
            * weight_P1

        )


        raw_values[
            comune
        ] = (

            numerator
            /
            area_tot

        )


    return raw_values



# ============================================================
# 12. NORMALIZE MUNICIPAL HAZARD VALUES
# ============================================================
# Apply the same normalization procedure used for the baseline indicator.

def normalize_values(
    raw_values
):


    positive_values = [

        value

        for value
        in raw_values.values()

        if value > 0

    ]


    normalized = {}



    if not positive_values:

        for comune in raw_values:

            normalized[
                comune
            ] = EPSILON

        return normalized


    min_value = min(
        positive_values
    )

    max_value = max(
        positive_values
    )


    for comune, value in raw_values.items():


        if value == 0:

            normalized[
                comune
            ] = EPSILON


        elif max_value == min_value:

            normalized[
                comune
            ] = NORMALIZED_MAX


        else:

            normalized[
                comune
            ] = (

                POSITIVE_MIN

                +

                (
                    value
                    -
                    min_value
                )

                /

                (
                    max_value
                    -
                    min_value
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
# 13. CALCULATE THE BASELINE CONFIGURATION
# ============================================================
# Calculate the reference municipal values using the original weights.

baseline_raw = calculate_raw(

    W_P4_BASE,
    W_P3_BASE,
    W_P2_BASE,
    W_P1_BASE

)


baseline = normalize_values(
    baseline_raw
)


print("")
print("Baseline configuration calculated.")

print(
    "Baseline weights:",
    W_P4_BASE,
    W_P3_BASE,
    W_P2_BASE,
    W_P1_BASE
)



# ============================================================
# 14. CHECK THE BASELINE OUTPUT
# ============================================================
# Report the number and range of positive raw municipal hazard values.

positive_baseline = [

    value

    for value
    in baseline_raw.values()

    if value > 0

]


print(
    "Municipalities with P_raw > 0:",
    len(positive_baseline)
)


if positive_baseline:

    print(
        "Minimum positive P_raw:",
        min(positive_baseline)
    )

    print(
        "Maximum P_raw:",
        max(positive_baseline)
    )



# ============================================================
# 15. STATISTICAL FUNCTIONS
# ============================================================
# Define the descriptive statistics used to summarize simulation outputs.

def mean(values):

    if not values:
        return 0.0

    return (
        sum(values)
        /
        len(values)
    )


def standard_deviation(
    values
):

    if len(values) < 2:
        return 0.0


    m = mean(
        values
    )


    variance = (

        sum(

            (x - m) ** 2

            for x in values

        )

        /

        (
            len(values) - 1
        )

    )


    return math.sqrt(
        variance
    )


def percentile(
    values,
    percentile_value
):

    if not values:
        return 0.0


    sorted_values = sorted(
        values
    )


    k = (

        (
            len(sorted_values)
            -
            1
        )

        *

        percentile_value

    )


    floor_k = math.floor(k)

    ceil_k = math.ceil(k)


    if floor_k == ceil_k:

        return sorted_values[
            int(k)
        ]


    lower = sorted_values[
        floor_k
    ]

    upper = sorted_values[
        ceil_k
    ]


    return (

        lower
        *
        (
            ceil_k - k
        )

        +

        upper
        *
        (
            k - floor_k
        )

    )



# ============================================================
# 16. SPEARMAN RANK CORRELATION
# ============================================================
# Define the functions used to assess municipal ranking stability.

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

            j + 1
            <
            len(indexed)

            and

            indexed[j + 1][1]
            ==
            indexed[i][1]

        ):

            j += 1


        average_rank = (

            (
                i + j
            )

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


def pearson(
    x,
    y
):


    if len(x) != len(y):
        return 0.0


    if len(x) < 2:
        return 0.0


    mx = mean(x)
    my = mean(y)


    numerator = sum(

        (
            a - mx
        )

        *

        (
            b - my
        )

        for a, b
        in zip(x, y)

    )


    denominator_x = math.sqrt(

        sum(

            (
                a - mx
            ) ** 2

            for a in x

        )

    )


    denominator_y = math.sqrt(

        sum(

            (
                b - my
            ) ** 2

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


def spearman(
    x,
    y
):


    rank_x = rank_values(
        x
    )

    rank_y = rank_values(
        y
    )


    return pearson(
        rank_x,
        rank_y
    )



# ============================================================
# 17. PREPARE SIMULATION OUTPUTS
# ============================================================
# Initialize containers and preserve a fixed municipal order.

simulation_results = defaultdict(
    list
)

spearman_results = []

weight_history = []



municipality_ids = list(
    area_comuni.keys()
)


baseline_vector = [

    baseline[comune]

    for comune
    in municipality_ids

]



# ============================================================
# 18. MONTE CARLO SIMULATIONS
# ============================================================
# Generate valid weight combinations and recalculate the municipal indicator.

print("")
print(
    "Starting",
    N_SIMULATIONS,
    "Monte Carlo simulations..."
)


valid_simulations = 0


while valid_simulations < N_SIMULATIONS:



    weight_P4 = W_P4_BASE



    weight_P3 = random.uniform(

        W_P3_BASE
        *
        (
            1 - VARIATION
        ),

        W_P3_BASE
        *
        (
            1 + VARIATION
        )

    )



    weight_P2 = random.uniform(

        W_P2_BASE
        *
        (
            1 - VARIATION
        ),

        W_P2_BASE
        *
        (
            1 + VARIATION
        )

    )



    weight_P1 = random.uniform(

        W_P1_BASE
        *
        (
            1 - VARIATION
        ),

        W_P1_BASE
        *
        (
            1 + VARIATION
        )

    )



    if not (

        weight_P4
        >
        weight_P3
        >
        weight_P2
        >
        weight_P1

    ):

        continue


    valid_simulations += 1


    weight_history.append(

        (
            weight_P4,
            weight_P3,
            weight_P2,
            weight_P1
        )

    )



    raw_simulation = calculate_raw(

        weight_P4,
        weight_P3,
        weight_P2,
        weight_P1

    )



    normalized_simulation = (
        normalize_values(
            raw_simulation
        )
    )



    simulation_vector = []


    for comune in municipality_ids:


        value = (
            normalized_simulation[
                comune
            ]
        )


        simulation_results[
            comune
        ].append(
            value
        )


        simulation_vector.append(
            value
        )



    rho = spearman(

        baseline_vector,
        simulation_vector

    )


    spearman_results.append(
        rho
    )



    if (
        valid_simulations
        %
        100
        ==
        0
    ):

        print(
            "Valid simulations:",
            valid_simulations
        )



# ============================================================
# 19. CALCULATE MUNICIPAL ROBUSTNESS STATISTICS
# ============================================================
# Summarize the simulated distribution for each municipality.

summary = {}


for comune in municipality_ids:


    values = (
        simulation_results[
            comune
        ]
    )


    sim_mean = mean(
        values
    )


    sim_sd = standard_deviation(
        values
    )



    if sim_mean != 0:

        cv = (

            sim_sd
            /
            sim_mean

        ) * 100

    else:

        cv = 0.0



    absolute_differences = [

        abs(

            value
            -
            baseline[
                comune
            ]

        )

        for value
        in values

    ]


    mean_absolute_difference = mean(
        absolute_differences
    )


    summary[
        comune
    ] = {

        "P_BASE":
            baseline[comune],

        "P_MEAN":
            sim_mean,

        "P_SD":
            sim_sd,

        "P_CV":
            cv,

        "P_MIN":
            min(values),

        "P_MAX":
            max(values),

        "P_P025":
            percentile(
                values,
                0.025
            ),

        "P_P975":
            percentile(
                values,
                0.975
            ),

        "ABS_DIFF":
            mean_absolute_difference

    }



# ============================================================
# 20. CALCULATE GLOBAL ROBUSTNESS STATISTICS
# ============================================================
# Calculate overall rank stability and variability metrics.

mean_spearman = mean(
    spearman_results
)

min_spearman = min(
    spearman_results
)

max_spearman = max(
    spearman_results
)


mean_cv = mean([

    data[
        "P_CV"
    ]

    for data
    in summary.values()

])


global_abs_diff = mean([

    data[
        "ABS_DIFF"
    ]

    for data
    in summary.values()

])


print("")
print("=" * 60)
print("GLOBAL RESULTS")
print("=" * 60)


print(
    "Valid simulations:",
    len(spearman_results)
)


print(
    "Mean Spearman coefficient:",
    round(
        mean_spearman,
        6
    )
)


print(
    "Minimum Spearman coefficient:",
    round(
        min_spearman,
        6
    )
)


print(
    "Maximum Spearman coefficient:",
    round(
        max_spearman,
        6
    )
)


print(
    "Mean municipal CV (%):",
    round(
        mean_cv,
        4
    )
)


print(
    "Mean absolute difference from the baseline:",
    round(
        global_abs_diff,
        6
    )
)



# ============================================================
# 21. REPORT SIMULATED WEIGHT RANGES
# ============================================================
# Summarize the effective minimum and maximum weights used.

p3_values = [
    w[1]
    for w
    in weight_history
]

p2_values = [
    w[2]
    for w
    in weight_history
]

p1_values = [
    w[3]
    for w
    in weight_history
]


print("")
print("Simulated weight ranges:")


print(
    "P4:",
    W_P4_BASE,
    "(fixed)"
)


print(
    "P3:",
    round(min(p3_values), 4),
    "-",
    round(max(p3_values), 4)
)


print(
    "P2:",
    round(min(p2_values), 4),
    "-",
    round(max(p2_values), 4)
)


print(
    "P1:",
    round(min(p1_values), 4),
    "-",
    round(max(p1_values), 4)
)



# ============================================================
# 22. EXPORT MUNICIPAL RESULTS
# ============================================================
# Save the municipal sensitivity statistics as a semicolon-delimited CSV file.

output_folder = (
    QgsProject.instance().homePath()
)


if not output_folder:

    output_folder = (
        tempfile.gettempdir()
    )


output_file = os.path.join(

    output_folder,

    "sensitivity_hydrogeological.csv"

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

        "P_BASE",

        "P_MEAN",

        "P_SD",

        "P_CV_percent",

        "P_MIN",

        "P_MAX",

        "P_P025",

        "P_P975",

        "MEAN_ABS_DIFF"

    ])


    for comune in municipality_ids:


        data = summary[
            comune
        ]


        writer.writerow([

            comune,

            data["P_BASE"],

            data["P_MEAN"],

            data["P_SD"],

            data["P_CV"],

            data["P_MIN"],

            data["P_MAX"],

            data["P_P025"],

            data["P_P975"],

            data["ABS_DIFF"]

        ])



# ============================================================
# 23. FINAL OUTPUT
# ============================================================
# Report the output location and confirm that the source layers were not modified.

print("")
print("=" * 60)
print("HYDROGEOLOGICAL SENSITIVITY ANALYSIS COMPLETED")
print("=" * 60)

print("")
print(
    "Municipal results saved to:"
)

print(
    output_file
)

print("")
print(
    "The original layers were not modified."
)

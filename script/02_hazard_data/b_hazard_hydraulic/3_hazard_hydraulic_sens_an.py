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
# HYDRAULIC HAZARD
#
# Monte Carlo sensitivity analysis
# ============================================================
#
# Purpose
# -------
# Evaluate the robustness of the municipal hydraulic hazard
# indicator with respect to the weights assigned to the PGRA
# hazard classes:
#
# H = 1.00
# M = 0.25
# L = 0.10
#
# During each Monte Carlo simulation:
#
# 1. The H weight is retained as a fixed reference value.
# 2. The M weight is randomly varied by ±20%.
# 3. The L weight is randomly varied by ±20%.
# 4. The raw municipal hazard indicator is recalculated.
# 5. Positive values are normalized between 0.02 and 0.99,
#    while municipalities with no mapped hazard retain 0.01.
# 6. The simulated results are compared with the baseline
#    configuration.
#
# Input
# -----
# - Hydraulic hazard polygon layer containing municipal
#   identifiers and the H, M, and L hazard classes.
# - Municipal boundary layer containing total municipal areas.
#
# Output
# ------
# Two CSV files are generated:
#
# 1. Municipal results:
#    - P_BASE: baseline normalized value
#    - P_MEAN: mean simulated value
#    - P_SD: standard deviation
#    - P_CV: coefficient of variation (%)
#    - P_MIN: minimum simulated value
#    - P_MAX: maximum simulated value
#    - P_P025: 2.5th percentile
#    - P_P975: 97.5th percentile
#    - ABS_DIFF: mean absolute difference from the baseline
#
# 2. Global summary:
#    - Number of simulations
#    - Mean, minimum, and maximum Spearman coefficients
#    - Mean municipal coefficient of variation
#    - Mean absolute difference from the baseline
#
# The original layers are not modified.
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

# Name of the hydraulic hazard polygon layer.
HAZARD_LAYER_NAME = "prove_sensitività"

# Name of the municipal boundary layer.
COMUNI_LAYER_NAME = "Comuni_correnti_poligonali"

# Municipal identifier field.
ID_FIELD = "COD_ISTATN"

# Field containing the H, M, and L hazard classes.
CLASS_FIELD = "CODSCENAR"

# Field containing the total municipal area.
COMUNE_AREA_FIELD = "SHAPE_AREA"

# Number of Monte Carlo simulations.
N_SIMULATIONS = 1000


# ============================================================
# 2. BASELINE WEIGHTS
# ============================================================

W_H_BASE = 1.00
W_M_BASE = 0.25
W_L_BASE = 0.10


# ============================================================
# 3. WEIGHT VARIATION
# ============================================================
#
# A value of 0.20 corresponds to a ±20% variation.
#
# M = 0.25 ±20% -> 0.20–0.30
# L = 0.10 ±20% -> 0.08–0.12
#
# The H weight remains fixed at 1 because it represents the
# reference hazard class.

VARIATION = 0.20


# ============================================================
# 4. NORMALIZATION PARAMETERS
# ============================================================

# Value assigned to municipalities with no mapped hazard.
EPSILON = 0.01

# Minimum value assigned to municipalities with positive
# hydraulic hazard.
POSITIVE_MIN = 0.02

# Maximum normalized value.
NORMALIZED_MAX = 0.99


# ============================================================
# 5. REPRODUCIBILITY
# ============================================================
#
# The random seed ensures that the same 1,000 weight
# configurations are generated whenever the script is run.

RANDOM_SEED = 42

random.seed(RANDOM_SEED)


# ============================================================
# 6. RETRIEVE THE INPUT LAYERS
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
print("HYDRAULIC HAZARD SENSITIVITY ANALYSIS")
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
# 7. RETRIEVE MUNICIPAL AREAS
# ============================================================
#
# Store the total area of each municipality using the ISTAT
# municipal identifier as the dictionary key.
#
# This avoids reading the municipal layer during each Monte
# Carlo iteration.

area_comuni = {}

for feature in comuni_layer.getFeatures():

    comune = feature[ID_FIELD]

    area = feature[COMUNE_AREA_FIELD]

    if comune is None:
        continue

    if area is None:
        continue

    area_comuni[comune] = float(area)


print(
    "Municipalities retrieved:",
    len(area_comuni)
)


# ============================================================
# 8. AGGREGATE HAZARD AREAS BY MUNICIPALITY
# ============================================================
#
# For each municipality, calculate the area assigned to the
# H, M, and L hydraulic hazard classes.
#
# Polygon areas are calculated directly from the geometry.
# The input layer must therefore use an appropriate projected
# coordinate reference system with metric units.

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

    if comune is None:
        continue

    if scenario is None:
        continue

    scenario = str(scenario).strip().upper()

    if scenario not in ["H", "M", "L"]:
        continue

    geometry = feature.geometry()

    if geometry is None:
        continue

    if geometry.isEmpty():
        continue

    polygon_area = geometry.area()

    areas[comune][scenario] += polygon_area


print(
    "Municipalities with at least one hazard polygon:",
    len(areas)
)


# ============================================================
# 9. CALCULATE THE RAW MUNICIPAL HAZARD INDICATOR
# ============================================================
#
# The raw municipal hydraulic hazard indicator is calculated
# as:
#
#             AH × wH + AM × wM + AL × wL
# P_raw = -------------------------------------
#                     municipal area
#
# where:
#
# AH = area assigned to class H
# AM = area assigned to class M
# AL = area assigned to class L
# wH, wM, wL = corresponding class weights

def calculate_raw(
    weight_H,
    weight_M,
    weight_L
):

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

            data["H"] * weight_H

            +

            data["M"] * weight_M

            +

            data["L"] * weight_L

        )


        raw_values[comune] = (
            numerator / area_tot
        )


    return raw_values


# ============================================================
# 10. NORMALIZE THE MUNICIPAL HAZARD VALUES
# ============================================================
#
# Municipalities with P_raw = 0 are assigned 0.01.
#
# Positive values are normalized between 0.02 and 0.99.
#
# The minimum and maximum positive values are recalculated
# during every simulation because changes in the class weights
# may affect the complete distribution of municipal values.

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
# 11. CALCULATE THE BASELINE CONFIGURATION
# ============================================================
#
# The baseline represents the municipal hazard indicator
# obtained using the weights adopted in the main analysis:
#
# H = 1.00
# M = 0.25
# L = 0.10

baseline_raw = calculate_raw(

    W_H_BASE,

    W_M_BASE,

    W_L_BASE

)


baseline = normalize_values(
    baseline_raw
)


print("")
print("Baseline configuration calculated.")

print(
    "Baseline weights:",
    W_H_BASE,
    W_M_BASE,
    W_L_BASE
)


# ============================================================
# 12. STATISTICAL FUNCTIONS
# ============================================================

def mean(values):

    if not values:
        return 0.0

    return sum(values) / len(values)


def standard_deviation(values):

    if len(values) < 2:
        return 0.0

    m = mean(values)

    variance = sum(

        (x - m) ** 2

        for x in values

    ) / (len(values) - 1)

    return math.sqrt(variance)


def percentile(values, percentile_value):

    if not values:
        return 0.0

    sorted_values = sorted(values)

    k = (
        (len(sorted_values) - 1)
        *
        percentile_value
    )

    floor_k = math.floor(k)

    ceil_k = math.ceil(k)

    if floor_k == ceil_k:

        return sorted_values[int(k)]


    lower = sorted_values[floor_k]

    upper = sorted_values[ceil_k]


    return (

        lower * (ceil_k - k)

        +

        upper * (k - floor_k)

    )


# ============================================================
# 13. SPEARMAN RANK CORRELATION
# ============================================================
#
# Spearman's coefficient measures the stability of the
# municipal ranking.
#
# A coefficient equal to 1 indicates that the simulated and
# baseline rankings are identical.

def rank_values(values):

    indexed = list(
        enumerate(values)
    )

    indexed.sort(
        key=lambda x: x[1]
    )


    ranks = [0.0] * len(values)

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
            i + j
        ) / 2.0 + 1


        for k in range(i, j + 1):

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


    return numerator / denominator


def spearman(x, y):

    rank_x = rank_values(x)

    rank_y = rank_values(y)

    return pearson(
        rank_x,
        rank_y
    )


# ============================================================
# 14. PREPARE THE SIMULATION OUTPUTS
# ============================================================
#
# For each municipality, store the values obtained during the
# 1,000 Monte Carlo simulations.

simulation_results = defaultdict(
    list
)


spearman_results = []


# Use a fixed municipal order to compare the baseline and
# simulated vectors consistently.

municipality_ids = list(
    area_comuni.keys()
)


baseline_vector = [

    baseline[comune]

    for comune in municipality_ids

]


# Store the weights generated during the simulations for
# possible subsequent checks.

weight_history = []


# ============================================================
# 15. MONTE CARLO SIMULATIONS
# ============================================================

print("")
print(
    "Starting",
    N_SIMULATIONS,
    "Monte Carlo simulations..."
)


for simulation in range(
    N_SIMULATIONS
):


    # Retain the H weight as the fixed reference value.

    weight_H = W_H_BASE


    # Randomly vary the M weight by ±20%.

    weight_M = random.uniform(

        W_M_BASE
        *
        (1 - VARIATION),

        W_M_BASE
        *
        (1 + VARIATION)

    )


    # Randomly vary the L weight by ±20%.

    weight_L = random.uniform(

        W_L_BASE
        *
        (1 - VARIATION),

        W_L_BASE
        *
        (1 + VARIATION)

    )


    # Preserve the ordinal hierarchy H > M > L.
    #
    # The selected ranges already make violations unlikely,
    # but the condition is explicitly checked.

    if not (
        weight_H
        >
        weight_M
        >
        weight_L
    ):

        continue


    weight_history.append(

        (
            weight_H,
            weight_M,
            weight_L
        )

    )


    # Recalculate the raw municipal indicator.

    raw_simulation = calculate_raw(

        weight_H,

        weight_M,

        weight_L

    )


    # Normalize the simulated municipal values.

    normalized_simulation = (
        normalize_values(
            raw_simulation
        )
    )


    # Store the municipal results.

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


    # Calculate Spearman's rank correlation between the
    # baseline and the current simulated configuration.

    rho = spearman(

        baseline_vector,

        simulation_vector

    )


    spearman_results.append(
        rho
    )


    # Print progress every 100 simulations.

    if (
        (simulation + 1)
        % 100
        == 0
    ):

        print(
            "Simulations completed:",
            simulation + 1
        )


# ============================================================
# 16. CALCULATE MUNICIPAL ROBUSTNESS STATISTICS
# ============================================================

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


    sim_sd = (
        standard_deviation(
            values
        )
    )


    # Calculate the coefficient of variation:
    #
    # CV = standard deviation / mean × 100
    #
    # Lower values indicate greater relative stability.

    if sim_mean != 0:

        cv = (

            sim_sd
            /
            sim_mean

        ) * 100

    else:

        cv = 0.0


    # Calculate the mean absolute difference between the
    # simulated values and the baseline.

    absolute_differences = [

        abs(
            value
            -
            baseline[comune]
        )

        for value in values

    ]


    mean_absolute_difference = mean(
        absolute_differences
    )


    summary[comune] = {

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
# 17. CALCULATE GLOBAL ROBUSTNESS STATISTICS
# ============================================================

mean_spearman = mean(
    spearman_results
)

min_spearman = min(
    spearman_results
)

max_spearman = max(
    spearman_results
)


print("")
print("==========================================")
print("GLOBAL RESULTS")
print("==========================================")

print(
    "Valid simulations:",
    len(spearman_results)
)

print(
    "Mean Spearman coefficient:",
    round(mean_spearman, 6)
)

print(
    "Minimum Spearman coefficient:",
    round(min_spearman, 6)
)

print(
    "Maximum Spearman coefficient:",
    round(max_spearman, 6)
)


# Mean municipal coefficient of variation.

mean_cv = mean([

    data["P_CV"]

    for data in summary.values()

])


print(
    "Mean municipal CV (%):",
    round(mean_cv, 4)
)


# Mean absolute difference from the baseline.

global_abs_diff = mean([

    data["ABS_DIFF"]

    for data in summary.values()

])


print(
    "Mean absolute difference from the baseline:",
    round(global_abs_diff, 6)
)


# ============================================================
# 18. DEFINE THE OUTPUT DIRECTORY
# ============================================================
#
# The CSV files are saved in the QGIS project directory.
#
# If no project directory is available, the system temporary
# directory is used.

output_folder = QgsProject.instance().homePath()


if not output_folder:

    output_folder = tempfile.gettempdir()


# ============================================================
# 19. EXPORT THE MUNICIPAL RESULTS
# ============================================================

output_file = os.path.join(
    output_folder,
    "sensitivity_hydraulic.csv"
)


with open(
    output_file,
    "w",
    newline="",
    encoding="utf-8"
) as csvfile:


    # Use a semicolon delimiter to facilitate opening the file
    # in spreadsheet software configured with European locale
    # settings.

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

        data = summary[comune]


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
# 20. EXPORT THE GLOBAL SUMMARY
# ============================================================

summary_output_file = os.path.join(
    output_folder,
    "sensitivity_hydraulic_summary.csv"
)


with open(
    summary_output_file,
    "w",
    newline="",
    encoding="utf-8"
) as csvfile:


    writer = csv.writer(
        csvfile,
        delimiter=";"
    )


    writer.writerow([
        "Statistic",
        "Value"
    ])


    writer.writerow([
        "Number_of_simulations",
        len(spearman_results)
    ])


    writer.writerow([
        "Mean_Spearman",
        mean_spearman
    ])


    writer.writerow([
        "Minimum_Spearman",
        min_spearman
    ])


    writer.writerow([
        "Maximum_Spearman",
        max_spearman
    ])


    writer.writerow([
        "Mean_CV_percent",
        mean_cv
    ])


    writer.writerow([
        "Mean_absolute_difference",
        global_abs_diff
    ])


# ============================================================
# 21. FINAL OUTPUT
# ============================================================

print("")
print("==========================================")
print("HYDRAULIC SENSITIVITY ANALYSIS COMPLETED")
print("==========================================")

print("")

print(
    "Municipal results saved to:"
)

print(
    output_file
)

print("")

print(
    "Global summary saved to:"
)

print(
    summary_output_file
)

print("")

print(
    "The original layers were not modified."
)
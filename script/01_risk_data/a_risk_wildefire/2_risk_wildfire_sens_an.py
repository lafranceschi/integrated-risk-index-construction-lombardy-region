# ============================================================
# Supplementary Material
#
# WILDFIRE NORMALIZATION SENSITIVITY ANALYSIS
#
# Purpose
# -------
# Evaluate the robustness of the municipal integrated risk index
# with respect to the numerical contribution of the normalized
# wildfire risk component.
#
# During each Monte Carlo simulation:
#
# 1. R_wildfire is randomly varied by ±20%.
# 2. All other hazard-specific risk components remain fixed.
# 3. The integrated municipal risk index is recalculated as:
#
#    R_in_index =
#        R_wildfire
#        + R_seism
#        + R_hdr
#        + R_hydgeo
#        + R_aval
#        + R_adv_w
#
# 4. The simulated municipal ranking is compared with the
#    baseline ranking using Spearman's rank correlation.
#
# The original layer is not modified.
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

LAYER_NAME = "rischio_integrato"

ID_FIELD = "COD_ISTATN"

WILDFIRE_FIELD = "R_wildfire"
SEISMIC_FIELD = "R_seism"
HYDRAULIC_FIELD = "R_hdr"
HYDROGEO_FIELD = "R_hydgeo"
AVALANCHE_FIELD = "R_aval"
ADVERSE_WEATHER_FIELD = "R_adv_w"

# Existing integrated-risk field.
# It is not used as the baseline value because the baseline is
# recalculated directly from the six components.
INTEGRATED_FIELD = "R_in_index"

N_SIMULATIONS = 1000

# ±20% perturbation.
VARIATION = 0.20

# Fixed seed for reproducibility.
RANDOM_SEED = 42

random.seed(RANDOM_SEED)


# ============================================================
# 2. RETRIEVE INPUT LAYER
# ============================================================

project = QgsProject.instance()

layers = project.mapLayersByName(
    LAYER_NAME
)

if not layers:
    raise Exception(
        "Layer not found: " + LAYER_NAME
    )

layer = layers[0]


print("==========================================")
print("WILDFIRE NORMALIZATION SENSITIVITY ANALYSIS")
print("==========================================")

print(
    "Input layer:",
    layer.name()
)


# ============================================================
# 3. CHECK REQUIRED FIELDS
# ============================================================

required_fields = [

    ID_FIELD,

    WILDFIRE_FIELD,
    SEISMIC_FIELD,
    HYDRAULIC_FIELD,
    HYDROGEO_FIELD,
    AVALANCHE_FIELD,
    ADVERSE_WEATHER_FIELD

]


available_fields = [
    field.name()
    for field in layer.fields()
]


missing_fields = [

    field
    for field in required_fields
    if field not in available_fields

]


if missing_fields:

    raise Exception(

        "Missing fields: "
        +
        ", ".join(
            missing_fields
        )

    )


# ============================================================
# 4. SAFE NUMERIC CONVERSION
# ============================================================
#
# Null values are treated as zero.
#

def numeric_value(value):

    if value is None:
        return 0.0

    try:
        return float(value)

    except (TypeError, ValueError):
        return 0.0


# ============================================================
# 5. RETRIEVE MUNICIPAL RISK COMPONENTS
# ============================================================
#
# Store all six risk components by municipality.
#

municipal_data = {}


for feature in layer.getFeatures():

    comune = feature[
        ID_FIELD
    ]

    if comune is None:
        continue


    municipal_data[
        comune
    ] = {

        "wildfire":
            numeric_value(
                feature[
                    WILDFIRE_FIELD
                ]
            ),

        "seismic":
            numeric_value(
                feature[
                    SEISMIC_FIELD
                ]
            ),

        "hydraulic":
            numeric_value(
                feature[
                    HYDRAULIC_FIELD
                ]
            ),

        "hydrogeo":
            numeric_value(
                feature[
                    HYDROGEO_FIELD
                ]
            ),

        "avalanche":
            numeric_value(
                feature[
                    AVALANCHE_FIELD
                ]
            ),

        "adverse_weather":
            numeric_value(
                feature[
                    ADVERSE_WEATHER_FIELD
                ]
            )

    }


print(
    "Municipalities retrieved:",
    len(municipal_data)
)


# ============================================================
# 6. CALCULATE BASELINE INTEGRATED RISK
# ============================================================
#
# Baseline:
#
# R_in_index =
#     R_wildfire
#     + R_seism
#     + R_hdr
#     + R_hydgeo
#     + R_aval
#     + R_adv_w
#

baseline = {}


for comune, data in municipal_data.items():

    baseline[
        comune
    ] = (

        data[
            "wildfire"
        ]

        +

        data[
            "seismic"
        ]

        +

        data[
            "hydraulic"
        ]

        +

        data[
            "hydrogeo"
        ]

        +

        data[
            "avalanche"
        ]

        +

        data[
            "adverse_weather"
        ]

    )


print("")
print("Baseline integrated risk calculated.")


# ============================================================
# 7. OPTIONAL CONSISTENCY CHECK
# ============================================================
#
# If R_in_index already exists in the layer, compare it with
# the recalculated baseline and report the maximum difference.
#

if INTEGRATED_FIELD in available_fields:

    stored_values = {}

    for feature in layer.getFeatures():

        comune = feature[
            ID_FIELD
        ]

        if comune is None:
            continue

        stored_values[
            comune
        ] = numeric_value(
            feature[
                INTEGRATED_FIELD
            ]
        )


    differences = [

        abs(
            baseline[comune]
            -
            stored_values.get(
                comune,
                0.0
            )
        )

        for comune in baseline

    ]


    if differences:

        print(
            "Maximum difference between recalculated "
            "and stored R_in_index:",
            max(differences)
        )


# ============================================================
# 8. STATISTICAL FUNCTIONS
# ============================================================

def mean(values):

    if not values:
        return 0.0

    return (
        sum(values)
        /
        len(values)
    )


def standard_deviation(values):

    if len(values) < 2:
        return 0.0

    m = mean(
        values
    )

    variance = sum(

        (
            x - m
        ) ** 2

        for x in values

    ) / (
        len(values) - 1
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
            - 1
        )

        *

        percentile_value

    )


    floor_k = math.floor(
        k
    )

    ceil_k = math.ceil(
        k
    )


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
# 9. SPEARMAN RANK CORRELATION
# ============================================================

def rank_values(values):

    indexed = list(
        enumerate(
            values
        )
    )

    indexed.sort(
        key=lambda x: x[1]
    )


    ranks = [
        0.0
    ] * len(
        values
    )


    i = 0


    while i < len(
        indexed
    ):

        j = i


        while (

            j + 1
            <
            len(
                indexed
            )

            and

            indexed[
                j + 1
            ][1]

            ==

            indexed[
                i
            ][1]

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

            original_index = indexed[
                k
            ][0]

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


    mx = mean(
        x
    )

    my = mean(
        y
    )


    numerator = sum(

        (
            a - mx
        )

        *

        (
            b - my
        )

        for a, b
        in zip(
            x,
            y
        )

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
# 10. PREPARE OUTPUTS
# ============================================================

simulation_results = defaultdict(
    list
)

spearman_results = []

perturbation_history = []


# Fixed municipal order for ranking comparisons.

municipality_ids = list(
    municipal_data.keys()
)


baseline_vector = [

    baseline[
        comune
    ]

    for comune in municipality_ids

]


# ============================================================
# 11. MONTE CARLO SIMULATIONS
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


    # --------------------------------------------------------
    # Generate one common perturbation factor for wildfire.
    #
    # ±20% corresponds to a multiplicative factor between:
    #
    # 0.80 and 1.20
    #
    # The same factor is applied to all municipalities during
    # each simulation because the uncertainty concerns the
    # normalization scale of the wildfire component, rather
    # than municipality-specific measurement uncertainty.
    # --------------------------------------------------------

    wildfire_factor = random.uniform(

        1 - VARIATION,

        1 + VARIATION

    )


    perturbation_history.append(
        wildfire_factor
    )


    simulation_vector = []


    for comune in municipality_ids:

        data = municipal_data[
            comune
        ]


        simulated_wildfire = (

            data[
                "wildfire"
            ]

            *

            wildfire_factor

        )


        simulated_integrated_risk = (

            simulated_wildfire

            +

            data[
                "seismic"
            ]

            +

            data[
                "hydraulic"
            ]

            +

            data[
                "hydrogeo"
            ]

            +

            data[
                "avalanche"
            ]

            +

            data[
                "adverse_weather"
            ]

        )


        simulation_results[
            comune
        ].append(
            simulated_integrated_risk
        )


        simulation_vector.append(
            simulated_integrated_risk
        )


    # --------------------------------------------------------
    # Compare the municipal ranking with the baseline.
    # --------------------------------------------------------

    rho = spearman(

        baseline_vector,

        simulation_vector

    )


    spearman_results.append(
        rho
    )


    if (
        (
            simulation + 1
        )
        % 100
        == 0
    ):

        print(
            "Simulations completed:",
            simulation + 1
        )


# ============================================================
# 12. MUNICIPAL ROBUSTNESS STATISTICS
# ============================================================

summary = {}


for comune in municipality_ids:

    values = simulation_results[
        comune
    ]


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

        for value in values

    ]


    mean_absolute_difference = mean(
        absolute_differences
    )


    summary[
        comune
    ] = {

        "R_BASE":
            baseline[
                comune
            ],

        "R_MEAN":
            sim_mean,

        "R_SD":
            sim_sd,

        "R_CV":
            cv,

        "R_MIN":
            min(
                values
            ),

        "R_MAX":
            max(
                values
            ),

        "R_P025":
            percentile(
                values,
                0.025
            ),

        "R_P975":
            percentile(
                values,
                0.975
            ),

        "ABS_DIFF":
            mean_absolute_difference

    }


# ============================================================
# 13. GLOBAL ROBUSTNESS STATISTICS
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


mean_cv = mean([

    data[
        "R_CV"
    ]

    for data in summary.values()

])


global_abs_diff = mean([

    data[
        "ABS_DIFF"
    ]

    for data in summary.values()

])


print("")
print("==========================================")
print("GLOBAL RESULTS")
print("==========================================")

print(
    "Valid simulations:",
    len(
        spearman_results
    )
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
    "Mean absolute difference from baseline:",
    round(
        global_abs_diff,
        6
    )
)


# ============================================================
# 14. OUTPUT DIRECTORY
# ============================================================

output_folder = (
    QgsProject.instance().homePath()
)


if not output_folder:

    output_folder = (
        tempfile.gettempdir()
    )


# ============================================================
# 15. EXPORT MUNICIPAL RESULTS
# ============================================================

output_file = os.path.join(

    output_folder,

    "sensitivity_wildfire_integrated_risk.csv"

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

        "R_BASE",

        "R_MEAN",

        "R_SD",

        "R_CV_percent",

        "R_MIN",

        "R_MAX",

        "R_P025",

        "R_P975",

        "MEAN_ABS_DIFF"

    ])


    for comune in municipality_ids:

        data = summary[
            comune
        ]


        writer.writerow([

            comune,

            data[
                "R_BASE"
            ],

            data[
                "R_MEAN"
            ],

            data[
                "R_SD"
            ],

            data[
                "R_CV"
            ],

            data[
                "R_MIN"
            ],

            data[
                "R_MAX"
            ],

            data[
                "R_P025"
            ],

            data[
                "R_P975"
            ],

            data[
                "ABS_DIFF"
            ]

        ])


# ============================================================
# 16. EXPORT GLOBAL SUMMARY
# ============================================================

summary_output_file = os.path.join(

    output_folder,

    "sensitivity_wildfire_integrated_risk_summary.csv"

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
        len(
            spearman_results
        )
    ])


    writer.writerow([
        "Wildfire_variation_percent",
        VARIATION * 100
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
# 17. FINAL OUTPUT
# ============================================================

print("")
print("==========================================")
print("WILDFIRE SENSITIVITY ANALYSIS COMPLETED")
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
    "The original layer was not modified."
)
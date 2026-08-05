# ============================================================================
# Supplementary Material
#
# This script accompanies the manuscript:
#
# "Municipal Integrated Risk Index for Lombardy:
# A GIS-based framework for multi-hazard assessment
# supporting Civil Protection planning."
#
# ---------------------------------------------------------------------------
# Script: Integrated Risk Spatial Analysis
#
# Purpose
# -------
# This script evaluates the spatial structure of the final municipal
# Integrated Risk Index (R_in_index) using:
#   1. Global Moran's I
#   2. Getis-Ord Gi*
#
# The workflow automatically:
# - builds a Queen contiguity matrix;
# - excludes Campione d'Italia;
# - performs a Monte Carlo permutation test;
# - identifies hotspots and coldspots;
# - writes Gi* results to the layer.
#
# The original integrated risk values are never modified.
# ============================================================================

from qgis.core import (
    QgsProject,
    QgsSpatialIndex,
    QgsField
)

from qgis.PyQt.QtCore import QVariant

import math
import random


# =====================================================================
# 1. PARAMETERS
# =====================================================================

# Name of the final municipal integrated-risk layer.
LAYER_NAME = "rischio_integrato"

# Field containing the municipal Integrated Risk Index.
VALUE_FIELD = "R_in_index"

# Field containing the municipal identifier.
ID_FIELD = "COD_ISTATN"

# Campione d'Italia is identified by a string code, which preserves
# the leading zero.
CODICE_CAMPIONE = "03013040"

# Number of permutations used for the Moran's I significance test.
N_PERMUTATIONS = 999

# Random seed used to ensure reproducibility.
RANDOM_SEED = 42

random.seed(RANDOM_SEED)


# =====================================================================
# 2. LOAD INPUT LAYER
# =====================================================================

project = QgsProject.instance()

layers = project.mapLayersByName(
    LAYER_NAME
)

if not layers:
    raise Exception(
        "Layer '{}' not found.".format(
            LAYER_NAME
        )
    )

layer = layers[0]


# =====================================================================
# 3. VERIFY REQUIRED FIELDS
# =====================================================================

field_names = [
    field.name()
    for field in layer.fields()
]

if VALUE_FIELD not in field_names:
    raise Exception(
        "Field '{}' not found.".format(
            VALUE_FIELD
        )
    )

if ID_FIELD not in field_names:
    raise Exception(
        "Field '{}' not found.".format(
            ID_FIELD
        )
    )


print("")
print("=" * 70)
print("SPATIAL ANALYSIS OF THE INTEGRATED RISK INDEX")
print("=" * 70)

print(
    "Layer:",
    layer.name()
)

print(
    "Analysed variable:",
    VALUE_FIELD
)


# =====================================================================
# 4. LOAD MUNICIPALITIES
# =====================================================================

features = {}

values = {}

municipality_codes = {}

campione_excluded = False


for feat in layer.getFeatures():

    codice = feat[ID_FIELD]


    # -------------------------------------------------------------
    # EXCLUDE CAMPIONE D'ITALIA
    # -------------------------------------------------------------

    if codice is not None:

        codice_str = str(
            codice
        ).strip()

        if codice_str == CODICE_CAMPIONE:

            print(
                "Excluded from the spatial analysis:",
                codice_str,
                "- Campione d'Italia"
            )

            campione_excluded = True

            continue


    # -------------------------------------------------------------
    # VALIDATE THE INTEGRATED RISK VALUE
    # -------------------------------------------------------------

    value = feat[
        VALUE_FIELD
    ]

    if value is None:
        continue

    try:

        value = float(
            value
        )

    except:

        continue


    # -------------------------------------------------------------
    # VALIDATE THE GEOMETRY
    # -------------------------------------------------------------

    geometry = feat.geometry()

    if geometry is None:
        continue

    if geometry.isEmpty():
        continue


    # -------------------------------------------------------------
    # STORE THE ANALYSIS DATA
    # -------------------------------------------------------------

    fid = feat.id()

    features[
        fid
    ] = geometry

    values[
        fid
    ] = value

    municipality_codes[
        fid
    ] = str(
        codice
    ).strip()


# Number of municipalities included in the analysis.

n = len(
    features
)


print("")
print(
    "Municipalities included in the analysis:",
    n
)


if not campione_excluded:

    print("")
    print(
        "WARNING: Campione d'Italia was not found."
    )


if n < 3:

    raise Exception(
        "Insufficient number of municipalities for the analysis."
    )


# =====================================================================
# 5. BUILD QUEEN CONTIGUITY MATRIX
# =====================================================================
#
# Two municipalities are considered neighbours when they share either
# a boundary segment or a single vertex.
#
# =====================================================================

print("")
print(
    "Building the Queen contiguity matrix..."
)


spatial_index = QgsSpatialIndex()


for fid in features:

    feat = layer.getFeature(
        fid
    )

    spatial_index.addFeature(
        feat
    )


neighbors = {

    fid: set()

    for fid in features

}


processed = 0


for fid, geometry in features.items():

    candidate_ids = spatial_index.intersects(
        geometry.boundingBox()
    )


    for other_fid in candidate_ids:

        # Exclude self-neighbour relationships.
        if other_fid == fid:
            continue

        # Skip municipalities excluded from the analysis.
        if other_fid not in features:
            continue

        # Avoid duplicated neighbour pairs.
        if other_fid in neighbors[
            fid
        ]:
            continue


        other_geometry = features[
            other_fid
        ]


        try:

            are_neighbors = geometry.touches(
                other_geometry
            )

        except:

            are_neighbors = False


        if are_neighbors:

            neighbors[
                fid
            ].add(
                other_fid
            )

            neighbors[
                other_fid
            ].add(
                fid
            )


    processed += 1


    if processed % 200 == 0:

        print(
            "  municipalities processed:",
            processed,
            ""
        )


print("")
print(
    "Queen contiguity matrix completed."
)


# =====================================================================
# 6. NEIGHBOURHOOD DIAGNOSTICS
# =====================================================================

neighbor_counts = [

    len(
        neighbors[fid]
    )

    for fid in features

]


mean_neighbors = (

    sum(
        neighbor_counts
    )

    /

    len(
        neighbor_counts
    )

)


print("")
print(
    "Mean number of neighbouring municipalities:",
    round(
        mean_neighbors,
        2
    )
)

print(
    "Minimum:",
    min(
        neighbor_counts
    )
)

print(
    "Maximum:",
    max(
        neighbor_counts
    )
)


isolated = [

    fid

    for fid in features

    if len(
        neighbors[fid]
    ) == 0

]


if isolated:

    print("")
    print(
        "WARNING:",
        len(isolated),
        "municipalities have no neighbours."
    )

    print(
        "Municipal codes:"
    )

    for fid in isolated:

        print(
            " -",
            municipality_codes[
                fid
            ]
        )

else:

    print("")
    print(
        "No isolated municipalities were found."
    )


# =====================================================================
# 7. PREPARE ANALYSIS DATA
# =====================================================================

fids = list(
    features.keys()
)

x = [

    values[
        fid
    ]

    for fid in fids

]


# =====================================================================
# 8. GLOBAL MORAN'S I FUNCTION
# =====================================================================
#
# Row-standardised spatial weights are used. Each neighbour receives
# a weight equal to 1 divided by the number of neighbours of municipality i.
#
# =====================================================================

def calculate_moran(
    value_dictionary
):


    local_mean = (

        sum(
            value_dictionary.values()
        )

        /

        len(
            value_dictionary
        )

    )


    deviations = {

        fid:
        value_dictionary[
            fid
        ]
        -
        local_mean

        for fid in fids

    }


    numerator = 0.0

    S0 = 0.0


    for fid in fids:

        n_neighbors = len(
            neighbors[
                fid
            ]
        )


        if n_neighbors == 0:
            continue


        weight = (

            1.0

            /

            n_neighbors

        )


        for neighbor in neighbors[
            fid
        ]:

            numerator += (

                weight

                *

                deviations[
                    fid
                ]

                *

                deviations[
                    neighbor
                ]

            )

            S0 += weight


    denominator = sum(

        deviations[
            fid
        ] ** 2

        for fid in fids

    )


    if denominator == 0:
        return 0.0

    if S0 == 0:
        return 0.0


    I = (

        len(
            fids
        )

        /

        S0

        *

        numerator

        /

        denominator

    )


    return I


# =====================================================================
# 9. COMPUTE OBSERVED MORAN'S I
# =====================================================================

observed_moran = calculate_moran(
    values
)


expected_moran = (

    -1.0

    /

    (
        n
        -
        1
    )

)


print("")
print("=" * 70)
print("GLOBAL MORAN'S I")
print("=" * 70)

print(
    "Observed Moran's I:",
    round(
        observed_moran,
        6
    )
)

print(
    "Expected Moran's I:",
    round(
        expected_moran,
        6
    )
)


# =====================================================================
# 10. MONTE CARLO PERMUTATION TEST
# =====================================================================

print("")
print(
    "Starting the permutation test with",
    N_PERMUTATIONS,
    "permutations..."
)


original_values = [

    values[
        fid
    ]

    for fid in fids

]


permuted_morans = []


for permutation in range(
    N_PERMUTATIONS
):

    shuffled = original_values.copy()

    random.shuffle(
        shuffled
    )


    random_dictionary = {

        fid:
        shuffled[
            i
        ]

        for i, fid
        in enumerate(
            fids
        )

    }


    perm_I = calculate_moran(
        random_dictionary
    )


    permuted_morans.append(
        perm_I
    )


    if (
        permutation
        +
        1
    ) % 100 == 0:

        print(
            "  permutations completed:",
            permutation
            +
            1
        )


# =====================================================================
# 11. SIGNIFICANCE ASSESSMENT
# =====================================================================

observed_distance = abs(

    observed_moran

    -

    expected_moran

)


extreme_count = 0


for perm_I in permuted_morans:

    perm_distance = abs(

        perm_I

        -

        expected_moran

    )


    if perm_distance >= observed_distance:

        extreme_count += 1


moran_p = (

    extreme_count
    +
    1

) / (

    N_PERMUTATIONS
    +
    1

)


permutation_mean = (

    sum(
        permuted_morans
    )

    /

    len(
        permuted_morans
    )

)


permutation_variance = (

    sum(

        (
            value
            -
            permutation_mean
        ) ** 2

        for value in permuted_morans

    )

    /

    (
        len(
            permuted_morans
        )
        -
        1
    )

)


permutation_sd = math.sqrt(
    permutation_variance
)


if permutation_sd > 0:

    moran_z = (

        observed_moran

        -

        permutation_mean

    ) / permutation_sd

else:

    moran_z = 0.0


print("")
print(
    "Pseudo p-value:",
    round(
        moran_p,
        6
    )
)

print(
    "Permutation z-score:",
    round(
        moran_z,
        4
    )
)


# =====================================================================
# 12. INTERPRETATION OF GLOBAL MORAN'S I
# =====================================================================

print("")
print(
    "Interpretation:"
)


if moran_p < 0.05:

    if observed_moran > expected_moran:

        print(
            "SIGNIFICANT POSITIVE SPATIAL AUTOCORRELATION."
        )

        print(
            "Municipalities with similar values tend to be spatially clustered."
        )

    else:

        print(
            "SIGNIFICANT NEGATIVE SPATIAL AUTOCORRELATION."
        )

        print(
            "Municipalities with dissimilar values tend to be spatially adjacent."
        )

else:

    print(
        "Spatial autocorrelation is not statistically significant."
    )


# =====================================================================
# 13. GETIS-ORD Gi*
# =====================================================================

print("")
print("=" * 70)
print("GETIS-ORD Gi*")
print("=" * 70)

print(
    "Computing hotspot and coldspot statistics..."
)


global_mean = (

    sum(
        x
    )

    /

    n

)


global_variance = (

    sum(

        (
            value
            -
            global_mean
        ) ** 2

        for value in x

    )

    /

    n

)


global_sd = math.sqrt(
    global_variance
)


# =====================================================================
# 14. NORMAL CUMULATIVE DISTRIBUTION FUNCTION
# =====================================================================

def normal_cdf(
    z
):


    return (

        1.0

        +

        math.erf(

            z

            /

            math.sqrt(
                2.0
            )

        )

    ) / 2.0

# =====================================================================
# 15. COMPUTE GETIS-ORD Gi*
# =====================================================================

gi_results = {}


for fid in fids:


    # -------------------------------------------------------------
    # INCLUDE THE TARGET MUNICIPALITY
    # -------------------------------------------------------------
    #
    # The Gi* local neighbourhood includes both the target
    # municipality and its contiguous neighbours.

    local_neighbors = set(
        neighbors[
            fid
        ]
    )

    local_neighbors.add(
        fid
    )


    # -------------------------------------------------------------
    # BINARY SPATIAL WEIGHTS
    # -------------------------------------------------------------
    #
    # Each municipality included in the local neighbourhood
    # receives a weight equal to 1.

    sum_w = float(
        len(
            local_neighbors
        )
    )

    sum_w_squared = (
        sum_w
    )


    # -------------------------------------------------------------
    # LOCAL SUM OF INTEGRATED RISK VALUES
    # -------------------------------------------------------------

    local_sum = sum(

        values[
            neighbor
        ]

        for neighbor in local_neighbors

    )


    # -------------------------------------------------------------
    # NUMERATOR OF THE Gi* STATISTIC
    # -------------------------------------------------------------

    numerator = (

        local_sum

        -

        global_mean
        *
        sum_w

    )


    # -------------------------------------------------------------
    # DENOMINATOR OF THE Gi* STATISTIC
    # -------------------------------------------------------------

    denominator_component = (

        (

            n
            *
            sum_w_squared

            -

            sum_w ** 2

        )

        /

        (
            n
            -
            1
        )

    )


    if denominator_component > 0:

        denominator = (

            global_sd

            *

            math.sqrt(
                denominator_component
            )

        )

    else:

        denominator = 0.0


    if denominator == 0:

        z_score = 0.0

    else:

        z_score = (

            numerator

            /

            denominator

        )


    # -------------------------------------------------------------
    # TWO-TAILED P-VALUE
    # -------------------------------------------------------------

    p_value = (

        2.0

        *

        (

            1.0

            -

            normal_cdf(
                abs(
                    z_score
                )
            )

        )

    )


    # -------------------------------------------------------------
    # HOTSPOT AND COLDSPOT CLASSIFICATION
    # -------------------------------------------------------------
    #
    # Standard normal critical values are used:
    #
    # |z| >= 2.576 -> 99% confidence level
    # |z| >= 1.960 -> 95% confidence level
    # |z| >= 1.645 -> 90% confidence level

    if z_score >= 2.576:

        gi_class = (
            "Hotspot 99%"
        )

    elif z_score >= 1.960:

        gi_class = (
            "Hotspot 95%"
        )

    elif z_score >= 1.645:

        gi_class = (
            "Hotspot 90%"
        )

    elif z_score <= -2.576:

        gi_class = (
            "Coldspot 99%"
        )

    elif z_score <= -1.960:

        gi_class = (
            "Coldspot 95%"
        )

    elif z_score <= -1.645:

        gi_class = (
            "Coldspot 90%"
        )

    else:

        gi_class = (
            "Not significant"
        )


    gi_results[
        fid
    ] = {

        "z":
            z_score,

        "p":
            p_value,

        "class":
            gi_class

    }


# =====================================================================
# 16. SUMMARISE HOTSPOTS AND COLDSPOTS
# =====================================================================

categories = {

    "Hotspot 99%": 0,

    "Hotspot 95%": 0,

    "Hotspot 90%": 0,

    "Coldspot 99%": 0,

    "Coldspot 95%": 0,

    "Coldspot 90%": 0,

    "Not significant": 0

}


for result in gi_results.values():

    categories[
        result[
            "class"
        ]
    ] += 1


print("")
print(
    "Getis-Ord Gi* results:"
)


for category, count in categories.items():

    percentage = (

        count

        /

        n

        *

        100

    )


    print(

        " ",

        category,

        ":",

        count,

        "(",

        round(
            percentage,
            2
        ),

        "%)"

    )


# =====================================================================
# 17. CREATE OUTPUT FIELDS
# =====================================================================

existing_fields = [

    field.name()

    for field in layer.fields()

]


new_fields = []


if "GI_Z" not in existing_fields:

    new_fields.append(

        QgsField(
            "GI_Z",
            QVariant.Double
        )

    )


if "GI_P" not in existing_fields:

    new_fields.append(

        QgsField(
            "GI_P",
            QVariant.Double
        )

    )


if "GI_CLASS" not in existing_fields:

    new_fields.append(

        QgsField(
            "GI_CLASS",
            QVariant.String,
            len=30
        )

    )


if new_fields:

    layer.dataProvider().addAttributes(
        new_fields
    )

    layer.updateFields()


# =====================================================================
# 18. WRITE Gi* RESULTS TO THE LAYER
# =====================================================================

idx_z = layer.fields().indexOf(
    "GI_Z"
)

idx_p = layer.fields().indexOf(
    "GI_P"
)

idx_class = layer.fields().indexOf(
    "GI_CLASS"
)


updates = {}


for fid, result in gi_results.items():

    updates[
        fid
    ] = {

        idx_z:
            float(
                result[
                    "z"
                ]
            ),

        idx_p:
            float(
                result[
                    "p"
                ]
            ),

        idx_class:
            result[
                "class"
            ]

    }


layer.dataProvider().changeAttributeValues(
    updates
)


# =====================================================================
# 19. CLEAR PREVIOUS RESULTS FOR CAMPIONE D'ITALIA
# =====================================================================
#
# Any Gi* values assigned to Campione d'Italia during a
# previous execution are cleared to ensure consistency
# between repeated runs.

campione_updates = {}


for feat in layer.getFeatures():

    codice = feat[
        ID_FIELD
    ]

    if codice is None:
        continue


    codice_str = str(
        codice
    ).strip()


    if codice_str == CODICE_CAMPIONE:

        campione_updates[
            feat.id()
        ] = {

            idx_z:
                None,

            idx_p:
                None,

            idx_class:
                None

        }


if campione_updates:

    layer.dataProvider().changeAttributeValues(
        campione_updates
    )


layer.triggerRepaint()


# =====================================================================
# 20. FINAL SUMMARY
# =====================================================================

print("")
print("=" * 70)
print("SPATIAL ANALYSIS COMPLETED")
print("=" * 70)


print("")
print(
    "Municipalities analysed:",
    n
)


print("")
print(
    "GLOBAL MORAN'S I"
)


print(
    " I =",
    round(
        observed_moran,
        6
    )
)


print(
    " Expected I =",
    round(
        expected_moran,
        6
    )
)


print(
    " z =",
    round(
        moran_z,
        4
    )
)


print(
    " p =",
    round(
        moran_p,
        6
    )
)


print("")
print(
    "GETIS-ORD Gi*"
)


print(
    "Results written to the layer:"
)

print(
    " GI_Z"
)

print(
    " GI_P"
)

print(
    " GI_CLASS"
)


print("")

if campione_excluded:

    print(
        "Campione d'Italia was correctly excluded from "
        "Moran's I and Getis-Ord Gi*."
    )

else:

    print(
        "WARNING: Campione d'Italia was not excluded."
    )

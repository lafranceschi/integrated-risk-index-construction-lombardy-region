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
# SEISMIC HAZARD
#
# Municipal hazard normalization
# ============================================================
#
# Purpose
# -------
# Calculate the normalized municipal seismic hazard
# indicator by reclassifying the official Italian seismic
# zones into an increasing hazard scale and applying
# min-max normalization.
#
# Input
# -----
# Active QGIS layer containing the official seismic zoning
# assigned to each municipality.
#
# Output
# ------
# R_seism: normalized municipal seismic hazard indicator.
#
# The original geometries are not modified.
# ============================================================


from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsField


# ============================================================
# 1. INPUT LAYER
# ============================================================

layer = iface.activeLayer()


# ============================================================
# 2. INPUT PARAMETERS
# ============================================================
#
# Set the field names according to the input layer.

input_field = "zona"
output_field = "R_seism"


# Normalization interval adopted to ensure consistency and
# comparability with the remaining hazard and risk indicators.

min_norm = 0.01
max_norm = 0.99


# ============================================================
# 3. RECLASSIFY THE SEISMIC ZONES
# ============================================================
#
# The official Italian seismic zoning is converted into an
# increasing hazard score:
#
# Zone 4 -> 1 (lowest hazard)
# Zone 3 -> 2
# Zone 2 -> 3
# Zone 1 -> 4 (highest hazard)

mapping = {
    4: 1,
    3: 2,
    2: 3,
    1: 4
}

reclassified = {}

for f in layer.getFeatures():

    z = f[input_field]

    if z in mapping:
        reclassified[f.id()] = mapping[z]
    else:
        reclassified[f.id()] = None


# ============================================================
# 4. DEFINE THE NORMALIZATION RANGE
# ============================================================
#
# The normalized values are calculated from the theoretical
# minimum and maximum hazard scores.

vmin = 1
vmax = 4


# ============================================================
# 5. CREATE THE OUTPUT FIELD
# ============================================================

layer.startEditing()

if output_field not in [f.name() for f in layer.fields()]:

    layer.dataProvider().addAttributes([
        QgsField(output_field, QVariant.Double)
    ])

    layer.updateFields()

idx = layer.fields().indexOf(output_field)


# ============================================================
# 6. APPLY MIN-MAX NORMALIZATION
# ============================================================
#
# The reclassified hazard scores are normalized to the
# predefined interval while preserving the relative
# differences among municipalities.

updates = {}

for feat in layer.getFeatures():

    val = reclassified[feat.id()]

    if val is None:

        norm = None

    else:

        norm = (
            min_norm +
            ((val - vmin) / (vmax - vmin))
            * (max_norm - min_norm)
        )

    updates[feat.id()] = {idx: norm}

layer.dataProvider().changeAttributeValues(updates)


# ============================================================
# 7. SAVE THE RESULTS
# ============================================================

layer.commitChanges()


print("")
print("========================================")
print("Seismic hazard normalization completed successfully.")
print("========================================")
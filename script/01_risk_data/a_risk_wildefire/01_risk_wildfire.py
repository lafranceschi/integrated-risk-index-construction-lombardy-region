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
# WILDFIRE RISK
#
# Municipal risk normalization
# ============================================================
#
# Purpose
# -------
# Normalize the municipal wildfire risk indicator using
# min-max normalization in order to obtain values that are
# directly comparable with the other hazard and risk
# components included in the integrated framework.
#
# Input
# -----
# Active QGIS layer containing the raw municipal wildfire
# risk values.
#
# Output
# ------
# RISK_NORM: normalized municipal wildfire risk indicator.
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

input_field = "RISK_2025"
output_field = "RISK_NORM"


# Normalization interval adopted to ensure consistency and
# comparability with the remaining hazard and risk indicators.

min_norm = 0.0001
max_norm = 0.55


# ============================================================
# 3. RETRIEVE THE INPUT VALUES
# ============================================================

values = [
    float(f[input_field])
    for f in layer.getFeatures()
    if f[input_field] is not None
]

if not values:
    raise Exception("No valid input values were found.")

vmin = min(values)
vmax = max(values)

layer.startEditing()


# ============================================================
# 4. CREATE THE OUTPUT FIELD
# ============================================================

if output_field not in [f.name() for f in layer.fields()]:

    layer.dataProvider().addAttributes([
        QgsField(output_field, QVariant.Double, "double", 20, 10)
    ])

    layer.updateFields()


# ============================================================
# 5. APPLY MIN-MAX NORMALIZATION
# ============================================================
#
# The wildfire risk values are normalized to the predefined
# interval while preserving the relative differences among
# municipalities.

for feat in layer.getFeatures():

    value = feat[input_field]

    if value is None:

        norm = None

    elif vmax == vmin:

        norm = (min_norm + max_norm) / 2

    else:

        norm = (
            min_norm +
            ((float(value) - vmin) / (vmax - vmin))
            * (max_norm - min_norm)
        )

    feat[output_field] = norm
    layer.updateFeature(feat)


# ============================================================
# 6. SAVE THE RESULTS
# ============================================================

layer.commitChanges()


print("")
print("========================================")
print("Wildfire risk normalization completed successfully.")
print("========================================")
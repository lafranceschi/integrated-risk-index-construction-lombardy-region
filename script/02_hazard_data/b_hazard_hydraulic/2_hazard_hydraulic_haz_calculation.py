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
# Municipal hazard calculation and normalization
# ============================================================
#
# Purpose
# -------
# Calculate the municipal hydraulic hazard indicator by
# aggregating the areas assigned to the high, medium, and low
# hazard classes, applying class-specific weights, and
# normalizing the resulting municipal values.
#
# Municipalities with no mapped hydraulic hazard are assigned
# the minimum normalized value (0.01), whereas positive hazard
# values are normalized within the interval 0.02–0.99.
#
# Input
# -----
# - Active QGIS layer containing hydraulic hazard polygons,
#   municipal identifiers, hazard classes, and polygon areas.
# - Municipal boundary layer containing the total area of
#   each municipality.
#
# Output
# ------
# P_hdr: normalized municipal hydraulic hazard indicator.
#
# The original geometries are not modified.
# ============================================================


from collections import defaultdict
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsField, QgsProject


# ============================================================
# 1. INPUT LAYERS
# ============================================================

layer = iface.activeLayer()

comuni_layer = QgsProject.instance().mapLayersByName(
    "Comuni_correnti_poligonali"
)[0]


# ============================================================
# 2. HAZARD-CLASS WEIGHTS
# ============================================================
#
# The weights represent the relative severity assigned to the
# hydraulic hazard classes:
#
# H = high hazard
# M = medium hazard
# L = low hazard

weights = {
    'H': 1.0,
    'M': 0.25,
    'L': 0.1
}


# ============================================================
# 3. RETRIEVE MUNICIPAL AREAS
# ============================================================
#
# Store the total area of each municipality using the ISTAT
# municipal identifier as the dictionary key.

area_comuni = {}

for f in comuni_layer.getFeatures():

    cod = f['COD_ISTATN']
    area = f['SHAPE_AREA']

    if cod is not None and area is not None:
        area_comuni[cod] = float(area)

print("Municipalities retrieved:", len(area_comuni))


# ============================================================
# 4. AGGREGATE HAZARD AREAS BY MUNICIPALITY
# ============================================================
#
# Sum the polygon areas associated with each hazard class
# within each municipality.

sums = defaultdict(lambda: {
    'H': 0.0,
    'M': 0.0,
    'L': 0.0
})

for f in layer.getFeatures():

    com = f['COD_ISTATN']
    scen = f['CODSCENAR']
    val = float(f['area_all'] or 0)

    if scen in weights:
        sums[com][scen] += val


# ============================================================
# 5. CALCULATE THE RAW MUNICIPAL HAZARD INDICATOR
# ============================================================
#
# For each municipality, the raw indicator is calculated as
# the weighted sum of the areas assigned to the three hazard
# classes divided by the total municipal area.

raw_p = {}

for com, area_tot in area_comuni.items():

    data = sums.get(com, {
        'H': 0.0,
        'M': 0.0,
        'L': 0.0
    })

    if area_tot > 0:

        p = (
            data['H'] * weights['H'] +
            data['M'] * weights['M'] +
            data['L'] * weights['L']
        ) / area_tot

    else:

        p = 0

    raw_p[com] = p


# ============================================================
# 6. NORMALIZE THE MUNICIPAL HAZARD VALUES
# ============================================================
#
# Municipalities with no mapped hydraulic hazard are assigned
# the value 0.01.
#
# Positive raw hazard values are normalized between 0.02 and
# 0.99, preserving their relative differences.

norm_p = {}

positive_vals = [v for v in raw_p.values() if v > 0]

if positive_vals:

    min_p = min(positive_vals)
    max_p = max(positive_vals)

    for com, p in raw_p.items():

        if p == 0:

            norm_p[com] = 0.01

        elif max_p == min_p:

            norm_p[com] = 0.99

        else:

            norm_p[com] = (
                0.02 +
                ((p - min_p) / (max_p - min_p))
                * (0.99 - 0.02)
            )

else:

    # Assign the minimum value when no municipality presents
    # a positive hydraulic hazard value.
    for com in raw_p:
        norm_p[com] = 0.01

print(
    "Minimum positive raw hazard value:",
    min(positive_vals) if positive_vals else 0
)

print(
    "Maximum positive raw hazard value:",
    max(positive_vals) if positive_vals else 0
)


# ============================================================
# 7. CREATE AND POPULATE THE OUTPUT FIELD
# ============================================================
#
# Store the normalized municipal hydraulic hazard indicator
# in the P_hdr field.

layer.startEditing()

if 'P_hdr' not in [field.name() for field in layer.fields()]:

    layer.dataProvider().addAttributes([
        QgsField('P_hdr', QVariant.Double)
    ])

    layer.updateFields()

idx = layer.fields().indexOf('P_hdr')

updates = {}

for f in layer.getFeatures():

    com = f['COD_ISTATN']

    if com in norm_p:

        updates[f.id()] = {
            idx: norm_p[com]
        }

layer.dataProvider().changeAttributeValues(updates)


# ============================================================
# 8. SAVE THE RESULTS
# ============================================================

layer.commitChanges()


print("")
print("========================================")
print("Hydraulic hazard calculation completed successfully.")
print("The normalized values were stored in the P_hdr field.")
print("========================================")
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
# Municipal hazard calculation and normalization
# ============================================================
#
# Purpose
# -------
# Calculate the normalized municipal hydrogeological hazard
# indicator by aggregating the areas assigned to the four
# landslide hazard classes, applying class-specific weights,
# and normalizing the resulting municipal values.
#
# Municipalities with no mapped hydrogeological hazard are
# assigned the minimum normalized value (0.01), whereas
# positive hazard values are normalized within the interval
# 0.02–0.99.
#
# Input
# -----
# - Active QGIS layer containing landslide hazard polygons,
#   municipal identifiers, hazard classes, and polygon areas.
# - Municipal boundary layer containing the total area of
#   each municipality.
#
# Output
# ------
# P_hydgeo: normalized municipal hydrogeological hazard
# indicator.
#
# The original geometries are not modified.
# ============================================================


from collections import defaultdict
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsField, QgsProject


# ============================================================
# 1. INPUT LAYERS
# ============================================================

hazard_layer = iface.activeLayer()

comuni_layer = QgsProject.instance().mapLayersByName(
    "Comuni_correnti_poligonali"
)[0]


# ============================================================
# 2. HAZARD-CLASS WEIGHTS
# ============================================================
#
# The weights represent the relative severity assigned to the
# hydrogeological hazard classes:
#
# Molto elevata P4 = very high hazard
# Elevata P3       = high hazard
# Media P2         = medium hazard
# Moderata P1      = moderate hazard

weights = {
    'Molto elevata P4': 4,
    'Elevata P3': 3,
    'Media P2': 2,
    'Moderata P1': 1
}


# ============================================================
# 3. RETRIEVE MUNICIPAL AREAS
# ============================================================
#
# Store the total area of each municipality using the ISTAT
# municipal identifier as the dictionary key.

area_comuni = {
    f['COD_ISTATN']: float(f['SHAPE_AREA'])
    for f in comuni_layer.getFeatures()
    if f['COD_ISTATN'] is not None and f['SHAPE_AREA'] is not None
}


# ============================================================
# 4. AGGREGATE HAZARD AREAS BY MUNICIPALITY
# ============================================================
#
# Sum the polygon areas associated with each hydrogeological
# hazard class within each municipality.

sums = defaultdict(lambda: {
    'Molto elevata P4': 0.0,
    'Elevata P3': 0.0,
    'Media P2': 0.0,
    'Moderata P1': 0.0
})

for f in hazard_layer.getFeatures():

    com = f['COD_ISTATN']
    scen = f['per_fr_ita']
    val = float(f['area_frana'] or 0)

    if scen in weights:
        sums[com][scen] += val


# ============================================================
# 5. CALCULATE THE RAW MUNICIPAL HAZARD INDICATOR
# ============================================================
#
# For each municipality, the raw indicator is calculated as
# the weighted sum of the areas assigned to the four hazard
# classes divided by the total municipal area.

raw_p = {}

for com, area_tot in area_comuni.items():

    data = sums.get(com)

    if not data:
        raw_p[com] = 0
        continue

    if area_tot > 0:

        raw_p[com] = (
            data['Molto elevata P4'] * 4 +
            data['Elevata P3'] * 3 +
            data['Media P2'] * 2 +
            data['Moderata P1'] * 1
        ) / area_tot

    else:
        raw_p[com] = 0


# ============================================================
# 6. NORMALIZE THE MUNICIPAL HAZARD VALUES
# ============================================================
#
# Municipalities with no mapped hydrogeological hazard are
# assigned the value 0.01.
#
# Positive raw hazard values are normalized between 0.02 and
# 0.99, preserving their relative differences.

epsilon = 0.01
positive_min = 0.02

positive_vals = [v for v in raw_p.values() if v > 0]

norm_p = {}

if positive_vals:

    min_p = min(positive_vals)
    max_p = max(positive_vals)

    for com, p in raw_p.items():

        if p == 0:
            norm_p[com] = epsilon

        elif max_p == min_p:
            norm_p[com] = 0.99

        else:
            norm_p[com] = (
                positive_min +
                (p - min_p) / (max_p - min_p) * (0.99 - positive_min)
            )
else:

    # Assign the minimum normalized value when no municipality
    # presents a positive hydrogeological hazard value.

    for com in raw_p:
        norm_p[com] = epsilon


# ============================================================
# 7. CREATE AND POPULATE THE OUTPUT FIELD
# ============================================================
#
# Store the normalized municipal hydrogeological hazard
# indicator in the P_hydgeo field.
#
# Attribute values are written in a single batch operation to
# improve processing efficiency.

layer = hazard_layer

field_names = [f.name() for f in layer.fields()]

if 'P_hydgeo' not in field_names:
    layer.dataProvider().addAttributes([
        QgsField('P_hydgeo', QVariant.Double)
    ])
    layer.updateFields()

idx = layer.fields().indexOf('P_hydgeo')

updates = {}

for fid, feat in enumerate(layer.getFeatures()):
    com = feat['COD_ISTATN']
    updates[feat.id()] = {idx: norm_p.get(com, epsilon)}

layer.dataProvider().changeAttributeValues(updates)

layer.commitChanges()


# ============================================================
# 8. FINAL OUTPUT
# ============================================================

print("")
print("========================================")
print("Hydrogeological hazard calculation completed successfully.")
print("The normalized values were stored in the P_hydgeo field.")
print("========================================")
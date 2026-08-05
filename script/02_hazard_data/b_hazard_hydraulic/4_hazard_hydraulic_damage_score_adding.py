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
# Damage score assignment
# ============================================================
#
# Purpose
# -------
# Assign the normalized municipal hydraulic damage score by
# linking the RASDA damage database to the municipal layer.
#
# Municipalities with no recorded hydraulic damage are
# assigned the minimum normalized value (0.01), whereas
# positive damage scores are normalized within the interval
# 0.02–0.99.
#
# Input
# -----
# - Active municipal layer.
# - RASDA database containing municipal damage scores.
#
# Output
# ------
# D_hdr: normalized municipal hydraulic damage score.
#
# The original geometries are not modified.
# ============================================================


from qgis.core import QgsProject, QgsField, edit
from qgis.PyQt.QtCore import QVariant


# ============================================================
# 1. INPUT LAYERS
# ============================================================

project = QgsProject.instance()

layer = iface.activeLayer()

csv_layer = project.mapLayersByName(
    '260520_RASDA_per_comune'
)[0]


# ============================================================
# 2. AUXILIARY FUNCTION
# ============================================================
#
# Convert municipal identifiers into integer values to ensure
# a consistent match between the municipal layer and the
# RASDA database.

def clean_cod(val):
    try:
        return int(float(val))
    except:
        return None


# ============================================================
# 3. BUILD THE DAMAGE SCORE DICTIONARY
# ============================================================
#
# Extract the hydraulic damage scores from the RASDA database
# and store them using the municipal identifier as key.

csv_dict = {}

for f in csv_layer.getFeatures():

    cod = clean_cod(f['COD_ISTATN'])

    tipo = str(
        f['Tipo di evento']
    ).strip().upper()

    if cod and tipo == 'IDRAULICO':

        score = f['Score']

        if score is not None:
            csv_dict[cod] = float(score)


print(
    "Municipal codes retrieved from the RASDA database:",
    len(csv_dict)
)


# ============================================================
# 4. ASSIGN THE RAW DAMAGE SCORES
# ============================================================
#
# Municipalities without recorded hydraulic damage are
# assigned a raw damage score equal to zero.

raw_scores = {}

for f in layer.getFeatures():

    cod = clean_cod(
        f['COD_ISTATN']
    )

    raw_scores[cod] = csv_dict.get(
        cod,
        0
    )


# ============================================================
# 5. NORMALIZE THE DAMAGE SCORES
# ============================================================
#
# Positive damage scores are normalized between 0.02 and
# 0.99.
#
# Municipalities with no recorded damage retain the value
# 0.01, allowing them to be distinguished from municipalities
# with very low but non-zero damage scores.

norm_scores = {}

positive_scores = [
    v
    for v in raw_scores.values()
    if v > 0
]

if positive_scores:

    min_s = min(
        positive_scores
    )

    max_s = max(
        positive_scores
    )

    for cod, score in raw_scores.items():

        if score == 0:

            norm_scores[cod] = 0.01

        elif max_s == min_s:

            norm_scores[cod] = 0.99

        else:

            norm_scores[cod] = (
                0.02 +
                ((score - min_s) / (max_s - min_s))
                * (0.99 - 0.02)
            )

else:

    # Assign the minimum normalized value when no hydraulic
    # damage is recorded for any municipality.

    for cod in raw_scores:

        norm_scores[cod] = 0.01


print(
    "Minimum positive damage score:",
    min(positive_scores) if positive_scores else 0
)

print(
    "Maximum positive damage score:",
    max(positive_scores) if positive_scores else 0
)


# ============================================================
# 6. CREATE AND POPULATE THE OUTPUT FIELD
# ============================================================
#
# Store the normalized hydraulic damage score in the D_hdr
# field of the municipal layer.

with edit(layer):

    if 'D_hdr' not in layer.fields().names():

        layer.addAttribute(
            QgsField(
                'D_hdr',
                QVariant.Double
            )
        )

        layer.updateFields()

    idx = layer.fields().indexOf(
        'D_hdr'
    )

    for f in layer.getFeatures():

        cod = clean_cod(
            f['COD_ISTATN']
        )

        layer.changeAttributeValue(
            f.id(),
            idx,
            norm_scores.get(
                cod,
                0.01
            )
        )


# ============================================================
# 7. FINAL OUTPUT
# ============================================================

print("")
print("========================================")
print("Hydraulic damage score assignment completed successfully.")
print("The normalized values were stored in the D_hdr field.")
print("========================================")
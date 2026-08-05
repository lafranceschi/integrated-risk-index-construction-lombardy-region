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
# ADVERSE WEATHER EVENTS
#
# Damage score assignment
# ============================================================
#
# Purpose
# -------
# Assign the normalized municipal damage score associated
# with adverse weather events by linking the RASDA damage
# database to the municipal layer.
#
# Municipalities with no recorded damage are assigned the
# minimum normalized value (0.0001), whereas positive damage
# scores are normalized within the interval 0.0002–0.55.
#
# Input
# -----
# - Active municipal layer.
# - RASDA database containing municipal damage scores.
#
# Output
# ------
# D_adv_w: normalized municipal damage score associated with
# adverse weather events.
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
# Extract the damage scores associated with adverse weather
# events from the RASDA database and store them using the
# municipal identifier as key.

csv_dict = {}

for f in csv_layer.getFeatures():

    cod = clean_cod(f['COD_ISTATN'])

    tipo = str(
        f['Tipo di evento']
    ).strip().upper()

    if cod and tipo == 'FENOMENI METEO AVVERSI':

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
# Municipalities without recorded damage from adverse weather
# events are assigned a raw damage score equal to zero.

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
# Positive damage scores are normalized between 0.0002 and
# 0.55.
#
# Municipalities with no recorded damage retain the value
# 0.0001, allowing them to be distinguished from
# municipalities with very low but non-zero damage scores.

norm_scores = {}

positive_scores = [
    v
    for v in raw_scores.values()
    if v > 0
]


# Normalization interval adopted for the adverse weather
# damage component.

no_damage_value = 0.0001
min_positive = 0.0002
max_positive = 0.55


if positive_scores:

    min_s = min(
        positive_scores
    )

    max_s = max(
        positive_scores
    )

    for cod, score in raw_scores.items():

        if score == 0:

            norm_scores[cod] = no_damage_value

        elif max_s == min_s:

            norm_scores[cod] = max_positive

        else:

            norm_scores[cod] = (
                min_positive +
                ((score - min_s) / (max_s - min_s))
                * (max_positive - min_positive)
            )

else:

    # Assign the minimum normalized value when no damage from
    # adverse weather events is recorded for any municipality.

    for cod in raw_scores:

        norm_scores[cod] = no_damage_value


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
# Store the normalized adverse-weather damage score in the
# D_adv_w field of the municipal layer.

with edit(layer):

    if 'D_adv_w' not in layer.fields().names():

        layer.addAttribute(
            QgsField(
                'D_adv_w',
                QVariant.Double
            )
        )

        layer.updateFields()

    idx = layer.fields().indexOf(
        'D_adv_w'
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
                no_damage_value
            )
        )


# ============================================================
# 7. FINAL OUTPUT
# ============================================================

print("")
print("========================================")
print(
    "Adverse-weather damage score assignment completed successfully."
)
print(
    "The normalized values were stored in the D_adv_w field."
)
print(
    "Normalization interval: 0.0001–0.55."
)
print("========================================")
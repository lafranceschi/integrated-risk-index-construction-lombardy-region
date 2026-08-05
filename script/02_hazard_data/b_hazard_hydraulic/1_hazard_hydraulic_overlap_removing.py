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
# Removal of overlapping hazard polygons
# ============================================================
#
# Purpose
# -------
# Remove spatial overlaps among hydraulic hazard classes by
# applying a hierarchical priority rule.
#
# High-hazard polygons are retained unchanged. Areas assigned
# to the medium-hazard class are clipped by the high-hazard
# geometries, while low-hazard polygons are clipped by the
# combined high- and medium-hazard geometries.
#
# This procedure ensures that each portion of the study area
# is assigned exclusively to the highest applicable hazard
# class.
#
# Input
# -----
# Active QGIS polygon layer containing the hydraulic hazard
# classes stored in the CODSCENAR field.
#
# Output
# ------
# Pericolosita_no_overlap: temporary polygon layer containing
# non-overlapping hydraulic hazard classes.
#
# The input layer is not modified.
# ============================================================


from qgis.core import (
    QgsProject,
    QgsFeature,
    QgsVectorLayer,
    QgsWkbTypes
)


# ============================================================
# 1. INPUT LAYER
# ============================================================

layer = iface.activeLayer()


# ============================================================
# 2. CREATE THE OUTPUT LAYER
# ============================================================
#
# Create an in-memory layer with the same geometry type,
# coordinate reference system, and attribute structure as the
# input layer.

output = QgsVectorLayer(
    f"{QgsWkbTypes.displayString(layer.wkbType())}?crs={layer.crs().authid()}",
    "Pericolosita_no_overlap",
    "memory"
)

output.dataProvider().addAttributes(layer.fields())
output.updateFields()


# ============================================================
# 3. SEPARATE FEATURES BY HAZARD CLASS
# ============================================================
#
# Hydraulic hazard polygons are grouped according to the
# CODSCENAR classification:
#
# H = high hazard
# M = medium hazard
# L = low hazard

feat_H = []
feat_M = []
feat_L = []

for f in layer.getFeatures():

    scen = f["CODSCENAR"]

    if scen == "H":
        feat_H.append(f)

    elif scen == "M":
        feat_M.append(f)

    elif scen == "L":
        feat_L.append(f)


# ============================================================
# 4. MERGE HIGH-HAZARD GEOMETRIES
# ============================================================
#
# Build a single geometry representing the complete spatial
# extent of the high-hazard class.

geom_H = None

for f in feat_H:
    if geom_H is None:
        geom_H = f.geometry()
    else:
        geom_H = geom_H.combine(f.geometry())


# ============================================================
# 5. MERGE MEDIUM-HAZARD GEOMETRIES
# ============================================================
#
# Build a single geometry representing the complete spatial
# extent of the medium-hazard class.

geom_M = None

for f in feat_M:
    if geom_M is None:
        geom_M = f.geometry()
    else:
        geom_M = geom_M.combine(f.geometry())


# ============================================================
# 6. RETAIN HIGH-HAZARD POLYGONS
# ============================================================
#
# High-hazard polygons have the highest priority and are
# therefore copied to the output layer without modification.

output.startEditing()

for f in feat_H:
    output.addFeature(f)


# ============================================================
# 7. REMOVE HIGH-HAZARD AREAS FROM MEDIUM-HAZARD POLYGONS
# ============================================================
#
# Portions of medium-hazard polygons overlapping the
# high-hazard class are removed.

for f in feat_M:

    new_feat = QgsFeature(output.fields())
    new_feat.setAttributes(f.attributes())

    geom = f.geometry()

    if geom_H and geom.intersects(geom_H):
        geom = geom.difference(geom_H)

    if not geom.isEmpty():
        new_feat.setGeometry(geom)
        output.addFeature(new_feat)


# ============================================================
# 8. REMOVE HIGH- AND MEDIUM-HAZARD AREAS FROM LOW-HAZARD
#    POLYGONS
# ============================================================
#
# A combined geometry of the high- and medium-hazard classes
# is created and subtracted from the low-hazard polygons.

union_HM = geom_H

if geom_M:
    if union_HM:
        union_HM = union_HM.combine(geom_M)
    else:
        union_HM = geom_M

for f in feat_L:

    new_feat = QgsFeature(output.fields())
    new_feat.setAttributes(f.attributes())

    geom = f.geometry()

    if union_HM and geom.intersects(union_HM):
        geom = geom.difference(union_HM)

    if not geom.isEmpty():
        new_feat.setGeometry(geom)
        output.addFeature(new_feat)


# ============================================================
# 9. SAVE AND ADD THE OUTPUT LAYER
# ============================================================

output.commitChanges()

QgsProject.instance().addMapLayer(output)


print("")
print("========================================")
print("Hydraulic hazard overlap removal completed successfully.")
print("========================================")
"""Transient additions to a scenario; never write a design back to Urban API."""

from math import isfinite

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape


def validated_features(layer):
    if not isinstance(layer, dict) or layer.get("type") != "FeatureCollection":
        raise ValueError("A WGS84 FeatureCollection is required")
    features = layer.get("features")
    if not isinstance(features, list):
        raise ValueError("FeatureCollection.features must be a list")
    for feature in features:
        geometry = shape(feature["geometry"])
        if not geometry.is_valid or geometry.is_empty:
            raise ValueError("Variant geometry must be valid and nonempty")
        xmin, ymin, xmax, ymax = geometry.bounds
        if not (-180 <= xmin <= xmax <= 180 and -90 <= ymin <= ymax <= 90):
            raise ValueError("Variant geometry must use WGS84 longitude/latitude")
        yield geometry, feature.get("properties") or {}


def add_generated_buildings(baseline, layer):
    """Keep baseline attributes; GenBuilder excluded features carry zeroed values."""
    rows = []
    first_id = min([0, *baseline.get("building_id", [])]) - 1
    for geometry, props in validated_features(layer):
        if props.get("is_excluded"):
            continue  # Baseline buildings are retained, not replaced by these stubs.
        if props.get("zone") != "residential":
            continue
        floors = props.get("floors_count")
        if (
            isinstance(floors, bool)
            or not isinstance(floors, (int, float))
            or not isfinite(floors)
            or floors <= 0
        ):
            raise ValueError(
                "Generated residential buildings require positive floors_count"
            )
        if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
            raise ValueError("Generated buildings must be polygons")
        rows.append(
            {
                "geometry": geometry,
                "building_id": first_id - len(rows),
                "storeys_count": floors,
            }
        )
    if not rows:
        raise ValueError("No generated residential buildings in supplied variant")
    added = gpd.GeoDataFrame(rows, geometry="geometry", crs=4326)
    if baseline.empty:
        return added
    return gpd.GeoDataFrame(
        pd.concat([baseline.to_crs(4326), added], ignore_index=True), crs=4326
    )


def additional_services(layer, service_type_id, first_id=-1):
    rows = []
    for geometry, props in validated_features(layer):
        capacity = props.get("capacity")
        if (
            isinstance(capacity, bool)
            or not isinstance(capacity, (int, float))
            or not isfinite(capacity)
            or capacity <= 0
        ):
            raise ValueError("Proposed services require an explicit positive capacity")
        if props.get("service_type_id") != service_type_id:
            raise ValueError(
                "Proposed service_type_id must match its requested service group"
            )
        rows.append(
            {
                "geometry": geometry,
                "service_id": first_id - len(rows),
                "capacity": capacity,
            }
        )
    return gpd.GeoDataFrame(
        rows,
        columns=["geometry", "service_id", "capacity"],
        geometry="geometry",
        crs=4326,
    )

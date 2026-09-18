import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon, mapping

from app.provision.variant import add_generated_buildings, additional_services
from app.schemas.provision_base_schema import VariantProvisionRequestSchema


def feature(properties, geometry=None):
    return {
        "type": "Feature",
        "geometry": mapping(
            geometry or Polygon([(28, 61), (28.01, 61), (28.01, 61.01), (28, 61)])
        ),
        "properties": properties,
    }


def layer(*features):
    return {"type": "FeatureCollection", "features": list(features)}


def test_generated_layer_retains_existing_attributes_and_no_duplicate_stubs():
    baseline = gpd.GeoDataFrame(
        [{"geometry": Point(28, 61), "building_id": 10, "storeys_count": 9}], crs=4326
    )
    result = add_generated_buildings(
        baseline,
        layer(
            feature({"is_excluded": True, "physical_object_id": 10, "floors_count": 0}),
            feature({"zone": "residential", "floors_count": 5}),
            feature({"zone": "business", "floors_count": 3}),
        ),
    )
    assert len(result) == 2
    assert result.iloc[0].building_id == 10 and result.iloc[0].storeys_count == 9
    assert result.iloc[1].building_id < 0 and result.iloc[1].storeys_count == 5
    assert len(baseline) == 1
    assert result.crs.to_epsg() == 4326


@pytest.mark.parametrize("floors", [0, -1, None, True, float("nan")])
def test_missing_or_invalid_floors_are_not_invented(floors):
    baseline = gpd.GeoDataFrame(
        columns=["geometry", "building_id", "storeys_count"], crs=4326
    )
    with pytest.raises(ValueError):
        add_generated_buildings(
            baseline, layer(feature({"zone": "residential", "floors_count": floors}))
        )


def test_service_capacity_type_and_synthetic_identity():
    result = additional_services(
        layer(feature({"service_type_id": 22, "capacity": 550}, Point(28, 61))), 22, -8
    )
    assert result.iloc[0].capacity == 550
    assert result.iloc[0].service_id == -8
    with pytest.raises(ValueError):
        additional_services(
            layer(feature({"service_type_id": 21, "capacity": 550})), 22
        )
    with pytest.raises(ValueError):
        additional_services(layer(feature({"service_type_id": 22})), 22)


def test_variant_requires_total_population():
    with pytest.raises(ValueError):
        VariantProvisionRequestSchema(
            scenario_id=772, services={22: {"name": "school"}}
        )
    with pytest.raises(ValueError):
        VariantProvisionRequestSchema(
            scenario_id=772, services={22: {"name": "school"}}, target_population=0
        )

import asyncio

import pytest
from pydantic import ValidationError

from app.dto.provision_dto import NormativeOverride, NormativeProvisionDTO
from app.provision.provision_mcp import provision_mcp
from app.provision.provision_service import ProvisionService

PROJECT = {"territory": {"id": 1}, "properties": {"context": [2]}}
URBAN_NORMATIVE = {
    "services_capacity_per_1000_normative": 120,
    "capacity_type": "capacity",
    "normative_value": 15,
    "normative_type": "time",
}


class Gateway:
    def __init__(self, *, fail=False):
        self.fail = fail

    async def get_service_normative(self, **kwargs):
        if self.fail:
            raise RuntimeError("no normative for the territory")
        return dict(URBAN_NORMATIVE)


def resolve(override, *, fail=False):
    service = ProvisionService(Gateway(fail=fail))
    return asyncio.run(service._resolve_normative(PROJECT, 22, "user", override))


def test_without_override_the_urban_api_normative_is_kept():
    assert resolve(None) == URBAN_NORMATIVE


def test_norm_values_replace_the_urban_api_ones():
    normative = resolve(
        NormativeOverride(
            capacity_per_1000=124, accessibility_type="dist", accessibility_value=500
        )
    )
    assert normative["services_capacity_per_1000_normative"] == 124
    assert normative["capacity_type"] == "capacity"
    assert (normative["normative_value"], normative["normative_type"]) == (500, "dist")


def test_partial_override_keeps_the_rest():
    normative = resolve(NormativeOverride(capacity_per_1000=80))
    assert normative["services_capacity_per_1000_normative"] == 80
    assert normative["normative_value"] == 15


def test_complete_norm_does_not_need_the_urban_api_normative():
    complete = NormativeOverride(
        capacity_per_1000=124, accessibility_type="time", accessibility_value=10
    )
    assert resolve(complete, fail=True)["normative_value"] == 10
    with pytest.raises(RuntimeError):
        resolve(NormativeOverride(capacity_per_1000=124), fail=True)


def test_accessibility_value_requires_its_type():
    with pytest.raises(ValidationError):
        NormativeProvisionDTO(scenario_id=1, service_type_id=2, accessibility_value=500)


def test_tool_is_published():
    tools = asyncio.run(provision_mcp.list_tools())
    assert "CalculateNormativeProvision" in {tool.name for tool in tools}


def test_objects_per_residents_norm_counts_every_resident_as_demand():
    normative = resolve(
        NormativeOverride(
            residents_per_service=10_000,
            accessibility_type="time",
            accessibility_value=30,
        ),
        fail=True,
    )
    assert normative["capacity_type"] == "unit"
    assert normative["services_capacity_per_1000_normative"] == pytest.approx(0.1)
    assert normative["normative_value"] == 30


def test_places_and_residents_per_service_exclude_each_other():
    with pytest.raises(ValidationError):
        NormativeOverride(capacity_per_1000=10, residents_per_service=10_000)


def _houses(floors, footprints_m, living_area_official=None):
    import geopandas as gpd
    from shapely.geometry import box

    # Squares near Shlisselburg; side in degrees ~ metres / 111 km.
    rows = []
    for index, (count, side) in enumerate(zip(floors, footprints_m)):
        x, y = 31.03 + index * 0.001, 59.94
        rows.append(
            {
                "building_id": index + 1,
                "storeys_count": count,
                "living_area_official": (
                    living_area_official[index] if living_area_official else None
                ),
                "geometry": box(x, y, x + side / 55_000, y + side / 111_000),
            }
        )
    return gpd.GeoDataFrame(rows, crs=4326)


def test_indicator_far_from_the_housing_stock_is_replaced_by_its_capacity():
    from app.common.modules.data_restorator import data_restorator

    houses = _houses([5, 5], [20, 20])  # ~400 m2 footprints
    restored = data_restorator._restore_population(houses, target_population=204_314)
    info = restored.attrs["population"]
    assert info["source"] == "housing_stock"
    assert info["indicator"] == 204_314
    assert 80 <= restored["population"].sum() <= 120  # 2 x 400 x 5 x 0.8 / 33 ~ 97
    assert restored["population"].sum() == info["population"]


def test_indicator_close_to_the_housing_stock_is_kept():
    from app.common.modules.data_restorator import data_restorator

    restored = data_restorator._restore_population(
        _houses([5, 5], [20, 20]), target_population=150
    )
    assert restored.attrs["population"]["source"] == "indicator"
    assert restored["population"].sum() == 150


def test_explicit_population_always_wins_and_official_living_area_weighs_it():
    from app.common.modules.data_restorator import data_restorator

    restored = data_restorator._restore_population(
        _houses([5, 5], [20, 20], living_area_official=[3000, 1000]),
        target_population=150,
        explicit_population=10_000,
    )
    assert restored.attrs["population"]["source"] == "explicit"
    assert restored["population"].tolist() == [7500, 2500]


def test_density_parameter_scales_the_capacity():
    from app.common.modules.data_restorator import data_restorator

    houses = _houses([9], [30], living_area_official=[3300])
    restored = data_restorator._restore_population(houses, living_area_per_person=33)
    assert restored["population"].sum() == 100
    restored = data_restorator._restore_population(
        _houses([9], [30], living_area_official=[3300]), living_area_per_person=22
    )
    assert restored["population"].sum() == 150

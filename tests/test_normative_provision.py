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

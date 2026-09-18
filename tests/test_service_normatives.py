from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.common.modules.effects_api_gateway import EffectsAPIGateway


@pytest.mark.asyncio
@pytest.mark.parametrize("context_ids,requested", [([7], 7), ([], 9), ([7, 8], 9)])
async def test_empty_normatives_explain_missing_input(context_ids, requested):
    handler = AsyncMock()
    handler.get.return_value = []
    with pytest.raises(HTTPException) as error:
        await EffectsAPIGateway(handler).get_service_normative(9, context_ids, 22, "u1")
    assert error.value.status_code == 400
    assert error.value.detail["detail"]["code"] == "missing_service_normative"
    assert error.value.detail["input"]["request_ter_id"] == requested
    assert error.value.detail["detail"]["Available service ids"] == []
    assert error.value.detail["detail"]["required_action"]
    handler.get.assert_awaited_once_with(
        f"/api/v1/territory/{requested}/normatives", headers={"X-User-Id": "u1"}
    )


@pytest.mark.asyncio
async def test_latest_available_normative_is_preserved():
    handler = AsyncMock()
    handler.get.return_value = [
        {
            "service_type": {"id": 22},
            "year": year,
            "radius_availability_meters": radius,
            "time_availability_minutes": None,
            "services_per_1000_normative": None,
        }
        for year, radius in [(2020, 500), (2025, 750)]
    ]
    result = await EffectsAPIGateway(handler).get_service_normative(9, [], 22, "u1")
    assert (
        result["normative_value"],
        result["normative_type"],
        result["capacity_type"],
    ) == (750, "dist", "capacity")


@pytest.mark.asyncio
async def test_missing_service_in_nonempty_catalog_is_actionable():
    handler = AsyncMock()
    handler.get.return_value = [{"service_type": {"id": 21}, "year": 2025}]
    with pytest.raises(HTTPException) as error:
        await EffectsAPIGateway(handler).get_service_normative(9, [], 22, "u1")
    assert error.value.detail["detail"]["code"] == "missing_service_normative"
    assert error.value.detail["detail"]["Available service ids"] == [21]


@pytest.mark.asyncio
async def test_missing_normative_keeps_other_service_layers():
    import geopandas as gpd
    from shapely.geometry import Point

    from app.provision.provision_service import ProvisionService
    from app.schemas.provision_base_schema import MultiProvisionRequestSchema

    gateway = AsyncMock()
    gateway.get_project_id_by_scenario.return_value = 1
    service = ProvisionService(gateway)
    service._fetch_shared_data = AsyncMock(return_value={})
    layer = gpd.GeoDataFrame({"geometry": [Point(30, 60)]}, crs=4326)
    service._calculate_for_service = AsyncMock(
        side_effect=[
            EffectsAPIGateway._missing_service_normative(9, [], 9, 22, [21]),
            {"buildings": layer, "services": layer, "links": layer},
        ]
    )
    service._build_summary = lambda **kwargs: None
    result = await service.calculate_multi_provision(
        MultiProvisionRequestSchema(
            scenario_id=123,
            services={22: {"name": "Школа"}, 21: {"name": "Детский сад"}},
        ),
        "u1",
    )
    assert "missing_service_normative" in result.services[22].error
    assert result.services[22].layers is None
    assert result.services[21].error is None
    assert len(result.services[21].layers.buildings.features) == 1


@pytest.mark.asyncio
async def test_explicit_mock_normative_is_scoped_and_has_provenance(
    tmp_path, monkeypatch
):
    import json
    from hashlib import sha256

    fixture = tmp_path / "norms.json"
    fixture.write_text(
        json.dumps(
            {
                "id": "test-education-v1",
                "source_kind": "test_mock",
                "description": "Synthetic assessment values",
                "territory_ids": [9],
                "normatives": [
                    {
                        "service_type": {"id": 22},
                        "year": 2026,
                        "radius_availability_meters": None,
                        "time_availability_minutes": 15,
                        "services_per_1000_normative": None,
                        "services_capacity_per_1000_normative": 100,
                    }
                ],
            }
        )
    )
    monkeypatch.setenv("TEST_SERVICE_NORMATIVES_FILE", str(fixture))
    handler = AsyncMock()
    handler.get.return_value = []
    gateway = EffectsAPIGateway(handler)
    result = await gateway.get_service_normative(9, [], 22, "u1")
    assert result["normative_type"] == "time"
    assert result["normative_value"] == 15
    assert result["source"]["kind"] == "test_mock"
    assert result["source"]["sha256"] == sha256(fixture.read_bytes()).hexdigest()
    assert result["source"]["legal_compliance_claim"] is False
    with pytest.raises(HTTPException):
        await gateway.get_service_normative(10, [], 22, "u1")
    with pytest.raises(HTTPException):
        await gateway.get_service_normative(9, [], 21, "u1")
    # A configured fixture must never replace available authoritative input.
    handler.get.return_value = [
        dict(result, source={"kind": "urban_api"}, time_availability_minutes=20)
    ]
    actual = await gateway.get_service_normative(9, [], 22, "u1")
    assert actual["normative_value"] == 20
    assert actual["source"]["kind"] == "urban_api"

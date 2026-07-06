import traceback

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token
from loguru import logger

from app.dependencies import provision_mcp_service
from app.dto.provision_dto import ProvisionDTO
from app.schemas.provision_base_schema import (
    MultiProvisionRequestSchema,
    ServiceInfoSchema,
)

provision_mcp = FastMCP("Object Provision MCP server")


@provision_mcp.tool(
    name="CalculateServiceProvision",
    title="Get service provision for scenario",
    description="""
    Calculate service provision by service type id for scenario id.
    Population and demand are restored from Urban API data, then provision is evaluated
    with a gravity-based model within the service normative accessibility.

    Args to select:
    - scenario_id (int): Scenario ID from Urban API to calculate provision for.
    - service_type_id (int): Service type ID to calculate provision for.

    Returns provision layers as GeoJSON FeatureCollections in WGS84 (EPSG:4326).
    Response format:
        {
            "buildings": FeatureCollection,
            "services": FeatureCollection,
            "links": FeatureCollection
        }
    """,
)
async def calc_service_provision(scenario_id: int, service_type_id: int):

    try:
        token = get_access_token()
        project_id = await provision_mcp_service.gateway.get_project_id_by_scenario(
            scenario_id, token
        )
        provision_dto = ProvisionDTO(
            project_id=project_id,
            scenario_id=scenario_id,
            service_type_id=service_type_id,
        )
        result = await provision_mcp_service.calculate_provision(provision_dto, token)
        return result.model_dump()
    except Exception as e:
        tb = traceback.format_exc()
        logger.opt(exception=True).error(
            f"Error in MCP tool 'CalculateServiceProvision': {type(e).__name__}: {e}"
        )
        raise Exception(f"{type(e).__name__}: {e}\n\nTraceback:\n{tb}") from e


@provision_mcp.tool(
    name="CalculateServicesProvision",
    title="Get provision for multiple services",
    description="""
    Calculate service provision for several service types at once for scenario id.
    Population and demand are restored from Urban API data, then provision is evaluated
    per service type with a gravity-based model within the service normative accessibility.

    Args to select:
    - scenario_id (int): Scenario ID from Urban API to calculate provision for.
    - services (dict): Service type IDs to calculate, each with display name and layer flag:
        {"22": {"name": "Школа", "as_layer": true}, "21": {"name": "Детский сад", "as_layer": false}}
      For as_layer=true the response includes GeoJSON layers, otherwise only summary statistics.

    Returns per-service results keyed by service type id.
    Response format:
        {
            "services": {
                "22": {
                    "name": str,
                    "summary": {
                        "services_count": int,
                        "total_capacity": int,
                        "total_demand": int,
                        "satisfied_demand_within": int,
                        "satisfied_demand_without": int,
                        "unsatisfied_demand": int,
                        "average_provision_value": float,
                        "median_provision_value": float
                    },
                    "layers": {
                        "buildings": FeatureCollection,
                        "services": FeatureCollection,
                        "links": FeatureCollection
                    } | null,
                    "error": str | null
                }
            }
        }
    """,
)
async def calc_services_provision(
    scenario_id: int, services: dict[int, ServiceInfoSchema]
):

    try:
        token = get_access_token()
        multi_provision_params = MultiProvisionRequestSchema(
            scenario_id=scenario_id,
            services=services,
        )
        result = await provision_mcp_service.calculate_multi_provision(
            multi_provision_params, token
        )
        return result.model_dump()
    except Exception as e:
        tb = traceback.format_exc()
        logger.opt(exception=True).error(
            f"Error in MCP tool 'CalculateServicesProvision': {type(e).__name__}: {e}"
        )
        raise Exception(f"{type(e).__name__}: {e}\n\nTraceback:\n{tb}") from e

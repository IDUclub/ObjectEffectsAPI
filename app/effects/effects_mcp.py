import traceback

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token
from loguru import logger

from app.dependencies import effects_mcp_service
from app.dto.provision_dto import ProvisionDTO

effects_mcp = FastMCP("Object Effects MCP server")


@effects_mcp.tool(
    name="CalculateObjectEffects",
    title="Get provision effects for service",
    description="""
    Retrieve service provision effects by service id for scenario id.
    If total population is provided, demand is restored from it. Otherwise, population is restored from living square.
    
    Args to select:
    - scenario_id (int): Scenario ID from Urban API to calculate effects for.
    - service_type_id (int): Service type ID to calculate provision effects for.
    - target_population (int, optional): Total population for demand calculation. If not provided, population is restored from living square.
    
    
    Returns effects layers with estimated pivot info for llm analyses.
    Response format:
        {
            "before_prove_data": {
                "buildings": FeatureCollection,
                "services": FeatureCollection,
                "": FeatureCollection
            },
            "after_prove_data": {
                "buildings": FeatureCollection,
                "services": FeatureCollection,
                "links": FeatureCollection
            },
            "effects": FeatureCollection,
            "pivot": {
                "sum_absolute_total": int,
                "average_absolute_total": float,
                "median_absolute_total": int,
                "average_index_total": float,
                "median_index_total": int,
                "sum_absolute_within": int,
                "average_absolute_within": float,
                "median_absolute_within": int,
            },
            "": str
        }
    """,
)
async def calc_provision_effects(
    scenario_id: int, service_type_id: int, target_population: int | None = None
):

    try:
        token = get_access_token()
        project_id = await effects_mcp_service.gateway.get_project_id_by_scenario(
            scenario_id, token
        )
        effects_dto = ProvisionDTO(
            project_id=project_id,
            scenario_id=scenario_id,
            service_type_id=service_type_id,
            target_population=target_population,
        )
        result = await effects_mcp_service.calculate_effects(
            effects_dto, token, for_mcp=True
        )
        return result
    except Exception as e:
        tb = traceback.format_exc()
        logger.opt(exception=True).error(
            f"Error in MCP tool 'CalculateObjectEffects': {type(e).__name__}: {e}"
        )
        raise Exception(f"{type(e).__name__}: {e}\n\nTraceback:\n{tb}") from e

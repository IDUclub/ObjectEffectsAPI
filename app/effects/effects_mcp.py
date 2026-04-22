from fastmcp import FastMCP
from fastmcp.server.dependencies import CurrentContext, get_access_token

from app.dto.provision_dto import ProvisionDTO

from .effects_service import effects_service

effects_mcp = FastMCP("Object Effects MCP server")


@effects_mcp.tool(
    name="CalculateObjectEffects",
    title="Get provision effects for service",
    description="""
    Retrieve service provision effects by service id.
    If total population is provided, demand is restored from it. Otherwise, population is restored from living square.
    
    Args to select: 
    
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
    service_type_id: int, target_population: int | None = None, ctx=CurrentContext()
):

    project_id = int(ctx.request_context.meta.project_id)
    scenario_id = int(ctx.request_context.meta.scenario_id)
    token = get_access_token()
    effects_dto = ProvisionDTO(
        project_id=project_id,
        scenario_id=scenario_id,
        service_type_id=service_type_id,
        target_population=target_population,
    )
    result = await effects_service.calculate_effects(effects_dto, token, for_mcp=True)
    return result

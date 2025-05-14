import json
import asyncio

import geopandas as gpd
import pandas as pd
from loguru import logger

from app.dependencies import http_exception
from .dto.effects_dto import EffectsDTO
from .modules import (
    effects_api_gateway,
    data_restorator,
    attribute_parser,
    matrix_builder, objectnat_calculator
)


class EffectsService:
    """
    Class for handling services calculation
    """

    @staticmethod
    async def _get_pivot(
            effects: pd.DataFrame | gpd.GeoDataFrame,
    ) -> dict[str, int | float]:
        """
        Function creates a pivot table for effects data
        Args:
            effects (pd.DataFrame | gpd.GeoDataFrame): effects data
        Returns:
            dict[str, int | float]: pivot table for effects data
        """

        result = {
            "sum_absolute_total": int(effects["absolute_total"].sum()),
            "average_absolute_total": effects["absolute_total"].mean(),
            "median_absolute_total": int(effects["absolute_total"].median()),
            "average_index_total": effects["index_total"].mean(),
            "median_index_total": int(effects["index_total"].median()),
            "sum_absolute_within": int(effects["absolute_within"].sum()),
            "average_absolute_within": effects["absolute_within"].mean(),
            "median_absolute_within": int(effects["absolute_within"].median()),
        }

        if effects[effects["is_project"]].empty:
            return result
        result["median_index_scenario_project"] = int(effects[effects["is_project"]]["index_scenario_project"].median())
        result["average_index_scenario_project"] = effects[effects["is_project"]]["index_scenario_project"].mean()
        result["sum_absolute_scenario_project"] = int(
            effects[effects["is_project"]]["absolute_scenario_project"].sum()
        )
        result["median_absolute_scenario_project"] = int(
            effects[effects["is_project"]]["absolute_scenario_project"].median()
        )
        result["average_absolute_scenario_project"] = effects[effects["is_project"]]["absolute_scenario_project"].mean()
        result["median_absolute_scenario_project"] = int(
            effects[effects["is_project"]]["absolute_scenario_project"].median()
        )
        result["average_index_scenario_project"] = effects[effects["is_project"]]["index_scenario_project"].mean()
        result["median_index_scenario_project"] = int(effects[effects["is_project"]]["index_scenario_project"].median())
        return result

    # ToDo Split function
    # ToDo Rewrite to context ids normal handling
    async def calculate_effects(
            self,
            effects_params: EffectsDTO
    ) -> dict[str, dict]:
        """
        Calculate provision effects by project data and target scenario
        Args:
            effects_params (EffectsDTO): Project data
        Returns:
             gpd.GeoDataFrame: Provision effects
        """

        logger.info(
            f"Started calculating effects for {effects_params.scenario_id} and service{effects_params.service_type_id}"
        )
        project_data = await effects_api_gateway.get_project_data(
            effects_params.project_id
        )
        project_territory = await effects_api_gateway.get_project_territory(effects_params.project_id)
        normative_data = await effects_api_gateway.get_service_normative(
            territory_id=project_data["territory"]["id"],
            service_type_id=effects_params.service_type_id,
            year=effects_params.year,
        )
        context_population = await effects_api_gateway.get_context_population(
            territory_ids_list=project_data["properties"]["context"]
        )
        context_buildings = await effects_api_gateway.get_project_context_buildings(
            project_id=effects_params.project_id,
        )
        context_buildings.drop(index=context_buildings.sjoin(project_territory).index, inplace=True)
        context_buildings = await attribute_parser.parse_all_from_buildings(
            living_buildings=context_buildings,
        )
        context_buildings = await asyncio.to_thread(
            data_restorator.restore_demands,
            buildings=context_buildings,
            service_normative=normative_data["services_capacity_per_1000_normative"],
            service_normative_type=normative_data["capacity_type"],
            target_population=context_population,
        )
        context_buildings["is_project"] = False
        context_services = await effects_api_gateway.get_project_context_services(
            project_id=effects_params.project_id,
            service_type_id=effects_params.service_type_id,
        )
        if context_services.empty:
            raise http_exception(
                status_code=404,
                msg="No services of {service_type_id} type found in context",
                _input={"service_type_id": effects_params.service_type_id},
                _detail={}
            )
        context_services = await attribute_parser.parse_all_from_services(
            services=context_services,
        )
        target_scenario_population = await effects_api_gateway.get_scenario_population_data(
            scenario_id=effects_params.scenario_id,
        )
        target_scenario_buildings = await effects_api_gateway.get_scenario_buildings(
            scenario_id=effects_params.scenario_id
        )
        target_scenario_buildings = await attribute_parser.parse_all_from_buildings(
            living_buildings=target_scenario_buildings,
        )
        target_scenario_buildings = await asyncio.to_thread(
            data_restorator.restore_demands,
            buildings=target_scenario_buildings,
            service_normative=normative_data["services_capacity_per_1000_normative"],
            service_normative_type=normative_data["capacity_type"],
            target_population=target_scenario_population,
        )
        target_scenario_buildings["is_project"] = True
        target_scenario_services = await effects_api_gateway.get_scenario_services(
            scenario_id=effects_params.scenario_id,
            service_type_id=effects_params.service_type_id,
        )
        target_scenario_services = await attribute_parser.parse_all_from_services(
            services=target_scenario_services,
        )
        base_scenario_buildings = await effects_api_gateway.get_scenario_buildings(
            scenario_id=project_data["base_scenario"]["id"]
        )
        base_scenario_buildings = await attribute_parser.parse_all_from_buildings(
            living_buildings=base_scenario_buildings,
        )
        base_scenario_buildings = await asyncio.to_thread(
            data_restorator.restore_demands,
            buildings=base_scenario_buildings,
            service_normative=normative_data["services_capacity_per_1000_normative"],
            service_normative_type=normative_data["capacity_type"],
        )
        base_scenario_buildings["is_project"] = True
        base_scenario_services = await effects_api_gateway.get_scenario_services(
            scenario_id=project_data["base_scenario"]["id"],
            service_type_id=effects_params.service_type_id,
        )
        base_scenario_services = await attribute_parser.parse_all_from_services(
            services=base_scenario_services,
        )
        after_buildings = await asyncio.to_thread(
            pd.concat,
            objs=[context_buildings, target_scenario_buildings]
        )
        after_services = await asyncio.to_thread(
            pd.concat,
            objs=[context_services, target_scenario_services]
        )
        before_buildings = await  asyncio.to_thread(
            pd.concat,
            objs=[context_buildings, base_scenario_buildings],
        )
        before_services = await asyncio.to_thread(
            pd.concat,
            objs=[context_services, base_scenario_services]
        )
        after_buildings.sort_values("is_project", ascending=False, inplace=True)
        after_buildings.drop_duplicates("building_id", keep="first", inplace=True)
        after_buildings.set_index("building_id", inplace=True)
        after_services.set_index("service_id", inplace=True)
        before_buildings.sort_values("is_project", ascending=False, inplace=True)
        before_buildings.drop_duplicates("building_id", keep="first", inplace=True)
        before_buildings.set_index("building_id", inplace=True)
        before_services.set_index("service_id", inplace=True)
        before_services.drop_duplicates("geometry", inplace=True)
        if target_scenario_buildings.empty:
            local_crs = context_buildings.estimate_utm_crs()
        else:
            local_crs = target_scenario_buildings.estimate_utm_crs()
        before_buildings.to_crs(local_crs, inplace=True)
        before_services.to_crs(local_crs, inplace=True)
        after_buildings.to_crs(local_crs, inplace=True)
        after_services.to_crs(local_crs, inplace=True)
        #ToDo context - project objects relation should be revised
        after_services.drop_duplicates("geometry", inplace=True)
        before_matrix = await asyncio.to_thread(
            matrix_builder.calculate_availability_matrix,
            buildings=before_buildings,
            services=before_services,
            normative_value=normative_data["normative_value"],
            normative_type=normative_data["normative_type"],
        )
        after_matrix = await asyncio.to_thread(
            matrix_builder.calculate_availability_matrix,
            buildings=after_buildings,
            services=after_services,
            normative_value=normative_data["normative_value"],
            normative_type=normative_data["normative_type"],
        )
        before_prove_data = await asyncio.to_thread(
            objectnat_calculator.evaluate_provision,
            buildings=before_buildings,
            services=before_services,
            matrix=before_matrix,
            service_normative=normative_data["normative_value"],
        )
        after_prove_data = await asyncio.to_thread(
            objectnat_calculator.evaluate_provision,
            buildings=after_buildings,
            services=after_services,
            matrix=after_matrix,
            service_normative=normative_data["normative_value"],
        )
        effects = await asyncio.to_thread(
            objectnat_calculator.estimate_effects,
            provision_before=before_prove_data["buildings"],
            provision_after=after_prove_data["buildings"],
        )
        logger.info(
            f"Calculated effects for {effects_params.scenario_id} and service type {effects_params.service_type_id}"
        )
        pivot = await self._get_pivot(effects)

        result = {
            "before_prove_data": {
                "buildings": json.loads(
                    before_prove_data["buildings"].to_crs(4326).to_json()
                ),
                "services": json.loads(
                    before_prove_data["services"].to_crs(4326).to_json()
                ),
                "links": json.loads(before_prove_data["links"].to_crs(4326).to_json()),
            },
            "after_prove_data": {
                "buildings": json.loads(
                    after_prove_data["buildings"].to_crs(4326).to_json()
                ),
                "services": json.loads(after_prove_data["services"].to_crs(4326).to_json()),
                "links": json.loads(after_prove_data["links"].to_crs(4326).to_json()),
            },
            "effects": json.loads(effects.to_crs(4326).to_json()),
            "pivot": pivot,
        }
        return result


effects_service = EffectsService()

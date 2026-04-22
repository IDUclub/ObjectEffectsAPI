import asyncio
import json

import geopandas as gpd
import pandas as pd
from loguru import logger

from app.common.exceptions.http_exception_wrapper import http_exception
from app.common.modules import (
    ATTRIBUTES_MAP,
    BUILDINGS_DROP_COLUMNS,
    EFFECTS_MAP,
    SERVICE_DROP_COLUMNS,
    attribute_parser,
    data_restorator,
    effects_api_gateway,
    matrix_builder,
    objectnat_calculator,
)
from app.dto.provision_dto import ProvisionDTO

from .shemas.effects_base_schema import EffectsSchema


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
        result["median_index_scenario_project"] = int(
            effects[effects["is_project"]]["index_scenario_project"].median()
        )
        result["average_index_scenario_project"] = effects[effects["is_project"]][
            "index_scenario_project"
        ].mean()
        result["sum_absolute_scenario_project"] = int(
            effects[effects["is_project"]]["absolute_scenario_project"].sum()
        )
        result["median_absolute_scenario_project"] = int(
            effects[effects["is_project"]]["absolute_scenario_project"].median()
        )
        result["average_absolute_scenario_project"] = effects[effects["is_project"]][
            "absolute_scenario_project"
        ].mean()
        result["median_absolute_scenario_project"] = int(
            effects[effects["is_project"]]["absolute_scenario_project"].median()
        )
        result["average_index_scenario_project"] = effects[effects["is_project"]][
            "index_scenario_project"
        ].mean()
        result["median_index_scenario_project"] = int(
            effects[effects["is_project"]]["index_scenario_project"].median()
        )
        return result

    # ToDo Add population retrievement by year
    # ToDo Split function
    # ToDo Rewrite to context ids normal handling
    async def calculate_effects(
        self, effects_params: ProvisionDTO, token: str, for_mcp: bool = False
    ) -> EffectsSchema:
        """
        Calculate provision effects by project data and target scenario
        Args:
            effects_params (ProvisionDTO): Project data
            token (str): Authorization token
            for_mcp (bool): If flag enabled adds string description for llm. Default to false.
        Returns:
             gpd.GeoDataFrame: Provision effects
        """

        logger.info(
            f"Started calculating effects for {effects_params.scenario_id} and service{effects_params.service_type_id}"
        )
        project_data = await effects_api_gateway.get_project_data(
            effects_params.project_id, token
        )
        project_territory = await effects_api_gateway.get_project_territory(
            effects_params.project_id, token
        )
        service_default_capacity = await effects_api_gateway.get_default_capacity(
            service_type_id=effects_params.service_type_id
        )
        normative_data = await effects_api_gateway.get_service_normative(
            territory_id=project_data["territory"]["id"],
            context_ids=project_data["properties"]["context"],
            service_type_id=effects_params.service_type_id,
            token=token,
        )
        context_population = await effects_api_gateway.get_context_population(
            territory_ids_list=project_data["properties"]["context"], token=token
        )
        context_buildings = await effects_api_gateway.get_project_context_buildings(
            scenario_id=project_data["base_scenario"]["id"], token=token
        )
        context_buildings.drop(
            index=context_buildings.sjoin(project_territory).index, inplace=True
        )
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
            scenario_id=project_data["base_scenario"]["id"],
            service_type_id=effects_params.service_type_id,
            token=token,
        )
        if context_services.empty:
            # ToDo Revise to another code
            raise http_exception(
                status_code=404,
                msg="No services of {service_type_id} type found in context",
                _input={"service_type_id": effects_params.service_type_id},
                _detail={},
            )
        context_services = await attribute_parser.parse_all_from_services(
            services=context_services, service_default_capacity=service_default_capacity
        )
        target_scenario_population = (
            await effects_api_gateway.get_scenario_population_data(
                scenario_id=effects_params.scenario_id, token=token
            )
        )
        target_scenario_buildings = await effects_api_gateway.get_scenario_buildings(
            scenario_id=effects_params.scenario_id, token=token
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
            token=token,
        )
        target_scenario_services = await attribute_parser.parse_all_from_services(
            services=target_scenario_services,
            service_default_capacity=service_default_capacity,
        )
        base_scenario_buildings = await effects_api_gateway.get_scenario_buildings(
            scenario_id=project_data["base_scenario"]["id"], token=token
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
            token=token,
        )
        base_scenario_services = await attribute_parser.parse_all_from_services(
            services=base_scenario_services,
            service_default_capacity=service_default_capacity,
        )
        after_buildings = await asyncio.to_thread(
            pd.concat, objs=[context_buildings, target_scenario_buildings]
        )
        after_services = await asyncio.to_thread(
            pd.concat, objs=[context_services, target_scenario_services]
        )
        before_buildings = await asyncio.to_thread(
            pd.concat,
            objs=[context_buildings, base_scenario_buildings],
        )
        before_services = await asyncio.to_thread(
            pd.concat, objs=[context_services, base_scenario_services]
        )
        after_buildings.sort_values("is_project", ascending=False, inplace=True)
        after_buildings.drop_duplicates("building_id", keep="first", inplace=True)
        after_buildings.set_index("building_id", inplace=True)
        after_services.set_index("service_id", inplace=True)
        after_services = after_services[
            ~after_services.index.duplicated(keep="first")
        ].copy()
        before_buildings.sort_values("is_project", ascending=False, inplace=True)
        before_buildings.drop_duplicates("building_id", keep="first", inplace=True)
        before_buildings.set_index("building_id", inplace=True)
        before_services.set_index("service_id", inplace=True)
        before_services.drop_duplicates("geometry", inplace=True)
        before_services = before_services[
            ~before_services.index.duplicated(keep="first")
        ].copy()
        if target_scenario_buildings.empty:
            local_crs = context_buildings.estimate_utm_crs()
        else:
            local_crs = target_scenario_buildings.estimate_utm_crs()
        before_buildings.to_crs(local_crs, inplace=True)
        before_services.to_crs(local_crs, inplace=True)
        after_buildings.to_crs(local_crs, inplace=True)
        after_services.to_crs(local_crs, inplace=True)
        # ToDo context - project objects relation should be revised
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
        before_services["capacity"] = before_services["capacity"].fillna(
            before_services["capacity"].mean()
        )
        before_prove_data = await asyncio.to_thread(
            objectnat_calculator.evaluate_provision,
            buildings=before_buildings,
            services=before_services[~before_services.index.duplicated(keep="first")],
            matrix=before_matrix,
            service_normative=normative_data["normative_value"],
        )
        after_prove_data = await asyncio.to_thread(
            objectnat_calculator.evaluate_provision,
            buildings=after_buildings,
            services=after_services[~after_services.index.duplicated(keep="first")],
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
                    before_prove_data["buildings"]
                    .rename(
                        columns={
                            k: v
                            for k, v in ATTRIBUTES_MAP.items()
                            if k in before_prove_data["buildings"].columns
                        }
                    )
                    .drop(columns=BUILDINGS_DROP_COLUMNS)
                    .to_crs(4326)
                    .to_json()
                ),
                "services": json.loads(
                    before_prove_data["services"]
                    .rename(
                        columns={
                            k: v
                            for k, v in ATTRIBUTES_MAP.items()
                            if k in before_prove_data["services"].columns
                        }
                    )
                    .drop(columns=SERVICE_DROP_COLUMNS)
                    .to_crs(4326)
                    .to_json()
                ),
                "links": json.loads(
                    before_prove_data["links"]
                    .rename(
                        columns={
                            k: v
                            for k, v in ATTRIBUTES_MAP.items()
                            if k in before_prove_data["links"].columns
                        }
                    )
                    .to_crs(4326)
                    .to_json()
                ),
            },
            "after_prove_data": {
                "buildings": json.loads(
                    after_prove_data["buildings"]
                    .rename(
                        columns={
                            k: v
                            for k, v in ATTRIBUTES_MAP.items()
                            if k in after_prove_data["buildings"].columns
                        }
                    )
                    .drop(columns=BUILDINGS_DROP_COLUMNS)
                    .to_crs(4326)
                    .to_json()
                ),
                "services": json.loads(
                    after_prove_data["services"]
                    .rename(
                        columns={
                            k: v
                            for k, v in ATTRIBUTES_MAP.items()
                            if k in after_prove_data["services"].columns
                        }
                    )
                    .drop(columns=SERVICE_DROP_COLUMNS)
                    .to_crs(4326)
                    .to_json()
                ),
                "links": json.loads(
                    after_prove_data["links"]
                    .rename(
                        columns={
                            k: v
                            for k, v in ATTRIBUTES_MAP.items()
                            if k in after_prove_data["links"].columns
                        }
                    )
                    .to_crs(4326)
                    .to_json()
                ),
            },
            "effects": json.loads(
                effects.rename(columns=EFFECTS_MAP).to_crs(4326).to_json()
            ),
            "pivot": pivot,
        }
        if for_mcp:
            result["text_pivot"] = await self.form_llm_context(
                before_prove_data["buildings"],
                after_prove_data["buildings"],
                before_prove_data["services"],
                after_prove_data["services"],
            )
        return EffectsSchema(**result)

    @staticmethod
    async def form_llm_context(
        before_buildings: gpd.GeoDataFrame,
        after_buildings: gpd.GeoDataFrame,
        before_services: gpd.GeoDataFrame,
        after_services: gpd.GeoDataFrame,
    ) -> str:
        """
        Function forms text repr stats from calculated provision data for llm.
        Args:
            before_buildings (gpd.GeoDataFrame): Buildings provision layers before.
            after_buildings (gpd.GeoDataFrame): Buildings provision layers after.
            before_services (gpd.GeoDataFrame): Services provision layers before.
            after_services (gpd.GeoDataFrame): Services provision layers after.
        Returns:
            str: Text representation for formed stats in json string.
        """

        before_buildings_all = before_buildings.copy()
        after_buildings_all = after_buildings.copy()
        before_services_all = before_services.copy()
        after_services_all = after_services.copy()
        before_buildings_context = before_buildings[
            before_buildings["is_scenario_object"] == False
        ]
        after_buildings_context = after_buildings[
            after_buildings["is_scenario_object"] == False
        ]
        before_services_context = before_services[
            before_services["is_scenario_object"] == False
        ]
        after_services_context = after_services[
            after_services["is_scenario_object"] == False
        ]
        before_buildings_project = before_buildings[
            before_buildings["is_scenario_object"] == True
        ]
        after_buildings_project = after_buildings[
            after_buildings["is_scenario_object"] == True
        ]
        before_services_project = before_services[
            before_services["is_scenario_object"] == True
        ]
        after_services_project = after_services[
            after_services["is_scenario_object"] == True
        ]
        all_provision_before = int(
            before_buildings_all[
                "Удовлетворённый спрос вне нормативной доступности (до) (чел)"
            ].sum()
        )
        all_provision_after = int(
            after_buildings_all[
                "Удовлетворённый спрос вне нормативной доступности (после) (чел)"
            ].sum()
        )
        all_provision_within_before = int(
            before_buildings_all[
                "Удовлетворённый спрос в нормативной доступности (до) (чел)"
            ].sum()
        )
        all_provision_within_after = int(
            after_buildings_all[
                "Удовлетворённый спрос в нормативной доступности (после) (чел)"
            ].sum()
        )
        all_provision_without_before = int(
            before_buildings_all[
                "Удовлетворённый спрос вне нормативной доступности (до) (чел)"
            ].sum()
        )
        all_provision_without_after = int(
            after_buildings_all[
                "Удовлетворённый спрос вне нормативной доступности (после) (чел)"
            ].sum()
        )
        all_total_capacity_before = int(before_services_all["Вместимость (чел)"].sum())
        all_total_capacity_after = int(after_services_all["Вместимость (чел)"].sum())
        all_demand_before = int(before_buildings_all["Спрос (чел)"].sum())
        all_demand_after = int(after_buildings_all["Спрос (чел)"].sum())
        all_unmet_demand_before = int(
            before_buildings_all["Неудовлетворённый спрос (чел)"].sum()
        )
        all_unmet_demand_after = int(
            after_buildings_all["Неудовлетворённый спрос (чел)"].sum()
        )
        all_unmet_demand_within_before = int(
            before_buildings_all[
                "Неудовлетворённый спрос в нормативной доступности (до) (чел)"
            ].sum()
        )
        all_unmet_demand_within_after = int(
            after_buildings_all[
                "Неудовлетворённый спрос в нормативной доступности (после) (чел)"
            ].sum()
        )
        all_unmet_demand_without_before = int(
            before_buildings_all[
                "Неудовлетворённый спрос вне нормативной доступности (до) (чел)"
            ].sum()
        )
        all_unmet_demand_without_after = int(
            after_buildings_all[
                "Неудовлетворённый спрос вне нормативной доступности (после) (чел)"
            ].sum()
        )
        all_balance_before = all_total_capacity_before - all_demand_before
        all_balance_after = all_total_capacity_after - all_demand_after
        all_deficit_before = min(0, all_balance_before)
        all_deficit_after = min(0, all_balance_after)
        all_surplus_before = max(0, all_balance_before)
        all_surplus_after = max(0, all_balance_after)
        context_provision_before = int(
            before_buildings_context[
                "Удовлетворённый спрос вне нормативной доступности (до) (чел)"
            ].sum()
        )
        context_provision_after = int(
            after_buildings_context[
                "Удовлетворённый спрос вне нормативной доступности (после) (чел)"
            ].sum()
        )
        context_provision_within_before = int(
            before_buildings_context[
                "Удовлетворённый спрос в нормативной доступности (до) (чел)"
            ].sum()
        )
        context_provision_within_after = int(
            after_buildings_context[
                "Удовлетворённый спрос в нормативной доступности (после) (чел)"
            ].sum()
        )
        context_provision_without_before = int(
            before_buildings_context[
                "Удовлетворённый спрос вне нормативной доступности (до) (чел)"
            ].sum()
        )
        context_provision_without_after = int(
            after_buildings_context[
                "Удовлетворённый спрос вне нормативной доступности (после) (чел)"
            ].sum()
        )
        context_total_capacity_before = int(
            before_services_context["Вместимость (чел)"].sum()
        )
        context_total_capacity_after = int(
            after_services_context["Вместимость (чел)"].sum()
        )
        context_demand_before = int(before_buildings_context["Спрос (чел)"].sum())
        context_demand_after = int(after_buildings_context["Спрос (чел)"].sum())
        context_unmet_demand_before = int(
            before_buildings_context["Неудовлетворённый спрос (чел)"].sum()
        )
        context_unmet_demand_after = int(
            after_buildings_context["Неудовлетворённый спрос (чел)"].sum()
        )
        context_unmet_demand_within_before = int(
            before_buildings_context[
                "Неудовлетворённый спрос в нормативной доступности (до) (чел)"
            ].sum()
        )
        context_unmet_demand_within_after = int(
            after_buildings_context[
                "Неудовлетворённый спрос в нормативной доступности (после) (чел)"
            ].sum()
        )
        context_unmet_demand_without_before = int(
            before_buildings_context[
                "Неудовлетворённый спрос вне нормативной доступности (до) (чел)"
            ].sum()
        )
        context_unmet_demand_without_after = int(
            after_buildings_context[
                "Неудовлетворённый спрос вне нормативной доступности (после) (чел)"
            ].sum()
        )
        context_balance_before = context_total_capacity_before - context_demand_before
        context_balance_after = context_total_capacity_after - context_demand_after
        context_deficit_before = min(0, context_balance_before)
        context_deficit_after = min(0, context_balance_after)
        context_surplus_before = max(0, context_balance_before)
        context_surplus_after = max(0, context_balance_after)
        project_provision_before = int(
            before_buildings_project[
                "Удовлетворённый спрос вне нормативной доступности (до) (чел)"
            ].sum()
        )
        project_provision_after = int(
            after_buildings_project[
                "Удовлетворённый спрос вне нормативной доступности (после) (чел)"
            ].sum()
        )
        project_provision_within_before = int(
            before_buildings_project[
                "Удовлетворённый спрос в нормативной доступности (до) (чел)"
            ].sum()
        )
        project_provision_within_after = int(
            after_buildings_project[
                "Удовлетворённый спрос в нормативной доступности (после) (чел)"
            ].sum()
        )
        project_provision_without_before = int(
            before_buildings_project[
                "Удовлетворённый спрос вне нормативной доступности (до) (чел)"
            ].sum()
        )
        project_provision_without_after = int(
            after_buildings_project[
                "Удовлетворённый спрос вне нормативной доступности (после) (чел)"
            ].sum()
        )
        project_total_capacity_before = int(
            before_services_project["Вместимость (чел)"].sum()
        )
        project_total_capacity_after = int(
            after_services_project["Вместимость (чел)"].sum()
        )
        project_demand_before = int(before_buildings_project["Спрос (чел)"].sum())
        project_demand_after = int(after_buildings_project["Спрос (чел)"].sum())
        project_unmet_demand_before = int(
            before_buildings_project["Неудовлетворённый спрос (чел)"].sum()
        )
        project_unmet_demand_after = int(
            after_buildings_project["Неудовлетворённый спрос (чел)"].sum()
        )
        project_unmet_demand_within_before = int(
            before_buildings_project[
                "Неудовлетворённый спрос в нормативной доступности (до) (чел)"
            ].sum()
        )
        project_unmet_demand_within_after = int(
            after_buildings_project[
                "Неудовлетворённый спрос в нормативной доступности (после) (чел)"
            ].sum()
        )
        project_unmet_demand_without_before = int(
            before_buildings_project[
                "Неудовлетворённый спрос вне нормативной доступности (до) (чел)"
            ].sum()
        )
        project_unmet_demand_without_after = int(
            after_buildings_project[
                "Неудовлетворённый спрос вне нормативной доступности (после) (чел)"
            ].sum()
        )
        project_balance_before = project_total_capacity_before - project_demand_before
        project_balance_after = project_total_capacity_after - project_demand_after
        project_deficit_before = min(0, project_balance_before)
        project_deficit_after = min(0, project_balance_after)
        project_surplus_before = max(0, project_balance_before)
        project_surplus_after = max(0, project_balance_after)

        result = {
            "all": {
                "provision_before": all_provision_before,
                "provision_after": all_provision_after,
                "provision_delta": all_provision_after - all_provision_before,
                "provision_within_before": all_provision_within_before,
                "provision_within_after": all_provision_within_after,
                "provision_within_delta": all_provision_within_after
                - all_provision_within_before,
                "provision_without_before": all_provision_without_before,
                "provision_without_after": all_provision_without_after,
                "provision_without_delta": all_provision_without_after
                - all_provision_without_before,
                "total_capacity_before": all_total_capacity_before,
                "total_capacity_after": all_total_capacity_after,
                "total_capacity_delta": all_total_capacity_after
                - all_total_capacity_before,
                "balance_before": all_balance_before,
                "balance_after": all_balance_after,
                "balance_delta": all_balance_after - all_balance_before,
                "deficit_before": all_deficit_before,
                "deficit_after": all_deficit_after,
                "deficit_delta": all_deficit_after - all_deficit_before,
                "surplus_before": all_surplus_before,
                "surplus_after": all_surplus_after,
                "surplus_delta": all_surplus_after - all_surplus_before,
                "demand_before": all_demand_before,
                "demand_after": all_demand_after,
                "demand_delta": all_demand_after - all_demand_before,
                "unmet_demand_before": all_unmet_demand_before,
                "unmet_demand_after": all_unmet_demand_after,
                "unmet_demand_delta": all_unmet_demand_after - all_unmet_demand_before,
                "unmet_demand_within_before": all_unmet_demand_within_before,
                "unmet_demand_within_after": all_unmet_demand_within_after,
                "unmet_demand_within_delta": all_unmet_demand_within_after
                - all_unmet_demand_within_before,
                "unmet_demand_without_before": all_unmet_demand_without_before,
                "unmet_demand_without_after": all_unmet_demand_without_after,
                "unmet_demand_without_delta": all_unmet_demand_without_after
                - all_unmet_demand_without_before,
            },
            "context": {
                "provision_before": context_provision_before,
                "provision_after": context_provision_after,
                "provision_delta": context_provision_after - context_provision_before,
                "provision_within_before": context_provision_within_before,
                "provision_within_after": context_provision_within_after,
                "provision_within_delta": context_provision_within_after
                - context_provision_within_before,
                "provision_without_before": context_provision_without_before,
                "provision_without_after": context_provision_without_after,
                "provision_without_delta": context_provision_without_after
                - context_provision_without_before,
                "total_capacity_before": context_total_capacity_before,
                "total_capacity_after": context_total_capacity_after,
                "total_capacity_delta": context_total_capacity_after
                - context_total_capacity_before,
                "balance_before": context_balance_before,
                "balance_after": context_balance_after,
                "balance_delta": context_balance_after - context_balance_before,
                "deficit_before": context_deficit_before,
                "deficit_after": context_deficit_after,
                "deficit_delta": context_deficit_after - context_deficit_before,
                "surplus_before": context_surplus_before,
                "surplus_after": context_surplus_after,
                "surplus_delta": context_surplus_after - context_surplus_before,
                "demand_before": context_demand_before,
                "demand_after": context_demand_after,
                "demand_delta": context_demand_after - context_demand_before,
                "unmet_demand_before": context_unmet_demand_before,
                "unmet_demand_after": context_unmet_demand_after,
                "unmet_demand_delta": context_unmet_demand_after
                - context_unmet_demand_before,
                "unmet_demand_within_before": context_unmet_demand_within_before,
                "unmet_demand_within_after": context_unmet_demand_within_after,
                "unmet_demand_within_delta": context_unmet_demand_within_after
                - context_unmet_demand_within_before,
                "unmet_demand_without_before": context_unmet_demand_without_before,
                "unmet_demand_without_after": context_unmet_demand_without_after,
                "unmet_demand_without_delta": context_unmet_demand_without_after
                - context_unmet_demand_without_before,
            },
            "project": {
                "provision_before": project_provision_before,
                "provision_after": project_provision_after,
                "provision_delta": project_provision_after - project_provision_before,
                "provision_within_before": project_provision_within_before,
                "provision_within_after": project_provision_within_after,
                "provision_within_delta": project_provision_within_after
                - project_provision_within_before,
                "provision_without_before": project_provision_without_before,
                "provision_without_after": project_provision_without_after,
                "provision_without_delta": project_provision_without_after
                - project_provision_without_before,
                "total_capacity_before": project_total_capacity_before,
                "total_capacity_after": project_total_capacity_after,
                "total_capacity_delta": project_total_capacity_after
                - project_total_capacity_before,
                "balance_before": project_balance_before,
                "balance_after": project_balance_after,
                "balance_delta": project_balance_after - project_balance_before,
                "deficit_before": project_deficit_before,
                "deficit_after": project_deficit_after,
                "deficit_delta": project_deficit_after - project_deficit_before,
                "surplus_before": project_surplus_before,
                "surplus_after": project_surplus_after,
                "surplus_delta": project_surplus_after - project_surplus_before,
                "demand_before": project_demand_before,
                "demand_after": project_demand_after,
                "demand_delta": project_demand_after - project_demand_before,
                "unmet_demand_before": project_unmet_demand_before,
                "unmet_demand_after": project_unmet_demand_after,
                "unmet_demand_delta": project_unmet_demand_after
                - project_unmet_demand_before,
                "unmet_demand_within_before": project_unmet_demand_within_before,
                "unmet_demand_within_after": project_unmet_demand_within_after,
                "unmet_demand_within_delta": project_unmet_demand_within_after
                - project_unmet_demand_within_before,
                "unmet_demand_without_before": project_unmet_demand_without_before,
                "unmet_demand_without_after": project_unmet_demand_without_after,
                "unmet_demand_without_delta": project_unmet_demand_without_after
                - project_unmet_demand_without_before,
            },
        }
        return json.dumps(result)


effects_service = EffectsService()

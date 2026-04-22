import asyncio
import json

import pandas as pd
from loguru import logger

from app.common.exceptions.http_exception_wrapper import http_exception
from app.common.modules import (
    attribute_parser,
    data_restorator,
    matrix_builder,
    objectnat_calculator,
)
from app.common.modules.effects_api_gateway import effects_api_gateway
from app.dto.provision_dto import ProvisionDTO
from app.schemas.provision_base_schema import ProvisionSchema

LIVING_BUILDINGS_ID = 4


class ProvisionService:

    def __init__(self):
        pass

    @staticmethod
    async def calculate_provision(
        provision_params: ProvisionDTO, token: str
    ) -> ProvisionSchema:
        """
        Calculate provision effects by project data and target scenario
        Args:
            provision_params (ProvisionDTO): Project data
            token (str): Authorization token
        Returns:
             gpd.GeoDataFrame: Provision for scenario.
        """

        logger.info(
            f"Started calculating effects for {provision_params.scenario_id} and service{provision_params.service_type_id}"
        )
        project_data = await effects_api_gateway.get_project_data(
            provision_params.project_id, token
        )
        project_territory = await effects_api_gateway.get_project_territory(
            provision_params.project_id, token
        )
        service_default_capacity = await effects_api_gateway.get_default_capacity(
            service_type_id=provision_params.service_type_id
        )
        normative_data = await effects_api_gateway.get_service_normative(
            territory_id=project_data["territory"]["id"],
            context_ids=project_data["properties"]["context"],
            service_type_id=provision_params.service_type_id,
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
            service_type_id=provision_params.service_type_id,
            token=token,
        )
        if context_services.empty:
            # ToDo Revise to another code
            raise http_exception(
                status_code=404,
                msg="No services of {service_type_id} type found in context",
                _input={"service_type_id": provision_params.service_type_id},
                _detail={},
            )
        context_services = await attribute_parser.parse_all_from_services(
            services=context_services, service_default_capacity=service_default_capacity
        )
        target_scenario_population = (
            await effects_api_gateway.get_scenario_population_data(
                scenario_id=provision_params.scenario_id, token=token
            )
        )
        target_scenario_buildings = await effects_api_gateway.get_scenario_buildings(
            scenario_id=provision_params.scenario_id, token=token
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
            scenario_id=provision_params.scenario_id,
            service_type_id=provision_params.service_type_id,
            token=token,
        )
        target_scenario_services = await attribute_parser.parse_all_from_services(
            services=target_scenario_services,
            service_default_capacity=service_default_capacity,
        )
        before_buildings = await asyncio.to_thread(
            pd.concat,
            objs=[context_buildings, target_scenario_buildings],
        )
        before_services = await asyncio.to_thread(
            pd.concat, objs=[context_services, target_scenario_services]
        )
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
        before_matrix = await asyncio.to_thread(
            matrix_builder.calculate_availability_matrix,
            buildings=before_buildings,
            services=before_services,
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
        result = {k: json.loads(v.to_json()) for k, v in before_prove_data.items()}
        logger.info(
            f"Calculated PROVISION for {provision_params.scenario_id} and {provision_params.service_type_id}"
        )
        return ProvisionSchema(**result)


provision_service = ProvisionService()

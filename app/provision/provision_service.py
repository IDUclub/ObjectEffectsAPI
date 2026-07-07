import asyncio
import json

import geopandas as gpd
import pandas as pd
from loguru import logger

from app.common.exceptions.http_exception_wrapper import http_exception
from app.common.modules import (
    EffectsAPIGateway,
    attribute_parser,
    data_restorator,
    matrix_builder,
    objectnat_calculator,
)
from app.dto.provision_dto import ProvisionDTO
from app.schemas.provision_base_schema import (
    MultiProvisionRequestSchema,
    MultiProvisionSchema,
    ProvisionSchema,
    ProvisionSummarySchema,
    ServiceProvisionResultSchema,
)

LIVING_BUILDINGS_ID = 4


class ProvisionService:

    def __init__(self, gateway: EffectsAPIGateway) -> None:
        self.gateway = gateway

    async def _fetch_shared_data(
        self,
        project_id: int,
        scenario_id: int,
        token: str,
    ) -> dict:
        """
        Fetch scenario data which does not depend on service type
        Args:
            project_id (int): Project ID
            scenario_id (int): Target scenario ID
            token (str): Authorization token
        Returns:
            dict: project data, context and target scenario buildings with populations
        """

        project_data = await self.gateway.get_project_data(project_id, token)
        project_territory = await self.gateway.get_project_territory(project_id, token)
        context_population = await self.gateway.get_context_population(
            territory_ids_list=project_data["properties"]["context"], token=token
        )
        context_buildings = await self.gateway.get_project_context_buildings(
            scenario_id=project_data["base_scenario"]["id"], token=token
        )
        context_buildings.drop(
            index=context_buildings.sjoin(project_territory).index, inplace=True
        )
        context_buildings = await attribute_parser.parse_all_from_buildings(
            living_buildings=context_buildings,
        )
        target_scenario_population = await self.gateway.get_scenario_population_data(
            scenario_id=scenario_id, token=token
        )
        target_scenario_buildings = await self.gateway.get_scenario_buildings(
            scenario_id=scenario_id, token=token
        )
        target_scenario_buildings = await attribute_parser.parse_all_from_buildings(
            living_buildings=target_scenario_buildings,
        )
        return {
            "project_data": project_data,
            "context_population": context_population,
            "context_buildings": context_buildings,
            "target_scenario_population": target_scenario_population,
            "target_scenario_buildings": target_scenario_buildings,
        }

    async def _calculate_for_service(
        self,
        shared_data: dict,
        scenario_id: int,
        service_type_id: int,
        token: str,
    ) -> dict[str, gpd.GeoDataFrame]:
        """
        Calculate provision for one service type over prefetched scenario data
        Args:
            shared_data (dict): data prefetched by _fetch_shared_data
            scenario_id (int): Target scenario ID
            service_type_id (int): Service type ID
            token (str): Authorization token
        Returns:
            dict[str, gpd.GeoDataFrame]: dict with fields "buildings", "services" and "links"
        """

        project_data = shared_data["project_data"]
        service_default_capacity = await self.gateway.get_default_capacity(
            service_type_id=service_type_id
        )
        normative_data = await self.gateway.get_service_normative(
            territory_id=project_data["territory"]["id"],
            context_ids=project_data["properties"]["context"],
            service_type_id=service_type_id,
            token=token,
        )
        context_buildings = await asyncio.to_thread(
            data_restorator.restore_demands,
            buildings=shared_data["context_buildings"].copy(),
            service_normative=normative_data["services_capacity_per_1000_normative"],
            service_normative_type=normative_data["capacity_type"],
            target_population=shared_data["context_population"],
        )
        context_buildings["is_project"] = False
        context_services = await self.gateway.get_project_context_services(
            scenario_id=project_data["base_scenario"]["id"],
            service_type_id=service_type_id,
            token=token,
        )
        if context_services.empty:
            # ToDo Revise to another code
            raise http_exception(
                status_code=404,
                msg="No services of {service_type_id} type found in context",
                _input={"service_type_id": service_type_id},
                _detail={},
            )
        context_services = await attribute_parser.parse_all_from_services(
            services=context_services, service_default_capacity=service_default_capacity
        )
        target_scenario_buildings = await asyncio.to_thread(
            data_restorator.restore_demands,
            buildings=shared_data["target_scenario_buildings"].copy(),
            service_normative=normative_data["services_capacity_per_1000_normative"],
            service_normative_type=normative_data["capacity_type"],
            target_population=shared_data["target_scenario_population"],
        )
        target_scenario_buildings["is_project"] = True
        target_scenario_services = await self.gateway.get_scenario_services(
            scenario_id=scenario_id,
            service_type_id=service_type_id,
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
        return before_prove_data

    @staticmethod
    def _build_summary(
        buildings: gpd.GeoDataFrame,
        services: gpd.GeoDataFrame,
    ) -> ProvisionSummarySchema:
        """
        Aggregate provision results into summary statistics
        Args:
            buildings (gpd.GeoDataFrame): buildings layer with provision attributes
            services (gpd.GeoDataFrame): services layer with load attributes
        Returns:
            ProvisionSummarySchema: aggregated provision statistics
        """

        provision_values = buildings["provision_value"].dropna()
        total_capacity = int(services["capacity"].sum())
        total_demand = int(buildings["demand"].sum())
        balance = total_capacity - total_demand
        return ProvisionSummarySchema(
            services_count=int(len(services)),
            total_capacity=total_capacity,
            total_demand=total_demand,
            satisfied_demand_within=int(buildings["supplied_demands_within"].sum()),
            satisfied_demand_without=int(buildings["supplied_demands_without"].sum()),
            unsatisfied_demand=int(buildings["demand_left"].sum()),
            balance=balance,
            deficit=max(0, -balance),
            surplus=max(0, balance),
            average_provision_value=(
                round(float(provision_values.mean()), 3)
                if not provision_values.empty
                else None
            ),
            median_provision_value=(
                round(float(provision_values.median()), 3)
                if not provision_values.empty
                else None
            ),
        )

    async def calculate_provision(
        self, provision_params: ProvisionDTO, token: str
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
        shared_data = await self._fetch_shared_data(
            project_id=provision_params.project_id,
            scenario_id=provision_params.scenario_id,
            token=token,
        )
        if provision_params.target_population:
            shared_data["target_scenario_population"] = (
                provision_params.target_population
            )
        before_prove_data = await self._calculate_for_service(
            shared_data=shared_data,
            scenario_id=provision_params.scenario_id,
            service_type_id=provision_params.service_type_id,
            token=token,
        )
        result = {k: json.loads(v.to_json()) for k, v in before_prove_data.items()}
        logger.info(
            f"Calculated PROVISION for {provision_params.scenario_id} and {provision_params.service_type_id}"
        )
        return ProvisionSchema(**result)

    async def calculate_multi_provision(
        self, multi_params: MultiProvisionRequestSchema, token: str
    ) -> MultiProvisionSchema:
        """
        Calculate provision for several service types over one scenario
        Args:
            multi_params (MultiProvisionRequestSchema): project, scenario and services to calculate
            token (str): Authorization token
        Returns:
            MultiProvisionSchema: per-service summaries with optional GeoJSON layers
        """

        logger.info(
            f"Started calculating multi provision for {multi_params.scenario_id} "
            f"and services {list(multi_params.services)}"
        )
        project_id = await self.gateway.get_project_id_by_scenario(
            multi_params.scenario_id, token
        )
        shared_data = await self._fetch_shared_data(
            project_id=project_id,
            scenario_id=multi_params.scenario_id,
            token=token,
        )
        if multi_params.target_population:
            shared_data["target_scenario_population"] = multi_params.target_population
        results = {}
        for service_type_id, service_info in multi_params.services.items():
            try:
                before_prove_data = await self._calculate_for_service(
                    shared_data=shared_data,
                    scenario_id=multi_params.scenario_id,
                    service_type_id=service_type_id,
                    token=token,
                )
            except Exception as e:
                logger.opt(exception=True).error(
                    f"Provision calculation failed for service type {service_type_id}: {e}"
                )
                results[service_type_id] = ServiceProvisionResultSchema(
                    name=service_info.name,
                    error=f"{type(e).__name__}: {e}",
                )
                continue
            layers = None
            if service_info.as_layer:
                layers = ProvisionSchema(
                    **{
                        k: json.loads(v.to_crs(4326).to_json())
                        for k, v in before_prove_data.items()
                    }
                )
            results[service_type_id] = ServiceProvisionResultSchema(
                name=service_info.name,
                summary=self._build_summary(
                    buildings=before_prove_data["buildings"],
                    services=before_prove_data["services"],
                ),
                layers=layers,
            )
        logger.info(f"Calculated MULTI PROVISION for {multi_params.scenario_id}")
        return MultiProvisionSchema(services=results)

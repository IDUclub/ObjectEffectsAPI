import asyncio

from shapely.geometry import shape
import geopandas as gpd
import numpy as np
import pandas as pd

from app.dependencies import urban_api_handler, http_exception


class EffectsAPIGateway:

    @staticmethod
    async def get_service_normative(
            territory_id: int,
            context_ids: list[int],
            service_type_id: int,
    ) -> dict[str, int | str]:
        """
        Function retrieves normative data from urban_api
        Args:
            territory_id: territory id to get normative from
            context_ids: context id to get normative from
            service_type_id: service to get normative from
            year: year to get normative from
        Returns:
            dict[str, int | str]: normative data with normative value and normative type (Literal["time", "dist"])
        Raises:
            400, http exception id not found
        """

        if len(context_ids) == 1:
            response = await urban_api_handler.get(
                f"/api/v1/territory/{context_ids[0]}/normatives",
            )
            request_ter_id = context_ids[0]
        else:
            response = await urban_api_handler.get(
                f"/api/v1/territory/{territory_id}/normatives",
            )
            request_ter_id = territory_id
        response_df = pd.DataFrame.from_records(response)
        response_df["service_type_id"] = response_df["service_type"].apply(lambda x: x["id"])
        service_type = response_df[(response_df["year"] == response_df["year"].max()) & (
                    response_df["service_type_id"] == service_type_id)].iloc[0].to_dict()

        if service_type["service_type"]["id"] == service_type_id:
            if not pd.isna(service_type["radius_availability_meters"]):
                service_type["normative_value"] = service_type["radius_availability_meters"]
                service_type["normative_type"] = "dist"
                if not pd.isna(service_type.get("services_per_1000_normative")):
                    service_type["capacity_type"] = "unit"
                else:
                    service_type["capacity_type"] = "capacity"
                return service_type
            elif not pd.isna(service_type["time_availability_minutes"]):
                service_type["normative_value"] = service_type["time_availability_minutes"]
                service_type["normative_type"] = "time"
                if not pd.isna(service_type.get("services_per_1000_normative")):
                    service_type["capacity_type"] = "unit"
                else:
                    service_type["capacity_type"] = "capacity"
                return service_type
            else:
                raise http_exception(
                    status_code=404,
                    msg="Service type normative not found in urban_db. ",
                    _input={
                        "territory_id": territory_id,
                        "context_ids": context_ids,
                        "request_ter_id": request_ter_id,
                        "service_type_id": service_type_id,
                    },
                    _detail={
                        "Available service ids": [service_type["id"] for service_type in response]
                    },
                )
        raise http_exception(
            status_code=404,
            msg="Service type normative not found in urban_db. Try another year or service type.",
            _input={
                "territory_id": territory_id,
                "context_ids": context_ids,
                "request_ter_id": request_ter_id,
                "service_type_id": service_type_id,
            },
            _detail={
                "Available service ids": response_df["service_type_id"].to_list()
            },
        )

    @staticmethod
    async def get_project_data(project_id: int) -> dict[str, int | dict]:
        """
        Function retrieves project territory data from urban_api
        Args:
            project_id: project id to get territory from
        Returns:
            dict with "geometry" field as dict with "type" and "coordinates" fields and field "base_scenario_id"
        """

        response = await urban_api_handler.get(
            endpoint_url=f"/api/v1/projects/{project_id}",
        )

        return response

    @staticmethod
    async def get_scenario_buildings(
            scenario_id: int,
    ) -> gpd.GeoDataFrame:
        """
        Function retrieves scenario buildings data from urban_api
        Args:
            scenario_id: scenario id to get buildings from
        Returns:
            gpd.GeoDataFrame: buildings layer, can be empty
        """

        buildings = await urban_api_handler.get(
            endpoint_url=f"/api/v1/scenarios/{scenario_id}/geometries_with_all_objects",
            params={
                "physical_object_type_id": 4
            }
        )
        buildings_gdf = gpd.GeoDataFrame.from_features(buildings)
        if buildings_gdf.empty:
            return buildings_gdf
        buildings_gdf.set_crs(4326, inplace=True)
        return buildings_gdf

    @staticmethod
    async def get_project_context_buildings(
            project_id: int,
    ) -> gpd.GeoDataFrame:
        """
        Function retrieves scenario context buildings data from urban_api
        Args:
            project_id: scenario id to get buildings from
        Returns:
            gpd.GeoDataFrame: buildings layer
        Raises:
            404, http exception living buildings not found
        """

        context_buildings = await urban_api_handler.get(
            endpoint_url=f"/api/v1/projects/{project_id}/context/geometries_with_all_objects",
            params={
                "physical_object_type_id": 4,
            }
        )
        context_buildings_gdf = gpd.GeoDataFrame.from_features(context_buildings)
        if context_buildings_gdf.empty:
            return context_buildings_gdf
        context_buildings_gdf.set_crs(4326, inplace=True)
        return context_buildings_gdf

    @staticmethod
    async def get_scenario_services(
            scenario_id: int,
            service_type_id: int,
    ) -> gpd.GeoDataFrame:
        """
        Function retrieves scenario services data from urban_api
        Args:
            scenario_id: scenario id to get services from
            service_type_id: service to get services from
        Returns:
            gpd.GeoDataFrame: services layer, can be empty
        """

        services = await urban_api_handler.get(
            endpoint_url=f"/api/v1/scenarios/{scenario_id}/geometries_with_all_objects",
            params={
                "service_type_id": service_type_id,
            }
        )
        services_gdf = gpd.GeoDataFrame.from_features(services)
        if services_gdf.empty:
            return services_gdf
        services_gdf.set_crs(4326, inplace=True)
        return services_gdf

    @staticmethod
    async def get_project_context_services(
            project_id: int,
            service_type_id: int,
    ) -> gpd.GeoDataFrame:
        """
        Function retrieves scenario context services data from urban_api
        Args:
            project_id: scenario id to get services from
            service_type_id: service to get services from
        Returns:
            gpd.GeoDataFrame: context services layer. Can be empty
        """

        context_services = await urban_api_handler.get(
            endpoint_url=f"/api/v1/projects/{project_id}/context/geometries_with_all_objects",
            params={
                "service_type_id": service_type_id,
            }
        )
        context_services_gdf = gpd.GeoDataFrame.from_features(context_services)
        if context_services_gdf.empty:
            return context_services_gdf
        context_services_gdf.set_crs(4326, inplace=True)
        return context_services_gdf

    @staticmethod
    async def get_scenario_population_data(
            scenario_id: int | None
    ) -> int | None:
        """
        Function retrieves population data from urban_api
        Args:
            scenario_id: scenario id to get population data from
        Returns:
            int | none: population data layer, if < 1 returns None
        """

        population = await urban_api_handler.get(
            endpoint_url=f"/api/v1/scenarios/{scenario_id}/indicators_values",
            params={
                "indicators_ids": 1,
            }
        )

        if (value := population[0]["value"]) < 1:
            return None
        return value

    @staticmethod
    async def get_context_population(
            territory_ids_list: list[int],
    ) -> int:
        """
        Function retrieves territory population data from urban_api by territory id
        Args:
            territory_ids_list: list[int]: territory ids list to get population data from
        Returns:
            gpd.GeoDataFrame: territory population data layer
        """

        task_list = [urban_api_handler.get(
            endpoint_url=f"/api/v1/territory/{territory_id}/indicator_values",
            params={
                "indicator_ids": 1
            }
        ) for territory_id in territory_ids_list]

        result = await asyncio.gather(*task_list)
        return sum([item[0]["value"] for item in result])

    @staticmethod
    async def get_project_territory(project_id: int) -> gpd.GeoDataFrame:
        """
        Function retrieves territory data from urban_api
        Args:
            project_id: project id to get territory data from
        Returns:
            gpd.GeoDataFrame: territory data layer
        """

        territory = await urban_api_handler.get(
            endpoint_url=f"/api/v1/projects/{project_id}/territory",
        )
        territory_gdf = gpd.GeoDataFrame(geometry=[shape(territory["geometry"])], crs=4326)
        return territory_gdf

effects_api_gateway = EffectsAPIGateway()

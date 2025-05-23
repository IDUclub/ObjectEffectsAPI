import json
import asyncio

import pandas as pd
import geopandas as gpd

from app.dependencies import http_exception


class AttributeParser:
    """
    Cass aimed to parse data in acceptable format to convert in other dtypes
    """

    @staticmethod
    async def parse_all_from_buildings(
            living_buildings: pd.DataFrame | gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
        """
        Function purses living building area for buildings from nested response
        Args:
            living_buildings (gpd.GeoDataFrame): nested response from api as feature collection
        Returns:
            gpd.GeoDataFrame: living building area with parsed storeys data. Can be empty
        """

        living_buildings = living_buildings.copy()
        if living_buildings.empty:
            return living_buildings
        living_buildings["storeys_count"] = await asyncio.to_thread(
            living_buildings["physical_objects"].apply,
            lambda x: x[0]["building"]["floors"] if x[0]["building"] else None,
        )
        if living_buildings["storeys_count"].isna().all():
            living_buildings["storeys_count"] = await asyncio.to_thread(
                living_buildings["physical_objects"].apply,
                lambda x: x[0].get("properties").get("Количество этажей")
            )
        living_buildings["building_id"] = await asyncio.to_thread(
            living_buildings["physical_objects"].apply,
            lambda x: x[0]["physical_object_id"],
        )
        living_buildings = living_buildings.drop(
            ['object_geometry_id', 'territory', 'address', 'osm_id', 'physical_objects', 'services'],
            axis=1,
        )
        return living_buildings

    @staticmethod
    def _parse_service_capacity(
            services:gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
        """
        Function parses capacity attributes from nested response
        Args:
            services (gpd.GeoDataFrame): nested response from api as feature collection
        Returns:
            gpd.GeoDataFrame: service capacity with parsed storeys data. Can be empty
        """

        services["capacity"] = services["services"].apply(lambda x: x[0].get("capacity"))
        return services

    @staticmethod
    def _parse_service_id(
            services: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """
        Function parses service id from nested response
        Args:
            services (gpd.GeoDataFrame): nested response from api as feature collection
        Returns:
            gpd.GeoDataFrame: service id with parsed storeys data. Can be empty
        """

        services["service_id"] = services["services"].apply(lambda x: x[0].get("service_id"))
        return services

    async def parse_all_from_services(
            self,
            services: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
        """
        Function parses all required data from service request data
        Args:
            services (gpd.GeoDataFrame): nested response from api as feature collection
        Returns:
            gpd.GeoDataFrame: service capacity with parsed storeys data. Can be empty
        """
        services = services.copy()
        if services.empty:
            return services
        services = await asyncio.to_thread(
            self._parse_service_id,
            services=services,
        )
        services = await asyncio.to_thread(
            self._parse_service_capacity,
            services=services
        )
        services = services.drop(
            ['object_geometry_id', 'territory', 'address', 'osm_id', 'physical_objects', 'services'],
            axis=1
        )
        return services

attribute_parser = AttributeParser()

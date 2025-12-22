from typing import Literal

import geopandas as gpd
import numpy as np
import pandas as pd
from objectnat import get_balanced_buildings

from app.common.exceptions.http_exception_wrapper import http_exception


class DataRestorator:
    """
    Class for restoration demand and population for buildings layer
    """

    @staticmethod
    def _restore_stores(
        buildings: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
        """
        Function to restore stores from db, have to include columns stores_count
        Args:
            buildings (gpd.GeoDataFrame): buildings layer with "stores_count" attribute (column)\
        Returns:
            gpd.GeoDataFrame: restored buildings layer with "stores_count" attribute
        """

        if buildings.empty:
            return buildings
        if buildings["storeys_count"].isnull().all():
            buildings["storeys_count"] = 3
            return buildings
        average_stores = buildings["storeys_count"].mean()
        buildings["storeys_count"] = buildings["storeys_count"].fillna(average_stores)
        return buildings

    @staticmethod
    def _restore_target_population(
        buildings: gpd.GeoDataFrame,
    ) -> int:
        """
        Function estimates target population for territory
        Args:
            buildings (gpd.GeoDataFrame): living buildings data
        Returns:
            int: target population to restore
        """

        local_crs = buildings.estimate_utm_crs()
        buildings = buildings.to_crs(local_crs)
        return int(sum(buildings.area * buildings["storeys_count"]) * 0.8 / 33)

    # ToDo delete crs transformation
    def _restore_population(
        self,
        buildings: gpd.GeoDataFrame,
        target_population: int | None = None,
    ):
        """
        Function fills population data with objectnat population restoration
        Args:
            buildings (gpd.GeoDataFrame): living buildings data
            target_population (int | None): Target population to restore, defaults to None
        """

        if buildings.empty:
            return buildings
        buildings = self._restore_stores(buildings)
        if not target_population:
            target_population = self._restore_target_population(buildings)
        local_crs = buildings.estimate_utm_crs()
        buildings = buildings.to_crs(local_crs)
        buildings["storeys_count"] = buildings["storeys_count"].apply(
            lambda x: int(round(x))
        )
        buildings["living_area"] = buildings.area * buildings["storeys_count"] * 0.8
        buildings["living_area"] = buildings["living_area"].astype(int)
        balanced_buildings = get_balanced_buildings(
            living_buildings=buildings,
            population=int(target_population),
        )
        balanced_buildings["population"] = balanced_buildings["population"].astype(int)
        return balanced_buildings.to_crs(4326)

    @staticmethod
    def _generate_demand_per_building(
        buildings: gpd.GeoDataFrame,
        target_demand: int | float,
    ) -> pd.DataFrame | gpd.GeoDataFrame:
        """
        Function generates random demands by probability with population data per building
        Args:
            buildings (gpd.GeoDataFrame): living buildings data
            target_demand (float): target demand data
        Returns:
            gpd.GeoDataFrame: weighted random demand data
        """

        p = buildings["population"] / buildings["population"].sum()
        rng = np.random.default_rng(seed=0)
        r = pd.Series(0, p.index)
        choice = np.unique(
            rng.choice(p.index, int(target_demand), p=p.values), return_counts=True
        )
        choice = r.add(pd.Series(choice[1], choice[0]), fill_value=0)
        buildings["demand"] = choice.astype(int)
        return buildings

    # Todo review provision model or at least create capacity solver
    def restore_demands(
        self,
        buildings: gpd.GeoDataFrame,
        service_normative: int,
        service_normative_type: Literal["unit", "capacity"],
        target_population: int | None = None,
    ) -> gpd.GeoDataFrame:
        """
        Function restores demands in buildings by population for service
        Args:
            buildings: living buildings data
            service_normative (int): service normative
            service_normative_type (str): service normative type
            target_population (int | None): Target population to restore, defaults to None
        Returns:
            gdp.GeoDataFrame: buildings data with restored demands
        """

        if buildings.empty:
            return buildings
        buildings = self._restore_population(
            buildings=buildings,
            target_population=target_population,
        )
        if service_normative_type == "capacity":
            target_total_demand = (
                buildings["population"].sum() / 1000 * service_normative
            )
            buildings = self._generate_demand_per_building(
                buildings=buildings, target_demand=target_total_demand
            )
            return buildings
        elif service_normative_type == "unit":
            buildings["demand"] = buildings["population"].astype(int).copy()
            return buildings
        else:
            raise http_exception(
                status_code=500,
                msg="Service demand normative not found",
                _input={
                    "service_normative_type": service_normative_type,
                },
                _detail={"available_demand_type": ["unit", "capacity"]},
            )

        def restore_capacity(
            services: gpd.GeoDataFrame, service_capacity_normative: int
        ) -> gpd.GeoDataFrame:

            services["capacity"] = service_capacity_normative


data_restorator = DataRestorator()

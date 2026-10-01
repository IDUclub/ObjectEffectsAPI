from typing import Literal

import geopandas as gpd
import numpy as np
import pandas as pd

from app.common.exceptions.http_exception_wrapper import http_exception

# Share of a floor area that is living area, when the official one is unknown.
LIVING_AREA_SHARE = 0.8
DEFAULT_LIVING_AREA_PER_PERSON = 33.0
# A population indicator further than this factor from the housing capacity
# belongs to another territory (e.g. a whole municipality) and is not used.
INDICATOR_TOLERANCE = 2.0


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
    def _living_area(buildings: gpd.GeoDataFrame) -> pd.Series:
        """
        Living area of each building in m2, buildings in a metric CRS
        Args:
            buildings (gpd.GeoDataFrame): living buildings with "storeys_count" and,
                when known, "living_area_official" and "building_area_official"
        Returns:
            pd.Series: official living area, else footprint x storeys x 0.8
        """

        footprint = buildings.area
        if "building_area_official" in buildings.columns:
            official_footprint = pd.to_numeric(
                buildings["building_area_official"], errors="coerce"
            )
            footprint = official_footprint.where(official_footprint > 0, footprint)
        modeled = footprint * buildings["storeys_count"] * LIVING_AREA_SHARE
        if "living_area_official" not in buildings.columns:
            return modeled
        official = pd.to_numeric(buildings["living_area_official"], errors="coerce")
        return official.where(official > 0, modeled)

    @staticmethod
    def _choose_population(
        capacity: float,
        indicator: int | None,
        explicit: int | None,
    ) -> tuple[int, str]:
        """
        Total population to distribute and where it comes from
        Args:
            capacity (float): residents the housing stock holds
            indicator (int | None): Urban API population indicator
            explicit (int | None): population set by the caller
        Returns:
            tuple[int, str]: population and its source — "explicit", "indicator"
            or "housing_stock"
        """

        if explicit:
            return int(explicit), "explicit"
        if indicator and capacity <= 0:
            return int(indicator), "indicator"
        if (
            indicator
            and 1 / INDICATOR_TOLERANCE <= indicator / capacity <= INDICATOR_TOLERANCE
        ):
            return int(indicator), "indicator"
        return int(round(capacity)), "housing_stock"

    @staticmethod
    def _balance_population(
        buildings: gpd.GeoDataFrame,
        population: int,
    ) -> gpd.GeoDataFrame:
        """
        Function distributes population between buildings proportionally to their living area
        Args:
            buildings (gpd.GeoDataFrame): living buildings data with "living_area" attribute
            population (int): total population to distribute
        Returns:
            gpd.GeoDataFrame: buildings data with restored "population" attribute
        """

        if buildings["living_area"].sum() <= 0:
            buildings["living_area"] = 1
        shares = buildings["living_area"] / buildings["living_area"].sum()
        buildings["population"] = np.floor(shares * population).astype(int)
        remainder = int(population - buildings["population"].sum())
        if remainder > 0:
            top = (shares * population).mod(1).nlargest(remainder).index
            buildings.loc[top, "population"] += 1
        return buildings

    # ToDo delete crs transformation
    def _restore_population(
        self,
        buildings: gpd.GeoDataFrame,
        target_population: int | None = None,
        explicit_population: int | None = None,
        living_area_per_person: float = DEFAULT_LIVING_AREA_PER_PERSON,
    ):
        """
        Function distributes residents between buildings by their living area.

        The total is the explicit population when given, else the Urban API indicator
        when it agrees with the housing capacity (living area / m2 per person) within
        INDICATOR_TOLERANCE, else the housing capacity itself. How the total was chosen
        is kept in ``buildings.attrs["population"]``.
        Args:
            buildings (gpd.GeoDataFrame): living buildings data
            target_population (int | None): Urban API population indicator
            explicit_population (int | None): population set by the caller, always used
            living_area_per_person (float): m2 of living area per resident
        """

        if buildings.empty:
            return buildings
        buildings = self._restore_stores(buildings)
        local_crs = buildings.estimate_utm_crs()
        buildings = buildings.to_crs(local_crs)
        buildings["storeys_count"] = buildings["storeys_count"].apply(
            lambda x: max(int(round(x)), 1)
        )
        buildings["living_area"] = self._living_area(buildings).fillna(0).astype(int)
        capacity = float(buildings["living_area"].sum()) / living_area_per_person
        population, source = self._choose_population(
            capacity, target_population, explicit_population
        )
        buildings = self._balance_population(
            buildings=buildings,
            population=population,
        )
        result = buildings.to_crs(4326)
        result.attrs["population"] = {
            "source": source,
            "population": population,
            "housing_capacity": int(round(capacity)),
            "indicator": int(target_population) if target_population else None,
            "living_area_per_person": living_area_per_person,
            "buildings": int(len(result)),
        }
        return result

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
        explicit_population: int | None = None,
        living_area_per_person: float = DEFAULT_LIVING_AREA_PER_PERSON,
    ) -> gpd.GeoDataFrame:
        """
        Function restores demands in buildings by population for service
        Args:
            buildings: living buildings data
            service_normative (int): service normative
            service_normative_type (str): service normative type
            target_population (int | None): Urban API population indicator
            explicit_population (int | None): population set by the caller
            living_area_per_person (float): m2 of living area per resident
        Returns:
            gdp.GeoDataFrame: buildings data with restored demands
        """

        if buildings.empty:
            return buildings
        buildings = self._restore_population(
            buildings=buildings,
            target_population=target_population,
            explicit_population=explicit_population,
            living_area_per_person=living_area_per_person,
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


data_restorator = DataRestorator()

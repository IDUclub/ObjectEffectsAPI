import json
from typing import Literal

import pandas as pd
import geopandas as gpd
from objectnat import get_service_provision

from app.dependencies import http_exception


class ObjectNatCalculator:

    @staticmethod
    def evaluate_provision(
            buildings: gpd.GeoDataFrame,
            services: gpd.GeoDataFrame,
            matrix: pd.DataFrame,
            service_normative: int
    ) -> dict[str, gpd.GeoDataFrame]:
        """
        Function calculates provision and writes results as dict with fields "buildings", "services" and "links"
        Args:
            buildings (gpd.GeoDataFrame): GeoDataFrame of buildings
            services (gpd.GeoDataFrame): GeoDataFrame of services
            matrix (pd.DataFrame): GeoDataFrame of matrix
            service_normative (int): service normative accessibility
        Returns:
            dict[str, gpd.GeoDataFrame]: dict with fields "buildings", "services" and "links"
        """


        build_prov, services_prov, links_prov = get_service_provision(
            buildings=buildings,
            services=services,
            adjacency_matrix=matrix,
            threshold=int(service_normative * 1000 / 60 * 40),
        )

        return {
            "buildings": build_prov,
            "services": services_prov,
            "links": links_prov,
        }

    @staticmethod
    def _calculate_index(
            supplied_demand_after: pd.Series,
            supplied_demand_before: pd.Series,
            unsupplied_demand_after: pd.Series,
            unsupplied_demand_before: pd.Series,
            total_demand: int
    ) -> pd.Series:
        """
        Function calculates index effects marks for provided objects
        Args:
            supplied_demand_after (pd.Series): supplied demand for target scenario
            supplied_demand_before (pd.Series): supplied demand for base scenario
            unsupplied_demand_after (pd.Series): unsupplied demand for target scenario
            unsupplied_demand_before (pd.Series): unsupplied demand for base scenario
            total_demand(int): total demand for target scenario + base scenario
        """

        result = (
                         (
                                 supplied_demand_after - supplied_demand_before
                         ) - (
                                 unsupplied_demand_after - unsupplied_demand_before
                         )
                 ) / total_demand
        return result

    # ToDo fix is_project attribute
    @staticmethod
    def _calculate_absolute(
            supplied_demand_after: pd.Series,
            supplied_demand_before: pd.Series,
            unsupplied_demand_after: pd.Series,
            unsupplied_demand_before: pd.Series,
    ) -> pd.Series:
        """
        Function calculates absolute effects marks for provided objects
        Args:
            supplied_demand_after (pd.Series): supplied demand for target scenario
            supplied_demand_before (pd.Series): supplied demand for base scenario
            unsupplied_demand_after (pd.Series): unsupplied demand for target scenario
            unsupplied_demand_before (pd.Series): unsupplied demand for base scenario
        """

        result = (
                         supplied_demand_after - supplied_demand_before
                 ).apply(lambda x: max(0, x)) - (
                         unsupplied_demand_after - unsupplied_demand_before
                 ).apply(lambda x: max(0, x)
                         )
        return result

    def _calculate_effects(
            self,
            effects: pd.DataFrame | gpd.GeoDataFrame,
    ) -> pd.DataFrame | gpd.GeoDataFrame:
        """
        Function calculates provision effects
        Args:
            effects (pd.DataFrame | gpd.GeoDataFrame): GeoDataFrame of effects
        Returns:
            pd.Series: effects results
        """

        #ToDo fix calculation without/before
        effects = effects.copy()
        supplied_demand_within_before = effects["supplyed_demands_within_before"].fillna(0)
        supplied_demand_without_before = effects["supplyed_demands_without_before"].fillna(0)
        supplied_demand_within_after = effects["supplyed_demands_within_after"].fillna(0)
        supplied_demand_without_after = effects["supplyed_demands_without_after"].fillna(0)
        unsupplied_demand_within_before = effects["us_demands_within_before"].fillna(0)
        unsupplied_demand_within_after = effects["us_demands_within_after"].fillna(0)
        total_supplied_demands_before = supplied_demand_without_before
        total_supplied_demands_after = supplied_demand_without_after
        total_us_demands_before = effects["us_demands_without_before"].fillna(0)
        total_us_demands_after = effects["us_demands_without_after"].fillna(0)
        total_demand = int(effects["demand"].sum())

        effects.dropna(subset="is_project", inplace=True)

        project_total_supplied_demands_before = effects[
                                                    effects["is_project"]
                                                ]["supplyed_demands_without_before"].fillna(0)

        project_total_supplied_demands_after = effects[
                                                   effects["is_project"]
                                               ]["supplyed_demands_without_after"].fillna(0)

        project_total_us_demands_before = effects[
                                              effects["is_project"]
                                          ]["us_demands_without_before"].fillna(0)

        project_total_us_demands_after = effects[
                                             effects["is_project"]
                                         ]["us_demands_without_after"].fillna(0)

        project_total_demand = int(effects[effects["is_project"]]["demand"].sum())

        effects["absolute_total"] = self._calculate_absolute(
            supplied_demand_after=total_supplied_demands_after,
            supplied_demand_before=total_supplied_demands_before,
            unsupplied_demand_after=total_us_demands_after,
            unsupplied_demand_before=total_us_demands_before,
        )
        effects["index_total"] = self._calculate_index(
            supplied_demand_after=total_supplied_demands_after,
            supplied_demand_before=total_supplied_demands_before,
            unsupplied_demand_after=total_us_demands_after,
            unsupplied_demand_before=total_us_demands_before,
            total_demand=total_demand,
        )
        effects["absolute_scenario_project"] = None
        effects.loc[effects["is_project"], ["absolute_scenario_project"]] = self._calculate_absolute(
            supplied_demand_before=project_total_supplied_demands_before,
            supplied_demand_after=project_total_supplied_demands_after,
            unsupplied_demand_after=project_total_us_demands_after,
            unsupplied_demand_before=project_total_us_demands_before,
        )
        effects["index_scenario_project"] = None
        effects.loc[effects["is_project"], ["index_scenario_project"]] = self._calculate_index(
            supplied_demand_after=project_total_supplied_demands_after,
            supplied_demand_before=project_total_supplied_demands_before,
            unsupplied_demand_after=project_total_us_demands_after,
            unsupplied_demand_before=project_total_us_demands_before,
            total_demand=project_total_demand,
        )
        effects["absolute_within"] = self._calculate_absolute(
            supplied_demand_before=supplied_demand_within_before,
            supplied_demand_after=supplied_demand_within_after,
            unsupplied_demand_before=unsupplied_demand_within_before,
            unsupplied_demand_after=unsupplied_demand_within_after
        )
        return effects

    # ToDo split function
    def estimate_effects(
            self,
            provision_before: gpd.GeoDataFrame,
            provision_after: gpd.GeoDataFrame,
    ) -> pd.DataFrame | gpd.GeoDataFrame:
        """
        Main function which calculates provision and estimates effects
        Args:
            provision_before (gpd.GeoDataFrame): Provision before
            provision_after (gpd.GeoDataFrame): Provision after
        Returns:
            gpd.GeoDataFrame: layer with effects, provision before and after attributes
        """

        provision_before["supplyed_demands_within_before"] = provision_before["supplyed_demands_within"].copy()

        provision_before[
            "us_demands_within_before"
        ] = provision_before["demand"] - provision_before["supplyed_demands_within_before"]

        provision_before[
            "supplyed_demands_without_before"
        ] = provision_before["supplyed_demands_without"]

        provision_before[
            "us_demands_without_before"
        ] = provision_before["demand"] - provision_before["supplyed_demands_within_before"]

        provision_after["supplyed_demands_within_after"] = provision_after["supplyed_demands_within"].copy()

        provision_after[
            "us_demands_within_after"
        ] = provision_after["demand"] - provision_after["supplyed_demands_within_after"]

        provision_after[
            "supplyed_demands_without_after"
        ] = provision_after["supplyed_demands_within_after"] + provision_after["supplyed_demands_without"].copy()

        provision_after[
            "us_demands_without_after"
        ] = provision_after["demand"] - provision_after["supplyed_demands_without_after"]

        effects = provision_after.merge(
            provision_before,
            how="outer",
            on=["building_id"]
        )
        effects["geometry"] = effects.apply(
            lambda x: x["geometry_x"] if not pd.isna(x["geometry_x"]) else x["geometry_y"],
            axis=1
        )
        effects.drop(columns=["geometry_x", "geometry_y"], inplace=True)
        effects["demand"] = effects["demand_x"].fillna(0) + effects["demand_y"].fillna(0)
        effects.drop("is_project_y", axis=1, inplace=True)
        effects.rename(columns={"is_project_x": "is_project"}, inplace=True)
        effects = self._calculate_effects(effects)
        effects = effects[
            [
                "geometry",
                "absolute_total",
                "index_total",
                "absolute_scenario_project",
                "index_scenario_project",
                "absolute_within",
                "demand",
                "is_project"
            ]
        ]
        effects = gpd.GeoDataFrame(effects, geometry="geometry", crs=provision_before.crs)
        return effects


objectnat_calculator = ObjectNatCalculator()

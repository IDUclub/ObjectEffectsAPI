from typing import Literal

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import KDTree


class MatrixBuilder:

    @staticmethod
    def calculate_availability_matrix(
        buildings: gpd.GeoDataFrame,
        services: gpd.GeoDataFrame,
        normative_value: int,
        normative_type: Literal["time", "dist"],
    ) -> pd.DataFrame:
        """
        Calculated availability matrix with walk simulation
        Args:
            buildings (gpd.GeoDataFrame): Building geometries
            services (gpd.GeoDataFrame): Service geometries
            normative_value (int): Normative value
            normative_type (Literal["time", "dist"]): Type of normative value
        Returns:
            pd.DataFrame: Availability matrix with distance in minutes
        """

        if normative_type == "time":
            normative_value = (normative_value * 1000 / 60 * 40) / 1.41
        else:
            normative_value = (normative_value * 3) / 1.41
        local_crs = buildings.estimate_utm_crs()
        buildings = buildings.to_crs(local_crs).set_index(buildings.index, drop=True)
        services = services.to_crs(local_crs).set_index(services.index, drop=True)
        buildings_points = [
            geometry.coords[0] for geometry in buildings.geometry.centroid
        ]
        services_points = [
            geometry.coords[0] for geometry in services.geometry.centroid
        ]
        buildings_kd_tree = KDTree(buildings_points)
        services_kd_tree = KDTree(services_points)
        distances = buildings_kd_tree.sparse_distance_matrix(
            other=services_kd_tree, max_distance=normative_value * 3
        )
        matrix = pd.DataFrame.sparse.from_spmatrix(
            distances, index=buildings.index, columns=services.index
        )
        matrix = matrix.sparse.to_dense()
        matrix.replace(0.0, np.nan, inplace=True)
        return matrix


matrix_builder = MatrixBuilder()

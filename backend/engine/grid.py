from __future__ import annotations

from typing import Any

import numpy as np
import h3


class GridState:
    def __init__(
        self,
        h3_indices: list[str],
        E: np.ndarray,
        K: np.ndarray,
        R: np.ndarray,
        T: np.ndarray,
        baselines: dict[str, np.ndarray],
        neighbor_pairs: list[tuple[int, int, float]] | None = None,
    ):
        self.h3_indices = h3_indices
        self.n_cells = len(h3_indices)
        self.E = E
        self.K = K
        self.R = R
        self.T = T
        self.baselines = baselines
        self._neighbor_pairs = neighbor_pairs

    @classmethod
    def initialize(cls, region_boundary: dict[str, Any], params: dict[str, Any]) -> GridState:
        resolution = 8
        shape = h3.geo_to_h3shape(region_boundary)
        h3_indices = list(h3.h3shape_to_cells(shape, resolution))

        if not h3_indices:
            h3_indices = ["882a100d2dfffff"]

        n = len(h3_indices)
        E = np.full(n, 5000.0, dtype=np.float64)
        K = np.full(n, 0.5, dtype=np.float64)
        R = np.full(n, 1.0, dtype=np.float64)
        T = np.full(n, 0.3, dtype=np.float64)

        baselines = {
            "E": E.copy(),
            "K": K.copy(),
            "R": R.copy(),
            "T": T.copy(),
            "unemployment_rate": np.float64(0.04),
        }

        return cls(
            h3_indices=h3_indices,
            E=E,
            K=K,
            R=R,
            T=T,
            baselines=baselines,
        )

    def get_zone_cells(self, zone_geojson: dict[str, Any]) -> list[str]:
        zone_type = zone_geojson.get("type")
        if zone_type == "Point":
            coords = zone_geojson["coordinates"]
            return [h3.latlng_to_cell(coords[1], coords[0], 8)]
        elif zone_type == "Polygon":
            shape = h3.geo_to_h3shape(zone_geojson)
            return list(h3.h3shape_to_cells(shape, 8))
        return []

    def get_neighbor_distances(self) -> list[tuple[int, int, float]]:
        if self._neighbor_pairs is not None:
            return self._neighbor_pairs

        pairs: list[tuple[int, int, float]] = []
        for i, idx in enumerate(self.h3_indices):
            neighbors = h3.grid_disk(idx, 1)
            for j, jdx in enumerate(self.h3_indices):
                if jdx in neighbors and jdx != idx:
                    center_i = h3.cell_to_latlng(idx)
                    center_j = h3.cell_to_latlng(jdx)
                    d = self._haversine(center_i, center_j)
                    pairs.append((i, j, d))
        self._neighbor_pairs = pairs
        return pairs

    @staticmethod
    def _haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
        lat1, lon1 = np.radians(a[0]), np.radians(a[1])
        lat2, lon2 = np.radians(b[0]), np.radians(b[1])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        hav = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        return 6371.0 * 2 * np.arcsin(np.sqrt(hav))

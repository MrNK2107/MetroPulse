from uuid import UUID, uuid4
from typing import Any
from datetime import date

from app.config import settings


class DatabaseClient:
    def __init__(self):
        self._client = None

    async def connect(self):
        pass

    async def close(self):
        pass

    async def list_regions(self) -> list[dict[str, Any]]:
        return [
            {
                "id": str(uuid4()),
                "name": "Manhattan",
                "city": "New York",
                "country": "US",
                "population": 1_600_000,
                "boundary": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-74.025, 40.700],
                        [-73.925, 40.700],
                        [-73.925, 40.795],
                        [-74.025, 40.795],
                        [-74.025, 40.700],
                    ]],
                },
            }
        ]

    async def get_baseline(self, region_id: UUID) -> dict[str, Any] | None:
        return {
            "region_id": str(region_id),
            "recorded_at": date.today().isoformat(),
            "gdp_index": 1.0,
            "unemployment": 0.04,
            "real_estate_idx": 1.0,
            "transit_load": 0.5,
        }

    async def list_simulations(self, page: int = 1, per_page: int = 20) -> list[dict[str, Any]]:
        return []

    async def get_simulation(self, simulation_id: UUID) -> dict[str, Any] | None:
        return None

    async def save_simulation(
        self,
        region_id: UUID,
        params: dict[str, Any],
        horizon_months: int,
        result_summary: dict[str, Any],
        cell_states: list[dict[str, Any]],
    ) -> str:
        sim_id = str(uuid4())
        return sim_id

    async def search_case_studies(self, embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        return []


_db: DatabaseClient | None = None


async def get_db() -> DatabaseClient:
    global _db
    if _db is None:
        _db = DatabaseClient()
        await _db.connect()
    return _db

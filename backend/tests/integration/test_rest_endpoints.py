import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_list_regions():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/regions")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) > 0
        assert any(region["id"] == "hyderabad" for region in data["data"])


@pytest.mark.asyncio
async def test_region_profile():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/regions/hyderabad/profile")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["city"] == "Hyderabad"


@pytest.mark.asyncio
async def test_case_studies_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/case-studies?city=hyderabad&sector=manufacturing")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) > 0


@pytest.mark.asyncio
async def test_list_simulations():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/simulations")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

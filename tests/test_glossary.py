import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_glossary_terms(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/glossary/terms")
    assert resp.status_code == 200
    terms = resp.json()
    assert len(terms) >= 5
    term_names = [t["term"] for t in terms]
    assert "Repository" in term_names
    assert "Incident" in term_names
    assert "Sprint" in term_names


@pytest.mark.asyncio
async def test_create_glossary_term(seeded_client: AsyncClient):
    domains = (await seeded_client.get("/api/glossary/domains")).json()
    assert len(domains) > 0
    domain_id = domains[0]["id"]
    resp = await seeded_client.post(
        "/api/glossary/terms",
        json={"domain_id": domain_id, "term": "Endpoint", "definition": "An API endpoint URL"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["term"] == "Endpoint"
    assert data["definition"] == "An API endpoint URL"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_glossary_term(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/glossary/terms")
    terms = resp.json()
    if not terms:
        pytest.skip("No terms found")

    resp = await seeded_client.get(f"/api/glossary/terms/{terms[0]['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == terms[0]["id"]


@pytest.mark.asyncio
async def test_update_glossary_term(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/glossary/terms")
    terms = resp.json()
    if not terms:
        pytest.skip("No terms found")

    resp = await seeded_client.patch(
        f"/api/glossary/terms/{terms[0]['id']}",
        json={"definition": "Updated glossary definition"},
    )
    assert resp.status_code == 200
    assert resp.json()["definition"] == "Updated glossary definition"


@pytest.mark.asyncio
async def test_delete_glossary_term(seeded_client: AsyncClient):
    domains = (await seeded_client.get("/api/glossary/domains")).json()
    assert len(domains) > 0
    domain_id = domains[0]["id"]
    resp = await seeded_client.post(
        "/api/glossary/terms",
        json={"domain_id": domain_id, "term": "TempTerm", "definition": "To be deleted"},
    )
    term_id = resp.json()["id"]

    resp = await seeded_client.delete(f"/api/glossary/terms/{term_id}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_domains(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/glossary/domains")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_create_domain(seeded_client: AsyncClient):
    resp = await seeded_client.post(
        "/api/glossary/domains",
        json={"name": "Source Control", "description": "Version control and code management tools"},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Source Control"

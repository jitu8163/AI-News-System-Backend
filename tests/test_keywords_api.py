import pytest


@pytest.mark.asyncio
async def test_list_keywords_empty(client, auth_headers):
    resp = await client.get("/api/keywords", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_keyword(client, auth_headers):
    resp = await client.post("/api/keywords", json={"term": "Dengue"}, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["term"] == "Dengue"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_duplicate_keyword_returns_409(client, auth_headers):
    await client.post("/api/keywords", json={"term": "Inflation"}, headers=auth_headers)
    resp = await client.post("/api/keywords", json={"term": "Inflation"}, headers=auth_headers)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_update_keyword(client, auth_headers):
    create_resp = await client.post("/api/keywords", json={"term": "EV"}, headers=auth_headers)
    kw_id = create_resp.json()["id"]

    resp = await client.put(f"/api/keywords/{kw_id}", json={"is_active": False}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_delete_keyword(client, auth_headers):
    create_resp = await client.post("/api/keywords", json={"term": "ToDelete"}, headers=auth_headers)
    kw_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/keywords/{kw_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    list_resp = await client.get("/api/keywords", headers=auth_headers)
    ids = [k["id"] for k in list_resp.json()]
    assert kw_id not in ids


@pytest.mark.asyncio
async def test_list_keywords_is_public(client):
    # The keyword list is public so the frontend filters work without login.
    resp = await client.get("/api/keywords")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_unauthenticated_mutation_returns_401(client):
    # Mutations stay admin-only.
    resp = await client.post("/api/keywords", json={"term": "dengue"})
    assert resp.status_code == 401

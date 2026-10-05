import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_global_search_empty_query():
    response = client.get("/api/search?q=%20")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == ""
    assert data["results"] == {}
    assert data["total"] == 0

def test_global_search_basic():
    response = client.get("/api/search?q=test&types=users,matches,agents,academy")
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert data["query"] == "test"
    assert "types_searched" in data
    assert "results" in data
    assert "total" in data

def test_search_suggestions():
    response = client.get("/api/search/suggest?q=admin")
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)

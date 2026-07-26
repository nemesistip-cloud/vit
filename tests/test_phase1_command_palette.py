from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.command_palette.routes import router


def test_command_palette_lists_and_executes_registered_commands():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    list_response = client.get("/api/platform/commands")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] >= 1
    assert any(command["name"] == "open_wallet" for command in payload["commands"])

    search_response = client.get("/api/platform/commands/search", params={"q": "wallet"})
    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert any(command["name"] == "open_wallet" for command in search_payload["commands"])

    execute_response = client.post("/api/platform/commands/open_wallet")
    assert execute_response.status_code == 200
    assert execute_response.json()["result"] == "wallet"

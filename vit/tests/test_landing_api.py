import asyncio
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_landing():
    response = client.get("/api/public/landing")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("Stats:", data.get("stats"))
        print("Ticker count:", len(data.get("ticker", [])))
        print("Plans count:", len(data.get("plans", [])))
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    test_landing()

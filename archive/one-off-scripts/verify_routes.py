import os
os.environ['JWT_SECRET_KEY'] = 'test_secret'
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)

routes = [
    "/api/blockchain/metrics",
    "/api/blockchain/active",
    "/api/storage/stats",
    "/api/storage/nodes"
]

for r in routes:
    try:
        resp = client.get(r)
        print(f"Route {r}: {resp.status_code}")
        if resp.status_code == 200:
            print(f"  Data: {list(resp.json().keys()) if isinstance(resp.json(), dict) else 'List[' + str(len(resp.json())) + ']'}")
        else:
            print(f"  Error: {resp.text[:100]}")
    except Exception as e:
        print(f"Route {r} failed: {e}")

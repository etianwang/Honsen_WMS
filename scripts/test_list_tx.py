"""Test list transactions endpoint."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402

client = TestClient(app)

login = client.post(
    "/api/auth/login",
    json={"username": "Honsen_Admin", "password": "66778899HONSEN"},
)
assert login.status_code == 200, login.text
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

res = client.get("/api/transactions", headers=headers)
print("status", res.status_code)
if res.status_code != 200:
    print(res.text[:500])
else:
    data = res.json()
    print("items", len(data["items"]), "stats", data["stats"]["total"])
    if data["items"]:
        print("first item_id", data["items"][0].get("item_id"))

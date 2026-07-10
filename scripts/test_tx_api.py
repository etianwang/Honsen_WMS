"""FastAPI TestClient transaction tests."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402

client = TestClient(app)


def login() -> str:
    res = client.post(
        "/api/auth/login",
        json={"username": "Honsen_Admin", "password": "66778899HONSEN"},
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def main() -> None:
    token = login()
    h = auth_headers(token)

    inv = client.get("/api/inventory", headers=h)
    assert inv.status_code == 200, inv.text
    items = inv.json()
    assert items, "inventory empty"
    item = items[0]
    item_id = item["id"]

    for tx_type, extra in [
        ("IN", {"recipient_source": "TEST-CAB", "project_ref": ""}),
        ("OUT", {"recipient_source": "TEST-USER", "project_ref": "日常维护"}),
    ]:
        body = {
            "item_id": item_id,
            "type": tx_type,
            "quantity": 1,
            **extra,
        }
        res = client.post("/api/transactions", json=body, headers=h)
        print(tx_type, res.status_code, res.text)
        assert res.status_code == 201, res.text

    # validation: empty recipient
    bad = client.post(
        "/api/transactions",
        json={"item_id": item_id, "type": "IN", "quantity": 1, "recipient_source": ""},
        headers=h,
    )
    print("empty recipient", bad.status_code, bad.text)

    # item_id 0
    bad2 = client.post(
        "/api/transactions",
        json={"item_id": 0, "type": "OUT", "quantity": 1, "recipient_source": "x"},
        headers=h,
    )
    print("item_id 0 OUT", bad2.status_code, bad2.text)

    # ensure static mount does not swallow POST /api/transactions
    res = client.post(
        "/api/transactions",
        json={
            "item_id": item_id,
            "type": "IN",
            "quantity": 1,
            "recipient_source": "STATIC-TEST",
            "project_ref": "",
        },
        headers=h,
    )
    print("with static mount", res.status_code, res.text[:80])


if __name__ == "__main__":
    main()

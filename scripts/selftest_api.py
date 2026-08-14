"""Honsen WMS end-to-end API self-test (no external Postgres required for pass)."""
from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from backend.main import app

USER = "Honsen_Admin"
PASS = "66778899HONSEN"

results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    client = TestClient(app)

    # --- health / system ---
    try:
        r = client.get("/health")
        record("GET /health", r.status_code == 200 and r.json().get("status") == "ok", r.text[:120])
    except Exception as e:
        record("GET /health", False, str(e))

    try:
        r = client.get("/api/system/status")
        record("GET /api/system/status", r.status_code == 200, r.text[:160])
        status = r.json() if r.status_code == 200 else {}
    except Exception as e:
        record("GET /api/system/status", False, str(e))
        status = {}

    if not status.get("schema_ready", False):
        try:
            r = client.post("/api/system/init")
            record("POST /api/system/init", r.status_code == 200, r.text[:160])
        except Exception as e:
            record("POST /api/system/init", False, str(e))

    # --- auth ---
    token = None
    try:
        r = client.post("/api/auth/login", json={"username": USER, "password": PASS})
        ok = r.status_code == 200 and "access_token" in r.json()
        if ok:
            token = r.json()["access_token"]
        record("POST /api/auth/login", ok, r.text[:160])
    except Exception as e:
        record("POST /api/auth/login", False, str(e))

    if not token:
        print("\nAbort: login failed")
        return 1

    headers = {"Authorization": f"Bearer {token}"}

    try:
        r = client.post("/api/auth/login", json={"username": USER, "password": "wrong"})
        record("POST /api/auth/login bad password", r.status_code in (401, 400, 403), f"status={r.status_code}")
    except Exception as e:
        record("POST /api/auth/login bad password", False, str(e))

    # --- config ---
    try:
        r = client.get("/api/config", headers=headers)
        cfg = r.json() if r.status_code == 200 else {}
        record("GET /api/config", r.status_code == 200 and isinstance(cfg, dict), str(list(cfg.keys()))[:120])
    except Exception as e:
        record("GET /api/config", False, str(e))
        cfg = {}

    test_unit = "__SELFTEST_UNIT__"
    try:
        r = client.post(f"/api/config/UNIT", headers=headers, json={"value": test_unit})
        record("POST /api/config/UNIT", r.status_code in (200, 201), r.text[:120])
        r = client.get("/api/config/UNIT", headers=headers)
        payload = r.json() if r.status_code == 200 else {}
        units = payload.get("values", []) if isinstance(payload, dict) else []
        record("GET /api/config/UNIT contains test", test_unit in units, str(units)[:120])
        r = client.delete(f"/api/config/UNIT/{test_unit}", headers=headers)
        record("DELETE /api/config/UNIT/test", r.status_code == 200, r.text[:120])
    except Exception as e:
        record("config CRUD", False, traceback.format_exc()[-300:])

    # --- inventory CRUD ---
    item_id = None
    try:
        payload = {
            "name": "__SELFTEST_ITEM__",
            "reference": "ST-REF-001",
            "category": "其他",
            "domain": "其他",
            "unit": (cfg.get("UNIT") or ["PCS"])[0] if isinstance(cfg.get("UNIT"), list) else "PCS",
            "current_stock": 10,
            "min_stock": 2,
            "location": (cfg.get("LOCATION") or ["其他"])[0] if isinstance(cfg.get("LOCATION"), list) else "其他",
            "cabinet": "T1",
        }
        r = client.post("/api/inventory", headers=headers, json=payload)
        ok = r.status_code in (200, 201)
        body = r.json() if ok else {}
        item_id = body.get("id")
        record("POST /api/inventory", ok and item_id is not None, r.text[:200])
    except Exception as e:
        record("POST /api/inventory", False, str(e))

    try:
        r = client.get("/api/inventory", headers=headers)
        rows = r.json() if r.status_code == 200 else []
        found = any(i.get("id") == item_id for i in rows) if item_id else False
        record("GET /api/inventory", r.status_code == 200 and found, f"count={len(rows)}")
    except Exception as e:
        record("GET /api/inventory", False, str(e))

    try:
        if item_id:
            r = client.get(f"/api/inventory/{item_id}", headers=headers)
            record("GET /api/inventory/{id}", r.status_code == 200 and r.json().get("name") == "__SELFTEST_ITEM__", r.text[:160])
            r = client.put(
                f"/api/inventory/{item_id}",
                headers=headers,
                json={
                    "name": "__SELFTEST_ITEM__",
                    "reference": "ST-REF-001",
                    "category": "其他",
                    "domain": "其他",
                    "unit": "PCS",
                    "min_stock": 3,
                    "location": "其他",
                    "cabinet": "T1",
                },
            )
            record("PUT /api/inventory/{id}", r.status_code == 200 and r.json().get("min_stock") == 3, r.text[:160])
        else:
            record("GET/PUT inventory by id", False, "no item_id")
    except Exception as e:
        record("GET/PUT inventory by id", False, str(e))

    # --- transactions ---
    tx_id = None
    try:
        if item_id:
            r = client.post(
                "/api/transactions",
                headers=headers,
                json={
                    "item_id": item_id,
                    "type": "IN",
                    "quantity": 5,
                    "recipient_source": "selftest",
                    "project_ref": "ST-PROJ",
                },
            )
            ok = r.status_code in (200, 201)
            record("POST /api/transactions IN", ok, r.text[:200])

            r = client.get(f"/api/inventory/{item_id}", headers=headers)
            stock = r.json().get("current_stock") if r.status_code == 200 else None
            record("inventory stock after IN", stock == 15, f"stock={stock}")

            r = client.post(
                "/api/transactions",
                headers=headers,
                json={
                    "item_id": item_id,
                    "type": "OUT",
                    "quantity": 2,
                    "recipient_source": "selftest-out",
                    "project_ref": "ST-PROJ",
                },
            )
            ok = r.status_code in (200, 201)
            record("POST /api/transactions OUT", ok, r.text[:200])

            r = client.get(f"/api/inventory/{item_id}", headers=headers)
            stock = r.json().get("current_stock") if r.status_code == 200 else None
            record("inventory stock after OUT", stock == 13, f"stock={stock}")
        else:
            record("transactions", False, "no item_id")
    except Exception as e:
        record("transactions", False, traceback.format_exc()[-400:])

    try:
        r = client.get("/api/transactions", headers=headers, params={"search": "selftest"})
        data = r.json() if r.status_code == 200 else {}
        items = data.get("items", []) if isinstance(data, dict) else []
        record("GET /api/transactions", r.status_code == 200 and len(items) >= 1, f"count={len(items)}")
        tx_id = items[0]["id"] if items else None
    except Exception as e:
        record("GET /api/transactions", False, str(e))
        tx_id = None

    # reverse latest selftest tx
    try:
        if tx_id:
            r = client.post(f"/api/transactions/{tx_id}/reverse", headers=headers)
            record("POST /api/transactions/{id}/reverse", r.status_code == 200, r.text[:160])
        else:
            record("POST reverse", False, "no tx id")
    except Exception as e:
        record("POST reverse", False, str(e))

    # --- export ---
    try:
        r = client.get("/api/data/export/inventory", headers=headers)
        ok = r.status_code == 200 and ("name" in r.text or r.content[:3] == b"\xef\xbb\xbf")
        record("GET /api/data/export/inventory", ok, f"bytes={len(r.content)}")
    except Exception as e:
        record("GET /api/data/export/inventory", False, str(e))

    try:
        r = client.get("/api/data/export/transactions", headers=headers)
        record("GET /api/data/export/transactions", r.status_code == 200, f"bytes={len(r.content)}")
    except Exception as e:
        record("GET /api/data/export/transactions", False, str(e))

    # --- import tolerance ---
    try:
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=["name", "reference", "category", "domain", "unit", "current_stock", "min_stock", "location", "cabinet"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "name": "__SELFTEST_IMPORT__",
                "reference": "ST-IMP-001",
                "category": "其他",
                "domain": "其他",
                "unit": "PCS",
                "current_stock": "7.9",
                "min_stock": "1.2",
                "location": "其他",
                "cabinet": "I1",
            }
        )
        writer.writerow(
            {
                "name": "",
                "reference": "BAD",
                "category": "其他",
                "domain": "其他",
                "unit": "PCS",
                "current_stock": "1",
                "min_stock": "0",
                "location": "其他",
                "cabinet": "",
            }
        )
        raw = ("\ufeff" + buf.getvalue()).encode("utf-8")
        r = client.post(
            "/api/data/import/inventory",
            headers=headers,
            files={"file": ("selftest.csv", raw, "text/csv")},
        )
        ok = r.status_code == 200
        body = r.json() if ok else {}
        detail = json.dumps(body, ensure_ascii=False)[:220]
        record(
            "POST /api/data/import/inventory tolerant",
            ok and (body.get("inserted", 0) + body.get("updated", 0)) >= 1,
            detail,
        )

        # verify truncated stock
        r = client.get("/api/inventory", headers=headers, params={"search": "__SELFTEST_IMPORT__"})
        rows = r.json() if r.status_code == 200 else []
        imported = next((x for x in rows if x.get("reference") == "ST-IMP-001"), None)
        record(
            "import decimal truncated",
            imported is not None and imported.get("current_stock") == 7 and imported.get("min_stock") == 1,
            str(imported)[:200] if imported else "not found",
        )
    except Exception as e:
        record("import inventory", False, traceback.format_exc()[-400:])

    # --- sync settings (no remote required) ---
    try:
        r = client.get("/api/sync/settings", headers=headers)
        record("GET /api/sync/settings", r.status_code == 200, r.text[:160])

        r = client.put(
            "/api/sync/settings",
            headers=headers,
            json={
                "host": "127.0.0.1",
                "db_name": "postgres",
                "port": 5432,
                "user": "selftest",
                "password": "selftest",
                "connect_timeout": 3,
                "sslmode": "prefer",
            },
        )
        record("PUT /api/sync/settings", r.status_code == 200, r.text[:160])

        r = client.get("/api/sync/export-default-name", headers=headers)
        record("GET /api/sync/export-default-name", r.status_code == 200, r.text[:160])

        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "postgresql_sync.json")
            r = client.post(
                "/api/sync/export",
                headers=headers,
                json={
                    "settings": {
                        "host": "127.0.0.1",
                        "db_name": "postgres",
                        "port": 5432,
                        "user": "selftest",
                        "password": "selftest",
                        "connect_timeout": 3,
                        "sslmode": "prefer",
                    },
                    "target_path": target,
                },
            )
            record("POST /api/sync/export", r.status_code == 200 and Path(target).is_file(), r.text[:160])

        r = client.post(
            "/api/sync/test",
            headers=headers,
            json={
                "host": "127.0.0.1",
                "db_name": "postgres",
                "port": 5432,
                "user": "selftest",
                "password": "selftest",
                "connect_timeout": 2,
                "sslmode": "prefer",
            },
        )
        # Expect graceful failure (no server) rather than 500
        record(
            "POST /api/sync/test graceful fail",
            r.status_code == 200 and r.json().get("connected") is False,
            r.text[:200],
        )

        # STREAM: NDJSON log lines then done (invalid settings → immediate error stream)
        with client.stream(
            "POST",
            "/api/sync/run",
            headers=headers,
            json={
                "host": "",
                "db_name": "postgres",
                "port": 5432,
                "user": "selftest",
                "password": "selftest",
                "connect_timeout": 2,
                "sslmode": "prefer",
            },
        ) as stream_res:
            body = stream_res.read().decode("utf-8", errors="replace")
            lines = [ln for ln in body.splitlines() if ln.strip()]
            events = []
            for ln in lines:
                try:
                    events.append(json.loads(ln))
                except json.JSONDecodeError:
                    pass
            has_log = any(e.get("type") == "log" for e in events)
            done = next((e for e in events if e.get("type") == "done"), None)
            record(
                "POST /api/sync/run NDJSON stream",
                stream_res.status_code == 200
                and has_log
                and done is not None
                and done.get("success") is False,
                f"lines={len(lines)} done={done}",
            )
    except Exception as e:
        record("sync APIs", False, traceback.format_exc()[-400:])

    # --- batch APIs (docs/test-rules.md BATCH-INV-* / BATCH-TX-*) ---
    batch_ids: list[int] = []
    try:
        for suffix, cab in (("A", "B1"), ("B", "B2")):
            r = client.post(
                "/api/inventory",
                headers=headers,
                json={
                    "name": f"__SELFTEST_BATCH_{suffix}__",
                    "reference": f"ST-BATCH-{suffix}",
                    "category": "其他",
                    "domain": "其他",
                    "unit": "PCS",
                    "current_stock": 10,
                    "min_stock": 2,
                    "location": "其他",
                    "cabinet": cab,
                },
            )
            if r.status_code in (200, 201):
                batch_ids.append(r.json()["id"])
        record("setup batch items", len(batch_ids) == 2, f"ids={batch_ids}")
    except Exception as e:
        record("setup batch items", False, str(e))

    def fetch_items(ids: list[int]) -> dict[int, dict]:
        out: dict[int, dict] = {}
        for iid in ids:
            resp = client.get(f"/api/inventory/{iid}", headers=headers)
            if resp.status_code == 200:
                out[iid] = resp.json()
        return out

    if len(batch_ids) == 2:
        # BATCH-INV-01: 仅更新 location，其他字段不变
        try:
            before = fetch_items(batch_ids)
            r = client.patch(
                "/api/inventory/batch",
                headers=headers,
                json={"ids": batch_ids, "location": "__BATCH_LOC__"},
            )
            after = fetch_items(batch_ids)
            ok = (
                r.status_code == 200
                and r.json().get("updated") == 2
                and all(after[i]["location"] == "__BATCH_LOC__" for i in batch_ids)
                and all(after[i]["cabinet"] == before[i]["cabinet"] for i in batch_ids)
                and all(after[i]["min_stock"] == before[i]["min_stock"] for i in batch_ids)
            )
            record("BATCH-INV-01 patch location only", ok, r.text[:160])
        except Exception:
            record("BATCH-INV-01 patch location only", False, traceback.format_exc()[-300:])

        # BATCH-INV-02: 仅更新 min_stock，current_stock 不变
        try:
            r = client.patch(
                "/api/inventory/batch",
                headers=headers,
                json={"ids": batch_ids, "min_stock": 9},
            )
            after = fetch_items(batch_ids)
            ok = (
                r.status_code == 200
                and r.json().get("updated") == 2
                and all(after[i]["min_stock"] == 9 for i in batch_ids)
                and all(after[i]["current_stock"] == 10 for i in batch_ids)
            )
            record("BATCH-INV-02 patch min_stock only", ok, r.text[:160])
        except Exception:
            record("BATCH-INV-02 patch min_stock only", False, traceback.format_exc()[-300:])

        # BATCH-INV-03: 含无效 id 时跳过不报错
        try:
            r = client.patch(
                "/api/inventory/batch",
                headers=headers,
                json={"ids": [99999999, batch_ids[0]], "cabinet": "__B__"},
            )
            ok = r.status_code == 200 and r.json().get("updated") == 1
            record("BATCH-INV-03 invalid id skipped", ok, r.text[:160])
        except Exception:
            record("BATCH-INV-03 invalid id skipped", False, traceback.format_exc()[-300:])

        # BATCH-TX-01: 批量入库
        try:
            r = client.post(
                "/api/transactions/batch",
                headers=headers,
                json={
                    "type": "IN",
                    "recipient_source": "__BATCH_SRC__",
                    "items": [
                        {"item_id": batch_ids[0], "quantity": 3, "project_ref": ""},
                        {"item_id": batch_ids[1], "quantity": 4, "project_ref": ""},
                    ],
                },
            )
            after = fetch_items(batch_ids)
            ok = (
                r.status_code == 200
                and r.json().get("successful_count") == 2
                and after[batch_ids[0]]["current_stock"] == 13
                and after[batch_ids[1]]["current_stock"] == 14
            )
            record("BATCH-TX-01 batch IN", ok, r.text[:160])
        except Exception:
            record("BATCH-TX-01 batch IN", False, traceback.format_exc()[-300:])

        # BATCH-TX-02: 批量出库
        try:
            r = client.post(
                "/api/transactions/batch",
                headers=headers,
                json={
                    "type": "OUT",
                    "recipient_source": "__BATCH_RCV__",
                    "items": [
                        {"item_id": batch_ids[0], "quantity": 3, "project_ref": "ST-PROJ"},
                        {"item_id": batch_ids[1], "quantity": 4, "project_ref": "ST-PROJ"},
                    ],
                },
            )
            after = fetch_items(batch_ids)
            ok = (
                r.status_code == 200
                and r.json().get("successful_count") == 2
                and after[batch_ids[0]]["current_stock"] == 10
                and after[batch_ids[1]]["current_stock"] == 10
            )
            record("BATCH-TX-02 batch OUT", ok, r.text[:160])
        except Exception:
            record("BATCH-TX-02 batch OUT", False, traceback.format_exc()[-300:])

        # BATCH-TX-03: 库存不足 → 400 且整批回滚
        try:
            r = client.post(
                "/api/transactions/batch",
                headers=headers,
                json={
                    "type": "OUT",
                    "recipient_source": "__BATCH_RCV__",
                    "items": [
                        {"item_id": batch_ids[0], "quantity": 99999, "project_ref": ""},
                        {"item_id": batch_ids[1], "quantity": 1, "project_ref": ""},
                    ],
                },
            )
            after = fetch_items(batch_ids)
            ok = (
                r.status_code == 400
                and after[batch_ids[0]]["current_stock"] == 10
                and after[batch_ids[1]]["current_stock"] == 10
            )
            record("BATCH-TX-03 insufficient stock rollback", ok, f"status={r.status_code}")
        except Exception:
            record("BATCH-TX-03 insufficient stock rollback", False, traceback.format_exc()[-300:])

        # BATCH-TX-04: 缺共享来源/接收人 → 422
        try:
            r = client.post(
                "/api/transactions/batch",
                headers=headers,
                json={
                    "type": "IN",
                    "recipient_source": "",
                    "items": [{"item_id": batch_ids[0], "quantity": 1, "project_ref": ""}],
                },
            )
            record("BATCH-TX-04 empty recipient rejected", r.status_code == 422, f"status={r.status_code}")
        except Exception:
            record("BATCH-TX-04 empty recipient rejected", False, traceback.format_exc()[-300:])
    else:
        for case in (
            "BATCH-INV-01 patch location only",
            "BATCH-INV-02 patch min_stock only",
            "BATCH-INV-03 invalid id skipped",
            "BATCH-TX-01 batch IN",
            "BATCH-TX-02 batch OUT",
            "BATCH-TX-03 insufficient stock rollback",
            "BATCH-TX-04 empty recipient rejected",
        ):
            record(case, False, "setup failed")

    # --- cleanup inventory test rows ---
    try:
        r = client.get("/api/inventory", headers=headers)
        rows = r.json() if r.status_code == 200 else []
        ids = [i["id"] for i in rows if str(i.get("name", "")).startswith("__SELFTEST")]
        if ids:
            r = client.request("DELETE", "/api/inventory/batch", headers=headers, json={"ids": ids})
            record("DELETE /api/inventory/batch cleanup", r.status_code == 200, r.text[:160])
        else:
            record("DELETE cleanup", True, "nothing to clean")
    except Exception as e:
        record("DELETE cleanup", False, str(e))

    # summary
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    print("\n========== SUMMARY ==========")
    print(f"passed={passed} failed={failed} total={len(results)}")
    if failed:
        print("Failed cases:")
        for name, ok, detail in results:
            if not ok:
                print(f"  - {name}: {detail}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

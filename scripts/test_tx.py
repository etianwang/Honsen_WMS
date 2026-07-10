"""Quick transaction smoke test (no HTTP)."""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import db_manager  # noqa: E402

DB = str(ROOT / "db" / "honsen_storage.db")


def main() -> None:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT sql FROM sqlite_master WHERE name='transactions'")
    row = cur.fetchone()
    print("schema:", row[0] if row else None)
    cur.execute("SELECT id, current_stock FROM Inventory LIMIT 3")
    items = cur.fetchall()
    print("items:", items)
    conn.close()

    for iid, stock in items[:2]:
        ok_in = db_manager.record_transaction(
            DB, iid, "2026-07-10 12:00:00", "IN", 1, "SRC-01", ""
        )
        ok_out = (
            db_manager.record_transaction(
                DB, iid, "2026-07-10 12:01:00", "OUT", 1, "user", "proj"
            )
            if stock >= 1
            else None
        )
        print(f"item {iid}: IN={ok_in}, OUT={ok_out}")


if __name__ == "__main__":
    main()

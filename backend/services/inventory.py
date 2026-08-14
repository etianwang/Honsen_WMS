from backend.services import db as db_service
import db_manager


def stock_status(current_stock: int, min_stock: int) -> str:
    """库存三色状态：缺货 / 预警 / 正常（弘盛仓管业务规则）"""
    if current_stock <= 0:
        return "缺货"
    if current_stock <= min_stock:
        return "预警"
    return "正常"


def list_inventory(
    search: str | None = None,
    category: str | None = None,
    domain: str | None = None,
    location: str | None = None,
) -> list[dict]:
    items = db_manager.get_all_Inventory(db_service.DB_PATH)
    result = []
    for row in items:
        if category and category != "ALL" and row.get("category") != category:
            continue
        if domain and domain != "ALL" and row.get("domain") != domain:
            continue
        if location and location != "ALL" and row.get("location") != location:
            continue
        if search:
            needle = search.lower()
            haystack = " ".join(
                str(row.get(k, "")) for k in ("name", "reference", "cabinet", "location")
            ).lower()
            if needle not in haystack:
                continue
        row = dict(row)
        row["status"] = stock_status(row.get("current_stock", 0), row.get("min_stock", 0))
        result.append(row)
    return result


def get_inventory(item_id: int) -> dict | None:
    row = db_manager.get_Inventory_item_by_id(db_service.DB_PATH, item_id)
    if not row:
        return None
    data = dict(row)
    data["status"] = stock_status(data.get("current_stock", 0), data.get("min_stock", 0))
    return data

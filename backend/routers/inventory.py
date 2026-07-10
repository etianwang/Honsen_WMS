import db_manager
from fastapi import APIRouter, Depends

from backend.auth_jwt import get_current_user
from backend.exceptions import bad_request, conflict, not_found
from backend.schemas.inventory import (
    InventoryBatchDelete,
    InventoryBatchUpdate,
    InventoryCreate,
    InventoryItem,
    InventoryUpdate,
)
from backend.services import db as db_service
from backend.services import inventory as inventory_service

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("", response_model=list[InventoryItem])
def list_items(
    search: str | None = None,
    category: str | None = None,
    domain: str | None = None,
    location: str | None = None,
    _: str = Depends(get_current_user),
) -> list[InventoryItem]:
    rows = inventory_service.list_inventory(search, category, domain, location)
    return [InventoryItem(**row) for row in rows]


@router.get("/{item_id}", response_model=InventoryItem)
def get_item(item_id: int, _: str = Depends(get_current_user)) -> InventoryItem:
    row = inventory_service.get_inventory(item_id)
    if not row:
        raise not_found("物品不存在")
    return InventoryItem(**row)


@router.post("", response_model=InventoryItem, status_code=201)
def create_item(body: InventoryCreate, _: str = Depends(get_current_user)) -> InventoryItem:
    new_id = db_manager.insert_Inventory_item(
        db_service.DB_PATH,
        body.name,
        body.reference,
        body.category,
        body.domain,
        body.unit,
        body.current_stock,
        body.min_stock,
        body.location,
        body.cabinet,
    )
    if new_id is None:
        raise conflict("已存在相同名称/型号/位置/柜号的记录")
    row = inventory_service.get_inventory(new_id)
    return InventoryItem(**row)


@router.put("/{item_id}", response_model=InventoryItem)
def update_item(
    item_id: int,
    body: InventoryUpdate,
    _: str = Depends(get_current_user),
) -> InventoryItem:
    if not inventory_service.get_inventory(item_id):
        raise not_found("物品不存在")
    ok = db_manager.update_Inventory_item(
        db_service.DB_PATH,
        item_id,
        body.name,
        body.reference,
        body.category,
        body.domain,
        body.unit,
        body.min_stock,
        body.location,
        body.cabinet,
    )
    if not ok:
        raise bad_request("更新失败")
    return InventoryItem(**inventory_service.get_inventory(item_id))


@router.patch("/batch")
def batch_update(body: InventoryBatchUpdate, _: str = Depends(get_current_user)) -> dict:
    updated = 0
    for item_id in body.ids:
        row = inventory_service.get_inventory(item_id)
        if not row:
            continue
        ok = db_manager.update_Inventory_item(
            db_service.DB_PATH,
            item_id,
            row["name"],
            row["reference"],
            body.category if body.category is not None else row.get("category") or "其他",
            body.domain if body.domain is not None else row.get("domain") or "其他",
            body.unit if body.unit is not None else row.get("unit") or "",
            body.min_stock if body.min_stock is not None else row.get("min_stock", 0),
            body.location if body.location is not None else row.get("location") or "",
            body.cabinet if body.cabinet is not None else row.get("cabinet") or "",
        )
        if ok:
            updated += 1
    return {"updated": updated}


@router.delete("/batch")
def batch_delete(body: InventoryBatchDelete, _: str = Depends(get_current_user)) -> dict:
    deleted = 0
    for item_id in body.ids:
        if db_manager.delete_Inventory_item(db_service.DB_PATH, item_id):
            deleted += 1
    return {"deleted": deleted}


@router.delete("/{item_id}")
def delete_item(item_id: int, _: str = Depends(get_current_user)) -> dict:
    if not db_manager.delete_Inventory_item(db_service.DB_PATH, item_id):
        raise not_found("物品不存在或删除失败")
    return {"message": "已删除"}


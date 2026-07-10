from datetime import datetime

import db_manager
from fastapi import APIRouter, Depends, Query

from backend.auth_jwt import get_current_user
from backend.exceptions import bad_request, not_found
from backend.schemas.transaction import (
    TransactionBatchCreate,
    TransactionCreate,
    TransactionItem,
    TransactionListResponse,
    TransactionStats,
    TransactionUpdate,
)
from backend.services import db as db_service
from backend.services import inventory as inventory_service
from backend.services import transaction as transaction_service

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    start_date: str | None = None,
    end_date: str | None = None,
    type: str | None = Query(None, alias="type"),
    search: str | None = None,
    category: str | None = None,
    domain: str | None = None,
    location: str | None = None,
    project: str | None = None,
    _: str = Depends(get_current_user),
) -> TransactionListResponse:
    rows = transaction_service.list_transactions(
        start_date, end_date, type, search, category, location, project, domain
    )
    stats = transaction_service.compute_stats(rows)
    return TransactionListResponse(
        items=[TransactionItem(**row) for row in rows],
        stats=TransactionStats(**stats),
    )


@router.get("/{tx_id}", response_model=TransactionItem)
def get_transaction(tx_id: int, _: str = Depends(get_current_user)) -> TransactionItem:
    row = db_manager.get_transaction_by_id(db_service.DB_PATH, tx_id)
    if not row:
        raise not_found("交易记录不存在")
    return TransactionItem(**dict(row))


@router.post("", response_model=dict, status_code=201)
def create_transaction(body: TransactionCreate, _: str = Depends(get_current_user)) -> dict:
    item = inventory_service.get_inventory(body.item_id)
    if not item:
        raise bad_request("物品不存在，请刷新列表后重试")

    if body.type == "OUT" and item["current_stock"] < body.quantity:
        raise bad_request(
            f"库存不足：当前库存 {item['current_stock']}，出库数量 {body.quantity}"
        )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ok = db_manager.record_transaction(
        db_service.DB_PATH,
        body.item_id,
        now,
        body.type,
        body.quantity,
        body.recipient_source,
        body.project_ref,
    )
    if not ok:
        raise bad_request("交易失败，请确认物品存在且出库数量不超过库存")
    return {"message": "交易已记录"}


@router.post("/batch")
def create_batch_transactions(
    body: TransactionBatchCreate,
    _: str = Depends(get_current_user),
) -> dict:
    payload = [
        {"item_id": item.item_id, "quantity": item.quantity, "project_ref": item.project_ref}
        for item in body.items
    ]
    result = db_manager.batch_record_transactions(
        db_service.DB_PATH,
        body.type,
        body.recipient_source,
        payload,
    )
    if result["failed_transactions"]:
        raise bad_request("批量交易失败，可能库存不足")
    return {"successful_count": result["successful_count"]}


@router.put("/{tx_id}")
def update_transaction(
    tx_id: int,
    body: TransactionUpdate,
    _: str = Depends(get_current_user),
) -> dict:
    ok = db_manager.update_transaction(
        db_service.DB_PATH,
        tx_id,
        body.quantity,
        body.date,
        body.recipient_source,
        body.project_ref,
    )
    if not ok:
        raise bad_request("更新失败，可能为冲销记录或库存不足")
    return {"message": "已更新"}


@router.post("/{tx_id}/reverse")
def reverse_transaction(tx_id: int, _: str = Depends(get_current_user)) -> dict:
    if not db_manager.reverse_transaction(db_service.DB_PATH, tx_id):
        raise bad_request("冲销失败")
    return {"message": "已冲销"}


@router.delete("/{tx_id}")
def delete_transaction(tx_id: int, _: str = Depends(get_current_user)) -> dict:
    if not db_manager.delete_transaction(db_service.DB_PATH, tx_id):
        raise bad_request("删除失败，可能为冲销记录或会导致负库存")
    return {"message": "已删除"}

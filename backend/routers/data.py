import csv
import io
from datetime import datetime

import data_utility
import db_manager
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse

from backend.auth_jwt import get_current_user
from backend.exceptions import bad_request
from backend.services import db as db_service

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/export/inventory")
def export_inventory(_: str = Depends(get_current_user)) -> StreamingResponse:
    rows = db_manager.get_Inventory_for_export(db_service.DB_PATH)
    buffer = io.StringIO()
    headers = ["name", "reference", "category", "domain", "unit", "current_stock", "min_stock", "location", "cabinet"]
    writer = csv.DictWriter(buffer, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    content = "\ufeff" + buffer.getvalue()
    filename = f"inventory_export_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/transactions")
def export_transactions(_: str = Depends(get_current_user)) -> StreamingResponse:
    rows = db_manager.get_transactions_for_export(db_service.DB_PATH)
    buffer = io.StringIO()
    headers = ["date", "type", "quantity", "recipient_source", "project_ref", "item_name", "item_reference", "item_domain"]
    writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    content = "\ufeff" + buffer.getvalue()
    filename = f"transactions_export_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import/inventory")
async def import_inventory(
    file: UploadFile = File(...),
    _: str = Depends(get_current_user),
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise bad_request("请上传 CSV 文件")

    raw = await file.read()
    text = None
    for encoding in ("utf-8-sig", "gbk", "utf-8"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise bad_request("无法识别文件编码")

    reader = csv.DictReader(io.StringIO(text))
    items = [dict(row) for row in reader]
    if not items:
        raise bad_request("文件为空")

    row_errors: list[str] = []
    if hasattr(data_utility, "validate_inventory_data"):
        items, row_errors = data_utility.validate_inventory_data(items)

    if not items:
        detail = "; ".join(row_errors[:5]) if row_errors else "没有可导入的有效行"
        raise bad_request(detail)

    stats = db_manager.batch_import_Inventory(db_service.DB_PATH, items)
    return {
        **stats,
        "skipped": len(row_errors),
        "errors": row_errors[:20],
    }

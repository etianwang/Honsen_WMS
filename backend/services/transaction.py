from backend.services import db as db_service
import db_manager


def list_transactions(
    start_date: str | None = None,
    end_date: str | None = None,
    tx_type: str | None = None,
    search: str | None = None,
    category: str | None = None,
    location: str | None = None,
    project: str | None = None,
    domain: str | None = None,
) -> list[dict]:
    if tx_type == "REVERSAL-*":
        rows = db_manager.get_transactions_history(
            db_service.DB_PATH,
            start_date=start_date,
            end_date=end_date,
            tx_type=None,
            item_search=search,
            category=category if category and category != "ALL" else None,
            location=location if location and location != "ALL" else None,
            project=project if project and project != "ALL" else None,
            domain=domain if domain and domain != "ALL" else None,
        )
        return [dict(r) for r in rows if str(r.get("type", "")).startswith("REVERSAL")]

    return [
        dict(r)
        for r in db_manager.get_transactions_history(
            db_service.DB_PATH,
            start_date=start_date,
            end_date=end_date,
            tx_type=tx_type if tx_type and tx_type != "ALL" else None,
            item_search=search,
            category=category if category and category != "ALL" else None,
            location=location if location and location != "ALL" else None,
            project=project if project and project != "ALL" else None,
            domain=domain if domain and domain != "ALL" else None,
        )
    ]


def compute_stats(rows: list[dict]) -> dict:
    domains = {r.get("domain") for r in rows if r.get("domain")}
    locations = {r.get("location") for r in rows if r.get("location")}
    projects = {r.get("project_ref") for r in rows if r.get("project_ref")}
    total_in = sum(r.get("quantity", 0) for r in rows if r.get("type") == "IN")
    total_out = sum(r.get("quantity", 0) for r in rows if r.get("type") == "OUT")
    return {
        "total": len(rows),
        "total_in_qty": total_in,
        "total_out_qty": total_out,
        "unique_domains": len(domains),
        "unique_locations": len(locations),
        "unique_projects": len(projects),
    }

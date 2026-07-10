from backend.services import db as db_service
import db_manager

CONFIG_CATEGORIES = ("LOCATION", "PROJECT", "UNIT", "CATEGORY", "DOMAIN")


def get_all_config() -> dict[str, list[str]]:
    return {
        category: db_manager.get_config_options(db_service.DB_PATH, category)
        for category in CONFIG_CATEGORIES
    }

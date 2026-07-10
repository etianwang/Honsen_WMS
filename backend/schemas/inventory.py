from pydantic import BaseModel, Field


class InventoryItem(BaseModel):
    id: int
    name: str
    reference: str
    category: str | None = None
    domain: str | None = None
    unit: str | None = None
    current_stock: int
    min_stock: int
    location: str | None = None
    cabinet: str | None = None
    status: str | None = None


class InventoryCreate(BaseModel):
    name: str = Field(min_length=1)
    reference: str = Field(min_length=1)
    category: str = "其他"
    domain: str = "其他"
    unit: str = ""
    current_stock: int = 0
    min_stock: int = 0
    location: str = ""
    cabinet: str = ""


class InventoryUpdate(BaseModel):
    name: str = Field(min_length=1)
    reference: str = Field(min_length=1)
    category: str = "其他"
    domain: str = "其他"
    unit: str = ""
    min_stock: int = 0
    location: str = ""
    cabinet: str = ""


class InventoryBatchUpdate(BaseModel):
    ids: list[int] = Field(min_length=1)
    category: str | None = None
    domain: str | None = None
    unit: str | None = None
    min_stock: int | None = None
    location: str | None = None
    cabinet: str | None = None


class InventoryBatchDelete(BaseModel):
    ids: list[int] = Field(min_length=1)

from pydantic import BaseModel, Field, model_validator


class TransactionItem(BaseModel):
    id: int
    date: str
    type: str
    quantity: int
    recipient_source: str | None = None
    project_ref: str | None = None
    item_id: int
    item_name: str | None = None
    item_ref: str | None = None
    location: str | None = None
    category: str | None = None
    domain: str | None = None
    cabinet: str | None = None


class TransactionCreate(BaseModel):
    item_id: int = Field(gt=0)
    type: str = Field(pattern=r"^(IN|OUT)$")
    quantity: int = Field(gt=0)
    recipient_source: str = Field(
        default="",
        description="入库(IN)：来源柜号，必填；出库(OUT)：接收人，必填",
    )
    project_ref: str = ""

    @model_validator(mode="after")
    def validate_recipient_source(self) -> "TransactionCreate":
        if not self.recipient_source.strip():
            label = "来源柜号" if self.type == "IN" else "接收人"
            raise ValueError(f"{label}不能为空")
        return self


class TransactionBatchItem(BaseModel):
    item_id: int
    quantity: int = Field(gt=0)
    project_ref: str = ""


class TransactionBatchCreate(BaseModel):
    type: str = Field(pattern=r"^(IN|OUT)$")
    recipient_source: str = Field(
        default="",
        description="入库(IN)：来源柜号，必填；出库(OUT)：接收人，必填",
    )
    items: list[TransactionBatchItem] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_recipient_source(self) -> "TransactionBatchCreate":
        if not self.recipient_source.strip():
            label = "来源柜号" if self.type == "IN" else "接收人"
            raise ValueError(f"{label}不能为空")
        return self


class TransactionUpdate(BaseModel):
    quantity: int = Field(gt=0)
    date: str
    recipient_source: str = ""
    project_ref: str = ""


class TransactionStats(BaseModel):
    total: int
    total_in_qty: int
    total_out_qty: int
    unique_domains: int
    unique_locations: int
    unique_projects: int


class TransactionListResponse(BaseModel):
    items: list[TransactionItem]
    stats: TransactionStats

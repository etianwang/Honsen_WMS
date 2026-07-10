from pydantic import BaseModel, Field


class ConfigValueCreate(BaseModel):
    value: str = Field(min_length=1)


class ConfigMap(BaseModel):
    LOCATION: list[str] = []
    PROJECT: list[str] = []
    UNIT: list[str] = []
    CATEGORY: list[str] = []
    DOMAIN: list[str] = []

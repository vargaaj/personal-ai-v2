from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LoopItemModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    text: str
    id: str
    checked: bool
    section: str | None
    details: str = ""
    link: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LoopSectionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    items: list[LoopItemModel]


class LoopInfoModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    path: str
    exists: bool
    modified_time: float | None
    item_count: int
    open_item_count: int


class LoopContentModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    path: str
    exists: bool
    modified_time: float | None
    last_updated: str | None
    data: dict[str, Any]
    content: str
    sections: list[LoopSectionModel]


class LoopSaveRequest(BaseModel):
    data: dict[str, Any]
    expected_modified_time: float | None = None


class ItemAddRequest(BaseModel):
    section: str
    text: str
    details: str = ""
    link: str = ""
    expected_modified_time: float | None = None


class ItemToggleRequest(BaseModel):
    expected_modified_time: float | None = None

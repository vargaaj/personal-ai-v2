from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .schemas import ItemAddRequest, ItemToggleRequest, LoopContentModel, LoopInfoModel, LoopSaveRequest
from .storage import (
    InvalidLoopDataError,
    ItemAddError,
    ItemToggleError,
    LoopStorage,
    SaveConflictError,
    UnknownLoopError,
)


def create_api_router(storage: LoopStorage) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["loops"])

    @router.get("/loops", response_model=list[LoopInfoModel])
    def list_loops() -> list[LoopInfoModel]:
        return [LoopInfoModel.model_validate(loop) for loop in storage.list_loops()]

    @router.get("/loops/{loop_id}", response_model=LoopContentModel)
    def get_loop(loop_id: str) -> LoopContentModel:
        try:
            return LoopContentModel.model_validate(storage.read_loop(loop_id))
        except UnknownLoopError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except InvalidLoopDataError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.put("/loops/{loop_id}", response_model=LoopContentModel)
    def save_loop(loop_id: str, payload: LoopSaveRequest) -> LoopContentModel:
        try:
            loop = storage.save_loop(loop_id, payload.data, payload.expected_modified_time)
            return LoopContentModel.model_validate(loop)
        except UnknownLoopError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except InvalidLoopDataError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except SaveConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.patch("/loops/{loop_id}/items/{item_id}", response_model=LoopContentModel)
    def toggle_item(loop_id: str, item_id: str, payload: ItemToggleRequest | None = None) -> LoopContentModel:
        expected_modified_time = payload.expected_modified_time if payload else None
        try:
            loop = storage.toggle_item(loop_id, item_id, expected_modified_time)
            return LoopContentModel.model_validate(loop)
        except UnknownLoopError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except InvalidLoopDataError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ItemToggleError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except SaveConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.post("/loops/{loop_id}/items", response_model=LoopContentModel)
    def add_item(loop_id: str, payload: ItemAddRequest) -> LoopContentModel:
        try:
            loop = storage.add_item(
                loop_id,
                payload.section,
                payload.text,
                payload.details,
                payload.link,
                payload.expected_modified_time,
            )
            return LoopContentModel.model_validate(loop)
        except UnknownLoopError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (InvalidLoopDataError, ItemAddError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except SaveConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return router

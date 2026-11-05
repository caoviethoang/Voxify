"""Routes quản lý từ điển phát âm cá nhân."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas.dictionary import (
    DictionaryRuleCreateRequest,
    DictionaryRuleUpdateRequest,
    DictionaryRuleResponse,
)
from app.services.dictionary_service import DictionaryService

router = APIRouter(prefix="/api/dictionary", tags=["dictionary"])


@router.get("", response_model=List[DictionaryRuleResponse], summary="Lấy danh sách từ điển cá nhân")
async def get_dictionary_rules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rules = await DictionaryService.list_rules(db, current_user.id)
    return rules


@router.post("", response_model=DictionaryRuleResponse, status_code=status.HTTP_201_CREATED, summary="Thêm quy tắc phát âm mới")
async def create_dictionary_rule(
    data: DictionaryRuleCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        rule = await DictionaryService.create_rule(
            db=db,
            user_id=current_user.id,
            word=data.word,
            replacement=data.replacement,
            category=data.category or "custom",
        )
        return rule
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{rule_id}", response_model=DictionaryRuleResponse, summary="Cập nhật quy tắc phát âm")
async def update_dictionary_rule(
    rule_id: int,
    data: DictionaryRuleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rules = await DictionaryService.list_rules(db, current_user.id)
    target = next((r for r in rules if r.id == rule_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Không tìm thấy quy tắc phát âm")

    if data.replacement is not None:
        target.replacement = data.replacement.strip()
    if data.category is not None:
        target.category = data.category
    if data.is_active is not None:
        target.is_active = data.is_active

    await db.commit()
    await db.refresh(target)
    return target


@router.delete("/{rule_id}", summary="Xóa quy tắc phát âm")
async def delete_dictionary_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await DictionaryService.delete_rule(db, current_user.id, rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy quy tắc phát âm")
    return {"message": "Đã xóa quy tắc phát âm"}

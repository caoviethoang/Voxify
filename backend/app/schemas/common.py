"""Common schemas dùng chung cho API."""
from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic schema chuẩn cho dữ liệu trả về có phân trang."""

    items: List[T] = Field(default_factory=list, description="Danh sách bản ghi của trang hiện tại")
    total: int = Field(..., ge=0, description="Tổng số bản ghi")
    page: int = Field(1, ge=1, description="Trang hiện tại")
    limit: int = Field(10, ge=1, description="Số bản ghi mỗi trang")
    total_pages: int = Field(..., ge=0, description="Tổng số trang")

    @classmethod
    def create(cls, items: List[T], total: int, page: int, limit: int) -> "PaginatedResponse[T]":
        """Helper tính toán total_pages tự động và khởi tạo schema."""
        total_pages = (total + limit - 1) // limit if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
        )

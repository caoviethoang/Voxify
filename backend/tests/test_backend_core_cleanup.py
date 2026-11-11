"""Unit tests cho các cải tiến refactor core backend (Issue #43)."""
from unittest.mock import MagicMock

from fastapi import Request
from pydantic import BaseModel
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.security import get_client_ip
from app.db import Base, CreatedAtMixin, TimestampMixin
from app.schemas.common import PaginatedResponse


# Dummy models để kiểm thử Mixin
class DummyTimestampModel(Base, TimestampMixin):
    __tablename__ = "dummy_timestamp_models"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), default="test")


class DummyCreatedAtModel(Base, CreatedAtMixin):
    __tablename__ = "dummy_created_at_models"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)


class DummyItem(BaseModel):
    id: int
    name: str


def test_timestamp_mixin_attributes():
    """Kiểm tra TimestampMixin cung cấp đúng created_at và updated_at."""
    model = DummyTimestampModel()
    assert hasattr(model, "created_at")
    assert hasattr(model, "updated_at")


def test_created_at_mixin_attributes():
    """Kiểm tra CreatedAtMixin cung cấp created_at và không có updated_at."""
    model = DummyCreatedAtModel()
    assert hasattr(model, "created_at")
    assert not hasattr(model, "updated_at")


def test_get_client_ip_direct():
    """Kiểm tra trích xuất IP trực tiếp từ client.host."""
    request = MagicMock(spec=Request)
    request.headers = {}
    request.client = MagicMock()
    request.client.host = "192.168.1.10"

    assert get_client_ip(request) == "192.168.1.10"


def test_get_client_ip_forwarded_single():
    """Kiểm tra trích xuất IP từ header x-forwarded-for đơn."""
    request = MagicMock(spec=Request)
    request.headers = {"x-forwarded-for": "203.0.113.195"}
    request.client = MagicMock()
    request.client.host = "10.0.0.1"

    assert get_client_ip(request) == "203.0.113.195"


def test_get_client_ip_forwarded_multiple():
    """Kiểm tra trích xuất client IP đầu tiên từ chuỗi nhiều proxy x-forwarded-for."""
    request = MagicMock(spec=Request)
    request.headers = {"x-forwarded-for": "203.0.113.195, 70.41.3.18, 150.172.238.178"}
    request.client = MagicMock()
    request.client.host = "10.0.0.1"

    assert get_client_ip(request) == "203.0.113.195"


def test_get_client_ip_fallback():
    """Kiểm tra fallback khi không có client và header."""
    request = MagicMock(spec=Request)
    request.headers = {}
    request.client = None

    assert get_client_ip(request) == "127.0.0.1"
    assert get_client_ip(request, default="unknown") == "unknown"


def test_paginated_response_create():
    """Kiểm tra generic PaginatedResponse và helper method create."""
    items = [
        DummyItem(id=1, name="Item 1"),
        DummyItem(id=2, name="Item 2"),
    ]
    resp = PaginatedResponse.create(items=items, total=15, page=1, limit=5)

    assert resp.items == items
    assert resp.total == 15
    assert resp.page == 1
    assert resp.limit == 5
    assert resp.total_pages == 3


def test_paginated_response_empty():
    """Kiểm tra PaginatedResponse khi không có dữ liệu."""
    resp = PaginatedResponse[DummyItem].create(items=[], total=0, page=1, limit=10)
    assert resp.items == []
    assert resp.total == 0
    assert resp.total_pages == 0

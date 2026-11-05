"""Pytest configuration and global fixtures."""
import asyncio
import pytest
from app.db import create_tables


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Đảm bảo bảng và các cột SQLite được khởi tạo và migrate đầy đủ trước khi chạy test."""
    loop = asyncio.new_event_loop()
    loop.run_until_complete(create_tables())
    loop.close()

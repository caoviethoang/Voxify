"""Khung Công cụ Âm thanh (Audio Tools Framework) — Issue #20 / Prompt 19."""
from app.audio_tools.base import (
    CATEGORY_METADATA,
    AudioTool,
    AudioToolCategory,
    AudioToolRegistry,
    registry,
)
from app.audio_tools.builtin import register_builtin_tools

# Tự động nạp các công cụ tích hợp sẵn khi import package
register_builtin_tools()

__all__ = [
    "AudioTool",
    "AudioToolCategory",
    "AudioToolRegistry",
    "CATEGORY_METADATA",
    "registry",
]

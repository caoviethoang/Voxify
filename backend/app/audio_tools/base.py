"""Nền tảng Công cụ Âm thanh (Audio Tools Framework) — Issue #20 / Prompt 19."""
from __future__ import annotations

import abc
import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from app.services.audio_service import AudioService

logger = logging.getLogger(__name__)


class AudioToolCategory:
    """Các nhóm danh mục công cụ âm thanh theo đặc tả Prompt 19."""
    TRIM_CUT = "trim_cut"                  # Cắt & ghép
    VOLUME_DYNAMICS = "volume_dynamics"    # Âm lượng & động học
    EFFECTS = "effects"                    # Hiệu ứng
    CLEANUP = "cleanup"                    # Làm sạch
    AI_SEPARATION = "ai_separation"        # Tách âm AI
    FORMAT_CONVERSION = "format_conversion"# Chuyển đổi định dạng
    RECORDER = "recorder"                  # Ghi âm


CATEGORY_METADATA = {
    AudioToolCategory.TRIM_CUT: {
        "name_vi": "Cắt & ghép",
        "name_en": "Trim & Cut",
        "icon": "Scissors",
        "order": 1,
    },
    AudioToolCategory.VOLUME_DYNAMICS: {
        "name_vi": "Âm lượng & động học",
        "name_en": "Volume & Dynamics",
        "icon": "Volume2",
        "order": 2,
    },
    AudioToolCategory.EFFECTS: {
        "name_vi": "Hiệu ứng",
        "name_en": "Effects",
        "icon": "Sliders",
        "order": 3,
    },
    AudioToolCategory.CLEANUP: {
        "name_vi": "Làm sạch",
        "name_en": "Cleanup",
        "icon": "Sparkles",
        "order": 4,
    },
    AudioToolCategory.AI_SEPARATION: {
        "name_vi": "Tách âm AI",
        "name_en": "AI Separation",
        "icon": "Radio",
        "order": 5,
    },
    AudioToolCategory.FORMAT_CONVERSION: {
        "name_vi": "Chuyển đổi định dạng",
        "name_en": "Format Conversion",
        "icon": "FileAudio",
        "order": 6,
    },
    AudioToolCategory.RECORDER: {
        "name_vi": "Ghi âm",
        "name_en": "Recorder",
        "icon": "Mic",
        "order": 7,
    },
}


class AudioTool(abc.ABC):
    """
    Lớp cơ sở cho mọi công cụ âm thanh.
    Để thêm một công cụ mới, chỉ cần kế thừa lớp này và định nghĩa:
    - id, name_vi, name_en, category, icon
    - params_schema: JSON Schema cấu hình form điều khiển trên frontend
    - cost: credit/phút hoặc miễn phí
    - run(input_path, params, output_path, progress_cb) -> kết quả
    """
    id: str
    name_vi: str
    name_en: str
    description_vi: str
    description_en: str
    category: str
    icon: str
    params_schema: Dict[str, Any]
    cost: Dict[str, Any] = {"type": "free"}
    heavy: bool = False

    @abc.abstractmethod
    async def run(
        self,
        input_path: str,
        params: Dict[str, Any],
        output_path: str,
        progress_cb: Optional[Callable[[int], Awaitable[None]]] = None,
    ) -> Dict[str, Any]:
        """
        Thực thi xử lý âm thanh.
        Trả về dict:
        {
            "output_path": str,
            "output_filename": str,
            "duration": float,
            "size_bytes": int,
            "extra": dict (tùy chọn)
        }
        """
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        """Xuất thông tin công cụ ra dictionary phục vụ API và frontend."""
        cat_meta = CATEGORY_METADATA.get(self.category, {})
        return {
            "id": self.id,
            "name_vi": self.name_vi,
            "name_en": self.name_en,
            "description_vi": self.description_vi,
            "description_en": self.description_en,
            "category": self.category,
            "category_name_vi": cat_meta.get("name_vi", self.category),
            "category_name_en": cat_meta.get("name_en", self.category),
            "icon": self.icon,
            "params_schema": self.params_schema,
            "cost": self.cost,
            "heavy": self.heavy,
        }

    async def _safe_copy_fallback(self, input_path: str, output_path: str) -> None:
        """Helper fallback nếu ffmpeg không khả dụng trong môi trường test."""
        if os.path.exists(input_path):
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            shutil.copy2(input_path, output_path)

    async def run_ffmpeg_command(
        self,
        cmd: List[str],
        input_path: str,
        output_path: str,
        tool_name: str,
    ) -> bool:
        """
        Thực thi tiến trình ffmpeg với logging lỗi chi tiết và fallback an toàn.
        Trả về True nếu lệnh hoàn thành thành công (returncode == 0), ngược lại False.
        """
        success = False
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode == 0:
                success = True
            else:
                logger.warning(
                    f"ffmpeg {tool_name} thất bại: {stderr.decode('utf-8', errors='ignore')}"
                )
        except Exception as e:
            logger.warning(f"Không thể chạy ffmpeg cho {tool_name}: {e}")

        if not success:
            await self._safe_copy_fallback(input_path, output_path)

        return success

    def build_tool_result(
        self,
        output_path: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Đo đạc thời lượng âm thanh, kích thước file và đóng gói kết quả chuẩn.
        """
        measured_duration = AudioService.measure_duration(output_path)
        size_bytes = os.path.getsize(output_path) if os.path.exists(output_path) else 0

        return {
            "output_path": output_path,
            "output_filename": Path(output_path).name,
            "duration": round(measured_duration, 2),
            "size_bytes": size_bytes,
            "extra": extra or {},
        }


class AudioToolRegistry:
    """Kho lưu trữ và đăng ký tập trung cho mọi công cụ âm thanh."""

    def __init__(self) -> None:
        self._tools: Dict[str, AudioTool] = {}

    def register(self, tool: AudioTool) -> None:
        """Đăng ký một công cụ âm thanh vào hệ thống."""
        self._tools[tool.id] = tool

    def get(self, tool_id: str) -> Optional[AudioTool]:
        """Lấy một công cụ theo ID."""
        return self._tools.get(tool_id)

    def list_tools(self) -> List[AudioTool]:
        """Lấy toàn bộ danh sách công cụ đã đăng ký."""
        return list(self._tools.values())

    def get_by_category(self) -> Dict[str, Dict[str, Any]]:
        """Nhóm các công cụ theo danh mục để phục vụ Sidebar và Dashboard."""
        grouped: Dict[str, Dict[str, Any]] = {}
        for cat_id, meta in sorted(CATEGORY_METADATA.items(), key=lambda x: int(str(x[1]["order"]))):
            grouped[cat_id] = {
                "category": cat_id,
                "name_vi": meta["name_vi"],
                "name_en": meta["name_en"],
                "icon": meta["icon"],
                "tools": [],
            }

        for tool in self._tools.values():
            cat = tool.category
            if cat not in grouped:
                grouped[cat] = {
                    "category": cat,
                    "name_vi": cat,
                    "name_en": cat,
                    "icon": "Wand2",
                    "tools": [],
                }
            grouped[cat]["tools"].append(tool.to_dict())

        return grouped


# Singleton registry instance
registry = AudioToolRegistry()

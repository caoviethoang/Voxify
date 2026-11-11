"""Tự động đăng ký tất cả các công cụ âm thanh có sẵn vào Registry."""
from app.audio_tools.base import registry
from app.audio_tools.builtin.ai_vocal_remover import AIVocalRemoverTool
from app.audio_tools.builtin.format_converter import FormatConverterTool
from app.audio_tools.builtin.noise_reduction import NoiseReductionTool
from app.audio_tools.builtin.tempo_pitch import TempoPitchTool
from app.audio_tools.builtin.trim import TrimAudioTool
from app.audio_tools.builtin.volume import VolumeNormalizeTool


def register_builtin_tools() -> None:
    """Đăng ký các công cụ âm thanh mặc định."""
    tools = [
        TrimAudioTool(),
        VolumeNormalizeTool(),
        FormatConverterTool(),
        TempoPitchTool(),
        NoiseReductionTool(),
        AIVocalRemoverTool(),
    ]
    for tool in tools:
        registry.register(tool)


__all__ = ["register_builtin_tools"]

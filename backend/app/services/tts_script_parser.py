"""Parser phân tích kịch bản đa giọng ([Voice: Name]) và ngắt nghỉ ([pause Xs])."""
import re
from typing import List, Dict, Any


_PAUSE_REGEX = re.compile(r"\[pause\s*(\d+(?:\.\d+)?)\s*(s|ms)?\]", re.IGNORECASE)
_VOICE_REGEX = re.compile(r"\[Voice:\s*([^\]]+)\]", re.IGNORECASE)


class TTSScriptParser:
    @classmethod
    def parse_script(cls, text: str, default_voice: str) -> List[Dict[str, Any]]:
        """
        Phân tích văn bản thành chuỗi các block hành động:
        - {"type": "speech", "voice": str, "text": str}
        - {"type": "pause", "duration": float}
        """
        clean_text = text.strip()
        if not clean_text:
            return []

        # 1. Phân tách theo thẻ giọng [Voice: ...] nếu có
        voice_matches = list(_VOICE_REGEX.finditer(clean_text))
        if not voice_matches:
            # Chỉ có 1 giọng mặc định
            return cls._parse_pauses(clean_text, default_voice)

        blocks: List[Dict[str, Any]] = []
        current_voice = default_voice
        last_pos = 0

        for match in voice_matches:
            start, end = match.span()
            if start > last_pos:
                segment_text = clean_text[last_pos:start].strip()
                if segment_text:
                    blocks.extend(cls._parse_pauses(segment_text, current_voice))

            # Giọng mới được chỉ định
            specified_voice = match.group(1).strip()
            current_voice = cls._map_voice_alias(specified_voice, default_voice)
            last_pos = end

        if last_pos < len(clean_text):
            segment_text = clean_text[last_pos:].strip()
            if segment_text:
                blocks.extend(cls._parse_pauses(segment_text, current_voice))

        return blocks

    @classmethod
    def _parse_pauses(cls, text: str, voice: str) -> List[Dict[str, Any]]:
        """Tách các đoạn ngắt nghỉ [pause Xs] trong một đoạn văn bản."""
        blocks: List[Dict[str, Any]] = []
        pause_matches = list(_PAUSE_REGEX.finditer(text))
        if not pause_matches:
            if text.strip():
                blocks.append({"type": "speech", "voice": voice, "text": text.strip()})
            return blocks

        last_pos = 0
        for match in pause_matches:
            start, end = match.span()
            if start > last_pos:
                speech_txt = text[last_pos:start].strip()
                if speech_txt:
                    blocks.append({"type": "speech", "voice": voice, "text": speech_txt})

            raw_val = float(match.group(1))
            unit = (match.group(2) or "s").lower()
            duration = raw_val / 1000.0 if unit == "ms" else raw_val
            # Giới hạn an toàn từ 0.1s đến 10s
            duration = max(0.1, min(duration, 10.0))
            blocks.append({"type": "pause", "duration": duration})
            last_pos = end

        if last_pos < len(text):
            speech_txt = text[last_pos:].strip()
            if speech_txt:
                blocks.append({"type": "speech", "voice": voice, "text": speech_txt})

        return blocks

    @staticmethod
    def _map_voice_alias(voice_alias: str, default_voice: str) -> str:
        """Chuyển đổi tên gọi thân thiện sang Voice ID chuẩn."""
        v_low = voice_alias.lower().replace("-", "").replace("_", "").replace(" ", "")
        if "hoaimy" in v_low:
            return "vi-VN-HoaiMyNeural"
        if "namminh" in v_low:
            return "vi-VN-NamMinhNeural"
        return voice_alias if "-" in voice_alias else default_voice

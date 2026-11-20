"""Dịch vụ phân tích cú pháp tệp phụ đề SRT và WebVTT thành danh sách Cue chuẩn hóa."""
import re
from typing import Any, Dict, List, Optional, Tuple


def parse_timestamp_to_seconds(ts_str: str) -> float:
    """
    Chuyển đổi chuỗi mốc thời gian phụ đề sang số giây (float).
    Hỗ trợ cả định dạng SRT (00:01:23,456) và VTT (00:01:23.456 hoặc 01:23.456).
    """
    ts_clean = ts_str.strip().replace(",", ".")
    parts = ts_clean.split(":")

    if len(parts) == 3:
        hours = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
        return round(hours * 3600 + minutes * 60 + seconds, 3)
    elif len(parts) == 2:
        minutes = float(parts[0])
        seconds = float(parts[1])
        return round(minutes * 60 + seconds, 3)
    else:
        return round(float(parts[0]), 3)


def format_seconds_to_timestamp(seconds: float, is_vtt: bool = False) -> str:
    """Chuyển đổi số giây thành định dạng mốc thời gian SRT (00:01:23,456) hoặc VTT (00:01:23.456)."""
    if seconds < 0:
        seconds = 0.0

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        secs += 1
        millis = 0

    sep = "." if is_vtt else ","
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{sep}{millis:03d}"


class SubtitleParser:
    """Bộ phân tích cú pháp và trích xuất kịch bản phụ đề đa giọng."""

    # Regex nhận diện dòng mốc thời gian: 00:00:01,000 --> 00:00:04,500
    TIMESTAMP_REGEX = re.compile(
        r"((?:\d{1,2}:)?\d{2}:\d{2}[,\.]\d{3})\s*-->\s*((?:\d{1,2}:)?\d{2}:\d{2}[,\.]\d{3})"
    )

    # Regex nhận diện thẻ giọng nói hoặc nhân vật:
    # [Voice: vi-VN-HoaiMyNeural], [vi-VN-HoaiMyNeural], <v Speaker>
    VOICE_TAG_REGEX = re.compile(
        r"\[(?:Voice:\s*)?([a-zA-Z0-9_\-]+)\]",
        re.IGNORECASE,
    )
    VTT_VOICE_TAG_REGEX = re.compile(r"<v\s+([^>]+)>", re.IGNORECASE)
    HTML_TAG_REGEX = re.compile(r"<[^>]+>")

    @classmethod
    def clean_subtitle_text(cls, raw_text: str) -> Tuple[str, Optional[str]]:
        """
        Làm sạch nội dung cue:
        - Bóc tách tag định danh giọng đọc [Voice: ...] nếu có.
        - Loại bỏ các thẻ HTML / VTT formatting.
        - Trả về tuple (văn bản sạch, voice_id nếu tìm thấy).
        """
        detected_voice: Optional[str] = None

        # Kiểm tra tag VTT <v SpeakerName>
        vtt_match = cls.VTT_VOICE_TAG_REGEX.search(raw_text)
        if vtt_match:
            detected_voice = vtt_match.group(1).strip()
            raw_text = cls.VTT_VOICE_TAG_REGEX.sub("", raw_text)

        # Kiểm tra tag [Voice: voice_id]
        voice_match = cls.VOICE_TAG_REGEX.search(raw_text)
        if voice_match:
            detected_voice = voice_match.group(1).strip()
            raw_text = cls.VOICE_TAG_REGEX.sub("", raw_text)

        # Loại bỏ các thẻ html còn lại (<b>, <i>, ...)
        clean_text = cls.HTML_TAG_REGEX.sub("", raw_text)
        # Chuẩn hóa khoảng trắng
        clean_text = " ".join(clean_text.split()).strip()

        return clean_text, detected_voice

    @classmethod
    def parse(cls, content: str, default_voice: str = "vi-VN-HoaiMyNeural") -> List[Dict[str, Any]]:
        """
        Phân tích chuỗi nội dung SRT hoặc VTT thành danh sách Cue.
        Mỗi cue gồm:
        - index: int
        - start: float (giây)
        - end: float (giây)
        - duration: float (giây)
        - text: str (văn bản sạch)
        - voice: str (giọng đọc áp dụng)
        - original_voice_tag: Optional[str]
        """
        if not content:
            return []

        # Xóa UTF-8 BOM nếu có
        content = content.lstrip("\ufeff")

        # Chuẩn hóa ngắt dòng
        content = content.replace("\r\n", "\n").replace("\r", "\n")

        # Bỏ qua header WEBVTT nếu có
        lines = content.split("\n")
        start_idx = 0
        if lines and "WEBVTT" in lines[0]:
            start_idx = 1
            while start_idx < len(lines) and lines[start_idx].strip() != "":
                start_idx += 1

        # Phân chia theo block cách nhau bởi dòng trống
        blocks: List[List[str]] = []
        current_block: List[str] = []

        for line in lines[start_idx:]:
            trimmed = line.strip()
            if not trimmed:
                if current_block:
                    blocks.append(current_block)
                    current_block = []
            else:
                current_block.append(trimmed)

        if current_block:
            blocks.append(current_block)

        cues: List[Dict[str, Any]] = []
        cue_index = 1

        for block in blocks:
            # Tìm dòng mốc thời gian trong block
            time_line_idx = -1
            time_match = None

            for i, line in enumerate(block):
                m = cls.TIMESTAMP_REGEX.search(line)
                if m:
                    time_line_idx = i
                    time_match = m
                    break

            if not time_match or time_line_idx == -1:
                continue

            start_sec = parse_timestamp_to_seconds(time_match.group(1))
            end_sec = parse_timestamp_to_seconds(time_match.group(2))

            if end_sec <= start_sec:
                # Bỏ qua cue có thời gian không hợp lệ
                continue

            # Các dòng sau time_line_idx là nội dung text
            text_lines = block[time_line_idx + 1 :]
            combined_raw_text = " ".join(text_lines)

            clean_text, detected_voice = cls.clean_subtitle_text(combined_raw_text)
            if not clean_text:
                continue

            chosen_voice = detected_voice or default_voice
            duration = round(end_sec - start_sec, 3)

            cues.append({
                "index": cue_index,
                "start": start_sec,
                "end": end_sec,
                "duration": duration,
                "text": clean_text,
                "voice": chosen_voice,
                "original_voice_tag": detected_voice,
                "char_count": len(clean_text),
            })
            cue_index += 1

        return cues

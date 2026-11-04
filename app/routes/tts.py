import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.dependencies import get_tts_service
from app.services.tts_service import TTSService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tts", tags=["TTS"])


class TTSRequest(BaseModel):
    """Mẫu yêu cầu chuyển đổi văn bản thành giọng nói."""

    text: str = Field(
        ...,
        description="Văn bản cần đọc (tối đa 20.000 ký tự)",
        min_length=1,
    )
    voice: str = Field(
        ...,
        description="Mã định danh giọng đọc (ví dụ: vi-VN-HoaiMyNeural)",
        min_length=1,
    )
    rate: Optional[str] = Field(
        default="+0%",
        description="Tốc độ nói, ví dụ: +0%, +20%, -10%",
    )
    pitch: Optional[str] = Field(
        default="+0Hz",
        description="Cao độ giọng nói, ví dụ: +0Hz, +20Hz, -10Hz",
    )
    volume: Optional[str] = Field(
        default="+0%",
        description="Âm lượng giọng nói, ví dụ: +0%, -20%",
    )
    preview: Optional[bool] = Field(
        default=False,
        description="Nếu true, chỉ tạo giọng đọc cho 200 ký tự đầu",
    )


@router.post("", summary="Chuyển đổi văn bản thành file âm thanh MP3")
async def synthesize_speech(
    request: TTSRequest,
    tts_service: TTSService = Depends(get_tts_service),
):
    """
    Nhận văn bản và các thông số (giọng đọc, tốc độ, cao độ, âm lượng),
    tiến hành chuyển đổi và trả về dữ liệu file MP3.
    
    Quy tắc:
    - Giới hạn tối đa 20.000 ký tự, nếu vượt sẽ trả lỗi tiếng Việt rõ ràng.
    - Với văn bản dài, tự động chia nhỏ theo câu (~2.500 ký tự/đoạn) và ghép lại.
    - Nếu preview=True, chỉ đọc 200 ký tự đầu tiên để nghe thử nhanh.
    """
    clean_text = request.text.strip()
    if not clean_text:
        raise HTTPException(
            status_code=400,
            detail="Văn bản không được để trống. Vui lòng nhập nội dung cần đọc.",
        )

    try:
        audio_bytes = await tts_service.synthesize(
            text=clean_text,
            voice=request.voice.strip(),
            rate=request.rate or "+0%",
            pitch=request.pitch or "+0Hz",
            volume=request.volume or "+0%",
            preview=bool(request.preview),
        )

        filename = "preview.mp3" if request.preview else "speech.mp3"

        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Content-Length": str(len(audio_bytes)),
                "Accept-Ranges": "bytes",
                "Cache-Control": "no-cache",
            },
        )

    except ValueError as val_err:
        # Lỗi validate (vượt quá ký tự, text rỗng, giọng không hợp lệ)
        logger.warning(f"Lỗi tham số TTS: {val_err}")
        raise HTTPException(status_code=400, detail=str(val_err))
    except RuntimeError as run_err:
        # Lỗi kết nối hoặc timeout dịch vụ ngoài
        logger.error(f"Lỗi runtime TTS: {run_err}")
        raise HTTPException(
            status_code=502,
            detail=f"Lỗi dịch vụ tổng hợp giọng nói: {str(run_err)}",
        )
    except Exception as e:
        logger.exception(f"Lỗi không xác định khi tổng hợp giọng nói: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Đã xảy ra lỗi không mong muốn trên hệ thống: {str(e)}",
        )

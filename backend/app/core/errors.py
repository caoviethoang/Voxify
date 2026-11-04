"""Lớp ngoại lệ tùy chỉnh và định dạng lỗi JSON chuẩn."""
from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Lớp lỗi gốc của ứng dụng."""
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class TTSError(AppError):
    """Lỗi liên quan đến tổng hợp giọng nói."""
    def __init__(self, message: str):
        super().__init__(code="TTS_ERROR", message=message, status_code=502)


class ValidationError(AppError):
    """Lỗi validate đầu vào."""
    def __init__(self, message: str):
        super().__init__(code="VALIDATION_ERROR", message=message, status_code=400)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handler toàn cục cho AppError — trả về JSON chuẩn."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )

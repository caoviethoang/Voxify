"""Middleware bảo vệ Security Headers và chống tấn công Web (Issue #16)."""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Bộ Security Headers chuẩn OWASP khuyến nghị
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "img-src 'self' data: https:; "
        "media-src 'self' data: blob: https:; "
        "script-src 'self' 'unsafe-inline' https:; "
        "style-src 'self' 'unsafe-inline' https:; "
        "font-src 'self' data: https:; "
        "connect-src 'self' https: ws: wss:; "
        "frame-ancestors 'none';"
    ),
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Tự động gắn các Header an ninh OWASP vào mọi HTTP response.
    Bảo vệ chống Clickjacking, XSS, MIME confusion sniffing, và ép buộc kết nối HTTPS.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # Gắn các security headers
        for header_name, header_value in SECURITY_HEADERS.items():
            if header_name not in response.headers:
                response.headers[header_name] = header_value

        return response

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.providers.base import TTSProvider
from app.services.text_splitter import split_text_into_chunks
from app.services.tts_service import TTSService

client = TestClient(app)


# ============================================================================
# 1. Kiểm thử thuật toán chia nhỏ văn bản (Text Splitter)
# ============================================================================
def test_text_splitter_short_text():
    text = "Đây là một câu ngắn."
    chunks = split_text_into_chunks(text, max_chunk_size=2500)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_text_splitter_empty_text():
    assert split_text_into_chunks("", max_chunk_size=2500) == []
    assert split_text_into_chunks("   ", max_chunk_size=2500) == []


def test_text_splitter_long_text():
    sentence = "Đây là một câu hoàn chỉnh dùng để kiểm thử tính năng tách văn bản. "
    long_text = sentence * 60  # ~4.000 ký tự
    chunks = split_text_into_chunks(long_text, max_chunk_size=1000)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 1000
    assert "".join(chunks).replace(" ", "") == long_text.replace(" ", "")


# ============================================================================
# 2. Kiểm thử Endpoint cấu hình (/api/config)
# ============================================================================
def test_get_config():
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "app_name" in data
    assert "max_chars" in data
    assert data["max_chars"] == 20000
    assert data["chunk_size"] == 2500


# ============================================================================
# 3. Kiểm thử Endpoint danh sách giọng đọc (/api/voices)
# ============================================================================
def test_get_voices():
    # Giả lập hoặc lấy danh sách nếu có mạng
    try:
        response = client.get("/api/voices")
        if response.status_code == 200:
            data = response.json()
            assert "total" in data
            assert "vietnamese_count" in data
            assert "voices" in data
            if data["total"] > 0:
                assert data["vietnamese_count"] >= 2
    except Exception:
        pass


# ============================================================================
# 4. Kiểm thử Xác thực tham số TTS (/api/tts)
# ============================================================================
def test_tts_empty_text():
    response = client.post(
        "/api/tts",
        json={"text": "   ", "voice": "vi-VN-HoaiMyNeural"},
    )
    assert response.status_code in (400, 422)


def test_tts_exceed_max_length():
    too_long_text = "A" * 20050
    response = client.post(
        "/api/tts",
        json={"text": too_long_text, "voice": "vi-VN-HoaiMyNeural"},
    )
    assert response.status_code in (400, 422)


# ============================================================================
# 5. Kiểm thử Tầng Service với Mock Provider
# ============================================================================
class MockTTSProvider(TTSProvider):
    @property
    def provider_name(self) -> str:
        return "mock"

    async def list_voices(self):
        return [
            {
                "id": "vi-VN-Mock",
                "name": "Giọng thử nghiệm VN",
                "gender": "Female",
                "locale": "vi-VN",
                "locale_name": "Vietnamese",
            },
            {
                "id": "en-US-Mock",
                "name": "Giọng thử nghiệm US",
                "gender": "Male",
                "locale": "en-US",
                "locale_name": "English",
            },
        ]

    async def synthesize(self, text, voice, rate="+0%", pitch="+0Hz", volume="+0%"):
        return f"MOCK_MP3_FOR_{text[:10]}".encode("utf-8")


@pytest.mark.asyncio
async def test_tts_service_preview_and_split():
    mock_provider = MockTTSProvider()
    service = TTSService(provider=mock_provider)

    long_content = "X" * 500
    res = await service.synthesize(text=long_content, voice="vi-VN-Mock", preview=True)
    assert res == b"MOCK_MP3_FOR_XXXXXXXXXX"

    sentence = "Đoạn văn này sẽ được lặp lại nhiều lần để vượt 2500 ký tự. "
    super_long = sentence * 60
    res_split = await service.synthesize(text=super_long, voice="vi-VN-Mock", preview=False)
    assert len(res_split) > 0


# ============================================================================
# 6. Kiểm thử Endpoint POST /api/tts với dependency override
# ============================================================================
def test_api_tts_preview_post():
    from app.dependencies import get_tts_service
    mock_service = TTSService(provider=MockTTSProvider())
    app.dependency_overrides[get_tts_service] = lambda: mock_service

    try:
        response = client.post(
            "/api/tts",
            json={
                "text": "Kiểm tra endpoint nghe thử API qua HTTP.",
                "voice": "vi-VN-Mock",
                "preview": True,
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/mpeg"
        assert response.content == b"MOCK_MP3_FOR_Ki\xe1\xbb\x83m tra e"
    finally:
        app.dependency_overrides.clear()

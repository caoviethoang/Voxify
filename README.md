# Voxify — Vietnamese Text-to-Speech Studio

Nền tảng chuyển đổi văn bản thành giọng nói ưu tiên tiếng Việt, lấy cảm hứng từ YupVox / ElevenLabs / Vbee Studio.

## Stack

| Layer | Công nghệ |
|-------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0 + Alembic, Pydantic v2 |
| TTS Engine | `edge-tts` (Microsoft Edge TTS — miễn phí, dùng để test) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Frontend | Vite + React 18 + TypeScript + Tailwind CSS |
| Storage | Local filesystem (dev) / S3-compatible (prod) |
| Queue | Redis + ARQ _(Phase 2)_ |

---

## Cấu trúc thư mục

```
Voxify/
├── backend/                  # FastAPI app
│   ├── app/
│   │   ├── main.py           # FastAPI entry point
│   │   ├── config.py         # Settings từ .env
│   │   ├── db.py             # SQLAlchemy async engine
│   │   ├── models/           # User, Generation, CreditTransaction
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── routes/           # /api/config, /api/voices, /api/tts
│   │   ├── services/         # TTSService, StorageService, TextSplitter
│   │   ├── providers/        # TTSProvider interface + EdgeTTSProvider + ProviderRegistry
│   │   ├── storage/          # StorageBackend interface + LocalStorage
│   │   └── core/             # Errors, Logging
│   ├── alembic/              # Database migrations
│   ├── tests/                # pytest tests
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/                 # Vite + React + TS + Tailwind
│   ├── src/
│   │   ├── pages/            # TextToSpeech.tsx
│   │   ├── components/       # VoiceSelector, AudioPlayer, SliderControl...
│   │   ├── hooks/            # useVoices, useTTS, useAppConfig, useToast
│   │   ├── api/              # client.ts, tts.ts, config.ts
│   │   └── layouts/          # AppLayout.tsx
│   ├── vite.config.ts
│   └── package.json
├── storage/                  # Audio files + SQLite DB (gitignored)
├── docker-compose.yml        # Dev environment
└── README.md
```

---

## Cài đặt & Chạy

### Yêu cầu
- Docker & Docker Compose v2+
- **hoặc** Python 3.11+ và Node 20+ (nếu chạy local)

### Cách 1 — Docker Compose (khuyến nghị)

```bash
# 1. Clone repo
git clone https://github.com/caoviethoang/Voxify.git
cd Voxify

# 2. Tạo file .env từ example
cp backend/.env.example backend/.env
# (Chỉnh sửa SECRET_KEY và các giá trị cần thiết)

# 3. Khởi động backend + frontend
docker compose up

# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

**Với PostgreSQL (tùy chọn):**
```bash
docker compose --profile postgres up
# Và đổi DATABASE_URL trong backend/.env:
# DATABASE_URL=postgresql+asyncpg://voxify:voxify_dev_pass@db:5432/voxify
```

**Với Redis (tùy chọn — cần cho Phase 2+):**
```bash
docker compose --profile redis up
```

---

### Cách 2 — Local development

#### Backend
```bash
cd backend

# Tạo virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Cài dependencies
pip install -r requirements.txt

# Cấu hình
cp .env.example .env

# Tạo thư mục storage
mkdir -p storage/audio

# Chạy database migration
alembic upgrade head

# Khởi động server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

#### Frontend
```bash
cd frontend

# Cài dependencies
npm install

# Khởi động Vite dev server (proxy /api → localhost:8000)
npm run dev
# UI: http://localhost:5173
```

---

## Database Migrations (Alembic)

```bash
cd backend

# Áp dụng migration mới nhất
alembic upgrade head

# Tạo migration mới (sau khi thay đổi models)
alembic revision --autogenerate -m "mô tả thay đổi"

# Xem lịch sử migration
alembic history

# Rollback 1 bước
alembic downgrade -1
```

---

## API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/health` | Health check |
| `GET` | `/api/config` | Cấu hình frontend (app_name, max_chars...) |
| `GET` | `/api/voices` | Danh sách giọng đọc (tiếng Việt ưu tiên đầu) |
| `POST` | `/api/tts` | Tổng hợp giọng nói → trả file MP3 |
| `GET` | `/docs` | Swagger UI |

### POST /api/tts

```json
{
  "text": "Nội dung văn bản cần đọc (tối đa 20.000 ký tự)",
  "voice": "vi-VN-HoaiMyNeural",
  "rate": "+0%",
  "pitch": "+0Hz",
  "volume": "+0%",
  "preview": false
}
```

---

## Kiểm thử

```bash
cd backend
source .venv/bin/activate

# Chạy toàn bộ test suite
PYTHONPATH=. pytest tests/ -v

# Chạy một test cụ thể
PYTHONPATH=. pytest tests/test_tts.py::test_split_text -v
```

---

## Cấu hình .env (backend)

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| `APP_NAME` | `TTS Studio` | Tên hiển thị (không hardcode trong code) |
| `SECRET_KEY` | _(bắt buộc đổi)_ | JWT secret cho Phase 3 |
| `DATABASE_URL` | SQLite | Kết nối DB |
| `REDIS_URL` | localhost:6379 | Kết nối Redis |
| `STORAGE_PATH` | `./storage/audio` | Thư mục lưu file audio |
| `TTS_PROVIDER` | `edge` | Provider TTS (`edge` / `azure` / `elevenlabs`) |
| `DEFAULT_VOICE` | `vi-VN-HoaiMyNeural` | Giọng mặc định |
| `MAX_CHARS` | `20000` | Giới hạn ký tự mỗi request |

---

## Thêm TTS Provider mới

Implement interface `TTSProvider` trong `backend/app/providers/`:

```python
# backend/app/providers/azure.py
from app.providers.base import TTSProvider

class AzureTTSProvider(TTSProvider):
    async def list_voices(self): ...
    async def synthesize(self, text, voice, rate, pitch, volume) -> bytes: ...
```

Đăng ký vào `ProviderRegistry`:
```python
# backend/app/providers/__init__.py
from app.providers.azure import AzureTTSProvider
ProviderRegistry.register("azure", AzureTTSProvider)
```

Đổi trong `.env`: `TTS_PROVIDER=azure`

---

## Roadmap

- **Phase 1** ✅ MVP: TTS cơ bản, chọn giọng, sliders, lịch sử phiên
- **Phase 2** 🔲 Xuất SRT/VTT, từ điển phát âm, batch processing, lịch sử DB
- **Phase 3** 🔲 Auth, credit system, rate limiting, payments, admin dashboard

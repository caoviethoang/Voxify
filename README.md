# Text-to-Speech Studio (Phase 1 – MVP)

Hệ thống chuyển đổi văn bản thành giọng nói (Text-to-Speech) chất lượng cao, ưu tiên tiếng Việt tự nhiên, được thiết kế theo kiến trúc module hóa linh hoạt (dễ dàng mở rộng hỗ trợ Azure, ElevenLabs, Vbee,...).

> **Lưu ý cấu hình thương hiệu:** Tên ứng dụng được quản lý động qua biến `APP_NAME` trong file `.env` (không hardcode trong mã nguồn).

---

## 🚀 Công nghệ sử dụng (Tech Stack)

- **Backend:** Python 3.11+, FastAPI, Uvicorn, Pydantic v2
- **Engine TTS:** `edge-tts` (Dịch vụ Microsoft Edge Speech, hoàn toàn miễn phí cho thử nghiệm)
- **Frontend:** Single-page HTML5, CSS3, JavaScript thuần (ES6+, Dark Mode ElevenLabs / YupVox style, không dùng framework, không build step)
- **Cấu hình:** `python-dotenv`, `pydantic-settings`

---

## 📁 Cấu trúc thư mục

```text
├── app/
│   ├── __init__.py
│   ├── main.py              # Điểm khởi chạy FastAPI, middleware, static files mount
│   ├── config.py            # Quản lý cấu hình Settings từ file .env
│   ├── dependencies.py      # Dependency injection cho FastAPI
│   ├── providers/
│   │   ├── __init__.py      # Factory get_provider()
│   │   ├── base.py          # Interface TTSProvider trừu tượng
│   │   └── edge.py          # Hiện thực EdgeTTSProvider
│   ├── services/
│   │   ├── __init__.py
│   │   ├── text_splitter.py # Thuật toán chia câu thông minh (~2.500 ký tự)
│   │   └── tts_service.py   # Quản lý cache giọng đọc, validate, ghép nối MP3
│   └── routes/
│       ├── __init__.py
│       ├── config.py        # GET /api/config
│       ├── voices.py        # GET /api/voices
│       └── tts.py           # POST /api/tts
├── static/
│   ├── index.html           # Giao diện Dark mode responsive 1 trang
│   ├── style.css            # Thiết kế giao diện hiện đại
│   └── app.js               # Logic tương tác, audio player, lịch sử phiên
├── tests/
│   └── test_tts.py          # Bộ kiểm thử tự động pytest
├── requirements.txt         # Danh sách thư viện Python
├── Dockerfile               # Cấu hình build Docker image multi-stage
├── docker-compose.yml       # Cấu hình Docker Compose chạy service
├── entrypoint.sh            # Script khởi tạo container
├── .dockerignore            # Loại bỏ các file không cần thiết khi build Docker
├── .env.example             # Mẫu file cấu hình môi trường
└── README.md                # Tài liệu hướng dẫn
```

---

## ⚙️ Cài đặt & Khởi chạy

### Cách 1: Chạy bằng Docker & Docker Compose (Khuyên dùng)

```bash
# 1. Sao chép file cấu hình
cp .env.example .env

# 2. Khởi động ứng dụng bằng Docker Compose
docker compose up --build -d

# 3. Xem logs hoạt động
docker compose logs -f

# 4. Dừng container khi không sử dụng
docker compose down
```

Ứng dụng sẽ tự động chạy tại [http://localhost:8000](http://localhost:8000). Thư mục `./app` và `./static` được mount trực tiếp vào container giúp cập nhật code tức thì (hot-reload).

---

### Cách 2: Chạy trực tiếp trên máy chủ cục bộ (Local Python)

#### 1. Yêu cầu môi trường
- Python 3.11 trở lên
- Git

#### 2. Thiết lập môi trường ảo & cài đặt thư viện

```bash
# Tạo môi trường ảo
python3 -m venv .venv

# Kích hoạt môi trường ảo
# Trên Linux/macOS:
source .venv/bin/activate
# Trên Windows:
# .venv\Scripts\activate

# Cài đặt các gói phụ thuộc
pip install -r requirements.txt
```

### 3. Cấu hình file `.env`

Sao chép từ file mẫu `.env.example`:

```bash
cp .env.example .env
```

Nội dung `.env`:
```env
APP_NAME=Voxify
APP_DESCRIPTION=Nền tảng chuyển đổi văn bản thành giọng nói tiếng Việt chất lượng cao
HOST=0.0.0.0
PORT=8000
MAX_TEXT_LENGTH=20000
CHUNK_SIZE=2500
DEFAULT_VOICE=vi-VN-HoaiMyNeural
```

### 4. Khởi động Web App

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Truy cập trình duyệt tại:
- **Giao diện Web:** [http://localhost:8000](http://localhost:8000)
- **Tài liệu API Swagger:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Tài liệu ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📡 Chi tiết API Endpoints

### 1. `GET /api/config`
Lấy thông tin cấu hình ứng dụng (tên app, giới hạn ký tự, giọng mặc định).
- **Response:**
  ```json
  {
    "app_name": "Voxify",
    "app_description": "Nền tảng chuyển đổi văn bản thành giọng nói tiếng Việt chất lượng cao",
    "max_text_length": 20000,
    "chunk_size": 2500,
    "default_voice": "vi-VN-HoaiMyNeural"
  }
  ```

### 2. `GET /api/voices`
Lấy danh sách hơn 300 giọng đọc, cache trong bộ nhớ, **ưu tiên giọng tiếng Việt (`vi-VN`) lên đầu**.
- **Query params:** `refresh=true` (tùy chọn làm mới cache)
- **Response:**
  ```json
  {
    "total": 322,
    "vietnamese_count": 2,
    "voices": [
      {
        "id": "vi-VN-HoaiMyNeural",
        "name": "HoaiMy",
        "full_name": "Microsoft HoaiMy Online (Natural) - Vietnamese (Vietnam)",
        "gender": "Female",
        "locale": "vi-VN",
        "locale_name": "Vietnamese (Vietnam)",
        "is_vietnamese": true
      },
      {
        "id": "vi-VN-NamMinhNeural",
        "name": "NamMinh",
        "gender": "Male",
        "locale": "vi-VN",
        "is_vietnamese": true
      }
    ]
  }
  ```

### 3. `POST /api/tts`
Tạo file âm thanh MP3 từ văn bản.
- **Request Body:**
  ```json
  {
    "text": "Chào bạn, đây là thử nghiệm giọng đọc tự nhiên.",
    "voice": "vi-VN-HoaiMyNeural",
    "rate": "+0%",
    "pitch": "+0Hz",
    "volume": "+0%",
    "preview": false
  }
  ```
- **Xử lý đặc biệt:**
  - `preview=true`: chỉ đọc 200 ký tự đầu tiên để nghe thử nhanh.
  - Text > 2.500 ký tự: tự động cắt theo câu văn hoàn chỉnh và ghép nối audio liền mạch.
  - Text > 20.000 ký tự: trả về mã lỗi HTTP 400 kèm thông báo tiếng Việt cụ thể.
- **Response:** `Content-Type: audio/mpeg` (dữ liệu file MP3 nhị phân).

---

## 🧪 Kiểm thử (Testing)

### Kiểm thử tự động (Pytest)

Chạy bộ kiểm thử tự động toàn diện:
```bash
pytest tests/test_tts.py -v
```

Bộ test bao gồm:
1. `test_text_splitter_short_text`: Tách văn bản ngắn
2. `test_text_splitter_empty_text`: Kiểm tra chuỗi rỗng
3. `test_text_splitter_long_text`: Tách văn bản dài (>3000 ký tự) không làm đứt gãy câu
4. `test_get_config`: Xác thực endpoint `/api/config`
5. `test_get_voices`: Xác thực endpoint `/api/voices` ưu tiên tiếng Việt
6. `test_tts_empty_text`: Validate lỗi văn bản rỗng
7. `test_tts_exceed_max_length`: Validate lỗi văn bản > 20.000 ký tự
8. `test_tts_service_preview_and_split`: Kiểm thử logic tầng service với Mock Provider
9. `test_api_tts_preview_post`: Kiểm thử gọi API `/api/tts`
10. `test_edge_tts_synthesize_real`: Kiểm thử kết nối và tạo âm thanh thực tế từ Edge-TTS

### Hướng dẫn kiểm thử thủ công qua Web

1. **Mở trình duyệt:** Truy cập `http://localhost:8000`.
2. **Kiểm tra tên thương hiệu:** Tiêu đề trang và logo hiển thị theo `APP_NAME` đặt trong file `.env`.
3. **Thử văn bản mẫu:** Bấm nút **"Văn bản mẫu"** ở góc phải khung nhập liệu để tự động điền đoạn văn tiếng Việt.
4. **Kiểm tra bộ đếm ký tự:** Gõ hoặc xóa văn bản, quan sát bộ đếm ký tự và dòng trạng thái phân đoạn (ví dụ: `1 đoạn (210 ký tự)` hoặc `Dài: ~3 đoạn ghép tự động`).
5. **Chọn giọng đọc:**
   - Xem 2 giọng tiếng Việt `HoaiMy` (Nữ) và `NamMinh` (Nam) hiển thị đầu danh sách với huy hiệu màu vàng "Tiếng Việt".
   - Dùng ô tìm kiếm để gõ thử tên giọng hoặc ngôn ngữ khác.
   - Thử các tab lọc "Tiếng Việt", "Tất cả", "Nữ", "Nam".
6. **Điều chỉnh thông số âm thanh:**
   - Kéo thanh **Tốc độ đọc (Speed)** từ `0.5x` đến `2.0x`.
   - Kéo thanh **Cao độ (Pitch)** và **Âm lượng (Volume)**.
   - Bấm **"Đặt lại"** để đưa các giá trị về chuẩn (1.0x, 0Hz, 0%).
7. **Bấm "Nghe thử (200 ký tự)":**
   - Nút chuyển sang trạng thái loading.
   - Trình phát nhạc tự động bật lên và phát 200 ký tự đầu.
8. **Bấm "Tạo giọng nói":**
   - Tạo toàn bộ nội dung văn bản.
   - Bấm nút **"Tải MP3"** để tải file về máy.
9. **Kiểm tra Lịch sử phiên làm việc:**
   - Cuộn xuống phần **Lịch sử phiên làm việc**, các lần tạo trước đó đều hiển thị dạng thẻ.
   - Bấm **"Phát"** để nghe lại đoạn âm thanh cũ hoặc bấm biểu tượng tải về.
   - Bấm **"Xóa toàn bộ lịch sử"** để xóa các bản ghi trong phiên.

---

## 🔌 Khả năng mở rộng (Extensibility)

Để tích hợp thêm nhà cung cấp giọng đọc mới (Azure, ElevenLabs, Vbee,...) mà **không cần sửa mã nguồn route**:

1. Tạo file hiện thực mới trong `app/providers/`, kế thừa `TTSProvider`:
   ```python
   from app.providers.base import TTSProvider

   class ElevenLabsProvider(TTSProvider):
       @property
       def provider_name(self) -> str:
           return "elevenlabs"

       async def list_voices(self) -> list[dict]:
           # Gọi API ElevenLabs
           ...

       async def synthesize(self, text, voice, rate="+0%", pitch="+0Hz", volume="+0%") -> bytes:
           # Gọi API ElevenLabs
           ...
   ```
2. Đăng ký provider mới trong `app/providers/__init__.py`:
   ```python
   _PROVIDERS = {
       "edge": EdgeTTSProvider,
       "elevenlabs": ElevenLabsProvider,
   }
   ```
3. Cấu hình provider mong muốn trong `app/dependencies.py` hoặc qua biến `TTS_PROVIDER=elevenlabs` trong `.env`.

---

## 📌 Lộ trình phát triển các giai đoạn tiếp theo (Roadmap)

### Phase 2 (Khi có yêu cầu)
- Xuất phụ đề SRT/VTT theo câu (sử dụng word/sentence boundary của engine).
- Từ điển phát âm tùy chỉnh (thay thế từ viết tắt, tên riêng, số, ngày tháng trước khi đọc).
- Chèn khoảng ngắt (nghỉ) giữa các câu (cú pháp `[pause 1s]`).
- Tạo hàng loạt từ file `.txt`, tải về file nén `.zip`.
- Lưu trữ lịch sử vào SQLite (SQLAlchemy) và tệp audio vào thư mục `/storage`.

### Phase 3 (Thương mại hóa)
- Đăng nhập người dùng, hệ thống tính credit theo số ký tự, quản lý API key.
- Rate limiting, hàng đợi tác vụ nền (Background Queue / Celery / Redis).
- Cổng thanh toán trực tuyến, trang quản trị (Admin Dashboard).

# DỰ ÁN
Web SaaS Text-to-Speech cho người Việt, tên tạm "Voxify" (đặt trong APP_NAME ở config, KHÔNG hardcode).
Tham khảo chức năng/bố cục của yupvox.com, studio.vbee.vn, elevenlabs.io (chỉ học cách tổ chức tính năng, tự thiết kế giao diện, không sao chép logo/chữ/hình).
Hiện đã có khung: FastAPI + edge-tts + giao diện dark mode (chọn giọng, tốc độ/cao độ/âm lượng, nghe thử, tạo giọng).

# STACK
- Backend: Python 3.11, FastAPI, SQLAlchemy 2.0 + Alembic, Pydantic v2
- DB: SQLite khi dev, PostgreSQL khi production (cùng code, đổi qua DATABASE_URL)
- Hàng đợi: Redis + ARQ (job nền: TTS dài, STT, clone)
- Frontend: Vite + React + TypeScript + Tailwind + React Router + TanStack Query + i18next (vi mặc định, en)
- Lưu file: thư mục /storage khi dev, Cloudflare R2/S3 khi production (qua interface StorageBackend)
- Engine: interface TTSProvider (edge-tts hiện tại; thêm Azure/ElevenLabs/Vbee sau)

# KIẾN TRÚC
backend/app/{main.py,config.py,db.py,models/,schemas/,routes/,services/,providers/,workers/,core/}
frontend/src/{pages/,components/,api/,i18n/,hooks/,layouts/}
- Route mỏng, logic nằm ở services. Mọi tiền (credit) đi qua CreditService duy nhất.
- Mọi giá trị tiền/credit là số nguyên. Mọi thời gian lưu UTC.

# QUY TẮC
- Mọi tính năng/sửa lỗi mới phải kèm test; không merge khi CI đỏ.
- Type hints đầy đủ, lỗi trả JSON {"error": {"code","message"}} với message tiếng Việt.
- Không hardcode secret, dùng .env + .env.example. Không thêm thư viện thừa.
- Mỗi tính năng có test cơ bản (pytest) cho phần logic quan trọng (credit, auth, job).
- Chỉ làm đúng bước được yêu cầu, xong thì liệt kê file đã tạo/sửa, cách chạy, cách test thủ công và DỪNG.
- Giao diện: dark mode + light mode, responsive, tiếng Việt, đồng bộ phong cách với khung hiện tại.
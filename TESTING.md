# Hướng Dẫn Kiểm Thử & CI/CD Voxify (TESTING.md)

Tài liệu này quy định kiến trúc kiểm thử tự động, nguyên tắc phát triển kiểm thử (testing principles), và quy trình CI/CD cho dự án **Voxify**.

---

## 1. Nguyên Tắc Cốt Lõi (Core Principles)

1. **Quy Tắc Vàng (CLAUDE.md)**:
   > *"Mọi tính năng/sửa lỗi mới phải kèm test; không merge khi CI đỏ."*

2. **Nguyên Tắc Kiểm Thử Ngoại Tuyến (100% Offline Principle)**:
   - Trong môi trường CI/CD và automated test suites, **tuyệt đối không thực hiện request qua Internet** tới các dịch vụ bên thứ ba (Microsoft Edge TTS, OpenAI, AWS S3, Cloudflare, payment gateways,...).
   - Mọi external provider đều được thay thế bằng mock provider chuẩn: **`FakeTTSProvider`** (nằm trong `backend/app/providers/fake.py`).
   - Đảm bảo tốc độ chạy test nhanh (vài giây), không bị flake do network jitter hoặc rate limiting từ nhà cung cấp cloud.

3. **Chỉ Tiêu Test Coverage**:
   - **Toàn hệ thống Backend**: $\ge 80\%$ code coverage.
   - **Dịch vụ Sổ Cái & Tiền Tệ (`CreditService`)**: $\ge 90\%$ code coverage (hiện tại đạt 100%).

---

## 2. Kiến Trúc Kiểm Thử Backend (Python / Pytest)

### Cấu Trúc Thư Mục
```
backend/
├── app/
│   └── providers/
│       ├── fake.py            # FakeTTSProvider cho môi trường offline test
│       └── base.py            # ProviderRegistry & BaseTTSProvider
├── pytest.ini                 # Cấu hình asyncio_mode=auto, markers, filters
├── mypy.ini                   # Cấu hình kiểm tra kiểu tĩnh Mypy
├── ruff.toml                  # Linter & formatter cấu hình cực nhanh
└── tests/
    ├── conftest.py            # Fixtures: db session, client, test user, use_fake_tts
    ├── test_credits.py        # Test sổ cái credit, nạp/trừ, concurrency lock
    ├── test_dashboard.py      # Test KPI thống kê dashboard
    ├── test_history.py        # Test lịch sử tạo audio & phân trang
    ├── test_tts.py            # Test EdgeTTS provider offline logic
    ├── test_tts_jobs.py       # Test API tạo audio, download, subtitle, auto-refund
    └── test_coverage_boost.py # Test mở rộng contract 401/403/422, token lifecycle, dictionary
```

### Cách Chạy Kiểm Thử Backend
```bash
# Sử dụng Makefile
make test        # Chạy toàn bộ test backend + frontend
make coverage    # Chạy test với báo cáo coverage chi tiết

# Hoặc chạy trực tiếp với pytest
cd backend
pytest

# Chạy kèm đo coverage
pytest --cov=app --cov-report=term-missing --cov-fail-under=80
```

### FakeTTSProvider
`FakeTTSProvider` kế thừa từ `BaseTTSProvider` và cung cấp:
- Giả lập sinh audio bytes hợp lệ (MP3 header/frames giả lập) mà không cần mạng.
- Giả lập subtitle JSON, SRT, VTT có timestamps khớp độ dài text.
- Cờ `simulate_error = True` để kiểm thử logic xử lý lỗi & tự động hoàn tiền (`auto-refund`).

---

## 3. Kiến Trúc Kiểm Thử Frontend (React / Vitest / RTL)

### Cấu Trúc Thư Mục
```
frontend/
├── vitest.config.ts           # Cấu hình môi trường jsdom và test globals
├── eslint.config.js           # Cấu hình TypeScript ESLint
├── .prettierrc                # Định dạng code chuẩn
└── src/
    ├── test/
    │   ├── setup.ts           # Mock audio element, matchMedia, i18n
    │   └── vitest-env.d.ts    # Khai báo type ambient cho jest-dom
    ├── components/
    │   ├── AudioPlayer.test.tsx    # Test trình phát âm thanh, tua tốc độ, link SRT/VTT
    │   └── SliderControl.test.tsx  # Test thanh trượt tốc độ/âm lượng
    ├── hooks/
    │   └── useCredit.test.ts       # Test hook tính toán số dư và lịch sử giao dịch
    └── pages/
        ├── Dashboard.test.tsx      # Test render KPI card, loading, error state
        └── History.test.tsx        # Test danh sách lịch sử, chọn mục, audio preview
```

### Cách Chạy Kiểm Thử Frontend
```bash
# Sử dụng Makefile
make test

# Hoặc qua npm scripts
cd frontend
npm run test           # Chạy unit & component tests với Vitest
npm run test:coverage  # Đo độ phủ mã nguồn frontend
npm run lint           # Kiểm tra lỗi cú pháp với ESLint
npm run build          # Typecheck (tsc) và bundle build
```

---

## 4. Kiểm Thử Đầu Cuối E2E (Playwright)

Bộ kiểm thử E2E kiểm tra toàn bộ luồng trải nghiệm người dùng trong môi trường trình duyệt:
- `e2e/playwright.config.ts`: Cấu hình browser runner, tracing, video, screenshot khi có lỗi.
- `e2e/tests/auth.spec.ts`: Đăng nhập, kiểm tra thông báo lỗi khi sai mật khẩu, đăng nhập thành công, đăng xuất.
- `e2e/tests/studio.spec.ts`: Soạn thảo văn bản, chọn giọng đọc, sinh audio và tương tác thanh phát nhạc.
- `e2e/tests/dashboard.spec.ts`: Hiển thị chỉ số thống kê, danh sách tác vụ gần đây, điều hướng các trang.

### Cách Chạy E2E
```bash
make e2e
# hoặc:
cd frontend && npx playwright test -c ../e2e/playwright.config.ts
```

---

## 5. Bảng Lệnh Tiện Ích Makefile

| Lệnh | Mô tả |
| :--- | :--- |
| `make up` | Khởi chạy toàn bộ hệ thống bằng Docker Compose |
| `make down` | Dừng và dọn dẹp các container docker |
| `make lint` | Chạy linter toàn diện (Ruff + Mypy cho Backend, ESLint cho Frontend) |
| `make test` | Chạy toàn bộ test suites (Pytest + Vitest) |
| `make coverage` | Xuất báo cáo độ phủ mã nguồn và kiểm tra điều kiện vượt qua |
| `make e2e` | Khởi chạy bộ kiểm thử đầu cuối Playwright |
| `make format` | Tự động định dạng mã nguồn (Ruff format + Prettier) |
| `make clean` | Dọn dẹp cache kiểm thử, build rác và coverage artifacts |

---

## 6. Quy Trình CI/CD (GitHub Actions)

### 1. `ci.yml` (Continuous Integration)
Tự động kích hoạt khi có Pull Request hoặc Push vào nhánh `main` và `develop`:
- **`backend-lint`**: Chạy `ruff check` và `mypy` kiểm tra type safety.
- **`backend-test`**: Chạy `pytest` với cờ `--cov-fail-under=80`. Upload file `coverage.xml`.
- **`frontend`**: Cài đặt dependency sạch (`npm ci`), chạy `eslint`, `tsc`, `vite build`, và `vitest`.
- **`security`**: Quét lỗ hổng bảo mật với `pip-audit` và `npm audit`.

### 2. `deploy.yml` (Continuous Deployment)
- Tự động đóng gói Docker images cho Backend & Frontend với Multi-stage builds.
- Đẩy Docker Images lên GitHub Container Registry (`ghcr.io`).
- Triển khai và xác thực sức khỏe hệ sinh thái với endpoint `/health`.
- Tự động cảnh báo và kích hoạt rollback nếu healthcheck thất bại.


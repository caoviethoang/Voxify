# 🚀 Hướng Dẫn Triển Khai Production & DevOps — Voxify

Tài liệu này hướng dẫn chi tiết từng bước thiết lập hạ tầng, đóng gói Docker, cấu hình lưu trữ đám mây Cloudflare R2, reverse proxy Caddy tự động cấp SSL, cơ chế sao lưu tự động và quy trình CI/CD cho dự án **Voxify**.

---

## 📋 Mục lục
1. [Khuyến nghị Cấu hình Máy chủ (VPS Sizing)](#1-khuyến-nghị-cấu-hình-máy-chủ-vps-sizing)
2. [Cài đặt Môi trường trên VPS](#2-cài-đặt-môi-trường-trên-vps)
3. [Cấu hình Tên miền & DNS](#3-cấu-hình-tên-miền--dns)
4. [Cấu hình Lưu trữ Cloudflare R2 (hoặc AWS S3)](#4-cấu-hình-lưu-trữ-cloudflare-r2-hoặc-aws-s3)
5. [Thiết lập Biến Môi Trường (.env.production)](#5-thiết-lập-biến-môi-trường-envproduction)
6. [Triển khai với Docker Compose Production](#6-triển-khai-với-docker-compose-production)
7. [Tự động hóa Sao lưu & Khôi phục Cơ sở dữ liệu](#7-tự-động-hóa-sao-lưu--khôi-phục-cơ-sở-dữ-liệu)
8. [Tích hợp CI/CD với GitHub Actions](#8-tích-hợp-cicd-với-github-actions)
9. [Phương án Triển khai Hybrid: Vercel (Frontend) + VPS (Backend)](#9-phương-án-triển-khai-hybrid-vercel-frontend--vps-backend)
10. [Giám sát & Khắc phục Sự cố](#10-giám-sát--khắc-phục-sự-cố)

---

## 1. Khuyến nghị Cấu hình Máy chủ (VPS Sizing)

TTS (Text-to-Speech) và Voice Cloning có đặc thù xử lý audio nặng với FFmpeg:
- **Cấu hình tối thiểu (Dev/Staging/Traffic thấp)**:
  - CPU: **2 vCPU**
  - RAM: **4 GB RAM**
  - Disk: **40 GB SSD / NVMe**
  - OS: **Ubuntu 24.04 LTS** hoặc **Ubuntu 22.04 LTS**
  - Nhà cung cấp khuyến nghị: Hetzner Cloud (CPX21 / CAX21), DigitalOcean, Linode, Vultr hoặc AWS EC2 (t4g.medium / c6g.medium).
- **Cấu hình khuyến nghị cho Production**:
  - CPU: **4 vCPU**
  - RAM: **8 GB RAM**
  - Disk: **80 GB NVMe**
  - Swap: Khuyến nghị tạo **4 GB Swap** để đảm bảo máy chủ không bị OOM khi có spike xử lý đồng thời nhiều job TTS dài.

---

## 2. Cài đặt Môi trường trên VPS

### 2.1 Cập nhật hệ thống & Tạo Swap 4GB
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git ufw fail2ban jq

# Tạo Swapfile 4GB
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 2.2 Cấu hình Firewall (UFW)
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (Caddy Let's Encrypt challenge)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 443/udp   # HTTP/3 (QUIC)
sudo ufw enable
```

### 2.3 Cài đặt Docker & Docker Compose Plugin
```bash
# Cài đặt Docker chính thức từ Docker repository
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Thêm user hiện tại vào group docker
sudo usermod -aG docker $USER
newgrp docker

# Kiểm tra phiên bản
docker --version
docker compose version
```

---

## 3. Cấu hình Tên miền & DNS

Trỏ bản ghi DNS của tên miền về địa chỉ IP Public của VPS:
| Loại bản ghi (Type) | Tên (Host / Name) | Giá trị (Value / Target) | Proxy Status |
| :--- | :--- | :--- | :--- |
| **A** | `voxify.example.com` | `<VPS_IP_PUBLIC>` | DNS Only (hoặc Proxied nếu dùng Cloudflare) |
| **A** | `api.voxify.example.com` | `<VPS_IP_PUBLIC>` | DNS Only |

> [!NOTE]
> Nếu bạn sử dụng Cloudflare Proxy (đám mây cam), hãy đảm bảo SSL/TLS encryption mode trong Cloudflare Dashboard được đặt là **Full (Strict)** để Caddy trên VPS có thể bắt tay TLS an toàn.

---

## 4. Cấu hình Lưu trữ Cloudflare R2 (hoặc AWS S3)

Cloudflare R2 cung cấp chuẩn S3 API với chi phí egress **miễn phí 100%**, cực kỳ tối ưu cho việc phân phối các file audio TTS:

1. Đăng nhập vào [Cloudflare Dashboard](https://dash.cloudflare.com/) > Chọn **R2 Object Storage**.
2. Nhấn **Create bucket**: đặt tên bucket (ví dụ: `voxify-audio-prod`).
3. Truy cập **R2 API Tokens** > Nhấn **Create API Token**:
   - Quyền: **Admin Read & Write**.
   - Lưu lại các thông tin:
     - `Account ID` (hiển thị ở thanh địa chỉ hoặc trang R2 tổng quan).
     - `Access Key ID`
     - `Secret Access Key`
     - `Endpoint URL`: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`
4. *(Tùy chọn nhưng khuyến nghị)*: Kết nối Custom Domain với Bucket:
   - Trong trang chi tiết Bucket > Chọn tab **Settings** > **Public Access** > **Connect Domain**.
   - Nhập: `media.voxify.example.com`.
   - URL này sẽ được cấu hình vào biến `S3_PUBLIC_CDN_URL`.

---

## 5. Thiết lập Biến Môi Trường (.env.production)

Clone repository mã nguồn về thư mục `/opt/voxify`:
```bash
sudo mkdir -p /opt/voxify
sudo chown -R $USER:$USER /opt/voxify
git clone https://github.com/caoviethoang/Voxify.git /opt/voxify
cd /opt/voxify
```

Sao chép file mẫu và cấu hình:
```bash
cp .env.production.example .env.production
nano .env.production
```

Cập nhật các giá trị thiết yếu:
```env
# 1. Domain
DOMAIN=voxify.example.com
ACME_EMAIL=admin@example.com
BACKEND_URL=https://voxify.example.com
ALLOWED_ORIGINS=https://voxify.example.com

# 2. Secret Key (Tạo chuỗi ngẫu nhiên bằng: openssl rand -hex 32)
SECRET_KEY=generate_via_openssl_rand_hex_32_minimum_32_characters

# 3. Database
POSTGRES_DB=voxify_prod
POSTGRES_USER=voxify_user
POSTGRES_PASSWORD=YOUR_STRONG_PASSWORD_HERE
DATABASE_URL=postgresql+asyncpg://voxify_user:YOUR_STRONG_PASSWORD_HERE@db:5432/voxify_prod

# 4. Redis
REDIS_URL=redis://redis:6379/0

# 5. Cloudflare R2
STORAGE_BACKEND=r2
S3_ENDPOINT_URL=https://<your_account_id>.r2.cloudflarestorage.com
S3_ACCESS_KEY_ID=YOUR_R2_ACCESS_KEY
S3_SECRET_ACCESS_KEY=YOUR_R2_SECRET_KEY
S3_BUCKET_NAME=voxify-audio-prod
S3_REGION_NAME=auto
S3_PUBLIC_CDN_URL=https://media.voxify.example.com
S3_PRESIGNED_EXPIRY_SECONDS=3600
```

---

## 6. Triển khai với Docker Compose Production

Khởi động toàn bộ stack dịch vụ:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Kiểm tra trạng thái các container:
```bash
docker compose -f docker-compose.prod.yml ps
```

Các dịch vụ sẽ khởi chạy:
- `voxify_prod_db`: PostgreSQL 16
- `voxify_prod_redis`: Redis 7
- `voxify_prod_backend`: FastAPI (tự động chạy `alembic upgrade head` khi boot)
- `voxify_prod_worker`: ARQ Background Worker (xử lý job TTS ngầm)
- `voxify_prod_frontend`: SPA chạy trên Nginx tối ưu nén Gzip & Cache
- `voxify_prod_caddy`: Reverse proxy tự động cấp SSL Let's Encrypt
- `voxify_prod_backup`: Container tự động sao lưu DB định kỳ lúc 02:00 sáng

Kiểm tra log của Backend & Migration:
```bash
docker compose -f docker-compose.prod.yml logs -f backend
```

---

## 7. Tự động hóa Sao lưu & Khôi phục Cơ sở dữ liệu

Hệ thống đã tích hợp sẵn container `db_backup` tự động chạy mỗi ngày vào lúc 02:00 sáng và lưu trữ file tại thư mục `./backups/` trên host.

### 7.1 Chạy sao lưu thủ công bất kỳ lúc nào
```bash
docker compose -f docker-compose.prod.yml exec db_backup /usr/local/bin/backup_db.sh
```

File backup sẽ được sinh ra dạng `backups/voxify_db_YYYYMMDD_HHMMSS.sql.gz`. Các file cũ hơn 7 ngày (hoặc biến `BACKUP_RETENTION_DAYS`) sẽ tự động được dọn dẹp.

### 7.2 Khôi phục dữ liệu (Restore)
Khi cần khôi phục lại dữ liệu từ một bản backup:
```bash
# Khôi phục trực tiếp qua script
./scripts/restore_db.sh backups/voxify_db_20261110_020000.sql.gz
```

---

## 8. Tích hợp CI/CD với GitHub Actions

Pipeline GitHub Actions đã được định cấu hình sẵn tại `.github/workflows/ci.yml`.

Khi merge code vào nhánh `main`, workflow sẽ:
1. Chạy Ruff lint & Mypy typecheck
2. Chạy toàn bộ Pytest với độ phủ Coverage $\ge 80\%$
3. Chạy ESLint, TypeScript check & Unit tests cho Frontend
4. Build thử nghiệm Docker Image của Backend và Frontend
5. Tự động kết nối SSH vào VPS và triển khai phiên bản mới nhất

### Cấu hình GitHub Secrets
Truy cập **GitHub Repository** > **Settings** > **Secrets and variables** > **Actions** > Thêm các secret sau:
- `SSH_HOST`: Địa chỉ IP của VPS (ví dụ: `123.45.67.89`)
- `SSH_USER`: Tên tài khoản trên VPS (ví dụ: `root` hoặc `ubuntu`)
- `SSH_KEY`: Nội dung SSH Private Key của server (Private Key có quyền truy cập vào VPS)
- `SSH_PORT`: Port SSH (mặc định: `22`)

---

## 9. Phương án Triển khai Hybrid: Vercel (Frontend) + VPS (Backend)

### Câu hỏi: *Tôi có thể sử dụng Vercel để deploy Voxify được không?*

> [!IMPORTANT]
> **Câu trả lời**:
> - **Frontend (React + Vite)**: **RẤT NÊN & HOÀN TOÀN ĐƯỢC** triển khai trên Vercel.
> - **Backend (FastAPI + Worker + DB)**: **KHÔNG THỂ / KHÔNG NÊN** triển khai trực tiếp trên Vercel Serverless.

### Tại sao Backend không phù hợp với Vercel Serverless?
1. **Thiếu thư viện hệ thống FFmpeg**: Việc cắt ghép file audio, điều chỉnh pitch/speed, ghép câu cho đoạn văn bản dài cần FFmpeg nhị phân (`/usr/bin/ffmpeg`). Vercel Serverless Function không có sẵn FFmpeg và bị giới hạn dung lượng package (50MB zip / 250MB unzipped).
2. **Timeout nghiêm ngặt**: Vercel Serverless Function bị giới hạn timeout tối đa 10 - 15 giây (gói Hobby) hoặc 60 giây (gói Pro). Các job chuyển đổi audio dài (đến 100.000 ký tự) hoặc tổng hợp giọng mẫu clone có thể mất từ 1 - 3 phút, sẽ lập tức bị kill tiến trình giữa chừng.
3. **Tiến trình chạy ngầm (ARQ Background Worker)**: ARQ yêu cầu một tiến trình Python daemon chạy thường trực kết nối với Redis để lắng nghe hàng đợi job. Serverless chỉ kích hoạt khi có HTTP request và giải phóng ngay sau khi trả lời lời gọi API.
4. **Kết nối DB & File tạm**: Serverless không có ổ cứng liên tục, thư mục `/tmp` chỉ là bộ nhớ tạm tối đa 512MB và bị xóa ngay sau mỗi execution.

---

### Hướng dẫn triển khai mô hình Hybrid tối ưu:

#### Bước 1: Deploy Backend trên VPS
Thực hiện các bước từ 1 đến 6 ở trên để VPS chạy Backend, Worker, Postgres, Redis và Caddy (API endpoint: `https://api.voxify.example.com`).

#### Bước 2: Deploy Frontend trên Vercel
1. Dự án đã có sẵn file cấu hình [`frontend/vercel.json`](file:///home/hoangcv/Voxify/frontend/vercel.json) hỗ trợ SPA routing và bảo mật HTTP headers.
2. Đăng nhập [Vercel](https://vercel.com/) > Nhấn **Add New Project** > Import repository GitHub của Voxify.
3. Trong phần thiết lập Project:
   - **Root Directory**: Chọn `frontend`.
   - **Framework Preset**: Chọn `Vite`.
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Cấu hình Environment Variable trên Vercel:
   - `VITE_API_URL`: Điền domain API của VPS, ví dụ `https://api.voxify.example.com`
5. Nhấn **Deploy**. Vercel sẽ tự động build và cấp phát domain toàn cầu tốc độ cao (Edge CDN).

#### Bước 3: Cấu hình CORS trên Backend VPS
Trong file `.env.production` trên VPS, thêm domain Vercel vào `ALLOWED_ORIGINS`:
```env
ALLOWED_ORIGINS=https://voxify.vercel.app,https://voxify.yourdomain.com
```
Khởi động lại backend:
```bash
docker compose -f docker-compose.prod.yml restart backend
```

---

## 10. Giám sát & Khắc phục Sự cố

### Kiểm tra sức khỏe dịch vụ (Health Check)
```bash
curl -I https://voxify.example.com/health
# Trả về: HTTP/2 200 OK
```

### Xem log theo thời gian thực
```bash
# Log Backend
docker compose -f docker-compose.prod.yml logs -f backend

# Log ARQ Worker
docker compose -f docker-compose.prod.yml logs -f worker

# Log Caddy Proxy (truy vấn SSL & Access log)
docker compose -f docker-compose.prod.yml logs -f caddy
```

### Khởi động lại dịch vụ khi cập nhật cấu hình
```bash
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

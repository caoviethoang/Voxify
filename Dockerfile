# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.11-slim
FROM python:${PYTHON_VERSION} AS base

WORKDIR /app

# Cài đặt các gói phụ thuộc cơ bản (curl cho healthcheck)
RUN apt-get update -qq && \
    apt-get install --no-install-recommends -y curl ca-certificates && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Build stage: Cài đặt các thư viện Python
FROM base AS build

# Cài đặt công cụ biên dịch nếu có thư viện C-extension
RUN apt-get update -qq && \
    apt-get install --no-install-recommends -y build-essential && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Final image
FROM base

# Sao chép các gói Python đã cài đặt từ build stage
COPY --from=build /install /usr/local

# Thiết lập biến môi trường tối ưu cho Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Sao chép mã nguồn ứng dụng
COPY . .

# Cấu hình entrypoint
COPY entrypoint.sh /usr/bin/entrypoint.sh
RUN chmod +x /usr/bin/entrypoint.sh
ENTRYPOINT ["/usr/bin/entrypoint.sh"]

EXPOSE 8000

# Chạy ứng dụng FastAPI qua Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

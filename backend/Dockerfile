# ==========================================
# Voxify Backend & Worker Multi-stage Dockerfile
# ==========================================

FROM python:3.11-slim AS base
WORKDIR /app

# Cài đặt runtime dependencies: ffmpeg (cho audio/tts) & curl (healthcheck)
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends curl ffmpeg libpq5 && \
    rm -rf /var/lib/apt/lists/*

# ------------------------------------------
# Stage 1: Build Python packages
# ------------------------------------------
FROM base AS build
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends gcc python3-dev libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ------------------------------------------
# Stage 2: Production Runtime
# ------------------------------------------
FROM base AS runtime
COPY --from=build /install /usr/local

COPY . .

# Chuẩn bị thư mục storage và cấp quyền cho entrypoint
RUN mkdir -p storage/audio storage/temp storage/voice_samples && \
    chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

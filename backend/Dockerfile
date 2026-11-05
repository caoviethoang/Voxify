FROM python:3.11-slim AS base
WORKDIR /app
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends curl ffmpeg && \
    rm -rf /var/lib/apt/lists/*

FROM base AS build
RUN apt-get update -qq && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM base AS runtime
COPY --from=build /install /usr/local
COPY . .
RUN mkdir -p storage/audio storage

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

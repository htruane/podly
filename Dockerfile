#frontend
FROM node:18-alpine AS frontend-build

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

#backend
FROM python:3.11-slim AS backend

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ARG CUDA_VERSION=12.4.1
ARG ROCM_VERSION=6.4
ARG USE_GPU=false
ARG USE_GPU_NVIDIA=${USE_GPU}
ARG USE_GPU_AMD=false

WORKDIR /app

# Install dependencies based on base image
RUN apt-get update && \
    apt-get install -y ca-certificates && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    gosu \
    python3 \
    python3-pip \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv pip install --system --no-cache .

RUN if [ "${USE_GPU_NVIDIA}" = "true" ]; then \
        uv pip install --system --no-cache nvidia-cudnn-cu12 torch; \
    elif [ "${USE_GPU_AMD}" = "true" ]; then \
        uv pip install --system --no-cache torch --index-url https://download.pytorch.org/whl/rocm${ROCM_VERSION}; \
    else \
        uv pip install --system --no-cache torch --index-url https://download.pytorch.org/whl/cpu; \
    fi;

COPY src/ ./src/
RUN rm -rf ./src/instance
COPY scripts/ ./scripts/

COPY --from=frontend-build /app/dist ./src/app/static

RUN groupadd -r appuser && \
    useradd --no-log-init -r -g appuser -d /home/appuser appuser && \
    mkdir -p /home/appuser && \
    chown -R appuser:appuser /home/appuser

RUN mkdir -p /app/processing /app/src/instance /app/src/instance/data /app/src/instance/data/in /app/src/instance/data/srv /app/src/instance/config /app/src/instance/db && \
    chown -R appuser:appuser /app

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod 755 /docker-entrypoint.sh

EXPOSE 5001

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["python3", "-u", "src/main.py"]

# ── Stage 1: Build the React UI ──────────────────────────────────────────
FROM node:20-alpine AS ui-builder

WORKDIR /app/ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ .
RUN npm run build

# ── Stage 2: Build the Python package ────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build
COPY --from=ui-builder /app/ui/dist src/toolatlas_mcp/ui/dist/

COPY pyproject.toml README.md ./
COPY src/ src/
COPY docs/ docs/
COPY examples/ examples/

RUN pip install build && python -m build

# ── Stage 3: Runtime ─────────────────────────────────────────────────────
FROM python:3.11-slim

RUN groupadd -r toolatlas && useradd -r -g toolatlas toolatlas

WORKDIR /app

COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install /tmp/*.whl && rm /tmp/*.whl

USER toolatlas

EXPOSE 8081

VOLUME ["/data"]

ENV TOOLATLAS_HOST=0.0.0.0
ENV TOOLATLAS_PORT=8081
ENV TOOLATLAS_STORAGE_TYPE=json
ENV TOOLATLAS_DATABASE_URL=sqlite+aiosqlite:////data/toolatlas.db

ENTRYPOINT ["toolatlas"]

CMD ["start"]

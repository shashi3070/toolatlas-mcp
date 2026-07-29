# ── Stage 1: Build the React UI ──────────────────────────────────────────
FROM node:20-bookworm-slim AS ui-builder

WORKDIR /app/ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ .
RUN npm run build

# ── Stage 2: Build the Python package ────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

COPY pyproject.toml README.md ./
COPY src/ src/
COPY docs/ docs/
COPY examples/ examples/

COPY --from=ui-builder /app/src/toolatlas_mcp/ui/dist src/toolatlas_mcp/ui/dist/

RUN pip install build && python -m build

# ── Stage 3: Runtime ─────────────────────────────────────────────────────
FROM python:3.11-slim

RUN groupadd -r toolatlas && useradd -r -m -d /home/toolatlas -g toolatlas toolatlas && mkdir -p /data && chown toolatlas:toolatlas /data

WORKDIR /app

COPY --from=ui-builder /usr/local/bin/node /usr/local/bin/node
COPY --from=ui-builder /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install /tmp/*.whl asyncpg && rm /tmp/*.whl

USER toolatlas

EXPOSE 8081

VOLUME ["/data"]

ENV HOME=/home/toolatlas
ENV TOOLATLAS_HOST=0.0.0.0
ENV TOOLATLAS_PORT=8081
ENV TOOLATLAS_STORAGE_TYPE=json
ENV TOOLATLAS_DATA_DIR=/data
ENV TOOLATLAS_DATABASE_URL=sqlite+aiosqlite:////data/toolatlas.db

ENTRYPOINT ["toolatlas"]

CMD ["start"]

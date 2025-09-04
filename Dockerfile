FROM python:3.13-bookworm AS deps
WORKDIR /workflow
COPY --from=ghcr.io/virtool/tools:1.1.0 /tools/bowtie2/2.5.4/bowtie* /usr/local/bin/
COPY --from=ghcr.io/virtool/tools:1.1.0 /tools/pigz/2.8/pigz /usr/local/bin/

FROM python:3.13-bookworm AS uv
WORKDIR /workflow
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}" \
    UV_CACHE_DIR='/tmp/uv_cache'
COPY uv.lock pyproject.toml README.md ./
RUN uv sync

FROM deps AS base
WORKDIR /workflow
ENV PATH="/workflow/.venv/bin:/root/.local/bin:${PATH}"
COPY --from=uv /workflow/.venv /workflow/.venv
COPY fixtures.py workflow.py VERSION* ./

FROM deps AS test
WORKDIR /workflow
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}" \
    UV_CACHE_DIR='/tmp/uv_cache'
COPY uv.lock pyproject.toml ./
COPY README.md ./
RUN uv sync
COPY fixtures.py workflow.py ./
COPY tests/ ./tests/

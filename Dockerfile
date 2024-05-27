FROM debian:bookworm as bowtie2
WORKDIR /build
RUN apt-get update && apt-get install -y unzip wget
RUN wget https://github.com/BenLangmead/bowtie2/releases/download/v2.3.2/bowtie2-2.3.2-legacy-linux-x86_64.zip && \
    unzip bowtie2-2.3.2-legacy-linux-x86_64.zip && \
    mkdir bowtie2 && \
    cp bowtie2-2.3.2-legacy/bowtie2* bowtie2

FROM debian:bookworm as pigz
WORKDIR /build
RUN apt-get update && apt-get install -y gcc make wget zlib1g-dev
RUN wget https://zlib.net/pigz/pigz-2.8.tar.gz && \
    tar -xzvf pigz-2.8.tar.gz && \
    cd pigz-2.8 && \
    make

FROM python:3.12-bookworm as build
WORKDIR /workflow
RUN curl -sSL https://install.python-poetry.org | python -
ENV PATH="/root/.local/bin:${PATH}" \
    POETRY_CACHE_DIR='/tmp/poetry_cache' \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1
COPY pyproject.toml poetry.lock ./
RUN poetry install --without dev --no-root

FROM python:3.12-bookworm as base
WORKDIR /workflow
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/workflow/.venv/bin:/opt/fastqc:${PATH}"
COPY --from=bowtie2 /build/bowtie2/* /usr/local/bin/
COPY --from=pigz /build/pigz-2.8/pigz /usr/local/bin/pigz
COPY --from=build /workflow/.venv /workflow/.venv
COPY fixtures.py workflow.py VERSION* ./

FROM build as test
WORKDIR /workflow
RUN curl -sSL https://install.python-poetry.org | python -
ENV PATH="/root/.local/bin:${PATH}" \
    POETRY_CACHE_DIR='/tmp/poetry_cache' \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1
COPY --from=build /workflow/.venv /workflow/.venv
COPY pyproject.toml poetry.lock ./
RUN poetry install
COPY fixtures.py workflow.py ./
COPY tests/ ./tests/

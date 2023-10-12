FROM debian:buster as prep
WORKDIR /build
RUN apt-get update && apt-get install -y make gcc zlib1g-dev wget unzip
RUN wget https://zlib.net/pigz/pigz-2.8.tar.gz && \
    tar -xzvf pigz-2.8.tar.gz && \
    cd pigz-2.8 && \
    make
RUN wget https://github.com/BenLangmead/bowtie2/releases/download/v2.3.2/bowtie2-2.3.2-legacy-linux-x86_64.zip && \
    unzip bowtie2-2.3.2-legacy-linux-x86_64.zip && \
    mkdir bowtie2 && \
    cp bowtie2-2.3.2-legacy/bowtie2* bowtie2

FROM python:3.10-buster as rust
WORKDIR /build
RUN apt-get update && apt-get install -y curl build-essential
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN pip install maturin==0.14.7
COPY src src
COPY Cargo.toml Cargo.lock ./
RUN maturin build --release

FROM python:3.10-buster as base
WORKDIR /workflow
RUN curl -sSL https://install.python-poetry.org | python -
ENV PATH="/root/.local/bin:${PATH}"
COPY --from=prep /build/bowtie2/* /usr/local/bin/
COPY --from=prep /build/pigz-2.8/pigz /usr/local/bin/pigz
COPY --from=rust /build/target/wheels/count_nucleotides_and_seqs*.whl ./
COPY fixtures.py workflow.py pyproject.toml poetry.lock ./
RUN poetry export > requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install ./count_nucleotides_and_seqs*.whl

FROM base as test
WORKDIR /workflow
RUN poetry export --with dev > requirements.txt
RUN pip install -r requirements.txt
COPY tests ./tests
RUN pytest
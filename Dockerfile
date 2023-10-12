FROM python:3.10-buster as rustPyo3
WORKDIR /build
RUN apt-get update && apt-get install -y curl build-essential
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN pip install maturin==0.14.5
COPY src src
COPY Cargo.toml Cargo.lock ./
RUN maturin build --release

FROM ghcr.io/virtool/workflow:5.4.2 as test
WORKDIR /test
COPY poetry.lock pyproject.toml /test/
RUN curl -sSL https://install.python-poetry.org | python -
RUN poetry install
COPY tests / test/
COPY fixtures.py workflow.py pytest.ini /test/
COPY --from=rustPyo3 /build/target/wheels/count_nucleotides_and_seqs*.whl ./
RUN ls
RUN pip3.10 install count_nucleotides_and_seqs*.whl
RUN poetry install
RUN poetry add ./count_nucleotides_and_seqs*.whl
RUN poetry run pytest


FROM ghcr.io/virtool/workflow:5.4.2
WORKDIR /workflow
COPY fixtures.py workflow.py /workflow/
COPY --from=rustPyo3 /build/target/wheels/count_nucleotides_and_seqs*.whl ./
RUN ls
RUN pip3.10 install count_nucleotides_and_seqs*.whl
RUN poetry install
RUN poetry add ./count_nucleotides_and_seqs*.whl

FROM rust:1.65-slim-buster as rust
WORKDIR /build
COPY /utils/count_nucleotides_and_seqs/ /build/
RUN ls
RUN cargo build -r

FROM virtool/workflow:5.1.0 as build
WORKDIR /workflow
COPY --from=rust /build/target/release/count_nucleotides_and_seqs /workflow/
COPY fixtures.py workflow.py /workflow/

FROM virtool/workflow:5.1.0 as test
WORKDIR /test
COPY poetry.lock pyproject.toml /test/
RUN curl -sSL https://install.python-poetry.org | python -
RUN poetry install --with dev
COPY --from=rust /build/target/release/count_nucleotides_and_seqs /test/
COPY tests / test/
COPY fixtures.py workflow.py pytest.ini /test/
RUN poetry run pytest

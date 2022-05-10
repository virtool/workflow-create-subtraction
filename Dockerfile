FROM rust:1.60.0-slim-buster as rust
WORKDIR /build
COPY /utils/count_nucleotides_and_seqs/ /build/
RUN ls
RUN cargo build -r

FROM virtool/workflow:4.0.2 as test
WORKDIR /test
COPY poetry.lock pyproject.toml /test/
RUN pip install poetry
RUN poetry install
COPY --from=rust /build/target/release/count_nucleotides_and_seqs /test/
COPY tests / test/
COPY workflow.py /test/
RUN poetry run pytest


FROM virtool/workflow:4.0.2
WORKDIR /workflow
COPY --from=rust /build/target/release/count_nucleotides_and_seqs /workflow/
COPY workflow.py /workflow/workflow.py

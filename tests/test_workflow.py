import gzip
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from virtool.workflow.data.subtractions import WFNewSubtraction
from virtool.workflow.runtime.run_subprocess import RunSubprocess

from workflow import build_index, compute_gc_and_count, finalize

ARABIDOPSIS_PATH = Path(__file__).parent / "files/subtraction.fa.gz"

FASTA = ">seq_1\nATGCATGCNN\n>seq_2\natgcatgcat\n"
"""A small FASTA that mixes upper and lower case bases."""

FASTA_GC = {"a": 0.25, "t": 0.25, "g": 0.2, "c": 0.2, "n": 0.1}

INDEX_NAMES = ["1", "2", "3", "4", "rev.1", "rev.2"]


def create_new_subtraction(
    mocker,
    path: Path,
    finalize_mock: AsyncMock | None = None,
    upload_mock: AsyncMock | None = None,
) -> WFNewSubtraction:
    """Create a subtraction whose FASTA lives in ``path``."""
    return WFNewSubtraction(
        id=1,
        delete=mocker.AsyncMock(),
        finalize=finalize_mock or mocker.AsyncMock(),
        name="bar",
        nickname="baz",
        path=path,
        upload=upload_mock or mocker.AsyncMock(),
    )


def write_fasta(path: Path, *, gzipped: bool, fasta: str = FASTA):
    """Write ``fasta`` to ``path``, gzipping it only if ``gzipped`` is set.

    The input file is always named ``subtraction.fa.gz``, whether or not the
    user's upload was compressed.
    """
    if gzipped:
        with gzip.open(path, "wt") as f:
            f.write(fasta)
    else:
        path.write_text(fasta)


@pytest.mark.datafiles(ARABIDOPSIS_PATH)
async def test_compute_gc_and_count(
    datafiles, mocker, run_subprocess: RunSubprocess, tmp_path: Path
):
    new_subtraction = create_new_subtraction(mocker, tmp_path)

    intermediate = SimpleNamespace()

    await compute_gc_and_count(intermediate, new_subtraction, 1, run_subprocess)

    assert intermediate.gc == {"a": 0.319, "t": 0.319, "g": 0.18, "c": 0.18, "n": 0.002}
    assert intermediate.count == 7


@pytest.mark.parametrize("gzipped", [True, False], ids=["gzipped", "uncompressed"])
async def test_compute_gc_and_count_compression(
    gzipped: bool, mocker, run_subprocess: RunSubprocess, tmp_path: Path
):
    """Test that GC and count are computed for compressed and plain input."""
    new_subtraction = create_new_subtraction(mocker, tmp_path)
    write_fasta(new_subtraction.fasta_path, gzipped=gzipped)

    intermediate = SimpleNamespace()

    await compute_gc_and_count(intermediate, new_subtraction, 1, run_subprocess)

    assert intermediate.gc == FASTA_GC
    assert intermediate.count == 2


@pytest.mark.parametrize("fasta", ["", ">seq_1\nRYKM\n"], ids=["empty", "no_bases"])
async def test_compute_gc_and_count_no_bases(
    fasta: str, mocker, run_subprocess: RunSubprocess, tmp_path: Path
):
    """Test that a FASTA with no countable bases raises instead of dividing by zero."""
    new_subtraction = create_new_subtraction(mocker, tmp_path)
    write_fasta(new_subtraction.fasta_path, gzipped=False, fasta=fasta)

    intermediate = SimpleNamespace()

    with pytest.raises(ValueError, match="found in subtraction FASTA"):
        await compute_gc_and_count(intermediate, new_subtraction, 1, run_subprocess)


@pytest.mark.parametrize("gzipped", [True, False], ids=["gzipped", "uncompressed"])
async def test_build_index(
    gzipped: bool, mocker, run_subprocess: RunSubprocess, tmp_path: Path
):
    """Test that an index is built from compressed and plain input.

    The input file is named ``subtraction.fa.gz`` in both cases, so this covers
    bowtie2-build's decision to decompress the reference based on its
    extension.
    """
    subtraction_path = tmp_path / "subtraction"
    subtraction_path.mkdir()

    new_subtraction = create_new_subtraction(mocker, subtraction_path)
    write_fasta(new_subtraction.fasta_path, gzipped=gzipped)

    bowtie_index_path = tmp_path / "bowtie"
    bowtie_index_path.mkdir()

    await build_index(bowtie_index_path, new_subtraction, 1, run_subprocess, tmp_path)

    assert sorted(path.name for path in bowtie_index_path.glob("*.bt2")) == sorted(
        f"subtraction.{name}.bt2" for name in INDEX_NAMES
    )


@pytest.mark.parametrize("gzipped", [True, False], ids=["gzipped", "uncompressed"])
@pytest.mark.parametrize("suffix", ["bt2", "bt2l"], ids=["small_index", "large_index"])
async def test_finalize(gzipped: bool, suffix: str, mocker, tmp_path: Path):
    """Test that the FASTA and all index files are uploaded.

    Large references produce ``.bt2l`` index files instead of ``.bt2`` ones.
    """
    subtraction_path = tmp_path / "subtraction"
    subtraction_path.mkdir()

    finalize_mock = mocker.AsyncMock()
    upload_mock = mocker.AsyncMock()

    new_subtraction = create_new_subtraction(
        mocker, subtraction_path, finalize_mock, upload_mock
    )

    write_fasta(new_subtraction.fasta_path, gzipped=gzipped)

    bowtie_index_path = tmp_path / "bowtie"
    bowtie_index_path.mkdir()

    for name in INDEX_NAMES:
        (bowtie_index_path / f"subtraction.{name}.{suffix}").write_text("index")

    intermediate = SimpleNamespace(count=2, gc=FASTA_GC)

    await finalize(bowtie_index_path, intermediate, new_subtraction, 1, tmp_path)

    fasta_path, *index_paths = [call.args[0] for call in upload_mock.call_args_list]

    with gzip.open(fasta_path, "rt") as f:
        assert f.read() == FASTA

    assert sorted(path.name for path in index_paths) == sorted(
        f"subtraction.{name}.{suffix}" for name in INDEX_NAMES
    )

    finalize_mock.assert_called_once_with(FASTA_GC, 2)


async def test_finalize_no_index(mocker, tmp_path: Path):
    """Test that a subtraction is not finalized when no index files were built."""
    subtraction_path = tmp_path / "subtraction"
    subtraction_path.mkdir()

    finalize_mock = mocker.AsyncMock()

    new_subtraction = create_new_subtraction(mocker, subtraction_path, finalize_mock)
    write_fasta(new_subtraction.fasta_path, gzipped=True)

    bowtie_index_path = tmp_path / "bowtie"
    bowtie_index_path.mkdir()

    intermediate = SimpleNamespace(count=2, gc=FASTA_GC)

    with pytest.raises(FileNotFoundError, match="No Bowtie2 index files found"):
        await finalize(bowtie_index_path, intermediate, new_subtraction, 1, tmp_path)

    finalize_mock.assert_not_called()

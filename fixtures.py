import asyncio
from pathlib import Path
from types import SimpleNamespace

from pyfixtures import fixture


@fixture
async def bowtie_index_path(work_path: Path) -> Path:
    """The output directory for the subtraction's Bowtie2 index."""
    path = work_path / "bowtie"
    await asyncio.to_thread(path.mkdir)

    return path


@fixture
async def decompressed_fasta_path(work_path: Path) -> Path:
    """The path to the input FASTA file for the subtraction."""
    return work_path / "subtraction.fa"


@fixture
def intermediate() -> SimpleNamespace:
    """A namespace for intermediate variables."""
    return SimpleNamespace()

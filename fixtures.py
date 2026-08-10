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
def intermediate() -> SimpleNamespace:
    """A namespace for intermediate variables."""
    return SimpleNamespace()

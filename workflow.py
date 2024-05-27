import asyncio
import shutil
from pathlib import Path
from types import SimpleNamespace

from pyfixtures import fixture
from virtool_core.utils import compress_file, decompress_file, is_gzipped
from virtool_workflow import hooks, step
from virtool_workflow.data.subtractions import WFNewSubtraction
from virtool_workflow.runtime.run_subprocess import RunSubprocess


@hooks.on_failure
async def delete_subtraction(new_subtraction: WFNewSubtraction):
    """Delete the subtraction in the case of a failure."""
    await new_subtraction.delete()


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


@step(name="Decompress FASTA")
async def decompress(
    decompressed_fasta_path: Path,
    new_subtraction: WFNewSubtraction,
    proc: int,
):
    """Ensure the input FASTA data is decompressed."""
    if await asyncio.to_thread(is_gzipped, new_subtraction.fasta_path):
        await asyncio.to_thread(
            decompress_file,
            new_subtraction.fasta_path,
            decompressed_fasta_path,
            processes=proc,
        )
    else:
        await asyncio.to_thread(
            shutil.copyfile, new_subtraction.fasta_path, decompressed_fasta_path
        )


@step(name="Compute GC and Count")
async def compute_gc_and_count(
    decompressed_fasta_path: Path, intermediate: SimpleNamespace
):
    """Compute the GC and count."""

    def func(path: Path):
        _count = 0
        _nucleotides = {"a": 0, "t": 0, "g": 0, "c": 0, "n": 0}

        with open(path, "r") as f:
            for line in f:
                if line[0] == ">":
                    _count += 1

                elif line:
                    for i in ["a", "t", "g", "c", "n"]:
                        # Find lowercase and uppercase nucleotide characters
                        _nucleotides[i] += line.lower().count(i)

        return _count, _nucleotides

    count, nucleotides = await asyncio.to_thread(func, decompressed_fasta_path)

    nucleotides_sum = sum(nucleotides.values())

    intermediate.count = count
    intermediate.gc = {
        key: round(nucleotides[key] / nucleotides_sum, 3) for key in nucleotides
    }


@step
async def build_index(
    bowtie_index_path: Path,
    decompressed_fasta_path: Path,
    proc: int,
    run_subprocess: RunSubprocess,
):
    """Build a Bowtie2 index."""
    await run_subprocess(
        [
            "bowtie2-build",
            "-f",
            "--threads",
            str(proc),
            decompressed_fasta_path,
            str(bowtie_index_path) + "/subtraction",
        ]
    )


@step
async def finalize(
    bowtie_index_path: Path,
    decompressed_fasta_path: Path,
    intermediate: SimpleNamespace,
    new_subtraction: WFNewSubtraction,
    proc: int,
    work_path: Path,
):
    """Compress and subtraction data."""
    compressed_path = work_path / "subtraction.fa.gz"

    await asyncio.to_thread(
        compress_file,
        decompressed_fasta_path,
        compressed_path,
        processes=proc,
    )

    await new_subtraction.upload(compressed_path)

    for path in bowtie_index_path.glob("*.bt2"):
        await new_subtraction.upload(path)

    await new_subtraction.finalize(intermediate.gc, intermediate.count)

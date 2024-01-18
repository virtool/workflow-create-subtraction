import asyncio
import shutil
from pathlib import Path
from types import SimpleNamespace

import count_nucleotides_and_seqs
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
    a, t, g, c, n, count = count_nucleotides_and_seqs.run(str(decompressed_fasta_path))

    nucleotides = {
        "a": int(a),
        "t": int(t),
        "g": int(g),
        "c": int(c),
        "n": int(n),
    }

    intermediate.count = int(count)

    nucleotides_sum = sum(nucleotides.values())

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

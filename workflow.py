import asyncio
import shutil
from pathlib import Path
from types import SimpleNamespace

import count_nucleotides_and_seqs
from virtool_core.utils import compress_file, decompress_file, is_gzipped
from virtool_workflow import hooks, step
from virtool_workflow.api.subtractions import SubtractionProvider
from virtool_workflow.runtime.run_subprocess import RunSubprocess


@hooks.on_failure
async def delete_subtraction(subtraction_provider: SubtractionProvider):
    """Delete the subtraction in the case of a failure."""
    await subtraction_provider.delete()


@step
async def decompress(
    fasta_path: Path,
    input_path: Path,
):
    """
    Ensure the input FASTA data is decompressed.

    """
    if is_gzipped(input_path):
        await asyncio.to_thread(
            decompress_file,
            input_path,
            fasta_path,
        )
    else:
        await asyncio.to_thread(shutil.copyfile, input_path, fasta_path)


@step(name="Compute GC and count")
async def compute_gc_and_count(fasta_path: Path, intermediate: SimpleNamespace):
    """Compute the GC and count."""
    a, t, g, c, n, count = count_nucleotides_and_seqs.run(str(fasta_path))

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
    fasta_path: Path,
    intermediate: SimpleNamespace,
    proc: int,
    run_subprocess: RunSubprocess,
    work_path: Path,
):
    """Build a Bowtie2 index."""
    bowtie_path = work_path / "index-build"
    bowtie_path.mkdir()

    command = [
        "bowtie2-build",
        "-f",
        "--threads",
        str(proc),
        str(fasta_path),
        str(bowtie_path) + "/subtraction",
    ]

    await run_subprocess(command)

    intermediate.bowtie_path = bowtie_path


@step
async def finalize(
    fasta_path: Path,
    intermediate: SimpleNamespace,
    proc: int,
    subtraction_provider: SubtractionProvider,
):
    """Compress and subtraction data."""
    compressed_path = fasta_path.parent / "subtraction.fa.gz"

    await asyncio.to_thread(
        compress_file,
        fasta_path,
        compressed_path,
        proc,
    )

    await subtraction_provider.upload(compressed_path)

    for path in intermediate.bowtie_path.glob("*.bt2"):
        await subtraction_provider.upload(path)

    await subtraction_provider.finalize(intermediate.gc, intermediate.count)

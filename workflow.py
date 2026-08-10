import asyncio
from pathlib import Path
from types import SimpleNamespace

from virtool.utils import compress_file, is_gzipped
from virtool.workflow import hooks, step
from virtool.workflow.data.subtractions import WFNewSubtraction
from virtool.workflow.runtime.run_subprocess import RunSubprocess


@hooks.on_failure
async def delete_subtraction(new_subtraction: WFNewSubtraction):
    """Delete the subtraction in the case of a failure."""
    await new_subtraction.delete()


@step(name="Compute GC and Count")
async def compute_gc_and_count(
    intermediate: SimpleNamespace,
    new_subtraction: WFNewSubtraction,
    proc: int,
    run_subprocess: RunSubprocess,
):
    """Compute the GC and count using seqkit.

    seqkit reads gzip-compressed FASTA natively, so this runs directly against
    the (possibly compressed) input file without a decompressed intermediate.
    """
    lines = []

    async def stdout_handler(line: bytes):
        lines.append(line.decode().rstrip())

    await run_subprocess(
        [
            "seqkit",
            "fx2tab",
            "--name",
            "--only-id",
            "--threads",
            str(proc),
            "--base-count",
            "a",
            "--base-count",
            "t",
            "--base-count",
            "g",
            "--base-count",
            "c",
            "--base-count",
            "n",
            str(new_subtraction.fasta_path),
        ],
        stdout_handler=stdout_handler,
    )

    nucleotides = {"a": 0, "t": 0, "g": 0, "c": 0, "n": 0}
    count = 0

    for line in lines:
        _, a, t, g, c, n = line.split("\t")

        nucleotides["a"] += int(a)
        nucleotides["t"] += int(t)
        nucleotides["g"] += int(g)
        nucleotides["c"] += int(c)
        nucleotides["n"] += int(n)
        count += 1

    nucleotides_sum = sum(nucleotides.values())

    intermediate.count = count
    intermediate.gc = {
        key: round(nucleotides[key] / nucleotides_sum, 3) for key in nucleotides
    }


@step
async def build_index(
    bowtie_index_path: Path,
    new_subtraction: WFNewSubtraction,
    proc: int,
    run_subprocess: RunSubprocess,
):
    """Build a Bowtie2 index.

    bowtie2-build reads gzip-compressed FASTA natively, so this runs directly
    against the (possibly compressed) input file without a decompressed
    intermediate.
    """
    await run_subprocess(
        [
            "bowtie2-build",
            "-f",
            "--threads",
            str(proc),
            str(new_subtraction.fasta_path),
            str(bowtie_index_path) + "/subtraction",
        ]
    )


@step
async def finalize(
    bowtie_index_path: Path,
    intermediate: SimpleNamespace,
    new_subtraction: WFNewSubtraction,
    proc: int,
    work_path: Path,
):
    """Upload the subtraction FASTA and index data."""
    if await asyncio.to_thread(is_gzipped, new_subtraction.fasta_path):
        compressed_path = new_subtraction.fasta_path
    else:
        compressed_path = work_path / "subtraction.fa.gz"
        await asyncio.to_thread(
            compress_file,
            new_subtraction.fasta_path,
            compressed_path,
            processes=proc,
        )

    await new_subtraction.upload(compressed_path)

    for path in bowtie_index_path.glob("*.bt2"):
        await new_subtraction.upload(path)

    await new_subtraction.finalize(intermediate.gc, intermediate.count)

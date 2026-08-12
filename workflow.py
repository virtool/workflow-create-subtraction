import asyncio
from pathlib import Path
from types import SimpleNamespace

from virtool.utils import compress_file, is_gzipped
from virtool.workflow import hooks, step
from virtool.workflow.data.subtractions import WFNewSubtraction
from virtool.workflow.errors import SubprocessFailedError
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
    count = 0
    nucleotides = {"a": 0, "t": 0, "g": 0, "c": 0, "n": 0}

    async def stdout_handler(line: bytes):
        """Add the base counts for one sequence to the running totals.

        The totals are accumulated as the lines arrive so that memory use does
        not scale with the number of sequences in the FASTA.
        """
        nonlocal count

        _, a, t, g, c, n = line.decode().rstrip().split("\t")

        nucleotides["a"] += int(a)
        nucleotides["t"] += int(t)
        nucleotides["g"] += int(g)
        nucleotides["c"] += int(c)
        nucleotides["n"] += int(n)

        count += 1

    command = [
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
    ]

    process = await run_subprocess(command, stdout_handler=stdout_handler)

    # ``run_subprocess`` treats termination by SIGTERM as success. Without this
    # check, a seqkit process killed part way through would leave us computing
    # the GC and count from a fraction of the sequences.
    if process.returncode:
        raise SubprocessFailedError(command=command, return_code=process.returncode)

    if not count:
        raise ValueError("No sequences found in subtraction FASTA")

    nucleotides_sum = sum(nucleotides.values())

    if not nucleotides_sum:
        raise ValueError("No A, T, G, C, or N bases found in subtraction FASTA")

    intermediate.count = count
    intermediate.gc = {
        key: round(nucleotides[key] / nucleotides_sum, 3) for key in nucleotides
    }


@step
async def finalize(
    intermediate: SimpleNamespace,
    new_subtraction: WFNewSubtraction,
    proc: int,
    work_path: Path,
):
    """Upload the subtraction FASTA and finalize the subtraction."""
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

    await new_subtraction.finalize(intermediate.gc, intermediate.count)

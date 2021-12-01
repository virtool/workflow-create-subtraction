import shutil
from pathlib import Path
from types import SimpleNamespace

import aiofiles
from fixtures import fixture
from virtool_core.utils import compress_file
from virtool_core.utils import is_gzipped, decompress_file
from virtool_workflow import hooks, step
from virtool_workflow.api.subtractions import SubtractionProvider
from virtool_workflow.execution.run_in_executor import FunctionExecutor
from virtool_workflow.execution.run_subprocess import RunSubprocess


@fixture
def subtraction_provider(subtraction_providers):
    return subtraction_providers[0]


@hooks.on_failure
async def delete_subtraction(subtraction_provider: SubtractionProvider):
    """Delete the subtraction in the case of a failure."""
    await subtraction_provider.delete()


@fixture
def intermediate():
    """A namespace for intermediate variables."""
    return SimpleNamespace()


@fixture
def input_path(input_files: dict) -> Path:
    """The path to the input FASTA file for the subtraction."""
    return list(input_files.values())[0]


@fixture
def fasta_path(work_path: Path) -> Path:
    """The path to the decompressed FASTA file."""
    return work_path / "subtraction.fa"


@step
async def decompress(
    fasta_path: Path,
    input_path: Path,
    run_in_executor: FunctionExecutor,
):
    """
    Decompress the input file to `fasta_path` if it is gzipped or copy it if it is uncompressed.
    """
    if is_gzipped(input_path):
        await run_in_executor(
            decompress_file,
            input_path,
            fasta_path,
        )
    else:
        await run_in_executor(
            shutil.copyfile,
            input_path,
            fasta_path
        )


@step
async def compute_fasta_gc_and_count(
    fasta_path: Path,
    intermediate: SimpleNamespace,
):
    """Compute the GC and count for the subtraction fasta file."""
    nucleotides = {
        "a": 0,
        "t": 0,
        "g": 0,
        "c": 0,
        "n": 0
    }

    count = 0

    # Go through the FASTA file getting the nucleotide counts, lengths, and number of sequences
    async with aiofiles.open(fasta_path, "r") as f:
        async for line in f:
            if line[0] == ">":
                count += 1
                continue

            for i in ["a", "t", "g", "c", "n"]:
                # Find lowercase and uppercase nucleotide characters
                nucleotides[i] += line.lower().count(i)

    nucleotides_sum = sum(nucleotides.values())

    intermediate.count = count
    intermediate.gc = {
        k: round(nucleotides[k] / nucleotides_sum, 3) for k in nucleotides}


@step
async def bowtie2_build(
    proc: int,
    fasta_path: Path,
    intermediate: SimpleNamespace,
    work_path: Path,
    run_subprocess: RunSubprocess,
):
    """Build the bowtie2 index of the fasta file."""
    bowtie_path = work_path / "index-build"
    bowtie_path.mkdir()

    command = [
        "bowtie2-build",
        "-f",
        "--threads", str(proc),
        str(fasta_path),
        str(bowtie_path) + "/subtraction",
    ]

    await run_subprocess(command)

    intermediate.bowtie_path = bowtie_path


@step
async def compress_fasta(
    fasta_path: Path,
    intermediate: SimpleNamespace,
    run_in_executor: FunctionExecutor,
    proc: int,
):
    """Compress the fasta file before uploading."""
    intermediate.compressed_path = fasta_path.parent/"subtraction.fa.gz"

    await run_in_executor(
        compress_file,
        fasta_path,
        intermediate.compressed_path,
        proc,
    )


@step
async def finalize(
    subtraction_provider: SubtractionProvider,
    intermediate: SimpleNamespace,
):
    """Upload files and fasta GC using the Virtool Jobs API."""
    await subtraction_provider.upload(intermediate.compressed_path)
    for path in intermediate.bowtie_path.glob("*.bt2"):
        await subtraction_provider.upload(path)

    await subtraction_provider.finalize(intermediate.gc, intermediate.count)

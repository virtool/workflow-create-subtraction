from types import SimpleNamespace
import aiofiles
from pathlib import Path
from virtool_workflow import step, fixture, hooks
from virtool_core.utils import compress_file
from virtool_workflow.execution.run_subprocess import RunSubprocess
from virtool_workflow.api.subtractions import SubtractionProvider
from virtool_workflow.execution.run_in_executor import FunctionExecutor

__package__ = "workflow_create_subtraction"


@hooks.on_failure
async def delete_subtraction(subtraction_provider: SubtractionProvider):
    """Delete the subtraction in the case of a failure."""
    await subtraction_provider.delete()


@fixture
def intermediate():
    """A namespace for intermediate variables."""
    return SimpleNamespace()


@fixture
def fasta_path(input_files: dict) -> Path:
    """The path to the fasta file for the subtraction."""
    return input_files["subtraction.fa"]


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

    # Go through the fasta file getting the nucleotide counts, lengths, and number of sequences
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

    return "Fasta GC computed."


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

    return "Finished bowtie2 build."


@step
async def compress_fasta(
    fasta_path: Path,
    intermediate: SimpleNamespace,
    run_in_executor: FunctionExecutor,
    proc: int,
):
    """Compress the fasta file before uploading."""
    intermediate.compressed_path = fasta_path.with_suffix(".fq.gz")

    await run_in_executor(
        compress_file(
            fasta_path,
            intermediate.compressed_path,
            proc,
        )
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

    await subtraction_provider.finalize(intermediate.gc)

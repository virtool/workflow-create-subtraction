from virtool_core.utils import compress_file
from virtool_workflow import cleanup, step

import utils
from utils import copy_or_decompress


@step
async def unpack(create_subtraction, number_of_processes, run_in_executor, work_path):
    """
    Unpack the FASTA file if it is gzipped.

    """
    await run_in_executor(
        copy_or_decompress,
        create_subtraction.fasta_path,
        work_path / "subtraction.fa",
        number_of_processes
    )


@step
async def bowtie_build(number_of_processes, run_subprocess, fasta_path, index_path, work_path):
    """
    Call `bowtie2-build` to build a Bowtie2 index for the subtraction.

    """
    command = [
        "bowtie2-build",
        "-f",
        "--threads", str(number_of_processes),
        fasta_path,
        index_path
    ]

    await run_subprocess(command)


@step
async def compress(fasta_path, number_of_processes, run_in_executor):
    """
    Compress the subtraction FASTA file for long-term storage and download.

    """
    await run_in_executor(
        compress_file,
        fasta_path,
        f"{fasta_path}.gz",
        number_of_processes
    )


@step
async def finish(create_subtraction, fasta_path, index_path):
    """
    Calculate and set the GC-content and chromosome count for the subtraction.

    TODO: Ensure finalize signature matches virtool-workflow.

    """
    await create_subtraction.upload_fasta(fasta_path)
    await create_subtraction.upload_bowtie2(index_path)

    gc, count = await utils.calculate_fasta_gc(fasta_path)

    await create_subtraction.finalize(
        count,
        gc,
    )


@cleanup
async def delete_subtraction(create_subtraction, run_in_executor):
    """
    Clean up if the job process encounters an error or is cancelled. Removes the host document from
    the database and deletes any index files.

    """
    await create_subtraction.delete()

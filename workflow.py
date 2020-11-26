import os
import shutil

from virtool_core.utils import compress_file, rm
from virtool_workflow import startup, step, cleanup
from virtool_workflow_runtime.db import VirtoolDatabase
from virtool_workflow.execute import run_subprocess

import utils


@startup
def check_db(job_params, data_path, temp_path):
    subtraction_id = job_params["subtraction_id"]
    file_id = job_params["file_id"]

    subtraction_path = os.path.join(
        data_path,
        "subtractions",
        subtraction_id.replace(" ", "_").lower()
    )

    temp_subtraction_path = os.path.join(
        temp_path,
        subtraction_id
    )

    job_params.update({
        "subtraction_path": subtraction_path,
        "temp_subtraction_path": temp_subtraction_path,

        # The path to the uploaded FASTA file to be used for creating a subtraction.
        "file_path": os.path.join(
            data_path,
            "files",
            file_id
        ),

        "temp_fasta_path": os.path.join(
            temp_subtraction_path,
            "subtraction.fa"
        ),

        "temp_index_path": os.path.join(
            temp_subtraction_path,
            "reference"
        )
    })


@step
async def make_subtraction_dir(job_params, run_in_executor):
    await run_in_executor(
        os.mkdir,
        job_params["temp_subtraction_path"]
    )


@step
async def unpack(job_params, run_in_executor, proc):
    await run_in_executor(
        utils.copy_or_decompress,
        job_params["file_path"],
        job_params["temp_fasta_path"],
        proc
    )


@step
async def set_stats(params, db: VirtoolDatabase):
    gc, count = await utils.calculate_fasta_gc(params["temp_fasta_path"])

    await db.subtraction.update_one({"_id": params["subtraction_id"]}, {
        "$set": {
            "gc": gc,
            "count": count
        }
    })


@step
async def bowtie_build(params, proc, run_subprocess, db: VirtoolDatabase):
    command = [
        "bowtie2-build",
        "-f",
        "--threads", proc,
        params["temp_fasta_path"],
        params["temp_index_path"]
    ]

    await run_subprocess(command)

    await db.subtraction.update_one({"_id": params["subtraction_id"]}, {
        "$set": {
            "ready": True
        }
    })


@step
async def compress(params, run_in_executor, proc):
    """
        Compress the subtraction FASTA file for long-term storage and download.
        """
    await run_in_executor(
        compress_file,
        params["temp_fasta_path"],
        params["temp_fasta_path"] + ".gz",
        proc
    )

    await run_in_executor(
        rm,
        params["temp_fasta_path"]
    )

    await run_in_executor(
        shutil.copytree,
        params["temp_subtraction_path"],
        params["subtraction_path"]
    )


@cleanup
async def delete_subtraction(params, run_in_executor, db: VirtoolDatabase):
    """
        Clean up if the job process encounters an error or is cancelled. Removes the host document from the database
        and deletes any index files.
    """
    try:
        await run_in_executor(
            rm,
            params["subtraction_path"],
            True
        )
    except FileNotFoundError:
        pass

    await db.subtraction.delete_one({"_id": params["subtraction_id"]})

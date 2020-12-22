import os

from virtool_workflow import fixture
from virtool_workflow_runtime.db import VirtoolDatabase
from virtool_workflow_runtime.config.configuration import db_name, db_connection_string
from virtool_workflow.storage.paths import data_path, temp_path


@fixture
def job_params(job_args, data_path, temp_path):
    subtraction_id = job_args["subtraction_id"]
    file_id = job_args["file_id"]

    subtraction_path = os.path.join(
        data_path,
        "subtractions",
        subtraction_id.replace(" ", "_").lower()
    )

    temp_subtraction_path = os.path.join(
        temp_path,
        subtraction_id
    )

    job_args.update({
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

    return job_args


@fixture
def db():
    return VirtoolDatabase(db_name(), db_connection_string())

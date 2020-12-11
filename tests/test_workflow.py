import os

import pytest

from virtool_workflow.execution.run_in_executor import run_in_executor
from virtool_workflow.fixtures.scope import WorkflowFixtureScope

import workflow


@pytest.mark.asyncio
async def test_check_db():
    with WorkflowFixtureScope() as scope:
        scope["job_params"] = {"subtraction_id": "foo", "file_id": "bar.fa.gz"}
        scope["data_path"] = f"{os.getcwd()}/virtool"
        scope["temp_path"] = f"{os.getcwd()}/temp"

        bound_function = await scope.bind(workflow.check_db)
        bound_function()

        assert scope["job_params"] == {
            "subtraction_id": "foo",

            "file_id": "bar.fa.gz",

            "subtraction_path": os.path.join(f"{os.getcwd()}/virtool", "subtractions", "foo"),

            "temp_subtraction_path": os.path.join(f"{os.getcwd()}/temp", "foo"),

            "file_path": os.path.join(f"{os.getcwd()}/virtool", "files", "bar.fa.gz"),

            "temp_fasta_path": os.path.join(f"{os.getcwd()}/temp", "foo", "subtraction.fa"),

            "temp_index_path": os.path.join(f"{os.getcwd()}/temp", "foo", "reference")
        }


@pytest.mark.asyncio
async def test_make_subtraction_dir(tmpdir):
    with WorkflowFixtureScope() as scope:
        scope["job_params"] = {"temp_subtraction_path": f"{tmpdir}/foo"}

        bound_function = await scope.bind(workflow.make_subtraction_dir)
        await bound_function()

        assert os.path.exists(scope["job_params"]["temp_subtraction_path"])
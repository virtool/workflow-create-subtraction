import os

import pytest

from virtool_workflow.fixtures.scope import WorkflowFixtureScope

import workflow


@pytest.mark.asyncio
async def test_make_subtraction_dir(tmpdir):
    with WorkflowFixtureScope() as scope:
        scope["job_params"] = {"temp_subtraction_path": f"{tmpdir}/foo"}

        bound_function = await scope.bind(workflow.make_subtraction_dir)
        await bound_function()

        assert os.path.exists(scope["job_params"]["temp_subtraction_path"])
from pathlib import Path
from types import SimpleNamespace

import pytest
from virtool.workflow.data.subtractions import WFNewSubtraction
from virtool.workflow.runtime.run_subprocess import RunSubprocess

from workflow import compute_gc_and_count

ARABIDOPSIS_PATH = Path(__file__).parent / "files/subtraction.fa.gz"


@pytest.mark.datafiles(ARABIDOPSIS_PATH)
async def test_compute_gc_and_count(
    datafiles, mocker, run_subprocess: RunSubprocess, tmp_path: Path
):
    new_subtraction = WFNewSubtraction(
        id=1,
        delete=mocker.Mock(),
        finalize=mocker.Mock(),
        name="bar",
        nickname="baz",
        path=tmp_path,
        upload=mocker.Mock(),
    )

    intermediate = SimpleNamespace()

    await compute_gc_and_count(intermediate, new_subtraction, 1, run_subprocess)

    assert intermediate.gc == {"a": 0.319, "t": 0.319, "g": 0.18, "c": 0.18, "n": 0.002}
    assert intermediate.count == 7

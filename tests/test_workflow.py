from pathlib import Path
from types import SimpleNamespace

import pytest
from virtool_workflow.data.subtractions import WFNewSubtraction

from workflow import compute_gc_and_count, decompress

ARABIDOPSIS_PATH = Path(__file__).parent / "files/subtraction.fa.gz"


@pytest.mark.datafiles(ARABIDOPSIS_PATH)
async def test_decompress_and_compute_gc(datafiles, mocker, tmp_path: Path):
    decompressed_fasta_path = tmp_path / "decompressed.fa"

    new_subtraction = WFNewSubtraction(
        id="foo",
        delete=mocker.Mock(),
        finalize=mocker.Mock(),
        name="bar",
        nickname="baz",
        path=tmp_path,
        upload=mocker.Mock(),
    )

    await decompress(decompressed_fasta_path, new_subtraction, 1)

    assert decompressed_fasta_path.is_file()

    intermediate = SimpleNamespace()

    await compute_gc_and_count(decompressed_fasta_path, intermediate)

    assert intermediate.gc == {"a": 0.319, "t": 0.319, "g": 0.18, "c": 0.18, "n": 0.002}
    assert intermediate.count == 7

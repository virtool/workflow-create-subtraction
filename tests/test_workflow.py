from pathlib import Path
from types import SimpleNamespace

import pytest
from virtool_workflow.execution.run_subprocess import run_subprocess

from workflow import compute_gc_and_count, decompress

ARABIDOPSIS_PATH = Path(__file__).parent / "files/arabidopsis_thaliana.fa.gz"


@pytest.mark.datafiles(ARABIDOPSIS_PATH)
async def test_decompress_and_compute_gc(datafiles, tmpdir):
    input_path = Path(datafiles) / "arabidopsis_thaliana.fa.gz"
    fasta_path = Path(tmpdir) / "decompress.fa"

    async def run_in_executor(func, *args):
        return func(*args)

    await decompress(fasta_path, input_path, run_in_executor)

    assert fasta_path.is_file()

    intermediate = SimpleNamespace()

    await compute_gc_and_count(fasta_path, intermediate, run_subprocess())

    print(intermediate.gc)

    assert intermediate.gc == {"a": 0.319, "t": 0.319, "g": 0.18, "c": 0.18, "n": 0.002}
    assert intermediate.count == 7

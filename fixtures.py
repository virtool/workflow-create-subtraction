from virtool_workflow import fixture


@fixture
async def fasta_path(work_path):
    return work_path / "subtraction.fa"


@fixture
async def index_path(work_path):
    return work_path / "subtraction"

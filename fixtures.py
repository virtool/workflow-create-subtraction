from virtool_workflow import fixture
from virtool_workflow_runtime.db import VirtoolDatabase
from virtool_workflow_runtime.config.configuration import db_name, db_connection_string


@fixture
def job_params(job_args):
    return dict(job_args)


@fixture
def db():
    return VirtoolDatabase(db_name(), db_connection_string())

from types import SimpleNamespace

from pyfixtures import fixture


@fixture
def intermediate() -> SimpleNamespace:
    """A namespace for intermediate variables."""
    return SimpleNamespace()

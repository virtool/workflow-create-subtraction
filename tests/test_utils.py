import pytest
import utils


@pytest.mark.parametrize("gzipped", [True, False])
@pytest.mark.parametrize("proc", [2, 4])
def test_copy_or_decompress(gzipped, proc, mocker):
    path = "/mnt/baz/test.file"
    target = "/mnt/bar/foo.file"

    mocker.patch("virtool_core.utils.is_gzipped", return_value=gzipped)

    m_copyfile = mocker.patch("shutil.copyfile")

    m_decompress_file = mocker.patch("virtool_core.utils.decompress_file", return_value=gzipped)

    utils.copy_or_decompress(path, target, proc)

    if not gzipped:
        m_decompress_file.assert_not_called()
        m_copyfile.assert_called_with(path, target)
        return

    m_decompress_file.assert_called_with(path, target, proc)
    m_copyfile.assert_not_called()


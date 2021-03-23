import os

import pytest

import utils


@pytest.mark.asyncio
async def test_calculate_fasta_gc(tmpdir):
    lines = [
        ">foo\n",
        "ATGGACTGGTTCTCTCTCTCTAGGCACTG\n",
        ">bar\n",
        "GGGTCGGCGCGGACATTCGGACTTATTAG\n",
        ">baz\n",
        "TTTCGACTTGACTTCTTNTCTCATGCGAT"
    ]

    path = os.path.join(str(tmpdir), "test.fa")

    with open(path, "w") as handle:
        for line in lines:
            handle.write(line)

    assert await utils.calculate_fasta_gc(path) == ({
        "a": 0.149,
        "t": 0.345,
        "g": 0.253,
        "c": 0.241,
        "n": 0.011
    }, 3)


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


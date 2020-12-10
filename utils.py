import shutil

import aiofiles

import virtool_core.utils


async def calculate_fasta_gc(path):
    nucleotides = {
        "a": 0,
        "t": 0,
        "g": 0,
        "c": 0,
        "n": 0
    }

    count = 0

    # Go through the fasta file getting the nucleotide counts, lengths, and number of sequences
    async with aiofiles.open(path, "r") as f:
        async for line in f:
            if line[0] == ">":
                count += 1
                continue

            for i in ["a", "t", "g", "c", "n"]:
                # Find lowercase and uppercase nucleotide characters
                nucleotides[i] += line.lower().count(i)

    nucleotides_sum = sum(nucleotides.values())

    return {k: round(nucleotides[k] / nucleotides_sum, 3) for k in nucleotides}, count


def copy_or_decompress(path: str, target: str, proc: int):
    """
    Copy the file at `path` to `target`. Decompress the file on-the-fly if it is not already compressed.

    This function will make use of `pigz` for decompression. Pass a `proc` number to assign workers to the `pigz` process.

    :param path: the path to copy from
    :param target: the path to copy to
    :param proc: the number of worker processes to allow for pigz

    """
    if virtool_core.utils.is_gzipped(path):
        virtool_core.utils.decompress_file(path, target, proc)
    else:
        shutil.copyfile(path, target)

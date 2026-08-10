# workflow-create-subtraction

A workflow for creating Virtool subtractions.

## Steps

1. Compute sequence count and nucleotide distribution using `seqkit`.
2. Build index for subtraction using `bowtie2-build`.
3. Compress the FASTA file for upload and long term retention, if it isn't already compressed.
4. Upload the FASTA and index files to the Virtool server and add sequence count and nucleotide distribution
data to the subtraction record.

`seqkit` and `bowtie2-build` both read gzip-compressed FASTA natively, so the workflow never decompresses
the input file to disk — this avoids the disk space blowup that comes from holding the compressed input,
a decompressed copy, and the Bowtie2 index all at once for large subtraction FASTA files.

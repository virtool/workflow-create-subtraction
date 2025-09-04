# workflow-create-subtraction

A workflow for creating Virtool subtractions.

## Steps

1. Decompress FASTA file if necessary.
2. Build index for subtraction using `bowtie-build`.
3. Compress the FASTA file for upload and long term retention.
4. Upload the index files to the Virtool server and add sequence count and nucleotide distribution data to
the subtraction record.

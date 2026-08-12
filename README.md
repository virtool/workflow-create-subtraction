# workflow-create-subtraction

A workflow for creating Virtool subtractions.

## Steps

1. Compute sequence count and nucleotide distribution using `seqkit`.
2. Compress the FASTA file for upload and long term retention, if it isn't already compressed.
3. Upload the FASTA to the Virtool server and add sequence count and nucleotide distribution
data to the subtraction record.

`seqkit` reads gzip-compressed FASTA natively, so the workflow never decompresses the input file to
disk — this avoids the disk space blowup that comes from holding both the compressed input and a
decompressed copy for large subtraction FASTA files.

Bowtie2 indexes are not built here. Analysis workflows that need one build it locally from the
subtraction FASTA.

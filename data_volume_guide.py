"""Static reference data for the Data volume reference guide (spec 007).

This is documentation content only — a set of rough, human-curated planning
ranges to help a user pick a reasonable dataset size when no measured
project volume is available yet. It intentionally contains no calculation
logic and is never used to derive or scale a dataset size; it must not be
imported by anything under ``cbio_cost`` (the calculation engine).
"""

from __future__ import annotations

DATA_VOLUME_GUIDE: list[dict[str, str]] = [
    {
        "format": "4× WGS FASTQ",
        "size": "~12–20 GB/sample",
        "notes": "Low-pass WGS; sequencing yield varies by platform",
    },
    {
        "format": "4× WGS CRAM",
        "size": "~5–8 GB/sample",
        "notes": "Reference-based compression; approximate planning range",
    },
    {
        "format": "12× WGS FASTQ",
        "size": "~35–50 GB/sample",
        "notes": "Medium-depth WGS; approximate planning range",
    },
    {
        "format": "12× WGS CRAM",
        "size": "~12–20 GB/sample",
        "notes": "Reference-based compression; approximate planning range",
    },
    {"format": "30× WGS FASTQ", "size": "~80–120 GB/sample", "notes": "Paired-end compressed FASTQ"},
    {"format": "30× WGS BAM", "size": "~80–120 GB/sample", "notes": "Can vary substantially"},
    {"format": "30× WGS CRAM", "size": "~30–50 GB/sample", "notes": "Reference-based compression"},
    {
        "format": "30× WGS gVCF",
        "size": "~5–10 GB/sample",
        "notes": (
            "Pipeline/caller dependent; does not necessarily scale linearly with sequencing depth"
        ),
    },
    {"format": "30× WGS QC + indexes", "size": "~1–5 GB/sample", "notes": "Usually relatively small"},
    {"format": "WES FASTQ", "size": "~8–15 GB/sample", "notes": "Depends strongly on target and sequencing depth"},
    {"format": "WES BAM/CRAM", "size": "~5–10 GB/sample", "notes": "Rough planning range"},
    {"format": "RNA-seq FASTQ", "size": "~5–15 GB/sample", "notes": "Highly dependent on read count"},
    {"format": "RNA-seq BAM", "size": "~5–20 GB/sample", "notes": "Alignment size varies with workflow"},
    {"format": "Genotyping array", "size": "<1 GB/sample", "notes": "Usually small relative to sequencing"},
    {
        "format": "Joint VCF/BCF",
        "size": "Project-level",
        "notes": "Depends strongly on cohort size and variant representation",
    },
]

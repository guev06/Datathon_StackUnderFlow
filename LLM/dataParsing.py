"""Backward-compatible imports for PrimeVul data ingestion helpers."""

from LLM.layer1_data_ingestion import (
    Record,
    _read_records,
    count_targets,
    iter_parser_batches,
    parser,
)

__all__ = [
    "Record",
    "_read_records",
    "count_targets",
    "iter_parser_batches",
    "parser",
]

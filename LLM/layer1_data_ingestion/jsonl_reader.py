from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping
from os import PathLike
from pathlib import Path
from typing import Any


Record = Mapping[str, Any]


def _read_records(data: str | PathLike[str] | Iterable[Record]) -> Iterator[Record]:
    if isinstance(data, (str, PathLike)):
        path = Path(data)
        with path.open(encoding="utf-8") as source:
            for line_number, line in enumerate(source, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(
                        f"Invalid JSON on line {line_number} of {path}"
                    ) from error
                if not isinstance(record, Mapping):
                    raise ValueError(
                        f"Expected a JSON object on line {line_number} of {path}"
                    )
                yield record
        return

    yield from data


def count_targets(data: str | PathLike[str]) -> tuple[int, int]:
    """Count PrimeVul negative and positive labels without loading code into memory."""
    negatives = 0
    positives = 0
    for record_number, record in enumerate(_read_records(data), start=1):
        target = record.get("target")
        if (
            not isinstance(target, int)
            or isinstance(target, bool)
            or target not in (0, 1)
        ):
            raise ValueError(f"Record {record_number} must have target 0 or 1")
        if target == 1:
            positives += 1
        else:
            negatives += 1
    if negatives + positives == 0:
        raise ValueError(f"No records found in {data}")
    return negatives, positives

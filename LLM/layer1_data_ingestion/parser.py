from __future__ import annotations

import random
from collections.abc import Callable, Iterable, Iterator, Mapping
from os import PathLike
from typing import Any

from .jsonl_reader import Record, _read_records


Tokenizer = Callable[..., Mapping[str, Any]]


def parser(
    data: str | PathLike[str] | Iterable[Record],
    tokenizer: Tokenizer,
    max_length: int = 128,
    batch_size: int = 2,
) -> dict[str, list[Any]]:
    """Tokenize PrimeVul records and collect all batches in memory."""
    if max_length < 1:
        raise ValueError("max_length must be at least 1")
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    result: dict[str, list[Any]] = {}
    for batch in iter_parser_batches(data, tokenizer, max_length, batch_size):
        for field, values in batch.items():
            result.setdefault(field, []).extend(values)
    return result


def iter_parser_batches(
    data: str | PathLike[str] | Iterable[Record],
    tokenizer: Tokenizer,
    max_length: int = 128,
    batch_size: int = 2,
) -> Iterator[dict[str, list[Any]]]:
    """Yield tokenized PrimeVul batches without retaining the full dataset."""
    if max_length < 1:
        raise ValueError("max_length must be at least 1")
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    batch_functions: list[str] = []
    batch_labels: list[int] = []

    def tokenize_batch() -> dict[str, list[Any]]:
        if not batch_functions:
            return {}
        encoded = tokenizer(
            batch_functions,
            truncation=True,
            padding="max_length",
            max_length=max_length,
        )
        for field, values in encoded.items():
            if field == "labels":
                raise ValueError("Tokenizer output must not contain a 'labels' field")
            if len(values) != len(batch_functions):
                raise ValueError(
                    f"Tokenizer field {field!r} returned {len(values)} items for "
                    f"{len(batch_functions)} functions"
                )
        tokenized = dict(encoded)
        tokenized["labels"] = list(batch_labels)
        batch_functions.clear()
        batch_labels.clear()
        return tokenized

    for record_number, record in enumerate(_read_records(data), start=1):
        if not isinstance(record, Mapping):
            raise ValueError(f"Expected a JSON object for record {record_number}")

        function = record.get("func")
        target = record.get("target")
        if not isinstance(function, str):
            raise ValueError(f"Record {record_number} has no string 'func' field")
        if (
            not isinstance(target, int)
            or isinstance(target, bool)
            or target not in (0, 1)
        ):
            raise ValueError(f"Record {record_number} must have target 0 or 1")

        batch_functions.append(function)
        batch_labels.append(target)
        if len(batch_functions) == batch_size:
            yield tokenize_batch()

    if batch_functions:
        yield tokenize_batch()


def source_windows(source: str, max_length: int) -> list[str]:
    """Split source into the same non-overlapping byte windows used for inference."""
    if max_length < 3:
        raise ValueError("max_length must be at least 3 for code, BOS, and EOS")
    window_size = max_length - 2
    source_bytes = source.encode("utf-8")
    return [
        source_bytes[index : index + window_size].decode(
            "utf-8", errors="replace"
        )
        for index in range(0, len(source_bytes), window_size)
    ] or [""]


def iter_window_parser_batches(
    data: str | PathLike[str] | Iterable[Record],
    tokenizer: Tokenizer,
    max_length: int = 128,
    batch_size: int = 2,
    progress: bool = False,
    max_windows_per_function: int | None = None,
) -> Iterator[dict[str, list[Any]]]:
    """Yield all windows for each function, retaining per-function labels."""
    if max_length < 3:
        raise ValueError("max_length must be at least 3")
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    if max_windows_per_function is not None and max_windows_per_function < 1:
        raise ValueError("max_windows_per_function must be at least 1")

    functions: list[str] = []
    labels: list[int] = []
    batch_number = 0

    def tokenize_batch() -> dict[str, list[Any]]:
        nonlocal batch_number
        batch_number += 1
        if progress and (batch_number == 1 or batch_number % 10 == 0):
            print(
                f"Preparing data batch {batch_number}: "
                f"{len(functions)} functions",
                flush=True,
            )
        windowed_functions = []
        for function in functions:
            windows = source_windows(function, max_length)
            if (
                max_windows_per_function is not None
                and len(windows) > max_windows_per_function
            ):
                windows = random.sample(windows, max_windows_per_function)
            windowed_functions.append(windows)
        flattened_windows = [
            window
            for windows in windowed_functions
            for window in windows
        ]
        if progress and (batch_number == 1 or batch_number % 10 == 0):
            print(
                f"Tokenizing data batch {batch_number}: "
                f"{len(flattened_windows)} windows",
                flush=True,
            )
        encoded = tokenizer(
            flattened_windows,
            truncation=True,
            padding="max_length",
            max_length=max_length,
        )
        for field, values in encoded.items():
            if field == "labels":
                raise ValueError("Tokenizer output must not contain a 'labels' field")
            if len(values) != len(flattened_windows):
                raise ValueError(
                    f"Tokenizer field {field!r} returned {len(values)} items for "
                    f"{len(flattened_windows)} windows"
                )
        tokenized = dict(encoded)
        tokenized["labels"] = list(labels)
        tokenized["window_counts"] = [len(windows) for windows in windowed_functions]
        functions.clear()
        labels.clear()
        return tokenized

    for record_number, record in enumerate(_read_records(data), start=1):
        if not isinstance(record, Mapping):
            raise ValueError(f"Expected a JSON object for record {record_number}")
        function = record.get("func")
        target = record.get("target")
        if not isinstance(function, str):
            raise ValueError(f"Record {record_number} has no string 'func' field")
        if (
            not isinstance(target, int)
            or isinstance(target, bool)
            or target not in (0, 1)
        ):
            raise ValueError(f"Record {record_number} must have target 0 or 1")

        functions.append(function)
        labels.append(target)
        if len(functions) == batch_size:
            yield tokenize_batch()

    if functions:
        yield tokenize_batch()

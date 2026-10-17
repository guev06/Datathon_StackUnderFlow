from __future__ import annotations

from os import PathLike
from typing import Any

import torch
from torch import Tensor
from torch.nn import functional as F

from LLM.layer1_data_ingestion import iter_window_parser_batches
from LLM.layer5_classification import VulnerabilityClassifier


def default_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def tensor_batch(
    batch: dict[str, list[Any]], device: torch.device
) -> tuple[Tensor, Tensor, Tensor]:
    input_ids = torch.tensor(batch["input_ids"], dtype=torch.long, device=device)
    attention_mask = torch.tensor(
        batch["attention_mask"], dtype=torch.long, device=device
    )
    labels = torch.tensor(batch["labels"], dtype=torch.long, device=device)
    return input_ids, attention_mask, labels


def tensor_window_batch(
    batch: dict[str, list[Any]], device: torch.device
) -> tuple[Tensor, Tensor, Tensor, list[int]]:
    input_ids = torch.tensor(batch["input_ids"], dtype=torch.long, device=device)
    attention_mask = torch.tensor(
        batch["attention_mask"], dtype=torch.long, device=device
    )
    labels = torch.tensor(batch["labels"], dtype=torch.long, device=device)
    window_counts = batch["window_counts"]
    if any(count < 1 for count in window_counts):
        raise ValueError("Each source function must have at least one window")
    if sum(window_counts) != input_ids.shape[0]:
        raise ValueError("window_counts must sum to the number of tokenized windows")
    return input_ids, attention_mask, labels, window_counts


def aggregate_window_probabilities(
    logits: Tensor, window_counts: list[int]
) -> Tensor:
    """Average class probabilities so each source function gets one prediction."""
    if any(count < 1 for count in window_counts):
        raise ValueError("Each source function must have at least one window")
    if sum(window_counts) != logits.shape[0]:
        raise ValueError("window_counts must sum to the number of window logits")
    probabilities = F.softmax(logits, dim=-1)
    return torch.stack(
        [window.mean(dim=0) for window in torch.split(probabilities, window_counts)]
    )


def run_evaluation(
    model: VulnerabilityClassifier,
    data: str | PathLike[str],
    batch_size: int,
    device: torch.device,
    progress: bool = False,
    max_windows_per_function: int | None = None,
) -> dict[str, float | int]:
    model.eval()
    loss_total = 0.0
    total = 0
    correct = 0
    true_positive = 0
    false_positive = 0
    false_negative = 0
    true_negative = 0

    batches = iter_window_parser_batches(
        data,
        model.tokenizer,
        max_length=model.config.max_length,
        batch_size=batch_size,
        progress=progress,
        max_windows_per_function=max_windows_per_function,
    )
    with torch.inference_mode():
        for batch_number, batch in enumerate(batches, start=1):
            input_ids, attention_mask, labels, window_counts = tensor_window_batch(
                batch, device
            )
            show_progress = progress and (
                batch_number == 1 or batch_number % 10 == 0
            )
            if show_progress:
                print(
                    f"Evaluation batch {batch_number}: "
                    f"{labels.numel()} functions, {input_ids.shape[0]} windows",
                    flush=True,
                )
            logits = model(input_ids, attention_mask, progress=show_progress)
            probabilities = aggregate_window_probabilities(logits, window_counts)
            predictions = probabilities.argmax(dim=-1)
            loss_total += F.nll_loss(
                probabilities.clamp_min(torch.finfo(probabilities.dtype).tiny).log(),
                labels,
                reduction="sum",
            ).item()
            correct += int((predictions == labels).sum().item())
            true_positive += int(((predictions == 1) & (labels == 1)).sum().item())
            false_positive += int(((predictions == 1) & (labels == 0)).sum().item())
            false_negative += int(((predictions == 0) & (labels == 1)).sum().item())
            true_negative += int(((predictions == 0) & (labels == 0)).sum().item())
            total += labels.numel()
            if show_progress:
                print(
                    f"Completed evaluation batch {batch_number} "
                    f"({total} functions evaluated)",
                    flush=True,
                )

    if total == 0:
        raise ValueError(f"No evaluation records found in {data}")

    precision_denominator = true_positive + false_positive
    recall_denominator = true_positive + false_negative
    precision = (
        true_positive / precision_denominator if precision_denominator else 0.0
    )
    recall = true_positive / recall_denominator if recall_denominator else 0.0
    f1_denominator = precision + recall
    f1 = 2 * precision * recall / f1_denominator if f1_denominator else 0.0
    return {
        "loss": loss_total / total,
        "accuracy": correct / total,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "examples": total,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
    }

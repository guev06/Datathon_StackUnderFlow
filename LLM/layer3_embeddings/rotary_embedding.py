from __future__ import annotations

import torch
from torch import Tensor


def _apply_rotary_embedding(values: Tensor, theta: float) -> Tensor:
    sequence_length = values.shape[-2]
    head_dimension = values.shape[-1]
    frequencies = 1.0 / (
        theta
        ** (
            torch.arange(
                0,
                head_dimension,
                2,
                device=values.device,
                dtype=torch.float32,
            )
            / head_dimension
        )
    )
    positions = torch.arange(
        sequence_length, device=values.device, dtype=torch.float32
    )
    angles = torch.outer(positions, frequencies)
    cosine = angles.cos().to(dtype=values.dtype)[None, None, :, :]
    sine = angles.sin().to(dtype=values.dtype)[None, None, :, :]

    even = values[..., 0::2]
    odd = values[..., 1::2]
    rotated = torch.stack(
        (even * cosine - odd * sine, even * sine + odd * cosine),
        dim=-1,
    )
    return rotated.flatten(start_dim=-2)

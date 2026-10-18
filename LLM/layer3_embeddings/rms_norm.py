from __future__ import annotations

import torch
from torch import Tensor, nn


class RMSNorm(nn.Module):
    def __init__(self, dimension: int, epsilon: float = 1e-6) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dimension))
        self.epsilon = epsilon

    def forward(self, values: Tensor) -> Tensor:
        normalized = values * torch.rsqrt(
            values.square().mean(dim=-1, keepdim=True) + self.epsilon
        )
        return normalized * self.weight

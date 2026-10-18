from __future__ import annotations

from torch import Tensor, nn
from torch.nn import functional as F


class SwiGLU(nn.Module):
    def __init__(self, dimension: int, dropout: float) -> None:
        super().__init__()
        hidden_dimension = 4 * dimension
        self.gate = nn.Linear(dimension, hidden_dimension, bias=False)
        self.value = nn.Linear(dimension, hidden_dimension, bias=False)
        self.output = nn.Linear(hidden_dimension, dimension, bias=False)
        self.dropout = nn.Dropout(dropout)

    def forward(self, values: Tensor) -> Tensor:
        hidden = F.silu(self.gate(values)) * self.value(values)
        return self.dropout(self.output(hidden))

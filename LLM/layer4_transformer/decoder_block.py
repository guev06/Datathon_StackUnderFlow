from __future__ import annotations

from torch import Tensor, nn

from LLM.layer3_embeddings import DecoderConfig, RMSNorm
from .causal_self_attention import CausalSelfAttention
from .swiglu import SwiGLU


class DecoderBlock(nn.Module):
    def __init__(self, config: DecoderConfig) -> None:
        super().__init__()
        self.attention_norm = RMSNorm(config.d_model)
        self.attention = CausalSelfAttention(config)
        self.feed_forward_norm = RMSNorm(config.d_model)
        self.feed_forward = SwiGLU(config.d_model, config.dropout)
        self.residual_dropout = nn.Dropout(config.dropout)

    def forward(self, values: Tensor, attention_mask: Tensor) -> Tensor:
        values = values + self.residual_dropout(
            self.attention(self.attention_norm(values), attention_mask)
        )
        return values + self.residual_dropout(
            self.feed_forward(self.feed_forward_norm(values))
        )

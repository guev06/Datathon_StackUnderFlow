from __future__ import annotations

import torch
from torch import Tensor, nn
from torch.nn import functional as F

from LLM.layer3_embeddings import DecoderConfig, _apply_rotary_embedding


class CausalSelfAttention(nn.Module):
    def __init__(self, config: DecoderConfig) -> None:
        super().__init__()
        self.num_heads = config.num_heads
        self.head_dimension = config.d_model // config.num_heads
        self.rope_theta = config.rope_theta
        self.qkv = nn.Linear(config.d_model, 3 * config.d_model, bias=False)
        self.output = nn.Linear(config.d_model, config.d_model, bias=False)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, values: Tensor, attention_mask: Tensor) -> Tensor:
        batch_size, sequence_length, dimension = values.shape
        query, key, value = self.qkv(values).chunk(3, dim=-1)

        def split_heads(tensor: Tensor) -> Tensor:
            return tensor.view(
                batch_size,
                sequence_length,
                self.num_heads,
                self.head_dimension,
            ).transpose(1, 2)

        query = _apply_rotary_embedding(split_heads(query), self.rope_theta)
        key = _apply_rotary_embedding(split_heads(key), self.rope_theta)
        value = split_heads(value)

        causal_mask = torch.ones(
            sequence_length,
            sequence_length,
            device=values.device,
            dtype=torch.bool,
        ).tril()
        attention_mask = causal_mask[None, None, :, :] & attention_mask[
            :, None, None, :
        ].bool()
        attended = F.scaled_dot_product_attention(
            query,
            key,
            value,
            attn_mask=attention_mask,
            dropout_p=self.dropout.p if self.training else 0.0,
        )
        attended = attended.transpose(1, 2).contiguous().view(
            batch_size, sequence_length, dimension
        )
        return self.output(attended)

from __future__ import annotations

from dataclasses import dataclass

from LLM.layer2_tokenization import ByteCodeTokenizer


@dataclass(frozen=True)
class DecoderConfig:
    vocab_size: int = ByteCodeTokenizer.vocab_size
    max_length: int = 128
    d_model: int = 32
    num_heads: int = 4
    num_layers: int = 2
    dropout: float = 0.1
    num_classes: int = 2
    rope_theta: float = 10000.0

    def __post_init__(self) -> None:
        if self.vocab_size < 1 or self.max_length < 3:
            raise ValueError("vocab_size must be positive and max_length at least 3")
        if self.d_model < 1 or self.num_heads < 1:
            raise ValueError("d_model and num_heads must be positive")
        if self.d_model % self.num_heads != 0:
            raise ValueError("d_model must be divisible by num_heads")
        if (self.d_model // self.num_heads) % 2 != 0:
            raise ValueError("Each attention head dimension must be even for RoPE")
        if self.num_layers < 1:
            raise ValueError("num_layers must be positive")
        if not 0.0 <= self.dropout < 1.0:
            raise ValueError("dropout must be in [0, 1)")
        if self.num_classes != 2:
            raise ValueError("Vulnerability classification requires two classes")

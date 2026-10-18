"""Backward-compatible imports for the model's layer-specific modules."""

from LLM.layer2_tokenization import ByteCodeTokenizer
from LLM.layer3_embeddings import DecoderConfig, RMSNorm, _apply_rotary_embedding
from LLM.layer4_transformer import CausalSelfAttention, DecoderBlock, SwiGLU
from LLM.layer5_classification import VulnerabilityClassifier

__all__ = [
    "ByteCodeTokenizer",
    "DecoderConfig",
    "RMSNorm",
    "_apply_rotary_embedding",
    "CausalSelfAttention",
    "DecoderBlock",
    "SwiGLU",
    "VulnerabilityClassifier",
]

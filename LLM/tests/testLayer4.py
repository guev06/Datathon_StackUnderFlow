import torch

from LLM.layer2_tokenization import ByteCodeTokenizer
from LLM.layer3_embeddings import DecoderConfig, RMSNorm
from LLM.layer4_transformer import CausalSelfAttention, DecoderBlock, SwiGLU
from LLM.layer5_classification import VulnerabilityClassifier


def test_layer_4() -> None:
    """Exercise normalization, causal attention, SwiGLU, and decoder blocks."""
    torch.manual_seed(4)
    config = DecoderConfig(
        max_length=128,
        d_model=32,
        num_heads=4,
        num_layers=2,
        dropout=0.0,
    )
    model = VulnerabilityClassifier(config, ByteCodeTokenizer())
    batch = model.tokenizer(
        ["int f(void) { return 0; }", "void g(void) { work(); }"],
        truncation=True,
        padding="max_length",
        max_length=config.max_length,
    )
    input_ids = torch.tensor(batch["input_ids"], dtype=torch.long)
    attention_mask = torch.tensor(batch["attention_mask"], dtype=torch.long)
    hidden = model.token_embeddings(input_ids)
    print("Test input embedding shape:")
    print(tuple(hidden.shape))

    normalization = RMSNorm(config.d_model)
    normalized = normalization(hidden)
    print("\nRMSNorm.forward(embeddings):")
    print(
        {
            "shape": tuple(normalized.shape),
            "first_vector_values": normalized[0, 0, :6].detach().tolist(),
        }
    )

    attention = CausalSelfAttention(config)
    attention_output = attention(normalized, attention_mask)
    print("\nCausalSelfAttention.forward(normalized, attention_mask):")
    print(
        {
            "shape": tuple(attention_output.shape),
            "first_vector_values": attention_output[0, 0, :6].detach().tolist(),
        }
    )

    feed_forward = SwiGLU(config.d_model, config.dropout)
    feed_forward_output = feed_forward(normalized)
    print("\nSwiGLU.forward(normalized):")
    print(
        {
            "shape": tuple(feed_forward_output.shape),
            "first_vector_values": feed_forward_output[0, 0, :6].detach().tolist(),
        }
    )

    block = DecoderBlock(config)
    block_output = block(hidden, attention_mask)
    print("\nDecoderBlock.forward(embeddings, attention_mask):")
    print(
        {
            "shape": tuple(block_output.shape),
            "first_vector_values": block_output[0, 0, :6].detach().tolist(),
        }
    )

    full_decoder_output = hidden
    for block_number, decoder_block in enumerate(model.blocks, start=1):
        full_decoder_output = decoder_block(full_decoder_output, attention_mask)
        print(f"\nModel decoder block {block_number} output:")
        print(
            {
                "shape": tuple(full_decoder_output.shape),
                "first_vector_values": (
                    full_decoder_output[0, 0, :6].detach().tolist()
                ),
            }
        )

    print("\nFull Layer 4 output: all decoder blocks:")
    print(
        {
            "shape": tuple(full_decoder_output.shape),
            "batch_size": full_decoder_output.shape[0],
            "sequence_length": full_decoder_output.shape[1],
            "hidden_dimension": full_decoder_output.shape[2],
        }
    )
    assert full_decoder_output.shape == (
        2,
        config.max_length,
        config.d_model,
    )


if __name__ == "__main__":
    test_layer_4()

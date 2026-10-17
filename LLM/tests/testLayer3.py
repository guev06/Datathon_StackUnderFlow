import torch

from LLM.layer2_tokenization import ByteCodeTokenizer
from LLM.layer3_embeddings import DecoderConfig, _apply_rotary_embedding
from LLM.layer5_classification import VulnerabilityClassifier


def test_layer_3() -> None:
    """Exercise token embeddings and rotary position encoding."""
    torch.manual_seed(3)
    config = DecoderConfig(
        max_length=128,
        d_model=32,
        num_heads=4,
        num_layers=2,
        dropout=0.0,
    )
    model = VulnerabilityClassifier(config, ByteCodeTokenizer())
    tokenized = model.tokenizer(
        ["int f(void) { return 0; }", "void g(void) { work(); }"],
        truncation=True,
        padding="max_length",
        max_length=config.max_length,
    )
    input_ids = torch.tensor(tokenized["input_ids"], dtype=torch.long)
    print("Token IDs passed into the vector embedding:")
    print(input_ids[0, :10].tolist())

    embedded = model.token_embeddings(input_ids)
    print("\nmodel.token_embeddings(input_ids):")
    print(
        {
            "shape": tuple(embedded.shape),
            "first_vector_values": embedded[0, 0, :6].detach().tolist(),
        }
    )
    assert embedded.shape == (
        input_ids.shape[0],
        config.max_length,
        config.d_model,
    )

    projected = model.blocks[0].attention.qkv(embedded)
    query, key, _ = projected.chunk(3, dim=-1)
    head_dimension = config.d_model // config.num_heads

    def to_heads(values: torch.Tensor) -> torch.Tensor:
        return values.view(
            input_ids.shape[0],
            config.max_length,
            config.num_heads,
            head_dimension,
        ).transpose(1, 2)

    query_heads = to_heads(query)
    key_heads = to_heads(key)
    print("\nQ/K/V linear projection and head reshape:")
    print(
        {
            "projected_shape": tuple(projected.shape),
            "query_heads_shape": tuple(query_heads.shape),
            "key_heads_shape": tuple(key_heads.shape),
        }
    )

    rotated_query = _apply_rotary_embedding(query_heads, config.rope_theta)
    rotated_key = _apply_rotary_embedding(key_heads, config.rope_theta)
    print("\n_apply_rotary_embedding(query) and _apply_rotary_embedding(key):")
    print(
        {
            "rotated_query_shape": tuple(rotated_query.shape),
            "rotated_key_shape": tuple(rotated_key.shape),
            "query_first_values": rotated_query[0, 0, 0, :6].detach().tolist(),
            "key_first_values": rotated_key[0, 0, 0, :6].detach().tolist(),
        }
    )
    assert rotated_query.shape == query_heads.shape
    assert rotated_key.shape == key_heads.shape

    print("\nFull Layer 3 output: embedded vectors with RoPE applied to Q and K:")
    print(
        {
            "input_ids_shape": tuple(input_ids.shape),
            "embedding_shape": tuple(embedded.shape),
            "rotary_query_shape": tuple(rotated_query.shape),
            "rotary_key_shape": tuple(rotated_key.shape),
        }
    )


if __name__ == "__main__":
    test_layer_3()

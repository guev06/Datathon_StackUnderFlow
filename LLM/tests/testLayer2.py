from LLM.layer2_tokenization import ByteCodeTokenizer


def test_layer_2() -> None:
    """Exercise the byte-level tokenizer on small source-code examples."""
    source_code = [
        "int safe(void) { return 0; }",
        "void unsafe(char *p) { strcpy(dst, p); }",
    ]
    tokenizer = ByteCodeTokenizer()
    print("ByteCodeTokenizer instance:")
    print(tokenizer)

    token_ids = tokenizer(
        source_code,
        truncation=True,
        padding="max_length",
        max_length=128,
    )
    print("\nByteCodeTokenizer.__call__(source_code):")
    print(
        {
            "input_ids": [row[:12] for row in token_ids["input_ids"]],
            "attention_mask": [row[:12] for row in token_ids["attention_mask"]],
            "full_sequence_length": len(token_ids["input_ids"][0]),
        }
    )
    assert len(token_ids["input_ids"]) == len(source_code)
    assert all(len(row) == 128 for row in token_ids["input_ids"])
    assert token_ids["input_ids"][0][0] == tokenizer.bos_token_id

    print("\nFull Layer 2 output:")
    print(
        {
            "vocabulary_size": tokenizer.vocab_size,
            "batch_size": len(token_ids["input_ids"]),
            "token_sequence_length": len(token_ids["input_ids"][0]),
            "attention_tokens_per_example": [
                sum(mask) for mask in token_ids["attention_mask"]
            ],
        }
    )


if __name__ == "__main__":
    test_layer_2()

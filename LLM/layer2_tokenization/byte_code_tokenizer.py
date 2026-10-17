from __future__ import annotations


class ByteCodeTokenizer:
    """A small deterministic tokenizer that represents UTF-8 bytes as tokens."""

    pad_token_id = 0
    bos_token_id = 1
    eos_token_id = 2
    vocab_size = 259

    def __call__(
        self,
        texts: list[str],
        *,
        truncation: bool = True,
        padding: str = "max_length",
        max_length: int = 128,
    ) -> dict[str, list[list[int]]]:
        if max_length < 3:
            raise ValueError("max_length must be at least 3 for code, BOS, and EOS")
        if not truncation:
            raise ValueError("ByteCodeTokenizer requires truncation=True")
        if padding != "max_length":
            raise ValueError("ByteCodeTokenizer requires padding='max_length'")

        input_ids: list[list[int]] = []
        attention_mask: list[list[int]] = []
        for text in texts:
            if not isinstance(text, str):
                raise TypeError("Tokenizer inputs must be strings")
            encoded = [self.bos_token_id]
            encoded.extend(byte + 3 for byte in text.encode("utf-8"))
            encoded.append(self.eos_token_id)
            encoded = encoded[:max_length]
            mask = [1] * len(encoded)
            padding_length = max_length - len(encoded)
            encoded.extend([self.pad_token_id] * padding_length)
            mask.extend([0] * padding_length)
            input_ids.append(encoded)
            attention_mask.append(mask)
        return {"input_ids": input_ids, "attention_mask": attention_mask}

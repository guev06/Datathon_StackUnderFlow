import json
import tempfile
from pathlib import Path

import torch
from torch.nn import functional as F

from LLM.layer2_tokenization import ByteCodeTokenizer
from LLM.layer3_embeddings import DecoderConfig
from LLM.layer5_classification import VulnerabilityClassifier
from LLM.training import class_aware_contrastive_loss


def test_layer_5() -> None:
    """Exercise final normalization, binary classification, and JSON prediction."""
    torch.manual_seed(5)
    config = DecoderConfig(
        max_length=128,
        d_model=32,
        num_heads=4,
        num_layers=2,
        dropout=0.0,
    )
    model = VulnerabilityClassifier(config, ByteCodeTokenizer())
    source = "int f(void) { return 0; }"
    second_source = "void g(void) { work(); }"
    tokenized = model.tokenizer(
        [source, second_source],
        truncation=True,
        padding="max_length",
        max_length=config.max_length,
    )
    input_ids = torch.tensor(tokenized["input_ids"], dtype=torch.long)
    attention_mask = torch.tensor(tokenized["attention_mask"], dtype=torch.long)

    hidden = model.token_embeddings(input_ids)
    for decoder_block in model.blocks:
        hidden = decoder_block(hidden, attention_mask)
    normalized = model.final_norm(hidden)
    print("model.final_norm(decoder_output):")
    print(
        {
            "shape": tuple(normalized.shape),
            "first_vector_values": normalized[0, 0, :6].detach().tolist(),
        }
    )

    positions = torch.arange(config.max_length).unsqueeze(0).expand_as(attention_mask)
    last_token_indices = positions.masked_fill(attention_mask == 0, -1).max(dim=1).values
    assert torch.all(last_token_indices >= 0)
    assert torch.all(last_token_indices < config.max_length)
    pooled = normalized[
        torch.arange(input_ids.shape[0]),
        last_token_indices,
    ]
    print("\nSelect last non-padding token:")
    print(
        {
            "last_token_indices": last_token_indices.tolist(),
            "pooled_shape": tuple(pooled.shape),
            "pooled_values": pooled[0, :6].detach().tolist(),
        }
    )

    logits = model.classifier(pooled)
    probabilities = F.softmax(logits, dim=-1)
    print("\nmodel.classifier(pooled) and softmax(logits):")
    print(
        {
            "logits": logits.detach().tolist(),
            "probabilities": probabilities.detach().tolist(),
            "class_order": ["not_vulnerable", "vulnerable"],
        }
    )

    full_logits = model(input_ids, attention_mask)
    print("\nVulnerabilityClassifier.forward(input_ids, attention_mask):")
    print(
        {
            "shape": tuple(full_logits.shape),
            "logits": full_logits.detach().tolist(),
        }
    )
    assert full_logits.shape == (2, config.num_classes)
    assert model.lm_head.weight is model.token_embeddings.weight

    auxiliary_logits, pooled_embeddings, lm_logits = model.forward_with_aux(
        input_ids, attention_mask
    )
    assert auxiliary_logits.shape == (2, config.num_classes)
    assert pooled_embeddings.shape == (2, config.d_model)
    assert lm_logits.shape == (
        2,
        config.max_length,
        config.vocab_size,
    )
    next_token_targets = input_ids[:, 1:].clone()
    next_token_targets.masked_fill_(attention_mask[:, 1:] == 0, -100)
    auxiliary_loss = F.cross_entropy(
        lm_logits[:, :-1, :].reshape(-1, config.vocab_size),
        next_token_targets.reshape(-1),
        ignore_index=-100,
    )
    combined_loss = F.cross_entropy(
        auxiliary_logits, torch.tensor([0, 1])
    ) + 0.02 * auxiliary_loss
    combined_loss.backward()
    assert model.classifier.weight.grad is not None
    assert model.token_embeddings.weight.grad is not None

    contrastive_embeddings = torch.tensor(
        [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.1, 0.9]],
        requires_grad=True,
    )
    contrastive_labels = torch.tensor([0, 0, 1, 1])
    contrastive_loss = class_aware_contrastive_loss(
        contrastive_embeddings, contrastive_labels
    )
    contrastive_loss.backward()
    assert torch.isfinite(contrastive_loss)
    assert contrastive_embeddings.grad is not None

    prediction = json.loads(model.predict_json(source))
    print("\nmodel.predict_json(source):")
    print(prediction)
    assert isinstance(prediction["vulnerable"], bool)
    assert 0.0 <= prediction["confidence"] <= 1.0

    try:
        model(input_ids, torch.zeros_like(attention_mask))
    except ValueError as error:
        print("\nReject all-padding attention mask:")
        print(str(error))
    else:
        raise AssertionError("Expected all-padding attention mask to be rejected")

    invalid_mask = attention_mask.clone()
    invalid_mask[0, 0] = 2
    try:
        model(input_ids, invalid_mask)
    except ValueError as error:
        print("\nReject non-binary attention mask:")
        print(str(error))
    else:
        raise AssertionError("Expected non-binary attention mask to be rejected")

    with tempfile.TemporaryDirectory() as temporary_directory:
        checkpoint_path = Path(temporary_directory) / "model.pt"
        model.save_checkpoint(checkpoint_path)
        restored_model = VulnerabilityClassifier.load_checkpoint(checkpoint_path)
        assert restored_model.lm_head.weight is restored_model.token_embeddings.weight

        source_path = Path(temporary_directory) / "sample.c"
        source_path.write_text(source, encoding="utf-8")
        file_prediction = json.loads(model.predict_file_json(source_path))
        print("\nmodel.predict_file_json(path):")
        print(file_prediction)
        assert file_prediction["windows_scanned"] == 1

    print("\nFull Layer 5 output: JSON vulnerability prediction:")
    print(json.dumps(prediction, indent=2))


if __name__ == "__main__":
    test_layer_5()

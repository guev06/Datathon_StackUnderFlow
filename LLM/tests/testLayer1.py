import json
import tempfile
from pathlib import Path

from LLM.layer1_data_ingestion import (
    _read_records,
    count_targets,
    iter_parser_batches,
    parser,
)
from LLM.layer2_tokenization import ByteCodeTokenizer


def test_layer_1() -> None:
    """Exercise PrimeVul JSONL reading, validation, and parser output."""
    records = [
        {"func": "int safe(void) { return 0; }", "target": 0},
        {"func": "void unsafe(char *p) { strcpy(dst, p); }", "target": 1},
    ]
    print("Input test records:")
    print(records)

    with tempfile.TemporaryDirectory() as temporary_directory:
        dataset_path = Path(temporary_directory) / "primevul_test.jsonl"
        dataset_path.write_text(
            "".join(json.dumps(record) + "\n" for record in records),
            encoding="utf-8",
        )

        read_result = list(_read_records(dataset_path))
        print("\n_read_records(path):")
        print(read_result)
        assert read_result == records

        target_counts = count_targets(dataset_path)
        print("\ncount_targets(path) -> (negative_count, positive_count):")
        print(target_counts)
        assert target_counts == (1, 1)

        tokenizer = ByteCodeTokenizer()
        batch_result = list(
            iter_parser_batches(
                dataset_path,
                tokenizer,
                max_length=128,
                batch_size=1,
            )
        )
        print("\niter_parser_batches(path, tokenizer, batch_size=1):")
        print(
            [
                {
                    "input_ids_shape": (
                        len(batch["input_ids"]),
                        len(batch["input_ids"][0]),
                    ),
                    "attention_mask_shape": (
                        len(batch["attention_mask"]),
                        len(batch["attention_mask"][0]),
                    ),
                    "labels": batch["labels"],
                }
                for batch in batch_result
            ]
        )
        assert [batch["labels"][0] for batch in batch_result] == [0, 1]

        parsed_result = parser(
            dataset_path,
            tokenizer,
            max_length=128,
            batch_size=2,
        )
        print("\nFull Layer 1 output: parser(path, tokenizer):")
        print(
            {
                "input_ids_shape": (
                    len(parsed_result["input_ids"]),
                    len(parsed_result["input_ids"][0]),
                ),
                "attention_mask_shape": (
                    len(parsed_result["attention_mask"]),
                    len(parsed_result["attention_mask"][0]),
                ),
                "labels": parsed_result["labels"],
            }
        )
        assert parsed_result["labels"] == [0, 1]


if __name__ == "__main__":
    test_layer_1()

# Datathon_StackUnderFlow LLM
Inputs: a source code file (or string), read as UTF-8. Training uses PrimeVul JSONL records with func (the code) and target (0 or 1).

Outputs: a JSON object with vulnerable, confidence, windows_scanned and a fixed boilerplate explanation. It is built in Python from the classifier head, not generated token by token by the model.

Training: pre-labelled functions go in. The loss is weighted classification NLL plus 0.02 times a next-token loss plus 0.1 times a contrastive loss. Settings are AdamW at 3e-4, batch 8 with 2-step accumulation (16 functions per update), clip 1.0, and 1 epoch (train_model.py now sets epochs=1). Training uses at most 2 random windows per function, shuffled each epoch with the epoch number as seed.

Layering

JSON parsing. It reads records, validates func and target, then cuts each function into non-overlapping 510-byte windows. Shuffling now loads the whole file into memory first, which is a RAM risk on the full train file. Validation and test use a fixed seed, so evaluation is now reproducible.

Tokenizing. Unchanged byte-level tokenizer with 259 tokens: pad, BOS, EOS, plus 256 bytes. Each window becomes BOS, up to 510 bytes, EOS, padded to 512.

Positional encoding and vectorizing. The embedding table (259 by 256) lives in the layer 5 class, not layer 3. RoPE is applied inside the attention code in layer 4. Initialization is now normal with std 0.02, and residual output projections are scaled by 1 over the square root of twice the layer count.

Decoder blocks. There are 6 blocks with d_model 256, 8 heads (head dimension 32), dropout 0.1, and about 1.05M parameters each.

Sub-layer 1: RMSNorm, then a fused bias-free QKV projection, RoPE on Q and K, and scaled_dot_product_attention with a combined causal and padding mask, then the output projection and residual add.

Sub-layer 2: RMSNorm, then SwiGLU (silu of gate times value, hidden size 1024, bias-free), then dropout and residual add.

Output layer.

A final RMSNorm.

Attention pooling. A learned query vector scores every active token, and a softmax-weighted sum of the hidden states gives one vector per window.

A Linear(256, 2) classifier produces the verdict. Window probabilities are averaged per function.

A language-model head tied to the embedding weights produces next-token logits, used only as an auxiliary training loss.

The total is about 6.36M parameters.

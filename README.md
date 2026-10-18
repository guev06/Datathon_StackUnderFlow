# FlowState — Datathon_StackUnderFlow

Paste any public **Python** GitHub repo and get an AI-generated, interactive dataflow map of it. Click any step
(or any function inside a step) to see the exact source code behind it.

## Run on Windows

The integrated app has a FastAPI backend and a Vite frontend. Run the backend
first in one PowerShell terminal, then the frontend in another. The Vite
development server proxies `/api` calls to the backend.

### One-time setup

Prerequisites: Git, Node.js with npm, and Python 3.12.

From the repository root, install Python if needed and create the backend
environment:

```powershell
winget install --id Python.Python.3.12 --exact --scope user --silent --accept-source-agreements --accept-package-agreements

$repo = (Get-Location).Path
$python = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
& $python --version
& $python -m venv "$repo\backend\.venv"
& "$repo\backend\.venv\Scripts\python.exe" -m pip install --upgrade pip
& "$repo\backend\.venv\Scripts\python.exe" -m pip install fastapi "uvicorn[standard]" click huggingface_hub scikit-learn skl2onnx onnxruntime numpy
```

Install and build the integrated frontend:

```powershell
Set-Location "$repo\frontend\flowstate"
npm ci
npm run build
```

### Start the app

**Terminal 1 — backend** (from any directory):

```powershell
$repo = "C:\path\to\Datathon_StackUnderFlow"
Set-Location "$repo\backend\repo_dataflow_ai"
& "$repo\backend\.venv\Scripts\python.exe" -m uvicorn server:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — frontend development server**:

```powershell
$repo = "C:\path\to\Datathon_StackUnderFlow"
Set-Location "$repo\frontend\flowstate"
npm run dev -- --host 127.0.0.1
```

Open <http://127.0.0.1:5173>. The backend also serves the production frontend
after the build at <http://127.0.0.1:8000>. Check backend readiness at
<http://127.0.0.1:8000/api/health>.

The Windows setup above was verified for serving the UI and backend health
endpoint. Installing all packages from `requirements.txt` also installs
`llama-cpp-python`; its source build can fail on Windows when long paths are
disabled. The Granite model weights are downloaded on first AI analysis.
Analysing a new repo takes about a minute on a laptop. Results are cached per
commit.

## How it works

```
GitHub repo ──clone──▶ AST index ──▶ ONNX role classifier ──▶ Granite: markdown dataflow report
                       (functions,     (entry/input/transform/      │
                        line spans,     storage/output per            ▼
                        call graph)     function)          Granite: report ──▶ dataflow graph (JSON)
                                                                              │  refs constrained to real symbols
                                                                              ▼
                                                     FlowState UI: steps → functions → source lines
```

1. **Index** (`src/indexer.py`): shallow-clones the repo and uses Python's `ast` to record every function, class,
   method and top-level script block with its exact line span, plus a call graph.
2. **Classify roles** (`src/roles.py`): a TF-IDF + logistic regression model, exported to **ONNX** and run with
   onnxruntime, labels each function as entry, input, transform, storage or output.
3. **Write the report** (`src/generator.py`): **IBM Granite 3.3 2B Instruct** (GGUF, llama.cpp) writes a numbered
   markdown walkthrough of the dataflow from a structural summary of the code.
4. **Generate the visualisation** (`src/visualizer.py`): Granite reads that markdown plus a catalogue of the real
   functions and returns stages and flows as JSON. The JSON schema is compiled into a llama.cpp grammar whose symbol
   references are an enum of catalogue ids, so **every step can only point at code that exists**. Line numbers
   always come from the AST, never from the model. If the output is unusable, a deterministic role-based graph is
   used instead.
5. **Explore** (`frontend/flowstate`): React + React Flow. You get a Dataflow view (play/step through the flow,
   ←/→ keys, role filters, call edges, function search), a Files view (import graph), and the AI report, where
   function names link to the code.

## IBM LinuxONE alignment

Built on the stack from [linuxone-community-cloud/jupyter-lab-ml](https://github.com/linuxone-community-cloud/jupyter-lab-ml):

- **IBM Granite on llama.cpp**, the same setup as the Loan Approval example. On IBM Z, llama.cpp uses its
  zDNN/NNPA backend, so `GraniteEngine` runs unchanged.
- **Train anywhere, run ONNX inference on Z**: the role classifier is trained with scikit-learn and exported with
  skl2onnx, like the MNIST/ONNX example. Only `onnxruntime` is needed at inference time.
- Libraries are limited to the ones in the container's `packages.txt` (scikit-learn, skl2onnx, onnx, llama_cpp_python,
  transformers, torch).

### Retraining the role classifier

```bash
cd backend/repo_dataflow_ai
../.venv/bin/python -m training.train_role_classifier --corpus /path/to/more/python/code
```

The training data is weakly supervised. Functions from the Python standard library and installed packages are
labelled by rules over the calls they make (`open`/`read` → input, `execute`/`commit` → storage, `write`/`dump` →
output, CLI/route decorators → entry). Half the samples have their call tokens removed, so the model also learns roles
from names, arguments and docstrings. The current model was trained on a balanced set of 49k samples (from ~485k
functions). On held-out data it scores 0.80 accuracy and 0.82 macro-F1 against those weak labels, and the ONNX export
agrees with scikit-learn on 99.8% of predictions. The output is `artifacts/role_classifier.onnx` (1.5 MB).

## Configuration

| Variable | Default | |
| --- | --- | --- |
| `FLOWSTATE_ENGINE` | `granite` | `transformers` uses a Hugging Face model with PyTorch instead |
| `FLOWSTATE_GGUF` | Granite 3.3 2B Q4_K_M | Path to another GGUF, e.g. Granite 3.3 8B for better graphs (slower) |
| `FLOWSTATE_HF_MODEL` | `Qwen/Qwen2.5-Coder-1.5B-Instruct` | Model for the transformers engine |
| `PORT` | `8000` | |

The original CLI still works: `python main.py --repo-path <folder> --output report.md`.

## Limits

- Python repos only for the AI dataflow. Up to 300 files are analysed, core code first and tests last.
- A 2B model sometimes orders steps loosely or picks a neighbouring function. Every reference is still real code, and
  dashed call edges show where steps are actually linked by calls.

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
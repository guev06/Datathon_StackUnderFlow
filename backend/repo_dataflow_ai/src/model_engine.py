"""Loads a language model for text processing.

GraniteEngine (default) runs IBM Granite as a GGUF file on llama.cpp, the stack used by the IBM LinuxONE
jupyter-lab-ml examples (there llama.cpp is built with zDNN/NNPA acceleration). ModelEngine runs any
Hugging Face causal LM with PyTorch/Transformers, e.g. the original Qwen2.5-Coder setup.
"""

import os
from pathlib import Path

DEFAULT_MODEL = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

GRANITE_REPO = "ibm-granite/granite-3.3-2b-instruct-GGUF"
GRANITE_FILE = "granite-3.3-2b-instruct-Q4_K_M.gguf"


def load_engine(name=None):
    """Pick an engine from FLOWSTATE_ENGINE ('granite' by default, or 'transformers')."""
    name = name or os.environ.get("FLOWSTATE_ENGINE", "granite")
    if name == "transformers":
        return ModelEngine(os.environ.get("FLOWSTATE_HF_MODEL", DEFAULT_MODEL))
    return GraniteEngine(os.environ.get("FLOWSTATE_GGUF"))


class GraniteEngine:
    """IBM Granite 3.3 2B Instruct on llama.cpp. Downloads the GGUF weights on first use."""

    def __init__(self, model_path=None, n_ctx=16384):
        from llama_cpp import Llama

        path = Path(model_path) if model_path else MODELS_DIR / "gguf" / GRANITE_FILE
        if not path.exists():
            from huggingface_hub import hf_hub_download
            path = Path(hf_hub_download(GRANITE_REPO, GRANITE_FILE, local_dir=MODELS_DIR / "gguf"))
        self.model_name = f"IBM Granite 3.3 2B Instruct ({path.stem.split('-')[-1]}, llama.cpp)"
        # n_gpu_layers=-1 offloads to Metal/CUDA when available; on IBM Z the zDNN backend is used instead.
        self.llm = Llama(str(path), n_ctx=n_ctx, n_gpu_layers=-1, verbose=False)

    def generate(self, prompt, system=None, max_new_tokens=512, temperature=0.2, schema=None):
        """Chat completion; with `schema`, output is constrained by a JSON-schema grammar so it always parses."""
        messages = [{"role": "system", "content": system}] if system else []
        messages.append({"role": "user", "content": prompt})
        kwargs = {"response_format": {"type": "json_object", "schema": schema}} if schema else {}
        result = self.llm.create_chat_completion(
            messages=messages, max_tokens=max_new_tokens, temperature=temperature, repeat_penalty=1.1, **kwargs,
        )
        return result["choices"][0]["message"]["content"]


def _pick_device():
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class ModelEngine:
    """Wraps a causal language model and its tokenizer for local text generation."""

    def __init__(self, model_name=DEFAULT_MODEL, cache_dir=MODELS_DIR):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.model_name = model_name
        self.device = _pick_device()
        # float16 is fast on CUDA and Apple Silicon (MPS) but slow or unsupported for many CPU ops.
        self.dtype = torch.float32 if self.device == "cpu" else torch.float16

        self.tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # device_map="auto" (via accelerate) spreads layers across GPUs and spills to CPU if memory runs out.
        # It segfaults on Apple Silicon, so on MPS/CPU the model is loaded normally and moved with .to().
        use_device_map = self.device == "cuda"
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            dtype=self.dtype,
            device_map="auto" if use_device_map else None,
            cache_dir=cache_dir,
        )
        if not use_device_map:
            self.model.to(self.device)
        self.model.eval()

    def generate(self, prompt, system=None, max_new_tokens=512, temperature=0.2, schema=None):
        """Generate a completion for `prompt` and return only the newly generated text.

        `schema` is accepted for interface parity with GraniteEngine but not enforced here.
        """
        import torch

        if self.tokenizer.chat_template:
            messages = [{"role": "system", "content": system}] if system else []
            messages.append({"role": "user", "content": prompt})
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            text = f"{system}\n\n{prompt}" if system else prompt

        inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)
        do_sample = temperature > 0
        with torch.inference_mode():
            output = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=do_sample,
                temperature=temperature if do_sample else None,
                pad_token_id=self.tokenizer.pad_token_id,
            )
        new_tokens = output[0, inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True)

"""Loads a PyTorch/Transformers model for text processing."""

from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

DEFAULT_MODEL = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


def _pick_device():
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class ModelEngine:
    """Wraps a causal language model and its tokenizer for local text generation."""

    def __init__(self, model_name=DEFAULT_MODEL, cache_dir=MODELS_DIR):
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

    @torch.inference_mode()
    def generate(self, prompt, system=None, max_new_tokens=512, temperature=0.2):
        """Generate a completion for `prompt` and return only the newly generated text."""
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
        output = self.model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            temperature=temperature if do_sample else None,
            pad_token_id=self.tokenizer.pad_token_id,
        )
        new_tokens = output[0, inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True)

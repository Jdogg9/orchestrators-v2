from __future__ import annotations

import json
import os
import importlib.util
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_TOKENIZER_DIR = str(
    Path(__file__).resolve().parents[2] / "ORCH_TOKENIZER" / "tokenizers"
)


class _ByteFallbackTokenizer:
    """Minimal byte-level tokenizer used when tiktoken isn't available."""

    name = "byte-fallback"
    vocab_size = 256

    def encode(self, text: str) -> list[int]:
        return list(text.encode("utf-8"))

    def decode(self, tokens: list[int]) -> str:
        return bytes(tokens).decode("utf-8", errors="replace")

    def info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "vocab_size": self.vocab_size,
            "fallback": True,
        }


def _load_tokenizer(model_name: str, tokenizer_dir: Optional[str]) -> Any:
    base_dir = Path(tokenizer_dir or os.getenv("ORCH_TOKENIZER_DIR", DEFAULT_TOKENIZER_DIR))
    loader_path = base_dir / "gpt-aimee_loader.py"

    if not loader_path.exists():
        raise FileNotFoundError(f"Tokenizer loader not found: {loader_path}")

    spec = importlib.util.spec_from_file_location("gpt_aimee_loader", loader_path)
    if spec is None or spec.loader is None:
        raise ImportError("Failed to load GPT-AIMEE tokenizer module")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "load_aimee_tokenizer"):
        raise AttributeError("Tokenizer loader missing load_aimee_tokenizer")

    return module.load_aimee_tokenizer(model_name=model_name)


def orch_tokenizer(
    action: str,
    text: Optional[str] = None,
    tokens: Optional[list[int]] = None,
    model_name: str = "gpt-aimee",
    tokenizer_dir: Optional[str] = None,
) -> Dict[str, Any]:
    action = (action or "").strip().lower()

    def _load_or_fallback() -> tuple[Any, Optional[str]]:
        try:
            return _load_tokenizer(model_name=model_name, tokenizer_dir=tokenizer_dir), None
        except (ImportError, ModuleNotFoundError) as exc:
            return _ByteFallbackTokenizer(), str(exc)

    if action not in {"encode", "decode", "count", "info"}:
        return {
            "status": "error",
            "error": "invalid_action",
            "message": "action must be one of: encode, decode, count, info",
        }

    if action == "info":
        try:
            tokenizer, fallback_error = _load_or_fallback()
        except Exception as exc:
            return {
                "status": "error",
                "error": "tokenizer_load_failed",
                "message": str(exc),
            }
        try:
            response = {
                "status": "ok",
                "action": "info",
                "model_name": model_name,
                "info": tokenizer.info(),
            }
            if fallback_error:
                response["warning"] = "fallback_tokenizer_used"
                response["warning_detail"] = fallback_error
            return response
        except Exception as exc:
            return {
                "status": "error",
                "error": "tokenizer_info_failed",
                "message": str(exc),
            }

    if action in {"encode", "count"}:
        if not isinstance(text, str) or not text.strip():
            return {
                "status": "error",
                "error": "missing_text",
                "message": "text is required for encode/count",
            }
        try:
            tokenizer, fallback_error = _load_or_fallback()
        except Exception as exc:
            return {
                "status": "error",
                "error": "tokenizer_load_failed",
                "message": str(exc),
            }
        try:
            encoded = tokenizer.encode(text)
            result: Dict[str, Any] = {
                "status": "ok",
                "action": action,
                "model_name": model_name,
                "token_count": len(encoded),
            }
            if action == "encode":
                result["tokens"] = encoded
            if fallback_error:
                result["warning"] = "fallback_tokenizer_used"
                result["warning_detail"] = fallback_error
            return result
        except Exception as exc:
            return {
                "status": "error",
                "error": "tokenize_failed",
                "message": str(exc),
            }

    if not isinstance(tokens, list) or not all(isinstance(item, int) for item in tokens):
        return {
            "status": "error",
            "error": "missing_tokens",
            "message": "tokens (array of integers) is required for decode",
        }

    try:
        tokenizer, fallback_error = _load_or_fallback()
    except Exception as exc:
        return {
            "status": "error",
            "error": "tokenizer_load_failed",
            "message": str(exc),
        }

    try:
        decoded = tokenizer.decode(tokens)
        response: Dict[str, Any] = {
            "status": "ok",
            "action": "decode",
            "model_name": model_name,
            "text": decoded,
            "token_count": len(tokens),
        }
        if fallback_error:
            response["warning"] = "fallback_tokenizer_used"
            response["warning_detail"] = fallback_error
        return response
    except Exception as exc:
        return {
            "status": "error",
            "error": "detokenize_failed",
            "message": str(exc),
        }

"""
Helpers for persisting passive worldbuilding capture artifacts.
"""

import json
import os
from hashlib import sha256
from typing import Any, Dict, Optional


def write_text_artifact(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def write_json_artifact(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def sha256_text(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()


class LLMCallRecorder:
    """Record prompt/output pairs as secondary files for auditability."""

    def __init__(self, base_dir: Optional[str], rel_base: str = "worldbuilding_artifacts/llm_calls"):
        self.base_dir = base_dir
        self.rel_base = self._normalize_rel_base(base_dir, rel_base)
        self.records = []
        self.warnings = []
        self._counter = 0

    @staticmethod
    def _normalize_rel_base(base_dir: Optional[str], rel_base: str) -> str:
        normalized = rel_base.strip("/\\")
        if not base_dir or not normalized:
            return normalized

        base_name = os.path.basename(os.path.normpath(base_dir))
        rel_parts = [part for part in normalized.replace("\\", "/").split("/") if part]

        if rel_parts and rel_parts[0] == base_name:
            rel_parts = rel_parts[1:]

        return "/".join(rel_parts)

    def enabled(self) -> bool:
        return bool(self.base_dir)

    def record(
        self,
        *,
        stage: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        output_text: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.enabled():
            return None

        self._counter += 1
        call_id = f"{stage}_{self._counter:03d}"
        rel_dir = os.path.join(self.rel_base, stage)
        abs_dir = os.path.join(self.base_dir, rel_dir)
        prompt_rel = os.path.join(rel_dir, f"{call_id}.prompt.txt")
        output_rel = os.path.join(rel_dir, f"{call_id}.output.json")
        prompt_abs = os.path.join(self.base_dir, prompt_rel)
        output_abs = os.path.join(self.base_dir, output_rel)

        prompt_payload = [
            f"[system]\n{system_prompt.strip()}",
            f"[user]\n{user_prompt.strip()}",
        ]
        prompt_text = "\n\n".join(prompt_payload).strip() + "\n"
        write_text_artifact(prompt_abs, prompt_text)

        output_payload = {
            "stage": stage,
            "model": model,
            "output_text": output_text,
        }
        if extra:
            output_payload.update(extra)
        write_json_artifact(output_abs, output_payload)

        record = {
            "call_id": call_id,
            "stage": stage,
            "model": model,
            "input_hash": sha256_text(prompt_text),
            "output_hash": sha256_text(output_text),
            "redacted_prompt_path": prompt_rel,
            "redacted_output_path": output_rel,
        }
        self.records.append(record)
        return record

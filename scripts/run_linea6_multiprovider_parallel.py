#!/usr/bin/env python3
"""Run Línea 6 Bolivia T3 entropy case for Gemma/Llama/Qwen in parallel.

This intentionally launches one backend process per model so the optional
Prompture multi-provider LLMClient path can use provider/model names while the
OASIS subprocesses remain isolated by port and environment.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from dotenv import dotenv_values

REPO = Path(__file__).resolve().parents[1]
PY = REPO / "backend/.venv/bin/python"
SEED = REPO / "backtesting/case-b-s2-bolivia-2025-runoff/seed_T3_clean.md"
OUT_ROOT = REPO / "runs/linea6" / ("multiprovider_parallel_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
REQUIREMENT = """# Question

Con la informacion disponible en el paquete de evidencia provisto, predecir quien ganara el balotaje presidencial de Bolivia del 19 de octubre de 2025.

Responder exclusivamente en espanol.

La respuesta debe:

- identificar desde la evidencia cuales son los dos candidatos competitivos del balotaje;
- elegir una prediccion principal unica, sin responder empate;
- estimar el porcentaje de voto de los dos candidatos competitivos y de otros/blanco/nulo;
- estimar el margen entre el ganador predicho y el segundo candidato en puntos;
- justificar la prediccion usando solo evidencia del contexto entregado;
- explicar como pesan la crisis economica, el colapso del MAS, la sorpresa de primera vuelta, el contraste de plataformas y la encuesta tardia;
- mencionar factores de incertidumbre;
- no usar informacion posterior a la fecha maxima del paquete.

Formato esperado:

Candidatos competitivos identificados:
- Candidato 1: __
- Candidato 2: __

Prediccion principal: __ gana

Estimacion de votos:
- [nombre completo del candidato 1]: __%
- [nombre completo del candidato 2]: __%
- Otros / blanco / nulo: __%

Margen estimado ganador-segundo: __ puntos

Justificacion:
- evidencia 1
- evidencia 2
- evidencia 3

Incertidumbre:
- factor 1
- factor 2"""


@dataclass(frozen=True)
class ModelRun:
    label: str
    prompture_model: str
    openai_model: str
    port: int


MODELS = [
    ModelRun("gemma", "openrouter/google/gemma-3-27b-it", "google/gemma-3-27b-it", 5010),
    ModelRun("llama", "openrouter/meta-llama/llama-3.3-70b-instruct", "meta-llama/llama-3.3-70b-instruct", 5011),
    ModelRun("qwen", "openrouter/qwen/qwen3-8b", "qwen/qwen3-8b", 5012),
]


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def redact_env_snapshot(env: dict[str, str]) -> dict[str, str]:
    keys = [
        "FLASK_PORT",
        "LLM_MODEL_NAME",
        "LLM_BASE_URL",
        "GRAPHITI_LLM_MODEL",
        "GRAPHITI_LLM_BASE_URL",
        "GRAPHITI_EMBEDDER_MODEL",
        "GRAPHITI_EMBEDDER_BASE_URL",
        "GRAPHITI_ADD_TEXT_TIMEOUT",
        "GRAPHITI_MAX_COROUTINES",
    ]
    snap = {k: env.get(k, "") for k in keys}
    for k in ["LLM_API_KEY", "OPENAI_API_KEY", "GRAPHITI_LLM_API_KEY", "GRAPHITI_EMBEDDER_API_KEY"]:
        snap[k] = "<set>" if env.get(k) else "<unset>"
    return snap


def make_env(model: ModelRun) -> dict[str, str]:
    env = dict(os.environ)
    env.update({k: v for k, v in dotenv_values(REPO / ".env").items() if v is not None})
    key = env.get("OPENROUTER_API_KEY") or env.get("LLM_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY/LLM_API_KEY is required")

    env.update(
        {
            "FLASK_HOST": "127.0.0.1",
            "FLASK_PORT": str(model.port),
            "FLASK_DEBUG": "false",
            "PYTHONUNBUFFERED": "1",
            # LLMClient / Prompture path: provider/model.
            "LLM_MODEL_NAME": model.prompture_model,
            "LLM_API_KEY": key,
            "OPENAI_API_KEY": key,
            # Keep empty: Prompture's OpenRouter driver fails if an OpenAI base_url
            # is also forced. OASIS/CAMEL normalizes openrouter/* to OPENROUTER_BASE.
            "LLM_BASE_URL": "",
            # Graphiti remains OpenAI-compatible, so it gets the raw OpenRouter model.
            "GRAPHITI_LLM_API_KEY": key,
            "GRAPHITI_LLM_BASE_URL": OPENROUTER_BASE,
            "GRAPHITI_LLM_MODEL": model.openai_model,
            "GRAPHITI_LLM_SMALL_MODEL": model.openai_model,
            "GRAPHITI_RERANKER_API_KEY": key,
            "GRAPHITI_RERANKER_BASE_URL": OPENROUTER_BASE,
            "GRAPHITI_RERANKER_MODEL": model.openai_model,
            "GRAPHITI_ADD_TEXT_TIMEOUT": "900",
            # Avoid stacking too much Graphiti concurrency while three backends run.
            "GRAPHITI_MAX_COROUTINES": "1",
        }
    )
    return env


def wait_health(port: int, timeout: int = 90) -> None:
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/health"
    last = None
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    return
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1)
    raise TimeoutError(f"backend on port {port} not ready: {last}")


def start_backend(model: ModelRun, env: dict[str, str], out: Path) -> subprocess.Popen[str]:
    out.mkdir(parents=True, exist_ok=True)
    stdout = (out / "backend_stdout.log").open("w", encoding="utf-8")
    stderr = (out / "backend_stderr.log").open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [str(PY), "backend/run.py"],
        cwd=REPO,
        env=env,
        stdout=stdout,
        stderr=stderr,
        text=True,
        start_new_session=True,
    )
    return proc


def start_headless(model: ModelRun, env: dict[str, str], out: Path) -> subprocess.Popen[str]:
    stdout = (out / "headless_stdout.log").open("w", encoding="utf-8")
    stderr = (out / "headless_stderr.log").open("w", encoding="utf-8")
    cmd = [
        str(PY),
        "tools/mirofish_headless.py",
        "--base-url",
        f"http://127.0.0.1:{model.port}",
        "--file",
        str(SEED),
        "--requirement",
        REQUIREMENT,
        "--project-name",
        f"Linea6 multiprovider {model.label} Bolivia T3",
        "--platform",
        "reddit",
        "--max-rounds",
        "48",
        "--no-report",
        "--no-graph-memory-update",
        "--graph-chunk-size",
        "3000",
        "--accept-language",
        "es",
        "--poll-timeout",
        "7200",
        "--output-dir",
        str(out),
    ]
    return subprocess.Popen(cmd, cwd=REPO, env=env, stdout=stdout, stderr=stderr, text=True)


def run_entropy(label: str, sim_id: str, out: Path) -> dict[str, Any]:
    sim_dir = REPO / "backend/uploads/simulations" / sim_id
    pooled = out / f"phase2_{label}_multiprovider_pooled.json"
    posts = out / f"phase2_{label}_multiprovider_postsonly.json"
    commands = [
        [str(PY), "backend/scripts/entropy_phase2_analysis.py", "--sim-dir", str(sim_dir), "--label", f"{label}-multiprovider-pooled", "--with-embeddings", "--real-embedder", "--output", str(pooled)],
        [str(PY), "backend/scripts/entropy_phase2_analysis.py", "--sim-dir", str(sim_dir), "--label", f"{label}-multiprovider-postsonly", "--with-embeddings", "--real-embedder", "--no-comments", "--output", str(posts)],
    ]
    results = {}
    for name, cmd in zip(["pooled", "postsonly"], commands):
        cp = subprocess.run(cmd, cwd=REPO, text=True, capture_output=True, timeout=1800)
        (out / f"entropy_{name}.stdout.log").write_text(cp.stdout, encoding="utf-8")
        (out / f"entropy_{name}.stderr.log").write_text(cp.stderr, encoding="utf-8")
        results[name] = {"exit_code": cp.returncode, "output": str(pooled if name == "pooled" else posts)}
    return results


def main() -> int:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(timezone.utc).isoformat()
    write_json(OUT_ROOT / "run_manifest.json", {"started_at": started_at, "models": [m.__dict__ for m in MODELS]})

    procs: dict[str, subprocess.Popen[str]] = {}
    headless: dict[str, subprocess.Popen[str]] = {}
    envs: dict[str, dict[str, str]] = {}
    summary: dict[str, Any] = {"started_at": started_at, "out_root": str(OUT_ROOT), "models": {}}

    try:
        for model in MODELS:
            out = OUT_ROOT / model.label
            env = make_env(model)
            envs[model.label] = env
            write_json(out / "backend_env_sanitized.json", redact_env_snapshot(env))
            procs[model.label] = start_backend(model, env, out)

        for model in MODELS:
            wait_health(model.port)
            summary["models"].setdefault(model.label, {})["backend_ready"] = True

        for model in MODELS:
            out = OUT_ROOT / model.label
            headless[model.label] = start_headless(model, envs[model.label], out)

        for model in MODELS:
            proc = headless[model.label]
            rc = proc.wait()
            out = OUT_ROOT / model.label
            model_summary: dict[str, Any] = summary["models"].setdefault(model.label, {})
            model_summary["headless_exit_code"] = rc
            manifest_path = out / "run_manifest.json"
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                model_summary["headless_manifest"] = manifest
                sim_id = manifest.get("simulation_id")
                if rc == 0 and sim_id:
                    model_summary["entropy"] = run_entropy(model.label, sim_id, out)
            write_json(OUT_ROOT / "summary.json", summary)

        summary["completed_at"] = datetime.now(timezone.utc).isoformat()
        write_json(OUT_ROOT / "summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if all(summary["models"].get(m.label, {}).get("headless_exit_code") == 0 for m in MODELS) else 1
    finally:
        for proc in procs.values():
            if proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        time.sleep(3)
        for proc in procs.values():
            if proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


if __name__ == "__main__":
    raise SystemExit(main())

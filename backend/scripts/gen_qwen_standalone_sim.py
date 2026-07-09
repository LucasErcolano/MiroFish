#!/usr/bin/env python3
"""Generate reddit_profiles.json + simulation_config.json for Qwen Phase-2 standalone run.

Does NOT depend on Flask / Neo4j / Graphiti. Talks to OpenRouter directly with
Qwen 3 8B to produce 40 personas consistent with the Bolivia T3 evidence
package, then writes the two files the standalone `run_reddit_simulation.py`
expects.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import urllib.request
import urllib.error

OR_KEY = Path("/tmp/or_key").read_text().strip()
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "qwen/qwen3-8b"

SYSTEM_PROMPT = """Eres un generador de personas para una simulación de debate online sobre el balotaje presidencial de Bolivia del 19 de octubre de 2025. Devuelves SIEMPRE JSON válido, sin texto adicional, sin markdown, sin comentarios."""


def call_qwen(user_prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
    """Call Qwen via OpenRouter. Strips <think>...</think> blocks and returns clean text."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {OR_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read())
            content = data["choices"][0]["message"]["content"]
            # Strip Qwen thinking blocks
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            return content
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            last_err = f"HTTP {e.code}: {body[:200]}"
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(last_err)
        except Exception as e:
            last_err = str(e)
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Qwen call failed after 3 attempts: {last_err}")


def parse_json_obj(text: str) -> dict:
    """Robust JSON object parse. Strips leading/trailing junk."""
    # Find first { and matching }
    start = text.find("{")
    if start < 0:
        raise ValueError(f"No JSON object found in: {text[:200]}")
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        c = text[i]
        if esc:
            esc = False
            continue
        if c == "\\":
            esc = True
            continue
        if c == '"' and not esc:
            in_str = not in_str
            continue
        if in_str:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError(f"Unbalanced JSON: {text[:200]}")


# ---------- Persona generation ----------

PERSONA_PROMPT = """Genera 1 persona ficticia para una simulación de debate en Reddit sobre el balotaje Bolivia 2025 entre Rodrigo Paz y Jorge "Tuto" Quiroga. Devuelve SOLO un objeto JSON con esta estructura exacta (sin markdown, sin explicaciones):

{{
  "username": "username_reddit_minusculas_con_guiones_bajo",
  "bio": "bio de hasta 200 caracteres, en español, sobre la persona",
  "persona": "descripción detallada de la persona en 200-400 palabras. Tono, intereses, postura probable frente al balotaje, fuentes que consume, profesión, contexto social.",
  "mbti": "uno de 16 tipos (INTJ, INTP, ENTJ, ENTP, INFJ, INFP, ENFJ, ENFP, ISTJ, ISFJ, ESTJ, ESFJ, ISTP, ISFP, ESTP, ESFP)",
  "gender": "Male o Female o Non-binary",
  "age": número entre 18 y 75,
  "country": "país (Bolivia para la mayoría, alguno de la región)",
  "stance": "uno de: supporting_paz, supporting_quiroga, supporting_mas, neutral, skeptical",
  "profession": "profesión o actividad (ingeniero, docente, comerciante, etc.)",
  "interested_topics": ["tema1","tema2","tema3"]
}}

Restricciones: NO incluir datos del resultado real (no sabemos quién ganó). La persona es ficticia y representa una voz auténtica del debate.

{persona_spec}"""


def gen_persona(idx: int, total: int) -> dict:
    """Generate one persona with retries."""
    spec_options = [
        "Esta persona es de La Paz, profesional, votó nulo en la primera vuelta y está indecisa.",
        "Esta persona es de Santa Cruz, comerciante,傾向 a la derecha, votó por Quiroga.",
        "Esta persona es de Cochabamba, joven estudiante universitario,倾向 al cambio y al votante joven.",
        "Esta persona es de El Alto, obrera, desconfía del sistema pero no del MAS.",
        "Esta persona es migrante boliviana en Buenos Aires, sigue el debate desde afuera, pragmática.",
        "Esta persona es de Tarija, agricultor, le preocupa la economía y el tipo de cambio.",
        "Esta persona es académica, socióloga, analiza la crisis del MAS con perspectiva crítica.",
        "Esta persona es jubilada, anti-casta política,反对 al modelo del MAS pero también a la derecha tradicional.",
        "Esta persona es de Potosí, minera, ve a Paz como continuidad moderada.",
        "Esta persona es influencer digital, vive en Santa Cruz, tono informativo-neutral.",
    ]
    spec = spec_options[idx % len(spec_options)]
    last_err = None
    for attempt in range(3):
        try:
            text = call_qwen(PERSONA_PROMPT.format(persona_spec=spec), max_tokens=900, temperature=0.85)
            obj = parse_json_obj(text)
            # Required fields check
            for k in ("username", "bio", "persona", "mbti", "gender", "age", "country"):
                if k not in obj:
                    raise ValueError(f"Missing field: {k}")
            obj["age"] = int(obj["age"])
            obj["mbti"] = obj["mbti"].strip().upper()
            obj["gender"] = obj["gender"].strip().capitalize()
            return obj
        except Exception as e:
            last_err = e
            print(f"  [retry] persona {idx} attempt {attempt+1}: {e}", file=sys.stderr)
            time.sleep(2)
    raise RuntimeError(f"Failed to generate persona {idx}: {last_err}")


# ---------- Main ----------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True, help="Simulation directory to write into")
    ap.add_argument("--n-personas", type=int, default=40)
    ap.add_argument("--max-rounds", type=int, default=48)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating {args.n_personas} personas with {MODEL}...", file=sys.stderr)
    personas = []
    t0 = time.time()
    for i in range(args.n_personas):
        p = gen_persona(i, args.n_personas)
        personas.append(p)
        # Re-id by index
        elapsed = time.time() - t0
        rate = (i + 1) / max(elapsed, 0.1)
        eta = (args.n_personas - i - 1) / max(rate, 0.01)
        print(f"  [{i+1:3d}/{args.n_personas}] {p['username']:30s} mbti={p['mbti']} st={p['stance'][:10]:10s} | {elapsed:.0f}s elapsed, ~{eta:.0f}s left", file=sys.stderr)
        # Save incrementally so a crash doesn't lose everything
        with open(out_dir / "reddit_profiles.json", "w", encoding="utf-8") as f:
            json.dump(personas, f, ensure_ascii=False, indent=2)

    # Build agent_configs for simulation_config.json
    import random
    rng = random.Random(args.seed)
    agent_configs = []
    stance_pool = ["supporting_paz", "supporting_quiroga", "supporting_mas", "neutral", "skeptical",
                   "supporting_paz", "neutral", "supporting_quiroga", "skeptical", "neutral"]
    for i, p in enumerate(personas):
        ac = {
            "agent_id": i,
            "username": p["username"],
            "name": p["username"],
            "bio": p["bio"],
            "persona": p["persona"],
            "mbti": p["mbti"],
            "gender": p["gender"],
            "age": p["age"],
            "country": p["country"],
            "profession": p.get("profession", ""),
            "interested_topics": p.get("interested_topics", []),
            "stance": p.get("stance", rng.choice(stance_pool)),
            "entity_type": "user",
            "active_hours": list(range(8, 23)),
            "activity_level": round(rng.uniform(0.2, 0.9), 2),
        }
        agent_configs.append(ac)

    # simulation_config.json — same shape as line5 llama
    sim_config = {
        "simulation_id": out_dir.name,
        "graph_id": "n/a_standalone_qwen",
        "llm_model": MODEL,
        "generation_reasoning": (
            "Standalone Phase-2 run for Linea 6 (Issue #28). "
            "LLM=qwen/qwen3-8b via OpenRouter. Personas generated directly by "
            "the LLM (no Graphiti) using the same T3_clean seed evidence package "
            "as the gemma/llama Phase-2 comparison. "
            "Config tuned to match the clean Phase-2 setup documented in "
            "docs/linea6_comparison_gemma_vs_llama.md (48 rounds, peak h8-h22, "
            "off-peak 0.3x, 40 personas, OASIS_SEMAPHORE=30)."
        ),
        "time_config": {
            "total_simulation_hours": 96,  # 4 days, covers h8-h22 cleanly
            "minutes_per_round": 30,
            "agents_per_hour_min": 5,
            "agents_per_hour_max": 20,
            "peak_hours": [9, 10, 11, 14, 15, 20, 21, 22],
            "peak_activity_multiplier": 1.5,
            "off_peak_hours": [0, 1, 2, 3, 4, 5],
            "off_peak_activity_multiplier": 0.3,
        },
        "event_config": {
            "initial_posts": [
                # 5 seed posts to kick off the conversation; each attributed to a
                # specific agent. These mirror the kind of content the
                # Bolivia 2025 runoff debate would have.
                {"poster_agent_id": 0,
                 "content": "Acabo de leer el último paquete de evidencia. La fragmentación del MAS es real y eso cambia todo para el balotaje. ¿Alguien más está repensando su voto?"},
                {"poster_agent_id": 5,
                 "content": "Lo que me llama la atención es la encuesta tardía que muestra a Quiroga arriba. Pero las encuestas también fallaron en la primera vuelta con Paz. Hay que mirar con cuidado."},
                {"poster_agent_id": 10,
                 "content": "El tema de fondo es económico: la crisis de dólares, la inflación, la escasez. Cualquiera que gane va a tener que enfrentar eso el día uno."},
                {"poster_agent_id": 15,
                 "content": "Vivo afuera hace 5 años y sigo el debate. Lo que veo es que los dos candidatos representan modelos distintos, no solo personas. Hay que votar por el modelo, no por el candidato."},
                {"poster_agent_id": 20,
                 "content": "Me preocupa que el debate se centre solo en los candidatos y no en las propuestas concretas. ¿Dónde están los planes detallados para los primeros 100 días?"},
            ],
            "hot_topics": ["crisis_economica", "colapso_mas", "plan_ajuste", "relaciones_eeuu", "politica_social"],
        },
        "agent_configs": agent_configs,
    }

    with open(out_dir / "simulation_config.json", "w", encoding="utf-8") as f:
        json.dump(sim_config, f, ensure_ascii=False, indent=2)
    print(f"\nWrote {out_dir / 'reddit_profiles.json'} ({len(personas)} personas)", file=sys.stderr)
    print(f"Wrote {out_dir / 'simulation_config.json'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

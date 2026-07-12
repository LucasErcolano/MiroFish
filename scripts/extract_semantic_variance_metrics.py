#!/usr/bin/env python3
"""Extract semantic variance / cluster entropy metrics from existing MiroFish run artifacts.

This script does not re-run simulations or LLM generation. It reads existing
profiles + SQLite outputs, embeds text with local Ollama bge-m3, and writes
aggregate metrics for tri-model runs and available single-model baselines.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib import request

import numpy as np

MODEL_QWEN = "qwen/qwen3-8b"
MODEL_GEMMA = "google/gemma-3-27b-it"
MODEL_LLAMA = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
MODELS = [MODEL_QWEN, MODEL_GEMMA, MODEL_LLAMA]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def normalize_model_name(model: str) -> str:
    m = model.strip()
    if m == "meta-llama/llama-3.3-70b-instruct":
        return MODEL_LLAMA
    if m == "meta-llama/Llama-3.3-70B-Instruct-Turbo":
        return MODEL_LLAMA
    return m


def route_map_from_audit(path: Path) -> dict[int, str]:
    out = {}
    for rec in load_jsonl(path):
        out[int(rec["agent_id"])] = normalize_model_name(rec["model"])
    return out


def user_to_agent(db_path: Path) -> dict[int, int]:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    return {int(user_id): int(agent_id) for user_id, agent_id in cur.execute("select user_id, agent_id from user")}


def load_dataset(kind: str, label: str, run_dir: Path, sim_dir: Path | None, fixed_model: str | None = None) -> dict[str, list[dict[str, Any]]]:
    if sim_dir is None:
        sim_dir = run_dir
    db_path = run_dir / "reddit_simulation.db"
    profiles_path = run_dir / "reddit_profiles.json"
    if not db_path.exists():
        db_path = sim_dir / "reddit_simulation.db"
    if not profiles_path.exists():
        profiles_path = sim_dir / "reddit_profiles.json"
    if not db_path.exists() or not profiles_path.exists():
        raise FileNotFoundError(f"missing db/profiles for {label}: {db_path} {profiles_path}")

    if kind == "tri":
        audit_path = run_dir / "model_routing_audit.jsonl"
        routes = route_map_from_audit(audit_path)
        u2a = user_to_agent(db_path)
        def model_for_user(uid: int) -> str:
            return routes[u2a[int(uid)]]
    else:
        assert fixed_model
        def model_for_user(uid: int) -> str:
            return fixed_model

    levels: dict[str, list[dict[str, Any]]] = {"personas": [], "posts-only": [], "comments-only": [], "pooled": []}
    profiles = json.load(open(profiles_path, encoding="utf-8"))
    for p in profiles:
        uid = int(p["user_id"])
        text = (p.get("persona") or p.get("bio") or "").strip()
        if text:
            item = {"id": f"persona:{uid}", "user_id": uid, "model": model_for_user(uid), "text": text}
            levels["personas"].append(item)

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    for r in cur.execute("select post_id, user_id, content from post where coalesce(content,'') != ''"):
        uid = int(r["user_id"])
        item = {"id": f"post:{r['post_id']}", "user_id": uid, "model": model_for_user(uid), "text": r["content"].strip()}
        levels["posts-only"].append(item)
        levels["pooled"].append(item)
    for r in cur.execute("select comment_id, user_id, content from comment where coalesce(content,'') != ''"):
        uid = int(r["user_id"])
        item = {"id": f"comment:{r['comment_id']}", "user_id": uid, "model": model_for_user(uid), "text": r["content"].strip()}
        levels["comments-only"].append(item)
        levels["pooled"].append(item)
    return levels


def htext(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ollama_embed(text: str, url: str, model: str, timeout: int = 120) -> list[float]:
    payload = json.dumps({"model": model, "prompt": text}).encode("utf-8")
    req = request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    emb = data.get("embedding")
    if not emb:
        raise RuntimeError(f"empty embedding response for {text[:50]!r}")
    return emb


def embed_texts(texts: list[str], cache_path: Path, model: str = "bge-m3", url: str = "http://127.0.0.1:11434/api/embeddings") -> np.ndarray:
    cache: dict[str, list[float]] = {}
    if cache_path.exists():
        cache = json.load(open(cache_path, encoding="utf-8"))
    changed = False
    arr = []
    for i, text in enumerate(texts, 1):
        key = htext(text)
        if key not in cache:
            # retry transient local HTTP issues
            last = None
            for attempt in range(3):
                try:
                    cache[key] = ollama_embed(text, url=url, model=model)
                    changed = True
                    break
                except Exception as e:
                    last = e
                    time.sleep(1.5 * (attempt + 1))
            else:
                raise RuntimeError(f"embedding failed after retries: {last}")
            if changed and len(cache) % 25 == 0:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                json.dump(cache, open(cache_path, "w", encoding="utf-8"))
        arr.append(cache[key])
    if changed:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        json.dump(cache, open(cache_path, "w", encoding="utf-8"))
    x = np.array(arr, dtype=np.float64)
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return x / norms


def pairwise_cosine_mean(x: np.ndarray) -> float | None:
    n = len(x)
    if n < 2:
        return None
    sim = x @ x.T
    iu = np.triu_indices(n, k=1)
    return float(np.mean(1.0 - sim[iu]))


def centroid_cosine_distances(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    c = np.mean(x, axis=0)
    norm = np.linalg.norm(c)
    if norm > 0:
        cn = c / norm
    else:
        cn = c
    d = 1.0 - (x @ cn)
    return c, d


def shannon_entropy(labels: list[int]) -> dict[str, float | int]:
    n = len(labels)
    if n == 0:
        return {"entropy_bits": 0.0, "normalized_entropy": 0.0, "effective_n": 0.0, "unique": 0, "n": 0}
    counts = Counter(labels)
    probs = np.array([c / n for c in counts.values()], dtype=np.float64)
    h = float(-np.sum(probs * np.log2(probs)))
    k = len(counts)
    return {
        "entropy_bits": h,
        "normalized_entropy": h / math.log2(k) if k > 1 else 0.0,
        "effective_n": float(2 ** h),
        "unique": k,
        "n": n,
    }


def jsd(p: np.ndarray, q: np.ndarray) -> float:
    p = p.astype(np.float64); q = q.astype(np.float64)
    p = p / p.sum() if p.sum() else p
    q = q / q.sum() if q.sum() else q
    m = 0.5 * (p + q)
    def kl(a, b):
        mask = a > 0
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def mutual_information(model_labels: list[str], cluster_labels: list[int]) -> dict[str, float]:
    n = len(model_labels)
    if n == 0:
        return {"mi_bits": 0.0, "nmi_by_cluster_entropy": 0.0, "nmi_by_model_entropy": 0.0}
    models = sorted(set(model_labels)); clusters = sorted(set(cluster_labels))
    mi = 0.0
    cm = Counter(model_labels); cc = Counter(cluster_labels); joint = Counter(zip(model_labels, cluster_labels))
    for m in models:
        for c in clusters:
            pxy = joint[(m,c)] / n
            if pxy:
                px = cm[m] / n; py = cc[c] / n
                mi += pxy * math.log2(pxy / (px * py))
    hm = shannon_entropy([models.index(m) for m in model_labels])["entropy_bits"]
    hc = shannon_entropy(cluster_labels)["entropy_bits"]
    return {
        "mi_bits": float(mi),
        "nmi_by_cluster_entropy": float(mi / hc) if hc else 0.0,
        "nmi_by_model_entropy": float(mi / hm) if hm else 0.0,
    }


def kmeans(x: np.ndarray, k: int, seed: int = 13, n_iter: int = 60) -> np.ndarray:
    n = len(x)
    if n == 0:
        return np.array([], dtype=int)
    k = max(1, min(k, n))
    rng = np.random.default_rng(seed)
    # kmeans++ lite initialization on cosine-normalized data using euclidean distance
    centers = [x[int(rng.integers(0, n))]]
    while len(centers) < k:
        c = np.vstack(centers)
        d2 = np.min(((x[:, None, :] - c[None, :, :]) ** 2).sum(axis=2), axis=1)
        if d2.sum() <= 0:
            idx = int(rng.integers(0, n))
        else:
            idx = int(rng.choice(n, p=d2 / d2.sum()))
        centers.append(x[idx])
    centers = np.vstack(centers)
    labels = np.zeros(n, dtype=int)
    for _ in range(n_iter):
        d2 = ((x[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        new = np.argmin(d2, axis=1)
        if np.array_equal(new, labels):
            break
        labels = new
        for j in range(k):
            if np.any(labels == j):
                centers[j] = x[labels == j].mean(axis=0)
                norm = np.linalg.norm(centers[j])
                if norm: centers[j] /= norm
    return labels


def analyze_items(items: list[dict[str, Any]], cache_path: Path) -> dict[str, Any]:
    n = len(items)
    if n == 0:
        return {"n": 0}
    x = embed_texts([it["text"] for it in items], cache_path)
    c, dcent = centroid_cosine_distances(x)
    centered = x - np.mean(x, axis=0)
    result: dict[str, Any] = {
        "n": n,
        "pairwise_cosine_distance_mean": pairwise_cosine_mean(x),
        "centroid_cosine_distance_mean": float(np.mean(dcent)),
        "centroid_cosine_distance_std": float(np.std(dcent)),
        "centroid_cosine_distance_max": float(np.max(dcent)),
        "embedding_variance_trace": float(np.mean(np.sum(centered ** 2, axis=1))),
        "centroid_norm": float(np.linalg.norm(c)),
    }
    labels = [it["model"] for it in items]
    by_model = {}
    for m in sorted(set(labels)):
        idx = [i for i, lab in enumerate(labels) if lab == m]
        xm = x[idx]
        cm, dm = centroid_cosine_distances(xm)
        by_model[m] = {
            "n": len(idx),
            "pairwise_cosine_distance_mean": pairwise_cosine_mean(xm),
            "centroid_cosine_distance_mean": float(np.mean(dm)) if len(dm) else None,
            "embedding_variance_trace": float(np.mean(np.sum((xm - np.mean(xm, axis=0)) ** 2, axis=1))) if len(xm) else None,
            "centroid_norm": float(np.linalg.norm(cm)),
        }
    result["within_model"] = by_model
    if len(set(labels)) >= 2:
        centroids = {}
        for m in sorted(set(labels)):
            xm = x[[i for i, lab in enumerate(labels) if lab == m]]
            cm = np.mean(xm, axis=0)
            norm = np.linalg.norm(cm)
            centroids[m] = cm / norm if norm else cm
        between = {}
        ms = sorted(centroids)
        for i, a in enumerate(ms):
            for b in ms[i+1:]:
                between[f"{a}__{b}"] = float(1.0 - np.dot(centroids[a], centroids[b]))
        result["between_model_centroid_cosine_distance"] = between
        global_mean = np.mean(x, axis=0)
        total_sse = float(np.sum((x - global_mean) ** 2))
        within_sse = 0.0
        for m in ms:
            idx = [i for i, lab in enumerate(labels) if lab == m]
            xm = x[idx]
            within_sse += float(np.sum((xm - np.mean(xm, axis=0)) ** 2))
        result["variance_decomposition"] = {
            "total_sse": total_sse,
            "within_model_sse": within_sse,
            "between_model_sse": total_sse - within_sse,
            "between_share": (total_sse - within_sse) / total_sse if total_sse else 0.0,
        }
    k = min(max(2, int(round(math.sqrt(n)))), 8)
    cl = kmeans(x, k=k)
    result["cluster_entropy"] = {"k": int(k), **shannon_entropy(cl.tolist()), "counts": dict(Counter(map(int, cl)))}
    if len(set(labels)) >= 2:
        ms = sorted(set(labels)); clusters = sorted(set(map(int, cl)))
        # per-model cluster distribution
        dist = {}
        for m in ms:
            vals = [int(cl[i]) for i, lab in enumerate(labels) if lab == m]
            cnt = Counter(vals); arr = np.array([cnt[c] for c in clusters], dtype=float)
            dist[m] = {str(c): int(cnt[c]) for c in clusters}
        result["model_cluster_counts"] = dist
        pair_jsd = {}
        for i, a in enumerate(ms):
            pa = np.array([dist[a][str(c)] for c in clusters], dtype=float)
            for b in ms[i+1:]:
                pb = np.array([dist[b][str(c)] for c in clusters], dtype=float)
                pair_jsd[f"{a}__{b}"] = jsd(pa, pb)
        result["model_cluster_jsd_bits"] = pair_jsd
        result["model_cluster_mutual_information"] = mutual_information(labels, cl.tolist())
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-root", default="runs/linea6/semantic_variance_existing_artifacts_20260709")
    ap.add_argument("--cache", default="runs/linea6/semantic_variance_existing_artifacts_20260709/embedding_cache_bge_m3.json")
    args = ap.parse_args()
    out_root = Path(args.out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    cache = Path(args.cache)

    tri_root = Path("runs/linea6/trimodel_model_map_all_real_20260709_012117")
    single_root = Path("runs/linea6/multiprovider_parallel_20260705_184644")
    single_sims = {
        "single_qwen": (single_root / "qwen", Path("backend/uploads/simulations/sim_8633c5a63557"), MODEL_QWEN),
        "single_gemma": (single_root / "gemma", Path("backend/uploads/simulations/sim_6e49710b43e8"), MODEL_GEMMA),
        "single_llama": (single_root / "llama", Path("backend/uploads/simulations/sim_9ef534050066"), MODEL_LLAMA),
    }

    datasets = {}
    for case in ["t0", "t1", "t2", "t3", "t3_clean"]:
        datasets[f"tri_{case}"] = load_dataset("tri", f"tri_{case}", tri_root / case, None)
    for name, (run_dir, sim_dir, model) in single_sims.items():
        datasets[name] = load_dataset("single", name, run_dir, sim_dir, model)

    results: dict[str, Any] = {"note": "Existing artifacts only; no simulation or LLM generation was re-run. Embeddings computed with local Ollama bge-m3.", "datasets": {}}
    for name, levels in datasets.items():
        results["datasets"][name] = {}
        for level, items in levels.items():
            print("analyze", name, level, len(items), flush=True)
            results["datasets"][name][level] = analyze_items(items, cache)

    # Comparisons: tri t3_clean vs single baselines at same levels.
    comps: dict[str, Any] = {}
    tri = results["datasets"]["tri_t3_clean"]
    for level in ["personas", "posts-only", "comments-only", "pooled"]:
        comps[level] = {}
        tri_total = tri[level].get("pairwise_cosine_distance_mean")
        tri_var = tri[level].get("embedding_variance_trace")
        tri_cluster = tri[level].get("cluster_entropy", {}).get("entropy_bits")
        for sname in ["single_qwen", "single_gemma", "single_llama"]:
            base = results["datasets"][sname][level]
            comps[level][sname] = {
                "tri_pairwise_minus_single": None if tri_total is None or base.get("pairwise_cosine_distance_mean") is None else tri_total - base["pairwise_cosine_distance_mean"],
                "tri_variance_trace_minus_single": None if tri_var is None or base.get("embedding_variance_trace") is None else tri_var - base["embedding_variance_trace"],
                "tri_cluster_entropy_minus_single": None if tri_cluster is None or base.get("cluster_entropy", {}).get("entropy_bits") is None else tri_cluster - base["cluster_entropy"]["entropy_bits"],
            }
    results["comparisons_tri_t3_clean_vs_single_baselines"] = comps

    out_json = out_root / "semantic_variance_metrics.json"
    json.dump(results, open(out_json, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    # Markdown summary
    lines = ["# Semantic variance metrics from existing artifacts", "", f"JSON: `{out_json.resolve()}`", "", "No simulations/LLM generations were re-run; only local bge-m3 embeddings were computed from existing profiles/posts/comments.", ""]
    def row_for(ds, level):
        r = results["datasets"][ds][level]
        return [r.get("n",0), r.get("pairwise_cosine_distance_mean"), r.get("embedding_variance_trace"), r.get("centroid_cosine_distance_mean"), r.get("cluster_entropy",{}).get("entropy_bits"), r.get("cluster_entropy",{}).get("normalized_entropy")]
    for level in ["personas","posts-only","comments-only","pooled"]:
        lines.append(f"## {level}")
        lines.append("| dataset | n | pairwise_cos_dist_mean | variance_trace | centroid_dist_mean | cluster_entropy_bits | cluster_entropy_norm |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for ds in ["single_qwen","single_gemma","single_llama","tri_t3_clean"]:
            vals=row_for(ds,level)
            fmt=[]
            for v in vals:
                if isinstance(v,float): fmt.append(f"{v:.4f}")
                else: fmt.append(str(v))
            lines.append(f"| {ds} | " + " | ".join(fmt) + " |")
        lines.append("")
    lines.append("## Tri-model T3_clean: intra/inter model decomposition")
    for level in ["personas","posts-only","comments-only","pooled"]:
        r=results["datasets"]["tri_t3_clean"][level]
        lines.append(f"### {level}")
        vd=r.get("variance_decomposition",{})
        lines.append(f"between_share={vd.get('between_share',0):.4f}; total_sse={vd.get('total_sse',0):.4f}; within_sse={vd.get('within_model_sse',0):.4f}; between_sse={vd.get('between_model_sse',0):.4f}")
        lines.append("centroid distances: " + json.dumps(r.get("between_model_centroid_cosine_distance",{}), ensure_ascii=False))
        lines.append("cluster JSD bits: " + json.dumps(r.get("model_cluster_jsd_bits",{}), ensure_ascii=False))
        lines.append("model-cluster MI: " + json.dumps(r.get("model_cluster_mutual_information",{}), ensure_ascii=False))
        lines.append("")
    out_md = out_root / "semantic_variance_report.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(out_json)
    print(out_md)

if __name__ == "__main__":
    main()

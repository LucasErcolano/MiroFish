"""
Local OpenAI-compatible embedding server using sentence_transformers.
Used as a free-tier fallback when Gemini embedding quota is exhausted.

Embeddings are padded with zeros to TARGET_DIM (default 3072) to stay
compatible with any existing Neo4j vector indexes built at that dimension.
Zero-padding preserves cosine similarity for normalized embeddings.

Usage:
    uv run python tools/local_embedding_server.py [--port 9999] [--dim 3072]
"""

import argparse
import json
import logging
import sys

import numpy as np
from flask import Flask, jsonify, request
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"  # 384-dim, supports Spanish

app = Flask(__name__)
_model: SentenceTransformer | None = None
_target_dim: int = 3072


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        log.info("Loading sentence_transformers model: %s", MODEL_NAME)
        _model = SentenceTransformer(MODEL_NAME)
        log.info("Model loaded. Native dim: %d → padded to %d", _model.get_sentence_embedding_dimension(), _target_dim)
    return _model


@app.route("/v1/embeddings", methods=["POST"])
def embeddings():
    data = request.get_json(force=True)
    inputs = data.get("input", [])
    if isinstance(inputs, str):
        inputs = [inputs]

    model = get_model()
    raw = model.encode(inputs, normalize_embeddings=True)  # shape (N, 384)

    native_dim = raw.shape[1]
    if native_dim < _target_dim:
        padding = np.zeros((raw.shape[0], _target_dim - native_dim), dtype=np.float32)
        padded = np.concatenate([raw, padding], axis=1)
    else:
        padded = raw[:, :_target_dim]

    response = {
        "object": "list",
        "data": [
            {"object": "embedding", "index": i, "embedding": row.tolist()}
            for i, row in enumerate(padded)
        ],
        "model": data.get("model", MODEL_NAME),
        "usage": {"prompt_tokens": 0, "total_tokens": 0},
    }
    return jsonify(response)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9999)
    parser.add_argument("--dim", type=int, default=3072)
    args = parser.parse_args()

    _target_dim = args.dim
    get_model()  # pre-load
    log.info("Starting local embedding server on port %d", args.port)
    app.run(host="0.0.0.0", port=args.port, debug=False)

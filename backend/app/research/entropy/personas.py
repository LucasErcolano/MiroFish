"""
Load persona/agent profiles produced by the ``prepare`` stage.

The profile generator writes one or more of:

- ``reddit_profiles.json`` — JSON list of reddit-format dicts
- ``twitter_profiles.csv`` — CSV (``interested_topics`` is ';'-joined)
- ``*_profiles.json`` via ``save_profiles_to_json`` — JSON list of full dicts

These loaders return a plain ``list[dict]`` ready for
:func:`metrics.profile_categorical_report` and for text-diversity metrics over
the ``persona`` / ``bio`` fields.
"""

from __future__ import annotations

import csv
import glob
import json
import os
from typing import List, Optional


def _profiles_from_json_obj(obj) -> List[dict]:
    if isinstance(obj, list):
        return [p for p in obj if isinstance(p, dict)]
    if isinstance(obj, dict):
        for key in ("profiles", "agents", "data"):
            if isinstance(obj.get(key), list):
                return [p for p in obj[key] if isinstance(p, dict)]
        # A single profile dict.
        return [obj]
    return []


def load_profiles_json(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return _profiles_from_json_obj(json.load(f))


def load_profiles_csv(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def load_profiles(path: str) -> List[dict]:
    """Load a single profiles file, dispatching on extension."""
    if path.endswith(".csv"):
        return load_profiles_csv(path)
    return load_profiles_json(path)


# Preference order when a simulation dir has several profile files.
_PROFILE_GLOBS = ("reddit_profiles.json", "twitter_profiles.csv", "*_profiles.json", "*_profiles.csv")


def find_profiles_file(sim_dir: str) -> Optional[str]:
    """Return the most relevant profiles file in a prepared simulation directory."""
    for pattern in _PROFILE_GLOBS:
        matches = sorted(glob.glob(os.path.join(sim_dir, pattern)))
        if matches:
            return matches[0]
    return None


def load_profiles_from_sim_dir(sim_dir: str) -> List[dict]:
    path = find_profiles_file(sim_dir)
    if not path:
        raise FileNotFoundError(f"No *_profiles.(json|csv) found under {sim_dir}")
    return load_profiles(path)


def persona_texts(profiles: List[dict], fields=("persona", "bio")) -> List[str]:
    """Concatenate the free-text persona fields of each profile (for lexical/embedding metrics)."""
    texts = []
    for p in profiles:
        parts = [str(p.get(f, "")).strip() for f in fields]
        texts.append(" ".join(x for x in parts if x))
    return texts

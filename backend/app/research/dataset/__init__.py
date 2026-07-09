"""
Run-bundle dataset export (Issue #28, PD).

Persists each MiroFish run as a normalized record bundling the three things a
fine-tuning / distillation dataset needs:

- **prompt**: the natural-language question / simulation requirement (+ seed
  provenance),
- **plan**: the planning the model generated (config reasoning, time/event
  config, agent-config distributions, report outline),
- **completion**: the result (the generated report) plus run-result metadata.

Records are content-hashed and deduplicated so re-exporting a run is idempotent.
"""

from .run_bundle import (
    DEFAULT_UPLOADS,
    append_to_dataset,
    build_bundle,
    to_training_record,
    write_bundle,
)

__all__ = [
    "DEFAULT_UPLOADS",
    "append_to_dataset",
    "build_bundle",
    "to_training_record",
    "write_bundle",
]

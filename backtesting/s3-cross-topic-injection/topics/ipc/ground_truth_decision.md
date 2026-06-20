# IPC Ground Truth Decision

PR #22 has a ground-truth mismatch:

- `cases/CASE-B2-ARG-IPC-2025/answer_key_post_x/ground_truth.md` says February 2.4%, April 3.7%, July about 3.0%, December 2.8%, accumulated 31.5%.
- `cases/CASE-B2-ARG-IPC-2025/ground_truth.json` says February 2.4%, April 2.8%, July 1.9%, December 2.8%.

S3 decision:

- Use the answer-key markdown as canonical because it is the explicit post-X answer key and contains the richer evaluation notes.
- Keep the mismatch visible in reports.
- Do not score IPC as final if future inspection proves the JSON is the authoritative artifact.

Canonical S3 IPC values for scoring:

- February: 2.4%
- April: 3.7%
- July: about 3.0%
- December: 2.8%
- Annual accumulated: 31.5%


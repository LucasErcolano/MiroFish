# Case Card

case_id: `case-a-s2-positional-noise`

Question: with information available up to 2024-07-13 23:59 UTC, predict the winner of the Copa America 2024 final between Argentina and Colombia.

Ground truth: Argentina won on 2024-07-14.

Backtesting rule: no document or model reasoning should use information after 2024-07-13 23:59 UTC.

Primary comparison:

- `baseline`: no scheduled injection.
- `signal-*`: a relevant pre-match signal is injected at a controlled round.
- `noise-*`: a plausible but irrelevant sports-news distraction is injected at a controlled round.

Primary outcome:

- final predicted winner;
- narrative justification;
- uncertainty framing;
- whether the injected document appears in the final reasoning.

This case inherits S1 seed material from `backtesting/case-a/`.

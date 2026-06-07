# Complexity Gate

S1 Case A had only two seed documents and a short time window. That is enough for a backtesting proof, but weak for Issue #19 because positional injection needs enough baseline context for the injected signal/noise to compete with existing discussion.

Minimum S2 hardening:

- keep the original S1 seed sources;
- add the `signal_doc.md` only through scheduled injection;
- add the `noise_doc.md` only through scheduled injection;
- do not include signal/noise in the baseline seed bundle;
- run all conditions with the same model, prompt, initial sources, and round count.

If time is short, prioritize real scheduled injection over adding more seed documents. A smaller but temporally correct experiment is better evidence for Issue #19 than a larger bundle that only changes initial context.

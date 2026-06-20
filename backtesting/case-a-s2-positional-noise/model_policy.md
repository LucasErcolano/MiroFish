# Model Policy

Primary S2 conclusion should use one fixed hosted model across all seven conditions.

Recommended primary model:

- provider: `deepinfra`
- model: `meta-llama/Llama-3.3-70B-Instruct-Turbo`

Reason:

- keep the model fixed so condition differences are attributable to injection position/type;
- avoid mixing positional sensitivity with heterogeneous model behavior;
- use the S2 model ladder only as a separate sanity check.

Model ladder for secondary checks:

- A: `qwen/qwen3-8b` through OpenRouter.
- B: `google/gemma-3-27b-it` through DeepInfra.
- C: `meta-llama/Llama-3.3-70B-Instruct-Turbo` through DeepInfra.

Do not use unlisted models for the reported S2 experiment unless the issue owner approves it.

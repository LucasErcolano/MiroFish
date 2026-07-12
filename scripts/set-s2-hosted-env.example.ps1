# Usage:
# 1. Copy/paste this into a PowerShell terminal.
# 2. Replace the placeholder token values in memory only.
# 3. Do not save real API keys in this file.

$env:PYTHONIOENCODING = "utf-8"

# Primary S2 model path.
$env:DEEPINFRA_API_KEY = "PASTE_DEEPINFRA_API_KEY"
$env:DEEPINFRA_BASE_URL = "https://api.deepinfra.com/v1/openai"

$env:LLM_API_KEY = $env:DEEPINFRA_API_KEY
$env:OPENAI_API_KEY = $env:LLM_API_KEY
$env:LLM_BASE_URL = $env:DEEPINFRA_BASE_URL
$env:LLM_MODEL_NAME = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
$env:LLM_MAX_TOKENS = "4096"

# Optional model ladder path.
$env:OPENROUTER_API_KEY = "PASTE_OPENROUTER_API_KEY"
$env:OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Graphiti can use the same hosted model if local embeddings are not desired.
$env:GRAPH_BACKEND = "graphiti"
$env:GRAPHITI_URI = "bolt://127.0.0.1:7687"
$env:GRAPHITI_USER = "neo4j"
$env:GRAPHITI_PASSWORD = "mirofishpassword"
$env:GRAPHITI_DATABASE = "neo4j"

$env:GRAPHITI_LLM_API_KEY = $env:LLM_API_KEY
$env:GRAPHITI_LLM_BASE_URL = $env:LLM_BASE_URL
$env:GRAPHITI_LLM_MODEL = $env:LLM_MODEL_NAME
$env:GRAPHITI_LLM_CLIENT_MODE = "generic"
$env:GRAPHITI_LLM_MAX_TOKENS = "4096"

# Keep local embeddings if the server on 8002 is running.
$env:GRAPHITI_EMBEDDER_API_KEY = "local-dev"
$env:GRAPHITI_EMBEDDER_BASE_URL = "http://127.0.0.1:8002/v1"
$env:GRAPHITI_EMBEDDER_MODEL = "bge-small-en-v1.5"
$env:GRAPHITI_EMBEDDER_DIM = "384"

$env:GRAPH_SEARCH_APP_EMBEDDER_API_KEY = "local-dev"
$env:GRAPH_SEARCH_APP_EMBEDDER_BASE_URL = "http://127.0.0.1:8002/v1"
$env:GRAPH_SEARCH_APP_EMBEDDER_MODEL = "bge-small-en-v1.5"

Write-Host "S2 hosted env set. Verify tokens before running paid jobs."

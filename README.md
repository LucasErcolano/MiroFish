<div align="center">

<img src="./static/image/MiroFish_logo_compressed.jpeg" alt="MiroFish Logo" width="75%"/>

<a href="https://trendshift.io/repositories/16144" target="_blank"><img src="https://trendshift.io/api/badge/repositories/16144" alt="666ghj%2FMiroFish | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

简洁通用的群体智能引擎，预测万物
</br>
<em>A Simple and Universal Swarm Intelligence Engine, Predicting Anything</em>

<a href="https://www.shanda.com/" target="_blank"><img src="./static/image/shanda_logo.png" alt="666ghj%2MiroFish | Shanda" height="40"/></a>

[![GitHub Stars](https://img.shields.io/github/stars/666ghj/MiroFish?style=flat-square&color=DAA520)](https://github.com/666ghj/MiroFish/stargazers)
[![GitHub Watchers](https://img.shields.io/github/watchers/666ghj/MiroFish?style=flat-square)](https://github.com/666ghj/MiroFish/watchers)
[![GitHub Forks](https://img.shields.io/github/forks/666ghj/MiroFish?style=flat-square)](https://github.com/666ghj/MiroFish/network)
[![Docker](https://img.shields.io/badge/Docker-Build-2496ED?style=flat-square&logo=docker&logoColor=white)](https://hub.docker.com/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/666ghj/MiroFish)

[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?style=flat-square&logo=discord&logoColor=white)](http://discord.gg/ePf5aPaHnA)
[![X](https://img.shields.io/badge/X-Follow-000000?style=flat-square&logo=x&logoColor=white)](https://x.com/mirofish_ai)
[![Instagram](https://img.shields.io/badge/Instagram-Follow-E4405F?style=flat-square&logo=instagram&logoColor=white)](https://www.instagram.com/mirofish_ai/)

[English](./README.md) | [中文文档](./README-ZH.md)

For automation and AI-agent execution without the browser UI, see [AI_HEADLESS_RUNNER.md](./AI_HEADLESS_RUNNER.md).

</div>

## Stable Fork Quick Start

This fork integrates MiroFish with the course backtesting/research features:

- simulation observability dock and artifact browsing
- multi-model routing with OpenRouter/DeepInfra model maps and LLM telemetry
- scheduled signal/noise injection for temporal backtesting
- wiki-backed report memory and experimental memory fallback
- S2/S3 compact benchmark artifacts for football, Bolivia, and IPC
- Linea 6 entropy analysis tools
- Qwen/truncated-JSON resilience with tested delimiter repair
- deterministic smoke/example commands for reviewers

### Verify The Checkout

```bash
cp .env.example .env
npm run setup:all
npm run check
```

`npm run check` runs repository hygiene, the offline smoke/example, the full
test suite, and the frontend build. None of these commands call paid APIs.
Generated artifacts stay under the git-ignored `outputs/` directory.

If `make` is available, equivalent targets are:

```bash
make smoke-test
make run-example
make test
make check
```

### Run The App Locally

```bash
cp .env.example .env
npm run setup:all
npm run dev
```

Service URLs:

- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:5001/health`

### Docker / Compose

```bash
cp .env.example .env
docker compose up --build --wait
npm run docker-test
```

Compose builds this checkout locally and exposes the same frontend/backend
ports. Paid LLM keys are only required for real simulations, not for the offline
smoke/example commands or the limited UI/health startup. Stop the stack with
`npm run docker-down`.

`npm run docker-test` runs the offline smoke, example, backend test suite, and
frontend production build inside the container. Repository hygiene runs from
the host checkout through `npm run hygiene`, because Git metadata and local
secrets are intentionally excluded from the image.

The first image build downloads the OASIS/ML dependency stack and can take
several minutes. Later builds reuse BuildKit caches. The default service has a
6 GB memory limit and does not auto-restart after it is stopped.

The default Compose stack starts only the app so lower-memory machines can run
the smoke path. Start Neo4j in the same network only when you need Graphiti from
inside Docker:

```bash
docker compose --profile graphiti up --build
```

### Real Provider Smoke

The default smoke is offline. To verify the paid path end to end with a small,
bounded run, set only `OPENROUTER_API_KEY` in `.env` or the shell and run:

```bash
npm run docker-up:openrouter-smoke
npm run smoke-test:real
npm run docker-down:openrouter-smoke
```

This opt-in test uses Qwen3-8B plus Qwen embeddings through OpenRouter, a
1.2 KB seed, one Graphiti chunk, a small generated agent set, and nine simulated
rounds. Only the final hour activates agents. It requires non-empty graph,
OASIS actions, experimental-memory evidence, a ReportAgent report, sanitized
artifacts, and graceful environment shutdown. Artifacts are written below
`outputs/real-smoke/` and remain git-ignored. The command is intentionally not
part of `npm run check` because it consumes provider credits. The smoke requests
Spanish output because this fork ships complete native ReportAgent prompts for
`es` and `zh`; English currently falls back to the original Chinese prompts.

The same bounded flow can use DeepInfra with Gemma 3 and BGE-M3. Set only
`DEEPINFRA_API_KEY` and run:

```bash
npm run docker-up:deepinfra-smoke
npm run smoke-test:real
npm run docker-down:deepinfra-smoke
```

Both provider overlays map secrets only at runtime and never write them into
the repository or generated evidence.

### Research Docs

- Upstream PR candidates: `docs/upstream_pr_candidates.md`
- Verified real E2E smoke: `docs/real_e2e_smoke.md`
- Headless runner: `AI_HEADLESS_RUNNER.md`
- S2 positional injection: `backtesting/case-a-s2-positional-noise/`
- S2 positional v2 multi-provider results:
  `backtesting/case-a-s2-positional-noise-v2/`
- S3 cross-topic injection:
  `backtesting/s3-cross-topic-injection/evaluation/results_analysis.md`
- IPC tri-model multi-agent:
  `backtesting/ipc-trimodel-multiagent/RESULTS_ANALYSIS.md`
- Linea 6 entropy:
  `docs/linea6_entropia.md`

### Known Limits

The smoke path proves repository integrity and deterministic artifact creation.
Full OASIS simulations still require provider API keys, OASIS/CAMEL-compatible
runtime dependencies, and enough model quota for the selected matrix.

The default Docker image uses the official CPU-only PyTorch index. MiroFish
uses hosted model providers by default and Docker Compose does not expose a
GPU, so CUDA runtime wheels are intentionally excluded. GPU/local-model setups
require a separate dependency profile and are not part of the supported
one-command path. The image measured approximately 4.19 GB in the 2026-07-10
clean-build validation, down from 14.3 GB with CUDA wheels.

## ⚡ Overview

**MiroFish** is a next-generation AI prediction engine powered by multi-agent technology. By extracting seed information from the real world (such as breaking news, policy drafts, or financial signals), it automatically constructs a high-fidelity parallel digital world. Within this space, thousands of intelligent agents with independent personalities, long-term memory, and behavioral logic freely interact and undergo social evolution. You can inject variables dynamically from a "God's-eye view" to precisely deduce future trajectories — **rehearse the future in a digital sandbox, and win decisions after countless simulations**.

> You only need to: Upload seed materials (data analysis reports or interesting novel stories) and describe your prediction requirements in natural language</br>
> MiroFish will return: A detailed prediction report and a deeply interactive high-fidelity digital world

### Our Vision

MiroFish is dedicated to creating a swarm intelligence mirror that maps reality. By capturing the collective emergence triggered by individual interactions, we break through the limitations of traditional prediction:

- **At the Macro Level**: We are a rehearsal laboratory for decision-makers, allowing policies and public relations to be tested at zero risk
- **At the Micro Level**: We are a creative sandbox for individual users — whether deducing novel endings or exploring imaginative scenarios, everything can be fun, playful, and accessible

From serious predictions to playful simulations, we let every "what if" see its outcome, making it possible to predict anything.

## 🌐 Live Demo

Welcome to visit our online demo environment and experience a prediction simulation on trending public opinion events we've prepared for you: [mirofish-live-demo](https://666ghj.github.io/mirofish-demo/)

## 📸 Screenshots

<div align="center">
<table>
<tr>
<td><img src="./static/image/Screenshot/运行截图1.png" alt="Screenshot 1" width="100%"/></td>
<td><img src="./static/image/Screenshot/运行截图2.png" alt="Screenshot 2" width="100%"/></td>
</tr>
<tr>
<td><img src="./static/image/Screenshot/运行截图3.png" alt="Screenshot 3" width="100%"/></td>
<td><img src="./static/image/Screenshot/运行截图4.png" alt="Screenshot 4" width="100%"/></td>
</tr>
<tr>
<td><img src="./static/image/Screenshot/运行截图5.png" alt="Screenshot 5" width="100%"/></td>
<td><img src="./static/image/Screenshot/运行截图6.png" alt="Screenshot 6" width="100%"/></td>
</tr>
</table>
</div>

## 🎬 Demo Videos

### 1. Wuhan University Public Opinion Simulation + MiroFish Project Introduction

<div align="center">
<a href="https://www.bilibili.com/video/BV1VYBsBHEMY/" target="_blank"><img src="./static/image/武大模拟演示封面.png" alt="MiroFish Demo Video" width="75%"/></a>

Click the image to watch the complete demo video for prediction using BettaFish-generated "Wuhan University Public Opinion Report"
</div>

### 2. Dream of the Red Chamber Lost Ending Simulation

<div align="center">
<a href="https://www.bilibili.com/video/BV1cPk3BBExq" target="_blank"><img src="./static/image/红楼梦模拟推演封面.jpg" alt="MiroFish Demo Video" width="75%"/></a>

Click the image to watch MiroFish's deep prediction of the lost ending based on hundreds of thousands of words from the first 80 chapters of "Dream of the Red Chamber"
</div>

> **Financial Prediction**, **Political News Prediction** and more examples coming soon...

## 🔄 Workflow

1. **Graph Building**: Seed extraction & Individual/collective memory injection & GraphRAG construction
2. **Environment Setup**: Entity relationship extraction & Persona generation & Agent configuration injection
3. **Simulation**: Dual-platform parallel simulation & Auto-parse prediction requirements & Dynamic temporal memory updates
4. **Report Generation**: ReportAgent with rich toolset for deep interaction with post-simulation environment
5. **Deep Interaction**: Chat with any agent in the simulated world & Interact with ReportAgent

## 🚀 Quick Start

### Option 1: Source Code Deployment (Recommended)

#### Prerequisites

| Tool | Version | Description | Check Installation |
|------|---------|-------------|-------------------|
| **Node.js** | 20.19+ | Frontend runtime, includes npm | `node -v` |
| **Python** | ≥3.11, ≤3.12 | Backend runtime | `python --version` |
| **uv** | Latest | Python package manager | `uv --version` |

#### 1. Configure Environment Variables

```bash
# Copy the example configuration file
cp .env.example .env

# Edit the .env file and fill in the required API keys
```

**Required Environment Variables:**

```env
# LLM API Configuration (supports any LLM API with OpenAI SDK format)
# Recommended: Alibaba Qwen-plus model via Bailian Platform: https://bailian.console.aliyun.com/
# High consumption, try simulations with fewer than 40 rounds first
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus

# Zep Cloud Configuration
# Free monthly quota is sufficient for simple usage: https://app.getzep.com/
ZEP_API_KEY=your_zep_api_key
```

#### Multi-Provider Support (Optional)

Install [Prompture](https://github.com/jhd3197/prompture) to unlock 12+ LLM providers beyond OpenAI-compatible APIs:

```bash
pip install prompture
```

Then use `"provider/model"` format in your `.env`:

| Provider | `LLM_MODEL_NAME` | Cost |
|---|---|---|
| LM Studio | `lmstudio/local-model` | Free (local) |
| Ollama | `ollama/llama3.1:8b` | Free (local) |
| OpenAI | `openai/gpt-4o` | Paid |
| Claude | `claude/claude-sonnet-4-20250514` | Paid |
| Kimi / Moonshot | `moonshot/moonshot-v1-8k` | Paid |
| Groq | `groq/llama-3.1-70b-versatile` | Free tier |
| Google | `google/gemini-1.5-pro` | Paid |
| OpenRouter | `openrouter/anthropic/claude-2` | Paid |

> Without Prompture, the original OpenAI SDK backend works as before — no changes needed.

#### 2. Install Dependencies

```bash
# One-click installation of all dependencies (root + frontend + backend)
npm run setup:all
```

Or install step by step:

```bash
# Install Node dependencies (root + frontend)
npm run setup

# Install Python dependencies (backend, auto-creates virtual environment)
npm run setup:backend
```

#### 3. Start Services

```bash
# Start both frontend and backend (run from project root)
npm run dev
```

**Service URLs:**
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:5001`

**Start Individually:**

```bash
npm run backend   # Start backend only
npm run frontend  # Start frontend only
```

### Option 2: Docker Deployment

```bash
# 1. Configure environment variables (same as source deployment)
cp .env.example .env

# 2. Build this checkout and start the default app stack
docker compose up --build --wait
npm run docker-test
```

Reads `.env` from the root directory by default and maps ports
`3000 (frontend) / 5001 (backend)`.

Stop and remove the default stack with `npm run docker-down`.

Neo4j/Graphiti is intentionally optional in this fork's Compose file. Start it
only when you need Graphiti from inside Docker:

```bash
docker compose --profile graphiti up --build
```

## 📬 Join the Conversation

<div align="center">
<img src="./static/image/QQ群.png" alt="QQ Group" width="60%"/>
</div>

&nbsp;

The MiroFish team is recruiting full-time/internship positions. If you're interested in multi-agent simulation and LLM applications, feel free to send your resume to: **mirofish@shanda.com**

## 📄 Acknowledgments

**MiroFish has received strategic support and incubation from Shanda Group!**

MiroFish's simulation engine is powered by **[OASIS (Open Agent Social Interaction Simulations)](https://github.com/camel-ai/oasis)**, We sincerely thank the CAMEL-AI team for their open-source contributions!

## 📈 Project Statistics

<a href="https://www.star-history.com/#666ghj/MiroFish&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=666ghj/MiroFish&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=666ghj/MiroFish&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=666ghj/MiroFish&type=date&legend=top-left" />
 </picture>
</a>

# QuizForge Live

**GenAI Works Open Agent Hackathon 2026 — Wildcard [Tinkerer] entry** by David Scott Cain (solo, team HackOS).

QuizForge (v1, submitted to Build With AI: Basics) forged one quiz and stopped. **QuizForge Live turns it into a live study agent**: plan the round, generate the questions, grade the answers, adapt the next round — running on **NVIDIA Nemotron**, with the study corpus behind the **Zetaris** AI Data Harness and every model call metered by **Meterless**.

## The loop

1. **PLAN** — Nemotron reads the topic + your graded history and picks focus areas, difficulty, and a probing strategy.
2. **GENERATE** — the QuizForge engine builds the round's quiz (LLM chain, then an offline engine that always works).
3. **GRADE** — answers graded on the spot; score + per-question results.
4. **ADAPT** — every miss gets an **evidence-backed explanation** citing the study sources; weak topics drive the next round's plan.

## Quick start

```bash
cp .env.example .env   # fill in keys (all optional — the demo runs keyless)
python3 app.py         # serve at http://localhost:8765
```

## API

- `GET /` — single-page UI · `GET /sample` — demo study text · `GET /health` — liveness
- `POST /api/generate` — v1 quiz generation (unchanged)
- `POST /api/round` — plan + generate one agentic round `{text, topic, history, count}`
- `POST /api/grade` — grade a round, explain misses with citations `{questions, answers, topic, sources}`
- `GET /api/usage` — metered model-call counts

## Architecture

- `nemotron.py` — NVIDIA Nemotron client (OpenRouter free tier) — the agent's brain.
- `agent.py` — the plan → generate → grade → adapt loop.
- `explain.py` — evidence-backed explanations (the "explain why" core).
- `zetaris.py` — Zetaris AI Data Harness layer (study corpus as fragmented, governed sources).
- `meterless.py` — Meterless/Nightshift metering for every model call.
- `generator.py` — the v1 quiz engine (unchanged).

## License

MIT.

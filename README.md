# QuizForge Live

**GenAI Works Open Agent Hackathon 2026 — Wildcard [Tinkerer] entry** by David Scott Cain (solo, team HackOS).

QuizForge (v1, submitted to Build With AI: Basics) forged one quiz and stopped. **QuizForge Live turns it into a live study agent**: plan the round, generate the questions, grade the answers, adapt the next round — running on **NVIDIA Nemotron**, with the learner's state carried between rounds by the **Meterless Markovian Engine**, the study corpus behind the **Zetaris** AI Data Harness, and every model call metered as inspectable JSONL evidence.

## The loop

1. **PLAN** — Nemotron reads the topic + your graded history and picks focus areas, difficulty, and a probing strategy.
2. **GENERATE** — the QuizForge engine builds the round's quiz (LLM chain, then an offline engine that always works).
3. **GRADE** — answers graded on the spot; score + per-question results.
4. **ADAPT** — every miss gets an **evidence-backed explanation** citing the study sources; weak topics drive the next round's plan.

## Sponsor technology

**Meterless Markovian Engine — INTEGRATED (open-source route).** The four Meterless engines are open source (Apache-2.0, [github.com/Meterless/Meterless](https://github.com/Meterless/Meterless)); upstream ships them as implementation specs plus a TypeScript reference, so `markovian.py` is a faithful standard-library port of the Markovian reference core: config validation, the `[STATE_CHECKPOINT]` marker protocol, the four-level carryover compression cascade (marker → model → heuristic → truncation), and the section-6 efficiency accounting. It is load-bearing, not decorative: each round, the learner's graded history is folded into a canonical state block (COMPLETED = mastered topics, REMAINING = weak topics, DECISIONS = strategy, CONTEXT = session facts), compressed to an 800-token budget, and *that bounded state* — never the raw history — drives the next round's focus and difficulty. Missed topics sit in REMAINING and resurface until mastered. Every engine decision is logged to `logs/events.jsonl` (`trace` per plan, `telemetry` per graded round); every model call is counted in `logs/model_calls.jsonl` with the actual provider and model.

**Nightshift — env-gated route (local-only software).** Nightshift has no hosted console, signup, or cloud endpoint: it is a local app (Windows / Mac), and its Console tab issues the runtime token. When a participant machine runs it, set `METERLESS_BASE_URL=http://127.0.0.1:8088/v1`, `METERLESS_RUNTIME_TOKEN=<token>`, `METERLESS_MODEL=meterless/auto` and QuizForge Live routes Nemotron through it first (the NVIDIA key stays in Nightshift's Providers tab, never in this repo). **With no `METERLESS_*` env set, the app honestly runs on the OpenRouter/NVIDIA free-tier fallback plus the offline heuristic engine** — the full loop, keyless.

**NVIDIA Nemotron — the agent's reasoning model.** Planning and explanations run on Nemotron (through Nightshift when configured; `nvidia/nemotron-3.5-super-vl:free` via OpenRouter otherwise).

**Zetaris AI Data Harness — REST layer built, preflight-gated.** `zetaris.py` implements the documented Zetaris REST surface (Bearer + X-Org-ID + X-Request-ID; SQL via `POST /sql-editor/sqls/run`), verified against Zetaris's own public getting-started scripts, with a `SELECT 1` preflight mirroring theirs. No participant instance URL or key has been issued yet (the workspace access page is still a placeholder), so until one exists the agent runs on the offline local-corpus fallback and the status panel says so.

## Quick start

```bash
cp .env.example .env   # fill in keys (all optional — the demo runs keyless)
python3 app.py         # serve at http://localhost:8765
```

## API

- `GET /` — single-page UI with two tabs: the v1 one-shot forge, and the **Live study loop** (plan → answer → grade → next round focused on your misses, with the bounded Markovian state — COMPLETED / REMAINING — rendered on screen) · `GET /sample` — demo study text · `GET /health` — liveness
- `POST /api/generate` — v1 quiz generation (unchanged)
- `POST /api/round` — plan + generate one agentic round `{text, topic, history, count}`
- `POST /api/grade` — grade a round, explain misses with citations `{questions, answers, topic, sources}`
- `GET /api/usage` — metered model-call counts + JSONL evidence inventory
- `GET /api/status` — integration health panel (Nemotron route, Zetaris, Meterless, Markovian engine)

## Architecture

- `nemotron.py` — NVIDIA Nemotron client: Nightshift first (documented `METERLESS_*` env), OpenRouter free tier as fallback.
- `agent.py` — the plan → generate → grade → adapt loop; plans are decided from the Markovian learner state.
- `markovian.py` — the Meterless Markovian Engine (stdlib port of the Apache-2.0 upstream spec): bounded learner state, marker protocol, compression cascade, efficiency accounting.
- `explain.py` — evidence-backed explanations (the "explain why" core).
- `zetaris.py` — Zetaris AI Data Harness layer (study corpus as fragmented, governed sources).
- `meterless.py` — Meterless metering: JSONL evidence for every model call and engine event.
- `generator.py` — the v1 quiz engine (unchanged).
- `tests/test_stage3a.py` — 27 deterministic offline tests: `python3 -m unittest discover -s tests -v`.

## License

MIT.

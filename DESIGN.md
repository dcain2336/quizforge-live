# QuizForge Live — build design (Stage 1, 2026-10-23)

**Project:** QuizForge Live — "QuizForge Live" entry for the GenAI Works Open Agent Hackathon 2026.
**Lane (primary):** Wildcard [Tinkerer] — bring the existing QuizForge (v1, submitted to Build With AI: Basics on 2026-10-23) and extend it. Entries are judged on the new work, not prior development; the lane requires integrating Zetaris and Meterless.
**Fallback lane:** Track 02 — "The Agent That Can Explain Why".
**Entrant:** David Scott Cain, solo, team "HackOS", registered on hackathon.genai.works under dcain1@my.gcu.edu.
**Deadline:** Tue Oct 27, 2026, 19:45 EDT (23:45 UTC). Results Nov 6.

## 1. What QuizForge v1 already does (reused, not rebuilt)

- `generator.py` — turns pasted study text into a study guide + quiz (MCQ + short answer) + answer key. Provider chain: Groq free → OpenRouter free → offline heuristic. Zero dependencies, every line plain-English commented.
- `app.py` — stdlib-only threaded HTTP server; routes `/` (UI), `/sample`, `/health`, `/api/generate`.
- `static/index.html` — single-page UI. `sample_data/first-responder-sample.txt` — demo material.
- Public repo: https://github.com/dcain2336/quizforge (MIT).

## 2. The agentic loop (the "new work" the Wildcard lane judges)

v1 generated one quiz and stopped. Live turns it into a **study loop**:

```
PLAN → GENERATE → GRADE → ADAPT → (repeat)
```

1. **PLAN** (`agent.plan_round`): Nemotron reads the topic + the learner's graded history and returns a JSON plan — `focus_areas` (2–4 concept labels), `difficulty` (easy/medium/hard), `strategy` (how to probe weak spots). Offline fallback: rule-based escalation (rounds 1–2 easy, 3–4 medium, 5+ hard; revisit missed topics first).
2. **GENERATE** (`agent.run_round`): the v1 engine builds the round's questions (its own provider chain, then offline heuristic). The plan travels with the quiz so the UI shows the adaptation.
3. **GRADE** (`agent.grade_round` via `POST /api/grade`): each answer graded (tolerant match); the score, per-question results, and the metering snapshot go back to the UI.
4. **ADAPT** (`explain.explain_outcome`): every miss gets an **evidence-backed explanation** — Nemotron cites the numbered study sources inline ([1], [2]); if the model is unreachable, a plain offline explanation quotes the source sentence. Miss topics feed the next round's plan.

## 3. Where Zetaris fits (Wildcard requirement #1)

- The study corpus stops being "text the user pasted" and becomes **fragmented sources queried through the Zetaris AI Data Harness** (`zetaris.py`).
- Judging narrative: the agent discovers and queries study material in place through one harness — the "fragmented intelligence" theme that also echoes Track 01.
- Scaffold state: `query_corpus(sql)` / `ingest_source(name, text)` / `local_corpus(text)` stubs. Local fallback keeps the demo alive; Stage 2 wires the real REST cookbook from `zetaris/getting-started` (company_dns sample pattern, dry-run first) once the HackOS workspace supplies the endpoint + key.
- Demo beat: "watch the corpus grow inside the harness" — ingest a second source mid-demo, query it, the agent's next round draws on it.

## 4. Where Meterless/Nightshift fits (Wildcard requirement #2)

- Every Nemotron call is metered through `meterless.count_call(provider, model)` — local counters now, remote POST to the Meterless/Nightshift ingest endpoint once the workspace supplies the event shape (Stage 2).
- Judging narrative: agent ops — the demo shows the `/api/usage` panel: "this round cost N Nemotron calls," proving the loop is observable and budget-aware.
- Fail-open: metering never blocks the loop; without credentials it meters locally.

## 5. Where Nemotron fits (the DGX Spark prize)

- All agentic reasoning (plan, explain) runs on `nvidia/nemotron-3.5-super-vl:free` via OpenRouter (`nemotron.py`; the seat was verified live in ARC on 2026-10-22; override via `NEMOTRON_MODEL`).
- The v1 generator keeps its Groq → OpenRouter → heuristic chain for question *generation* (judges see generation + agentic reasoning on the NVIDIA model).
- In-kind prize target: **NVIDIA DGX Spark Founder's Edition ($4,699)** for best use of Nemotron — permanent ARC hardware.

## 6. The demo story (Wildcard, ~2 min)

1. "QuizForge v1 forged one quiz and stopped." (5s — reuse the submitted video's opening beat)
2. "Live turns it into an agent." Paste topic → **PLAN** appears: focus areas + difficulty chosen by Nemotron. (20s)
3. Answer a round, miss one deliberately → **evidence-backed explanation with citations**. (30s)
4. **ADAPT**: next round's plan visibly targets the missed topic; difficulty steps up. (25s)
5. Sponsor beat: study corpus queried from **Zetaris** (fragmented sources, one harness); **Meterless** usage panel shows the call count. (25s)
6. Close: "plan → generate → grade → adapt — the loop keeps studying with you." (15s)

## 7. Track 02 fallback delta — SUPERSEDED by Stage-2 platform facts (2026-10-23)

- The workspace recon (parent report, Stage 2) established that Tracks 01–03 ALSO require Zetaris as the data layer and at least one Meterless Engine in a working feature, with Nightshift as the primary AI provider. **There is no sponsor-free lane.** The Track 02 pivot below therefore does NOT dodge the integrations.
- REVISED TRIGGER RULE: if **working Zetaris + Meterless credentials are not in hand by Sun Oct 25, 12:00 EDT**, REPORT THE BLOCKER to the parent immediately — do not pivot silently. The Wildcard lane stays primary as long as the credentials arrive.
- What survives regardless: the agentic loop runs fully on the offline engine (plan → generate → grade → adapt) and is fully demo-able without any sponsor keys, so the build never stalls waiting for credentials. The Zetaris integration (documented REST surface, env-driven) and Nightshift route are coded and verified in shape; live verification happens the moment credentials land.

## 8. File map

```
quizforge-live/
  app.py            # server: v1 routes + /api/round, /api/grade, /api/usage
  generator.py      # v1 engine (unchanged) — question generation
  nemotron.py       # NEW — NVIDIA Nemotron client via OpenRouter free tier
  agent.py          # NEW — the agentic loop: plan / run_round / grade_round
  explain.py        # NEW — evidence-backed explanations (Track 02 core)
  zetaris.py        # NEW — Zetaris data harness (stubbed until Stage 2)
  meterless.py      # NEW — Meterless/Nightshift metering (local now, remote Stage 2)
  static/index.html # v1 UI (Live tab wired in Stage 3)
  sample_data/      # demo material
  .env.example      # all keys incl. Zetaris + Meterless
  DESIGN.md         # this file
  PLATFORM-NOTES.md # scoring, submission format, sponsor key mechanics
  BUILD-LOG.md      # running build log
  README.md         # entry README (Stage 3)
  LICENSE           # MIT
```

## 9. Standing rules honored

- Free only: no card anywhere in the build or the entry. Nemotron via `:free` OpenRouter seat; Zetaris/Meterless via the workspace's free sponsor credits only.
- Per-line commenting rule (2026-10-15): every line of new code carries a plain-English comment — scaffold holds; Stage 2/3 code must too.
- Legit and factually sound: no EOD topics; demo shows real outputs, not faked footage.

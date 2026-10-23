# QuizForge Live — submission pack (Stage 3b, 2026-10-23)

> **FILE-LOCAL NOTES — not part of the submission text (delete before pasting anywhere):**
>
> - **Pivot trigger:** if Zetaris is still TBC at **Sun Oct 25, 12:00 EDT**, reconsider the primary track
>   (Track 02 — AI Agents for Operations & Enterprise Workflows — per PLATFORM-NOTES.md). Roster locks when
>   the first submission is created, so decide before submitting. Deadline: **Tue Oct 27, 19:45 EDT**.
> - **Assets:** demo video `demo/quizforge-live-demo.mp4` (2:02, 720p, verified) — upload to Scott's
>   **personal** YouTube channel, unlisted (his standing rule for contest videos), then paste the link below.
>   Deck: `demo/quizforge-live-deck.pdf` (11 slides). Repo: https://github.com/dcain2336/quizforge-live — the
>   Stage 3b assets commit is local only; **push before submitting** so the public repo matches.
> - **Pre-existing-components wording:** the organizers ask for a declaration of components built before
>   Oct 22 00:00 UTC. Workspace records show QuizForge v1 was built Oct 22–23, 2026 and submitted to
>   Build With AI on Oct 23 — so the declaration below states v1's origin and dates factually rather than
>   asserting it predates the Oct 22 boundary. Adjust at submit time if the form's exact wording demands it.
> - **Known product gap (not in the submission text):** the shipped web UI is still the v1 shell
>   (`/api/generate` one-shot flow). The Live loop is fully implemented at the API level
>   (`/api/round`, `/api/grade`, `/api/usage`, `/api/status`) and is what the demo films; a browser
>   "Live" tab wired to those endpoints is listed in the deck's future enhancements. If time allows
>   before Oct 27, wiring that tab is the highest-value remaining product work (Product & UX points).

---

## Submission text (paste into the HackOS submission form)

**Project name:** QuizForge Live

**Tagline:** The study agent that remembers what you missed.

**Primary track:** Wildcard [Tinkerer]

**Team:** David Scott Cain (solo) — team HackOS

**Description:**

QuizForge Live turns any pasted study material into a live study agent. Where a quiz generator forges one quiz and stops, QuizForge Live runs a loop — PLAN → GENERATE → GRADE → ADAPT — round after round, until the learner has mastered the material.

Each plan is decided from a small, bounded learner state carried by the Meterless Markovian engine: which topics are completed, which remain (the weak ones), the current strategy, and the difficulty — compressed to an 800-token budget and never the raw history, so planning cost stays constant no matter how long the learner studies. Questions are generated from the learner's own material; grading is instant, and every miss returns an explanation that cites the study source it came from. Missed topics are folded back into the state and resurface as the next round's focus until they are mastered.

In the filmed demo (a first-responder exam excerpt, run fully offline), round 1 is an easy baseline probe of four questions; the learner deliberately misses every question on two topics and scores 1/4. Round 2's plan — decided by the engine from a 69-token state — targets exactly those two topics, SAMPLE and DCAP-BTLS. Every step leaves evidence: plan traces and grade telemetry in a JSONL log, metered model calls, and `/api/usage` + `/api/status` endpoints that report exactly what the agent did and which integrations are live.

The whole loop runs keyless and offline with zero dependencies (Python standard library only), so anyone can reproduce it; model routes enrich planning and explanations when configured.

**Sponsor technology explanation:**

- **Meterless (Markovian engine) — integrated and load-bearing.** Upstream ships the engines as implementation specifications plus TypeScript references ("not a runtime library"), so we ported the Markovian engine's core faithfully into Python's standard library (`markovian.py`, Apache-2.0, provenance and adaptation notes in the file header): the canonical COMPLETED / REMAINING / DECISIONS / CONTEXT state block, the `[STATE_CHECKPOINT]` marker protocol, the 4-level carryover cascade (verbatim → line-truncated → decisions-only → marker-only), and token-budget accounting — measured at a 45% context saving on 3 full history chunks (48,000 → 26,400 tokens), with the saving honestly reported as 0 for histories too small to compress. The engine decides every round's focus and difficulty in QuizForge Live.
- **Meterless (Nightshift) — implemented, env-gated.** `nemotron.py` routes model calls to Nightshift's OpenAI-compatible endpoint (`/v1/chat/completions`) first when `METERLESS_BASE_URL` / `METERLESS_RUNTIME_TOKEN` are set. Nightshift is a local-install product (Windows/Mac app; its Console tab issues the runtime token) with no hosted endpoint, so this route activates on a participant machine; the code path is complete and covered by offline routing tests.
- **Zetaris — client built, preflight-gated.** The full REST layer (`zetaris.py`) implements Zetaris's documented surface (Bearer auth + `X-Org-ID` + `X-Request-ID`, SQL via `POST /sql-editor/sqls/run`) and mirrors their own getting-started preflight (`GET /datasource/datasources`, `SELECT 1`). The organizers' participant instance is still a TBC placeholder in the event workspace — no instance URL or key has been issued — so until one exists, study corpora run on the documented offline local-corpus fallback, and `/api/status` reports the Zetaris state exactly (`configured: false`) rather than claiming a live connection.
- **Cursor — not used.** The organizers confirmed participants may use any coding tool and included no free Cursor credits in this event. We state this plainly rather than claim a tool we did not use.
- **NVIDIA — Nemotron.** NVIDIA's Nemotron (`nvidia/nemotron-3.5-super-vl:free`) is the reasoning model for plan refinement and explanations when a route is configured: via Nightshift where installed, with a live-verified OpenRouter free-tier seat as the fallback route. When no route is configured, the loop runs on the Markovian engine plus the offline generator — the same code paths, no blocked features.

**Declaration of pre-existing components:**

- **QuizForge v1** — the question-generation engine (`generator.py`) and the static web UI — was built for the **Build With AI: Basics** hackathon and submitted there on **Oct 23, 2026** (Devpost: quizforge-ki0zgj; repo: github.com/dcain2336/quizforge). It is declared here as the pre-existing base of this Wildcard entry.
- **New work in this event:** the Live agent loop (`agent.py`), the Meterless Markovian engine port (`markovian.py`), the Zetaris REST layer (`zetaris.py`), the Nightshift-first model routing (`nemotron.py`), the evidence-cited explanations (`explain.py`), and the JSONL evidence system (`meterless.py`, `logs/`), plus the demo film and this deck.

**Links:**

- Public repo: https://github.com/dcain2336/quizforge-live
- Demo video (1–4 min): https://www.youtube.com/watch?v=ozvwvb0QFh0 (unlisted, Scott's personal channel @davidcain3710; uploaded Oct 23, 2026; checks clean)
- Slide deck: `quizforge-live-deck.pdf` (11 slides, covering the 8 required points)
- Run it: `python3 app.py` → http://localhost:8765 (Python 3 standard library only; the full loop works with no API keys)
- Tests: 27 deterministic offline tests, all passing — `python3 -m unittest discover -s tests`
- License: MIT. The Markovian engine port is Apache-2.0 (Meterless), attributed in `markovian.py`.

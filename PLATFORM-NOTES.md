# GenAI Works Open Agent Hackathon — platform notes (verified live 2026-10-23 ~10:15 EDT; workspace pull pending)

## Confirmed on the public event page (https://hackathon.genai.works/event/open-agent-hackathon-2026)

- Submissions close **Tue Oct 27, 2026, 23:45 UTC = 19:45 EDT — HARD deadline.** Registration closes at the same instant. Results announced Nov 6, 16:00 UTC.
- Entrant: David Scott Cain, solo, team "HackOS", registered under dcain1@my.gcu.edu. One account per participant.
- **Track 01 — Solving Fragmented Intelligence:** "Demonstrate a clever ability to discover and work across fragmented data sources." $3,700 ($1,600 / $1,200 / $900).
- **Track 02 — The Agent That Can Explain Why:** "Build agents that investigate complex questions across multiple data sources, connect findings, and produce evidence-backed answers or recommendations." $3,700 (prize split presumably $1,600 / $1,200 / $900 like Track 01 — confirm).
- **Track 03 — Reasoning Architecture:** "Demonstrate a novel ability to turn data, knowledge, memory, and reasoning into reliable decisions and actions." $3,600 ($1,500 / $1,200 / $900).
- **Wildcard [Tinkerer] — Bring Your Own Project:** "Bring an existing project, prototype or concept and extend it using sponsor technology such as Meterless and Zetaris. Entries are judged on the same criteria as the other tracks, **must integrate Zetaris and Meterless, and are scored on the new work rather than prior development.**" $2,000 ($1,000 / $600 / $400).
- **In-kind prize — Best use of NVIDIA Nemotron: NVIDIA DGX Spark AI Supercomputer (Founder's Edition), $4,699 value.** Cross-track.
- Scoring: 100 points. Only **Impact 30** is public: "Consistency with the challenge statements: how effectively the solution addresses a meaningful real-world problem for its intended users." Other 70 pts live in the HackOS workspace.
- Eligibility: open worldwide, 16+ at build-window start; organizer/judging-sponsor employees may enter but not win cash. No federal-employee exclusion found.
- Headline collab: Zetaris (AI Data Harness) + SpaceXAI (Grok Build coding harness). ~5,000 builders expected from 100+ countries. Mentors from NVIDIA, Zetaris, SpaceX "reviewing your work in real time." Sponsor APIs/resources/workshops free; submission free.
- Zetaris getting-started: public repo `zetaris/getting-started` + `company_dns` sample via REST cookbook; dry-run before creating anything; AI-coding-assistant prompt included. Medium post by Michael Hay (~3 days old) documents the dev experience.

## Still to pull from the HackOS workspace (browser task for the main agent)

1. Full 100-point scoring breakdown (the other 70 pts).
2. Submission format: repo URL + demo video length limits + any writeup template + whether the submission happens on the platform or Devpost.
3. Zetaris access mechanics: where in the workspace the API URL + key come from; free credit limits; the exact REST cookbook URL.
4. Meterless / Nightshift access mechanics: where the endpoint + key come from; the documented event shape for usage logging.
5. Whether Wildcard judging requires BOTH Zetaris and Meterless integrated ("must integrate Zetaris and Meterless" reads as both — confirm with mentors or FAQ).
6. Bright Data / Cursor / SpaceXAI bonus mechanics (any extra credit claims or tracks).
7. Track 02 prize split + whether tracks 01–03 require any sponsor integration (none stated publicly).

## Stage-2 findings (2026-10-23, build subagent) — sponsor integrations, verified against Zetaris's public getting-started repo

- **Zetaris REST surface (verified from their own reference scripts, stdlib-safe):** base `ZETARIS_REST_URL` (e.g. `https://<instance>/api/v1.0`); headers `Authorization: Bearer <key>`, `X-Org-ID` (default "1"), `X-Request-ID` (fresh UUID per call); SQL runs at `POST /sql-editor/sqls/run` with body `{"queryId": <uuid>, "sql": <sql>, "source": "SqlEditor", "limit": <n>}` and rows under `data`; instance health via `GET /datasource/datasources`. Implemented in `zetaris.py` (`preflight()`, `run_sql()`, `query_corpus()`, `datasources()`), all env-driven, zero deps.
- **Zetaris access BLOCKER (honest):** their docs route participants to "their own Zetaris instance, either downloaded locally or deployed through AWS." This sandbox cannot run Docker; the e2-micro's 1 GB RAM cannot host the Zetaris Java/Spark stack. The workspace's "free Zetaris instance for participants" (Getting-access section) is still a TBC placeholder. **The ONLY viable path is a cloud-hosted instance URL + API key + org id from the HackOS task board** — then the integration works from anywhere, since it is plain HTTPS. If the only documented path is local Docker, the harness integration can be demoed only against a provisioned instance the judges supply; `query_corpus` fails open with exact next steps.
- **Nightshift route (Stage 2):** `nemotron.py` now routes Nightshift-first (env `NIGHTSHIFT_API_URL` + `NIGHTSHIFT_API_KEY`), NVIDIA key stays in Nightshift's Providers tab (never in code); OpenRouter free is the fallback. `get_provider()` selects the route; agent.py/explain.py meter with the ACTUAL provider+model (the auto-router honesty rule). Assumption flagged in code: Nightshift exposes OpenAI-compatible `/chat/completions` — confirm from the workspace.
- **Meterless JSONL (Stage 2):** every model call appends a JSONL line (`ts`, `session`, `seq`, `event: model_call`, `provider`, `model`, `tokens_in/out`) to `logs/model_calls.jsonl`; `log_event(kind, payload)` writes audit/trace/telemetry/provenance to `logs/events.jsonl`; remote POST mirrors when credentials exist, failing open. `/api/usage` now shows counts + evidence inventory; new `/api/status` reports integration health.
- **Still to fetch from the workspace (batched ask to the parent):** (1) HackOS task board "Where do I get sponsor credits?" — Zetaris instance URL + API key + org id; Meterless/Nightshift endpoint + API key + documented usage-event shape; NVIDIA key for the Nightshift Providers tab. (2) Participant Setup Guide Data layer — cloud-hosted vs Docker-only verdict. (3) Zetaris Getting-access section — check whether the TBC placeholder was updated. (4) Cursor provisioning mechanics. (5) README Template / Pitch Deck Template / Demo Script Template contents or locations. (6) Create the public GitHub repo `dcain2336/quizforge-live` (browser github.com/new) so the code can be pushed.

## Lane decision (locked from the brief)

- **Primary: Wildcard [Tinkerer]** — explicit reuse lane; QuizForge is the existing project; new work = the live agentic loop + Zetaris + Meterless integration.
- **Fallback: Track 02** — pivot trigger: Zetaris credentials not in hand by Sun Oct 25, 12:00 EDT.
- **Nemotron in-kind angle rides with the primary build** — plan/explain calls on `nvidia/nemotron-3.5-super-vl:free` (ARC seat verified 2026-10-22).

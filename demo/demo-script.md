# QuizForge Live — demo video script (Stage 3b, 2026-10-23)

**Format:** 1280×720 (720p), H.264 + AAC, target runtime ~2:00–2:30 (hard window: 1–4 minutes).
**Method:** genuine capture only. `capture.py` runs the real `app.py` locally with a scrubbed
environment (no API keys anywhere), so the app runs its offline engine + the Meterless Markovian
planner — exactly the keyless path a judge can reproduce. Every screen is either the app's own UI
or a verbatim transcript of the live API responses rendered in Chromium's native text view
(full raw responses saved under `demo/transcripts/raw/`). The usage/status endpoints were also
filmed as transcripts (`recapture_json.py`) after Chromium's raw JSON view proved unframeable
(single overflowing lines); the payloads are the live ones either way. Nothing is mocked.
**Flow filmed:** load sample → POST /api/round (round 1) → answer with deliberate misses →
POST /api/grade (evidence-quoted explanations) → POST /api/round with the graded history
(round 2 plan = the missed topics) → GET /api/usage → GET /api/status.
**Topic names** in beats 4–5 are confirmed against `demo/shots/capture_meta.json` after capture:
the filmed session's questions covered SAMPLE, DCAP-BTLS (×2), and Airway; the deliberate misses
were SAMPLE + DCAP-BTLS (score 1/4), and round 2's focus came back exactly
`["DCAP-BTLS", "SAMPLE"]` — `focus_matches_missed: true` in the metadata.

## Timed beats

| # | Target time | Shot | On screen | Narration |
|---|-------------|------|-----------|-----------|
| 1 | 0:00–0:16 | shot01_home.png | QuizForge Live home page, empty paste box | "QuizForge forged one quiz and stopped. QuizForge Live turns it into a study agent: it plans a round, generates the questions, grades your answers, and adapts what comes next. It starts the same way — paste in any study material." |
| 2 | 0:16–0:31 | shot02_sample.png | Sample first-responder text loaded in the textarea | "I'll load the built-in sample: a first-responder exam excerpt covering scene safety, A V P U, SAMPLE, and O P Q R S T. Then I'll start a live round against the app's real A P I." |
| 3 | 0:31–0:47 | shot03_round1.png | Round 1 response transcript, framed on the plan block | "The agent plans before it asks. Its memory is the Meterless Markovian engine: everything it knows about the learner, compressed into one small, bounded state block. Round one is a baseline probe — easy difficulty, four questions." |
| 4 | 0:47–1:02 | shot04_grade.png | Grade response transcript, framed on the first explanation | "I answer all four — and deliberately miss every question on two topics. Grading is instant, one of four, and every miss comes back with an explanation that quotes the study material itself, word for word. Nothing invented, nothing to hunt down." |
| 5 | 1:02–1:22 | shot05_round2.png | Round 2 response transcript, framed on the plan block (the money shot) | "Now the money shot. Round two's plan targets exactly the two topics I missed — SAMPLE and D C A P B T L S — carried forward in the state's remaining list until I master them. The raw history is never re-read; every round costs the same small, bounded context." |
| 6 | 1:22–1:36 | shot06_usage.png | GET /api/usage transcript (evidence inventory) | "And every step leaves evidence. The usage endpoint inventories the session's J S O N L evidence log: three events — a trace for each plan, telemetry for the graded round — and any model calls would be metered here too, with the actual provider named." |
| 7 | 1:36–1:53 | shot07_status.png | GET /api/status transcript, framed on the Markovian engine block | "The status panel is honest about the sponsor wiring: the Zetaris data-harness client is built and preflight-checked, waiting on the organizers' participant instance; Nemotron routes through Nightshift where it's installed locally, with a free OpenRouter seat behind it." |
| 8 | 1:53–2:06 | shot01_home.png (reprise) | Home page again, closing frame | "Plan, generate, grade, adapt. QuizForge Live — the QuizForge you know, extended with the Meterless Markovian engine, the Zetaris data harness, and NVIDIA Nemotron. It keeps studying with you." |

Narration ≈ 295 words ≈ 1:58 of speech at ~150 wpm, plus 0.7 s of padding per segment
→ ≈ 2:05 total. If capture shows different missed topics than AVPU/OPQRST, beat 5's
narration is re-voiced with the captured topics before assembly — the video never
names a topic the capture did not produce.

---

## Addendum (Stage 3d, 2026-10-23) — combined v2 film

**Deliverable:** `quizforge-live-demo-v2.mp4` — the film above (2:02) + a 2.6 s title card
("Update: the loop, live in the browser") + the Live-tab addendum below = **2:58 total**
(1280×720, H.264 + AAC, ffprobe-verified, frame-checked at every seam).
**Method:** `capture_addendum.py` runs the real `app.py` with the same scrubbed environment and
drives the shipped UI itself — Live tab, sample button, radio inputs, grade and next-round
buttons; the /api/round and /api/grade payloads were intercepted read-only to verify the
narration (`shots/addendum_meta.json`, `focus_matches_missed: true`). Assembled by
`assemble_v2.py` with the same recipe as `assemble.py`; narration in `narration_addendum.txt`.
**Session filmed:** round 1 topics Airway, OPQRST, AVPU, MOI; deliberate misses Airway + OPQRST;
grade **2/4**; round 2 focus `["Airway", "OPQRST"]`, state COMPLETED: AVPU, MOI /
REMAINING: Airway, OPQRST, 68 carryover tokens.

| # | Time (in v2) | Shot | On screen | Narration |
|---|--------------|------|-----------|-----------|
| C | 2:02–2:05 | card_update.png | Title card (ink background) | — (silent) |
| A1 | 2:05–2:17 | shot09_live_setup.png | Live tab: honesty banner, sample loaded, 4-question round set | "Update — the loop now runs live in the browser. This is the new Live tab: same app, same offline engine, and the banner says exactly that. No keys, nothing hidden." |
| A2 | 2:17–2:28 | shot10_live_round1.png | Round 1 in the browser: plan, 61-token state, questions | "Round one, planned right on the page by the Meterless Markovian engine — focus, difficulty, strategy — with the bounded learner state underneath: sixty-one tokens of carryover. Four questions, dealt in the browser." |
| A3 | 2:28–2:41 | shot11_live_grade.png | Results card: 2/4, cited explanations, missed pills | "I answer in the browser and deliberately miss Airway and O P Q R S T. Instant grade — two of four — every miss quoting the study material back at me, the missed topics pinned as pills." |
| A4 | 2:41–2:58 | shot12_live_round2.png | Round 2 plan: focus pills = the misses, state on screen | "One click plans round two — and its focus lands on exactly those two misses. The state reads: completed, A V P U and M O I; remaining, Airway and O P Q R S T. Sixty-eight tokens. The loop now happens where the learner sits: in the browser." |

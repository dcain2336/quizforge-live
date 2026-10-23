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

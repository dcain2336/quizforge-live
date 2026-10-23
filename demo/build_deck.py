# build_deck.py - build the QuizForge Live submission slide deck (HTML slides rendered to PDF by headless Chromium).  # Module header: purpose of this file.
# Written 2026-10-23 for Stage 3b of the GenAI Works Open Agent Hackathon entry. Demo tooling, not part of the shipped app.  # Provenance: demo tooling.
# The deck covers exactly the organizers' 8 required points, one numbered section each, plus a title and a closing slide.  # Structure: 8 required points.
# Sponsor claims are the verified ones from PLATFORM-NOTES.md: Meterless integrated, Nightshift env-gated, Zetaris preflight-gated, Cursor not used.  # Honesty: sponsor state.
# Import the OS module for path building.  # Library: os.
import os  # Make the os module available.
# Import subprocess so pdfinfo can verify the finished deck.  # Library: subprocess.
import subprocess  # Only used for the final page count check.
# Import the synchronous Playwright API, our renderer (Chromium prints the slides to PDF).  # Library: playwright.
from playwright.sync_api import sync_playwright  # The sync API keeps the build readable top to bottom.
# Define the folder this script lives in (the demo folder).  # Constant: demo folder.
HERE = os.path.dirname(os.path.abspath(__file__))  # Absolute path of demo/.
# Define the HTML slides path (kept beside the PDF for later edits).  # Constant: slides HTML.
SLIDES_HTML = os.path.join(HERE, "slides.html")  # The editable deck source.
# Define the PDF deliverable path.  # Constant: deck PDF.
DECK_PDF = os.path.join(HERE, "quizforge-live-deck.pdf")  # The submission artifact.
# Define the shared stylesheet: the app's own palette (ink, forge orange, paper) so deck and product match.  # Constant: CSS.
CSS = """  /* Open the stylesheet block (a Python string, rendered verbatim into the HTML head). */
@page { size: 1280px 720px; margin: 0; }  /* One landscape 16:9 page per slide, no printer margins. */
* { box-sizing: border-box; margin: 0; padding: 0; }  /* Predictable sizing everywhere. */
body { font-family: Georgia, 'Times New Roman', serif; background: #faf7f2; color: #1c2333; }  /* The app's paper and ink. */
.slide { width: 1280px; height: 720px; padding: 56px 72px; page-break-after: always; overflow: hidden; position: relative; display: flex; flex-direction: column; }  /* One fixed-size slide per page. */
.slide:last-child { page-break-after: auto; }  /* No trailing blank page after the closer. */
.kicker { font-size: 15px; letter-spacing: 0.22em; text-transform: uppercase; color: #b3541e; margin-bottom: 14px; }  /* Small orange section label. */
h1 { font-size: 64px; line-height: 1.05; margin-bottom: 18px; }  /* Title-slide headline. */
h2 { font-size: 40px; line-height: 1.12; margin-bottom: 26px; border-bottom: 3px solid #b3541e; padding-bottom: 12px; }  /* Section headline with the forge rule. */
p, li { font-size: 21px; line-height: 1.45; }  /* Body copy sized for projection. */
ul { margin-left: 26px; }  /* Indented bullets. */
li { margin-bottom: 13px; }  /* Breathing room between bullets. */
strong { color: #b3541e; }  /* Orange emphasis matches the app. */
.sub { font-size: 26px; font-style: italic; opacity: 0.85; line-height: 1.4; }  /* Title-slide subtitle. */
.meta { margin-top: auto; font-size: 18px; opacity: 0.75; line-height: 1.5; }  /* Footer block pinned to the slide bottom. */
.flow { display: flex; align-items: stretch; gap: 10px; margin: 10px 0 26px; }  /* The architecture loop as a row of boxes. */
.box { flex: 1; background: #1c2333; color: #f5efe4; border-radius: 10px; padding: 16px 14px; font-size: 18px; line-height: 1.35; }  /* One loop stage. */
.box b { display: block; font-size: 20px; color: #ffb37a; margin-bottom: 6px; }  /* Stage name inside a box. */
.arrow { align-self: center; font-size: 26px; color: #b3541e; }  /* Orange arrows between stages. */
.cols { display: flex; gap: 36px; }  /* Two-column layout for text slides. */
.col { flex: 1; }  /* Equal columns. */
.shots { display: flex; gap: 28px; }  /* Side-by-side screenshots on the visuals slides. */
.shot { flex: 1; }  /* One screenshot column. */
.shot img { width: 100%; border: 1px solid #e3ddd2; border-radius: 8px; display: block; }  /* Framed genuine capture. */
.cap { font-size: 16.5px; font-style: italic; opacity: 0.8; margin-top: 10px; line-height: 1.4; }  /* Caption under each capture. */
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 19px; background: #f0e9dd; padding: 1px 6px; border-radius: 5px; }  /* Inline code chips. */
.big { font-size: 24px; }  /* Slightly larger body for short slides. */
"""  # Close the stylesheet string.
# Define the slide bodies, in order: title, the 8 required points (point 7 gets two slides), closing.  # Data: slides.
SLIDES = [  # One HTML string per slide.
    # Slide 0: the title slide (project, event, lane, entrant).  # Slide: title.
    """<section class="slide">
<div class="kicker">GenAI Works Open Agent Hackathon 2026 · Wildcard [Tinkerer]</div>
<h1>QuizForge Live</h1>
<p class="sub">The study agent that remembers what you missed.<br>Paste any study material — it plans a round, generates the questions, grades your answers, and adapts what comes next.</p>
<div class="meta">David Scott Cain · solo · Team HackOS<br>Built on QuizForge (v1, Build With AI: Basics, submitted Oct 23, 2026) — all Live work is new in this event window.<br>Demo video: 2 minutes · Repo: github.com/dcain2336/quizforge-live</div>
</section>""",  # End of the title slide.
    # Slide 1: required point 1 - the problem and who it is for.  # Slide: point 1.
    """<section class="slide">
<div class="kicker">1 · Problem + target users</div>
<h2>Quizzes forget the learner</h2>
<ul>
<li><strong>The problem:</strong> re-reading notes feels like studying but builds weak recall. One-shot quiz tools generate once, grade once, and adapt <em>never</em> — the learner's history evaporates between sessions.</li>
<li><strong>The scaling trap:</strong> an agent that re-reads the full history every round pays O(n²) context — planning gets slower and dumber as the learner improves.</li>
<li><strong>Target users:</strong> students and certification candidates studying from <em>their own</em> texts — our filmed demo uses a first-responder exam excerpt (scene safety, SAMPLE, OPQRST, DCAP-BTLS).</li>
<li><strong>Also:</strong> tutors and self-learners who need quizzes grounded in their material, plus an inspectable record of what the agent decided and why.</li>
</ul>
</section>""",  # End of point 1.
    # Slide 2: required point 2 - the solution.  # Slide: point 2.
    """<section class="slide">
<div class="kicker">2 · Solution</div>
<h2>A study loop, not a quiz generator</h2>
<ul>
<li><strong>QuizForge Live</strong> turns any pasted study material into a live agent loop: <strong>PLAN → GENERATE → GRADE → ADAPT</strong>, round after round.</li>
<li>Each plan is decided from a <strong>bounded learner state</strong> — mastered topics, remaining (weak) topics, strategy, difficulty — carried by the Meterless Markovian engine, never the raw history.</li>
<li>Every miss returns an <strong>evidence-backed explanation</strong> that cites the study source; missed topics resurface next round until mastered.</li>
<li>Every decision is <strong>inspectable</strong>: JSONL evidence (plan traces, grade telemetry, metered model calls) plus <code>/api/usage</code> and <code>/api/status</code> endpoints.</li>
<li>The full loop runs <strong>keyless and offline</strong>; model routes enrich it when configured — it never blocks on credentials.</li>
</ul>
</section>""",  # End of point 2.
    # Slide 3: required point 3 - the agent workflow and architecture.  # Slide: point 3.
    """<section class="slide">
<div class="kicker">3 · Agent workflow / architecture</div>
<h2>Plan → generate → grade → adapt</h2>
<div class="flow">
<div class="box"><b>PLAN</b>agent.py + markovian.py fold graded history into the canonical state block (COMPLETED / REMAINING / DECISIONS / CONTEXT), compress it to an 800-token budget, and decide focus + difficulty.</div>
<div class="arrow">→</div>
<div class="box"><b>GENERATE</b>The v1 QuizForge engine builds the round's questions from the material (LLM chain, then an offline engine that always works).</div>
<div class="arrow">→</div>
<div class="box"><b>GRADE</b>Answers graded on the spot; explain.py attaches an evidence-backed explanation, citing the study sources, to every miss.</div>
<div class="arrow">→</div>
<div class="box"><b>ADAPT</b>Missed topics land in the state's REMAINING list as telemetry — the next plan targets exactly them. Loop repeats.</div>
</div>
<p>When a model route is configured, Nemotron refines the plan — prompted with the bounded state via the engine's <code>build_prompt</code>, its reply marker-parsed and shape-validated, with the engine plan as the fallback. Metering (meterless.py) records every call and event as JSONL either way.</p>
</section>""",  # End of point 3.
    # Slide 4: required point 4 - the technical stack.  # Slide: point 4.
    """<section class="slide">
<div class="kicker">4 · Technical stack</div>
<h2>Zero dependencies, stdlib only</h2>
<ul>
<li><strong>Runtime:</strong> Python 3 standard library only — no pip installs, no build step; <code>python3 app.py</code> serves the UI and API on port 8765.</li>
<li><strong>Modules:</strong> <code>app.py</code> (HTTP API) · <code>agent.py</code> (the loop) · <code>markovian.py</code> (Meterless engine port) · <code>generator.py</code> (v1 engine) · <code>nemotron.py</code> (model routes) · <code>explain.py</code> (cited explanations) · <code>zetaris.py</code> (data-harness client) · <code>meterless.py</code> (JSONL evidence).</li>
<li><strong>Models:</strong> NVIDIA Nemotron (<code>nvidia/nemotron-3.5-super-vl:free</code>) via Nightshift locally or OpenRouter's free tier.</li>
<li><strong>Data layer:</strong> Zetaris REST — Bearer + X-Org-ID + X-Request-ID, SQL via <code>POST /sql-editor/sqls/run</code>.</li>
<li><strong>Tests:</strong> 27 deterministic offline tests (engine bounds, compression cascade, behavior change, env routing, full loop) — <code>python3 -m unittest discover -s tests</code>.</li>
</ul>
</section>""",  # End of point 4.
    # Slide 5: required point 5 - how Zetaris and Meterless were used, stated honestly.  # Slide: point 5.
    """<section class="slide">
<div class="kicker">5 · How Zetaris and Meterless were used</div>
<h2>Sponsor technology, honestly labeled</h2>
<ul>
<li><strong>Meterless — integrated and load-bearing.</strong> The Markovian engine is ported from the open-source specs (Apache-2.0) and decides every plan; the Nightshift route is implemented (OpenAI-compatible <code>/v1/chat/completions</code>) and env-gated via <code>METERLESS_BASE_URL</code> / <code>METERLESS_RUNTIME_TOKEN</code> — Nightshift is local-install software with no hosted endpoint, so it activates on a participant machine.</li>
<li><strong>Zetaris — client built, preflight-gated.</strong> The full REST layer is implemented and verified against Zetaris's own public getting-started scripts, with their <code>SELECT 1</code> preflight pattern. The organizers' participant instance is still a TBC placeholder (no URL or key issued), so until one exists the corpus runs on the offline local-corpus fallback — and <code>/api/status</code> says exactly that.</li>
<li><strong>Cursor — not used.</strong> The organizers confirmed any coding tool is allowed and included no free Cursor credits in this event; we state this rather than claim it.</li>
</ul>
</section>""",  # End of point 5.
    # Slide 6: required point 6 - what was unique about the sponsor-tech use.  # Slide: point 6.
    """<section class="slide">
<div class="kicker">6 · What was unique about the sponsor-tech use</div>
<h2>We didn't call the engine — we became it</h2>
<ul>
<li><strong>A faithful port, not a wrapper:</strong> upstream ships the Markovian engine as an implementation spec + TypeScript reference ("not a runtime library"), so <code>markovian.py</code> re-implements its core — config bounds, the <code>[STATE_CHECKPOINT]</code> marker protocol, the 4-level carryover cascade — in stdlib Python, with provenance and an honest adaptation list in the file header.</li>
<li><strong>Learner state as a Markov chain:</strong> topics transition weak → mastered by explicit rules. In the filmed session the carried state was <strong>69 tokens</strong>; the measured saving at 3 full chunks is 48,000 → 26,400 tokens (45%), growing with history — and the logs report 0 saved when a history is too small to save anything.</li>
<li><strong>Evidence as a feature:</strong> judges can replay every state transition from <code>logs/events.jsonl</code>. The demo's round-2 focus change is provable from the log, not just narrated over video.</li>
<li><strong>Honesty as design:</strong> <code>/api/status</code> exposes which sponsor pieces are live, gated, or fallback — no vaporware claims anywhere in the product.</li>
</ul>
</section>""",  # End of point 6.
    # Slide 7: required point 7, first visuals slide - the product surface and the round-1 plan.  # Slide: point 7a.
    """<section class="slide">
<div class="kicker">7 · Product visuals (1 of 2)</div>
<h2>The product, running offline</h2>
<div class="shots">
<div class="shot"><img src="shots/shot01_home.png" alt="QuizForge Live home page"><p class="cap">The app: paste any study material (or load the bundled first-responder sample). One command runs it — no installs, no keys required.</p></div>
<div class="shot"><img src="shots/shot03_round1.png" alt="Round 1 plan transcript"><p class="cap">Round 1 (live API response): the Markovian plan — focus "First Aid", easy baseline probe, state COMPLETED: none yet — with the round's questions above it.</p></div>
</div>
</section>""",  # End of point 7, first slide.
    # Slide 8: required point 7, second visuals slide - the money shot and the evidence log.  # Slide: point 7b.
    """<section class="slide">
<div class="kicker">7 · Product visuals (2 of 2)</div>
<h2>The adaptation, and its proof</h2>
<div class="shots">
<div class="shot"><img src="shots/shot05_round2.png" alt="Round 2 plan transcript"><p class="cap">Round 2's plan targets exactly the missed topics — focus: DCAP-BTLS, SAMPLE — decided from the state block: COMPLETED: Airway · REMAINING: DCAP-BTLS, SAMPLE (69 carryover tokens).</p></div>
<div class="shot"><img src="shots/shot08_events.png" alt="Evidence log"><p class="cap">The session's evidence log (logs/events.jsonl): a trace per plan, telemetry for the graded round (score 1/4, missed topics recorded) — every state transition replayable.</p></div>
</div>
</section>""",  # End of point 7, second slide.
    # Slide 9: required point 8 - future enhancements.  # Slide: point 8.
    """<section class="slide">
<div class="kicker">8 · Future enhancements</div>
<h2>Where Live goes next</h2>
<ul>
<li><strong>Live Zetaris corpus</strong> the moment a participant instance is issued: ingest a second source mid-session and watch the next round draw on it, with per-source provenance in explanations.</li>
<li><strong>Nightshift on the participant's machine</strong> (or a DGX Spark): local Nemotron planning through the already-built route; model checkpoints already parsed and kept as evidence.</li>
<li><strong>More Meterless engines:</strong> H-MEM for cross-session learner memory; Scout Intent to route across a multi-subject study library.</li>
<li><strong>Spaced repetition from the state:</strong> schedule reviews straight off the REMAINING list (v1's review plan meets the Markovian state), plus cohort/class mode and Anki export.</li>
<li><strong>A Live tab in the UI</strong> that plays rounds in the browser against the same API the demo films.</li>
</ul>
</section>""",  # End of point 8.
    # Slide 10: the closing slide - run instructions, repo, license.  # Slide: closing.
    """<section class="slide">
<div class="kicker">QuizForge Live</div>
<h2>Plan · Generate · Grade · Adapt</h2>
<p class="big">Run it: <code>python3 app.py</code> → http://localhost:8765 — the whole loop works with no keys at all.</p>
<p class="big" style="margin-top:18px;">Repo: github.com/dcain2336/quizforge-live · Tests: 27 offline, all passing · License: MIT</p>
<div class="meta">GenAI Works Open Agent Hackathon 2026 · Wildcard [Tinkerer] · David Scott Cain (solo, team HackOS)<br>Pre-existing base: QuizForge v1 (declared). New in this event: the agent loop, the Markovian engine port, the Zetaris REST layer, the Nightshift route, and the JSONL evidence trail.</div>
</section>""",  # End of the closing slide.
]  # End of the slide list.

# Start the main build: assemble the HTML, render the PDF, verify the pages.  # Function: main.
def main():  # Write slides.html, print it to PDF with Chromium, and report the page count.
    # Assemble the full HTML document: head with the shared CSS, body with every slide in order.  # Step: build the HTML.
    html = ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<title>QuizForge Live — submission deck</title>\n<style>\n" + CSS + "\n</style>\n</head>\n<body>\n" + "\n".join(SLIDES) + "\n</body>\n</html>\n")  # One document, slides in order.
    # Write the HTML beside the PDF so the deck stays editable.  # Step: write the source.
    with open(SLIDES_HTML, "w", encoding="utf-8") as handle:  # The editable deck source.
        handle.write(html)  # The complete document.
    # Open a Playwright session for the render.  # Step: start the driver.
    with sync_playwright() as pw:  # The context manager closes everything on exit.
        # Launch headless Chromium (Playwright's build).  # Step: start the browser.
        browser = pw.chromium.launch()  # The same driver the captures used.
        # Create a page at the slide size; the PDF comes from the print layout, not the screen.  # Step: open the page.
        page = browser.new_page(viewport={"width": 1280, "height": 720})  # Matches the slide geometry.
        # Load the slides from disk so the screenshot images resolve relatively.  # Step: load the deck.
        page.goto("file://" + SLIDES_HTML)  # Local file access lets the captures embed.
        # Wait until every embedded image has finished loading.  # Step: await images.
        page.wait_for_function("() => Array.from(document.images).every((img) => img.complete && img.naturalWidth > 0)")  # No broken or pending images in the PDF.
        # Print the page to the deck PDF, honoring the CSS page size and backgrounds.  # Step: render the PDF.
        page.pdf(path=DECK_PDF, prefer_css_page_size=True, print_background=True)  # 1280x720 pages, colors intact.
        # Close the browser cleanly.  # Step: shut down.
        browser.close()  # Frees the Chromium processes.
    # Verify the deck with pdfinfo and report its page count and size.  # Step: verify.
    done = subprocess.run(["pdfinfo", DECK_PDF], capture_output=True, text=True)  # Page count, size, and dimensions.
    # Print the summary lines that matter for the report.  # Step: summarize.
    for line in done.stdout.splitlines():  # pdfinfo prints one fact per line.
        if line.startswith(("Pages:", "Page size:", "File size:")):  # The three facts the report needs.
            print(line)  # Echo just those.
    # Print the deliverable path as the final line.  # Step: report.
    print("DECK:", DECK_PDF)  # The finished slide deck.

# Run main() only when this file is executed directly.  # Entry-point guard.
if __name__ == "__main__":  # Check how the file was started.
    main()  # Build the deck.

# capture.py - run the real QuizForge Live app offline and capture genuine stills of the Live loop for the demo video and deck.  # Module header: purpose of this file.
# Written 2026-10-23 for Stage 3b of the GenAI Works Open Agent Hackathon entry. Demo tooling, not part of the shipped app.  # Provenance: demo tooling.
# Honesty contract: the server runs with a scrubbed environment (no API keys), so every response below is the app's real  # Honesty: what this script guarantees.
# offline path - heuristic generation, the Meterless Markovian planner, and source-quoting fallback explanations.  # Honesty continued: no mocked data anywhere.
# Transcripts are the server's verbatim responses, pretty-printed only; the full raw payloads are saved beside them.  # Honesty continued: transcripts are real.
# Import the JSON module so API payloads and the capture metadata can be encoded and decoded.  # Library: json.
import json  # Make the json module available.
# Import the OS module so paths can be built from this file's location.  # Library: os.
import os  # Make the os module available.
# Import subprocess so the app server can be started and stopped as a child process.  # Library: subprocess.
import subprocess  # The server lifecycle is managed here.
# Import sys so the same Python interpreter can be reused for the server process.  # Library: sys.
import sys  # sys.executable points at this Python.
# Import time so the server startup can be polled with small sleeps.  # Library: time.
import time  # Used only for the health-check poll.
# Import urllib.request so the API flow can be driven with the standard library only.  # Library: urllib.request.
import urllib.request  # POST and GET helpers below are built on it.
# Import the synchronous Playwright API, our browser driver for the screenshots.  # Library: playwright.
from playwright.sync_api import sync_playwright  # The sync API keeps the shot sequence readable top to bottom.
# Define the folder this script lives in (the demo folder).  # Constant: demo folder.
HERE = os.path.dirname(os.path.abspath(__file__))  # Absolute path of demo/.
# Define the project root (one level up from demo/).  # Constant: project root.
PROJECT = os.path.dirname(HERE)  # app.py and the modules live here.
# Define the folder that will hold the screenshots.  # Constant: shots folder.
SHOTS = os.path.join(HERE, "shots")  # Stills go in demo/shots/.
# Define the folder that will hold the session transcripts.  # Constant: transcripts folder.
TRANSCRIPTS = os.path.join(HERE, "transcripts")  # Human-readable verbatim transcripts go in demo/transcripts/.
# Define the folder that will hold the raw JSON payloads.  # Constant: raw folder.
RAW = os.path.join(TRANSCRIPTS, "raw")  # Unmodified server responses go in demo/transcripts/raw/.
# Define the local base URL of the running app.  # Constant: app URL.
APP_URL = "http://127.0.0.1:8765"  # app.py's default port, via the numeric loopback (strict Chromium builds treat the name "localhost" more strictly).
# Define the path of the bundled demo study text the flow runs on.  # Constant: sample path.
SAMPLE_PATH = os.path.join(PROJECT, "sample_data", "first-responder-sample.txt")  # The same file the /sample route serves.
# Define the session topic label used for both rounds.  # Constant: topic.
TOPIC = "First Aid"  # Matches the Stage 3a wire smoke, so the plan reads the same way.
# Define the number of questions requested per round.  # Constant: round size.
COUNT = 4  # Four questions keep the transcripts short enough to frame on screen.
# Define the environment the server child process gets: PATH and PORT only, deliberately no API keys.  # Constant: server env.
SERVER_ENV = {"PATH": os.environ.get("PATH", ""), "PORT": "8765", "LANG": "C.UTF-8"}  # No OPENROUTER/GROQ/METERLESS/ZETARIS variables: the offline path is forced and labeled by the app itself.
# Create the output folders if they do not exist yet.  # Step: prepare folders.
for folder in (SHOTS, TRANSCRIPTS, RAW):  # Walk the three output folders.
    os.makedirs(folder, exist_ok=True)  # Safe to re-run.

# Start the helper that performs one HTTP GET and returns the decoded JSON body.  # Function: get_json.
def get_json(path):  # Fetch a JSON endpoint from the running app.
    # Open the URL and read the whole response body.  # Step: request.
    with urllib.request.urlopen(APP_URL + path, timeout=30) as response:  # The app answers on loopback.
        return json.loads(response.read().decode("utf-8"))  # Decode the JSON payload.

# Start the helper that performs one HTTP POST with a JSON body and returns the decoded JSON reply.  # Function: post_json.
def post_json(path, payload):  # Send one JSON payload to an app endpoint.
    # Encode the payload as UTF-8 JSON bytes.  # Step: encode.
    body = json.dumps(payload).encode("utf-8")  # The wire format the API expects.
    # Build the POST request with the JSON content type.  # Step: build request.
    request = urllib.request.Request(APP_URL + path, data=body, headers={"Content-Type": "application/json"}, method="POST")  # One explicit request object.
    # Send it and read the whole response body.  # Step: send.
    with urllib.request.urlopen(request, timeout=60) as response:  # Generation can take a moment even offline.
        return json.loads(response.read().decode("utf-8"))  # Decode the JSON reply.

# Start the helper that waits until the app's health endpoint answers.  # Function: wait_for_server.
def wait_for_server():  # Poll /health until the child server is up.
    # Try for up to fifteen seconds before giving up.  # Step: poll loop.
    for _ in range(75):  # 75 tries at 0.2 s is a 15 s budget.
        # Attempt one health probe, tolerating connection errors while the server boots.  # Step: probe.
        try:  # The first probes usually fail because nothing listens yet.
            get_json("/health")  # A 200 here means the server is ready.
            return  # Ready: stop polling.
        except Exception:  # Any connection problem just means "not yet".
            time.sleep(0.2)  # Wait a beat and try again.
    # Raise if the server never came up, so the failure is loud and precise.  # Step: give up loudly.
    raise RuntimeError("app.py did not answer /health within 15 seconds")  # The server log in demo/server.log explains why.

# Start the helper that saves one raw payload exactly as the server sent it.  # Function: save_raw.
def save_raw(name, payload):  # Persist one unmodified response for the record.
    # Write the payload as compact JSON, byte-faithful to the decoded response.  # Step: write raw.
    with open(os.path.join(RAW, name), "w", encoding="utf-8") as handle:  # One file per API step.
        json.dump(payload, handle)  # No indent: the record copy, not the screen copy.

# Start the helper that writes one screen transcript: a labeled header plus the pretty-printed response.  # Function: save_transcript.
def save_transcript(name, header_lines, payload):  # Build one transcript text file for screenshotting.
    # Join the header lines into the transcript's title block.  # Step: header.
    text = "\n".join(header_lines) + "\n" + ("-" * 100) + "\n"  # A ruled line separates the label from the payload.
    # Append the response, pretty-printed with a two-space indent (formatting only; content untouched).  # Step: payload.
    text += json.dumps(payload, indent=2) + "\n"  # The server's own keys, values, and order.
    # Write the transcript to disk.  # Step: write transcript.
    with open(os.path.join(TRANSCRIPTS, name), "w", encoding="utf-8") as handle:  # One file per filmed step.
        handle.write(text)  # The exact text the browser will render.
    # Return the path so the screenshot step can open it.  # Step: hand back path.
    return os.path.join(TRANSCRIPTS, name)  # file:// target for Chromium's native text view.

# Start the helper that picks the learner's answers for round 1: miss every question on the two target topics, pass the rest.  # Function: choose_answers.
def choose_answers(questions):  # Decide the scripted answers from the real generated questions.
    # Collect the distinct topics in the order the questions present them.  # Step: list topics.
    distinct = []  # Topic labels, first-appearance order.
    # Walk the questions once to gather the topic order.  # Loop: questions.
    for question in questions:  # Each generated question carries its topic.
        # Add a topic the first time it appears.  # Step: dedupe.
        if question.get("topic") not in distinct:  # First sighting of this topic.
            distinct.append(question.get("topic"))  # Remember it.
    # The deliberate misses target the first two distinct topics (fewer if the round has fewer).  # Step: pick targets.
    targets = distinct[:2]  # These topics must end up as round 2's focus, verbatim.
    # Build the answer list in question order.  # Step: build answers.
    answers = []  # One answer string per question, matching /api/grade's contract.
    # Walk the questions and choose each answer.  # Loop: questions.
    for question in questions:  # The grader compares each answer to the question's "answer" text.
        # Miss deliberately when this question's topic is a target topic.  # Branch: deliberate miss.
        if question.get("topic") in targets:  # Every question on a target topic is missed, so the topic stays unmastered.
            # Multiple-choice misses pick the option after the correct one (wrapping), which is never the key.  # Branch: miss an MCQ.
            if question.get("type") == "mcq":  # The radio-style question shape.
                wrong = question["options"][(question["answer_index"] + 1) % len(question["options"])]  # A real option, definitely wrong.
                answers.append(wrong)  # Record the wrong option's text.
            else:  # Short-answer questions are missed with an honest non-answer.
                answers.append("I don't know")  # Never accidentally matches the key.
        else:  # Every other question is answered correctly with the key text itself.
            answers.append(question["answer"])  # The exact expected answer.
    # Return the targets and the answers together.  # Step: hand back.
    return targets, answers  # The capture metadata records both.

# Start the helper that sets the page render scale for one shot, with a CSS-zoom fallback.  # Function: set_scale.
def set_scale(page, cdp, factor):  # Scale the rendered page so small JSON text stays legible at 720p.
    # Try the CDP page-scale emulation first: it scales the whole rendering, viewers included.  # Step: CDP scale.
    try:  # The emulation command exists on Chromium builds.
        cdp.send("Emulation.setPageScaleFactor", {"pageScaleFactor": factor})  # One multiplier for this page.
        return  # Scaled: nothing else to do.
    except Exception:  # Older or restricted builds may refuse the command.
        pass  # Fall through to the CSS approach.
    # Fall back to CSS zoom on the document element, ignoring failures on viewer pages.  # Step: CSS zoom fallback.
    try:  # Some internal viewer pages reject script styling.
        page.evaluate("(f) => { document.documentElement.style.zoom = f; }", factor)  # Zoom the whole document.
    except Exception:  # A rejected zoom is not fatal: the shot is still genuine, just smaller.
        pass  # Legibility is checked by eye from the saved stills.

# Start the helper that screenshots a transcript file, scrolled so a chosen anchor string is in frame.  # Function: shot_transcript.
def shot_transcript(page, cdp, path, anchor, filename):  # Render one transcript in Chromium's native text view and frame the anchor.
    # Open the transcript as a local file: Chromium renders plain text natively, with no custom markup from us.  # Step: open the file.
    page.goto("file://" + path)  # The browser's own text rendering is the presentation.
    # Enlarge the text so it survives the downscale to 720p in the video.  # Step: scale up.
    set_scale(page, cdp, 1.6)  # 1.6x keeps long JSON lines mostly in frame.
    # Scroll the anchor into view using the browser's own find, when an anchor was given.  # Step: frame the anchor.
    if anchor:  # Some transcripts are short enough to frame from the top.
        page.evaluate("(a) => window.find(a)", anchor)  # Chromium selects and scrolls to the first match.
    # Give the browser a beat to paint the final frame.  # Step: settle.
    page.wait_for_timeout(400)  # Static text paints fast.
    # Save the viewport as a PNG named for this shot.  # Step: capture.
    page.screenshot(path=os.path.join(SHOTS, filename))  # 2560x1440 pixels because deviceScaleFactor is 2.

# Start the main capture routine: run the flow once against the live server, then photograph every stage.  # Function: main.
def main():  # One honest pass: API flow first (it writes the evidence logs), then the browser stills.
    # Open the server log file so the child process's output survives for diagnosis.  # Step: server log.
    server_log = open(os.path.join(HERE, "server.log"), "w", encoding="utf-8")  # Truncated each run.
    # Start the real app with the scrubbed environment on its default port.  # Step: start the server.
    server = subprocess.Popen([sys.executable, os.path.join(PROJECT, "app.py")], cwd=PROJECT, env=SERVER_ENV, stdout=server_log, stderr=subprocess.STDOUT)  # app.py serves until terminated.
    # Guard everything below so the server is always shut down, even on failure.  # Step: guarded capture.
    try:  # The flow and the photography happen inside this block.
        # Wait until the app answers its health endpoint.  # Step: await readiness.
        wait_for_server()  # Raises loudly if the app never boots.
        # Read the bundled sample study text from disk (the same bytes the /sample route serves).  # Step: load the material.
        with open(SAMPLE_PATH, encoding="utf-8") as handle:  # The demo material file.
            study_text = handle.read()  # The learner's pasted material for both rounds.
        # Run round 1: plan plus questions, with no graded history.  # Step: round 1.
        round1 = post_json("/api/round", {"text": study_text, "topic": TOPIC, "history": [], "count": COUNT})  # The Live loop's first turn.
        save_raw("step3_round1.json", round1)  # Keep the unmodified response.
        # Choose the scripted answers: deliberate misses on the first two distinct topics.  # Step: choose answers.
        targets, answers = choose_answers(round1["questions"])  # Targets must resurface as round 2's focus.
        # Grade round 1 with no extra sources, so explanations fall back to quoting each question's source sentence.  # Step: grade.
        grade = post_json("/api/grade", {"questions": round1["questions"], "answers": answers, "topic": TOPIC, "sources": []})  # Score plus cited explanations.
        save_raw("step4_grade.json", grade)  # Keep the unmodified response.
        # Fold the graded results into the history shape the planner consumes (one topic/correct item per answer).  # Step: build history.
        history = [{"topic": item["topic"], "correct": item["correct"]} for item in grade["results"]]  # The observation the Markovian state folds in.
        # Run round 2 with the graded history: its plan is the money shot.  # Step: round 2.
        round2 = post_json("/api/round", {"text": study_text, "topic": TOPIC, "history": history, "count": COUNT})  # The adaptive second turn.
        save_raw("step5_round2.json", round2)  # Keep the unmodified response.
        # Fetch the usage snapshot and the status panel from the same live process.  # Step: evidence endpoints.
        usage = get_json("/api/usage")  # Metered counts plus the JSONL evidence inventory.
        status = get_json("/api/status")  # Integration health, honestly labeled.
        save_raw("step6_usage.json", usage)  # Keep the unmodified response.
        save_raw("step7_status.json", status)  # Keep the unmodified response.
        # Write the three filmed transcripts with labeled headers.  # Step: transcripts.
        t_round1 = save_transcript("step3_round1.txt", ["QUIZFORGE LIVE - LIVE CAPTURE TRANSCRIPT", "Step 3 - POST /api/round (round 1: topic \"" + TOPIC + "\", no history, " + str(COUNT) + " questions)", "Offline engine run: heuristic generation + Meterless Markovian plan (no API keys in environment)"], round1)  # Round 1's full response.
        t_grade = save_transcript("step4_grade.txt", ["QUIZFORGE LIVE - LIVE CAPTURE TRANSCRIPT", "Step 4 - POST /api/grade (round 1 answers: deliberate misses on " + ", ".join(targets) + "; all other answers correct)", "Every miss carries an explanation quoting the study source, produced by the app's offline fallback (engine: fallback)"], grade)  # The grading package.
        t_round2 = save_transcript("step5_round2.txt", ["QUIZFORGE LIVE - LIVE CAPTURE TRANSCRIPT", "Step 5 - POST /api/round (round 2: same material, history = round 1's graded results)", "The plan block below is the money shot: its focus list must equal round 1's missed topics"], round2)  # Round 2's full response.
        # Write the usage and status transcripts too: Chromium's raw JSON view overflows the frame (single unchecked lines),  # Step: JSON-view transcripts.
        # so these two endpoints are filmed in the same labeled transcript style as steps 3-5 (see recapture_json.py).  # Step continued: consistent framing.
        t_usage = save_transcript("step6_usage.txt", ["QUIZFORGE LIVE - LIVE CAPTURE TRANSCRIPT", "Step 6 - GET /api/usage (metered model-call counts + JSONL evidence inventory)", "Offline run: no model calls were made, so the counts are empty and the inventory is the story"], usage)  # The usage payload.
        t_status = save_transcript("step7_status.txt", ["QUIZFORGE LIVE - LIVE CAPTURE TRANSCRIPT", "Step 7 - GET /api/status (integration health, exactly as the app reports it)", "Offline run: Nemotron route unset, Zetaris unconfigured (organizers' instance still TBC), Markovian engine active"], status)  # The status payload.
        # Read back the evidence log the session just wrote, for the deck's evidence still.  # Step: read the events log.
        events_path = os.path.join(PROJECT, "logs", "events.jsonl")  # meterless writes beside the modules.
        # Copy the events log into a transcript file so the browser can render it as text.  # Step: events transcript.
        with open(events_path, encoding="utf-8") as handle:  # The session's trace and telemetry lines.
            events_text = handle.read()  # Verbatim JSONL, one event per line.
        # Prepend a label so the still explains what the file is.  # Step: label the events.
        t_events = os.path.join(TRANSCRIPTS, "step8_events.txt")  # The events transcript path.
        with open(t_events, "w", encoding="utf-8") as handle:  # Write the labeled copy.
            handle.write("QUIZFORGE LIVE - EVIDENCE LOG (logs/events.jsonl, written by this session)\n" + ("-" * 100) + "\n" + events_text)  # Label plus verbatim lines.
        # Record the capture metadata: what actually happened, for narration, the deck, and the report.  # Step: metadata.
        meta = {"round1_plan": round1["plan"], "round1_source": round1["source"], "question_topics": [q.get("topic") for q in round1["questions"]], "targets_missed": targets, "answers_given": answers, "grade_score": grade["score"], "grade_total": grade["total"], "missed_topics": grade["missed_topics"], "round2_focus": round2["plan"]["focus_areas"], "round2_plan": round2["plan"], "focus_matches_missed": sorted(round2["plan"]["focus_areas"]) == sorted(grade["missed_topics"]), "usage": usage, "status": status}  # Every fact the narration is allowed to state.
        # Save the metadata beside the shots.  # Step: persist metadata.
        with open(os.path.join(SHOTS, "capture_meta.json"), "w", encoding="utf-8") as handle:  # The narration and deck read this.
            json.dump(meta, handle, indent=2)  # Pretty JSON for human checking.
        # Open a Playwright session for the stills.  # Step: start the driver.
        with sync_playwright() as pw:  # The context manager closes everything on exit.
            # Launch headless Chromium (Playwright's build, which does not block loopback navigation).  # Step: start the browser.
            browser = pw.chromium.launch()  # The same driver the v1 demo used.
            # Create a page sized like a 720p video frame, doubled for crisp stills.  # Step: size the page.
            page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)  # 1280x720 CSS pixels, 2560x1440 image pixels.
            # Open a CDP session for the page-scale emulation used on the text and JSON shots.  # Step: CDP session.
            cdp = page.context.new_cdp_session(page)  # One session reused for every scaled shot.
            # Load the app's home page at natural scale.  # Step: open the app.
            page.goto(APP_URL)  # The server is still running from the flow above.
            # Wait until the paste box is really on screen, then let the page settle.  # Step: confirm load.
            page.wait_for_selector("#material")  # The textarea is the first thing a user sees.
            page.wait_for_timeout(800)  # Fonts and layout finish painting.
            # Shot 1: the untouched home page (intro and closing frame).  # Shot: home.
            page.screenshot(path=os.path.join(SHOTS, "shot01_home.png"))  # Full viewport at scroll position zero.
            # Click the sample loader, exactly as a user would.  # Step: load the demo material.
            page.click("#sampleBtn")  # Fetches the first-responder excerpt into the textarea.
            # Wait until the textarea actually holds the sample text.  # Step: confirm the load.
            page.wait_for_function("() => document.getElementById('material').value.length > 500")  # The sample is ~2,300 characters.
            # Shot 2: the sample material sitting in the textarea.  # Shot: sample loaded.
            page.screenshot(path=os.path.join(SHOTS, "shot02_sample.png"))  # Same framing as shot 1, now filled.
            # Shot 3: the round 1 transcript, framed on the plan block.  # Shot: round 1.
            shot_transcript(page, cdp, t_round1, '"focus_areas"', "shot03_round1.png")  # The plan is the story of this beat.
            # Shot 4: the grade transcript, framed on the first fallback explanation.  # Shot: grade.
            shot_transcript(page, cdp, t_grade, '"engine": "fallback"', "shot04_grade.png")  # That anchor sits at the end of the first miss's cited explanation.
            # Shot 5: the round 2 transcript, framed on the plan block (the money shot).  # Shot: round 2.
            shot_transcript(page, cdp, t_round2, '"focus_areas"', "shot05_round2.png")  # Focus must equal the missed topics.
            # Shot 6: the usage transcript, framed on the evidence entry that exists.  # Shot: usage.
            shot_transcript(page, cdp, t_usage, '"exists": true', "shot06_usage.png")  # That flag marks the events.jsonl inventory line.
            # Shot 7: the status transcript, framed on the Markovian engine block.  # Shot: status.
            shot_transcript(page, cdp, t_status, '"markovian_engine"', "shot07_status.png")  # The engine block sits mid-payload.
            # Shot 8 (deck only): the session's evidence log rendered as text.  # Shot: events.
            shot_transcript(page, cdp, t_events, None, "shot08_events.png")  # No anchor: the file is short enough from the top at a smaller scale.
            # Close the browser cleanly.  # Step: shut down the browser.
            browser.close()  # Frees the Chromium processes.
        # Print the key facts so the run log shows what was actually filmed.  # Step: report.
        print("ROUND1 plan engine:", round1["plan"].get("engine"), "| focus:", round1["plan"].get("focus_areas"), "| source:", round1["source"])  # The opening plan.
        print("TARGETS missed:", targets, "| grade:", grade["score"], "/", grade["total"], "| missed_topics:", grade["missed_topics"])  # The scripted outcome.
        print("ROUND2 focus:", round2["plan"].get("focus_areas"), "| focus == missed:", meta["focus_matches_missed"])  # The money-shot check.
    # Whatever happens above, the server child process must not outlive this script.  # Step: guaranteed shutdown.
    finally:  # Runs on success and on failure alike.
        server.terminate()  # Ask the app to stop.
        # Wait briefly for a clean exit, then force it if needed.  # Step: reap the server.
        try:  # A well-behaved server exits at once.
            server.wait(timeout=5)  # Five seconds is generous for a stdlib server.
        except subprocess.TimeoutExpired:  # It ignored the polite request.
            server.kill()  # Force-stop so the port is freed.
        server_log.close()  # Flush and release the log file.

# Run main() only when this file is executed directly.  # Entry-point guard.
if __name__ == "__main__":  # Check how the file was started.
    main()  # Start the capture.

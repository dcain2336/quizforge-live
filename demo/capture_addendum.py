# capture_addendum.py - film the Stage 3c browser Live tab: a genuine UI session for the demo addendum.  # Module header: purpose of this file.
# Written 2026-10-23 for Stage 3d of the GenAI Works Open Agent Hackathon entry. Demo tooling, not part of the shipped app.  # Provenance: demo tooling.
# Honesty contract: same discipline as capture.py - the real app.py runs with a scrubbed environment (no API keys),  # Honesty: what this script guarantees.
# and every beat is driven through the shipped UI (tab, buttons, radios, text fields), never by calling the API directly.  # Honesty continued: the browser is the driver.
# The /api/round and /api/grade responses are intercepted off the wire only to record verbatim metadata for narration.  # Honesty continued: interception is read-only.
# Import the JSON module so intercepted payloads and the capture metadata can be encoded and decoded.  # Library: json.
import json  # Make the json module available.
# Import the OS module so paths can be built from this file's location.  # Library: os.
import os  # Make the os module available.
# Import subprocess so the app server can be started and stopped as a child process.  # Library: subprocess.
import subprocess  # The server lifecycle is managed here.
# Import sys so the same Python interpreter can be reused for the server process.  # Library: sys.
import sys  # sys.executable points at this Python.
# Import time so the server startup can be polled with small sleeps.  # Library: time.
import time  # Used only for the health-check poll.
# Import urllib.request so the health probe can use the standard library only.  # Library: urllib.request.
import urllib.request  # Only the /health probe uses it.
# Import the synchronous Playwright API, our browser driver for the session and screenshots.  # Library: playwright.
from playwright.sync_api import sync_playwright  # The sync API keeps the shot sequence readable top to bottom.
# Define the folder this script lives in (the demo folder).  # Constant: demo folder.
HERE = os.path.dirname(os.path.abspath(__file__))  # Absolute path of demo/.
# Define the project root (one level up from demo/).  # Constant: project root.
PROJECT = os.path.dirname(HERE)  # app.py and the modules live here.
# Define the folder that will hold the screenshots.  # Constant: shots folder.
SHOTS = os.path.join(HERE, "shots")  # Stills go in demo/shots/, beside the Stage 3b shots.
# Define the local base URL of the running app.  # Constant: app URL.
APP_URL = "http://127.0.0.1:8765"  # app.py's default port, via the numeric loopback (same choice as capture.py).
# Define the environment the server child process gets: PATH and PORT only, deliberately no API keys.  # Constant: server env.
SERVER_ENV = {"PATH": os.environ.get("PATH", ""), "PORT": "8765", "LANG": "C.UTF-8"}  # The offline path is forced, and the UI's own banner labels it.
# Define the round size the filming uses (four questions, matching the Stage 3b film).  # Constant: round size.
COUNT = "4"  # The Live count dropdown's value for a four-question round.

# Start the helper that waits until the app's health endpoint answers.  # Function: wait_for_server.
def wait_for_server():  # Poll /health until the child server is up.
    # Try for up to fifteen seconds before giving up.  # Step: poll loop.
    for _ in range(75):  # 75 tries at 0.2 s is a 15 s budget.
        # Attempt one health probe, tolerating connection errors while the server boots.  # Step: probe.
        try:  # The first probes usually fail because nothing listens yet.
            with urllib.request.urlopen(APP_URL + "/health", timeout=2) as response:  # A 200 here means the server is ready.
                response.read()  # Drain the body so the connection closes cleanly.
            return  # Ready: stop polling.
        except Exception:  # Any connection problem just means "not yet".
            time.sleep(0.2)  # Wait a beat and try again.
    # Raise if the server never came up, so the failure is loud and precise.  # Step: give up loudly.
    raise RuntimeError("app.py did not answer /health within 15 seconds")  # The server log in demo/server_addendum.log explains why.

# Start the helper that picks the learner's answers: miss every question on the first two distinct topics, pass the rest.  # Function: choose_answers.
def choose_answers(questions):  # Decide the scripted answers from the real questions the UI was dealt.
    # Collect the distinct topics in the order the questions present them.  # Step: list topics.
    distinct = []  # Topic labels, first-appearance order.
    # Walk the questions once to gather the topic order.  # Loop: questions.
    for question in questions:  # Each dealt question carries its topic.
        # Add a topic the first time it appears.  # Step: dedupe.
        if question.get("topic") not in distinct:  # First sighting of this topic.
            distinct.append(question.get("topic"))  # Remember it.
    # The deliberate misses target the first two distinct topics (fewer if the round has fewer).  # Step: pick targets.
    targets = distinct[:2]  # These topics must end up as round 2's focus, verbatim.
    # Build the answer plan in question order: (kind, value) per question.  # Step: build the plan.
    plan = []  # kind "mcq" carries the option index to click; kind "text" carries the string to type.
    # Walk the questions and choose each answer.  # Loop: questions.
    for question in questions:  # The grader compares each answer to the question's "answer" text.
        # Miss deliberately when this question's topic is a target topic.  # Branch: deliberate miss.
        if question.get("topic") in targets:  # Every question on a target topic is missed, so the topic stays unmastered.
            # Multiple-choice misses pick the option after the correct one (wrapping), which is never the key.  # Branch: miss an MCQ.
            if question.get("type") == "mcq":  # The radio-style question shape.
                plan.append(("mcq", (question["answer_index"] + 1) % len(question["options"])))  # A real option, definitely wrong.
            else:  # Short-answer questions are missed with an honest non-answer.
                plan.append(("text", "I don't know"))  # Never accidentally matches the key.
        else:  # Every other question is answered correctly.
            # Multiple-choice passes click the key's own radio.  # Branch: pass an MCQ.
            if question.get("type") == "mcq":  # The radio-style question shape.
                plan.append(("mcq", question["answer_index"]))  # The correct option.
            else:  # Short-answer passes type the key text itself.
                plan.append(("text", question["answer"]))  # The exact expected answer.
    # Return the targets and the answer plan together.  # Step: hand back.
    return targets, plan  # The capture metadata records both.

# Start the main capture routine: one genuine UI session, screenshotted at each beat.  # Function: main.
def main():  # Drive the Live tab exactly as a learner would, then photograph every stage.
    # Open the server log file so the child process's output survives for diagnosis.  # Step: server log.
    server_log = open(os.path.join(HERE, "server_addendum.log"), "w", encoding="utf-8")  # Separate from capture.py's log.
    # Start the real app with the scrubbed environment on its default port.  # Step: start the server.
    server = subprocess.Popen([sys.executable, os.path.join(PROJECT, "app.py")], cwd=PROJECT, env=SERVER_ENV, stdout=server_log, stderr=subprocess.STDOUT)  # app.py serves until terminated.
    # Guard everything below so the server is always shut down, even on failure.  # Step: guarded capture.
    try:  # The session and the photography happen inside this block.
        # Wait until the app answers its health endpoint.  # Step: await readiness.
        wait_for_server()  # Raises loudly if the app never boots.
        # Hold the wire payloads the UI actually receives, keyed by endpoint, for the narration metadata.  # State: wire log.
        wire = {"round": [], "grade": []}  # Verbatim /api/round and /api/grade responses, in arrival order.
        # Open a Playwright session for the filming.  # Step: start the driver.
        with sync_playwright() as pw:  # The context manager closes everything on exit.
            # Launch headless Chromium (Playwright's build).  # Step: start the browser.
            browser = pw.chromium.launch()  # The same driver the Stage 3b captures used.
            # Create a page sized like a 720p video frame, doubled for crisp stills.  # Step: size the page.
            page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)  # 1280x720 CSS pixels, 2560x1440 image pixels.
            # Define the response tap: record the JSON of the two loop endpoints, ignore everything else.  # Nested function: on_response.
            def on_response(response):  # Playwright calls this for every response the page receives.
                # Only the loop endpoints carry narration facts.  # Step: filter.
                if "/api/round" in response.url or "/api/grade" in response.url:  # One of the two endpoints we film.
                    # Parse the body defensively: a failed parse must not break the filming.  # Step: parse.
                    try:  # The bodies are JSON by contract.
                        payload = response.json()  # The verbatim payload the UI consumed.
                    except Exception:  # A non-JSON error body is not narration material.
                        return  # Skip it.
                    # File the payload under its endpoint, in arrival order.  # Step: record.
                    wire["round" if "/api/round" in response.url else "grade"].append(payload)  # Round 1, grade, round 2.
            # Attach the tap before any navigation, so no response is missed.  # Step: wire the tap.
            page.on("response", on_response)  # Read-only observation; the session is untouched.
            # Load the app's home page.  # Step: open the app.
            page.goto(APP_URL)  # The server is running from the step above.
            # Wait until the v1 paste box is on screen (the page's own readiness signal).  # Step: confirm load.
            page.wait_for_selector("#material")  # The textarea is the first thing a user sees.
            # Switch to the Live tab, exactly as a user would.  # Step: open the Live pane.
            page.click("#tabLiveBtn")  # The Stage 3c tab button.
            # Wait until the honesty banner names the real route (it starts as a "Checking..." placeholder).  # Step: await the banner.
            page.wait_for_function("() => !document.getElementById('liveMode').textContent.includes('Checking')")  # The banner is filled from /api/status.
            # Load the bundled sample into the Live pane.  # Step: load the demo material.
            page.click("#liveSampleBtn")  # Fetches the first-responder excerpt into the Live textarea.
            # Wait until the Live textarea actually holds the sample text.  # Step: confirm the load.
            page.wait_for_function("() => document.getElementById('liveMaterial').value.length > 500")  # The sample is ~2,300 characters.
            # Set the round size to four questions, matching the Stage 3b film.  # Step: set the count.
            page.select_option("#liveCountSel", COUNT)  # The dropdown's "4" option.
            # Let the pane settle before the first still.  # Step: settle.
            page.wait_for_timeout(600)  # Layout and fonts finish painting.
            # Shot 9: the Live tab setup - banner, explainer, loaded sample, controls.  # Shot: Live setup.
            page.screenshot(path=os.path.join(SHOTS, "shot09_live_setup.png"))  # Full viewport at scroll position zero.
            # Start round 1 through the UI's own button.  # Step: deal round 1.
            page.click("#liveStartBtn")  # POSTs /api/round with an empty history.
            # Wait until the round card is revealed and its questions are rendered.  # Step: await round 1.
            page.wait_for_function("() => !document.getElementById('liveRoundCard').classList.contains('hidden') && document.querySelectorAll('#liveQuestions .question').length > 0")  # The deal is complete.
            # Wait for the status line to confirm the round, then let the smooth scroll settle.  # Step: settle on round 1.
            page.wait_for_function("() => document.getElementById('liveStatus').textContent.includes('Round 1 is live')")  # The UI's own confirmation.
            page.wait_for_timeout(1200)  # The card scrolls itself into view smoothly; give it time to land.
            # Shot 10: round 1 in the browser - plan, visible Markovian state, and the questions.  # Shot: Live round 1.
            page.screenshot(path=os.path.join(SHOTS, "shot10_live_round1.png"))  # The round card tops the viewport after its scroll.
            # Read the dealt questions out of the page's own session state (the same objects the UI renders).  # Step: read the questions.
            questions = page.evaluate("() => liveQuestions")  # Includes each question's key, for choosing answers.
            # Choose the scripted answers: deliberate misses on the first two distinct topics.  # Step: choose answers.
            targets, plan = choose_answers(questions)  # Targets must resurface as round 2's focus.
            # Apply the answer plan through the real form controls.  # Loop: apply answers.
            for idx, (kind, value) in enumerate(plan):  # One plan entry per question, in order.
                # Multiple-choice answers click the chosen option's radio.  # Branch: answer an MCQ.
                if kind == "mcq":  # The radio-style question shape.
                    page.check(f"input[name='lq{idx}'][value='{value}']")  # The exact radio a learner would pick.
                else:  # Short-answer questions are typed into their field.
                    page.fill(f"#live-short-{idx}", value)  # The exact field a learner would type in.
            # Grade the round through the UI's own button.  # Step: grade round 1.
            page.click("#liveGradeBtn")  # POSTs /api/grade with the collected answers.
            # Wait until the results card is revealed and its score line is filled.  # Step: await grading.
            page.wait_for_function("() => !document.getElementById('liveResultsCard').classList.contains('hidden') && document.getElementById('liveScore').textContent.length > 0")  # The verdicts are rendered.
            # Let the results card's smooth scroll settle before the still.  # Step: settle on results.
            page.wait_for_timeout(1200)  # The card scrolls itself into view smoothly.
            # Shot 11: the graded round - score, verdicts with cited explanations, missed-topic pills.  # Shot: Live grade.
            page.screenshot(path=os.path.join(SHOTS, "shot11_live_grade.png"))  # The results card tops the viewport after its scroll.
            # Plan the next round through the UI's own button: the money shot.  # Step: deal round 2.
            page.click("#liveNextBtn")  # POSTs /api/round with the folded graded history.
            # Wait until the round card shows round 2's plan and the status line confirms it.  # Step: await round 2.
            page.wait_for_function("() => document.getElementById('liveRoundTitle').textContent === 'Round 2' && document.getElementById('liveStatus').textContent.includes('Round 2 is live')")  # The adaptive deal is complete.
            # Let the round card's smooth scroll settle before the still.  # Step: settle on round 2.
            page.wait_for_timeout(1200)  # The card scrolls itself into view smoothly.
            # Shot 12: round 2 in the browser - focus pills on the missed topics, COMPLETED / REMAINING state.  # Shot: Live round 2.
            page.screenshot(path=os.path.join(SHOTS, "shot12_live_round2.png"))  # The money shot, in the UI this time.
            # Close the browser cleanly.  # Step: shut down the browser.
            browser.close()  # Frees the Chromium processes.
        # Pull the three wire payloads the session produced, in order.  # Step: unpack the wire log.
        round1, round2 = wire["round"][0], wire["round"][1]  # The two plans the UI consumed.
        grade = wire["grade"][0]  # The one grading package the UI consumed.
        # Record the capture metadata: what actually happened, for narration and the report.  # Step: metadata.
        meta = {"round1_plan": round1["plan"], "round1_source": round1["source"], "question_topics": [q.get("topic") for q in round1["questions"]], "targets_missed": targets, "grade_score": grade["score"], "grade_total": grade["total"], "missed_topics": grade["missed_topics"], "round2_focus": round2["plan"]["focus_areas"], "round2_plan": round2["plan"], "focus_matches_missed": sorted(round2["plan"]["focus_areas"]) == sorted(grade["missed_topics"])}  # Every fact the narration is allowed to state.
        # Save the metadata beside the shots.  # Step: persist metadata.
        with open(os.path.join(SHOTS, "addendum_meta.json"), "w", encoding="utf-8") as handle:  # The narration and the report read this.
            json.dump(meta, handle, indent=2)  # Pretty JSON for human checking.
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

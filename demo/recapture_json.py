# recapture_json.py - re-shoot the usage + status stills as labeled transcripts after the browser JSON viewer proved unframeable.  # Module header: purpose of this file.
# Written 2026-10-23 for Stage 3b: the first pass screenshotted Chromium's raw JSON view (single overflowing lines, mostly  # Provenance: why this exists.
# blank frame), and the viewer's Pretty-print checkbox is not reachable by the automation driver, so these two endpoints  # Provenance continued: the framing failure, precisely.
# are presented exactly like steps 3-5 - verbatim responses, pretty-printed, rendered in Chromium's native text view.  # Provenance continued: the consistent fix.
# The payloads are fetched live from a fresh server process in this run; the evidence inventory is read from the on-disk  # Honesty: the data is live-fetched and identical.
# JSONL files the filmed session wrote (3 events), and plain GETs write no new events, so the values match the film.  # Honesty continued: GETs are read-only here.
# Import the JSON module so API payloads can be decoded and pretty-printed.  # Library: json.
import json  # Make the json module available.
# Import the OS module so paths can be built from this file's location.  # Library: os.
import os  # Make the os module available.
# Import subprocess so the app server can be started and stopped as a child process.  # Library: subprocess.
import subprocess  # The server lifecycle is managed here.
# Import sys so the same Python interpreter can be reused for the server process.  # Library: sys.
import sys  # sys.executable points at this Python.
# Import time so the server startup can be polled with small sleeps.  # Library: time.
import time  # Used only for the health-check poll.
# Import urllib.request so the endpoints can be fetched with the standard library only.  # Library: urllib.request.
import urllib.request  # The GET helper below is built on it.
# Import the synchronous Playwright API, our browser driver for the screenshots.  # Library: playwright.
from playwright.sync_api import sync_playwright  # The sync API keeps the shot sequence readable top to bottom.
# Define the folder this script lives in (the demo folder).  # Constant: demo folder.
HERE = os.path.dirname(os.path.abspath(__file__))  # Absolute path of demo/.
# Define the project root (one level up from demo/).  # Constant: project root.
PROJECT = os.path.dirname(HERE)  # app.py lives here.
# Define the folder holding the screenshots.  # Constant: shots folder.
SHOTS = os.path.join(HERE, "shots")  # The two replacement stills land beside the originals.
# Define the folder holding the session transcripts.  # Constant: transcripts folder.
TRANSCRIPTS = os.path.join(HERE, "transcripts")  # The two new transcripts join steps 3-5 here.
# Define the local base URL of the running app.  # Constant: app URL.
APP_URL = "http://127.0.0.1:8765"  # app.py's default port, via the numeric loopback.
# Define the same scrubbed server environment capture.py used: no API keys, offline path only.  # Constant: server env.
SERVER_ENV = {"PATH": os.environ.get("PATH", ""), "PORT": "8765", "LANG": "C.UTF-8"}  # Identical conditions to the filmed session.

# Start the helper that performs one HTTP GET and returns the decoded JSON body.  # Function: get_json.
def get_json(path):  # Fetch a JSON endpoint from the running app.
    # Open the URL and read the whole response body.  # Step: request.
    with urllib.request.urlopen(APP_URL + path, timeout=30) as response:  # The app answers on loopback.
        return json.loads(response.read().decode("utf-8"))  # Decode the JSON payload.

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

# Start the helper that writes one screen transcript: a labeled header plus the pretty-printed response.  # Function: save_transcript.
def save_transcript(name, header_lines, payload):  # Build one transcript text file for screenshotting.
    # Join the header lines into the transcript's title block.  # Step: header.
    text = "\n".join(header_lines) + "\n" + ("-" * 100) + "\n"  # A ruled line separates the label from the payload.
    # Append the response, pretty-printed with a two-space indent (formatting only; content untouched).  # Step: payload.
    text += json.dumps(payload, indent=2) + "\n"  # The server's own keys, values, and order.
    # Write the transcript to disk.  # Step: write transcript.
    path = os.path.join(TRANSCRIPTS, name)  # The transcript's home beside steps 3-5.
    with open(path, "w", encoding="utf-8") as handle:  # One file per re-shot endpoint.
        handle.write(text)  # The exact text the browser will render.
    # Return the path so the screenshot step can open it.  # Step: hand back path.
    return path  # file:// target for Chromium's native text view.

# Start the helper that screenshots a transcript file, scrolled so a chosen anchor string is in frame.  # Function: shot_transcript.
def shot_transcript(page, cdp, path, anchor, filename):  # Render one transcript in Chromium's native text view and frame the anchor.
    # Open the transcript as a local file: Chromium renders plain text natively, with no custom markup from us.  # Step: open the file.
    page.goto("file://" + path)  # The browser's own text rendering is the presentation.
    # Enlarge the text so it survives the downscale to 720p in the video, via CDP page-scale emulation.  # Step: scale up.
    try:  # The emulation command exists on Chromium builds.
        cdp.send("Emulation.setPageScaleFactor", {"pageScaleFactor": 1.6})  # The same scale as the other transcript shots.
    except Exception:  # A refused scale is not fatal: the shot is still genuine, just smaller.
        pass  # Proceed rather than failing the re-shoot.
    # Scroll the anchor into view using the browser's own find, when an anchor was given.  # Step: frame the anchor.
    if anchor:  # Both payloads have a natural anchor line.
        page.evaluate("(a) => window.find(a)", anchor)  # Chromium selects and scrolls to the first match.
    # Give the browser a beat to paint the final frame.  # Step: settle.
    page.wait_for_timeout(400)  # Static text paints fast.
    # Save the viewport as a PNG, replacing the raw-overflow original.  # Step: capture.
    page.screenshot(path=os.path.join(SHOTS, filename))  # Same filename: one canonical still per endpoint.

# Start the main routine: boot the app, fetch the two payloads live, transcript and photograph them, shut down.  # Function: main.
def main():  # Two stills only; the rest of the capture stands as filmed.
    # Open the server log file so the child process's output survives for diagnosis.  # Step: server log.
    server_log = open(os.path.join(HERE, "server.log"), "w", encoding="utf-8")  # Truncated each run.
    # Start the real app with the scrubbed environment on its default port.  # Step: start the server.
    server = subprocess.Popen([sys.executable, os.path.join(PROJECT, "app.py")], cwd=PROJECT, env=SERVER_ENV, stdout=server_log, stderr=subprocess.STDOUT)  # app.py serves until terminated.
    # Guard everything below so the server is always shut down, even on failure.  # Step: guarded capture.
    try:  # The fetch and the photography happen inside this block.
        # Wait until the app answers its health endpoint.  # Step: await readiness.
        wait_for_server()  # Raises loudly if the app never boots.
        # Fetch the usage snapshot live: counts plus the JSONL evidence inventory read from disk.  # Step: fetch usage.
        usage = get_json("/api/usage")  # The same values the filmed session produced (3 logged events).
        # Fetch the status panel live: configuration state only, nothing session-dependent.  # Step: fetch status.
        status = get_json("/api/status")  # Integration health, honestly labeled.
        # Write the two transcripts in the same labeled style as steps 3-5.  # Step: transcripts.
        t_usage = save_transcript("step6_usage.txt", ["QUIZFORGE LIVE - LIVE CAPTURE TRANSCRIPT", "Step 6 - GET /api/usage (metered model-call counts + JSONL evidence inventory)", "Offline run: no model calls were made, so the counts are empty and the inventory is the story"], usage)  # The usage payload.
        t_status = save_transcript("step7_status.txt", ["QUIZFORGE LIVE - LIVE CAPTURE TRANSCRIPT", "Step 7 - GET /api/status (integration health, exactly as the app reports it)", "Offline run: Nemotron route unset, Zetaris unconfigured (organizers' instance still TBC), Markovian engine active"], status)  # The status payload.
        # Open a Playwright session for the stills.  # Step: start the driver.
        with sync_playwright() as pw:  # The context manager closes everything on exit.
            # Launch headless Chromium (Playwright's build, which does not block loopback navigation).  # Step: start the browser.
            browser = pw.chromium.launch()  # The same driver the main capture used.
            # Create a page sized like a 720p video frame, doubled for crisp stills.  # Step: size the page.
            page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)  # 1280x720 CSS pixels, 2560x1440 image pixels.
            # Open a CDP session for the page-scale emulation.  # Step: CDP session.
            cdp = page.context.new_cdp_session(page)  # One session for both shots.
            # Shoot the usage transcript, framed on the events inventory line.  # Shot: usage, transcript style.
            shot_transcript(page, cdp, t_usage, '"events": 3', "shot06_usage.png")  # That count appears once: the events.jsonl entry.
            # Shoot the status transcript, framed on the Markovian engine block.  # Shot: status, transcript style.
            shot_transcript(page, cdp, t_status, '"markovian_engine"', "shot07_status.png")  # The engine block sits mid-payload.
            # Close the browser cleanly.  # Step: shut down the browser.
            browser.close()  # Frees the Chromium processes.
        # Print a one-line confirmation for the run log.  # Step: report.
        print("Re-shot shot06_usage.png and shot07_status.png as labeled transcripts (live-fetched payloads).")  # Same data, frameable presentation.
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
    main()  # Start the re-shoot.

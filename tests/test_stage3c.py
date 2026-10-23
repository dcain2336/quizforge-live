# test_stage3c.py - offline HTTP tests for the Stage 3c Live-tab UI wiring.  # Module header: what this file is.
# Stage 3c put the Live loop into the browser; these tests prove the wiring over real HTTP:  # Purpose: the served page carries the Live pane, and the endpoints the UI calls produce the money shot.
# the served page carries both panes (v1 intact + Live), and a two-round session driven exactly  # Purpose continued: the UI's own calls, end to end.
# the way the UI drives it (round -> grade all wrong -> round) lands round 2's focus on round 1's misses.  # Purpose continued: focus equals misses.
# Everything runs with NO network routes and NO keys: the environment is scrubbed before import,  # Guarantee: deterministic and offline.
# so the server answers on the Markovian engine + v1 heuristic - the keyless judge experience.  # Guarantee continued: the worst case is the tested case.
# Run from the repo root:  python3 -m unittest discover -s tests -v  # How to run this suite.
# Import the OS module to scrub route keys and locate the bundled sample text.  # Library: os.
import os  # Make the os module available.
# Import the sys module to put the repo root on the import path.  # Library: sys.
import sys  # Make the sys module available.
# Import the JSON module for request and response bodies.  # Library: json.
import json  # Make the json module available.
# Import the tempfile module for an isolated evidence-log directory.  # Library: tempfile.
import tempfile  # Make the tempfile module available.
# Import the threading module to run the HTTP server in the background of the test process.  # Library: threading.
import threading  # Make the threading module available.
# Import http.client for real HTTP calls against the in-process server.  # Library: http.client.
import http.client  # The standard-library HTTP client.
# Import the threaded HTTP server class the app itself uses.  # Library: http.server.
from http.server import ThreadingHTTPServer  # The same server class app.py serves with.
# Import the unittest framework (standard library only, like the whole project).  # Library: unittest.
import unittest  # Make the unittest framework available.
# Define every environment variable that could enable a network route or a real key.  # Constant: route env keys.
ROUTE_ENV_KEYS = ["METERLESS_BASE_URL", "METERLESS_RUNTIME_TOKEN", "METERLESS_MODEL", "NIGHTSHIFT_API_URL", "NIGHTSHIFT_API_KEY", "NIGHTSHIFT_CHAT_PATH", "NEMOTRON_MODEL", "NEMOTRON_MODEL_FALLBACK", "OPENROUTER_API_KEY", "GROQ_API_KEY", "METERLESS_API_URL", "METERLESS_API_KEY", "ZETARIS_REST_URL", "ZETARIS_API_KEY"]  # Mirrors the Stage 3a suite's scrub list.
# Scrub every route key so no test can reach the network through a real credential.  # Step: scrub the env.
for _key in ROUTE_ENV_KEYS:  # Each key that could open a route.
    os.environ.pop(_key, None)  # Remove it for the whole suite.
# Point the metering evidence at a throwaway directory when the Stage 3a suite has not already done so.  # Step: isolate the logs.
os.environ.setdefault("METERLESS_LOG_DIR", tempfile.mkdtemp(prefix="quizforge-live-test3c-logs-"))  # meterless.py reads this live on every write.
# Put the repo root (this file's parent's parent) on the import path.  # Step: import path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # tests/ lives one level below the modules.
# Import the app module under test, now that the environment is clean.  # Library: app (this project).
import app  # The web server: handler class plus the Live routes.
# Resolve the repo root once for fixture paths.  # Constant: repo root.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # The folder holding app.py and sample_data/.
# Start the HTTP fixture: one in-process server on an ephemeral port for the whole class.  # Class: LiveHttpTests.
class LiveHttpTests(unittest.TestCase):  # Define LiveHttpTests, covering the Stage 3c wiring over HTTP.
    # Boot the real handler on port 0 (the OS picks a free port) before any test runs.  # Method: setUpClass.
    @classmethod  # This fixture belongs to the class, not to each test.
    def setUpClass(cls):  # Define the class-level setup.
        # Build the server exactly the way app.main does, but on an ephemeral port.  # Step: build the server.
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), app.QuizForgeLiveHandler)  # Port 0 avoids clashing with a dev server.
        # Remember the port the OS assigned.  # Step: note the port.
        cls.port = cls.server.server_address[1]  # The actual listening port.
        # Serve on a daemon thread so the test process can always exit.  # Step: start serving.
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)  # Background serving.
        cls.thread.start()  # Begin answering requests.
        # Load the bundled sample text once for the round tests.  # Step: load the fixture text.
        with open(os.path.join(REPO_ROOT, "sample_data", "first-responder-sample.txt"), "r", encoding="utf-8") as handle:  # Read the demo material.
            cls.sample_text = handle.read()  # The curriculum the UI's sample button loads.
    # Shut the server down after the class finishes.  # Method: tearDownClass.
    @classmethod  # This teardown belongs to the class too.
    def tearDownClass(cls):  # Define the class-level teardown.
        cls.server.shutdown()  # Stop the serve loop.
        cls.server.server_close()  # Release the listening socket.
    # Start the request helper: one short-lived HTTP connection per call.  # Method: request.
    def request(self, method, path, payload=None):  # Define request with the verb, path, and optional JSON body.
        # Open a connection to the in-process server.  # Step: connect.
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)  # Local only, generous timeout.
        # Serialize the payload when one was given.  # Step: encode the body.
        body = json.dumps(payload) if payload is not None else None  # JSON text or no body at all.
        # Send the request with a JSON content type when a body exists.  # Step: send.
        conn.request(method, path, body=body, headers={"Content-Type": "application/json"} if body else {})  # The same shape the browser's fetch sends.
        # Read the full response before closing.  # Step: read.
        response = conn.getresponse()  # The server's reply.
        raw = response.read().decode("utf-8")  # The reply body as text.
        status = response.status  # The HTTP status code.
        conn.close()  # Done with this connection.
        # Return the status plus the parsed JSON when the body is JSON, else the raw text.  # Step: hand back.
        try:  # The API answers JSON; the page answers HTML.
            return status, json.loads(raw)  # Parsed body.
        except ValueError:  # HTML is not JSON.
            return status, raw  # Raw text body.
    # The served page must carry the Live pane AND the untouched v1 pane.  # Test: page wiring.
    def test_page_has_live_pane_and_v1_intact(self):  # Define the page test.
        # Fetch the home page the way a judge's browser does.  # Step: fetch.
        status, body = self.request("GET", "/")  # The single-page UI.
        # The page served and is HTML text.  # Step: page assertions.
        self.assertEqual(status, 200)  # The page exists.
        self.assertIsInstance(body, str)  # HTML came back, not JSON.
        # The Live pane's markers are all present.  # Step: Live markers.
        for marker in ['id="paneLive"', 'id="liveStartBtn"', 'id="liveGradeBtn"', 'id="liveNextBtn"', 'id="liveMode"', "Live study loop"]:  # Each marker the UI depends on.
            self.assertIn(marker, body)  # The Live wiring is in the served page.
        # The v1 pane's markers are still present (the one-shot generator was not disturbed).  # Step: v1 markers.
        for marker in ['id="paneForge"', 'id="generateBtn"', "Forge my quiz", 'id="checkBtn"']:  # The v1 controls a judge can still use.
            self.assertIn(marker, body)  # The v1 shell survived Stage 3c.
    # The v1 endpoint must still generate over HTTP, keyless.  # Test: v1 regression.
    def test_v1_generate_still_works_over_http(self):  # Define the v1 regression test.
        # POST the sample to the v1 endpoint exactly like the v1 tab does.  # Step: generate.
        status, data = self.request("POST", "/api/generate", {"text": self.sample_text, "count": 6})  # The v1 call.
        # Offline, the heuristic engine answers with a real quiz.  # Step: assertions.
        self.assertEqual(status, 200)  # The endpoint is healthy.
        self.assertEqual(data["source"], "heuristic")  # Keyless means the offline engine, labeled as such.
        self.assertGreaterEqual(len(data["questions"]), 3)  # A usable quiz came back.
    # The money shot over HTTP: round 1 misses become round 2's focus, via the UI's own calls.  # Test: the loop.
    def test_two_round_loop_focus_equals_misses(self):  # Define the loop test.
        # Deal round 1 the way the Live tab does: sample text, topic, empty history.  # Step: round 1.
        status, round1 = self.request("POST", "/api/round", {"text": self.sample_text, "topic": "First Aid", "history": [], "count": 4})  # The UI's start-round call.
        self.assertEqual(status, 200)  # The round was dealt.
        self.assertEqual(round1["plan"]["engine"], "markovian")  # Offline, the engine planned it.
        self.assertTrue(round1["questions"])  # Questions exist to answer.
        self.assertIn("REMAINING:", round1["plan"]["state"])  # The bounded state travels with the plan (the UI renders it).
        # Answer every question wrong on purpose, then grade through the UI's grade call.  # Step: grade all wrong.
        answers = ["definitely wrong"] * len(round1["questions"])  # No accidental matches with real answer terms.
        status, graded = self.request("POST", "/api/grade", {"questions": round1["questions"], "answers": answers, "topic": "First Aid", "sources": []})  # The UI's grade call.
        self.assertEqual(status, 200)  # Grading answered.
        self.assertEqual(graded["score"], 0)  # Every answer missed, honestly.
        missed = graded["missed_topics"]  # The grader's own list of missed topics.
        self.assertTrue(missed)  # There is something to remediate.
        # Fold the results into history exactly the way the Live tab's script does.  # Step: fold history.
        history = [{"topic": item["topic"], "correct": item["correct"]} for item in graded["results"]]  # The client's history shape.
        # Deal round 2 with that history.  # Step: round 2.
        status, round2 = self.request("POST", "/api/round", {"text": self.sample_text, "topic": "First Aid", "history": history, "count": 4})  # The UI's next-round call.
        self.assertEqual(status, 200)  # The adapted round was dealt.
        # Round 2's focus is exactly round 1's missed topics (at most 4 questions, so the focus cap cannot trim).  # Step: the money-shot assertion.
        self.assertEqual(set(round2["plan"]["focus_areas"]), set(missed))  # Focus equals misses.
        # The visible state agrees: every missed topic sits in the REMAINING line the UI displays.  # Step: state assertion.
        remaining_line = next(line for line in round2["plan"]["state"].split("\n") if line.startswith("REMAINING:"))  # The line the Live pane renders.
        for topic in missed:  # Each missed topic.
            self.assertIn(topic, remaining_line)  # It is carried in REMAINING, not buried in raw history.
# Run the suite when this file is executed directly.  # Entry-point guard.
if __name__ == "__main__":  # Check how the file was started.
    unittest.main()  # Run every test above.

# app.py - the QuizForge Live web server.  # Module header: what this file is.
# QuizForge Live extends v1 QuizForge (2026-10-22, Build With AI: Basics entry) with an agentic study loop.  # Provenance note: the Wildcard lane builds on the existing project.
# New routes in Live: /api/round (plan + generate one agentic round), /api/grade (grade + explain misses),  # New routes: the Live endpoints.
# /api/usage (metered call counts + JSONL evidence inventory), /api/status (integration health panel).  # New routes continued: observability for the judges.
# Still zero-dependency: Python standard library only, no pip installs needed.  # Design choice: runs anywhere Python 3 runs.
# Import the JSON module so the API can speak JSON.  # Library: json.
import json  # Make the json module available.
# Import the OS module so we can read the PORT environment variable.  # Library: os.
import os  # Make the os module available.
# Import BaseHTTPRequestHandler and ThreadingHTTPServer from the standard http.server module.  # Library: http.server.
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # The request-handler base class and a threaded server.
# Import our v1 generation engine from the sibling module.  # Library: generator (this project).
import generator  # The v1 quiz-generation engine lives in generator.py.
# Import the agentic study loop from the sibling module.  # Library: agent (this project).
import agent  # The plan/generate/grade/adapt loop lives in agent.py.
# Import the metering wrapper so the /api/usage endpoint can report call counts.  # Library: meterless (this project).
import meterless  # The metering wrapper lives in meterless.py.
# Import the Nemotron client so the status endpoint can report which model route is active.  # Library: nemotron (this project).
import nemotron  # The Nemotron client lives in nemotron.py (Nightshift first, OpenRouter fallback).
# Import the Zetaris data layer so the status endpoint can report its configuration state.  # Library: zetaris (this project).
import zetaris  # The Zetaris harness client lives in zetaris.py.
# Define the directory this file lives in, so static files resolve from anywhere.  # Constant: project root.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Absolute path of the project folder.
# Define the path of the single-page UI file.  # Constant: UI file path.
INDEX_PATH = os.path.join(BASE_DIR, "static", "index.html")  # The front-end page served at GET /.
# Define the path of the bundled demo study text.  # Constant: sample file path.
SAMPLE_PATH = os.path.join(BASE_DIR, "sample_data", "first-responder-sample.txt")  # The one-click demo material.
# Define the default port; the PORT environment variable can override it.  # Constant: listen port.
PORT = int(os.environ.get("PORT", "8765"))  # Default to 8765 for local demos.
# Start the helper that parses a JSON POST body and returns the payload dictionary.  # Function: read_json_body.
def read_json_body(handler):  # Define read_json_body, which reads and parses the request body.
    # Read the declared request-body length, defaulting to zero.  # Step: body length.
    length = int(handler.headers.get("Content-Length", "0"))  # The client tells us how many bytes to read.
    # Read exactly that many bytes from the request body.  # Step: read the body.
    raw_body = handler.rfile.read(length)  # The raw JSON the browser sent.
    # Parse the body as JSON.  # Step: parse the body.
    return json.loads(raw_body.decode("utf-8"))  # Convert bytes into a dictionary.
# Start the request-handler class that answers every HTTP request.  # Class: QuizForgeLiveHandler.
class QuizForgeLiveHandler(BaseHTTPRequestHandler):  # Define the handler by extending the standard base class.
    # Silence the default per-request stderr logging so demo output stays readable.  # Method: log_message (muted).
    def log_message(self, format, *args):  # Override the base logging hook.
        pass  # Do nothing: keep the console clean.
    # Start the helper that sends a JSON response with a chosen status code.  # Method: send_json.
    def send_json(self, status, payload):  # Define send_json, which serializes a dictionary to the client.
        # Serialize the payload to UTF-8 JSON bytes.  # Step: encode the body.
        body = json.dumps(payload).encode("utf-8")  # Convert the dictionary into bytes.
        # Send the HTTP status line.  # Step: status line.
        self.send_response(status)  # Write the status code.
        # Declare the JSON content type.  # Step: content-type header.
        self.send_header("Content-Type", "application/json; charset=utf-8")  # Tell the client the body is JSON.
        # Declare the exact body length so the client knows when it ends.  # Step: length header.
        self.send_header("Content-Length", str(len(body)))  # Byte length of the body.
        # Finish the header block.  # Step: end headers.
        self.end_headers()  # Blank line that ends the headers.
        # Write the body bytes to the client.  # Step: write the body.
        self.wfile.write(body)  # Send the JSON payload.
    # Start the helper that sends a plain file with a chosen content type.  # Method: send_file.
    def send_file(self, path, content_type):  # Define send_file, which streams a file from disk.
        # Read the whole file as bytes.  # Step: read the file.
        with open(path, "rb") as handle:  # Open in binary mode and auto-close afterwards.
            body = handle.read()  # Load the file contents.
        # Send a 200 OK status line.  # Step: status line.
        self.send_response(200)  # The file exists and is being served.
        # Declare the caller-provided content type.  # Step: content-type header.
        self.send_header("Content-Type", content_type)  # HTML or plain text, as requested.
        # Declare the exact body length.  # Step: length header.
        self.send_header("Content-Length", str(len(body)))  # Byte length of the file.
        # Finish the header block.  # Step: end headers.
        self.end_headers()  # Blank line that ends the headers.
        # Write the file bytes to the client.  # Step: write the body.
        self.wfile.write(body)  # Send the file contents.
    # Start the GET router: the home page, sample text, health, and metering snapshot.  # Method: do_GET.
    def do_GET(self):  # Define do_GET, which the server calls for every GET request.
        # Route the root path to the single-page UI.  # Branch: home page.
        if self.path == "/":  # Check for the root path.
            self.send_file(INDEX_PATH, "text/html; charset=utf-8")  # Serve the front-end page.
        # Route /sample to the bundled demo study text.  # Branch: sample text.
        elif self.path == "/sample":  # Check for the sample path.
            self.send_file(SAMPLE_PATH, "text/plain; charset=utf-8")  # Serve the demo material as plain text.
        # Route /health to a tiny liveness probe for scripts and judges.  # Branch: health check.
        elif self.path == "/health":  # Check for the health path.
            self.send_json(200, {"status": "ok", "app": "quizforge-live"})  # Report that the server is alive.
        # Route /api/usage to the metered model-call counts plus the JSONL evidence inventory.  # Branch: usage snapshot.
        elif self.path == "/api/usage":  # Check for the usage path.
            self.send_json(200, {"usage": meterless.summary(), "evidence": meterless.log_files()})  # The per-model call counts plus the JSONL evidence files.
        # Route /api/status to the integration health panel: Nemotron route, Zetaris, Meterless.  # Branch: status.
        elif self.path == "/api/status":  # Check for the status path.
            # Ask each integration whether it is configured, so the demo can show its working state honestly.  # Step: gather the health.
            status = {"nemotron_provider": nemotron.get_provider(), "nemotron_model": nemotron.get_model() if nemotron.get_provider() else None, "zetaris_configured": zetaris.is_configured(), "meterless_remote_configured": meterless.is_configured(), "evidence": meterless.log_files()}  # One honest panel for the judges.
            self.send_json(200, status)  # The integration health snapshot.
        # Anything else is a 404 with a JSON explanation.  # Branch: not found.
        else:  # No route matched.
            self.send_json(404, {"error": "Not found: " + self.path})  # Tell the client the path does not exist.
    # Start the POST router: the v1 generate API plus the Live agentic endpoints.  # Method: do_POST.
    def do_POST(self):  # Define do_POST, which the server calls for every POST request.
        # Parse the JSON body once for all POST routes, turning bad input into a clean 400.  # Step: parse the body.
        try:  # Begin the guarded parse.
            payload = read_json_body(self)  # Convert the body bytes into a dictionary.
        # Handle malformed JSON without crashing the handler.  # Handler: bad JSON.
        except (ValueError, UnicodeDecodeError):  # Catch decode and parse failures.
            self.send_json(400, {"error": "Request body must be valid JSON."})  # Explain the problem.
            return  # Stop processing this request.
        # Route /api/generate to the v1 quiz-generation engine (unchanged behavior).  # Branch: v1 generate.
        if self.path == "/api/generate":  # Check for the v1 generation path.
            # Pull the study text out of the payload, defaulting to empty.  # Step: read the text field.
            text = payload.get("text", "")  # The study material to quiz on.
            # Pull the requested question count, defaulting to eight and clamping to a sane range.  # Step: read the count field.
            count = max(3, min(20, int(payload.get("count", 8))))  # Between 3 and 20 questions per quiz.
            # Run the generation engine, turning its validation errors into clean 400 responses.  # Step: generate the quiz.
            try:  # Begin the guarded generation.
                result = generator.generate(text, count)  # The quiz package: source, guide, questions.
            # Handle the engine's user-facing validation errors.  # Handler: validation error.
            except ValueError as err:  # The engine raises ValueError with a readable message.
                self.send_json(400, {"error": str(err)})  # Pass the message through to the UI.
                return  # Stop processing this request.
            # Send the finished quiz package back as JSON.  # Step: success response.
            self.send_json(200, result)  # The browser renders the guide and the quiz.
            return  # Stop processing this request.
        # Route /api/round to the agentic loop: plan the round, then generate its questions.  # Branch: Live round.
        if self.path == "/api/round":  # Check for the Live round path.
            # Pull the study text, topic, and history out of the payload.  # Step: read the round inputs.
            text = payload.get("text", "")  # The study material for this round.
            topic = payload.get("topic", "General")  # The concept label the learner is studying.
            history = payload.get("history", [])  # Past graded rounds, for the adaptive plan.
            # Pull the question count, defaulting to six and clamping to a sane range.  # Step: read the count field.
            count = max(2, min(12, int(payload.get("count", 6))))  # Between 2 and 12 questions per round.
            # Run the agentic round, turning validation errors into clean 400 responses.  # Step: run the round.
            try:  # Begin the guarded round.
                result = agent.run_round(text, topic, history, count)  # The round package: plan plus quiz.
            # Handle user-facing validation errors from the engine.  # Handler: validation error.
            except ValueError as err:  # The engine raises ValueError with a readable message.
                self.send_json(400, {"error": str(err)})  # Pass the message through to the UI.
                return  # Stop processing this request.
            # Send the round package back as JSON.  # Step: success response.
            self.send_json(200, result)  # The browser renders the plan and plays the round.
            return  # Stop processing this request.
        # Route /api/grade to round grading with evidence-backed explanations for misses.  # Branch: Live grade.
        if self.path == "/api/grade":  # Check for the Live grade path.
            # Pull the questions, answers, topic, and sources out of the payload.  # Step: read the grading inputs.
            questions = payload.get("questions", [])  # The questions the learner answered.
            user_answers = payload.get("answers", [])  # The learner's answers in order.
            topic = payload.get("topic", "General")  # The concept label.
            sources = payload.get("sources", [])  # The study sources for citations.
            # Grade the round and explain the misses.  # Step: grade the round.
            result = agent.grade_round(questions, user_answers, topic, sources)  # Score, per-question results, usage.
            # Send the grading package back as JSON.  # Step: success response.
            self.send_json(200, result)  # The browser shows the score and the explanations.
            return  # Stop processing this request.
        # Anything else is a 404 with a JSON explanation.  # Branch: not found.
        self.send_json(404, {"error": "Not found: " + self.path})  # Tell the client the path does not exist.
# Start the program entry point: build the server and run it until interrupted.  # Function: main.
def main():  # Define main, the function executed when this file runs directly.
    # Load any project-local .env file so provider keys are ready before the first request.  # Step: load keys early.
    generator.load_dotenv()  # Read the .env file if one exists.
    # Create the threaded HTTP server bound to all local interfaces on our port.  # Step: build the server.
    server = ThreadingHTTPServer(("0.0.0.0", PORT), QuizForgeLiveHandler)  # Threaded so one slow Nemotron call never blocks other requests.
    # Announce where the app is listening, so a human running it knows the URL.  # Step: startup message.
    print("QuizForge Live is running at http://localhost:" + str(PORT) + "  (Ctrl+C to stop)")  # Print the local URL.
    # Serve requests forever; a keyboard interrupt shuts the server down cleanly.  # Step: serve loop.
    try:  # Begin the guarded serve block.
        server.serve_forever()  # Block here, answering requests, until interrupted.
    # Handle Ctrl+C as a normal, clean shutdown.  # Handler: keyboard interrupt.
    except KeyboardInterrupt:  # The user pressed Ctrl+C.
        pass  # Fall through to the close call below.
    # Release the listening socket.  # Step: close the server.
    server.server_close()  # Free the port.
# Run main() only when this file is executed directly, not when it is imported.  # Entry-point guard.
if __name__ == "__main__":  # Check how the file was started.
    main()  # Start the server.

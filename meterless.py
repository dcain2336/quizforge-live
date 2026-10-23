# meterless.py - the Meterless/Nightshift metering wrapper for QuizForge Live.  # Module header: what this file is.
# The Wildcard [Tinkerer] lane requires integrating Meterless alongside Zetaris:  # Design choice 1: why Meterless is here.
# every model call the agent makes is metered and logged, which is the agent-ops story for the judges.  # Design choice 1 continued: the judging narrative.
# "Meterless" covers the sponsor's inference-serving/metering layer; Nightshift is the related agent-ops surface.  # Terminology note: Meterless + Nightshift.
# Every call is logged as JSONL (one event per line) under the run's logs/ directory:  # Design choice 2: judges' evidence.
# audit, traces, telemetry, and provenance events land in files the judges can inspect after the run.  # Design choice 2 continued: what the logs hold.
# CRITICAL: each logged call records the PROVIDER and MODEL that actually handled the request,  # Design choice 3: the auto-router caveat.
# because a meterless/auto router can serve a non-NVIDIA model without the app asking for one.  # Design choice 3 continued: honesty about routing.
# It is safe to call at all times: without credentials it meters locally and never blocks the agent.  # Safety guarantee: fail-open, local-first.
# Import the OS module so we can read metering credentials and the log directory from the environment.  # Library: os.
import os  # Make the os module available.
# Import the JSON module so we can encode metering events.  # Library: json.
import json  # Make the json module available.
# Import urllib.request so optional remote logging needs zero third-party packages.  # Library: urllib.request.
import urllib.request  # Make the urllib.request module available.
# Import urllib.error so remote logging failures can be caught and swallowed.  # Library: urllib.error.
import urllib.error  # Make the urllib.error module available.
# Import datetime so every log line carries a UTC timestamp.  # Library: datetime.
import datetime  # Make the datetime module available.
# Import the threading module so the local counters stay correct under the threaded server.  # Library: threading.
import threading  # Make the threading module available.
# Import the uuid module so each process gets one session id for the whole run.  # Library: uuid.
import uuid  # Make the uuid module available.
# Start the live getters for the metering endpoint and key, read from the environment at call time.  # Functions: _api_url, _api_key.
def _api_url():  # Define _api_url, which returns the ingest endpoint each time it is called.
    # Read the value live so a .env loaded after import still works.  # Why live: env may load after import.
    return os.environ.get("METERLESS_API_URL", "")  # Empty until the HackOS workspace supplies the endpoint.
# Start the getter for the Meterless/Nightshift API key.  # Function: _api_key.
def _api_key():  # Define _api_key, which returns the key or an empty string.
    # Read the value live so a .env loaded after import still works.  # Why live: env may load after import.
    return os.environ.get("METERLESS_API_KEY", "")  # Empty until the HackOS workspace supplies the key.
# Define the base directory this file lives in, so the logs/ directory resolves from anywhere.  # Constant: project root.
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Absolute path of the project folder.
# Start the getter for the log directory, read from the environment at call time.  # Function: _log_dir.
def _log_dir():  # Define _log_dir, which returns the evidence folder each time it is called.
    # Read the value live; the default is the run's logs/ folder next to this file.  # Why live: env may load after import.
    return os.environ.get("METERLESS_LOG_DIR", os.path.join(_BASE_DIR, "logs"))  # The run's evidence folder, shipped with the entry.
# Start the getters for the two JSONL evidence file paths.  # Functions: _call_log_path, _event_log_path.
def _call_log_path():  # Define _call_log_path, which returns the per-call log path.
    return os.path.join(_log_dir(), "model_calls.jsonl")  # One line per model call the agent made.
# Start the getter for the generic event log path.  # Function: _event_log_path.
def _event_log_path():  # Define _event_log_path, which returns the event log path.
    return os.path.join(_log_dir(), "events.jsonl")  # One line per log_event call.
# Define one session id per process so judges can group the whole run's events.  # Constant: session id.
SESSION_ID = str(uuid.uuid4())  # A random session id, made once when this module loads.
# Create the lock that protects the local counters and file writes from concurrent requests.  # Constant: thread lock.
_LOG_LOCK = threading.Lock()  # One lock shared by all metering updates.
# Create the local call counters, keyed by "provider:model" strings.  # Constant: local counter store.
_LOCAL_COUNTERS = {}  # Maps a label like "nightshift:nvidia/nemotron-3.5-super-vl" to a call count.
# Create the per-process call sequence counter for log-line ordering.  # Constant: call sequence.
_CALL_SEQ = [0]  # A one-element list so the counter is mutable inside the lock.
# Start the helper that makes sure the logs/ directory exists.  # Function: _ensure_log_dir.
def _ensure_log_dir():  # Define _ensure_log_dir, which creates the directory when it is missing.
    # Create the directory and any parents, doing nothing when it already exists.  # Step: create the directory.
    os.makedirs(_log_dir(), exist_ok=True)  # Safe to call on every write: no error when the folder is there.
# Start the helper that appends one JSON event to a JSONL file under the lock.  # Function: _append_jsonl.
def _append_jsonl(path, event):  # Define _append_jsonl with the file path and the event dictionary.
    # Open the file in append mode and write the event as one line.  # Step: append the line.
    with open(path, "a", encoding="utf-8") as handle:  # Append mode: never overwrites past events.
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")  # One JSON object per line: the JSONL format.
# Start the check that reports whether remote metering is configured.  # Function: is_configured.
def is_configured():  # Define is_configured, which returns True when both values exist.
    # Remote metering is usable whenever the URL and the key are both present.  # Rule: both are required.
    return bool(_api_url() and _api_key())  # True only when the workspace credentials are set.
# Start the UTC timestamp helper for the log lines.  # Function: _now_iso.
def _now_iso():  # Define _now_iso, which returns the current UTC time in ISO format.
    # Format the current UTC time with a trailing Z.  # Step: build the timestamp.
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")  # ISO 8601 UTC, e.g. 2026-10-23T18:00:00Z.
# Start the generic event logger: audit, traces, telemetry, and provenance land here.  # Function: log_event.
def log_event(kind, payload=None):  # Define log_event with the event kind and an optional payload dictionary.
    # Build the base event with the timestamp, session, and kind.  # Step: assemble the envelope.
    event = {"ts": _now_iso(), "session": SESSION_ID, "event": kind}  # The envelope every logged event carries.
    # Merge the caller payload under the "data" key when one was given.  # Step: attach the payload.
    if payload:  # Check whether a payload was provided.
        event["data"] = payload  # The caller-supplied details live here.
    # Write the event to the event log under the lock so lines never interleave.  # Step: append the line.
    with _LOG_LOCK:  # Hold the lock for directory creation plus the append.
        _ensure_log_dir()  # Make sure logs/ exists before writing.
        _append_jsonl(_event_log_path(), event)  # One JSONL line per event.
    # Mirror the event to the remote ingest when credentials are configured, failing open.  # Step: optional remote mirror.
    _remote_post(event)  # Swallows its own errors: metering must never break the agent loop.
# Start the counter: record one model call, locally always, remotely when configured.  # Function: count_call.
def count_call(provider, model, tokens_in=0, tokens_out=0):  # Define count_call with provider, model, and token counts.
    # Build the human-readable label for this call.  # Step: make the label.
    label = provider + ":" + model  # A label like "nightshift:nvidia/nemotron-3.5-super-vl".
    # Build the JSONL event for this call, naming exactly which model handled it.  # Step: build the call event.
    with _LOG_LOCK:  # Hold the lock for the counter, the sequence number, and the file writes.
        _ensure_log_dir()  # Make sure logs/ exists before writing.
        _LOCAL_COUNTERS[label] = _LOCAL_COUNTERS.get(label, 0) + 1  # Add one to this label's count.
        _CALL_SEQ[0] += 1  # Advance the per-process call sequence.
        call_event = {"ts": _now_iso(), "session": SESSION_ID, "seq": _CALL_SEQ[0], "event": "model_call", "provider": provider, "model": model, "tokens_in": tokens_in, "tokens_out": tokens_out}  # The exact route the request took.
        _append_jsonl(_call_log_path(), call_event)  # One JSONL line per model call.
    # Mirror the call event to the remote ingest when configured, failing open.  # Step: optional remote mirror.
    _remote_post(call_event)  # Swallows its own errors: metering must never break the agent loop.
# Start the remote mirror: POST one event to the Meterless/Nightshift ingest endpoint.  # Function: _remote_post.
def _remote_post(event):  # Define _remote_post with the event dictionary to mirror.
    # Skip remote logging entirely when the workspace credentials are not set.  # Guard: unconfigured.
    if not is_configured():  # No URL or no key means local-only metering.
        return  # The JSONL files above are the whole story for now.
    # Send the event, swallowing every failure so the agent loop never breaks.  # Step: guarded POST.
    try:  # Begin the guarded network block.
        # Encode the event as JSON bytes for the POST body.  # Step: serialize the body.
        body = json.dumps(event).encode("utf-8")  # The event payload.
        # Build the POST request with the bearer key.  # Step: build the request.
        request = urllib.request.Request(_api_url(), data=body, method="POST")  # A POST to the ingest endpoint.
        # Add the JSON content-type header.  # Step: header 1 of 3.
        request.add_header("Content-Type", "application/json")  # Tell the endpoint we are sending JSON.
        # Add the bearer authorization header with the API key.  # Step: header 2 of 3.
        request.add_header("Authorization", "Bearer " + _api_key())  # Authenticate with the workspace key.
        # Add a browser-like user agent so strict API edges accept the call.  # Step: header 3 of 3.
        request.add_header("User-Agent", "curl/8.0")  # A plain user agent that API edges accept reliably.
        # Fire the request and read the reply, giving up after ten seconds.  # Step: perform the call.
        with urllib.request.urlopen(request, timeout=10) as response:  # Open the connection and auto-close it.
            response.read()  # Drain the reply body; the status is all we need.
    # Swallow network and HTTP failures: metering is observability, never load-bearing.  # Handler: fail open.
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):  # Catch the expected failure modes.
        pass  # The local JSONL files still hold the complete evidence.
# Start the summary helper: return the local call counts for the demo and the judges.  # Function: summary.
def summary():  # Define summary, which returns a copy of the local counters.
    # Copy the counters under the lock so the snapshot is consistent.  # Step: locked snapshot.
    with _LOG_LOCK:  # Hold the lock while copying.
        snapshot = dict(_LOCAL_COUNTERS)  # A plain copy of the counter map.
    # Return the snapshot to the caller.  # Step: hand back the result.
    return snapshot  # Call counts per provider:model label.
# Start the log-file inventory helper: which JSONL evidence files exist and how big they are.  # Function: log_files.
def log_files():  # Define log_files, which reports the evidence files on disk.
    # List the two known log files with their line counts and sizes.  # Step: stat the files.
    inventory = []  # Start with an empty inventory list.
    # Check each known log path in turn.  # Loop: the evidence files.
    for path in (_call_log_path(), _event_log_path()):  # The two JSONL files this module writes.
        # Stat the file when it exists, otherwise report it as absent.  # Step: file status.
        if os.path.exists(path):  # The file has been written at least once.
            # Count its lines cheaply without loading the whole file into memory.  # Step: line count.
            with open(path, "r", encoding="utf-8") as handle:  # Read the file in text mode.
                lines = sum(1 for _ in handle)  # One per event: the line count is the event count.
            inventory.append({"path": path, "exists": True, "events": lines, "bytes": os.path.getsize(path)})  # The evidence the judges can open.
        else:  # The file has not been written yet.
            inventory.append({"path": path, "exists": False, "events": 0, "bytes": 0})  # Nothing recorded so far.
    # Return the inventory to the caller.  # Step: hand back the result.
    return inventory  # Per-file existence, event count, and byte size.
# Start the reset helper: clear the local counters between demo rounds.  # Function: reset.
def reset():  # Define reset, which empties the local counters.
    # Clear the map under the lock so no concurrent update is lost.  # Step: locked clear.
    with _LOG_LOCK:  # Hold the lock while clearing.
        _LOCAL_COUNTERS.clear()  # Remove all recorded counts.

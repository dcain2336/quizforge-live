# zetaris.py - the Zetaris AI Data Harness data layer for QuizForge Live.  # Module header: what this file is.
# The Wildcard [Tinkerer] lane requires integrating Zetaris: the agent's study corpus lives  # Design choice 1: why Zetaris is here.
# behind the Zetaris data harness instead of being pasted into the prompt by hand.  # Design choice 1 continued: governed in-place queries.
# Zetaris story for the judges: the study material is fragmented across sources, and the agent  # Design choice 2: the judging narrative.
# discovers and queries it in place through one harness - the "fragmented intelligence" theme.  # Design choice 2 continued: mirrors Track 01's language.
# This module speaks the DOCUMENTED Zetaris REST surface (public zetaris/getting-started repo):  # Basis note: the request/response shape comes from Zetaris's own scripts.
# Bearer auth + X-Org-ID + X-Request-ID headers; SQL runs go to POST /sql-editor/sqls/run with  # The two verified calls this module makes.
# {"queryId": <uuid>, "sql": <sql>, "source": "SqlEditor", "limit": <n>}; rows come back under "data".  # The verified request/response contract.
# The NVIDIA API key is NEVER needed here - Zetaris is the data layer only.  # Security note: no model key touches this module.
# The instance itself is supplied by the HackOS workspace: a cloud-hosted "free Zetaris instance  # Access note: where the endpoint comes from.
# for participants" was promised (workspace Getting-access section); ZETARIS_REST_URL + ZETARIS_API_KEY  # Access note continued: the two values needed.
# point at it. Zero third-party dependencies: Python standard library only.  # Design choice 3: no installs needed.
# Import the JSON module so we can encode SQL requests and decode row payloads.  # Library: json.
import json  # Make the json module available.
# Import the OS module so we can read the Zetaris connection values from the environment.  # Library: os.
import os  # Make the os module available.
# Import the uuid module so every query carries a unique request id, as the Zetaris surface expects.  # Library: uuid.
import uuid  # Make the uuid module available.
# Import urllib.request so we can call the Zetaris REST surface with zero third-party packages.  # Library: urllib.request.
import urllib.request  # Make the urllib.request module available.
# Import urllib.error so HTTP failures can be caught and reported cleanly.  # Library: urllib.error.
import urllib.error  # Make the urllib.error module available.
# Define how long (in seconds) a Zetaris call may take before we give up.  # Constant: HTTP timeout.
HTTP_TIMEOUT_SECONDS = 60  # SQL queries against a harness can take a while.
# Define a browser-like user agent, because some API edges reject the default Python one.  # Constant: user agent string.
USER_AGENT = "curl/8.0"  # A plain user agent that API edges accept reliably.
# Start the exception type raised when the Zetaris call cannot produce rows.  # Class: ZetarisError.
class ZetarisError(Exception):  # Define ZetarisError, a plain exception with a message.
    pass  # No extra behavior: it is just a labeled error.
# Start the small getters that read the Zetaris connection values fresh from the environment.  # Functions: _rest_url, _api_key, _org_id, _corpus_table.
def _rest_url():  # Define _rest_url, which returns the instance URL each time it is called.
    # Read the value live so a .env loaded after import still works.  # Why live: env may load after import.
    return os.environ.get("ZETARIS_REST_URL", "").rstrip("/")  # The instance URL from the HackOS workspace (e.g. https://<instance>/api/v1.0).
# Start the getter for the Zetaris API key (created in the Zetaris GUI per their docs).  # Function: _api_key.
def _api_key():  # Define _api_key, which returns the key or an empty string.
    # Read the value live so a .env loaded after import still works.  # Why live: env may load after import.
    return os.environ.get("ZETARIS_API_KEY", "")  # Never hardcode it; never print it; never log it.
# Start the getter for the numeric Zetaris organization id.  # Function: _org_id.
def _org_id():  # Define _org_id, which returns the org id each time it is called.
    # Read the value live; their reference scripts default this to "1".  # Default: "1" like zetaris_sql.py.
    return os.environ.get("ZETARIS_ORG_ID", "1")  # The numeric org id the X-Org-ID header carries.
# Start the getter for the study-corpus table the agent queries.  # Function: _corpus_table.
def _corpus_table():  # Define _corpus_table, which returns the provisioned table name.
    # Read the value live; defaults to the QuizForge provisioning name.  # Default: the provisioned chunk table.
    return os.environ.get("ZETARIS_CORPUS_TABLE", "quizforge.study_chunks")  # The table holding study chunks (source_name, excerpt).
# Start the check that reports whether the Zetaris connection is configured.  # Function: is_configured.
def is_configured():  # Define is_configured, which returns True when the URL and key exist.
    # The data layer is usable whenever the URL and the key are both present.  # Rule: both are required.
    return bool(_rest_url() and _api_key())  # True only when the workspace credentials are set.
# Start the low-level helper that builds the verified Zetaris header set.  # Function: _headers.
def _headers():  # Define _headers, which returns the header dict for every call.
    # Assemble the bearer token plus the two Zetaris-required headers.  # Step: build the header map.
    return {"Authorization": "Bearer " + _api_key(), "X-Org-ID": _org_id(), "X-Request-ID": str(uuid.uuid4()), "Content-Type": "application/json", "User-Agent": USER_AGENT}  # X-Request-ID must be a fresh UUID per call.
# Start the low-level helper that calls one Zetaris REST path and returns the parsed body.  # Function: _call.
def _call(path, body=None):  # Define _call with a path and an optional JSON body.
    # Refuse clearly when the workspace credentials are not set, naming exactly what is missing.  # Guard: unconfigured.
    if not is_configured():  # No URL or no key means the harness cannot be reached yet.
        raise ZetarisError("Zetaris is not configured: set ZETARIS_REST_URL and ZETARIS_API_KEY from the HackOS workspace sponsor-credits section.")  # Point the operator at the onboarding source.
    # Build the HTTP request: GET when there is no body, POST with a JSON body otherwise.  # Step: build the request.
    data = json.dumps(body).encode("utf-8") if body is not None else None  # Serialize the body only when one was given.
    request = urllib.request.Request(_rest_url() + path, data=data, method="POST" if body is not None else "GET", headers=_headers())  # One request object for both verbs.
    # Send the request and read the response, giving up after the timeout.  # Step: perform the HTTP call.
    try:  # Begin the guarded network block.
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:  # Open the connection and auto-close it.
            # Decode the body and parse it as JSON, tolerating an empty body.  # Step: parse the response.
            return json.loads(response.read().decode("utf-8") or "null")  # The parsed response, or null for an empty body.
    # Turn network and HTTP failures into our own clear error type.  # Handler: request failure.
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as err:  # Catch the expected failure modes.
        raise ZetarisError("Zetaris request to " + path + " failed: " + str(err))  # Wrap the cause in our error type.
# Start the read-only preflight: proves the instance, the key, and SQL execution all work.  # Function: preflight.
def preflight():  # Define preflight, which mirrors the "SELECT 1" check in Zetaris's own preflight script.
    # List the datasources first: a 200 here proves the instance is up and the key is valid.  # Step 1: the datasources probe.
    datasources = _call("/datasource/datasources")  # The documented read-only endpoint from the getting-started AGENTS.md.
    # Run SELECT 1 through the SQL editor endpoint: proves query execution works too.  # Step 2: the query probe.
    one = run_sql("SELECT 1", limit=1)  # The exact check Zetaris's own preflight.py performs.
    # Return both results so the caller (or the /api/status page) can show them.  # Step: hand back the evidence.
    return {"datasources_ok": True, "datasources": datasources, "select_1_ok": bool(one.get("rows"))}  # True when both probes succeeded.
# Start the SQL runner: send one Lightning SQL statement and return its rows.  # Function: run_sql.
def run_sql(sql, limit=100):  # Define run_sql with a SQL string and a row cap.
    # Send the statement using the verified sql-editor request shape (queryId + source fields).  # Step: call the harness.
    out = _call("/sql-editor/sqls/run", {"queryId": str(uuid.uuid4()), "sql": sql, "source": "SqlEditor", "limit": limit})  # The request shape from Zetaris's own zetaris_sql.py.
    # Pull the rows out of the "data" field, tolerating the few shapes the surface returns.  # Step: normalize the rows.
    rows = out.get("data") if isinstance(out, dict) else None  # Rows live under "data" per the reference scripts.
    # Package the rows with their column names when the surface provides them.  # Step: hand back the result.
    return {"rows": rows if isinstance(rows, list) else [], "raw": out}  # Callers read "rows"; "raw" keeps everything for debugging.
# Start the corpus query: read study chunks from the provisioned harness table.  # Function: query_corpus.
def query_corpus(limit=50):  # Define query_corpus with a row cap.
    # Run a plain SELECT against the provisioned corpus table (source_name, excerpt columns).  # Step: query the harness.
    result = run_sql("SELECT source_name, excerpt FROM " + _corpus_table(), limit=limit)  # The study chunks provisioned on the instance.
    # Normalize the rows into the source dicts the rest of the app already understands.  # Step: normalize the rows.
    chunks = []  # Start with an empty chunk list.
    # Walk the returned rows, accepting both list rows and dict rows.  # Loop: tolerant row mapping.
    for row in result.get("rows", []):  # Each row from the harness.
        # Map list-shaped rows by column position.  # Branch: list rows.
        if isinstance(row, list) and len(row) >= 2:  # Positional rows: [source_name, excerpt].
            chunks.append({"source": str(row[0]), "excerpt": str(row[1])})  # Name plus text, matching the local_corpus shape.
        # Map dict-shaped rows by column name.  # Branch: dict rows.
        elif isinstance(row, dict):  # Named rows: {"source_name": ..., "excerpt": ...}.
            chunks.append({"source": str(row.get("source_name", "zetaris")), "excerpt": str(row.get("excerpt", ""))})  # Same shape as the offline fallback.
    # Return the chunk list to the caller.  # Step: hand back the corpus.
    return chunks  # The agent's study sources, queried from the harness.
# Start the ingestion helper: registers a study source's chunks on the harness.  # Function: ingest_source.
def ingest_source(name, text):  # Define ingest_source with a source name and its text.
    # Provisioning new datasources on the harness is instance-specific (their docs route it through  # Guard: explain the honest path.
    # the Zetaris Explorer GUI / first-dataset guide), so the agent stores the provisioned corpus table  # Guard continued: why this stays thin.
    # from the environment instead of inventing one. Report exactly what to do next.  # Guard continued: the operator's next step.
    raise ZetarisError("ingest_source needs a provisioned corpus: on the Zetaris instance, follow the getting-started first-dataset guide (docs/guides/first-dataset.md) to load study chunks into the '" + _corpus_table() + "' table, then query_corpus() will read them. QuizForge Live never invents table names.")  # Honest: no blind DDL from the agent.
# Start the offline fallback: split pasted text into source chunks without any harness.  # Function: local_corpus.
def local_corpus(text, chunk_chars=2000):  # Define local_corpus with text and a chunk size.
    # Walk the text in fixed-size windows so the agent always has "sources" to cite.  # Step: chunk the text.
    chunks = []  # Start with an empty chunk list.
    # Slice the text into non-overlapping windows.  # Loop: chunk windows.
    for start in range(0, len(text), chunk_chars):  # Step through the text in chunk-sized jumps.
        chunks.append({"source": "local-paste", "excerpt": text[start:start + chunk_chars]})  # Record each chunk with a generic source label.
    # Return the chunk list to the caller.  # Step: hand back the result.
    return chunks  # The offline stand-in for the harness query result.

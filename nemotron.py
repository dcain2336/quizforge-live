# nemotron.py - the NVIDIA Nemotron model client for QuizForge Live.  # Module header: what this file is.
# QuizForge Live runs its agentic loop on NVIDIA Nemotron models, and the GenAI Works rules demand it  # Design choice 1: the model and the rule behind it.
# through Nightshift: "Your app must use a Nemotron model through Nightshift in a working feature"  # The DGX Spark prize eligibility rule, exact wording.
# for the $4,699 NVIDIA DGX Spark in-kind prize. So the PRIMARY route is the Nightshift chat endpoint.  # Design choice 1 continued: Nightshift first.
# SECURITY RULE (workspace-verified): the NVIDIA API key goes into Nightshift's Providers tab,  # Security rule: where the NVIDIA key lives.
# NEVER into code or this repo. Nightshift injects the provider key server-side; this client only  # Security rule continued: the client never sees it.
# ever carries the Nightshift API key, which is a separate workspace-issued credential.  # Security rule continued: the one key this client holds.
# FALLBACK: when Nightshift is not configured, the client falls back to the OpenRouter free tier  # Design choice 2: the fallback keeps the demo alive.
# (the seat nvidia/nemotron-3.5-super-vl:free was verified live in ARC on 2026-10-22).  # Design choice 2 continued: the proven fallback seat.
# Zero third-party dependencies: it uses only Python's standard library, like the v1 engine.  # Design choice 3: no installs needed.
# ASSUMPTION (flagged, to confirm from the workspace): Nightshift exposes an OpenAI-compatible  # Assumption: the Nightshift endpoint shape.
# chat-completions endpoint at <NIGHTSHIFT_API_URL>/chat/completions with the Nemotron model named  # Assumption continued: the path and model naming.
# by NEMOTRON_MODEL. If the workspace documents a different path, only NIGHTSHIFT_CHAT_PATH changes.  # Assumption continued: the single place to adjust.
# Import the JSON module so we can encode requests and decode replies.  # Library: json.
import json  # Make the json module available.
# Import the OS module so we can read keys, URLs, and model overrides from the environment.  # Library: os.
import os  # Make the os module available.
# Import urllib.request so we can call the chat APIs with zero third-party packages.  # Library: urllib.request.
import urllib.request  # Make the urllib.request module available.
# Import urllib.error so HTTP failures can be caught and handled cleanly.  # Library: urllib.error.
import urllib.error  # Make the urllib.error module available.
# Define the OpenRouter chat-completions endpoint (the fallback route).  # Constant: fallback endpoint.
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"  # OpenRouter's chat endpoint, used only when Nightshift is absent.
# Define the Nightshift chat-completions path (OpenAI-compatible, per the flagged assumption).  # Constant: Nightshift chat path.
NIGHTSHIFT_CHAT_PATH = os.environ.get("NIGHTSHIFT_CHAT_PATH", "/chat/completions")  # Override this one value if the workspace documents a different route.
# Define the Nemotron model name used on Nightshift.  # Constant: Nightshift model name.
NIGHTSHIFT_MODEL = os.environ.get("NEMOTRON_MODEL", "nvidia/nemotron-3.5-super-vl")  # The NVIDIA model on the Nightshift side; override without editing code.
# Define the Nemotron model slug used on the OpenRouter fallback route.  # Constant: OpenRouter model slug.
OPENROUTER_MODEL = os.environ.get("NEMOTRON_MODEL_FALLBACK", "nvidia/nemotron-3.5-super-vl:free")  # The verified ARC free-tier seat, fallback only.
# Define how long (in seconds) a model call may take before we give up.  # Constant: HTTP timeout.
HTTP_TIMEOUT_SECONDS = 90  # Reasoning answers can queue on shared sponsor tiers.
# Define a browser-like user agent, because some API edges reject the default Python one.  # Constant: user agent string.
USER_AGENT = "curl/8.0"  # A plain user agent that API edges accept reliably.
# Start the exception type raised when the Nemotron call cannot produce an answer.  # Class: NemotronError.
class NemotronError(Exception):  # Define NemotronError, a plain exception with a message.
    pass  # No extra behavior: it is just a labeled error.
# Start the getter that reads the Nightshift API URL fresh from the environment.  # Function: _nightshift_url.
def _nightshift_url():  # Define _nightshift_url, which returns the Nightshift base URL each time it is called.
    # Read the value live so a .env loaded after import still works.  # Why live: env may load after import.
    return os.environ.get("NIGHTSHIFT_API_URL", "").rstrip("/")  # Empty until the HackOS workspace supplies it.
# Start the getter that reads the Nightshift API key fresh from the environment.  # Function: _nightshift_key.
def _nightshift_key():  # Define _nightshift_key, which returns the Nightshift key or an empty string.
    # Read the value live so a .env loaded after import still works.  # Why live: env may load after import.
    return os.environ.get("NIGHTSHIFT_API_KEY", "")  # The workspace-issued key: NOT the NVIDIA key, which lives in Nightshift's Providers tab.
# Start the getter that reads the OpenRouter key fresh from the environment.  # Function: _openrouter_key.
def _openrouter_key():  # Define _openrouter_key, which returns the OpenRouter key or an empty string.
    # Read the value live so a .env loaded after import still works.  # Why live: env may load after import.
    return os.environ.get("OPENROUTER_API_KEY", "")  # The free-tier key, fallback route only.
# Start the route check: is the Nightshift (primary) route configured?  # Function: nightshift_configured.
def nightshift_configured():  # Define nightshift_configured, which returns True when the URL and key exist.
    # Nightshift is usable whenever its URL and key are both present.  # Rule: both are required.
    return bool(_nightshift_url() and _nightshift_key())  # True only when the workspace credentials are set.
# Start the route check: is the OpenRouter (fallback) route configured?  # Function: openrouter_configured.
def openrouter_configured():  # Define openrouter_configured, which returns True when the key exists.
    # OpenRouter is usable whenever its key is present.  # Rule: key presence is the only requirement.
    return bool(_openrouter_key())  # True when OPENROUTER_API_KEY is set and non-empty.
# Start the route selector: which provider serves the next call?  # Function: get_provider.
def get_provider():  # Define get_provider, which returns "nightshift", "openrouter", or None.
    # Nightshift wins whenever it is configured: the DGX Spark rule requires it.  # Rule: primary route first.
    if nightshift_configured():  # Check the primary route.
        return "nightshift"  # The sponsor-required route.
    # OpenRouter is the fallback that keeps the demo alive without sponsor keys.  # Rule: fallback second.
    if openrouter_configured():  # Check the fallback route.
        return "openrouter"  # The verified free-tier seat.
    # Neither route is configured: the caller must fall back to the offline engine.  # Rule: no route.
    return None  # No model route is available.
# Start the model-name selector: which model string goes with the active provider?  # Function: get_model.
def get_model():  # Define get_model, which returns the model name for the active route.
    # Match the model name to whichever route get_provider picked.  # Rule: model follows the route.
    if get_provider() == "nightshift":  # Check whether the primary route is active.
        return NIGHTSHIFT_MODEL  # The Nemotron build on the Nightshift side.
    return OPENROUTER_MODEL  # The OpenRouter free-tier slug otherwise.
# Start the shared POST helper: send one OpenAI-style chat request and return the reply text.  # Function: _post_chat.
def _post_chat(url, api_key, model, prompt, system, max_tokens, referer=None):  # Define _post_chat with the endpoint, key, model, and messages.
    # Build the message list for the chat-completions request.  # Step: assemble messages.
    messages = []  # Start with an empty message list.
    # Put the system prompt first when one was given.  # Step: optional system message.
    if system:  # Check whether a system prompt was provided.
        messages.append({"role": "system", "content": system})  # System instructions lead the conversation.
    # Add the user prompt as the final message.  # Step: user message.
    messages.append({"role": "user", "content": prompt})  # The task the model must answer.
    # Build the JSON payload for the chat-completions request.  # Step: build the request body.
    payload = {"model": model, "messages": messages, "temperature": 0.4, "max_tokens": max_tokens}  # Low temperature for steady, coach-like answers.
    # Encode the payload as UTF-8 JSON bytes.  # Step: serialize the body.
    body = json.dumps(payload).encode("utf-8")  # Convert the dictionary into bytes.
    # Build the HTTP request object with the endpoint, body, and headers.  # Step: build the request.
    request = urllib.request.Request(url, data=body, method="POST")  # A POST request to the chat endpoint.
    # Add the JSON content-type header.  # Step: header 1 of 4.
    request.add_header("Content-Type", "application/json")  # Tell the endpoint we are sending JSON.
    # Add the bearer authorization header with the API key.  # Step: header 2 of 4.
    request.add_header("Authorization", "Bearer " + api_key)  # Authenticate with the route's key.
    # Add the user-agent header so strict API edges accept the call.  # Step: header 3 of 4.
    request.add_header("User-Agent", USER_AGENT)  # Use the plain user agent defined above.
    # Add the referer header when one was given (OpenRouter attribution; harmless elsewhere).  # Step: header 4 of 4.
    if referer:  # Check whether a referer was provided.
        request.add_header("HTTP-Referer", referer)  # The public repo judges can inspect.
    # Send the request and read the response, giving up after the timeout.  # Step: perform the HTTP call.
    try:  # Begin the guarded network block.
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:  # Open the connection and auto-close it.
            # Decode the response body and parse it as JSON.  # Step: parse the response envelope.
            envelope = json.loads(response.read().decode("utf-8"))  # The chat endpoint's response object.
    # Turn network and HTTP failures into our own clear error type.  # Handler: request failure.
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as err:  # Catch the expected failure modes.
        raise NemotronError("Nemotron request failed: " + str(err))  # Wrap the cause in our error type.
    # Pull the assistant message text out of the first choice.  # Step: extract the reply text.
    try:  # Begin the guarded extraction.
        return envelope["choices"][0]["message"]["content"]  # Return the raw model output.
    # Turn a malformed response into our own clear error type.  # Handler: bad response shape.
    except (KeyError, IndexError, TypeError) as err:  # Catch missing-field failures.
        raise NemotronError("Nemotron returned an unexpected response shape: " + str(err))  # Wrap the cause in our error type.
# Start the main chat call: send the prompt to Nemotron through Nightshift (or the fallback) and return its reply.  # Function: chat.
def chat(prompt, system=None, max_tokens=1200):  # Define chat with a user prompt, optional system prompt, and token cap.
    # Pick the route: Nightshift first, OpenRouter fallback, error when neither is configured.  # Step: route the call.
    provider = get_provider()  # The active route for this call.
    # Refuse clearly when no route is configured, so callers can fall back.  # Guard: no route.
    if provider is None:  # Neither Nightshift nor OpenRouter has a key.
        raise NemotronError("No Nemotron route is configured: set NIGHTSHIFT_API_URL + NIGHTSHIFT_API_KEY, or OPENROUTER_API_KEY for the fallback.")  # Tell the caller exactly what is wrong.
    # Call the Nightshift chat endpoint when it is the active route.  # Branch: primary route.
    if provider == "nightshift":  # Check whether the primary route is active.
        return _post_chat(_nightshift_url() + NIGHTSHIFT_CHAT_PATH, _nightshift_key(), NIGHTSHIFT_MODEL, prompt, system, max_tokens)  # NVIDIA serves Nemotron server-side; its key is in the Providers tab.
    # Call OpenRouter when it is the active fallback route.  # Branch: fallback route.
    return _post_chat(OPENROUTER_URL, _openrouter_key(), OPENROUTER_MODEL, prompt, system, max_tokens, referer="https://github.com/dcain2336/quizforge")  # The verified free-tier seat.
# Backwards-compatible alias: older code called is_configured() for the OpenRouter route.  # Alias note: keeps old callers working.
def is_configured():  # Define is_configured, kept for compatibility.
    # Report whether ANY route is available.  # Rule: any configured route counts.
    return get_provider() is not None  # True when Nightshift or OpenRouter is configured.

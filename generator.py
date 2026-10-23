# generator.py - the QuizForge question-generation engine.  # Module header: what this file is.
# Written from scratch on 2026-10-22 for the Build With AI: Basics hackathon entry.  # Provenance note: fresh code, per the contest's empty-folder rule.
# This module turns raw study text into a study guide, quiz questions, and an answer key.  # Purpose line 1 of 2.
# It tries a free-tier LLM first (Groq), then a second free provider (OpenRouter), then a local heuristic engine.  # Purpose line 2 of 2: the fallback chain.
# The heuristic engine needs no network and no API key, so the demo always works.  # Design guarantee: offline-safe.
# Import the JSON module so we can encode and decode structured data.  # Library: json.
import json  # Make the json module available.
# Import the OS module so we can read API keys from environment variables.  # Library: os.
import os  # Make the os module available.
# Import the random module so we can shuffle options and sample sentences.  # Library: random.
import random  # Make the random module available.
# Import the regular-expression module so we can split text and find key terms.  # Library: re.
import re  # Make the re module available.
# Import urllib.request so we can call LLM APIs with zero third-party packages.  # Library: urllib.request.
import urllib.request  # Make the urllib.request module available.
# Import urllib.error so HTTP failures can be caught and handled cleanly.  # Library: urllib.error.
import urllib.error  # Make the urllib.error module available.
# Define the maximum number of study-text characters we will send to a model or scan locally.  # Constant: input size cap.
MAX_TEXT_CHARS = 12000  # Cap input at 12000 characters to stay inside free-tier token limits.
# Define the Groq chat-completions endpoint (OpenAI-compatible, free tier).  # Constant: Groq endpoint URL.
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"  # Groq's OpenAI-compatible chat endpoint.
# Define the default Groq model: a large open model served on the free tier.  # Constant: Groq model name.
GROQ_MODEL = "openai/gpt-oss-120b"  # GPT-OSS 120B on Groq's free tier (verified live 2026-10-22; the older Llama slug had been retired upstream).
# Define the OpenRouter chat-completions endpoint (free models available).  # Constant: OpenRouter endpoint URL.
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"  # OpenRouter's chat endpoint.
# Define the default OpenRouter model slug: a free-tier model.  # Constant: OpenRouter model name.
OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct:free"  # Free Llama 3.3 70B route on OpenRouter.
# Define how long (in seconds) an LLM call may take before we give up and fall back.  # Constant: HTTP timeout.
HTTP_TIMEOUT_SECONDS = 45  # 45 seconds is generous for a short quiz-generation call.
# Define a browser-like user agent, because some API edges reject the default Python one.  # Constant: user agent string.
USER_AGENT = "curl/8.0"  # A plain user agent that API edges accept reliably.
# Define words that look capitalized but are not useful study terms.  # Constant: term stop-list.
TERM_STOPLIST = {"The", "This", "That", "These", "Those", "When", "While", "Below", "Above", "First", "Next", "Used", "Use", "Work", "Page", "Note", "Normal"}  # Sentence-starters, layout words, and generic adjectives to exclude from key terms.
# Start the helper that loads a local .env file (if one exists) into the process environment.  # Function: load_dotenv.
def load_dotenv():  # Define load_dotenv, which reads KEY=VALUE lines from a .env file beside this module.
    # Build the path of the .env file that sits next to this module.  # Step: locate the .env file.
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")  # Absolute path to the project-local .env file.
    # If there is no .env file, there is nothing to load, so stop here.  # Guard: missing file is fine.
    if not os.path.exists(env_path):  # Check whether the .env file exists.
        return  # Exit quietly when no .env file is present.
    # Open the .env file for reading.  # Step: open the file.
    with open(env_path, "r", encoding="utf-8") as handle:  # Open with UTF-8 decoding and auto-close afterwards.
        # Walk through the file one line at a time.  # Loop: each line of the file.
        for raw_line in handle:  # Iterate over every line in the .env file.
            # Strip surrounding whitespace from the line.  # Step: tidy the line.
            line = raw_line.strip()  # Remove leading and trailing whitespace.
            # Skip blank lines and comment lines.  # Guard: ignore non-settings lines.
            if not line or line.startswith("#") or "=" not in line:  # A usable line is non-empty, not a comment, and contains an equals sign.
                continue  # Move on to the next line.
            # Split the line into a key and a value at the first equals sign.  # Step: split key from value.
            key, _, value = line.partition("=")  # Partition returns key, separator, and value.
            # Store the pair only if the variable is not already set in the real environment.  # Rule: real environment wins over the file.
            os.environ.setdefault(key.strip(), value.strip().strip('"'))  # Set the variable if absent, trimming quotes from the value.
# Start the helper that normalizes raw user text before generation.  # Function: clean_text.
def clean_text(text):  # Define clean_text, which tidies whitespace and enforces the size cap.
    # Replace every run of whitespace (spaces, tabs, newlines) with a single space.  # Step: flatten whitespace.
    flattened = re.sub(r"\s+", " ", text or "")  # Collapse all whitespace runs into single spaces.
    # Trim the ends and cut the text down to the maximum allowed length.  # Step: trim and cap.
    return flattened.strip()[:MAX_TEXT_CHARS]  # Return the cleaned, capped text.
# Start the helper that breaks cleaned text into sentence-like study units.  # Function: split_units.
def split_units(text):  # Define split_units, which returns a list of sentence-sized strings.
    # Split the text after sentence-ending punctuation followed by a space.  # Step: sentence split.
    parts = re.split(r"(?<=[.!?])\s+", text)  # Split on the space that follows ., !, or ?.
    # Keep only units long enough to carry a real fact (at least 40 characters).  # Filter: drop fragments and headings.
    units = [part.strip() for part in parts if len(part.strip()) >= 40]  # Build the list of usable units.
    # Return the usable units to the caller.  # Step: hand back the result.
    return units  # Return the list of study units.
# Start the helper that finds the most important terms in the study text.  # Function: extract_key_terms.
def extract_key_terms(text, limit=14):  # Define extract_key_terms, which ranks candidate terms by frequency.
    # Create a counter dictionary for candidate terms.  # Step: prepare the counter.
    counts = {}  # Map each candidate term to how often it appears.
    # Find acronym terms: two or more capital letters in a row, optionally joined by hyphens (e.g. DCAP-BTLS).  # Step: find acronyms.
    for match in re.findall(r"\b[A-Z]{2,}(?:-[A-Z]{2,})*\b", text):  # Iterate over every acronym-looking token.
        counts[match] = counts.get(match, 0) + 1  # Add one to that acronym's count.
    # Find capitalized phrases of one to three words (e.g. "Scene Safety" or "SpO2"-style names).  # Step: find capitalized phrases.
    for match in re.findall(r"\b(?:[A-Z][a-z]{2,}|SpO2)(?:\s+(?:[A-Z][a-z]{2,}))?\b", text):  # Iterate over capitalized word sequences.
        # Skip phrases that are just sentence-starters or layout words.  # Guard: stop-list filter.
        if match in TERM_STOPLIST:  # Check the phrase against the stop-list.
            continue  # Do not count stop-list phrases.
        counts[match] = counts.get(match, 0) + 1  # Add one to that phrase's count.
    # Sort the terms by frequency, most frequent first.  # Step: rank the terms.
    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)  # Sort (term, count) pairs by count descending.
    # Keep only terms that appear at least twice, up to the requested limit.  # Filter: repeated terms are the real concepts.
    terms = [term for term, count in ranked if count >= 2][:limit]  # Take the top repeated terms.
    # If too few repeated terms exist, top the list up with single-appearance terms.  # Fallback: sparse texts still need terms.
    if len(terms) < 5:  # Check whether we have fewer than five terms.
        # Walk the ranked list again and add terms we have not already included.  # Loop: backfill terms.
        for term, _count in ranked:  # Iterate over every ranked term.
            # Stop as soon as we have enough terms.  # Guard: limit reached.
            if len(terms) >= limit:  # Check the running total against the limit.
                break  # Leave the loop once the list is full.
            # Add the term if it is new to the list.  # Guard: no duplicates.
            if term not in terms:  # Check for duplicates before appending.
                terms.append(term)  # Append the backfill term.
    # Return the final ranked term list.  # Step: hand back the result.
    return terms  # Return the key terms.
# Start the local heuristic generator: the offline engine that needs no API key.  # Function: heuristic_generate.
def heuristic_generate(text, num_mc, num_short):  # Define heuristic_generate, which builds a quiz from text patterns alone.
    # Break the text into sentence-sized study units.  # Step: get study units.
    units = split_units(text)  # Sentence-like chunks of the material.
    # Extract the ranked key terms from the whole text.  # Step: get key terms.
    terms = extract_key_terms(text)  # The concepts the quiz should revolve around.
    # If we somehow have no terms, we cannot build meaningful questions, so return empty lists.  # Guard: no terms, no quiz.
    if not terms or not units:  # Check for the degenerate case.
        return [], []  # Return empty guide and question lists.
    # Build the study guide: for each top term, find the first unit that explains it.  # Step: build the guide.
    guide = []  # Start with an empty guide list.
    # Walk the top eight terms for the guide.  # Loop: guide terms.
    for term in terms[:8]:  # Take at most eight guide entries.
        # Find the first study unit that mentions this term.  # Step: locate the defining sentence.
        defining = next((unit for unit in units if term in unit), None)  # First unit containing the term, or None.
        # Only add the guide entry when a defining sentence exists.  # Guard: skip orphan terms.
        if defining:  # Check that we found a sentence for the term.
            guide.append({"term": term, "point": defining})  # Add the term and its source sentence to the guide.
    # Prepare the lists and bookkeeping for question building.  # Step: prepare question state.
    questions = []  # Start with an empty question list.
    used_units = set()  # Remember which units already became questions, to avoid repeats.
    # Shuffle a copy of the units so questions are not always drawn from the top of the text.  # Step: randomize unit order.
    shuffled_units = units[:]  # Copy the unit list so the original order survives.
    random.shuffle(shuffled_units)  # Shuffle the copy in place.
    # Build the multiple-choice questions first.  # Step: build MC questions.
    for unit in shuffled_units:  # Walk units looking for ones that contain a key term.
        # Stop once we have built the requested number of MC questions.  # Guard: quota reached.
        if len([q for q in questions if q["type"] == "mcq"]) >= num_mc:  # Count MC questions built so far.
            break  # Leave the loop when the MC quota is full.
        # Find the key terms that appear inside this unit.  # Step: terms present in this unit.
        present = [term for term in terms if term in unit]  # Terms that occur in the current unit.
        # Skip units with no key term, and skip units already used.  # Guard: unusable unit.
        if not present or unit in used_units:  # A unit must contain a term and be unused.
            continue  # Move on to the next unit.
        # Choose the first present term as the blanked answer.  # Step: pick the answer term.
        answer_term = present[0]  # The term that will be removed from the sentence.
        # Build the question stem by replacing the term with a blank.  # Step: make the cloze stem.
        stem = unit.replace(answer_term, "_____", 1)  # Replace only the first occurrence of the term.
        # Pick three distractor terms that are not the answer.  # Step: choose distractors.
        distractors = random.sample([term for term in terms if term != answer_term], k=min(3, len(terms) - 1))  # Sample up to three wrong options.
        # If we cannot offer at least two wrong options, the question is too weak, so skip it.  # Guard: minimum option quality.
        if len(distractors) < 2:  # Check the distractor count.
            continue  # Move on to the next unit.
        # Combine the answer and distractors, then shuffle them into display order.  # Step: assemble options.
        options = distractors + [answer_term]  # Start with distractors, then add the correct term.
        random.shuffle(options)  # Shuffle so the correct answer is not always last.
        # Record where the correct answer landed after shuffling.  # Step: find the answer index.
        answer_index = options.index(answer_term)  # Position of the correct option.
        # Append the finished multiple-choice question.  # Step: store the MC question.
        questions.append({"type": "mcq", "question": "Which term best completes this statement from the study material? \"" + stem + "\"", "options": options, "answer_index": answer_index, "answer": answer_term, "topic": answer_term, "explanation": "Full statement: " + unit})  # Store the question with its key and explanation.
        # Mark this unit as used so it does not reappear as another question.  # Step: bookkeeping.
        used_units.add(unit)  # Add the unit to the used set.
    # Build the short-answer (fill-in-the-blank, no options shown) questions next.  # Step: build short-answer questions.
    for unit in shuffled_units:  # Walk the units again for fresh material.
        # Stop once we have built the requested number of short-answer questions.  # Guard: quota reached.
        if len([q for q in questions if q["type"] == "short"]) >= num_short:  # Count short-answer questions built so far.
            break  # Leave the loop when the short-answer quota is full.
        # Skip units already used by the MC questions.  # Guard: no repeats.
        if unit in used_units:  # Check the used set.
            continue  # Move on to the next unit.
        # Find the key terms that appear inside this unit.  # Step: terms present in this unit.
        present = [term for term in terms if term in unit]  # Terms that occur in the current unit.
        # Skip units that contain no key term.  # Guard: unusable unit.
        if not present:  # A short-answer question needs a term to blank out.
            continue  # Move on to the next unit.
        # Choose the first present term as the expected answer.  # Step: pick the answer term.
        answer_term = present[0]  # The term the learner must supply.
        # Build the fill-in-the-blank prompt from the unit.  # Step: make the cloze prompt.
        stem = unit.replace(answer_term, "_____", 1)  # Replace only the first occurrence of the term.
        # Append the finished short-answer question.  # Step: store the short-answer question.
        questions.append({"type": "short", "question": "Fill in the blank: \"" + stem + "\"", "options": [], "answer_index": -1, "answer": answer_term, "topic": answer_term, "explanation": "Full statement: " + unit})  # Store the question with its expected answer.
        # Mark this unit as used.  # Step: bookkeeping.
        used_units.add(unit)  # Add the unit to the used set.
    # Return the guide and the questions to the caller.  # Step: hand back the result.
    return guide, questions  # Return both lists.
# Start the helper that builds the instruction prompt sent to an LLM.  # Function: build_prompt.
def build_prompt(text, num_mc, num_short):  # Define build_prompt, which formats the generation instructions.
    # Assemble the prompt from fixed instructions plus the user's study text.  # Step: compose the prompt.
    prompt = (  # Open the multi-part string that becomes the prompt.
        "You are QuizForge, an expert study coach. Read the study material below and produce a JSON object only, "  # Instruction part 1: role and output format.
        "with no markdown fences and no commentary. The JSON object must have two keys: "  # Instruction part 2: the required shape.
        "\"guide\": a list of up to 8 objects {\"term\": string, \"point\": string} summarizing the key concepts; "  # Instruction part 3: the guide shape.
        "\"questions\": a list with exactly " + str(num_mc) + " multiple-choice objects and " + str(num_short) + " short-answer objects. "  # Instruction part 4: the question counts.
        "A multiple-choice object is {\"type\": \"mcq\", \"question\": string, \"options\": [4 strings], \"answer_index\": integer 0-3, \"topic\": string, \"explanation\": string}. "  # Instruction part 5: the MC shape.
        "A short-answer object is {\"type\": \"short\", \"question\": string, \"answer\": string, \"topic\": string, \"explanation\": string}. "  # Instruction part 6: the short-answer shape.
        "Questions must be answerable from the material alone, distractors must be plausible, and topics must be short concept labels.\n\nSTUDY MATERIAL:\n" + text  # Instruction part 7: quality rules, then the material itself.
    )  # Close the multi-part prompt string.
    # Return the finished prompt.  # Step: hand back the prompt.
    return prompt  # Return the prompt string.
# Start the helper that performs one chat-completion call against an OpenAI-compatible endpoint.  # Function: call_chat_api.
def call_chat_api(url, api_key, model, prompt):  # Define call_chat_api, which returns the model's text reply.
    # Build the JSON payload for the chat-completions request.  # Step: build the request body.
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.4, "response_format": {"type": "json_object"}}  # Ask for a single user-message completion with JSON output.
    # Encode the payload as UTF-8 JSON bytes.  # Step: serialize the body.
    body = json.dumps(payload).encode("utf-8")  # Convert the dictionary into bytes.
    # Build the HTTP request object with the endpoint, body, and headers.  # Step: build the request.
    request = urllib.request.Request(url, data=body, method="POST")  # A POST request to the provider endpoint.
    # Add the JSON content-type header.  # Step: header 1 of 3.
    request.add_header("Content-Type", "application/json")  # Tell the provider we are sending JSON.
    # Add the bearer authorization header with the API key.  # Step: header 2 of 3.
    request.add_header("Authorization", "Bearer " + api_key)  # Authenticate with the provider key.
    # Add the user-agent header so strict API edges accept the call.  # Step: header 3 of 3.
    request.add_header("User-Agent", USER_AGENT)  # Use the plain user agent defined above.
    # Send the request and read the response, giving up after the timeout.  # Step: perform the HTTP call.
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:  # Open the connection and auto-close it.
        # Decode the response body and parse it as JSON.  # Step: parse the response envelope.
        envelope = json.loads(response.read().decode("utf-8"))  # The provider's response object.
    # Pull the assistant message text out of the first choice.  # Step: extract the reply text.
    return envelope["choices"][0]["message"]["content"]  # Return the raw model output.
# Start the helper that extracts and validates the JSON quiz from raw model output.  # Function: parse_llm_json.
def parse_llm_json(raw_text):  # Define parse_llm_json, which returns (guide, questions) or raises ValueError.
    # Find the first opening brace and the last closing brace, in case the model added stray text.  # Step: locate the JSON span.
    start = raw_text.find("{")  # Index of the first opening brace.
    end = raw_text.rfind("}")  # Index of the last closing brace.
    # If no JSON span exists, the output is unusable.  # Guard: no braces found.
    if start == -1 or end == -1:  # Both braces must exist.
        raise ValueError("Model output contained no JSON object")  # Signal failure so the caller falls back.
    # Parse the located span as JSON.  # Step: parse the object.
    data = json.loads(raw_text[start:end + 1])  # Convert the span into a Python dictionary.
    # Read the guide and question lists, defaulting to empty lists when absent.  # Step: pull the two lists.
    guide = data.get("guide", [])  # The study-guide entries.
    questions = data.get("questions", [])  # The generated questions.
    # Validate every question and rebuild it in our canonical shape.  # Step: normalize questions.
    cleaned = []  # Start with an empty list of validated questions.
    # Walk each raw question from the model.  # Loop: raw questions.
    for raw_q in questions:  # Iterate over the model's questions.
        # Read the question type, defaulting to multiple choice.  # Step: read the type.
        qtype = raw_q.get("type", "mcq")  # Either "mcq" or "short".
        # Handle multiple-choice questions, which need options and a valid answer index.  # Branch: MC validation.
        if qtype == "mcq":  # Check the type.
            # Read the option list, defaulting to empty.  # Step: read options.
            options = raw_q.get("options", [])  # The four answer choices.
            # Read the answer index, defaulting to an invalid value.  # Step: read answer index.
            answer_index = raw_q.get("answer_index", -1)  # Which option is correct.
            # Skip malformed MC questions instead of failing the whole quiz.  # Guard: shape check.
            if len(options) != 4 or not (0 <= answer_index < 4) or not raw_q.get("question"):  # Require 4 options, a valid index, and a stem.
                continue  # Drop this question and keep the rest.
            # Append the normalized MC question.  # Step: store the MC question.
            cleaned.append({"type": "mcq", "question": raw_q["question"], "options": options, "answer_index": answer_index, "answer": options[answer_index], "topic": raw_q.get("topic", "General"), "explanation": raw_q.get("explanation", "")})  # Store the canonical MC shape.
        # Handle short-answer questions, which need an expected answer.  # Branch: short-answer validation.
        elif qtype == "short" and raw_q.get("question") and raw_q.get("answer"):  # Require a prompt and an answer.
            # Append the normalized short-answer question.  # Step: store the short-answer question.
            cleaned.append({"type": "short", "question": raw_q["question"], "options": [], "answer_index": -1, "answer": raw_q["answer"], "topic": raw_q.get("topic", "General"), "explanation": raw_q.get("explanation", "")})  # Store the canonical short-answer shape.
    # A usable quiz needs at least three questions; anything less means the model failed us.  # Guard: minimum quiz size.
    if len(cleaned) < 3:  # Check the validated count.
        raise ValueError("Model produced too few valid questions")  # Signal failure so the caller falls back.
    # Normalize the guide into our canonical shape, keeping at most eight entries.  # Step: normalize the guide.
    clean_guide = [{"term": str(entry.get("term", "")), "point": str(entry.get("point", ""))} for entry in guide[:8] if entry.get("term")]  # Keep entries that have a term.
    # Return the validated guide and questions.  # Step: hand back the result.
    return clean_guide, cleaned  # Return both lists.
# Start the public entry point that the web server calls.  # Function: generate.
def generate(text, total_questions=8):  # Define generate, which returns the full quiz package dictionary.
    # Load any project-local .env file so API keys are available.  # Step: load local keys.
    load_dotenv()  # Read the .env file if one exists.
    # Clean and cap the incoming study text.  # Step: normalize input.
    cleaned_text = clean_text(text)  # Whitespace-flattened, length-capped text.
    # Refuse to generate from text that is too short to contain real facts.  # Guard: minimum input size.
    if len(cleaned_text) < 200:  # Fewer than 200 characters cannot support a fair quiz.
        raise ValueError("Study material is too short - paste at least a few paragraphs (200+ characters).")  # Tell the user what to fix.
    # Split the requested total into multiple-choice and short-answer counts.  # Step: plan the question mix.
    num_mc = max(1, round(total_questions * 0.6))  # About sixty percent multiple choice.
    num_short = max(1, total_questions - num_mc)  # The remainder are short answer.
    # Build the provider attempt list: (display name, url, key, model) for each configured free provider.  # Step: assemble providers.
    providers = []  # Start with no providers.
    # Add Groq first when its key is configured.  # Provider 1: Groq free tier.
    if os.environ.get("GROQ_API_KEY"):  # Check for the Groq key.
        providers.append(("groq", GROQ_URL, os.environ["GROQ_API_KEY"], GROQ_MODEL))  # Queue the Groq attempt.
    # Add OpenRouter second when its key is configured.  # Provider 2: OpenRouter free models.
    if os.environ.get("OPENROUTER_API_KEY"):  # Check for the OpenRouter key.
        providers.append(("openrouter", OPENROUTER_URL, os.environ["OPENROUTER_API_KEY"], OPENROUTER_MODEL))  # Queue the OpenRouter attempt.
    # Try each configured provider in order until one returns a valid quiz.  # Loop: provider attempts.
    for name, url, key, model in providers:  # Iterate over the queued providers.
        # Guard the attempt so any failure simply moves us to the next option.  # Step: protected attempt.
        try:  # Begin the try block for this provider.
            # Build the instruction prompt for this attempt.  # Step: build the prompt.
            prompt = build_prompt(cleaned_text, num_mc, num_short)  # The full instruction plus material.
            # Call the provider and capture its raw reply.  # Step: call the model.
            raw_reply = call_chat_api(url, key, model, prompt)  # The model's text output.
            # Parse and validate the reply into our canonical shape.  # Step: validate the output.
            guide, questions = parse_llm_json(raw_reply)  # Raises ValueError when the output is unusable.
            # Return the successful package, labeled with the provider that made it.  # Step: success return.
            return {"source": "llm:" + name, "guide": guide, "questions": questions}  # The finished quiz package.
        # Any network, HTTP, or validation error means: fall through to the next option.  # Handler: provider failure.
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError, TimeoutError) as _err:  # Catch the expected failure modes.
            continue  # Move on to the next provider, or to the heuristic engine below.
    # No provider worked (or none was configured): run the local heuristic engine.  # Step: offline fallback.
    guide, questions = heuristic_generate(cleaned_text, num_mc, num_short)  # Build the quiz from text patterns alone.
    # If even the heuristic engine produced nothing, the text is unusable for quizzing.  # Guard: empty fallback result.
    if not questions:  # Check for an empty question list.
        raise ValueError("Could not find enough key concepts in that text - try denser study material with clear facts and definitions.")  # Explain the problem honestly.
    # Return the heuristic package, labeled so the UI can show which engine ran.  # Step: fallback return.
    return {"source": "heuristic", "guide": guide, "questions": questions}  # The finished quiz package.

# markovian.py - the Meterless Markovian Engine, ported to stdlib Python for QuizForge Live.  # Module header: what this file is.
# PROVENANCE: this is a faithful reimplementation of the Meterless Markovian Engine  # Provenance 1: the upstream project.
# (github.com/Meterless/Meterless, folder engines/markovian), licensed Apache-2.0.  # Provenance 2: repo, folder, and license.
# Upstream does NOT ship a runtime library: its own docs say the engine is "an AGENTS.md-driven  # Provenance 3: why a port is the intended integration path.
# implementation spec, not a runtime library", and implementers build it in their own stack.  # Provenance 3 continued: the implement-in-your-stack instruction.
# This port follows the upstream TypeScript reference implementation (engines/markovian/reference/src)  # Provenance 4: the conformance guide for this port.
# file by file: types.ts (config + estimator), markers.ts (marker protocol), carryover.ts  # Provenance 4 continued: the reference files mirrored here.
# (compression cascade), promptBuilder.ts (step prompts), configManager.ts (efficiency math).  # Provenance 4 continued: the remaining reference files.
# WHAT THE ENGINE DOES: long agent chains normally re-read their whole history every step, so cost  # Purpose 1: the problem the engine solves.
# grows quadratically. Markovian bounds each step to the goal plus a COMPRESSED CARRYOVER STATE,  # Purpose 2: bounded state instead of full history.
# so per-step context stays flat (O(1) per step) no matter how long the chain runs.  # Purpose 2 continued: the flat-cost property.
# HOW QUIZFORGE LIVE USES IT: every study round is one chunk in the chain. The learner's graded  # Purpose 3: the study-loop mapping.
# history is folded into the canonical state block (COMPLETED / REMAINING / DECISIONS / CONTEXT),  # Purpose 3 continued: history becomes state, not prompt bulk.
# compressed through the cascade to the carryover budget, and that bounded state - never the raw  # Purpose 3 continued: the budget is enforced by the cascade.
# history - is what the planner sees next round. Missed topics sit in REMAINING until mastered.  # Purpose 3 continued: misses resurface until fixed.
# ADAPTATIONS FROM UPSTREAM (honest list): TypeScript async becomes plain synchronous Python;  # Adaptation 1: sync instead of async.
# the compressor is any callable (prompt, system) -> text; the History/Progress services are not  # Adaptation 2: the injected compressor contract.
# ported (this app is stateless per request; run evidence lives in meterless.py's JSONL logs).  # Adaptation 3: no history service, by design.
# Zero third-party dependencies: Python standard library only, like the rest of this project.  # Design choice: no installs needed.
# Import the math module for the ceiling used by the token estimator.  # Library: math.
import math  # Make the math module available.
# Import the re module for the marker protocol and the heuristic phrase extractor.  # Library: re.
import re  # Make the re module available.
# Define the upstream default chunk configuration (types.ts DEFAULT_CONFIG).  # Constant: default config.
DEFAULT_CONFIG = {"chunk_size": 8000, "max_chunks": 24, "carryover_tokens": 800, "overlap_tokens": 0}  # Target generation budget, recursion cap, carryover budget, overlap window.
# Define the upstream validation bounds for every config key (types.ts BOUNDS).  # Constant: config bounds.
BOUNDS = {"chunk_size": (1000, 128000), "max_chunks": (1, 32), "carryover_tokens": (128, 32768), "overlap_tokens": (0, 4096)}  # (min, max) per key; upstream "step" values are UI slider granularity, not validation.
# Define the upstream framing constants used by the config sanity rule (types.ts).  # Constants: framing + output budget.
FRAMING_TOKENS = 400  # Tokens reserved for prompt framing in every chunk.
OUTPUT_BUDGET = 1200  # Tokens reserved for a chunk's own output.
# Start the exception type raised when a config value is invalid (upstream ConfigValidationError).  # Class: ConfigValidationError.
class ConfigValidationError(Exception):  # Define ConfigValidationError, a plain exception with a message.
    pass  # No extra behavior: it is just a labeled error, like upstream.
# Start the reference token estimator: ceil(chars / 4), labeled "estimated" everywhere upstream.  # Function: estimate_tokens.
def estimate_tokens(text):  # Define estimate_tokens, which approximates a token count from raw text.
    # Count characters and divide by four, rounding up (upstream: Math.ceil(text.length / 4)).  # Rule: the chars-per-token heuristic.
    return math.ceil(len(text) / 4)  # Provider-reported usage would be "measured"; this is always "estimated".
# Start the config resolver: merge a partial config over the defaults and validate it (configManager.ts).  # Function: resolve_config.
def resolve_config(partial=None):  # Define resolve_config, which returns a complete validated config dict.
    # Start from the upstream defaults, then overlay any caller-supplied values.  # Step: merge the config.
    config = dict(DEFAULT_CONFIG)  # A copy so callers can never mutate the module defaults.
    # Apply the overlay when the caller passed one.  # Step: apply overrides.
    if partial:  # Check whether overrides were given.
        config.update(partial)  # Caller values win over the defaults.
    # Validate every known key against its upstream bounds; nothing is silently clamped.  # Step: bounds validation.
    for key in ("chunk_size", "max_chunks", "carryover_tokens", "overlap_tokens"):  # The four config keys upstream validates.
        # Read this key's value and its (min, max) bounds.  # Step: read the pair.
        value = config[key]  # The candidate value for this key.
        low, high = BOUNDS[key]  # The allowed range for this key.
        # Reject non-numeric values with the typed error, exactly like upstream.  # Guard: numeric check.
        if not isinstance(value, (int, float)) or isinstance(value, bool):  # Booleans are ints in Python; upstream means real numbers.
            raise ConfigValidationError(key + " must be a number")  # Name the offending key.
        # Reject out-of-range values with the typed error.  # Guard: range check.
        if value < low or value > high:  # Compare against the upstream bounds.
            raise ConfigValidationError(key + "=" + str(value) + " outside [" + str(low) + ", " + str(high) + "]")  # Name the value and the range.
    # Reject a zero or negative carryover budget explicitly (upstream checks this separately).  # Guard: positive carryover.
    if config["carryover_tokens"] <= 0:  # The state budget must leave room for state.
        raise ConfigValidationError("carryover_tokens must be > 0")  # A zero budget would erase the chain's memory.
    # Reject a chunk size that cannot hold framing + carryover + one output (upstream sanity rule).  # Guard: chunk capacity.
    if config["chunk_size"] < FRAMING_TOKENS + config["carryover_tokens"] + OUTPUT_BUDGET:  # The minimum viable chunk.
        raise ConfigValidationError("chunk_size=" + str(config["chunk_size"]) + " < framing(" + str(FRAMING_TOKENS) + ") + carryover(" + str(config["carryover_tokens"]) + ") + outputBudget(" + str(OUTPUT_BUDGET) + ")")  # Show the arithmetic, like upstream.
    # Return the validated config.  # Step: hand back the config.
    return config  # Callers snapshot this per run, as upstream mandates.
# Define the state-block marker patterns (markers.ts STATE_BLOCKS): the <CARRYOVER> block form.  # Constant: state block patterns.
_STATE_BLOCKS = [re.compile(r"<CARRYOVER>([\s\S]*?)</CARRYOVER>")]  # The angle-bracket state block used across upstream examples.
# Define the state-tail marker patterns (markers.ts STATE_TAILS), tried in upstream's order.  # Constant: state tail patterns.
_STATE_TAILS = [re.compile(r"\[STATE_CHECKPOINT\]\s*([\s\S]*)$"), re.compile(r"@@@STATE@@@\s*([\s\S]*)$"), re.compile(r"(?<!_)\[STATE\]\s*([\s\S]*)$"), re.compile(r"---STATE---\s*([\s\S]*)$")]  # Canonical [STATE_CHECKPOINT] first, then the backward-compatible variants.
# Define the final markers (markers.ts FINAL_MARKERS): any one of them ends the chain.  # Constant: final marker patterns.
_FINAL_MARKERS = [re.compile(r"\[TASK_COMPLETE\]"), re.compile(r"@@@FINAL@@@"), re.compile(r"(?<!_)\[FINAL\]"), re.compile(r"---FINAL---"), re.compile(r"<DONE\s*/?>")]  # Canonical [TASK_COMPLETE] plus the accepted variants.
# Define the progress-block pattern (markers.ts PROGRESS_BLOCK).  # Constant: progress pattern.
_PROGRESS_BLOCK = re.compile(r"<PROGRESS>([\s\S]*?)</PROGRESS>")  # An optional progress note inside a chunk.
# Define the needs-tool pattern (markers.ts NEEDS_TOOL): a tool request embedded in a chunk.  # Constant: needs-tool pattern.
_NEEDS_TOOL = re.compile(r"""[<[]NEEDS_TOOL\s+tool="([^"]+)"\s+input=(?:"([^"]*)"|'([^']*)')\s*/?[\]>]""")  # Captures the tool name and its input, either quote style.
# Define the needs-clarification pattern (markers.ts NEEDS_CLARIFICATION).  # Constant: needs-clarification pattern.
_NEEDS_CLARIFICATION = re.compile(r"[<[]NEEDS_CLARIFICATION[\]>]\s*([^\n]*)")  # Captures the rest of the line as the question.
# Start the marker parser: extract state, completion, and tool requests from one chunk (markers.ts).  # Function: parse_markers.
def parse_markers(raw):  # Define parse_markers, which returns the marker fields plus display-safe text.
    # Start with no state found; block forms win over tail forms, last block wins (upstream order).  # Step: find the state.
    state = None  # The captured state text, if any marker carries one.
    # Try the <CARRYOVER> block form first, keeping the LAST block when several appear.  # Step: block form.
    for pattern in _STATE_BLOCKS:  # The block patterns, in upstream order.
        matches = pattern.findall(raw)  # All block captures in this chunk.
        # Keep the last block's content when at least one matched.  # Step: last block wins.
        if matches:  # Check whether any block matched.
            state = matches[-1].strip()  # The freshest state the step emitted.
    # Fall back to the tail forms only when no block form matched.  # Step: tail forms.
    if state is None:  # No <CARRYOVER> block was present.
        # Try each tail pattern in upstream's order and stop at the first hit.  # Loop: tail patterns.
        for pattern in _STATE_TAILS:  # Canonical form first, variants after.
            match = pattern.search(raw)  # Search the chunk for this tail marker.
            # Capture the state text when this pattern hits.  # Step: capture the tail state.
            if match:  # This tail form is present.
                state = match.group(1).strip()  # Everything after the marker is the state.
                break  # First matching tail form wins, like upstream.
    # Detect completion: any final marker anywhere in the chunk ends the chain.  # Step: detect done.
    done = any(pattern.search(raw) for pattern in _FINAL_MARKERS)  # True when a final marker is present.
    # Capture the optional progress note when one is embedded.  # Step: progress note.
    progress_match = _PROGRESS_BLOCK.search(raw)  # Look for a <PROGRESS> block.
    progress = progress_match.group(1).strip() if progress_match else None  # The note text, or None.
    # Capture an embedded tool request when one is present.  # Step: tool request.
    tool_match = _NEEDS_TOOL.search(raw)  # Look for a NEEDS_TOOL marker.
    needs_tool = {"tool": tool_match.group(1), "input": tool_match.group(2) or tool_match.group(3) or ""} if tool_match else None  # Tool name plus input from either quote group.
    # Capture an embedded clarification request when one is present.  # Step: clarification request.
    clarification_match = _NEEDS_CLARIFICATION.search(raw)  # Look for a NEEDS_CLARIFICATION marker.
    needs_clarification = clarification_match.group(1).strip() if clarification_match else None  # The question text, or None.
    # Return every field plus the marker-free display text.  # Step: hand back the parse.
    return {"state": state, "done": done, "progress": progress, "needs_tool": needs_tool, "needs_clarification": needs_clarification, "cleaned": clean_markers(raw)}  # The same shape as upstream's ParsedMarkers.
# Start the marker cleaner: strip every marker form from display text (markers.ts cleanMarkers).  # Function: clean_markers.
def clean_markers(raw):  # Define clean_markers, which returns text safe to show a human.
    # Remove the block forms first, contents and all.  # Step: strip blocks.
    out = re.sub(r"<CARRYOVER>[\s\S]*?</CARRYOVER>", "", raw)  # State blocks are machine-facing, not display text.
    out = re.sub(r"<PROGRESS>[\s\S]*?</PROGRESS>", "", out)  # Progress blocks likewise.
    # Remove tool and clarification markers wherever they appear.  # Step: strip inline markers.
    out = re.sub(r"[<[]NEEDS_TOOL[^\]>]*[\]>]", "", out)  # The whole tool-request marker.
    out = re.sub(r"[<[]NEEDS_CLARIFICATION[\]>][^\n]*", "", out)  # The clarification marker and its line.
    # Remove state tails: everything from a tail marker to the end of the chunk.  # Step: strip state tails.
    out = re.sub(r"\[STATE_CHECKPOINT\][\s\S]*$", "", out)  # The canonical tail.
    out = re.sub(r"@@@STATE@@@[\s\S]*$", "", out)  # The @@@ variant.
    out = re.sub(r"---STATE---[\s\S]*$", "", out)  # The dashes variant.
    # Remove a bare [STATE] tail only at a line start, so prose mentioning [STATE] survives (upstream's caution).  # Step: strip the bare variant carefully.
    out = re.sub(r"\n\[STATE\][\s\S]*$", "", out)  # Only when it starts a marker line.
    # Remove the standalone final markers wherever they appear.  # Step: strip final markers.
    for pattern in (r"\[TASK_COMPLETE\]", r"@@@FINAL@@@", r"---FINAL---", r"<DONE\s*/?>"):  # The non-tail final forms.
        out = re.sub(pattern, "", out)  # Each one is display noise once detected.
    # Remove a bare [FINAL] tail the same careful way.  # Step: strip the bare final tail.
    out = re.sub(r"\n\[FINAL\][\s\S]*$", "", out)  # Only at a line start, like upstream.
    # Tidy what is left: trailing spaces per line, then collapse 3+ newlines to a blank line.  # Step: whitespace tidy.
    out = re.sub(r"[ \t]+$", "", out, flags=re.MULTILINE)  # No trailing spaces on any line.
    out = re.sub(r"\n{3,}", "\n\n", out)  # At most one blank line in a row.
    # Return the cleaned text, trimmed.  # Step: hand back the text.
    return out.strip()  # Display-safe, like upstream's cleaned field.
# Start the canonical state block builder (carryover.ts canonicalBlock): the labeled state format.  # Function: canonical_block.
def canonical_block(completed, remaining, decisions, context):  # Define canonical_block with the four state fields.
    # Join the four labeled lines exactly as upstream formats them.  # Step: format the block.
    return "COMPLETED: " + completed + "\nREMAINING: " + remaining + "\nDECISIONS: " + decisions + "\nCONTEXT: " + context  # The block every compressor level targets.
# Define the heuristic key-phrase pattern (carryover.ts KEY_PHRASE): sentences that carry state.  # Constant: key-phrase pattern.
_KEY_PHRASE = re.compile(r"(?:^|\n|\.\s+)((?:Therefore|Key insight|Status|Decision|Decided|Next|Remaining|Completed)[^.\n]*)", re.IGNORECASE | re.MULTILINE)  # Upstream's state-bearing openers, case-insensitive.
# Define the minimum accepted carryover length (upstream: a state under 24 chars is not a state).  # Constant: minimum state length.
_MIN_STATE_CHARS = 24  # Shorter candidates are rejected at the marker and LLM cascade levels.
# Start the carryover service: compress one chunk into the next step's bounded state (carryover.ts).  # Class: CarryoverService.
class CarryoverService:  # Define CarryoverService, the four-level compression cascade.
    # Store the optional model compressor: any callable (prompt, system) -> text.  # Method: __init__.
    def __init__(self, compressor_fn=None):  # Define the constructor with the optional injected compressor.
        # Keep the compressor for cascade level 2; None means levels 1, 3, 4 only (the offline path).  # Step: store the compressor.
        self._compressor_fn = compressor_fn  # Injected by the caller, exactly like upstream's constructor.
    # Start the cascade: produce the next carryover state for a finished chunk.  # Method: next.
    def next(self, marker_state, previous_carryover, chunk_text, config):  # Define next with the parsed marker state, prior state, chunk text, and config.
        # Read the carryover budget every level must respect.  # Step: read the budget.
        budget = config["carryover_tokens"]  # No level may return state estimated above this.
        # Level 1: explicit marker override - the step's own [STATE_CHECKPOINT] block, when valid.  # Cascade level 1: marker.
        if marker_state is not None:  # The step emitted a state block.
            # Sanitize marker-shaped runs out of the state, exactly like upstream's cleanup.  # Step: sanitize the state.
            sanitized = re.sub(r"[<>\[\]@-]{3,}", "", marker_state).strip()  # Runs of 3+ marker characters are stripped.
            # Accept the marker state when it is long enough and inside the budget.  # Step: validate the marker state.
            if len(sanitized) >= _MIN_STATE_CHARS and estimate_tokens(sanitized) <= budget:  # The upstream acceptance rule.
                return {"carryover": sanitized, "level": "marker"}  # The step's own state wins.
        # Level 2: model compression through the injected compressor, when one was supplied.  # Cascade level 2: llm.
        if self._compressor_fn is not None:  # A model route is available to this run.
            # Compress, letting any failure fall through to the heuristic level (upstream behavior).  # Step: guarded model compression.
            try:  # Begin the guarded compressor block.
                # Build the compression prompt from the previous state and the chunk's tail (upstream prompt).  # Step: build the prompt.
                preview = chunk_text[-2000:]  # The last 2000 chars carry the freshest state.
                prompt = ("Previous state:\n" + (previous_carryover or "(none)") + "\n\nLatest chunk (tail):\n" + preview + "\n\n" + "Compress into 3-5 critical points as a labeled block:\nCOMPLETED: ...\nREMAINING: ...\nDECISIONS: ...\nCONTEXT: ...")  # Upstream's compression prompt, verbatim in shape.
                # Call the compressor with upstream's compressor system prompt.  # Step: call the model.
                compressed = self._compressor_fn(prompt, "You compress reasoning state. Be terse and lossless on decisions.").strip()  # Terse, decision-preserving compression.
                # Accept the model state when it is long enough and inside the budget.  # Step: validate the model state.
                if len(compressed) >= _MIN_STATE_CHARS and estimate_tokens(compressed) <= budget:  # The same acceptance rule as level 1.
                    return {"carryover": compressed, "level": "llm"}  # The model's compressed state.
            # Swallow compressor failures: the cascade must survive model instability (upstream rule).  # Handler: compressor failure.
            except Exception:  # Any compressor error falls through.
                pass  # The heuristic level below still produces a state.
        # Level 3: heuristic extraction of state-bearing phrases from the chunk text.  # Cascade level 3: heuristic.
        phrases = [match.group(1).strip() for match in _KEY_PHRASE.finditer(chunk_text)][:5]  # Up to five key phrases, in order.
        # Join the phrases when any were found and the result fits the budget.  # Step: try the heuristic state.
        if phrases:  # At least one state-bearing phrase exists.
            summary = "; ".join(phrases)  # One compact line of state.
            # Accept the heuristic state when it fits the budget.  # Step: validate the heuristic state.
            if estimate_tokens(summary) <= budget:  # The budget rule applies at every level.
                return {"carryover": summary, "level": "heuristic"}  # Extracted state, no model needed.
        # Level 4: absolute fallback - tail-truncate words to the token budget.  # Cascade level 4: truncation.
        words = (chunk_text or previous_carryover).split()  # Prefer the chunk; fall back to the prior state.
        # Walk the words backwards, keeping the longest tail that still fits the budget.  # Step: build the tail.
        tail = ""  # Start with an empty tail.
        # Add words from the end until the next word would break the budget.  # Loop: tail words.
        for word in reversed(words):  # The newest words are the most state-like.
            candidate = word + (" " + tail if tail else "")  # Prepend this word to the tail.
            # Stop before the candidate exceeds the budget.  # Guard: budget check.
            if estimate_tokens(candidate) > budget:  # One word too many.
                break  # The current tail is the state.
            tail = candidate  # Keep this word and continue.
        # Return the truncated tail; this level guarantees the budget by construction.  # Step: hand back the fallback state.
        return {"carryover": tail, "level": "truncation"}  # The chain always gets a state.
# Define the marker rules appended to every step prompt (promptBuilder.ts MARKER_RULES).  # Constant: marker rules text.
MARKER_RULES = ("End every non-final chunk with [STATE_CHECKPOINT] followed by a concise state block:\n" + "COMPLETED: ...\nREMAINING: ...\nDECISIONS: ...\nCONTEXT: ...\n" + "End the final chunk with [TASK_COMPLETE]. Exactly one marker per chunk. Never narrate the markers.")  # Upstream's marker instructions, verbatim in shape.
# Start the step prompt builder: assemble what one chunk sees (promptBuilder.ts buildPrompt).  # Function: build_prompt.
def build_prompt(mode, goal, step, carryover, overlap_text="", memory_context=None, attachments=None, config=None):  # Define build_prompt with the step's inputs; step is 1-based.
    # Collect the prompt parts in upstream's order.  # Step: assemble the parts.
    parts = []  # Start with an empty part list.
    first = step == 1  # Chunk 1 is special: it gets memory, the full goal, and attachments.
    # Memory context enters chunk 1 only (upstream section 5 rule).  # Step: memory on chunk 1.
    if first and memory_context:  # First chunk with memory supplied.
        parts.append(memory_context.strip())  # The memory block leads the prompt.
        parts.append("")  # A blank separator line.
    # Build the first chunk's framing: mode intro, full goal, attachments.  # Branch: first chunk.
    if first:  # This is the opening chunk.
        # Pick the mode intro line (upstream ships ARCHITECT and RESEARCH modes).  # Step: mode intro.
        if mode == "ARCHITECT":  # The build/plan/implement mode.
            parts.append("You are executing a long build task in bounded chunks. Analyze the goal, produce a plan, and start implementation.")  # Upstream's ARCHITECT intro.
        else:  # The RESEARCH mode: recursive analytical work.
            parts.append("You are executing recursive research in bounded chunks. Log every action as '>> action'. " + "Produce multi-file style output where useful and keep a research-tree state snapshot.")  # Upstream's RESEARCH intro.
        parts.append("")  # A blank separator line.
        parts.append("User Request: " + goal)  # The full goal, only ever sent whole on chunk 1.
        # Attachments ride chunk 1 only, like upstream.  # Step: attachments on chunk 1.
        if attachments:  # The caller supplied attachments.
            parts.append("")  # A blank separator line.
            # Add each attachment as a labeled block.  # Loop: attachments.
            for attachment in attachments:  # Each attachment dict carries name + content.
                parts.append("[ATTACHMENT " + attachment["name"] + "]\n" + attachment["content"])  # The labeled attachment block.
    # Build a continuation chunk's framing: truncated goal + carryover + optional overlap.  # Branch: continuation chunk.
    else:  # Every chunk after the first.
        parts.append("Continuing a chunked " + mode.lower() + " run. Goal (truncated): " + goal[:200])  # ~200 chars of goal: the bounded-context rule.
        parts.append("")  # A blank separator line.
        parts.append("[CARRYOVER STATE]\n" + carryover)  # The compressed state is the chain's memory.
        # Insert the overlap window after the carryover when one was sliced (never silently ignored).  # Step: overlap block.
        if overlap_text:  # overlap_tokens > 0 produced a slice.
            parts.append("")  # A blank separator line.
            parts.append("[OVERLAP]\n" + overlap_text)  # The tail of the previous chunk, verbatim.
        parts.append("")  # A blank separator line.
        parts.append("Continue exactly where the state leaves off. Do not repeat completed work.")  # Upstream's continuation instruction.
    # Append the marker rules to every chunk, first or continuation.  # Step: marker rules.
    parts.append("")  # A blank separator line.
    parts.append(MARKER_RULES)  # The step must end with a state checkpoint or the final marker.
    # Join the parts into the final prompt.  # Step: hand back the prompt.
    return "\n".join(parts)  # One string, ready for any provider.
# Start the overlap slicer: the tail of the previous chunk, sized by the config (promptBuilder.ts).  # Function: overlap_slice.
def overlap_slice(previous_cleaned, config):  # Define overlap_slice with the previous chunk's cleaned text and the config.
    # No overlap when the config disables it or there is no previous chunk.  # Guard: disabled or empty.
    if config["overlap_tokens"] <= 0 or not previous_cleaned:  # The default config disables overlap.
        return ""  # Nothing to overlap.
    # Return the final overlap_tokens*4 characters (chars, per the chars/4 estimator).  # Step: slice the tail.
    return previous_cleaned[-config["overlap_tokens"] * 4:]  # The overlap window upstream defines.
# Start the run efficiency accounting (configManager.ts runEfficiency, upstream section 6.3).  # Function: run_efficiency.
def run_efficiency(chunks, config):  # Define run_efficiency with the chunk token counts and the run's own config snapshot.
    # Total the tokens the chunks actually produced (all "estimated" via the chars/4 rule).  # Step: total used.
    total_used = sum(chunk["tokens"] for chunk in chunks)  # Sum of per-chunk estimated tokens.
    # Replay the naive cost: each chunk re-pays for every chunk before it (quadratic growth).  # Step: naive cost.
    standard_cost = 0  # The full-history price of the same work.
    prefix = 0  # The running sum of earlier chunks' tokens.
    # Walk the chunks, charging each one the whole prefix plus itself.  # Loop: naive accounting.
    for chunk in chunks:  # One charge per chunk.
        standard_cost += prefix + chunk["tokens"]  # This chunk would have re-read everything before it.
        prefix += chunk["tokens"]  # Grow the prefix for the next chunk.
    # Compute the Markovian cost: one carryover budget per chunk plus the chunks themselves.  # Step: bounded cost.
    markovian_cost = len(chunks) * config["carryover_tokens"] + total_used  # Flat per-step state cost, the engine's whole point.
    # Savings are the difference, floored at zero (tiny chains can cost more bounded than naive).  # Step: savings.
    tokens_saved = max(0, standard_cost - markovian_cost)  # Never report negative savings.
    # Efficiency is the saved share of the naive cost, as a percent.  # Step: efficiency percent.
    efficiency_percent = (tokens_saved / standard_cost) * 100 if standard_cost > 0 else 0  # Zero-safe division.
    # Return the full accounting, always computed against the run's own config snapshot (upstream rule).  # Step: hand back the accounting.
    return {"total_tokens_used": total_used, "standard_cost": standard_cost, "markovian_cost": markovian_cost, "tokens_saved": tokens_saved, "efficiency_percent": efficiency_percent}  # The section-6 numbers for one run.
# Start the projected efficiency curve (configManager.ts projectionCurve): modeled costs per step.  # Function: projection_curve.
def projection_curve(config, steps=10):  # Define projection_curve with the config and a step count.
    # Build one row per step: naive cost grows, Markovian cost stays flat.  # Step: build the curve.
    curve = []  # Start with an empty curve.
    # Walk the step numbers from 1 to the requested count.  # Loop: projected steps.
    for step in range(1, steps + 1):  # Ten steps by default, like upstream.
        history_size = (step - 1) * config["chunk_size"]  # What a naive step re-reads before writing.
        curve.append({"step": step, "standard": history_size + config["chunk_size"], "markovian": config["carryover_tokens"] + config["chunk_size"]})  # Naive grows linearly per step; bounded stays flat.
    # Return the curve rows.  # Step: hand back the curve.
    return curve  # The cost story in ten rows.

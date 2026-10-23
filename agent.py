# agent.py - the QuizForge Live agentic study loop.  # Module header: what this file is.
# v1 QuizForge generated one quiz and stopped. QuizForge Live turns that into a loop:  # Design choice 1: the loop.
# plan the round, generate questions, grade the answers, adapt the next round's difficulty.  # Design choice 1 continued: the four steps.
# The loop runs on NVIDIA Nemotron (the DGX Spark prize angle) and is fully metered.  # Design choice 2: model + metering.
# It degrades gracefully: without a Nemotron key it still runs the loop on the offline heuristic engine.  # Design guarantee: the demo always works.
# THE LEARNER STATE IS A MARKOVIAN CHAIN (Stage 3a): each round is one chunk, and the state carried  # Design choice 3: the Meterless Markovian engine drives adaptation.
# forward is a bounded, compressed carryover block from markovian.py (Meterless Markovian Engine,  # Design choice 3 continued: bounded state, not raw history.
# open-source, Apache-2.0) - never the raw graded history, so per-round planning context stays flat  # Design choice 3 continued: O(1) planning context per round.
# no matter how many rounds the learner plays. Missed topics sit in the state's REMAINING field and  # Design choice 3 continued: misses resurface until mastered.
# resurface as the next round's focus until the learner masters them (more correct than missed).  # Design choice 3 continued: the mastery rule.
# Import the sibling generator module for the v1 quiz engines (LLM chain + offline heuristic).  # Library: generator (this project).
import generator  # The v1 generation engine lives in generator.py.
# Import the sibling Nemotron client for the agentic reasoning calls.  # Library: nemotron (this project).
import nemotron  # The Nemotron model client lives in nemotron.py.
# Import the sibling explanation module for evidence-backed answer explanations.  # Library: explain (this project).
import explain  # The explanation module lives in explain.py.
# Import the sibling metering module so every model call is counted.  # Library: meterless (this project).
import meterless  # The metering wrapper lives in meterless.py.
# Import the sibling Markovian engine: bounded learner state, marker protocol, compression cascade.  # Library: markovian (this project).
import markovian  # The Meterless Markovian Engine port lives in markovian.py.
# Start the system instruction that teaches Nemotron the study-planner role.  # Constant: planner system prompt.
PLANNER_SYSTEM = (  # A fixed system prompt used for the planning call.
    "You are QuizForge, an expert study coach planning a quiz round. "  # Role instruction: a coach planning a round.
    "Reply with a short JSON object only, no commentary, with keys: "  # Output rule: JSON only.
    "focus_areas (list of 2-4 concept labels to emphasize), difficulty (one of easy, medium, hard), "  # Key 1 and 2: where to aim and how hard.
    "strategy (one sentence on how to probe the learner's weak spots)."  # Key 3: the probing strategy.
)  # Close the system prompt string.
# Resolve the engine config once at import: upstream defaults (800-token carryover budget).  # Constant: engine config snapshot.
ENGINE_CONFIG = markovian.resolve_config({})  # Validated at load; an invalid default would fail loudly here, never mid-demo.
# Start the per-topic scorekeeper: fold graded history into correct/missed counts per topic.  # Function: _topic_stats.
def _topic_stats(history):  # Define _topic_stats, which tallies the graded history by topic.
    # Walk the graded items and tally each topic's outcomes.  # Step: tally the history.
    stats = {}  # Maps a topic label to {"correct": n, "missed": n}.
    # Count every graded item under its topic.  # Loop: graded items.
    for item in history:  # Each item is one graded answer from an earlier round.
        topic = item.get("topic", "General")  # The concept this answer tested.
        entry = stats.setdefault(topic, {"correct": 0, "missed": 0})  # Start this topic's tally at zero.
        # File the outcome under correct or missed.  # Step: record the outcome.
        if item.get("correct"):  # The learner got this one right.
            entry["correct"] += 1  # One more success for the topic.
        else:  # The learner missed this one.
            entry["missed"] += 1  # One more miss for the topic.
    # Return the tallies to the caller.  # Step: hand back the stats.
    return stats  # The raw material the Markovian state is built from.
# Start the weak-topic ranker: topics still in the state's REMAINING field, worst first.  # Function: _weak_topics.
def _weak_topics(stats):  # Define _weak_topics, which lists topics the learner has not mastered.
    # A topic is weak while it has misses and its corrects have not outnumbered them.  # Rule: the mastery test.
    weak = [topic for topic, entry in stats.items() if entry["missed"] > 0 and entry["correct"] <= entry["missed"]]  # Unmastered topics only.
    # Rank by the miss surplus (worst gap first), then by name so the order is deterministic.  # Step: rank the weak topics.
    weak.sort(key=lambda topic: (-(stats[topic]["missed"] - stats[topic]["correct"]), topic))  # Biggest gap first; alphabetical tiebreak.
    # Return the ranked weak topics.  # Step: hand back the ranking.
    return weak  # These become the next round's focus areas.
# Start the mastered-topic lister: topics for the state's COMPLETED field.  # Function: _mastered_topics.
def _mastered_topics(stats):  # Define _mastered_topics, which lists topics the learner has beaten.
    # A topic is mastered once its corrects outnumber its misses (and it was attempted at all).  # Rule: the same mastery test, positive side.
    mastered = [topic for topic, entry in stats.items() if entry["correct"] > entry["missed"]]  # Proven topics only.
    # Sort by name so the state block is deterministic.  # Step: stable order.
    mastered.sort()  # Alphabetical: same history, same state, every time.
    # Return the mastered topics.  # Step: hand back the list.
    return mastered  # These fill the state's COMPLETED field.
# Start the difficulty state rule: the Markov transition for the next round's difficulty.  # Function: _difficulty_for.
def _difficulty_for(stats, attempts):  # Define _difficulty_for with the topic tallies and the attempt count.
    # Count the correct answers and the overall accuracy.  # Step: accuracy.
    correct_total = sum(entry["correct"] for entry in stats.values())  # Every right answer so far.
    accuracy = (correct_total / attempts) if attempts else 0.0  # The share of answers the learner got right.
    # First contact is always a gentle baseline probe.  # Rule: round one.
    if attempts == 0:  # Nothing graded yet.
        return "easy"  # Start easy, always.
    # Unmastered topics plus shaky accuracy means remediate, do not advance.  # Rule: remediate.
    if _weak_topics(stats) and accuracy < 0.6:  # Weak spots remain and accuracy is low.
        return "easy"  # Hold at easy until the gaps close.
    # Strong accuracy over a real sample earns the hardest setting.  # Rule: push on mastery.
    if accuracy >= 0.85 and attempts >= 3:  # The learner is beating the material.
        return "hard"  # Step all the way up.
    # Middling accuracy advances one notch.  # Rule: steady progress.
    if accuracy >= 0.6:  # More right than wrong overall.
        return "medium"  # The middle setting.
    # Anything else stays easy.  # Rule: default.
    return "easy"  # The safe setting.
# Start the model compressor adapter: lets the cascade's level 2 use the Nemotron route.  # Function: _compress_with_model.
def _compress_with_model(prompt, system):  # Define _compress_with_model, matching markovian's compressor contract.
    # Call the active Nemotron route for the compression.  # Step: call the model.
    reply = nemotron.chat(prompt, system=system, max_tokens=300)  # A short labeled state block.
    # Meter the compression call with the ACTUAL provider and model, like every other call.  # Step: meter the call.
    meterless.count_call(nemotron.get_provider(), nemotron.get_model())  # The cascade's model use is metered too.
    # Return the compressed state text.  # Step: hand back the state.
    return reply  # The cascade validates length and budget itself.
# Start the engine planner: build the bounded Markovian state and decide the next round from it.  # Function: _engine_plan.
def _engine_plan(topic, history):  # Define _engine_plan, which returns the offline plan plus its state evidence.
    # Import json locally for the history-size accounting, matching this module's existing pattern.  # Library: json (local).
    import json as json_module  # Used only for measuring the raw history the planner no longer sends.
    # Tally the graded history by topic.  # Step: tally.
    stats = _topic_stats(history)  # Per-topic correct/missed counts.
    attempts = len(history)  # Every graded answer so far.
    correct_total = sum(entry["correct"] for entry in stats.values())  # Right answers so far.
    missed_total = attempts - correct_total  # Wrong answers so far.
    # Split the topics into the state's COMPLETED and REMAINING fields.  # Step: partition the topics.
    mastered = _mastered_topics(stats)  # Topics the learner has beaten.
    weak = _weak_topics(stats)  # Topics still owed remediation.
    # Decide this round from the state: difficulty by the Markov rule, focus = REMAINING first.  # Step: decide.
    difficulty = _difficulty_for(stats, attempts)  # The transition for this state.
    focus = weak[:4] if weak else [topic]  # Probe the weak topics; otherwise aim at the session topic.
    # Write the DECISIONS field: the strategy sentences the state carries forward.  # Step: decisions text.
    if weak:  # There are gaps to close.
        decisions = "Revisit weak topics first: " + ", ".join(focus) + ". Difficulty " + difficulty + " per the Markov state rule."  # Remediation strategy.
    elif attempts:  # Everything tracked is mastered.
        decisions = "All tracked topics mastered; advance on the session topic. Difficulty " + difficulty + " per the Markov state rule."  # Advancement strategy.
    else:  # No history at all.
        decisions = "First round; baseline probe of the session topic. Difficulty easy."  # Opening strategy.
    # Write the CONTEXT field: the session facts the next step needs.  # Step: context text.
    context = "Session topic: " + topic + ". Attempts: " + str(attempts) + " (" + str(correct_total) + " correct, " + str(missed_total) + " missed). Engine: Meterless Markovian, carryover budget " + str(ENGINE_CONFIG["carryover_tokens"]) + " tokens."  # Bounded facts, no raw history.
    # Build the canonical state block (upstream COMPLETED / REMAINING / DECISIONS / CONTEXT).  # Step: canonical block.
    block = markovian.canonical_block(", ".join(mastered) if mastered else "none yet", ", ".join(weak) if weak else "none", decisions, context)  # The state before compression.
    # Synthesize this round's chunk report ending in a [STATE_CHECKPOINT], the upstream marker protocol:  # Step: chunk report.
    report = ("Status: " + str(attempts) + " graded answers so far, " + str(correct_total) + " correct. " + "Remaining weak topics: " + (", ".join(weak) if weak else "none") + ". " + "Decision: difficulty " + difficulty + "; focus " + ", ".join(focus) + ".\n[STATE_CHECKPOINT]\n" + block)  # The step output the cascade compresses.
    # Parse the report's markers so the cascade sees the step's own state checkpoint.  # Step: parse markers.
    parsed = markovian.parse_markers(report)  # The marker state, if the protocol was followed.
    # Run the compression cascade: marker state first, model compression when a route exists, then  # Step: compress the state.
    # heuristic extraction, then truncation - the result is guaranteed inside the carryover budget.  # Step continued: the budget guarantee.
    compressor = _compress_with_model if nemotron.get_provider() else None  # Level 2 exists only with a live model route.
    service = markovian.CarryoverService(compressor)  # The cascade for this plan.
    result = service.next(parsed["state"], "", report, ENGINE_CONFIG)  # The bounded state for the next round.
    carryover = result["carryover"]  # The compressed learner state.
    carryover_tokens = markovian.estimate_tokens(carryover)  # Its estimated size (chars/4 rule).
    # Account for the saving: what the raw history would have cost the planner vs the bounded state.  # Step: savings accounting.
    history_tokens = markovian.estimate_tokens(json_module.dumps(history))  # The naive full-history prompt cost, estimated.
    tokens_saved = max(0, history_tokens - carryover_tokens)  # The flat-context saving for this round, estimated.
    # Log the engine decision as a trace event: judges can replay every state transition from the JSONL.  # Step: evidence.
    meterless.log_event("trace", {"engine": "markovian", "decision": "plan_round", "topic": topic, "attempts": attempts, "focus_areas": focus, "difficulty": difficulty, "cascade_level": result["level"], "carryover_tokens": carryover_tokens, "history_tokens_estimated": history_tokens, "tokens_saved_estimated": tokens_saved, "upstream": "github.com/Meterless/Meterless engines/markovian (Apache-2.0), stdlib port in markovian.py"})  # One trace line per planning decision.
    # Assemble the plan in the shape the UI and the model path both expect, plus the state evidence.  # Step: package the plan.
    plan = {"focus_areas": focus, "difficulty": difficulty, "strategy": decisions, "engine": "markovian", "state": carryover, "state_level": result["level"], "carryover_tokens": carryover_tokens}  # Labeled markovian: the engine made this plan.
    # Return the plan.  # Step: hand back the plan.
    return plan  # The offline-capable plan, fully decided by the engine state.
# Start the helper that plans the next round from the learner's history.  # Function: plan_round.
def plan_round(topic, history):  # Define plan_round with the topic and the past rounds.
    # Decide the round from the bounded Markovian state first: this works with no keys at all.  # Step 1: engine plan.
    engine_plan = _engine_plan(topic, history)  # Focus, difficulty, strategy, and the compressed state.
    # Without a model route, the engine plan IS the plan (the demo never waits on credentials).  # Guard: offline.
    if nemotron.get_provider() is None:  # Neither Nightshift nor OpenRouter is configured.
        return engine_plan  # The Markovian plan stands on its own.
    # Try the Nemotron route for a richer plan, prompted the upstream way: goal + carryover state.  # Step 2: model attempt.
    try:  # Begin the guarded model block.
        # Build the planner goal text for this round.  # Step: build the goal.
        goal = "Plan the next quiz round for the study topic '" + topic + "'. Reply with a short JSON object only: focus_areas (list of 2-4 concept labels), difficulty (easy, medium, or hard), strategy (one sentence)."  # The planning task, stated once.
        # Assemble the step prompt with markovian.build_prompt: chunk 1 gets the full goal; later  # Step: build the bounded prompt.
        # chunks get the truncated goal plus the [CARRYOVER STATE] block - never the raw history.  # Step continued: the O(1) prompt.
        prompt = markovian.build_prompt("RESEARCH", goal, len(history) + 1, engine_plan["state"], config=ENGINE_CONFIG)  # Bounded by construction.
        # Call Nemotron for the plan and count the call with the meter.  # Step: call the model.
        reply = nemotron.chat(prompt, system=PLANNER_SYSTEM, max_tokens=300)  # A short JSON plan, ideally ending in a state checkpoint.
        # Record the model call with the metering layer, naming the ACTUAL route (Nightshift or fallback),  # Step: meter the call.
        # because a router can serve a different model than the one requested - the judges see the truth.  # Step continued: the routing caveat.
        meterless.count_call(nemotron.get_provider(), nemotron.get_model())  # One planning call consumed, truthfully labeled.
        # Run the marker protocol over the reply: strip markers before parsing, keep any checkpoint.  # Step: parse markers.
        parsed = markovian.parse_markers(reply)  # The model's own state checkpoint, when it emitted one.
        # Parse the plan as JSON from the cleaned text, tolerating stray text around the object.  # Step: parse the plan.
        import json as json_module  # Import json locally so this module needs no new top-level import.
        start = parsed["cleaned"].find("{")  # Index of the first opening brace.
        end = parsed["cleaned"].rfind("}")  # Index of the last closing brace.
        plan = json_module.loads(parsed["cleaned"][start:end + 1])  # The plan dictionary.
        # Validate the plan's shape; a malformed plan falls back to the engine plan below.  # Guard: shape check.
        if not isinstance(plan.get("focus_areas"), list) or plan.get("difficulty") not in ("easy", "medium", "hard"):  # The two fields the UI depends on.
            raise ValueError("Planner returned an unexpected plan shape")  # Treat it like a parse failure.
        # Tag the plan with its engine and the Markovian state evidence so the UI stays honest.  # Step: label the plan.
        plan["engine"] = "nemotron"  # The model refined the engine's plan.
        plan["state"] = engine_plan["state"]  # The bounded state the prompt actually carried.
        plan["state_level"] = engine_plan["state_level"]  # How the state was compressed.
        plan["carryover_tokens"] = engine_plan["carryover_tokens"]  # The state's estimated size.
        # Keep the model's own checkpoint when it emitted one: it seeds the next round's evidence.  # Step: keep the checkpoint.
        if parsed["state"]:  # The model followed the marker protocol.
            plan["model_checkpoint"] = parsed["state"]  # Visible in the round package for the judges.
        # Log the model-refined decision as a trace event too.  # Step: evidence.
        meterless.log_event("trace", {"engine": "nemotron+markovian", "decision": "plan_round_model", "topic": topic, "focus_areas": plan["focus_areas"], "difficulty": plan["difficulty"], "model_checkpoint": bool(parsed["state"])})  # The refinement is on the record.
        # Return the model's plan.  # Step: hand back the result.
        return plan  # The adaptive round plan.
    # Fall back to the engine plan when the model cannot be reached or answers badly.  # Handler: model unavailable.
    except (nemotron.NemotronError, ValueError, KeyError, IndexError):  # Catch model failures and JSON parse failures.
        return engine_plan  # The Markovian plan was already decided above; nothing is lost.
# Start the helper that grades one learner answer against the correct answer.  # Function: grade_answer.
def grade_answer(question, user_answer):  # Define grade_answer with the question and the learner's answer.
    # Read the correct answer from the question.  # Step: get the key.
    correct = question.get("answer", "")  # The expected answer.
    # Compare case-insensitively after trimming whitespace, so "Photosynthesis" matches "photosynthesis".  # Step: tolerant comparison.
    is_correct = str(user_answer).strip().lower() == str(correct).strip().lower()  # True when the answers match loosely.
    # Return the grading result with both answers for the UI.  # Step: package the result.
    return {"correct": is_correct, "expected": correct, "given": user_answer, "topic": question.get("topic", "General")}  # The grading record.
# Start the main entry point: run one full agentic round.  # Function: run_round.
def run_round(text, topic, history, count=6):  # Define run_round with the material, topic, history, and question count.
    # Plan the round first: focus areas, difficulty, and probing strategy.  # Step 1: plan.
    plan = plan_round(topic, history)  # The adaptive plan for this round.
    # Generate the quiz with the v1 engine (its own provider chain, then offline heuristic).  # Step 2: generate.
    quiz = generator.generate(text, count)  # The quiz package: source, guide, questions.
    # Tag the quiz with the plan's difficulty and focus so the UI can show the adaptation.  # Step: attach the plan.
    quiz["plan"] = plan  # The plan travels with the quiz to the browser.
    # Return the round package; grading happens when the learner's answers come back.  # Step: hand back the round.
    return quiz  # The client plays this round, then posts answers to /api/grade.
# Start the grading entry point: grade a finished round and explain the misses.  # Function: grade_round.
def grade_round(questions, user_answers, topic, sources):  # Define grade_round with the questions, answers, topic, and sources.
    # Walk the questions and grade each answer.  # Step: grade every answer.
    results = []  # Start with an empty result list.
    # Pair each question with the learner's answer for it.  # Loop: question-answer pairs.
    for question, user_answer in zip(questions, user_answers):  # Walk both lists together.
        # Grade this one answer.  # Step: grade the answer.
        graded = grade_answer(question, user_answer)  # The grading record.
        # When the learner missed it, attach an evidence-backed explanation.  # Step: explain the misses.
        if not graded["correct"]:  # Check whether the answer was wrong.
            graded["explanation"] = explain.explain_outcome(topic, question, user_answer, graded["expected"], sources)  # The cited explanation.
        # Add the graded record to the results.  # Step: store the result.
        results.append(graded)  # One record per question.
    # Count the correct answers for the round score.  # Step: compute the score.
    score = sum(1 for item in results if item["correct"])  # The number of right answers.
    # Collect the missed topics: they are the observation the Markovian state folds in next round.  # Step: missed topics.
    missed_topics = sorted(set(item["topic"] for item in results if not item["correct"]))  # Distinct topics missed this round.
    # Log the round outcome as telemetry: the engine's REMAINING field updates from exactly this.  # Step: evidence.
    meterless.log_event("telemetry", {"engine": "markovian", "observation": "round_graded", "topic": topic, "score": score, "total": len(results), "missed_topics": missed_topics})  # One telemetry line per graded round.
    # Return the score, the per-question results, the missed topics, and the metering snapshot.  # Step: hand back the grading package.
    return {"score": score, "total": len(results), "results": results, "missed_topics": missed_topics, "usage": meterless.summary()}  # Everything the UI needs to render the round outcome.

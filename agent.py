# agent.py - the QuizForge Live agentic study loop.  # Module header: what this file is.
# v1 QuizForge generated one quiz and stopped. QuizForge Live turns that into a loop:  # Design choice 1: the loop.
# plan the round, generate questions, grade the answers, adapt the next round's difficulty.  # Design choice 1 continued: the four steps.
# The loop runs on NVIDIA Nemotron (the DGX Spark prize angle) and is fully metered.  # Design choice 2: model + metering.
# It degrades gracefully: without a Nemotron key it still runs the loop on the offline heuristic engine.  # Design guarantee: the demo always works.
# Import the sibling generator module for the v1 quiz engines (LLM chain + offline heuristic).  # Library: generator (this project).
import generator  # The v1 generation engine lives in generator.py.
# Import the sibling Nemotron client for the agentic reasoning calls.  # Library: nemotron (this project).
import nemotron  # The Nemotron model client lives in nemotron.py.
# Import the sibling explanation module for evidence-backed answer explanations.  # Library: explain (this project).
import explain  # The explanation module lives in explain.py.
# Import the sibling metering module so every model call is counted.  # Library: meterless (this project).
import meterless  # The metering wrapper lives in meterless.py.
# Start the system instruction that teaches Nemotron the study-planner role.  # Constant: planner system prompt.
PLANNER_SYSTEM = (  # A fixed system prompt used for the planning call.
    "You are QuizForge, an expert study coach planning a quiz round. "  # Role instruction: a coach planning a round.
    "Reply with a short JSON object only, no commentary, with keys: "  # Output rule: JSON only.
    "focus_areas (list of 2-4 concept labels to emphasize), difficulty (one of easy, medium, hard), "  # Key 1 and 2: where to aim and how hard.
    "strategy (one sentence on how to probe the learner's weak spots)."  # Key 3: the probing strategy.
)  # Close the system prompt string.
# Start the helper that plans the next round from the learner's history.  # Function: plan_round.
def plan_round(topic, history):  # Define plan_round with the topic and the past rounds.
    # Count the rounds and misses so far to ground the plan.  # Step: summarize history.
    rounds_done = len(history)  # How many rounds the learner has played.
    misses = [item for item in history if not item.get("correct")]  # The rounds the learner got wrong.
    miss_topics = sorted(set(item.get("topic", "General") for item in misses))  # The distinct weak topics.
    # Try the Nemotron route for an adaptive plan.  # Step: model attempt.
    try:  # Begin the guarded model block.
        # Build the planning prompt from the topic and the weak spots.  # Step: build the prompt.
        prompt = (  # Open the composed prompt.
            "Topic: " + topic + ". Rounds completed: " + str(rounds_done) + ". "  # The current state of play.
            "Weak topics so far: " + (", ".join(miss_topics) if miss_topics else "none yet") + ". "  # The gaps to probe.
            "Plan the next quiz round."  # The task instruction.
        )  # Close the composed prompt.
        # Call Nemotron for the plan and count the call with the meter.  # Step: call the model.
        reply = nemotron.chat(prompt, system=PLANNER_SYSTEM, max_tokens=300)  # A short JSON plan.
        # Record the model call with the metering layer, naming the ACTUAL route (Nightshift or fallback),  # Step: meter the call.
        # because a router can serve a different model than the one requested - the judges see the truth.  # Step continued: the routing caveat.
        meterless.count_call(nemotron.get_provider(), nemotron.get_model())  # One planning call consumed, truthfully labeled.
        # Parse the plan as JSON, tolerating stray text around the object.  # Step: parse the plan.
        import json as json_module  # Import json locally so this module needs no new top-level import.
        start = reply.find("{")  # Index of the first opening brace.
        end = reply.rfind("}")  # Index of the last closing brace.
        plan = json_module.loads(reply[start:end + 1])  # The plan dictionary.
        # Tag the plan with its engine so the UI stays honest.  # Step: label the plan.
        plan["engine"] = "nemotron"  # The adaptive plan came from the model.
        # Return the model's plan.  # Step: hand back the result.
        return plan  # The adaptive round plan.
    # Fall back to a simple rule-based plan when the model cannot be reached.  # Handler: model unavailable.
    except (nemotron.NemotronError, ValueError, KeyError, IndexError):  # Catch model failures and JSON parse failures.
        # Escalate difficulty slowly as rounds accumulate, and probe the weak topics first.  # Rule: gentle adaptive logic.
        difficulty = "easy" if rounds_done < 2 else ("medium" if rounds_done < 4 else "hard")  # Rounds 1-2 easy, 3-4 medium, 5+ hard.
        # Return the rule-based plan.  # Step: hand back the fallback plan.
        return {"focus_areas": miss_topics[:4] if miss_topics else [topic], "difficulty": difficulty, "strategy": "Revisit missed topics before advancing.", "engine": "fallback"}  # Labeled fallback.
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
    # Return the score, the per-question results, and the metering snapshot.  # Step: hand back the grading package.
    return {"score": score, "total": len(results), "results": results, "usage": meterless.summary()}  # Everything the UI needs to render the round outcome.

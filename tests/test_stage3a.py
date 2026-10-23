# test_stage3a.py - offline tests for the Stage 3a Markovian engine integration.  # Module header: what this file is.
# Everything here runs with NO network and NO keys: the environment is scrubbed before the project  # Guarantee: deterministic and offline.
# modules are imported, so the Nemotron routes report "not configured" and the loop runs on the  # Guarantee continued: the engine path is what gets exercised.
# Meterless Markovian engine plus the v1 offline heuristic - exactly the demo's worst case.  # Guarantee continued: worst case is the tested case.
# Run from the repo root:  python3 -m unittest discover -s tests -v  # How to run this suite.
# Import the OS module to scrub and restore environment variables around the tests.  # Library: os.
import os  # Make the os module available.
# Import the sys module to put the repo root on the import path.  # Library: sys.
import sys  # Make the sys module available.
# Import the JSON module to read the JSONL evidence files the engine writes.  # Library: json.
import json  # Make the json module available.
# Import the tempfile module for an isolated evidence-log directory per test class.  # Library: tempfile.
import tempfile  # Make the tempfile module available.
# Import the unittest framework (standard library only, like the whole project).  # Library: unittest.
import unittest  # Make the unittest framework available.
# Define every environment variable that could enable a network route or a real key.  # Constant: route env keys.
ROUTE_ENV_KEYS = ["METERLESS_BASE_URL", "METERLESS_RUNTIME_TOKEN", "METERLESS_MODEL", "NIGHTSHIFT_API_URL", "NIGHTSHIFT_API_KEY", "NIGHTSHIFT_CHAT_PATH", "NEMOTRON_MODEL", "NEMOTRON_MODEL_FALLBACK", "OPENROUTER_API_KEY", "GROQ_API_KEY", "METERLESS_API_URL", "METERLESS_API_KEY", "ZETARIS_REST_URL", "ZETARIS_API_KEY"]  # Scrubbed before import and restored after the suite.
# Save the current values so the suite leaves the caller's environment untouched.  # Step: snapshot the env.
_SAVED_ENV = {key: os.environ.get(key) for key in ROUTE_ENV_KEYS + ["METERLESS_LOG_DIR"]}  # None marks "was unset".
# Scrub every route key so no test can reach the network through a real credential.  # Step: scrub the env.
for _key in ROUTE_ENV_KEYS:  # Each key that could open a route.
    os.environ.pop(_key, None)  # Remove it for the whole suite.
# Point the metering evidence at a throwaway directory so tests never pollute the repo's logs/.  # Step: isolate the logs.
_TEST_LOG_DIR = tempfile.mkdtemp(prefix="quizforge-live-test-logs-")  # A fresh temp folder for JSONL evidence.
os.environ["METERLESS_LOG_DIR"] = _TEST_LOG_DIR  # meterless.py reads this live on every write.
# Put the repo root (this file's parent's parent) on the import path.  # Step: import path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # tests/ lives one level below the modules.
# Import the project modules under test, now that the environment is clean.  # Libraries: project modules.
import markovian  # The Meterless Markovian Engine port.
import nemotron  # The Nemotron route client (env alignment tests).
import meterless  # The metering + JSONL evidence layer.
import agent  # The agentic loop with the engine wired in.
import generator  # The v1 engine, for the end-to-end regression test.
# Start the config validation tests (upstream types.ts BOUNDS + configManager.ts rules).  # Class: ConfigTests.
class ConfigTests(unittest.TestCase):  # Define ConfigTests, covering resolve_config.
    # The defaults must match upstream exactly: 8000 / 24 / 800 / 0.  # Test: upstream defaults.
    def test_defaults_match_upstream(self):  # Define the defaults test.
        # Resolve an empty overlay and compare against the upstream DEFAULT_CONFIG.  # Step: compare.
        self.assertEqual(markovian.resolve_config({}), {"chunk_size": 8000, "max_chunks": 24, "carryover_tokens": 800, "overlap_tokens": 0})  # The documented defaults, unchanged.
    # A carryover budget below the upstream minimum of 128 must be rejected, not clamped.  # Test: lower bound.
    def test_carryover_below_minimum_rejected(self):  # Define the lower-bound test.
        # 64 is below BOUNDS.carryover_tokens.min (128).  # Step: expect the typed error.
        with self.assertRaises(markovian.ConfigValidationError):  # The upstream typed error.
            markovian.resolve_config({"carryover_tokens": 64})  # Must raise.
    # A chunk too small to hold framing + carryover + output must be rejected.  # Test: chunk capacity rule.
    def test_chunk_too_small_rejected(self):  # Define the capacity test.
        # 2000 < 400 (framing) + 800 (carryover) + 1200 (output budget) = 2400.  # Step: expect the typed error.
        with self.assertRaises(markovian.ConfigValidationError):  # The upstream sanity rule.
            markovian.resolve_config({"chunk_size": 2000})  # Must raise.
    # A valid custom config must pass untouched.  # Test: valid overlay.
    def test_valid_overlay_accepted(self):  # Define the valid-overlay test.
        # 4000 >= 400 + 256 + 1200, and 256 is inside [128, 32768].  # Step: compare.
        self.assertEqual(markovian.resolve_config({"chunk_size": 4000, "carryover_tokens": 256})["carryover_tokens"], 256)  # The overlay wins.
# Start the token estimator tests (upstream: ceil(chars / 4), always labeled estimated).  # Class: EstimatorTests.
class EstimatorTests(unittest.TestCase):  # Define EstimatorTests, covering estimate_tokens.
    # Empty text estimates to zero tokens.  # Test: empty input.
    def test_empty_is_zero(self):  # Define the empty test.
        self.assertEqual(markovian.estimate_tokens(""), 0)  # ceil(0/4) = 0.
    # Four characters estimate to exactly one token.  # Test: exact boundary.
    def test_four_chars_one_token(self):  # Define the boundary test.
        self.assertEqual(markovian.estimate_tokens("abcd"), 1)  # ceil(4/4) = 1.
    # Five characters round UP to two tokens.  # Test: ceiling behavior.
    def test_five_chars_rounds_up(self):  # Define the ceiling test.
        self.assertEqual(markovian.estimate_tokens("abcde"), 2)  # ceil(5/4) = 2.
# Start the marker protocol tests (upstream markers.ts).  # Class: MarkerTests.
class MarkerTests(unittest.TestCase):  # Define MarkerTests, covering parse_markers and clean_markers.
    # A [STATE_CHECKPOINT] tail must be captured as the state and stripped from display text.  # Test: state tail.
    def test_state_checkpoint_captured_and_cleaned(self):  # Define the state-tail test.
        # Build a chunk the way the prompt rules ask a model to emit it.  # Step: build the chunk.
        raw = "Some reasoning.\n[STATE_CHECKPOINT]\nCOMPLETED: a\nREMAINING: b\nDECISIONS: c\nCONTEXT: d"  # A protocol-following chunk.
        parsed = markovian.parse_markers(raw)  # Run the parser.
        # The state is the block after the marker; the cleaned text keeps only the reasoning.  # Step: assertions.
        self.assertTrue(parsed["state"].startswith("COMPLETED: a"))  # The captured state.
        self.assertNotIn("STATE_CHECKPOINT", parsed["cleaned"])  # Markers never reach the display.
        self.assertEqual(parsed["cleaned"], "Some reasoning.")  # Only the prose survives.
    # A [TASK_COMPLETE] marker must flag completion.  # Test: final marker.
    def test_task_complete_detected(self):  # Define the completion test.
        self.assertTrue(markovian.parse_markers("All done. [TASK_COMPLETE]")["done"])  # The chain ends.
    # A <CARRYOVER> block must win as the state when present.  # Test: block form.
    def test_carryover_block_captured(self):  # Define the block-form test.
        parsed = markovian.parse_markers("Work.\n<CARRYOVER>COMPLETED: x and more state here</CARRYOVER>")  # The angle-bracket form.
        self.assertEqual(parsed["state"], "COMPLETED: x and more state here")  # The block content is the state.
# Start the compression cascade tests (upstream carryover.ts, strict level order).  # Class: CarryoverTests.
class CarryoverTests(unittest.TestCase):  # Define CarryoverTests, covering CarryoverService.
    # A valid marker state inside the budget must be accepted at level "marker".  # Test: level 1.
    def test_marker_level_accepted(self):  # Define the marker-level test.
        # Build a chunk ending in a small canonical state block.  # Step: build the chunk.
        block = markovian.canonical_block("fractions", "decimals", "Difficulty easy per the Markov state rule.", "Session topic: Math.")  # A valid state.
        chunk = "Status: 4 graded answers so far.\n[STATE_CHECKPOINT]\n" + block  # A protocol-following chunk.
        parsed = markovian.parse_markers(chunk)  # Extract the marker state.
        result = markovian.CarryoverService().next(parsed["state"], "", chunk, markovian.resolve_config({}))  # Run the cascade offline.
        # The step's own state wins, unchanged.  # Step: assertions.
        self.assertEqual(result["level"], "marker")  # Level 1 fired.
        self.assertEqual(result["carryover"], block)  # The state passed through.
    # An oversized state must be compressed until it fits the budget - the O(1) guarantee.  # Test: budget enforcement.
    def test_oversized_state_compressed_to_budget(self):  # Define the budget test.
        # Build a state block with hundreds of weak topics, far beyond 800 tokens (~1,550 estimated).  # Step: build the huge state.
        topics = ", ".join("Topic%03d" % index for index in range(600))  # 600 distinct topics: ~6,200 chars of state.
        block = markovian.canonical_block("none yet", topics, "Revisit weak topics first.", "Session topic: Everything.")  # Way over budget.
        chunk = "Status: many graded answers.\n[STATE_CHECKPOINT]\n" + block  # The huge chunk.
        parsed = markovian.parse_markers(chunk)  # The marker state is the huge block.
        result = markovian.CarryoverService().next(parsed["state"], "", chunk, markovian.resolve_config({}))  # Run the cascade offline.
        # The marker level must refuse it, and a later level must land inside the budget.  # Step: assertions.
        self.assertIn(result["level"], ("heuristic", "truncation"))  # The cascade fell through.
        self.assertLessEqual(markovian.estimate_tokens(result["carryover"]), 800)  # The budget held.
    # State-bearing sentences without markers must be extracted at the heuristic level.  # Test: level 3.
    def test_heuristic_level_extracts_key_phrases(self):  # Define the heuristic test.
        # A chunk with upstream key phrases and no marker block.  # Step: build the chunk.
        chunk = "The learner answered twice. Therefore the next round revisits decimals. Remaining work is fractions practice."  # Key phrases: Therefore / Remaining.
        result = markovian.CarryoverService().next(None, "", chunk, markovian.resolve_config({}))  # No marker state at all.
        # The extracted phrases become the state.  # Step: assertions.
        self.assertEqual(result["level"], "heuristic")  # Level 3 fired.
        self.assertIn("Therefore", result["carryover"])  # The phrase survived extraction.
# Start the efficiency accounting tests (upstream configManager.ts runEfficiency).  # Class: EfficiencyTests.
class EfficiencyTests(unittest.TestCase):  # Define EfficiencyTests, covering run_efficiency.
    # Three full chunks: naive cost is quadratic, Markovian cost is flat - exact numbers.  # Test: section-6 math.
    def test_run_efficiency_math(self):  # Define the accounting test.
        # Chunks of 8000 estimated tokens each under the default config.  # Step: run the accounting.
        result = markovian.run_efficiency([{"tokens": 8000}, {"tokens": 8000}, {"tokens": 8000}], markovian.resolve_config({}))  # Three chunks.
        # Naive: 8000 + 16000 + 24000 = 48000. Markovian: 3*800 carryover + 24000 = 26400.  # Step: assertions.
        self.assertEqual(result["standard_cost"], 48000)  # The quadratic price.
        self.assertEqual(result["markovian_cost"], 26400)  # The flat price.
        self.assertEqual(result["tokens_saved"], 21600)  # The difference.
        self.assertAlmostEqual(result["efficiency_percent"], 45.0)  # 21600 / 48000.
# Start the agent-level engine tests: the engine must CHANGE behavior across rounds.  # Class: AgentEngineTests.
class AgentEngineTests(unittest.TestCase):  # Define AgentEngineTests, covering plan_round and grade_round.
    # With no history, the plan is the engine's gentle baseline probe.  # Test: first round.
    def test_first_round_baseline(self):  # Define the baseline test.
        # Plan with an empty history (offline: no provider is configured in this suite).  # Step: plan.
        plan = agent.plan_round("First Aid", [])  # The opening round.
        # The engine labels its own plan and starts easy on the session topic.  # Step: assertions.
        self.assertEqual(plan["engine"], "markovian")  # The engine decided, not a model.
        self.assertEqual(plan["difficulty"], "easy")  # Round one is always easy.
        self.assertEqual(plan["focus_areas"], ["First Aid"])  # Nothing weak yet: aim at the topic.
        self.assertLessEqual(plan["carryover_tokens"], 800)  # The state is inside the budget.
    # A missed topic must resurface in the next plan's focus (the REMAINING field at work).  # Test: resurfacing.
    def test_missed_topic_resurfaces(self):  # Define the resurfacing test.
        # Three misses on Oxygen, nothing else: accuracy 0, Oxygen unmastered.  # Step: plan.
        history = [{"correct": False, "topic": "Oxygen"}, {"correct": False, "topic": "Oxygen"}, {"correct": False, "topic": "Oxygen"}]  # A struggling learner.
        plan = agent.plan_round("First Aid", history)  # The next round's plan.
        # Oxygen leads the focus and difficulty holds at easy for remediation.  # Step: assertions.
        self.assertIn("Oxygen", plan["focus_areas"])  # The miss resurfaced.
        self.assertEqual(plan["difficulty"], "easy")  # Remediate, do not advance.
        self.assertIn("Oxygen", plan["state"])  # The bounded state itself carries the miss.
    # A mastered topic must leave the focus, and strong accuracy must raise the difficulty.  # Test: mastery.
    def test_mastery_escalates_and_clears_focus(self):  # Define the mastery test.
        # Four correct answers on Oxygen: mastered, accuracy 1.0 over 4 attempts.  # Step: plan.
        history = [{"correct": True, "topic": "Oxygen"} for _ in range(4)]  # A learner beating the material.
        plan = agent.plan_round("First Aid", history)  # The next round's plan.
        # Difficulty steps up to hard and Oxygen is no longer a focus area.  # Step: assertions.
        self.assertEqual(plan["difficulty"], "hard")  # The Markov rule pushes on mastery.
        self.assertNotIn("Oxygen", plan["focus_areas"])  # Mastered topics leave REMAINING.
    # Remediation must clear a weakness: corrects outnumbering misses masters the topic.  # Test: remediation.
    def test_remediation_clears_weakness(self):  # Define the remediation test.
        # One miss, then two corrects on Oxygen: 2 > 1, so Oxygen is mastered.  # Step: plan.
        history = [{"correct": False, "topic": "Oxygen"}, {"correct": True, "topic": "Oxygen"}, {"correct": True, "topic": "Oxygen"}]  # Missed, then fixed twice.
        plan = agent.plan_round("First Aid", history)  # The next round's plan.
        self.assertNotIn("Oxygen", plan["focus_areas"])  # The weakness cleared.
    # Two different histories must produce two different plans (the engine is not decorative).  # Test: behavior change.
    def test_engine_changes_behavior_between_histories(self):  # Define the behavior-change test.
        # Same session topic, opposite learners.  # Step: plan both.
        struggling = agent.plan_round("First Aid", [{"correct": False, "topic": "Oxygen"}] * 3)  # All misses.
        cruising = agent.plan_round("First Aid", [{"correct": True, "topic": "Oxygen"}] * 4)  # All correct.
        # Focus and difficulty both differ.  # Step: assertions.
        self.assertNotEqual(struggling["focus_areas"], cruising["focus_areas"])  # Different focus.
        self.assertNotEqual(struggling["difficulty"], cruising["difficulty"])  # Different difficulty.
    # A giant history must still yield a bounded state: the Markovian O(1) property, end to end.  # Test: bounded state.
    def test_huge_history_state_stays_bounded(self):  # Define the bounded-state test.
        # 300 graded answers across 300 distinct missed topics.  # Step: plan.
        history = [{"correct": False, "topic": "Topic%03d" % index} for index in range(300)]  # A very long session.
        plan = agent.plan_round("First Aid", history)  # The next round's plan.
        # The state the planner carries is capped by the carryover budget, whatever the history size.  # Step: assertions.
        self.assertLessEqual(plan["carryover_tokens"], 800)  # Budget held at the token level.
        self.assertLessEqual(len(plan["state"]), 3200)  # 800 tokens * 4 chars, the estimator's own bound.
        self.assertEqual(plan["state_level"], "truncation")  # The cascade's last level guarantees the cap.
    # A full round trip: grade a round, fold the results into history, watch the plan adapt.  # Test: round trip.
    def test_grade_then_plan_adapts(self):  # Define the round-trip test.
        # Two questions: Oxygen answered wrong, Bleeding answered right.  # Step: grade.
        questions = [{"question": "What carries oxygen?", "answer": "Hemoglobin", "topic": "Oxygen", "explanation": "Hemoglobin carries oxygen in red blood cells."}, {"question": "First step for bleeding?", "answer": "Apply pressure", "topic": "Bleeding", "explanation": "Apply direct pressure first."}]  # A two-question round.
        graded = agent.grade_round(questions, ["Water", "Apply pressure"], "First Aid", [])  # One miss, one hit.
        # The grade reports the miss honestly.  # Step: grading assertions.
        self.assertEqual(graded["score"], 1)  # One of two correct.
        self.assertEqual(graded["missed_topics"], ["Oxygen"])  # The observation for the state.
        # Fold the graded results into history the way the client does, then plan again.  # Step: plan again.
        history = [{"correct": item["correct"], "topic": item["topic"]} for item in graded["results"]]  # The client's history shape.
        plan = agent.plan_round("First Aid", history)  # The adapted plan.
        self.assertIn("Oxygen", plan["focus_areas"])  # The miss drives the next round.
    # Every planning decision must land in the JSONL evidence as a trace event naming the engine.  # Test: trace evidence.
    def test_plan_writes_trace_evidence(self):  # Define the evidence test.
        # Plan once, then read the event log the metering layer wrote.  # Step: plan and read.
        agent.plan_round("First Aid", [{"correct": False, "topic": "Oxygen"}])  # One engine decision.
        events_path = os.path.join(_TEST_LOG_DIR, "events.jsonl")  # The evidence file for this suite.
        with open(events_path, "r", encoding="utf-8") as handle:  # Read the JSONL lines.
            events = [json.loads(line) for line in handle if line.strip()]  # Parse every event.
        # A trace event from the Markovian engine must be among them.  # Step: assertions.
        traces = [event for event in events if event.get("event") == "trace" and event.get("data", {}).get("engine") == "markovian"]  # The engine's decisions.
        self.assertTrue(traces)  # At least one engine trace exists.
        self.assertEqual(traces[-1]["data"]["decision"], "plan_round")  # It records the planning decision.
# Start the Nemotron env-alignment tests (documented METERLESS_* names, legacy fallbacks).  # Class: NemotronEnvTests.
class NemotronEnvTests(unittest.TestCase):  # Define NemotronEnvTests, covering route selection.
    # Restore the suite-scrubbed environment after each test in this class.  # Method: tearDown.
    def tearDown(self):  # Define the per-test cleanup.
        # Remove every route key the test may have set.  # Step: clean up.
        for key in ROUTE_ENV_KEYS:  # Each route key.
            os.environ.pop(key, None)  # Back to the scrubbed baseline.
    # With nothing set, there is no route and the loop runs offline.  # Test: no route.
    def test_no_env_no_route(self):  # Define the no-route test.
        self.assertIsNone(nemotron.get_provider())  # The offline engine path.
    # The documented METERLESS_* names must select Nightshift and its model.  # Test: documented names.
    def test_documented_meterless_names_win(self):  # Define the documented-names test.
        # Set the documented local-install values from the workspace Setup Guide.  # Step: configure.
        os.environ["METERLESS_BASE_URL"] = "http://127.0.0.1:8088/v1"  # The documented local base.
        os.environ["METERLESS_RUNTIME_TOKEN"] = "test-token-not-a-real-one"  # A placeholder token.
        os.environ["METERLESS_MODEL"] = "meterless/auto"  # The documented default model.
        # Nightshift is the provider and the documented model is reported.  # Step: assertions.
        self.assertEqual(nemotron.get_provider(), "nightshift")  # The primary route.
        self.assertEqual(nemotron.get_model(), "meterless/auto")  # The documented model name.
        self.assertTrue(nemotron.nightshift_configured())  # Both halves of the route are present.
    # The legacy NIGHTSHIFT_* names must still work when the documented names are unset.  # Test: legacy fallback.
    def test_legacy_nightshift_names_still_work(self):  # Define the legacy test.
        # Set only the Stage 1/2 names.  # Step: configure.
        os.environ["NIGHTSHIFT_API_URL"] = "http://127.0.0.1:8088/v1"  # The legacy base name.
        os.environ["NIGHTSHIFT_API_KEY"] = "test-token-not-a-real-one"  # The legacy key name.
        self.assertEqual(nemotron.get_provider(), "nightshift")  # The fallback names still route.
    # OpenRouter alone must select the fallback route.  # Test: openrouter fallback.
    def test_openrouter_only_selects_fallback(self):  # Define the fallback test.
        os.environ["OPENROUTER_API_KEY"] = "test-key-not-a-real-one"  # A placeholder key.
        self.assertEqual(nemotron.get_provider(), "openrouter")  # The fallback route.
# Start the end-to-end offline regression: the Stage 1/2 smoke loop, on the engine now.  # Class: OfflineLoopTests.
class OfflineLoopTests(unittest.TestCase):  # Define OfflineLoopTests, covering run_round + grade_round.
    # The full loop must run keyless on the bundled sample text.  # Test: the loop.
    def test_full_offline_loop(self):  # Define the loop test.
        # Load the bundled demo study text.  # Step: load the sample.
        sample_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_data", "first-responder-sample.txt")  # The demo material.
        with open(sample_path, "r", encoding="utf-8") as handle:  # Read the sample.
            text = handle.read()  # The study material.
        # Run one round and grade every answer wrong on purpose.  # Step: run and grade.
        quiz = agent.run_round(text, "First Aid", [], 4)  # Plan + generate, keyless.
        answers = ["definitely wrong"] * len(quiz["questions"])  # Every answer misses.
        graded = agent.grade_round(quiz["questions"], answers, "First Aid", [])  # Grade with explanations (empty sources: explain.py falls back to each question's own explanation).
        # The round carries an engine plan, real questions, and explained misses.  # Step: assertions.
        self.assertEqual(quiz["plan"]["engine"], "markovian")  # The engine planned the round.
        self.assertTrue(quiz["questions"])  # Questions were generated offline.
        self.assertEqual(graded["score"], 0)  # All answers were wrong.
        self.assertTrue(all("explanation" in item for item in graded["results"]))  # Every miss got an explanation.
# Restore the caller's environment at PROCESS EXIT only - restoring at import time would  # Step: defer the restore.
# re-enable real routes while the tests run, which is exactly what the scrub prevents.  # Why deferred: unittest executes after import completes.
import atexit  # Library: atexit (process-exit hooks).
# Start the exit-time environment restore.  # Function: _restore_env.
def _restore_env():  # Define _restore_env, registered with atexit below.
    # Put every saved key back the way the suite found it.  # Step: restore each key.
    for key, value in _SAVED_ENV.items():  # Each saved key.
        if value is None:  # It was unset before the suite.
            os.environ.pop(key, None)  # Leave it unset.
        else:  # It had a value before the suite.
            os.environ[key] = value  # Put it back.
# Register the restore so it fires when the test process ends.  # Step: register the hook.
atexit.register(_restore_env)  # The suite's process is throwaway, but politeness is free.
# Run the suite when this file is executed directly.  # Entry-point guard.
if __name__ == "__main__":  # Check how the file was started.
    unittest.main()  # Run every test above.

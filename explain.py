# explain.py - evidence-backed explanations for QuizForge Live.  # Module header: what this file is.
# When a learner misses a question, the agent does not just show the answer: it produces  # Design choice 1: the pedagogy.
# an explanation backed by quoted evidence from the study material.  # Design choice 1 continued: cite the sources.
# This module is also the core of the Track 02 (Explain Why) fallback lane:  # Design choice 2: the fallback lane.
# "investigate questions across sources, connect findings, produce evidence-backed answers."  # Design choice 2 continued: matches the track brief.
# Import the sibling Nemotron client so explanations come from the NVIDIA model.  # Library: nemotron (this project).
import nemotron  # The Nemotron model client lives in nemotron.py.
# Import the sibling metering module so every explanation call is counted too.  # Library: meterless (this project).
import meterless  # The metering wrapper lives in meterless.py.
# Import the sibling generator module so we can find the question's source sentence.  # Library: generator (this project).
import generator  # The v1 quiz engine lives in generator.py.
# Start the system instruction that teaches Nemotron the explanation format.  # Constant: system prompt.
SYSTEM_PROMPT = (  # A fixed system prompt used for every explanation call.
    "You are QuizForge, an expert study coach. You explain quiz answers with evidence. "  # Role instruction: a coach, not a chatbot.
    "Always cite the numbered sources you were given, like [1] and [2], right after the claim they support. "  # Citation rule: inline numbered citations.
    "Never invent facts that are not in the sources; say when the sources do not cover something. "  # Honesty rule: no hallucinating beyond the material.
    "Keep the explanation under 120 words, plain language, encouraging tone."  # Style rule: short and kind.
)  # Close the system prompt string.
# Start the helper that formats sources into a numbered list the model can cite.  # Function: format_sources.
def format_sources(sources):  # Define format_sources, which numbers each source for citation.
    # Build one numbered line per source.  # Step: number the sources.
    lines = []  # Start with an empty line list.
    # Walk the sources with a 1-based index.  # Loop: numbered sources.
    for index, source in enumerate(sources, start=1):  # Number sources starting at 1 so citations read [1], [2], and so on.
        lines.append("[" + str(index) + "] (" + source.get("source", "source") + ") " + source.get("excerpt", ""))  # One line per source with its label and excerpt.
    # Join the lines into a single block for the prompt.  # Step: join the lines.
    return "\n".join(lines)  # The numbered source block.
# Start the offline fallback that writes a plain explanation when the model is unavailable.  # Function: fallback_explanation.
def fallback_explanation(topic, question, user_answer, correct_answer, source_sentence):  # Define fallback_explanation with the quiz facts.
    # Build a short honest explanation from the facts we have.  # Step: compose the text.
    text = (  # Open the composed explanation.
        "Topic: " + topic + ". You answered '" + str(user_answer) + "'; the correct answer is '" + str(correct_answer) + "'. "  # State the question outcome plainly.
        "The study material says: \"" + source_sentence + "\" Review that sentence and the term '" + str(correct_answer) + "' before the next round."  # Quote the source and point at the term.
    )  # Close the composed explanation.
    # Return the explanation with the raw source as its single citation.  # Step: package the result.
    return {"explanation": text, "citations": [source_sentence], "engine": "fallback"}  # Labeled fallback so the UI stays honest.
# Start the main entry point: explain a quiz outcome with evidence.  # Function: explain_outcome.
def explain_outcome(topic, question, user_answer, correct_answer, sources):  # Define explain_outcome with the quiz facts and source list.
    # Normalize the sources into a list so callers can pass one string or many sources.  # Step: normalize inputs.
    if not sources:  # No sources were given.
        sources = [{"source": "study-material", "excerpt": question.get("explanation", "")}]  # Fall back to the question's own explanation as the single source.
    # Try the Nemotron route first for a rich cited explanation.  # Step: model attempt.
    try:  # Begin the guarded model block.
        # Format the sources into the numbered citation block.  # Step: format the sources.
        source_block = format_sources(sources)  # The [1], [2] list the model must cite.
        # Build the user prompt with the question, the learner's answer, and the sources.  # Step: build the prompt.
        prompt = (  # Open the composed prompt.
            "Question: " + question.get("question", "") + "\n"  # The question the learner faced.
            "Learner answered: " + str(user_answer) + ". Correct answer: " + str(correct_answer) + ".\n"  # The outcome to explain.
            "Topic: " + topic + ".\n"  # The concept label.
            "Explain why the correct answer is right, citing the numbered sources.\n"  # The task instruction.
            "SOURCES:\n" + source_block  # The evidence the model may cite.
        )  # Close the composed prompt.
        # Call Nemotron for the cited explanation.  # Step: call the model.
        reply = nemotron.chat(prompt, system=SYSTEM_PROMPT, max_tokens=400)  # A short, cited, encouraging explanation.
        # Meter the call with the ACTUAL provider and model, so the log never lies about routing.  # Step: meter the call.
        meterless.count_call(nemotron.get_provider(), nemotron.get_model())  # One explanation call consumed, truthfully labeled.
        # Return the model's explanation with the source excerpts as citations.  # Step: package the result.
        return {"explanation": reply.strip(), "citations": [s.get("excerpt", "") for s in sources], "engine": "nemotron"}  # Labeled Nemotron so the UI can say which engine ran.
    # Fall back to the plain offline explanation when the model cannot be reached.  # Handler: model unavailable.
    except nemotron.NemotronError:  # The Nemotron client raises NemotronError on any failure.
        return fallback_explanation(topic, question, user_answer, correct_answer, question.get("explanation", ""))  # Honest offline explanation.

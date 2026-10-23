# assemble.py - turn the captured stills plus TTS narration into the finished QuizForge Live demo video.  # Module header: purpose of this file.
# Written 2026-10-23 for Stage 3b of the GenAI Works Open Agent Hackathon entry, following the proven v1 pattern:  # Provenance: demo tooling.
# one clip per shot, each timed to its narration segment, slow zoom, fades, concat, mux.  # Provenance continued: same recipe as quizforge-fresh/video/assemble.py.
# Import the JSON module so ffprobe output can be parsed.  # Library: json.
import json  # Make the json module available.
# Import the OS module for path building.  # Library: os.
import os  # Make the os module available.
# Import subprocess so ffmpeg, ffprobe, and the tts CLI can be run.  # Library: subprocess.
import subprocess  # All media work is delegated to these three tools.
# Define the folder this script lives in.  # Constant: script folder.
HERE = os.path.dirname(os.path.abspath(__file__))  # Absolute path of the demo folder.
# Define the folder holding the screenshots from capture.py.  # Constant: shots folder.
SHOTS = os.path.join(HERE, "shots")  # Input stills live here.
# Define the folder that will hold the narration audio segments.  # Constant: audio folder.
AUDIO = os.path.join(HERE, "audio")  # One MP3 per narration segment.
# Define the folder that will hold the intermediate per-shot clips.  # Constant: clips folder.
CLIPS = os.path.join(HERE, "clips")  # One silent MP4 and one padded M4A per shot.
# Create the working folders if they do not exist yet.  # Step: prepare folders.
os.makedirs(AUDIO, exist_ok=True)  # Safe to re-run.
os.makedirs(CLIPS, exist_ok=True)  # Safe to re-run.
# Define the shot order and the exact narration spoken over each shot (final wording verified against capture_meta.json).  # Data: the demo script.
SEGMENTS = [  # One tuple per shot: (screenshot filename, narration text).
    ("shot01_home.png", "QuizForge forged one quiz and stopped. QuizForge Live turns it into a study agent: it plans a round, generates the questions, grades your answers, and adapts what comes next. It starts the same way — paste in any study material."),  # Intro over the untouched home page.
    ("shot02_sample.png", "I'll load the built-in sample: a first-responder exam excerpt covering scene safety, A V P U, SAMPLE, and O P Q R S T. Then I'll start a live round against the app's real A P I."),  # The one-click sample load.
    ("shot03_round1.png", "The agent plans before it asks. Its memory is the Meterless Markovian engine: everything it knows about the learner, compressed into one small, bounded state block. Round one is a baseline probe — easy difficulty, four questions."),  # Round 1's plan block.
    ("shot04_grade.png", "I answer all four — and deliberately miss every question on two topics. Grading is instant, one of four, and every miss comes back with an explanation that quotes the study material itself, word for word. Nothing invented, nothing to hunt down."),  # Graded answers with cited explanations.
    ("shot05_round2.png", "Now the money shot. Round two's plan targets exactly the two topics I missed — SAMPLE and D C A P B T L S — carried forward in the state's remaining list until I master them. The raw history is never re-read; every round costs the same small, bounded context."),  # Round 2's plan: focus equals the missed topics.
    ("shot06_usage.png", "And every step leaves evidence. The usage endpoint inventories the session's J S O N L evidence log: three events — a trace for each plan, telemetry for the graded round — and any model calls would be metered here too, with the actual provider named."),  # The usage snapshot and evidence inventory.
    ("shot07_status.png", "The status panel is honest about the sponsor wiring: the Zetaris data-harness client is built and preflight-checked, waiting on the organizers' participant instance; Nemotron routes through Nightshift where it's installed locally, with a free OpenRouter seat behind it."),  # Integration health, honestly labeled.
    ("shot01_home.png", "Plan, generate, grade, adapt. QuizForge Live — the QuizForge you know, extended with the Meterless Markovian engine, the Zetaris data harness, and NVIDIA Nemotron. It keeps studying with you."),  # Closing over the home page reprise.
]  # End of the demo script.
# Define the narration head/tail padding, in seconds, inside every clip.  # Constant: padding.
PAD = 0.35  # A breath before the voice starts and after it ends.
# Define the fade length, in seconds, at both ends of every clip.  # Constant: fade.
FADE = 0.35  # Short fades to black read as clean cuts in a slideshow demo.
# Define the frame rate of the finished video.  # Constant: fps.
FPS = 30  # Standard for hackathon embeds and video hosts.

# Start the helper that runs a command and fails loudly on error.  # Function: run.
def run(cmd, input_text=None):  # Execute one external command, optionally feeding it stdin text.
    # Run the command, capturing its output for diagnostics.  # Step: execute.
    done = subprocess.run(cmd, input=input_text, capture_output=True, text=True)  # ffmpeg and friends report on stderr.
    # Turn any non-zero exit into an exception carrying the tail of the output.  # Step: check.
    if done.returncode != 0:  # Zero means success for all three tools.
        raise RuntimeError("Command failed: " + " ".join(cmd) + "\n" + (done.stderr or done.stdout)[-2000:])  # Keep the useful end of the log.
    # Hand back the completed process for callers that need stdout.  # Step: return.
    return done  # ffprobe results are read from here.

# Start the helper that measures a media file's duration in seconds.  # Function: duration_of.
def duration_of(path):  # Ask ffprobe how long a media file plays.
    # Run ffprobe and ask for the format duration as JSON.  # Step: probe.
    done = run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path])  # Quiet, machine-readable output.
    # Parse the JSON and return the duration as a float.  # Step: read.
    return float(json.loads(done.stdout)["format"]["duration"])  # Seconds, sub-second precision.

# Start the main build: narrate, time, render, concat, mux.  # Function: main.
def main():  # Produce quizforge-live-demo.mp4 in this folder.
    # Hold the per-segment clip durations (narration plus padding) for both render passes.  # State: durations.
    durations = []  # One float per segment, in script order.
    # Hold the spoken lines so the exact script is saved for the submission record.  # State: script lines.
    script_lines = []  # Written to narration.txt below.
    # First pass: synthesize every narration segment and measure it.  # Step: narration pass.
    for idx, (shot, text) in enumerate(SEGMENTS, start=1):  # idx is the 1-based segment number.
        # Build this segment's narration path.  # Step: name the file.
        seg_audio = os.path.join(AUDIO, f"seg{idx:02d}.mp3")  # audio/segNN.mp3.
        # Synthesize the narration only if it is not already on disk, so re-runs stay fast.  # Step: speak.
        if not os.path.exists(seg_audio):  # A kept segment is never re-voiced.
            run(["/opt/hatch/bin/tts", "speak", "--text", text, "--output", seg_audio])  # Default voice, text passed as an argument.
        # This clip lasts exactly as long as its narration plus a breath on each side.  # Step: time the clip.
        durations.append(duration_of(seg_audio) + 2 * PAD)  # Clip duration in seconds.
        # Record the spoken line for the script file.  # Step: log the line.
        script_lines.append(f"[{idx:02d}] ({shot}) {text}")  # Shot name plus its exact narration.
    # Save the narration script next to the video for the submission record.  # Step: write the script.
    with open(os.path.join(HERE, "narration.txt"), "w", encoding="utf-8") as handle:  # Open narration.txt for writing.
        handle.write("\n".join(script_lines) + "\n")  # One line per segment.
    # Second pass: render one silent video clip and one padded audio piece per segment.  # Step: render pass.
    for idx, (shot, text) in enumerate(SEGMENTS, start=1):  # Same order as the narration pass.
        # Read this segment's clip duration back from the table.  # Step: fetch duration.
        dur = durations[idx - 1]  # Seconds this shot stays on screen.
        # Convert the duration to a whole frame count for the zoom filter.  # Step: frame count.
        frames = max(1, round(dur * FPS))  # zoompan works in frames, not seconds.
        # Alternate the slow zoom direction per shot so the slideshow feels alive.  # Step: pick the zoom.
        zoom = "min(zoom+0.0009,1.13)" if idx % 2 == 1 else "if(eq(on,0),1.13,max(zoom-0.0009,1.0))"  # Odd shots push in; even shots pull back.
        # Build the video filter: normalize size, slow-zoom, pixel format, fades at both ends.  # Step: compose the filter.
        vf = (f"scale=2560:1440,zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1280x720:fps={FPS},"
              f"format=yuv420p,fade=t=in:st=0:d={FADE},fade=t=out:st={dur - FADE:.3f}:d={FADE}")  # 720p output, gentle motion, clean fades.
        # Render this shot's silent clip.  # Step: render the clip.
        run(["ffmpeg", "-y", "-loop", "1", "-i", os.path.join(SHOTS, shot), "-vf", vf, "-t", f"{dur:.3f}",  # One still becomes one clip.
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-r", str(FPS), os.path.join(CLIPS, f"vid{idx:02d}.mp4")])  # H.264, web-standard settings.
        # Build this segment's audio piece: narration delayed by the head pad, then padded and trimmed to the clip length.  # Step: pad the audio.
        run(["ffmpeg", "-y", "-i", os.path.join(AUDIO, f"seg{idx:02d}.mp3"), "-af", f"adelay={int(PAD * 1000)}|{int(PAD * 1000)},apad,atrim=0:{dur:.3f}",  # Silence, voice, silence — exactly one clip long.
             "-c:a", "aac", "-b:a", "160k", "-ar", "48000", os.path.join(CLIPS, f"aud{idx:02d}.m4a")])  # AAC at a fixed sample rate so concat is clean.
    # Write the concat lists for the video clips and the audio pieces.  # Step: prepare concat.
    with open(os.path.join(CLIPS, "list_v.txt"), "w", encoding="utf-8") as handle:  # Open the video list.
        handle.write("".join(f"file 'vid{idx:02d}.mp4'\n" for idx in range(1, len(SEGMENTS) + 1)))  # One line per clip, in order.
    with open(os.path.join(CLIPS, "list_a.txt"), "w", encoding="utf-8") as handle:  # Open the audio list.
        handle.write("".join(f"file 'aud{idx:02d}.m4a'\n" for idx in range(1, len(SEGMENTS) + 1)))  # One line per piece, in order.
    # Concatenate the video clips into one silent track (identical codecs, so stream copy is safe).  # Step: join video.
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(CLIPS, "list_v.txt"), "-c", "copy", os.path.join(CLIPS, "video_only.mp4")])  # The full picture track.
    # Concatenate the audio pieces into one narration track (re-encoded once for safety).  # Step: join audio.
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(CLIPS, "list_a.txt"), "-c:a", "aac", "-b:a", "160k", os.path.join(CLIPS, "audio_full.m4a")])  # The full voice track.
    # Mux picture and voice into the deliverable, with faststart so web players can stream it.  # Step: mux.
    final = os.path.join(HERE, "quizforge-live-demo.mp4")  # The finished demo video.
    run(["ffmpeg", "-y", "-i", os.path.join(CLIPS, "video_only.mp4"), "-i", os.path.join(CLIPS, "audio_full.m4a"), "-c", "copy", "-movflags", "+faststart", final])  # No re-encode: both tracks are already final-spec.
    # Probe the finished file and report its key facts.  # Step: verify.
    done = run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", final])  # Streams plus format.
    # Parse the probe output for the summary print.  # Step: summarize.
    info = json.loads(done.stdout)  # Dict of streams and format data.
    # Print the deliverable path and total duration.  # Step: report.
    print("FINAL:", final, "| duration:", info["format"]["duration"], "s | segments:", len(SEGMENTS), "| total narrated:", f"{sum(durations):.1f}", "s")  # One-line build summary.

# Run main() only when this file is executed directly.  # Entry-point guard.
if __name__ == "__main__":  # Check how the file was started.
    main()  # Start the build.

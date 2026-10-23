# assemble_v2.py - build the combined v2 demo film: the Stage 3b film, a title card, and the Stage 3d Live-tab addendum.  # Module header: purpose of this file.
# Written 2026-10-23 for Stage 3d of the GenAI Works Open Agent Hackathon entry. Demo tooling, not part of the shipped app.  # Provenance: demo tooling.
# The addendum stills come from capture_addendum.py (a genuine UI session), and every narration claim below was verified  # Honesty: narration source.
# against shots/addendum_meta.json: round 1 topics Airway/OPQRST/AVPU/MOI, deliberate misses Airway + OPQRST, grade 2/4,  # Honesty continued: the verified facts.
# round 2 focus [Airway, OPQRST] (== the missed topics), round 2 state COMPLETED: AVPU, MOI / REMAINING: Airway, OPQRST, 68 tokens.  # Honesty continued: the money shot.
# The render recipe (one clip per shot, timed to its narration, slow zoom, fades, concat, mux) follows assemble.py exactly.  # Method: same recipe as Stage 3b.
# Import the JSON module so ffprobe output can be parsed.  # Library: json.
import json  # Make the json module available.
# Import the OS module for path building.  # Library: os.
import os  # Make the os module available.
# Import subprocess so ffmpeg, ffprobe, and the tts CLI can be run.  # Library: subprocess.
import subprocess  # All media work is delegated to these three tools.
# Import the synchronous Playwright API, used once to render the title card still.  # Library: playwright.
from playwright.sync_api import sync_playwright  # The card is HTML, like the slides, so it matches the deck.
# Define the folder this script lives in.  # Constant: script folder.
HERE = os.path.dirname(os.path.abspath(__file__))  # Absolute path of the demo folder.
# Define the folder holding the screenshots from the capture scripts.  # Constant: shots folder.
SHOTS = os.path.join(HERE, "shots")  # Input stills live here.
# Define the folder that will hold the narration audio segments.  # Constant: audio folder.
AUDIO = os.path.join(HERE, "audio")  # One MP3 per narration segment.
# Define the folder that will hold the intermediate clips.  # Constant: clips folder.
CLIPS = os.path.join(HERE, "clips")  # Per-shot clips and the joined tracks live here.
# Define the Stage 3b film, the first part of the combined deliverable.  # Constant: original film.
ORIGINAL = os.path.join(HERE, "quizforge-live-demo.mp4")  # 2:02, verified in Stage 3b.
# Define the combined deliverable path.  # Constant: v2 film.
FINAL = os.path.join(HERE, "quizforge-live-demo-v2.mp4")  # Original + title card + addendum, target under 3:30.
# Define the title card still path (rendered from HTML below).  # Constant: card still.
CARD_PNG = os.path.join(SHOTS, "card_update.png")  # 2560x1440, the app palette.
# Define how long the title card stays on screen, in seconds.  # Constant: card duration.
CARD_DUR = 2.6  # Long enough to read the headline, short enough to keep moving.
# Define the title card's HTML: the deck's ink and forge orange, headline exactly as the submission describes it.  # Data: card markup.
CARD_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { width: 1280px; height: 720px; background: #1c2333; color: #f5efe4; font-family: Georgia, 'Times New Roman', serif; display: flex; flex-direction: column; justify-content: center; padding: 72px 96px; }
.kicker { font-size: 17px; letter-spacing: 0.24em; text-transform: uppercase; color: #ffb37a; margin-bottom: 22px; }
h1 { font-size: 58px; line-height: 1.12; margin-bottom: 20px; }
p { font-size: 25px; font-style: italic; opacity: 0.85; line-height: 1.45; }
</style></head><body>
<div class="kicker">QuizForge Live · Update</div>
<h1>Update: the loop, live in the browser</h1>
<p>Since the film above was shot, the Live tab shipped. Same app, same offline engine — now the loop plays in the UI. Here it is, playing a real round.</p>
</body></html>"""  # The card text: headline plus one honest framing line.
# Define the addendum beats: (screenshot filename, narration text), facts verified against addendum_meta.json.  # Data: the addendum script.
SEGMENTS = [  # One tuple per shot, in film order.
    ("shot09_live_setup.png", "Update — the loop now runs live in the browser. This is the new Live tab: same app, same offline engine, and the banner says exactly that. No keys, nothing hidden."),  # The Live tab and its honesty banner.
    ("shot10_live_round1.png", "Round one, planned right on the page by the Meterless Markovian engine — focus, difficulty, strategy — with the bounded learner state underneath: sixty-one tokens of carryover. Four questions, dealt in the browser."),  # Round 1's plan and visible state.
    ("shot11_live_grade.png", "I answer in the browser and deliberately miss Airway and O P Q R S T. Instant grade — two of four — every miss quoting the study material back at me, the missed topics pinned as pills."),  # The graded round, misses pinned.
    ("shot12_live_round2.png", "One click plans round two — and its focus lands on exactly those two misses. The state reads: completed, A V P U and M O I; remaining, Airway and O P Q R S T. Sixty-eight tokens. The loop now happens where the learner sits: in the browser."),  # Round 2's plan: focus equals the misses.
]  # End of the addendum script.
# Define the narration head/tail padding, in seconds, inside every clip (same as assemble.py).  # Constant: padding.
PAD = 0.35  # A breath before the voice starts and after it ends.
# Define the fade length, in seconds, at both ends of every clip (same as assemble.py).  # Constant: fade.
FADE = 0.35  # Short fades to black read as clean cuts in a slideshow demo.
# Define the frame rate of the finished video (same as assemble.py).  # Constant: fps.
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

# Start the helper that renders one still into a silent, faded video clip of a given length.  # Function: render_clip.
def render_clip(shot_path, dur, out_path, zoom_in):  # One still becomes one 720p clip, assemble.py's recipe.
    # Convert the duration to a whole frame count for the zoom filter.  # Step: frame count.
    frames = max(1, round(dur * FPS))  # zoompan works in frames, not seconds.
    # Alternate the slow zoom direction per shot so the slideshow feels alive.  # Step: pick the zoom.
    zoom = "min(zoom+0.0009,1.13)" if zoom_in else "if(eq(on,0),1.13,max(zoom-0.0009,1.0))"  # Push in or pull back.
    # Build the video filter: normalize size, slow-zoom, pixel format, fades at both ends.  # Step: compose the filter.
    vf = (f"scale=2560:1440,zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1280x720:fps={FPS},"
          f"format=yuv420p,fade=t=in:st=0:d={FADE},fade=t=out:st={dur - FADE:.3f}:d={FADE}")  # 720p output, gentle motion, clean fades.
    # Render the silent clip.  # Step: render.
    run(["ffmpeg", "-y", "-loop", "1", "-i", shot_path, "-vf", vf, "-t", f"{dur:.3f}",  # One still becomes one clip.
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-r", str(FPS), out_path])  # H.264, web-standard settings.

# Start the main build: card, addendum, combine, verify.  # Function: main.
def main():  # Produce quizforge-live-demo-v2.mp4 in this folder.
    # Render the title card still from its HTML, at the same 2x scale as the captures.  # Step: card still.
    with sync_playwright() as pw:  # The context manager closes everything on exit.
        # Launch headless Chromium (Playwright's build).  # Step: start the browser.
        browser = pw.chromium.launch()  # The same driver the captures used.
        # Create a page at the card's CSS size, doubled for crisp pixels.  # Step: size the page.
        page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)  # 1280x720 CSS pixels, 2560x1440 image pixels.
        # Load the card markup directly (no file needed for a one-off still).  # Step: load the card.
        page.set_content(CARD_HTML)  # The ink-and-orange card.
        # Save the card as a PNG in the shots folder.  # Step: capture the card.
        page.screenshot(path=CARD_PNG)  # Full viewport, exactly one card.
        # Close the browser cleanly.  # Step: shut down.
        browser.close()  # Frees the Chromium processes.
    # Render the title card's silent video clip at the fixed card duration (no zoom: it is a graphic, not a photo).  # Step: card clip.
    render_clip(CARD_PNG, CARD_DUR, os.path.join(CLIPS, "card.mp4"), True)  # The push-in is barely perceptible at 2.6 s.
    # Build the title card's silent audio piece: pure silence, exactly one card long.  # Step: card audio.
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{CARD_DUR:.3f}",  # A silent stereo bed.
         "-c:a", "aac", "-b:a", "160k", os.path.join(CLIPS, "card_aud.m4a")])  # Same codec settings as the narration pieces.
    # Hold the per-segment clip durations (narration plus padding) for the render pass.  # State: durations.
    durations = []  # One float per segment, in script order.
    # Hold the spoken lines so the exact script is saved for the submission record.  # State: script lines.
    script_lines = []  # Written to narration_addendum.txt below.
    # First pass: synthesize every addendum narration segment and measure it.  # Step: narration pass.
    for idx, (shot, text) in enumerate(SEGMENTS, start=1):  # idx is the 1-based addendum segment number.
        # Build this segment's narration path (the "add" prefix keeps it clear of assemble.py's segNN files).  # Step: name the file.
        seg_audio = os.path.join(AUDIO, f"add{idx:02d}.mp3")  # audio/addNN.mp3.
        # Synthesize the narration only if it is not already on disk, so re-runs stay fast.  # Step: speak.
        if not os.path.exists(seg_audio):  # A kept segment is never re-voiced.
            run(["/opt/hatch/bin/tts", "speak", "--text", text, "--output", seg_audio])  # Default voice, text passed as an argument.
        # This clip lasts exactly as long as its narration plus a breath on each side.  # Step: time the clip.
        durations.append(duration_of(seg_audio) + 2 * PAD)  # Clip duration in seconds.
        # Record the spoken line for the script file.  # Step: log the line.
        script_lines.append(f"[add{idx:02d}] ({shot}) {text}")  # Shot name plus its exact narration.
    # Save the addendum narration script next to the video for the submission record.  # Step: write the script.
    with open(os.path.join(HERE, "narration_addendum.txt"), "w", encoding="utf-8") as handle:  # Open narration_addendum.txt for writing.
        handle.write("\n".join(script_lines) + "\n")  # One line per segment.
    # Second pass: render one silent video clip and one padded audio piece per addendum segment.  # Step: render pass.
    for idx, (shot, text) in enumerate(SEGMENTS, start=1):  # Same order as the narration pass.
        # Read this segment's clip duration back from the table.  # Step: fetch duration.
        dur = durations[idx - 1]  # Seconds this shot stays on screen.
        # Render this shot's silent clip, alternating zoom direction as in assemble.py.  # Step: render the clip.
        render_clip(os.path.join(SHOTS, shot), dur, os.path.join(CLIPS, f"avid{idx:02d}.mp4"), idx % 2 == 1)  # Odd shots push in; even shots pull back.
        # Build this segment's audio piece: narration delayed by the head pad, then padded and trimmed to the clip length.  # Step: pad the audio.
        run(["ffmpeg", "-y", "-i", os.path.join(AUDIO, f"add{idx:02d}.mp3"), "-af", f"adelay={int(PAD * 1000)}|{int(PAD * 1000)},apad,atrim=0:{dur:.3f}",  # Silence, voice, silence — exactly one clip long.
             "-c:a", "aac", "-b:a", "160k", "-ar", "48000", os.path.join(CLIPS, f"aaud{idx:02d}.m4a")])  # AAC at a fixed sample rate so concat is clean.
    # Write the concat lists for the addendum: title card first, then the four beats, video and audio separately.  # Step: prepare concat.
    with open(os.path.join(CLIPS, "list_v2_v.txt"), "w", encoding="utf-8") as handle:  # Open the addendum video list.
        handle.write("file 'card.mp4'\n" + "".join(f"file 'avid{idx:02d}.mp4'\n" for idx in range(1, len(SEGMENTS) + 1)))  # Card, then one line per beat.
    with open(os.path.join(CLIPS, "list_v2_a.txt"), "w", encoding="utf-8") as handle:  # Open the addendum audio list.
        handle.write("file 'card_aud.m4a'\n" + "".join(f"file 'aaud{idx:02d}.m4a'\n" for idx in range(1, len(SEGMENTS) + 1)))  # Silence, then one line per piece.
    # Concatenate the addendum video clips into one silent track (identical codecs, so stream copy is safe).  # Step: join addendum video.
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(CLIPS, "list_v2_v.txt"), "-c", "copy", os.path.join(CLIPS, "addendum_video.mp4")])  # Card plus four beats.
    # Concatenate the addendum audio pieces into one track (re-encoded once for safety).  # Step: join addendum audio.
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(CLIPS, "list_v2_a.txt"), "-c:a", "aac", "-b:a", "160k", os.path.join(CLIPS, "addendum_audio.m4a")])  # Silence plus narration.
    # Mux the addendum into a standalone part file, so the final combine has three clean inputs.  # Step: mux the addendum.
    addendum = os.path.join(CLIPS, "addendum.mp4")  # The titled addendum as one file.
    run(["ffmpeg", "-y", "-i", os.path.join(CLIPS, "addendum_video.mp4"), "-i", os.path.join(CLIPS, "addendum_audio.m4a"), "-c", "copy", "-movflags", "+faststart", addendum])  # No re-encode at this stage.
    # Combine original + addendum into the v2 deliverable with one re-encode, so timestamps and codecs are uniform.  # Step: combine.
    run(["ffmpeg", "-y", "-i", ORIGINAL, "-i", addendum,  # The Stage 3b film, then the titled addendum.
         "-filter_complex", "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]",  # One continuous picture and voice.
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-ar", "48000",  # The house spec, end to end.
         "-movflags", "+faststart", FINAL])  # Web-streamable output.
    # Probe the finished file and report its key facts.  # Step: verify.
    done = run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", FINAL])  # Streams plus format.
    # Parse the probe output for the summary print.  # Step: summarize.
    info = json.loads(done.stdout)  # Dict of streams and format data.
    # Print the deliverable's duration and size, plus the addendum's own length for the report.  # Step: report.
    print("FINAL:", FINAL, "| duration:", info["format"]["duration"], "s | size:", info["format"]["size"], "bytes")  # The combined film.
    print("ADDENDUM (card + beats):", f"{CARD_DUR + sum(durations):.1f}", "s | narrated beats:", len(SEGMENTS))  # The appended part alone.

# Run main() only when this file is executed directly.  # Entry-point guard.
if __name__ == "__main__":  # Check how the file was started.
    main()  # Start the build.

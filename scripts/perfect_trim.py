#!/usr/bin/env python3
"""
perfect_trim.py — Detect and remove duplicate consecutive sentences from a video.

Extracts audio with MoviePy, transcribes with Whisper, flags any two back-to-back
sentences that are 85%+ similar, cuts the first attempt, and exports a clean video.

Requirements:
    pip install openai-whisper moviepy

Usage:
    py perfect_trim.py input.mp4
    py perfect_trim.py input.mp4 -o output.mp4
    py perfect_trim.py input.mp4 --threshold 0.90 --dry-run
"""

import argparse
import sys
import tempfile
import wave
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np


# ── Audio extraction ──────────────────────────────────────────────────────────

def extract_audio(video_path: str) -> np.ndarray:
    """
    Write a 16 kHz mono WAV via MoviePy's bundled ffmpeg, then read it back
    with the stdlib wave module. Returns float32 in [-1, 1]. No system ffmpeg needed.
    """
    from moviepy import VideoFileClip

    print("Extracting audio...")
    clip = VideoFileClip(video_path)

    if clip.audio is None:
        clip.close()
        sys.exit(f"No audio track found in: {video_path}")

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()

    try:
        clip.audio.write_audiofile(
            tmp.name,
            fps=16_000,
            nbytes=2,
            codec="pcm_s16le",
            logger=None,
        )
        clip.close()

        with wave.open(tmp.name, "rb") as wf:
            channels = wf.getnchannels()
            raw = wf.readframes(wf.getnframes())

        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)

        if channels > 1:
            samples = samples.reshape(-1, channels).mean(axis=1)

        peak = np.abs(samples).max()
        if peak > 0:
            samples /= peak

        print(f"Audio: {len(samples) / 16_000:.1f}s extracted.")
        return np.ascontiguousarray(samples)

    finally:
        Path(tmp.name).unlink(missing_ok=True)


# ── Transcription ─────────────────────────────────────────────────────────────

def transcribe(audio: np.ndarray, model_name: str) -> list[dict]:
    """
    Transcribe audio at segment level using Whisper.
    Returns [{start, end, text}, ...] — one entry per spoken sentence or phrase.
    Passing a numpy array avoids Whisper's internal ffmpeg dependency.
    """
    try:
        import whisper
    except ImportError:
        sys.exit("Missing dependency. Run: pip install openai-whisper")

    print(f"Loading Whisper '{model_name}' model...")
    model = whisper.load_model(model_name)

    print("Transcribing... (may take a few minutes on CPU)")
    result = model.transcribe(audio, word_timestamps=False, language="en")

    segments = [
        {
            "start": float(s["start"]),
            "end":   float(s["end"]),
            "text":  s["text"].strip(),
        }
        for s in result["segments"]
        if s["text"].strip()
    ]

    print(f"Found {len(segments)} sentence segment(s).\n")
    return segments


# ── Duplicate detection ───────────────────────────────────────────────────────

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()


def find_duplicate_cuts(segments: list[dict], threshold: float) -> list[tuple[float, float]]:
    """
    Compare each sentence to the one immediately after it.
    If they are >= threshold similar, the first sentence is marked for removal.
    The second sentence (the speaker's clean attempt) is always kept.
    """
    cuts = []
    i = 0

    while i < len(segments) - 1:
        current = segments[i]
        nxt     = segments[i + 1]

        sim = similarity(current["text"], nxt["text"])

        if sim >= threshold:
            print(
                f"  [{current['start']:.2f}s – {current['end']:.2f}s]  "
                f"sim={sim:.0%}\n"
                f"    CUT:  \"{current['text']}\"\n"
                f"    KEEP: \"{nxt['text']}\"\n"
            )
            cuts.append((current["start"], current["end"]))
            i += 2      # skip both; next iteration starts at the sentence after the kept one
        else:
            i += 1

    return cuts


# ── Video splicing ────────────────────────────────────────────────────────────

def cuts_to_keep(
    cuts: list[tuple[float, float]],
    total_duration: float,
    padding: float,
) -> list[tuple[float, float]]:
    """Convert cut regions to keep regions with a small padding at each edge."""
    keep = []
    cursor = 0.0

    for cut_start, cut_end in cuts:
        end_of_keep = max(cursor, cut_start - padding)
        if end_of_keep - cursor > 0.05:
            keep.append((cursor, end_of_keep))
        cursor = min(total_duration, cut_end + padding)

    if total_duration - cursor > 0.05:
        keep.append((cursor, total_duration))

    return keep


def export(
    input_path: str,
    output_path: str,
    cuts: list[tuple[float, float]],
    padding: float,
) -> None:
    from moviepy import VideoFileClip, concatenate_videoclips

    clip = VideoFileClip(input_path)
    keep = cuts_to_keep(cuts, clip.duration, padding)

    removed = sum(e - s for s, e in cuts)
    print(f"Removing {len(cuts)} duplicate(s) — {removed:.1f}s total.")
    print(f"Final duration: ~{clip.duration - removed:.1f}s\n")

    subclips = [clip.subclipped(s, e) for s, e in keep]
    final = concatenate_videoclips(subclips)
    final.write_videofile(output_path, logger="bar")

    clip.close()
    final.close()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Cut duplicate consecutive sentences from a video.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input",
                        help="Input video file")
    parser.add_argument("--output", "-o", default=None,
                        help="Output path (default: <input>_trimmed.mp4)")
    parser.add_argument("--model", "-m", default="base",
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model size")
    parser.add_argument("--threshold", "-t", type=float, default=0.85,
                        help="Similarity threshold to flag a sentence as a duplicate")
    parser.add_argument("--padding", "-p", type=float, default=0.05,
                        help="Seconds of audio kept on each side of a cut")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show duplicates without exporting the video")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"File not found: {input_path}")

    output_path = args.output or str(input_path.parent / f"{input_path.stem}_trimmed.mp4")

    audio    = extract_audio(str(input_path))
    segments = transcribe(audio, args.model)

    if not segments:
        sys.exit("No speech detected. Check the video has audible audio.")

    print(f"Scanning {len(segments)} segment(s) for duplicates "
          f"(threshold={args.threshold:.0%})...\n")

    cuts = find_duplicate_cuts(segments, args.threshold)

    if not cuts:
        print("No duplicates found — video is already clean.")
        sys.exit(0)

    print(f"{len(cuts)} duplicate(s) found.")

    if args.dry_run:
        print("\n--dry-run active: no video written.")
        sys.exit(0)

    export(str(input_path), output_path, cuts, args.padding)
    print(f"Done. Saved to: {output_path}")


if __name__ == "__main__":
    main()

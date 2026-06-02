#!/usr/bin/env python3
"""
word_dedup.py — Remove repeated consecutive words from a video.

Catches stutters like "I I want", "the the enzyme", "so so basically".
Transcribes with Whisper word timestamps, finds back-to-back duplicate
words, cuts the first occurrence, and exports a clean video.

Requirements:
    pip install openai-whisper moviepy

Usage:
    py word_dedup.py input.mp4
    py word_dedup.py input.mp4 -o clean.mp4
    py word_dedup.py input.mp4 --dry-run
"""

import argparse
import re
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np


# ── Audio extraction ──────────────────────────────────────────────────────────

def extract_audio(video_path: str) -> np.ndarray:
    """
    MoviePy writes a 16 kHz mono WAV via its bundled ffmpeg (imageio_ffmpeg).
    stdlib wave reads it back — no system ffmpeg required on Windows.
    Returns float32 normalized to [-1, 1].
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
            tmp.name, fps=16_000, nbytes=2, codec="pcm_s16le", logger=None
        )
        clip.close()

        with wave.open(tmp.name, "rb") as wf:
            channels = wf.getnchannels()
            raw      = wf.readframes(wf.getnframes())

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
    Returns a flat list of {word, start, end} using Whisper word timestamps.
    Passing a numpy array bypasses Whisper's internal ffmpeg call.
    """
    try:
        import whisper
    except ImportError:
        sys.exit("Missing dependency. Run: pip install openai-whisper")

    print(f"Loading Whisper '{model_name}' model...")
    model = whisper.load_model(model_name)

    print("Transcribing (may take a few minutes on CPU)...")
    result = model.transcribe(audio, word_timestamps=True, language="en")

    words = []
    for segment in result["segments"]:
        for w in segment.get("words", []):
            clean = re.sub(r"[^\w'-]", "", w["word"]).strip().lower()
            if clean:
                words.append({
                    "word":  clean,
                    "start": float(w["start"]),
                    "end":   float(w["end"]),
                })

    print(f"Transcribed {len(words)} word(s).\n")
    return words


# ── Duplicate word detection ──────────────────────────────────────────────────

def find_repeated_words(words: list[dict]) -> list[tuple[float, float]]:
    """
    Walk the word list and flag any word that is identical to the one
    immediately after it. The FIRST occurrence is cut; the second is kept.

    Handles runs of 3+ repetitions ("I I I want") by re-checking after
    each cut until no more consecutive matches remain at that position.
    """
    cuts = []
    i = 0

    while i < len(words) - 1:
        current = words[i]["word"]
        nxt     = words[i + 1]["word"]

        if current == nxt:
            print(
                f"  [{words[i]['start']:.2f}s – {words[i]['end']:.2f}s]"
                f"  repeated word: \"{current}\""
            )
            cuts.append((words[i]["start"], words[i]["end"]))
            # Don't advance i — re-check the kept word against the one after it
            # so runs like "I I I" are all caught in a single pass
            words.pop(i)
        else:
            i += 1

    return cuts


# ── Video splicing ────────────────────────────────────────────────────────────

def cuts_to_keep(
    cuts: list[tuple[float, float]],
    total: float,
    pad: float,
) -> list[tuple[float, float]]:
    """
    Invert cut regions into keep regions.
    pad extends each keep segment slightly into the cut to avoid clipping
    the very end of a word that borders the duplicate.
    """
    keep   = []
    cursor = 0.0

    for cut_start, cut_end in cuts:
        seg_end = min(total, max(cursor, cut_start + pad))
        if seg_end - cursor > 0.02:
            keep.append((cursor, seg_end))
        cursor = min(total, cut_end + pad)

    if total - cursor > 0.02:
        keep.append((cursor, total))

    return keep


def export(
    input_path: str,
    output_path: str,
    cuts: list[tuple[float, float]],
    pad: float,
) -> None:
    from moviepy import VideoFileClip, concatenate_videoclips

    clip = VideoFileClip(input_path)
    keep = cuts_to_keep(cuts, clip.duration, pad)

    removed = sum(e - s for s, e in cuts)
    print(f"\nRemoving {len(cuts)} repeated word(s) — {removed:.2f}s total.")
    print(f"Final duration: ~{clip.duration - removed:.1f}s\n")

    subclips = [clip.subclipped(s, e) for s, e in keep]
    final    = concatenate_videoclips(subclips)
    final.write_videofile(output_path, logger="bar")

    clip.close()
    final.close()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Remove repeated consecutive words from a video.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input",
                        help="Input video file (mp4, mkv, mov, …)")
    parser.add_argument("--output", "-o", default=None,
                        help="Output path (default: <input>_wordclean.mp4)")
    parser.add_argument("--model", "-m", default="base",
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model size")
    parser.add_argument("--pad", "-p", type=float, default=0.05,
                        help="Seconds of buffer kept around each cut (default 50ms)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show repeated words without editing the video")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"File not found: {input_path}")

    output_path = args.output or str(
        input_path.parent / f"{input_path.stem}_wordclean.mp4"
    )

    audio = extract_audio(str(input_path))
    words = transcribe(audio, args.model)

    if not words:
        sys.exit("No speech detected. Check the video has audible audio.")

    print(f"Scanning {len(words)} word(s) for consecutive repeats...\n")
    cuts = find_repeated_words(words)

    if not cuts:
        print("No repeated words found — video is already clean.")
        sys.exit(0)

    print(f"\n{len(cuts)} repeated word(s) found.")

    if args.dry_run:
        print("\n--dry-run: no video written.")
        sys.exit(0)

    export(str(input_path), output_path, cuts, args.pad)
    print(f"\nDone. Saved to: {output_path}")


if __name__ == "__main__":
    main()

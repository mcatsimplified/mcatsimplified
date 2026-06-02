#!/usr/bin/env python3
"""
dupe_cut.py — Remove back-to-back duplicate sentences and phrases from a video.

Requirements:
    pip install openai-whisper moviepy

Usage:
    py dupe_cut.py input.mp4
    py dupe_cut.py input.mp4 -o clean.mp4
    py dupe_cut.py input.mp4 -o clean.mp4 --threshold 0.75
    py dupe_cut.py input.mp4 --dry-run
"""

import argparse
import sys
import tempfile
import wave
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np


# ── Stage 1: Audio extraction ─────────────────────────────────────────────────

def extract_audio(video_path: str) -> np.ndarray:
    """
    Use MoviePy to write a 16 kHz mono WAV, then read it back with the stdlib
    wave module. Returns a float32 numpy array normalized to [-1, 1].

    MoviePy ships with imageio_ffmpeg (a self-contained bundled ffmpeg binary),
    so no system-level ffmpeg install is required on Windows or any platform.
    The stdlib wave reader that follows is pure Python — no external deps at all.
    """
    from moviepy import VideoFileClip

    print("Extracting audio...")
    clip = VideoFileClip(video_path)

    if clip.audio is None:
        clip.close()
        sys.exit(f"Error: no audio track found in '{video_path}'.")

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()

    try:
        # write_audiofile uses MoviePy's bundled imageio_ffmpeg — not system ffmpeg
        clip.audio.write_audiofile(
            tmp.name,
            fps=16_000,
            nbytes=2,               # 16-bit PCM
            codec="pcm_s16le",
            logger=None,            # suppress moviepy progress bar
        )
        clip.close()

        # Read back with Python's built-in wave module — zero external dependencies
        with wave.open(tmp.name, "rb") as wf:
            n_channels = wf.getnchannels()
            raw = wf.readframes(wf.getnframes())

        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)

        # Mix stereo → mono
        if n_channels > 1:
            samples = samples.reshape(-1, n_channels).mean(axis=1)

        # Normalize to [-1, 1] — Whisper silently returns nothing if out of range
        peak = np.abs(samples).max()
        if peak > 0:
            samples /= peak

        print(f"Audio: {len(samples) / 16_000:.1f}s  |  peak={peak:.0f}  |  "
              f"normalized peak={np.abs(samples).max():.4f}")
        return np.ascontiguousarray(samples)

    finally:
        Path(tmp.name).unlink(missing_ok=True)


# ── Stage 2: Transcription ────────────────────────────────────────────────────

def transcribe(audio: np.ndarray, model_name: str) -> list[dict]:
    """
    Transcribe using Whisper at segment level (full sentences/phrases with
    start + end timestamps). Passing a numpy array bypasses Whisper's internal
    ffmpeg call, keeping us fully ffmpeg-on-PATH independent.
    """
    try:
        import whisper
    except ImportError:
        sys.exit("openai-whisper not installed. Run: pip install openai-whisper")

    print(f"\nLoading Whisper '{model_name}' model (downloads ~74 MB on first use)...")
    model = whisper.load_model(model_name)

    print("Transcribing (this takes a while on CPU — grab a coffee)...")
    result = model.transcribe(
        audio,
        word_timestamps=False,   # segment-level only — faster and enough for phrase matching
        language="en",
    )

    segments = [
        {"start": float(s["start"]), "end": float(s["end"]), "text": s["text"].strip()}
        for s in result["segments"]
        if s["text"].strip()
    ]
    print(f"Transcript: {len(segments)} segment(s) detected.\n")
    return segments


# ── Stage 3: Duplicate detection ──────────────────────────────────────────────

def phrase_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()


def find_cuts(
    segments: list[dict],
    threshold: float,
    max_window: int,
) -> list[tuple[float, float]]:
    """
    Walk the segment list looking for back-to-back repeated phrases.
    Checks windows of 1 → max_window consecutive segments so it catches
    both single-sentence stutters and multi-sentence re-takes.

    The FIRST occurrence is always marked for removal; the second (the
    speaker's intended version) is kept.
    """
    cuts = []
    i = 0

    while i < len(segments):
        matched = False

        # Try larger windows first so multi-segment matches beat single-word ones
        for n in range(min(max_window, len(segments) - i), 0, -1):
            a_segs = segments[i : i + n]
            b_segs = segments[i + n : i + 2 * n]

            if len(b_segs) < n:
                continue

            a_text = " ".join(s["text"] for s in a_segs)
            b_text = " ".join(s["text"] for s in b_segs)
            sim = phrase_similarity(a_text, b_text)

            if sim >= threshold:
                cut_start = a_segs[0]["start"]
                cut_end   = a_segs[-1]["end"]
                label     = "sentence" if n == 1 else f"{n}-segment phrase"
                preview   = a_text[:70] + ("…" if len(a_text) > 70 else "")
                print(f"  [{cut_start:.2f}s – {cut_end:.2f}s]  {label}  "
                      f"sim={sim:.0%}  →  cut: \"{preview}\"")
                cuts.append((cut_start, cut_end))
                i += n        # land on the kept (second) version
                matched = True
                break

        if not matched:
            i += 1

    return cuts


# ── Stage 4: Video splicing ───────────────────────────────────────────────────

def merge_adjacent(cuts: list[tuple[float, float]], slop: float = 0.1) -> list[tuple[float, float]]:
    """Merge cut regions that are within slop seconds of each other."""
    if not cuts:
        return []
    merged = [list(cuts[0])]
    for s, e in cuts[1:]:
        if s - merged[-1][1] <= slop:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


def cuts_to_keep(
    cuts: list[tuple[float, float]],
    total: float,
    padding: float,
) -> list[tuple[float, float]]:
    """Invert a list of cut regions into a list of keep regions."""
    keep = []
    cursor = 0.0
    for cut_start, cut_end in cuts:
        seg_end = max(cursor, cut_start - padding)
        if seg_end - cursor > 0.05:           # skip micro-fragments < 50ms
            keep.append((cursor, seg_end))
        cursor = min(total, cut_end + padding)
    if total - cursor > 0.05:
        keep.append((cursor, total))
    return keep


def export_video(
    input_path: str,
    output_path: str,
    cuts: list[tuple[float, float]],
    padding: float,
) -> None:
    from moviepy import VideoFileClip, concatenate_videoclips

    clip = VideoFileClip(input_path)
    keep = cuts_to_keep(cuts, clip.duration, padding)

    removed = sum(e - s for s, e in cuts)
    print(f"Removing {len(cuts)} region(s)  |  {removed:.1f}s cut  "
          f"({removed / clip.duration * 100:.1f}% of original)")
    print(f"Output duration: ~{clip.duration - removed:.1f}s\n")

    subclips = [clip.subclipped(s, e) for s, e in keep]
    final = concatenate_videoclips(subclips)
    final.write_videofile(output_path, logger="bar")

    clip.close()
    final.close()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Remove back-to-back duplicate sentences and phrases from a video.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input",
                        help="Input video file (mp4, mkv, mov, …)")
    parser.add_argument("--output", "-o", default=None,
                        help="Output path (default: <input>_clean.mp4)")
    parser.add_argument("--model", "-m", default="base",
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model — tiny: fastest; small/medium: more accurate")
    parser.add_argument("--threshold", "-t", type=float, default=0.80,
                        help="Similarity ratio (0–1) to flag two phrases as a duplicate")
    parser.add_argument("--max-window", type=int, default=3,
                        help="Max consecutive segments to group into one phrase for comparison")
    parser.add_argument("--padding", "-p", type=float, default=0.05,
                        help="Seconds of audio kept on each side of a cut for a clean join")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print detected duplicates without editing the video")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"File not found: {input_path}")

    output_path = args.output or str(input_path.parent / f"{input_path.stem}_clean.mp4")

    # 1. Extract audio (MoviePy → WAV → numpy, no system ffmpeg)
    audio = extract_audio(str(input_path))

    # 2. Transcribe at segment level (numpy → Whisper, no system ffmpeg)
    segments = transcribe(audio, args.model)
    if not segments:
        sys.exit("No speech detected. Check that the video has audible speech.")

    # 3. Detect duplicates
    print("Scanning for duplicates...\n")
    raw_cuts = find_cuts(segments, args.threshold, args.max_window)

    if not raw_cuts:
        print("No duplicates found — video is already clean.")
        sys.exit(0)

    cuts = merge_adjacent(raw_cuts)
    print(f"\n{len(cuts)} region(s) to cut.")

    if args.dry_run:
        print("\n--dry-run: no video was written.")
        sys.exit(0)

    # 4. Splice and export
    export_video(str(input_path), output_path, cuts, args.padding)
    print(f"\nDone. Saved to: {output_path}")


if __name__ == "__main__":
    main()

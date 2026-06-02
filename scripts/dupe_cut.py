#!/usr/bin/env python3
"""
dupe_cut.py — Remove spoken duplicate words, stuttered phrases, and repeated
              sentences from a video using Whisper + MoviePy.

Requires:
    pip install openai-whisper moviepy
    ffmpeg on PATH (already installed in this workspace)

Usage:
    python scripts/dupe_cut.py input.mp4
    python scripts/dupe_cut.py input.mp4 -o clean.mp4
    python scripts/dupe_cut.py input.mp4 --model small --min-similarity 0.80
    python scripts/dupe_cut.py input.mp4 --dry-run   # print cuts without editing

What it detects (all back-to-back within --max-gap seconds):
    Single-word stutter  :  "I... I want to"
    Phrase stutter       :  "the enzyme the enzyme kinetics"
    Sentence repeat      :  "This is important. This is important."

What it keeps:
    The SECOND occurrence (the intended version). The first is cut.
"""

import argparse
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path


# ── Transcription ─────────────────────────────────────────────────────────────

def load_audio_array(video_path: str) -> "np.ndarray":
    """
    Extract audio from a video using MoviePy and return a float32 mono array
    at 16 kHz — the format Whisper expects. No ffmpeg on PATH required.
    """
    from moviepy import VideoFileClip
    import numpy as np

    clip = VideoFileClip(video_path)
    if clip.audio is None:
        clip.close()
        raise ValueError(f"No audio track found in {video_path}")

    samples = clip.audio.to_soundarray(fps=16_000)
    clip.close()

    if samples.ndim > 1:
        samples = samples.mean(axis=1)

    # Whisper expects float32 in the range [-1, 1]
    return samples.astype("float32")


def transcribe(video_path: str, model_name: str) -> list[dict]:
    """
    Return [{word, start, end}, …] using Whisper word-level timestamps.
    Models download on first use (~74 MB for base, ~461 MB for small).
    """
    try:
        import whisper
    except ImportError:
        sys.exit("openai-whisper not installed. Run: pip install openai-whisper")

    print(f"Loading Whisper '{model_name}' model  (downloads on first use)...")
    model = whisper.load_model(model_name)

    print("Extracting audio...")
    audio = load_audio_array(video_path)

    # Pass the numpy array directly — bypasses Whisper's internal ffmpeg call
    print("Transcribing with word-level timestamps...")
    result = model.transcribe(audio, word_timestamps=True, language="en")

    words = []
    for segment in result["segments"]:
        for w in segment.get("words", []):
            clean = re.sub(r"[^\w'-]", "", w["word"]).strip().lower()
            if clean:
                words.append({"word": clean, "start": float(w["start"]), "end": float(w["end"])})

    return words


# ── Duplicate detection ───────────────────────────────────────────────────────

def normalize(word: str) -> str:
    return re.sub(r"[^\w]", "", word).lower()


def phrase_sim(a: list[dict], b: list[dict]) -> float:
    a_str = " ".join(normalize(w["word"]) for w in a)
    b_str = " ".join(normalize(w["word"]) for w in b)
    return SequenceMatcher(None, a_str, b_str).ratio()


def find_cuts(
    words: list[dict],
    max_phrase_len: int,
    min_similarity: float,
    max_gap: float,
) -> list[tuple[float, float]]:
    """
    Scan for back-to-back repeated phrases. Returns (start, end) pairs to cut.

    At each position we try phrase windows from longest→shortest so that
    multi-word phrase matches are preferred over single-word matches inside them.
    When a repeat is found the FIRST occurrence is marked for removal and we
    advance past it — the next iteration starts at the intended (second) version.
    """
    cuts = []
    i = 0

    while i < len(words):
        matched = False
        max_window = min(max_phrase_len, (len(words) - i) // 2)

        for n in range(max_window, 0, -1):
            a = words[i : i + n]
            b = words[i + n : i + 2 * n]

            if len(b) < n:
                continue

            # Skip if the gap between the two occurrences is suspiciously large
            gap = b[0]["start"] - a[-1]["end"]
            if gap > max_gap:
                continue

            sim = phrase_sim(a, b)
            if sim >= min_similarity:
                cut_start = a[0]["start"]
                cut_end   = a[-1]["end"]
                a_text = " ".join(w["word"] for w in a)
                b_text = " ".join(w["word"] for w in b)
                label = "stutter" if n == 1 else f"{n}-word phrase"
                print(f"  [{cut_start:.2f}s–{cut_end:.2f}s]  {label}  "
                      f"cut: '{a_text}'  →  keep: '{b_text}'  (sim={sim:.0%})")
                cuts.append((cut_start, cut_end))
                i += n          # skip the first (cut) occurrence
                matched = True
                break

        if not matched:
            i += 1

    return cuts


def merge_adjacent(cuts: list[tuple[float, float]], slop: float = 0.08) -> list[tuple[float, float]]:
    """Merge cuts that are within `slop` seconds of each other."""
    if not cuts:
        return []
    out = [list(cuts[0])]
    for start, end in cuts[1:]:
        if start - out[-1][1] <= slop:
            out[-1][1] = max(out[-1][1], end)
        else:
            out.append([start, end])
    return [(s, e) for s, e in out]


def cuts_to_keep(cuts: list[tuple[float, float]], total: float, pad: float) -> list[tuple[float, float]]:
    """Invert cut regions → keep regions, with `pad` seconds of cushion at each edge."""
    keep = []
    cursor = 0.0
    for cut_start, cut_end in cuts:
        seg_end = max(cursor, cut_start - pad)
        if seg_end - cursor > 0.02:
            keep.append((cursor, seg_end))
        cursor = min(total, cut_end + pad)
    if total - cursor > 0.02:
        keep.append((cursor, total))
    return keep


# ── Video editing ─────────────────────────────────────────────────────────────

def edit_video(
    input_path: str,
    output_path: str,
    cuts: list[tuple[float, float]],
    padding: float,
) -> None:
    from moviepy import VideoFileClip, concatenate_videoclips

    clip = VideoFileClip(input_path)
    keep = cuts_to_keep(cuts, clip.duration, padding)

    removed_s = sum(e - s for s, e in cuts)
    print(f"\nRemoving {len(cuts)} region(s) totalling {removed_s:.2f}s "
          f"({removed_s / clip.duration * 100:.1f}% of original).")
    print(f"Output duration: ~{clip.duration - removed_s:.2f}s\n")

    subclips = [clip.subclipped(s, e) for s, e in keep]
    final = concatenate_videoclips(subclips)
    final.write_videofile(output_path, logger="bar")
    clip.close()
    final.close()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Remove duplicate words, stutters, and repeated phrases from a video.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input", help="Input video file (mp4, mkv, mov, …)")
    parser.add_argument("--output", "-o", default=None,
                        help="Output path (default: <input>_deduped.mp4)")
    parser.add_argument("--model", "-m", default="base",
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model  —  tiny/base: fast; small/medium: more accurate")
    parser.add_argument("--max-phrase", type=int, default=8,
                        help="Max phrase length in words to compare for repeats")
    parser.add_argument("--min-similarity", type=float, default=0.85,
                        help="Similarity ratio (0–1) for two phrases to be treated as a repeat")
    parser.add_argument("--max-gap", type=float, default=4.0,
                        help="Max seconds between two occurrences to be treated as a stutter")
    parser.add_argument("--padding", type=float, default=0.04,
                        help="Seconds kept on each side of every cut for a clean join")
    parser.add_argument("--dry-run", action="store_true",
                        help="Transcribe and print detected duplicates without editing the video")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"File not found: {input_path}")

    output_path = args.output or str(input_path.parent / f"{input_path.stem}_deduped.mp4")

    # ── Transcribe
    words = transcribe(str(input_path), args.model)
    if not words:
        sys.exit("No speech found in transcript. Check that the video has audible speech.")
    print(f"\nTranscript: {len(words)} words detected.\n")

    # ── Detect
    print("Scanning for duplicates...\n")
    raw_cuts = find_cuts(
        words,
        max_phrase_len=args.max_phrase,
        min_similarity=args.min_similarity,
        max_gap=args.max_gap,
    )

    if not raw_cuts:
        print("\nNo duplicates detected — video is already clean.")
        sys.exit(0)

    cuts = merge_adjacent(raw_cuts)
    print(f"\n{len(cuts)} cut region(s) after merging.")

    if args.dry_run:
        print("\n--dry-run: skipping video export.")
        sys.exit(0)

    # ── Edit
    edit_video(str(input_path), output_path, cuts, args.padding)
    print(f"\nDone. Saved to: {output_path}")


if __name__ == "__main__":
    main()

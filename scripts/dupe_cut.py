#!/usr/bin/env python3
"""
dupe_cut.py — Remove back-to-back duplicate sentences from a video.

Uses word-level Whisper timestamps to rebuild sentences on punctuation and
pauses, then cuts any first-take duplicates at 75%+ similarity.

Requirements:
    pip install openai-whisper moviepy

Usage:
    py dupe_cut.py input.mp4
    py dupe_cut.py input.mp4 -o clean.mp4
    py dupe_cut.py input.mp4 --threshold 0.75 --dry-run
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
    MoviePy writes a 16 kHz mono WAV using its bundled ffmpeg (imageio_ffmpeg).
    stdlib wave reads it back as int16 — no system ffmpeg required on Windows.
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
            tmp.name,
            fps=16_000,
            nbytes=2,
            codec="pcm_s16le",
            logger=None,
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


# ── Stage 2: Transcription ────────────────────────────────────────────────────

def transcribe_words(audio: np.ndarray, model_name: str) -> list[dict]:
    """
    Transcribe with word_timestamps=True.
    Returns a flat list of {word, start, end} across the whole video.
    Passing a numpy array bypasses Whisper's internal ffmpeg dependency.
    """
    try:
        import whisper
    except ImportError:
        sys.exit("Missing dependency. Run: pip install openai-whisper")

    print(f"Loading Whisper '{model_name}' model...")
    model = whisper.load_model(model_name)

    print("Transcribing with word-level timestamps (this takes a few minutes on CPU)...")
    result = model.transcribe(audio, word_timestamps=True, language="en")

    words = []
    for segment in result["segments"]:
        for w in segment.get("words", []):
            text = w["word"].strip()
            if text:
                words.append({
                    "word":  text,
                    "start": float(w["start"]),
                    "end":   float(w["end"]),
                })

    print(f"Transcribed {len(words)} word(s).")
    return words


# ── Stage 3: Smart sentence rebuilding ───────────────────────────────────────

SENTENCE_ENDINGS = {".", "?", "!"}
CLAUSE_ENDINGS   = {","}

def build_sentences(words: list[dict], pause_threshold: float = 1.5) -> list[dict]:
    """
    Group words into sentences by splitting whenever:
      - A word ends with a sentence-ending punctuation mark (. ? !)
      - A word ends with a clause mark (, ) and the next pause is > pause_threshold
      - The silence gap between consecutive words exceeds pause_threshold seconds

    This produces tighter, more natural sentence boundaries than Whisper's
    default segments, which are often split mid-thought.
    """
    if not words:
        return []

    sentences  = []
    current    = []

    for i, word in enumerate(words):
        current.append(word)

        last_char          = word["word"].rstrip()[-1] if word["word"].strip() else ""
        is_sentence_end    = last_char in SENTENCE_ENDINGS
        is_clause_end      = last_char in CLAUSE_ENDINGS

        # Measure pause to the next word (infinite if this is the last word)
        if i < len(words) - 1:
            pause = words[i + 1]["start"] - word["end"]
        else:
            pause = float("inf")

        long_pause  = pause > pause_threshold
        is_last     = i == len(words) - 1

        # Flush the current sentence if we hit a natural boundary
        if is_sentence_end or (is_clause_end and long_pause) or long_pause or is_last:
            text = " ".join(w["word"].strip() for w in current).strip()
            if text:
                sentences.append({
                    "start": current[0]["start"],
                    "end":   current[-1]["end"],
                    "text":  text,
                })
            current = []

    return sentences


# ── Stage 4: Duplicate detection ─────────────────────────────────────────────

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()


def find_cuts(sentences: list[dict], threshold: float) -> list[tuple[float, float]]:
    """
    Compare every sentence to the one immediately after it.
    If similarity >= threshold the FIRST (bad) take is flagged for removal.
    The LAST (good) take is always kept.
    """
    cuts = []
    i = 0

    while i < len(sentences) - 1:
        a = sentences[i]
        b = sentences[i + 1]
        sim = similarity(a["text"], b["text"])

        if sim >= threshold:
            print(
                f"  [{a['start']:.2f}s – {a['end']:.2f}s]  sim={sim:.0%}\n"
                f"    CUT:  \"{a['text']}\"\n"
                f"    KEEP: \"{b['text']}\"\n"
            )
            cuts.append((a["start"], a["end"]))
            i += 2      # skip the kept sentence; resume comparison after it
        else:
            i += 1

    return cuts


# ── Stage 5: Video splicing ───────────────────────────────────────────────────

def cuts_to_keep(
    cuts: list[tuple[float, float]],
    total: float,
    padding: float,
) -> list[tuple[float, float]]:
    keep   = []
    cursor = 0.0

    for cut_start, cut_end in cuts:
        seg_end = max(cursor, cut_start - padding)
        if seg_end - cursor > 0.05:
            keep.append((cursor, seg_end))
        cursor = min(total, cut_end + padding)

    if total - cursor > 0.05:
        keep.append((cursor, total))

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
    print(f"Removing {len(cuts)} duplicate(s) — {removed:.1f}s "
          f"({removed / clip.duration * 100:.1f}% of original).")
    print(f"Final duration: ~{clip.duration - removed:.1f}s\n")

    subclips = [clip.subclipped(s, e) for s, e in keep]
    final    = concatenate_videoclips(subclips)
    final.write_videofile(output_path, logger="bar")

    clip.close()
    final.close()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Remove duplicate consecutive sentences from a video.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input",
                        help="Input video file (mp4, mkv, mov, …)")
    parser.add_argument("--output", "-o", default=None,
                        help="Output path (default: <input>_cut.mp4)")
    parser.add_argument("--model", "-m", default="base",
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model size")
    parser.add_argument("--threshold", "-t", type=float, default=0.75,
                        help="Similarity threshold (0–1) to flag a duplicate")
    parser.add_argument("--pause", type=float, default=1.5,
                        help="Silence gap in seconds that ends a sentence")
    parser.add_argument("--padding", "-p", type=float, default=0.05,
                        help="Seconds kept on each side of a cut for a clean join")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show duplicates without exporting the video")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"File not found: {input_path}")

    output_path = args.output or str(input_path.parent / f"{input_path.stem}_cut.mp4")

    # 1. Extract audio (no system ffmpeg)
    audio = extract_audio(str(input_path))

    # 2. Transcribe with word-level timestamps
    words = transcribe_words(audio, args.model)
    if not words:
        sys.exit("No speech detected. Check the video has audible audio.")

    # 3. Rebuild sentences from word timestamps
    sentences = build_sentences(words, pause_threshold=args.pause)
    print(f"Built {len(sentences)} sentence(s) from word timestamps.\n")

    # 4. Detect duplicates at 75% threshold
    print(f"Scanning for duplicates (threshold={args.threshold:.0%})...\n")
    cuts = find_cuts(sentences, args.threshold)

    if not cuts:
        print("No duplicates found — video is already clean.")
        sys.exit(0)

    print(f"{len(cuts)} duplicate(s) found.")

    if args.dry_run:
        print("\n--dry-run: no video written.")
        sys.exit(0)

    # 5. Splice and export
    export(str(input_path), output_path, cuts, args.padding)
    print(f"\nDone. Saved to: {output_path}")


if __name__ == "__main__":
    main()

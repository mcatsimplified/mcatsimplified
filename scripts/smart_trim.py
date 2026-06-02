#!/usr/bin/env python3
"""
smart_trim.py — Automatically remove repeated phrases AND dead air from a video.

Two things happen in one pass:
  1. Repeated phrases — any sentence/phrase repeated within a 40-second window
     is detected and the FIRST (bad) take is deleted. The clean take is kept.
  2. Dead air — silence longer than 0.5s is removed. The last word before each
     gap is always kept fully — the keep region extends 150ms into the silence
     so nothing gets clipped.

Requirements:
    pip install openai-whisper moviepy

Usage:
    py smart_trim.py input.mp4
    py smart_trim.py input.mp4 -o clean.mp4
    py smart_trim.py input.mp4 --dry-run
    py smart_trim.py input.mp4 --window 60 --silence-threshold 0.008
"""

import argparse
import re
import sys
import tempfile
import wave
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — Audio extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_audio(video_path: str) -> np.ndarray:
    """
    MoviePy writes a 16 kHz mono WAV via its bundled imageio_ffmpeg.
    stdlib wave reads it back — no system ffmpeg needed on Windows.
    Returns float32 normalized to [-1, 1].
    Extracted once and reused for both transcription and silence analysis.
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

        print(f"Audio: {len(samples) / 16_000:.1f}s  |  peak normalized to {np.abs(samples).max():.4f}")
        return np.ascontiguousarray(samples)

    finally:
        Path(tmp.name).unlink(missing_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — Transcription + sentence rebuilding
# ─────────────────────────────────────────────────────────────────────────────

def transcribe_words(audio: np.ndarray, model_name: str) -> list[dict]:
    """Transcribe with word-level timestamps. Returns [{word, start, end}, ...]."""
    try:
        import whisper
    except ImportError:
        sys.exit("Missing dependency. Run: pip install openai-whisper")

    print(f"\nLoading Whisper '{model_name}' model...")
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

    print(f"Transcribed {len(words)} word(s).")
    return words


def build_sentences(words: list[dict], pause_threshold: float = 1.5) -> list[dict]:
    """
    Group words into sentences by splitting on:
      - Sentence-ending punctuation  (. ? !)
      - Silence gap longer than pause_threshold seconds between words
    Returns [{start, end, text}, ...].
    """
    if not words:
        return []

    sentences = []
    current   = []

    for i, word in enumerate(words):
        current.append(word)
        last_char   = word["word"][-1] if word["word"] else ""
        is_sent_end = last_char in {".", "?", "!"}
        pause       = (words[i + 1]["start"] - word["end"]) if i < len(words) - 1 else float("inf")
        long_pause  = pause > pause_threshold

        if is_sent_end or long_pause or i == len(words) - 1:
            text = " ".join(w["word"] for w in current).strip()
            if text:
                sentences.append({
                    "start": current[0]["start"],
                    "end":   current[-1]["end"],
                    "text":  text,
                })
            current = []

    return sentences


# ─────────────────────────────────────────────────────────────────────────────
# Stage 3a — Repeated phrase detection (40-second window)
# ─────────────────────────────────────────────────────────────────────────────

def phrase_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()


def find_phrase_cuts(
    sentences: list[dict],
    window: float,
    threshold: float,
) -> list[tuple[float, float]]:
    """
    For every sentence, look ahead up to `window` seconds.
    If a later sentence matches at >= threshold, the FIRST (bad) take is cut.
    The LAST (clean) take is always kept.
    """
    cut_indices = set()
    cuts        = []

    for i in range(len(sentences)):
        if i in cut_indices:
            continue                       # already flagged, skip

        for j in range(i + 1, len(sentences)):
            gap = sentences[j]["start"] - sentences[i]["end"]
            if gap > window:
                break                      # outside 40-second window

            sim = phrase_similarity(sentences[i]["text"], sentences[j]["text"])
            if sim >= threshold:
                cut_indices.add(i)
                cuts.append((sentences[i]["start"], sentences[i]["end"]))
                print(
                    f"  [phrase {sentences[i]['start']:.2f}s – {sentences[i]['end']:.2f}s]"
                    f"  sim={sim:.0%}\n"
                    f"    CUT:  \"{sentences[i]['text']}\"\n"
                    f"    KEEP: \"{sentences[j]['text']}\"\n"
                )
                break

    return cuts


# ─────────────────────────────────────────────────────────────────────────────
# Stage 3b — Dead air detection
# ─────────────────────────────────────────────────────────────────────────────

def rms_chunks(audio: np.ndarray, fps: int = 16_000, chunk_dur: float = 0.02):
    """Split audio into 20ms chunks and return RMS per chunk."""
    chunk_size = max(1, int(fps * chunk_dur))
    remainder  = len(audio) % chunk_size
    padded     = np.pad(audio, (0, chunk_size - remainder)) if remainder else audio
    chunks     = padded.reshape(-1, chunk_size)
    return np.sqrt((chunks ** 2).mean(axis=1)), chunk_dur


def find_silence_cuts(
    audio: np.ndarray,
    threshold: float,
    min_silence: float,
    tail_pad: float,
) -> list[tuple[float, float]]:
    """
    Detect silence regions in the audio and return (start, end) pairs to cut.
    tail_pad extends every keep region INTO the silence so the last word
    before each gap is fully preserved — nothing gets clipped.
    """
    rms, chunk_dur = rms_chunks(audio)
    total          = len(audio) / 16_000

    silence_regions = []
    sil_start       = None

    for i, loud in enumerate(rms > threshold):
        t = i * chunk_dur
        if not loud:
            if sil_start is None:
                sil_start = t
        else:
            if sil_start is not None:
                if t - sil_start >= min_silence:
                    silence_regions.append((sil_start, t))
                sil_start = None

    if sil_start is not None and total - sil_start >= min_silence:
        silence_regions.append((sil_start, total))

    cuts = []
    for sil_start, sil_end in silence_regions:
        # Keep sil_start → sil_start+tail_pad (word tail), cut the rest of the gap
        cut_start = min(total, sil_start + tail_pad)
        cut_end   = sil_end
        if cut_end - cut_start > 0.05:    # only cut if there's meaningful dead air left
            cuts.append((cut_start, cut_end))
            print(
                f"  [silence  {cut_start:.2f}s – {cut_end:.2f}s]"
                f"  {cut_end - cut_start:.2f}s of dead air removed"
            )

    return cuts


# ─────────────────────────────────────────────────────────────────────────────
# Stage 4 — Merge cuts + export
# ─────────────────────────────────────────────────────────────────────────────

def merge_cuts(cuts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Sort and merge overlapping or adjacent cut regions."""
    if not cuts:
        return []
    sorted_cuts = sorted(cuts)
    merged      = [list(sorted_cuts[0])]
    for s, e in sorted_cuts[1:]:
        if s <= merged[-1][1] + 0.05:     # merge if gap is < 50ms
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


def cuts_to_keep(
    cuts: list[tuple[float, float]],
    total: float,
) -> list[tuple[float, float]]:
    """Invert cut regions into keep regions."""
    keep   = []
    cursor = 0.0
    for cut_start, cut_end in cuts:
        if cut_start - cursor > 0.02:
            keep.append((cursor, cut_start))
        cursor = min(total, cut_end)
    if total - cursor > 0.02:
        keep.append((cursor, total))
    return keep


def export(
    input_path: str,
    output_path: str,
    cuts: list[tuple[float, float]],
) -> None:
    from moviepy import VideoFileClip, concatenate_videoclips

    clip = VideoFileClip(input_path)
    keep = cuts_to_keep(cuts, clip.duration)

    removed = sum(e - s for s, e in cuts)
    print(f"\nTotal removed : {removed:.1f}s  ({removed / clip.duration * 100:.1f}% of original)")
    print(f"Final duration: ~{clip.duration - removed:.1f}s\n")

    subclips = [clip.subclipped(s, e) for s, e in keep]
    final    = concatenate_videoclips(subclips)
    final.write_videofile(output_path, logger="bar")

    clip.close()
    final.close()


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Remove repeated phrases and dead air from a video in one pass.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input",
                        help="Input video file (mp4, mkv, mov, …)")
    parser.add_argument("--output", "-o", default=None,
                        help="Output path (default: <input>_trimmed.mp4)")
    parser.add_argument("--model", "-m", default="base",
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model size")
    parser.add_argument("--window", type=float, default=40.0,
                        help="Seconds to look ahead for repeated phrases")
    parser.add_argument("--phrase-threshold", type=float, default=0.80,
                        help="Similarity ratio (0–1) to flag a phrase as a duplicate")
    parser.add_argument("--silence-threshold", type=float, default=0.008,
                        help="RMS level below which audio counts as silence")
    parser.add_argument("--min-silence", type=float, default=0.5,
                        help="Minimum silence duration in seconds to remove")
    parser.add_argument("--tail-pad", type=float, default=0.15,
                        help="Seconds to keep INTO each silence so word tails aren't clipped")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be cut without editing the video")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"File not found: {input_path}")

    output_path = args.output or str(
        input_path.parent / f"{input_path.stem}_trimmed.mp4"
    )

    # Extract audio once — reused for both transcription and silence analysis
    audio = extract_audio(str(input_path))

    # ── Repeated phrase detection ──────────────────────────────────────────
    words     = transcribe_words(audio, args.model)
    sentences = build_sentences(words)
    print(f"Built {len(sentences)} sentence(s).\n")

    print(f"Scanning for repeated phrases (window={args.window}s, "
          f"threshold={args.phrase_threshold:.0%})...\n")
    phrase_cuts = find_phrase_cuts(sentences, args.window, args.phrase_threshold)

    # ── Dead air detection ─────────────────────────────────────────────────
    print(f"Scanning for dead air (threshold={args.silence_threshold} RMS, "
          f"min={args.min_silence}s, tail-pad={args.tail_pad}s)...\n")
    silence_cuts = find_silence_cuts(
        audio,
        threshold=args.silence_threshold,
        min_silence=args.min_silence,
        tail_pad=args.tail_pad,
    )

    # ── Merge and report ───────────────────────────────────────────────────
    all_cuts = merge_cuts(phrase_cuts + silence_cuts)

    if not all_cuts:
        print("\nNothing to cut — video is already clean.")
        sys.exit(0)

    removed = sum(e - s for s, e in all_cuts)
    print(f"\n{'─' * 50}")
    print(f"Phrase cuts : {len(phrase_cuts)}")
    print(f"Silence cuts: {len(silence_cuts)}")
    print(f"Total cuts  : {len(all_cuts)}  ({removed:.1f}s to remove)")
    print(f"{'─' * 50}")

    if args.dry_run:
        print("\n--dry-run: no video written.")
        sys.exit(0)

    # ── Export ─────────────────────────────────────────────────────────────
    export(str(input_path), output_path, all_cuts)
    print(f"\nDone. Saved to: {output_path}")


if __name__ == "__main__":
    main()

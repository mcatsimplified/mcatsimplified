#!/usr/bin/env python3
"""
silence_cut.py — Remove silent segments from a video using MoviePy.

Usage:
    python scripts/silence_cut.py input.mp4
    python scripts/silence_cut.py input.mp4 --output trimmed.mp4
    python scripts/silence_cut.py input.mp4 --threshold 0.008 --min-silence 0.5 --padding 0.4

Flags:
    --threshold   RMS volume level below which audio counts as silent (default: 0.008).
                  Lower = more sensitive — quieter word tails are treated as speech, not silence.
                  Raise (e.g. 0.02) only if too much background noise is being kept.
    --min-silence Minimum continuous silence duration (seconds) to remove (default: 0.5).
    --padding     Seconds of audio preserved on each side of a cut (default: 0.4).
                  400ms ensures the trailing sound of a word is never clipped.
    --output, -o  Output path. Defaults to <input>_cut.mp4 in the same folder.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from moviepy import VideoFileClip, concatenate_videoclips


def rms_over_time(audio_array: np.ndarray, audio_fps: int, chunk_dur: float = 0.02):
    """
    Split audio into fixed-size chunks and return (rms_per_chunk, chunk_dur).
    chunk_dur is the actual time each RMS value represents.
    """
    mono = audio_array.mean(axis=1) if audio_array.ndim > 1 else audio_array
    chunk_size = max(1, int(audio_fps * chunk_dur))

    # Pad so length is a multiple of chunk_size
    remainder = len(mono) % chunk_size
    if remainder:
        mono = np.pad(mono, (0, chunk_size - remainder))

    chunks = mono.reshape(-1, chunk_size)
    rms = np.sqrt((chunks ** 2).mean(axis=1))
    return rms, chunk_dur


def find_keep_segments(
    rms: np.ndarray,
    chunk_dur: float,
    threshold: float,
    min_silence: float,
    padding: float,
    total_duration: float,
) -> list[tuple[float, float]]:
    """
    Return (start, end) pairs (in seconds) of regions to keep.
    Silence runs longer than min_silence are removed; padding is left at each edge.
    """
    # Collect silence regions
    silence_regions = []
    silence_start = None

    for i, loud in enumerate(rms > threshold):
        t = i * chunk_dur
        if not loud:
            if silence_start is None:
                silence_start = t
        else:
            if silence_start is not None:
                duration = t - silence_start
                if duration >= min_silence:
                    silence_regions.append((silence_start, t))
                silence_start = None

    # Catch silence that runs to the end of the clip
    if silence_start is not None:
        duration = total_duration - silence_start
        if duration >= min_silence:
            silence_regions.append((silence_start, total_duration))

    if not silence_regions:
        return [(0.0, total_duration)]

    # Invert silence regions → keep regions, trimmed by padding
    keep = []
    cursor = 0.0

    for sil_start, sil_end in silence_regions:
        # Floor with cursor so padding never produces a backwards/overlapping segment
        seg_end = max(cursor, sil_start - padding)
        if seg_end - cursor > 0.01:          # skip micro-segments < 10ms
            keep.append((cursor, seg_end))
        cursor = min(total_duration, sil_end + padding)

    if total_duration - cursor > 0.01:
        keep.append((cursor, total_duration))

    return keep


def cut_silence(
    input_path: str,
    output_path: str,
    threshold: float,
    min_silence: float,
    padding: float,
) -> None:
    print(f"\nLoading  : {input_path}")
    clip = VideoFileClip(input_path)

    if clip.audio is None:
        sys.exit("Error: this video has no audio track.")

    print(f"Duration : {clip.duration:.2f}s | Video FPS: {clip.fps} | Audio FPS: {clip.audio.fps}")
    print("Analysing audio...")

    audio_arr = clip.audio.to_soundarray(fps=clip.audio.fps)
    rms, chunk_dur = rms_over_time(audio_arr, clip.audio.fps)

    print(f"Threshold: {threshold} RMS | Min silence: {min_silence}s | Padding: {padding}s")

    keep = find_keep_segments(
        rms=rms,
        chunk_dur=chunk_dur,
        threshold=threshold,
        min_silence=min_silence,
        padding=padding,
        total_duration=clip.duration,
    )

    kept_duration = sum(e - s for s, e in keep)
    removed = clip.duration - kept_duration
    print(f"Segments : keeping {len(keep)}, removing {removed:.2f}s of silence "
          f"({removed / clip.duration * 100:.1f}% of original)")

    if not keep:
        sys.exit("Error: no speech detected — try lowering --threshold.")

    subclips = [clip.subclipped(start, end) for start, end in keep]
    final = concatenate_videoclips(subclips)

    print(f"Exporting: {output_path}  ({final.duration:.2f}s)\n")
    final.write_videofile(output_path, logger="bar")

    clip.close()
    final.close()
    print(f"\nDone. Saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Cut silent segments out of a video.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input", help="Input video file (mp4, mkv, mov, …)")
    parser.add_argument("--output", "-o", default=None,
                        help="Output file path (default: <input>_cut.mp4)")
    parser.add_argument("--threshold", "-t", type=float, default=0.008,
                        help="RMS volume threshold below which audio is silent "
                             "(lower = more sensitive, preserves quiet word tails)")
    parser.add_argument("--min-silence", "-s", type=float, default=0.5,
                        help="Minimum silence duration in seconds to cut")
    parser.add_argument("--padding", "-p", type=float, default=0.4,
                        help="Seconds of audio preserved on each side of a cut "
                             "(400ms default prevents trailing word clipping)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"File not found: {input_path}")

    output_path = args.output or str(input_path.parent / f"{input_path.stem}_cut.mp4")

    cut_silence(
        input_path=str(input_path),
        output_path=output_path,
        threshold=args.threshold,
        min_silence=args.min_silence,
        padding=args.padding,
    )


if __name__ == "__main__":
    main()

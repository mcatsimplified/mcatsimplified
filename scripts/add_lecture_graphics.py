#!/usr/bin/env python3
"""
add_lecture_graphics.py
Adds a lower-third intro and an equation highlight overlay to finale.mp4,
then exports final_lecture_edit.mp4 with the original audio intact.

Usage:
    py add_lecture_graphics.py
"""

import os
import subprocess
import sys

# ─────────────────────────────────────────────────────────────────────────────
# 1. Dependency check — installs moviepy / Pillow if missing
# ─────────────────────────────────────────────────────────────────────────────
DEPS = {"moviepy": "moviepy", "PIL": "Pillow"}
print("Checking dependencies...")
for import_name, pip_name in DEPS.items():
    try:
        __import__(import_name)
        print(f"  ✓ {pip_name}")
    except ImportError:
        print(f"  Installing {pip_name}...")
        subprocess.run([sys.executable, "-m", "pip", "install", pip_name], check=True)
        print(f"  ✓ {pip_name} installed")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Imports
# ─────────────────────────────────────────────────────────────────────────────
from moviepy import CompositeVideoClip, ImageClip, VideoClip, VideoFileClip, vfx
from PIL import Image, ImageDraw, ImageFont
import numpy as np

INPUT  = "finale.mp4"
OUTPUT = "final_lecture_edit.mp4"

if not os.path.exists(INPUT):
    sys.exit(f"\nERROR: '{INPUT}' not found in {os.getcwd()}\n"
             f"Place finale.mp4 in the same folder as this script.")

print(f"\nLoading {INPUT}...")
video = VideoFileClip(INPUT)
W, H  = video.size
FPS   = video.fps
DUR   = video.duration
print(f"  Resolution : {W}x{H}")
print(f"  FPS        : {FPS}")
print(f"  Duration   : {DUR:.2f}s")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Font helper — tries Arial/system fonts, falls back to PIL default
# ─────────────────────────────────────────────────────────────────────────────
def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    if bold:
        candidates = [
            "arialbd.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
        ]
    else:
        candidates = [
            "arial.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
        ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    try:
        return ImageFont.load_default(size=size)  # Pillow ≥ 10.1
    except TypeError:
        return ImageFont.load_default()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Lower-third overlay (0s → 5s)
#    Dark-gray rounded container • "Enzyme Kinetics" bold white
#    • "Biology Lecture Series" light-blue accent
#    Fades in over 0.5s, fades out at 5s
# ─────────────────────────────────────────────────────────────────────────────
LT_END   = 5.0
LT_FADE  = 0.5
LT_PAD   = int(W * 0.025)             # outer margin ~48 px on 1920
BOX_W    = int(W * 0.295)             # ~566 px on 1920
BOX_H    = int(H * 0.135)             # ~146 px on 1080
BOX_X1   = LT_PAD
BOX_Y1   = H - BOX_H - LT_PAD
BOX_X2   = BOX_X1 + BOX_W
BOX_Y2   = BOX_Y1 + BOX_H

def make_lower_third_rgba() -> np.ndarray:
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d      = ImageDraw.Draw(canvas)

    # Background container
    d.rounded_rectangle(
        [BOX_X1, BOX_Y1, BOX_X2, BOX_Y2],
        radius=int(H * 0.012),
        fill=(12, 12, 12, 200),             # dark gray, ~78 % opacity
    )

    # Left accent bar
    bar_x = BOX_X1 + int(BOX_W * 0.035)
    bar_w = max(5, int(BOX_W * 0.012))
    d.rounded_rectangle(
        [bar_x, BOX_Y1 + int(BOX_H * 0.14),
         bar_x + bar_w, BOX_Y2 - int(BOX_H * 0.14)],
        radius=3,
        fill=(80, 170, 255, 240),            # light blue
    )

    text_x     = bar_x + bar_w + int(BOX_W * 0.04)
    title_size = max(26, int(H * 0.036))
    sub_size   = max(18, int(H * 0.024))

    # Title
    d.text(
        (text_x, BOX_Y1 + int(BOX_H * 0.12)),
        "Enzyme Kinetics",
        font=load_font(title_size, bold=True),
        fill=(255, 255, 255, 255),
    )

    # Subtitle
    d.text(
        (text_x, BOX_Y1 + int(BOX_H * 0.57)),
        "Biology Lecture Series",
        font=load_font(sub_size, bold=False),
        fill=(110, 185, 255, 220),           # light blue accent
    )

    return np.array(canvas)


def _make_lt_clip() -> ImageClip:
    rgba   = make_lower_third_rgba()
    rgb    = rgba[:, :, :3]
    alpha  = (rgba[:, :, 3] / 255.0)

    clip   = ImageClip(rgb).with_duration(LT_END)
    mask   = ImageClip(alpha, ismask=True).with_duration(LT_END)
    return (
        clip
        .with_mask(mask)
        .with_start(0)
        .with_effects([vfx.FadeIn(LT_FADE), vfx.FadeOut(LT_FADE)])
    )

lower_third = _make_lt_clip()
print("  ✓ Lower-third overlay ready")


# ─────────────────────────────────────────────────────────────────────────────
# 5. Equation highlight box (starts at 19s, stays to end)
#    Red outline that "draws in" from its centre over 0.35 s.
#    ┌──────────────────────────────────────────────────────────────────────┐
#    │ TUNE THESE if the box doesn't frame the equation precisely           │
#    │ Values are fractions of the video W/H (0.0 – 1.0)                   │
#    └──────────────────────────────────────────────────────────────────────┘
EQ_LEFT   = 0.10    # left edge
EQ_TOP    = 0.28    # top edge
EQ_RIGHT  = 0.90    # right edge
EQ_BOTTOM = 0.62    # bottom edge
# ─────────────────────────────────────────────────────────────────────────────

EQ_START   = 19.0
DRAW_DUR   = 0.35
LINE_W     = max(3, int(H * 0.004))
BOX_COLOR  = (220, 45, 45)            # red  — swap to (30, 140, 255) for blue

bx1 = int(W * EQ_LEFT)
by1 = int(H * EQ_TOP)
bx2 = int(W * EQ_RIGHT)
by2 = int(H * EQ_BOTTOM)
bcx = (bx1 + bx2) / 2
bcy = (by1 + by2) / 2
bhw = (bx2 - bx1) / 2
bhh = (by2 - by1) / 2

_static_frame_cache: dict = {}

def _render_highlight(progress: float) -> np.ndarray:
    """Return RGBA numpy array for a given animation progress (0 → 1)."""
    eased = progress ** 0.45             # ease-out: snappy expansion
    hw    = bhw * eased
    hh    = bhh * eased

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if hw < 4 or hh < 4:
        return np.array(img)

    d   = ImageDraw.Draw(img)
    r, g, b = BOX_COLOR
    tick    = min(hw, hh) * 0.15        # corner tick length

    # Main outline
    d.rectangle(
        [bcx - hw, bcy - hh, bcx + hw, bcy + hh],
        outline=(r, g, b, 255),
        width=LINE_W,
    )

    # Bold corner ticks for a modern "targeting" look
    for sx, sy, dx, dy in [
        (bcx - hw, bcy - hh,  1,  1),
        (bcx + hw, bcy - hh, -1,  1),
        (bcx - hw, bcy + hh,  1, -1),
        (bcx + hw, bcy + hh, -1, -1),
    ]:
        d.line([(sx, sy), (sx + dx * tick, sy)], fill=(r, g, b, 255), width=LINE_W + 2)
        d.line([(sx, sy), (sx, sy + dy * tick)], fill=(r, g, b, 255), width=LINE_W + 2)

    return np.array(img)


def _get_frame(t: float) -> np.ndarray:
    if t >= DRAW_DUR:
        if "static" not in _static_frame_cache:
            _static_frame_cache["static"] = _render_highlight(1.0)
        return _static_frame_cache["static"]

    key = round(t * FPS)
    if key not in _static_frame_cache:
        _static_frame_cache[key] = _render_highlight(min(1.0, t / DRAW_DUR))
    return _static_frame_cache[key]


eq_duration = max(0.5, DUR - EQ_START)

def eq_make_rgb(t: float)  -> np.ndarray: return _get_frame(t)[:, :, :3]
def eq_make_mask(t: float) -> np.ndarray: return _get_frame(t)[:, :, 3] / 255.0

eq_rgb  = VideoClip(eq_make_rgb,  duration=eq_duration)
eq_mask = VideoClip(eq_make_mask, ismask=True, duration=eq_duration)
highlight = eq_rgb.with_mask(eq_mask).with_start(EQ_START)

print("  ✓ Equation highlight overlay ready")


# ─────────────────────────────────────────────────────────────────────────────
# 6. Composite + export
#    CompositeVideoClip layers: base video → lower-third → highlight
#    Audio is explicitly re-attached from the original clip so nothing is lost.
# ─────────────────────────────────────────────────────────────────────────────
print("\nCompositing all layers...")
final = CompositeVideoClip([video, lower_third, highlight])
final = final.with_audio(video.audio)

print(f"Exporting → {OUTPUT}")
print("(Rendering may take a few minutes — progress shown below)\n")
final.write_videofile(
    OUTPUT,
    fps=FPS,
    codec="libx264",
    audio_codec="aac",
    logger="bar",
)

video.close()
final.close()
print(f"\n✓ Done.  Final video saved to: {os.path.abspath(OUTPUT)}")

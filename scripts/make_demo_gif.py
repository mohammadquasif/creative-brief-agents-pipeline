"""Generate assets/demo.gif — an animated terminal demo of the pipeline.

Renders a fake terminal window frame-by-frame (typing the request, then the
validated JSON response) and writes an animated GIF for the README.

Usage:
    python scripts/make_demo_gif.py
Output:
    assets/demo.gif

Requires Pillow:  pip install Pillow   (already present in dev requirements)
"""
from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "demo.gif"

# --- window geometry ------------------------------------------------------ #
W, H = 1020, 620
PAD_X, PAD_Y = 40, 64
LINE_H = 25
FONT_SIZE = 16
TITLE_FONT_SIZE = 14

BG = (13, 16, 32)          # outer page background
TERM_BG = (10, 13, 31)     # terminal background
TITLE_BAR = (23, 29, 56)
BORDER = (43, 51, 92)
TEXT = (223, 235, 255)     # near-white
DIM = (152, 162, 198)      # muted grey-blue
GREEN = (52, 211, 153)
CYAN = (122, 162, 255)
YELLOW = (251, 191, 36)
RED_DOT, YELLOW_DOT, GREEN_DOT = (255, 95, 86), (255, 189, 46), (39, 201, 63)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/DejaVuSansMono.ttf",
        "C:/Windows/Fonts/consola.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT = _font(FONT_SIZE)
FONT_B = _font(FONT_SIZE, bold=True)
FONT_T = _font(TITLE_FONT_SIZE, bold=True)

# --- demo "script" --------------------------------------------------------- #
# Each entry: (kind, text)  kind: p=prompt, o=stdout, i=input(json key), v=value
TERM_TITLE = "creative-brief-agent-pipeline — python run.py (127.0.0.1:8001)"

SCRIPT: list[tuple[str, str]] = [
    ("p", "PS C:\\repo> python run.py"),
    ("o", "INFO:     Uvicorn running on http://127.0.0.1:8001"),
    ("o", "INFO:     Application startup complete."),
    ("o", ""),
    ("p", "PS C:\\repo> $body = @{ raw_brief = 'Need something for the new sneaker drop "
          "targeting gen z, kinda hype energy, has to be ready by friday.' } | ConvertTo-Json"),
    ("o", "PS C:\\repo> Invoke-RestMethod -Uri 'http://127.0.0.1:8001/api/v1/generate' `"),
    ("o", ">>   -Method Post -Body $body -ContentType 'application/json'"),
    ("o", ""),
    ("i", "validated_brief"),
    ("v", "  campaign_name    : Sneaker Drop Campaign"),
    ("v", "  target_audience  : Gen Z"),
    ("v", "  key_message      : The sneaker drop is live — limited pairs, no restocks."),
    ("v", "  tone             : hype"),
    ("v", "  deadline         : 2026-09-11        # 'friday' auto-resolved"),
    ("i", "creative"),
    ("v", "  ad_concept   : The sneaker drop is live — limited pairs, no restocks. —"),
    ("v", "                 Gen Z can't miss this one."),
    ("v", "  social_caption: The sneaker drop is live — limited pairs, no restocks."),
    ("v", "                 Don't sleep — cop yours before they're gone."),
    ("v", "  hashtags     : #SneakerDropCampaign, #GenZ, #Hype, #NewDrop, #CopOrMiss"),
    ("i", "meta"),
    ("v", "  provider: local · validation_attempts: 1 · repair_passes: 0 · fallbacks: []"),
    ("o", ""),
    ("done", "  ✅ Draft ready — validated brief → on-brand creative output"),
]


def frame(lines: list[tuple[str, str]]) -> Image.Image:
    """Render one frame from the lines visible so far."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # terminal window
    d.rounded_rectangle([PAD_X - 8, PAD_Y - 46, W - PAD_X + 8, H - PAD_Y + 26],
                        radius=12, fill=TERM_BG, outline=BORDER)
    d.rounded_rectangle([PAD_X - 8, PAD_Y - 46, W - PAD_X + 8, PAD_Y - 46 + 34],
                        radius=10, fill=TITLE_BAR)
    d.ellipse([PAD_X + 4, PAD_Y - 38, PAD_X + 16, PAD_Y - 26], fill=RED_DOT)
    d.ellipse([PAD_X + 22, PAD_Y - 38, PAD_X + 34, PAD_Y - 26], fill=YELLOW_DOT)
    d.ellipse([PAD_X + 40, PAD_Y - 38, PAD_X + 52, PAD_Y - 26], fill=GREEN_DOT)
    t_w = d.textlength(TERM_TITLE, font=FONT_T)
    d.text(((W - t_w) / 2, PAD_Y - 40), TERM_TITLE, font=FONT_T, fill=DIM)

    y = PAD_Y
    for kind, text in lines:
        if not text:
            y += LINE_H
            continue
        color = TEXT
        font = FONT
        if kind == "p":
            color, font = GREEN, FONT_B
        elif kind == "o":
            color = DIM
        elif kind == "i":
            color = CYAN
        elif kind == "v":
            color = TEXT
        elif kind == "done":
            color, font = YELLOW, FONT_B
        for sub in text.split("\n"):
            d.text((PAD_X, y), sub, font=font, fill=color)
            y += LINE_H
    return img


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # progressive reveal: show one more script line per frame; dwell on final
    frames: list[Image.Image] = []
    visible: list[tuple[str, str]] = []
    for entry in SCRIPT:
        visible.append(entry)
        frames.append(frame(list(visible)))

    # linger on the last two frames so people can read the output
    frames.append(frame(list(visible)))
    frames.append(frame(list(visible)))

    # GIF: ~50ms per frame with a longer hold for the reveal dwell
    delays = [140] * max(0, len(frames) - 3) + [900, 900, 900]
    frames[0].save(
        OUT, save_all=True, append_images=frames[1:],
        duration=delays, loop=0, disposal=2,
    )
    print(f"wrote {OUT}  ({len(frames)} frames, {OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()

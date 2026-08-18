#!/usr/bin/env python3
"""Compose 1440x900 Olares Market promo images from real screenshots."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
PROMO = ROOT / "promo"
W, H = 1440, 900
ACCENT = (34, 197, 94)
BG_TOP = (248, 250, 252)
BG_BOTTOM = (241, 245, 249)
TEXT = (15, 23, 42)
MUTED = (100, 116, 139)


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def gradient_bg() -> Image.Image:
    img = Image.new("RGB", (W, H), BG_TOP)
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / max(H - 1, 1)
        r = int(BG_TOP[0] * (1 - t) + BG_BOTTOM[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_BOTTOM[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_BOTTOM[2] * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    return img


def fit_screenshot(path: Path, box_w: int, box_h: int) -> Image.Image:
    shot = Image.open(path).convert("RGBA")
    shot.thumbnail((box_w, box_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (box_w, box_h), (255, 255, 255, 0))
    x = (box_w - shot.width) // 2
    y = (box_h - shot.height) // 2
    canvas.paste(shot, (x, y), shot if shot.mode == "RGBA" else None)
    return canvas


def draw_headline(draw: ImageDraw.ImageDraw, title: str, subtitle: str) -> None:
    title_font = load_font(64, bold=True)
    sub_font = load_font(30)
    title_y = 72
    words = title.split(" ")
    if len(words) >= 3:
        line1 = " ".join(words[:2])
        line2 = " ".join(words[2:])
        draw.text((W // 2, title_y), line1, font=title_font, fill=TEXT, anchor="ma")
        draw.text((W // 2, title_y + 78), line2, font=title_font, fill=ACCENT, anchor="ma")
        sub_y = title_y + 170
    else:
        draw.text((W // 2, title_y), title, font=title_font, fill=TEXT, anchor="ma")
        sub_y = title_y + 92
    draw.text((W // 2, sub_y), subtitle, font=sub_font, fill=MUTED, anchor="ma")


def compose(out_name: str, title: str, subtitle: str, screenshot: Path) -> Path:
    base = gradient_bg().convert("RGBA")
    draw = ImageDraw.Draw(base)
    draw_headline(draw, title, subtitle)

    shot_w, shot_h = 1180, 560
    shot = fit_screenshot(screenshot, shot_w, shot_h)
    radius = 24
    shot = ImageOps.expand(shot, border=8, fill=(255, 255, 255, 255))
    mask = Image.new("L", shot.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, shot.width, shot.height), radius=radius, fill=255)
    shadow = Image.new("RGBA", (shot.width + 40, shot.height + 40), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle((20, 20, shot.width + 20, shot.height + 20), radius=radius, fill=(15, 23, 42, 60))
    x = (W - shot.width) // 2
    y = H - shot.height - 36
    base.alpha_composite(shadow, (x - 20, y - 12))
    base.paste(shot, (x, y), mask)

    out = PROMO / out_name
    base.convert("RGB").save(out, format="PNG", optimize=True)
    return out


def main() -> int:
    jobs = [
        ("1.png", "Open Design on Olares", "Local-first AI design studio with BYOK models", "screenshot_home.png"),
        ("2.png", "Generate slides and decks", "Prompt-driven HTML decks with agent workflows", "screenshot_task.png"),
        ("3.png", "Connect local LLM APIs", "Use Olares-hosted llama.cpp or LiteLLM gateways", "upstream_workflow.webp"),
    ]
    for out_name, title, subtitle, src in jobs:
        src_path = PROMO / src
        if not src_path.exists():
            print(f"missing screenshot: {src_path}", file=sys.stderr)
            return 1
        out = compose(out_name, title, subtitle, src_path)
        im = Image.open(out)
        assert im.size == (W, H), im.size
        print(f"OK {out} {im.size[0]}x{im.size[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

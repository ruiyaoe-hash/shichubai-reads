#!/usr/bin/env python3
"""Compose a 初白de小岛 1280×720 cover from a chosen still.

Order, which must not be skipped:
  chosen frame or owner-provided still
  → pencil sketch (grayscale, invert-blur-divide, contour gradient)
  → composite onto warm paper with a four-edge smoothstep fade
  → typography grid on the left (the paper, not the raw photograph)

This matches the published 001 / 003 covers documented in README and
COMPLIANCE.md §五之二: subject on the right, exact paper on the left,
no hard frame or column rule. Day paper is #F6EFE4, night paper is the
one-step-darker #E6D8C5; the sketch is re-rendered onto each paper color.

Do not output a full-bleed untreated photograph with type on top.

Inputs come from the operator (a highlight frame, or a still for an
original episode with no video). This script never overwrites a published
cover unless the output path is pointed there on purpose.

Dependencies: numpy, pillow, opencv-python-headless, plus ffmpeg-free
local fonts (Noto Serif CJK SC). YuNet is optional and only used to
place a face in the right-hand panel.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


COVER_W, COVER_H = 1280, 720
PAPER_DAY = (0xF6, 0xEF, 0xE4)
PAPER_NIGHT = (0xE6, 0xD8, 0xC5)
INK = (0x3B, 0x32, 0x29)  # matches darkest published pencil strokes and body text

# Typography on paper — copied from the published 001 / 003 SVGs.
PALETTES = {
    "day": {
        "paper": PAPER_DAY,
        "brand": "#8B7E6E",
        "ink": "#3B3229",
        "accent": "#A9684B",
        "meta": "#8B7E6E",
        "line": "#D6C7B4",
        "rule": "#A9684B",
    },
    "night": {
        "paper": PAPER_NIGHT,
        "brand": "#7A6D5C",
        "ink": "#3B3229",
        "accent": "#A9684B",
        "meta": "#7A6D5C",
        "line": "#C9B9A0",
        "rule": "#A9684B",
    },
}

FONT_SC_REG = Path("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc")
FONT_SC_BOLD = Path("/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc")
FONT_EN_I = Path("/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf")
FONT_EN = Path("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf")
DEFAULT_YUNET = Path(__file__).resolve().parent / "models" / "face_detection_yunet_2023mar.onnx"

# Right-hand panel. Fade insets put the source crop edges in the alpha=0
# zone, the same "无硬边界" rule as the published covers. Content becomes
# visible around x≈660, matching 001 / 003.
DEST = (620, 0, 1280, 655)
FADE = (170, 70, 70, 100)  # left, right, top, bottom in px


def load_font(path: Path, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size, index=index)


def smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - edge0) / (edge1 - edge0 + 1e-8), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def detect_face(bgr: np.ndarray, model: Path | None) -> dict | None:
    if model is None or not model.is_file():
        return None
    h, w = bgr.shape[:2]
    det = cv2.FaceDetectorYN_create(str(model), "", (w, h), 0.6, 0.3, 5000)
    _retval, faces = det.detect(bgr)
    if faces is None or len(faces) == 0:
        return None
    faces = sorted(faces, key=lambda r: float(r[2] * r[3]), reverse=True)
    x, y, fw, fh = [float(v) for v in faces[0][:4]]
    return {"x": x, "y": y, "w": fw, "h": fh}


def pencil_sketch(bgr: np.ndarray, paper: tuple[int, int, int]) -> np.ndarray:
    """Grayscale → invert-blur-divide (color dodge) → contour gradient.

    Mid-lights are bleached toward paper so room backgrounds fade the way
    they do on 001 / 003. The result is a warm-brown ink on `paper`.
    """
    paper_f = np.array(paper, dtype=np.float32)
    ink_f = np.array(INK, dtype=np.float32)
    den = cv2.bilateralFilter(bgr, d=5, sigmaColor=25, sigmaSpace=5)
    gray = cv2.cvtColor(den, cv2.COLOR_BGR2GRAY).astype(np.float32)
    inv = 255.0 - gray
    sigma = 17.0
    k = int(max(3, round(sigma * 4)) // 2 * 2 + 1)
    blur = cv2.GaussianBlur(inv, (k, k), sigmaX=sigma)
    dodge = np.clip(gray * 255.0 / np.maximum(255.0 - blur, 1.0), 0, 255)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(gx * gx + gy * gy)
    mag = np.clip(mag / (np.percentile(mag, 99.0) + 1e-6), 0, 1)
    sketch = dodge * (1.0 - 0.34 * mag)
    sketch = (sketch - 255.0) * 1.12 + 255.0
    lift_start = 255.0 - 18.0 * 4
    lift = np.clip((sketch - lift_start) / (255.0 - lift_start + 1e-6), 0, 1)
    sketch = np.clip(sketch + lift * (255.0 - sketch) * 0.65, 0, 255)
    ink_amt = np.power(np.clip(1.0 - sketch / 255.0, 0, 1), 0.92)
    rgb = paper_f * (1.0 - ink_amt)[..., None] + ink_f * ink_amt[..., None]
    return np.clip(rgb, 0, 255).astype(np.uint8)


def place_on_paper(
    sketch_rgb: np.ndarray,
    paper: tuple[int, int, int],
    face: dict | None,
) -> np.ndarray:
    """Sit the sketch in the right-hand panel and fade all four edges."""
    paper_f = np.array(paper, dtype=np.float32)
    dx0, dy0, dx1, dy1 = DEST
    dw, dh = dx1 - dx0, dy1 - dy0
    h, w = sketch_rgb.shape[:2]
    aspect = dw / dh
    if face is not None:
        cx = face["x"] + face["w"] / 2.0
        cy = face["y"] + face["h"] / 2.0
        crop_h = max(face["h"] * 3.5, h * 0.82)
        x_bias, y_bias = 0.52, 0.36
    else:
        # No face: favour the right side of a wide frame.
        crop_h = float(h)
        cx, cy = w * 0.64, h / 2.0
        x_bias, y_bias = 0.5, 0.5
    # Keep the destination aspect ratio. Shrink the crop (both sides
    # together) until it fits inside the source; never clip one side only,
    # which would make the final resize stretch the figure.
    crop_h = min(crop_h, float(h), w / aspect)
    crop_w = crop_h * aspect
    x0 = int(round(np.clip(cx - crop_w * x_bias, 0, w - crop_w)))
    y0 = int(round(np.clip(cy - crop_h * y_bias, 0, h - crop_h)))
    crop = sketch_rgb[y0:y0 + int(round(crop_h)), x0:x0 + int(round(crop_w))]
    got = crop.shape[1] / crop.shape[0]
    assert abs(got - aspect) / aspect < 0.01, f"crop aspect {got:.4f} != panel {aspect:.4f}"
    crop = cv2.resize(crop, (dw, dh), interpolation=cv2.INTER_LANCZOS4)
    fl, fr, ft, fb = FADE
    yy, xx = np.mgrid[0:dh, 0:dw]
    mx = smoothstep(0, fl, xx) * (1.0 - smoothstep(dw - fr, dw, xx))
    my = smoothstep(0, ft, yy) * (1.0 - smoothstep(dh - fb, dh, yy))
    alpha = np.clip(mx * my, 0.0, 1.0)[..., None]
    canvas = np.full((COVER_H, COVER_W, 3), paper_f, dtype=np.float32)
    canvas[dy0:dy1, dx0:dx1] = crop.astype(np.float32) * alpha + paper_f * (1.0 - alpha)
    # Typography lives on exact paper, as on 001 / 003 (left of x=640 is pure fill).
    canvas[:, :640] = paper_f
    return np.clip(canvas, 0, 255).astype(np.uint8)


def encode_webp(im: Image.Image, quality: int = 82) -> bytes:
    buf = io.BytesIO()
    im.save(buf, format="WEBP", quality=quality, method=6)
    return buf.getvalue()


def title_ys(n: int) -> list[int]:
    if n <= 0:
        return []
    if n == 1:
        return [332]
    if n == 2:
        return [291, 373]
    return [250, 332, 414][:n]


def svg_for(
    *,
    webp: bytes,
    palette_name: str,
    kicker: str,
    title_lines: list[str],
    en_title: str,
    figure: str,
    number: str,
    date: str,
    brand: str,
    footer: str,
    desc: str,
) -> str:
    pal = PALETTES[palette_name]
    paper = pal["paper"]
    fill = f"#{paper[0]:02X}{paper[1]:02X}{paper[2]:02X}"
    b64 = base64.b64encode(webp).decode("ascii")

    def t(x, y, size, text, color, *, anchor=None, family="cjk", weight=None, italic=False, tracking=None):
        fam = {
            "cjk": "'Noto Serif CJK SC','Source Han Serif SC','Songti SC','SimSun',serif",
            "en": "Georgia,'Times New Roman',serif",
        }[family]
        attrs = [
            f'x="{x}"', f'y="{y}"',
            f"font-family=\"{fam}\"",
            f'font-size="{size}"',
            f'fill="{color}"',
        ]
        if anchor:
            attrs.append(f'text-anchor="{anchor}"')
        if weight:
            attrs.append(f'font-weight="{weight}"')
        if italic:
            attrs.append('font-style="italic"')
        if tracking is not None:
            attrs.append(f'letter-spacing="{tracking}"')
        esc = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f"  <text {' '.join(attrs)}>{esc}</text>"

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 1280 720" role="img">',
        f"  <desc>{desc.replace('&','&amp;').replace('<','&lt;')}</desc>",
        "  <defs>",
        '    <linearGradient id="lf" gradientUnits="userSpaceOnUse" x1="88" y1="0" x2="1192" y2="0">',
        f'      <stop offset="0" stop-color="{pal["line"]}" stop-opacity=".72"/>',
        f'      <stop offset="0.32" stop-color="{pal["line"]}" stop-opacity=".72"/>',
        f'      <stop offset="0.52" stop-color="{pal["line"]}" stop-opacity="0"/>',
        "    </linearGradient>",
        "  </defs>",
        f'  <rect width="1280" height="720" fill="{fill}"/>',
        f'  <image x="0" y="0" width="1280" height="720" preserveAspectRatio="xMidYMid meet" xlink:href="data:image/webp;base64,{b64}"/>',
        '  <line x1="88" y1="88" x2="1192" y2="88" stroke="url(#lf)" stroke-width="1"/>',
        '  <line x1="88" y1="628" x2="1192" y2="628" stroke="url(#lf)" stroke-width="1"/>',
        t(88, 72, 21, brand, pal["brand"], tracking=3),
        t(1192, 72, 19, f"NO. {number}", pal["meta"], anchor="end", family="en", tracking=5),
        f'  <line x1="1168" y1="100" x2="1192" y2="100" stroke="{pal["rule"]}" stroke-width="2"/>',
        f'  <rect x="88" y="158" width="14" height="14" fill="{pal["accent"]}"/>',
        t(116, 177, 22, kicker, pal["accent"], tracking=7),
    ]
    for y, line in zip(title_ys(len(title_lines)), title_lines):
        lines.append(t(88, y, 56, line, pal["ink"], weight=600))
    lines += [
        t(88, 492, 19, en_title, pal["meta"], family="en", italic=True, tracking=0.6),
        f'  <line x1="88" y1="530" x2="168" y2="530" stroke="{pal["rule"]}" stroke-width="2"/>',
        t(88, 575, 23, figure, pal["ink"]),
        t(88, 668, 18, footer, pal["meta"], tracking=2.5),
        t(1192, 668, 18, date, pal["meta"], anchor="end", family="en", tracking=2),
        "</svg>",
        "",
    ]
    return "\n".join(lines)


def rasterize_preview(
    im: Image.Image,
    *,
    palette_name: str,
    kicker: str,
    title_lines: list[str],
    en_title: str,
    figure: str,
    number: str,
    date: str,
    brand: str,
    footer: str,
) -> Image.Image:
    pal = PALETTES[palette_name]
    canvas = im.convert("RGB").resize((COVER_W, COVER_H), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(canvas)

    def col(hex_color: str):
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    sc_r = load_font(FONT_SC_REG, 21)
    sc_k = load_font(FONT_SC_REG, 22)
    sc_t = load_font(FONT_SC_BOLD, 56)
    sc_f = load_font(FONT_SC_REG, 23)
    sc_ft = load_font(FONT_SC_REG, 18)
    en_n = load_font(FONT_EN, 19)
    en_i = load_font(FONT_EN_I, 19)
    en_d = load_font(FONT_EN, 18)
    line = col(pal["line"]) + (int(255 * 0.72),)

    # The published covers fade the grid lines in SVG; the PNG preview
    # approximates that with a solid line that stops near x=662.
    draw.line((88, 88, 662, 88), fill=line[:3], width=1)
    draw.line((88, 628, 662, 628), fill=line[:3], width=1)
    draw.text((88, 72), brand, font=sc_r, fill=col(pal["brand"]), anchor="ls")
    draw.text((1192, 72), f"NO. {number}", font=en_n, fill=col(pal["meta"]), anchor="rs")
    draw.line((1168, 100, 1192, 100), fill=col(pal["rule"]), width=2)
    draw.rectangle((88, 158, 102, 172), fill=col(pal["accent"]))
    draw.text((116, 177), kicker, font=sc_k, fill=col(pal["accent"]), anchor="ls")
    for y, line_text in zip(title_ys(len(title_lines)), title_lines):
        draw.text((88, y), line_text, font=sc_t, fill=col(pal["ink"]), anchor="ls")
    draw.text((88, 492), en_title, font=en_i, fill=col(pal["meta"]), anchor="ls")
    draw.line((88, 530, 168, 530), fill=col(pal["rule"]), width=2)
    draw.text((88, 575), figure, font=sc_f, fill=col(pal["ink"]), anchor="ls")
    draw.text((88, 668), footer, font=sc_ft, fill=col(pal["meta"]), anchor="ls")
    draw.text((1192, 668), date, font=en_d, fill=col(pal["meta"]), anchor="rs")
    return canvas


def render_base(frame: Path, paper: tuple[int, int, int], yunet: Path | None) -> Image.Image:
    bgr = cv2.imread(str(frame))
    if bgr is None:
        # Pillow fallback for stills cv2 cannot decode
        rgb = np.asarray(Image.open(frame).convert("RGB"))
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    face = detect_face(bgr, yunet)
    sketched = pencil_sketch(bgr, paper)
    placed = place_on_paper(sketched, paper, face)
    return Image.fromarray(placed, "RGB")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("frame", type=Path, help="Chosen still (highlight frame or owner-provided image).")
    ap.add_argument("--out-prefix", type=Path, required=True, help="Writes PREFIX.svg, PREFIX-dark.svg, and PNG previews.")
    ap.add_argument("--title", required=True, help="Cover title. Use / or ／ to split short couplet lines.")
    ap.add_argument("--en-title", required=True)
    ap.add_argument("--figure", required=True)
    ap.add_argument(
        "--number", required=True,
        help="Digits only, shown as NO. {number}. Example: 5 or 005.",
    )
    ap.add_argument("--date", required=True, help="Cover date, e.g. 2026.11")
    ap.add_argument("--kicker", default="中文精读")
    ap.add_argument("--brand", default="初白de小岛")
    ap.add_argument("--footer", default="")
    ap.add_argument("--desc", default="")
    ap.add_argument("--yunet", type=Path, default=DEFAULT_YUNET)
    args = ap.parse_args(argv)

    if not args.number.isascii() or not args.number.isdigit():
        raise SystemExit("--number takes digits only, for example 5 or 005")

    frame = args.frame.expanduser().resolve()
    if not frame.is_file():
        raise SystemExit(f"frame not found: {frame}")

    title_lines = [p.strip() for p in args.title.replace("／", "/").split("/") if p.strip()]
    if not title_lines:
        raise SystemExit("title produced no lines")
    footer = args.footer or f"{args.brand} · {args.kicker}"
    yunet = args.yunet if args.yunet.is_file() else None

    day = render_base(frame, PAPER_DAY, yunet)
    night = render_base(frame, PAPER_NIGHT, yunet)

    desc = args.desc or (
        f"第 {args.number} 期封面：选定静帧先经铅笔素描化（灰度、反相模糊除法、"
        "轮廓梯度增强），再铺满幅暖纸、四边 smoothstep 柔和渐隐，左侧为标题网格，"
        "右侧为主人物图，右上角保留 NO. 编号。"
        f"ViewBox {COVER_W}x{COVER_H}。"
    )

    prefix = args.out_prefix.expanduser().resolve()
    prefix.parent.mkdir(parents=True, exist_ok=True)

    day_svg = svg_for(
        webp=encode_webp(day), palette_name="day", kicker=args.kicker,
        title_lines=title_lines, en_title=args.en_title, figure=args.figure,
        number=args.number, date=args.date, brand=args.brand, footer=footer,
        desc=desc + "日读版。",
    )
    night_svg = svg_for(
        webp=encode_webp(night), palette_name="night", kicker=args.kicker,
        title_lines=title_lines, en_title=args.en_title, figure=args.figure,
        number=args.number, date=args.date, brand=args.brand, footer=footer,
        desc=desc + "夜读（同帧素描铺在压暗一档暖纸上）版。",
    )
    (prefix.with_suffix(".svg")).write_text(day_svg, encoding="utf-8")
    dark_path = prefix.with_name(prefix.name + "-dark.svg")
    dark_path.write_text(night_svg, encoding="utf-8")

    day_png = rasterize_preview(
        day, palette_name="day", kicker=args.kicker, title_lines=title_lines,
        en_title=args.en_title, figure=args.figure, number=args.number,
        date=args.date, brand=args.brand, footer=footer,
    )
    night_png = rasterize_preview(
        night, palette_name="night", kicker=args.kicker, title_lines=title_lines,
        en_title=args.en_title, figure=args.figure, number=args.number,
        date=args.date, brand=args.brand, footer=footer,
    )
    day_png.save(prefix.with_suffix(".png"))
    night_png.save(prefix.with_name(prefix.name + "-dark.png"))
    day.save(prefix.with_name(prefix.name + "-base.webp"), quality=86, method=6)
    night.save(prefix.with_name(prefix.name + "-dark-base.webp"), quality=86, method=6)

    def paper_stats(im: Image.Image, paper: tuple[int, int, int]) -> dict:
        arr = np.asarray(im)
        left = arr[:, :500]
        exact = float(np.all(left == np.array(paper, dtype=np.uint8), axis=2).mean())
        return {"left500_exact_paper": round(exact, 4), "left500_mean": left.mean(axis=(0, 1)).round(2).tolist()}

    meta = {
        "frame": str(frame),
        "process": "pencil-sketch + warm-paper",
        "paper_day": list(PAPER_DAY),
        "paper_night": list(PAPER_NIGHT),
        "title_lines": title_lines,
        "day_paper_check": paper_stats(day, PAPER_DAY),
        "night_paper_check": paper_stats(night, PAPER_NIGHT),
        "outputs": {
            "svg": str(prefix.with_suffix(".svg")),
            "svg_dark": str(dark_path),
            "png": str(prefix.with_suffix(".png")),
            "png_dark": str(prefix.with_name(prefix.name + "-dark.png")),
        },
    }
    prefix.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    if meta["day_paper_check"]["left500_exact_paper"] < 0.99:
        raise SystemExit("day cover left band is not exact warm paper")
    if meta["night_paper_check"]["left500_exact_paper"] < 0.99:
        raise SystemExit("night cover left band is not exact warm paper")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Extract and rank highlight / hero frames from a video for 初白de小岛 covers.

This tool is a paved path for *future* episode covers. It does not rewrite
covers already published on the site.

Pipeline:
  1. Probe duration; skip a short head and tail (titles / end cards).
  2. Sample uniformly (default: one frame every 6 seconds) at a scoring size.
  3. Optionally merge ffmpeg scene-cut timestamps (select=gt(scene,...)).
  4. Hard-filter blur, extreme exposure, letterboxing, burned-in captions,
     and (by default) frames with no detectable face.
  5. Score sharpness, exposure, face size / right-side placement, and how
     much quiet room the left typography band has.
  6. Greedy-pick a diverse top-K, then re-extract those frames at full
     resolution (1280x720 by default).

Dependencies: ffmpeg, ffprobe, numpy, opencv-python-headless, pillow.
Face detector: OpenCV YuNet ONNX (tools/models/face_detection_yunet_2023mar.onnx).
Aesthetic models (CLIP / LAION / NIMA) are intentionally *not* a hard
dependency; they are optional later and human review of top-K remains the gate.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
DEFAULT_YUNET = HERE / "models" / "face_detection_yunet_2023mar.onnx"
COVER_W, COVER_H = 1280, 720
# Left typography band used by the existing 1280x720 cover grid (text starts at x=88).
TEXT_BAND = (0.00, 0.00, 0.52, 1.00)
TARGET_FACE_CX = 0.70  # prefer subject on the right so the title can sit on the left


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def probe_duration(video: Path) -> float:
    out = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nokey=1:noprint_wrappers=1", str(video),
    ])
    return float(out.stdout.strip())


def detect_scene_cuts(video: Path, threshold: float = 0.35) -> list[float]:
    """Return cut timestamps using ffmpeg's select scene metric (0–1 scale)."""
    # Decode at a reduced size; still a full pass, but cheaper than full-res.
    vf = f"scale=320:-2,select='gt(scene,{threshold})',showinfo"
    proc = run([
        "ffmpeg", "-hide_banner", "-i", str(video),
        "-vf", vf, "-f", "null", "-",
    ], check=False)
    times: list[float] = []
    blob = (proc.stderr or "") + (proc.stdout or "")
    for line in blob.splitlines():
        if "pts_time:" not in line:
            continue
        # showinfo: pts_time:12.345678
        try:
            part = line.split("pts_time:")[1].split()[0].rstrip(",")
            times.append(float(part))
        except (IndexError, ValueError):
            continue
    # Dedup cuts that land within 0.4s of each other.
    times = sorted(times)
    kept: list[float] = []
    for t in times:
        if not kept or t - kept[-1] >= 0.4:
            kept.append(t)
    return kept


def extract_lowres_uniform(
    video: Path, out_dir: Path, *, start: float, end: float, every: float, width: int
) -> list[tuple[float, Path]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    # fps=1/every starts at the trimmed origin, i.e. clock time = start + i*every.
    pattern = str(out_dir / "u_%05d.jpg")
    run([
        "ffmpeg", "-hide_banner", "-y",
        "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(video),
        "-vf", f"fps=1/{every:g},scale={width}:-2",
        "-q:v", "4", pattern,
    ])
    frames = sorted(out_dir.glob("u_*.jpg"))
    items: list[tuple[float, Path]] = []
    for i, path in enumerate(frames):
        items.append((start + i * every, path))
    return items


def extract_fullres(video: Path, t: float, dest: Path, *, width: int, height: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Input seek is keyframe-approximate but fast; highlight stills can
    # tolerate ~0.1–0.5s. (Output seek on a long interview is many minutes per frame.)
    run([
        "ffmpeg", "-hide_banner", "-y",
        "-ss", f"{t:.3f}", "-i", str(video),
        "-frames:v", "1",
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
        "-q:v", "2", str(dest),
    ])


class FaceFinder:
    def __init__(self, model: Path, score_threshold: float = 0.65):
        if not model.is_file():
            raise SystemExit(
                f"YuNet model missing: {model}\n"
                "Download face_detection_yunet_2023mar.onnx from "
                "https://github.com/opencv/opencv_zoo (models/face_detection_yunet/)."
            )
        self.model = str(model)
        self.score_threshold = score_threshold
        self._det = None
        self._size = None

    def _detector(self, w: int, h: int):
        if self._det is None or self._size != (w, h):
            self._det = cv2.FaceDetectorYN_create(
                self.model, "", (w, h), self.score_threshold, 0.3, 5000
            )
            self._size = (w, h)
        return self._det

    def detect(self, bgr: np.ndarray) -> list[dict]:
        h, w = bgr.shape[:2]
        _retval, faces = self._detector(w, h).detect(bgr)
        if faces is None or len(faces) == 0:
            return []
        out = []
        for row in faces:
            x, y, fw, fh = [float(v) for v in row[:4]]
            score = float(row[-1])
            # Landmarks: right eye, left eye, nose, right mouth, left mouth.
            lmk = [(float(row[4 + 2 * i]), float(row[5 + 2 * i])) for i in range(5)]
            out.append({
                "x": x, "y": y, "w": fw, "h": fh, "score": score,
                "cx": (x + fw / 2) / w, "cy": (y + fh / 2) / h,
                "area": (fw * fh) / (w * h),
                "landmarks": lmk,
            })
        out.sort(key=lambda f: f["area"] * f["score"], reverse=True)
        return out


def laplacian_var(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def letterbox_ratio(gray: np.ndarray, luma_cut: float = 16.0) -> float:
    """Share of rows at the top/bottom that look like solid bars."""
    h, w = gray.shape
    band = max(4, h // 20)
    top = gray[:band].mean(axis=1)
    bot = gray[-band:].mean(axis=1)
    bar = int((top < luma_cut).sum() + (bot < luma_cut).sum())
    return bar / (2 * band)


def clip_share(gray: np.ndarray) -> float:
    return float(((gray < 8) | (gray > 247)).mean())


def band_stats(gray: np.ndarray, box: tuple[float, float, float, float]) -> dict:
    h, w = gray.shape
    x0, y0, x1, y1 = box
    xa, xb = int(w * x0), int(w * x1)
    ya, yb = int(h * y0), int(h * y1)
    roi = gray[ya:yb, xa:xb]
    if roi.size == 0:
        return {"mean": 0.0, "std": 0.0, "edge": 0.0}
    edges = cv2.Laplacian(roi, cv2.CV_64F)
    return {
        "mean": float(roi.mean()),
        "std": float(roi.std()),
        "edge": float(np.abs(edges).mean()),
    }



def caption_overlay_score(bgr: np.ndarray) -> float:
    """Heuristic for burned-in English caption chips (yellow + white glyphs).

    Looks only at the lower band, where this family of hardsubbed encodes
    (and most YouTube/podcast hardsubs) place captions. Background art in
    the upper half is ignored. Returns a 0–1 text-like area ratio.
    """
    h, w = bgr.shape[:2]
    roi = bgr[int(h * 0.70): int(h * 0.92), int(w * 0.18): int(w * 0.82)]
    if roi.size == 0:
        return 0.0
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    yellow = cv2.inRange(hsv, (18, 90, 160), (40, 255, 255))
    white = cv2.inRange(hsv, (0, 0, 210), (180, 50, 255))

    def textish(mask: np.ndarray) -> float:
        num, _labels, cc, _cent = cv2.connectedComponentsWithStats(
            (mask > 0).astype("uint8"), 8
        )
        area = 0
        H, W = mask.shape
        for i in range(1, num):
            _x, _y, _bw, bh, a = cc[i]
            if a < 40:
                continue
            if bh > 0.35 * H:
                continue
            if bh < 8 or bh > 80:
                if a < 200:
                    continue
            area += int(a)
        return area / (H * W)

    return float(textish(yellow) + textish(white))


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _score_ok(bgr: np.ndarray, faces: list[dict], *, require_face: bool) -> tuple[dict, list[str]]:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    sharp = laplacian_var(gray)
    mean = float(gray.mean())
    std = float(gray.std())
    bars = letterbox_ratio(gray)
    clip = clip_share(gray)
    left = band_stats(gray, TEXT_BAND)

    reasons: list[str] = []
    if sharp < 40:
        reasons.append("blur")
    if mean < 28 or mean > 230:
        reasons.append("exposure")
    if std < 12:
        reasons.append("flat")
    if bars > 0.35:
        reasons.append("letterbox")
    if clip > 0.22:
        reasons.append("clipped")
    cap = caption_overlay_score(bgr)
    if cap >= 0.015:
        reasons.append("caption")
    if require_face and not faces:
        reasons.append("no_face")

    main = faces[0] if faces else None
    # Sharpness: talking-head 720p often lands 80–400. Soft-cap at 250.
    sharp_n = clamp01(sharp / 250.0)
    # Exposure: prefer mid-dark to mid (studio lights, not crushed, not blown).
    exposure_n = clamp01(1.0 - abs(mean - 110.0) / 110.0)
    contrast_n = clamp01(std / 60.0)
    if main:
        # Face should be visible but not a clipped extreme close-up that eats the title.
        size_n = clamp01((main["area"] - 0.02) / 0.18)
        if main["area"] > 0.42:
            size_n *= 0.45
        # Reward faces sitting on the right; lightly penalize faces deep in the title band.
        place_n = clamp01(1.0 - abs(main["cx"] - TARGET_FACE_CX) / 0.45)
        if main["cx"] < 0.40:
            place_n *= 0.55
        face_n = 0.55 * size_n + 0.45 * place_n
        face_n *= clamp01(main["score"])
    else:
        face_n = 0.0
    # Quiet left band (low edge density) is ideal. If the left is busy, still
    # accept it when the band is dark enough for light type, or light enough
    # for dark ink — but prefer quiet space.
    quiet_n = clamp01(1.0 - left["edge"] / 18.0)
    # Contrast available for type: distance of mean luma from mid-grey.
    type_n = clamp01(abs(left["mean"] - 128.0) / 80.0)
    text_n = 0.65 * quiet_n + 0.35 * type_n

    overall = (
        0.26 * sharp_n
        + 0.14 * exposure_n
        + 0.08 * contrast_n
        + 0.32 * face_n
        + 0.20 * text_n
    )
    metrics = {
        "sharpness": round(sharp, 2),
        "luma_mean": round(mean, 2),
        "luma_std": round(std, 2),
        "letterbox": round(bars, 3),
        "clip": round(clip, 3),
        "left_luma": round(left["mean"], 2),
        "left_edge": round(left["edge"], 2),
        "caption": round(cap, 4),
        "n_faces": len(faces),
        "face_cx": round(main["cx"], 3) if main else None,
        "face_cy": round(main["cy"], 3) if main else None,
        "face_area": round(main["area"], 4) if main else None,
        "face_score": round(main["score"], 3) if main else None,
        "parts": {
            "sharp": round(sharp_n, 3),
            "exposure": round(exposure_n, 3),
            "contrast": round(contrast_n, 3),
            "face": round(face_n, 3),
            "text_room": round(text_n, 3),
        },
        "overall": round(float(overall), 4),
    }
    return metrics, reasons


def greedy_diverse(rows: list[dict], k: int, min_gap: float) -> list[dict]:
    chosen: list[dict] = []
    for row in sorted(rows, key=lambda r: r["metrics"]["overall"], reverse=True):
        if any(abs(row["t"] - c["t"]) < min_gap for c in chosen):
            continue
        chosen.append(row)
        if len(chosen) >= k:
            break
    chosen.sort(key=lambda r: r["metrics"]["overall"], reverse=True)
    return chosen


def mmss(t: float) -> str:
    t = max(0.0, t)
    m, s = divmod(int(round(t)), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def contact_sheet(paths_and_labels: list[tuple[Path, str]], dest: Path, cols: int = 4) -> None:
    if not paths_and_labels:
        return
    thumbs = []
    tw, th = 320, 180
    for path, label in paths_and_labels:
        im = Image.open(path).convert("RGB")
        im = im.resize((tw, th), Image.Resampling.LANCZOS)
        thumbs.append((im, label))
    rows = math.ceil(len(thumbs) / cols)
    pad, caption = 8, 28
    sheet = Image.new("RGB", (cols * tw + pad * (cols + 1), rows * (th + caption) + pad * (rows + 1)), (30, 28, 26))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 14
        )
    except OSError:
        font = ImageFont.load_default()
    for i, (im, label) in enumerate(thumbs):
        r, c = divmod(i, cols)
        x = pad + c * (tw + pad)
        y = pad + r * (th + caption + pad)
        sheet.paste(im, (x, y))
        draw.text((x + 4, y + th + 6), label, fill=(236, 228, 214), font=font)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest, quality=90)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--every", type=float, default=6.0, help="Uniform sample interval in seconds.")
    ap.add_argument("--skip-head", type=float, default=25.0)
    ap.add_argument("--skip-tail", type=float, default=30.0)
    ap.add_argument("--score-width", type=int, default=640)
    ap.add_argument("--width", type=int, default=COVER_W)
    ap.add_argument("--height", type=int, default=COVER_H)
    ap.add_argument("--top-k", type=int, default=12)
    ap.add_argument("--min-gap", type=float, default=45.0, help="Minimum seconds between winners.")
    ap.add_argument("--scenes", action="store_true", help="Also sample ~0.4s after ffmpeg scene cuts.")
    ap.add_argument("--scene-threshold", type=float, default=0.35)
    ap.add_argument(
        "--scan-caption-gaps",
        action="store_true",
        help="1 fps low-res pass to catch 1–2s gaps between burned-in captions.",
    )
    ap.add_argument("--allow-no-face", action="store_true")
    ap.add_argument("--yunet", type=Path, default=DEFAULT_YUNET)
    args = ap.parse_args(argv)

    video = args.video.expanduser().resolve()
    if not video.is_file():
        raise SystemExit(f"video not found: {video}")
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise SystemExit("ffmpeg and ffprobe are required")

    out = args.out.expanduser().resolve()
    lowres = out / "candidates_lowres"
    top_dir = out / "top"
    out.mkdir(parents=True, exist_ok=True)

    duration = probe_duration(video)
    start = min(args.skip_head, max(0.0, duration - 1))
    end = max(start + 1.0, duration - args.skip_tail)
    print(f"duration={duration:.2f}s window={start:.1f}-{end:.1f}s", flush=True)

    print(f"extracting uniform frames every {args.every:g}s …", flush=True)
    items = extract_lowres_uniform(
        video, lowres, start=start, end=end, every=args.every, width=args.score_width
    )
    if args.scan_caption_gaps:
        print("scanning 1 fps for caption gaps …", flush=True)
        gap_dir = out / "caption_scan"
        gap_dir.mkdir(parents=True, exist_ok=True)
        run([
            "ffmpeg", "-hide_banner", "-y",
            "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(video),
            "-vf", "fps=1,scale=480:-2", "-q:v", "6",
            str(gap_dir / "c_%05d.jpg"),
        ])
        existing_t = [t for t, _ in items]
        added = 0
        for path in sorted(gap_dir.glob("c_*.jpg")):
            idx = int(path.stem.split("_")[1])
            t = start + (idx - 1)
            bgr = cv2.imread(str(path))
            if bgr is None:
                continue
            if caption_overlay_score(bgr) >= 0.015:
                continue
            if any(abs(t - u) < 0.6 for u in existing_t):
                continue
            dest = lowres / f"g_{idx:05d}_{t:07.2f}.jpg"
            shutil.copy2(path, dest)
            items.append((t, dest))
            existing_t.append(t)
            added += 1
        print(f"caption-gap frames added: {added}", flush=True)

    extra_times: list[float] = []
    if args.scenes:
        print("detecting scene cuts …", flush=True)
        cuts = detect_scene_cuts(video, args.scene_threshold)
        extra_times = [t + 0.4 for t in cuts if start <= t <= end]
        print(f"scene cuts kept: {len(extra_times)}", flush=True)
        # Extract only cuts that are not already near a uniform sample.
        existing = {round(t, 2) for t, _ in items}
        for i, t in enumerate(extra_times):
            if any(abs(t - u) < 0.75 for u, _ in items):
                continue
            dest = lowres / f"s_{i:05d}_{t:07.2f}.jpg"
            run([
                "ffmpeg", "-hide_banner", "-y", "-ss", f"{t:.3f}", "-i", str(video),
                "-frames:v", "1", "-vf", f"scale={args.score_width}:-2",
                "-q:v", "4", str(dest),
            ], check=False)
            if dest.is_file():
                items.append((t, dest))

    finder = FaceFinder(args.yunet)
    require_face = not args.allow_no_face
    scored: list[dict] = []
    rejected = 0
    reject_counts: dict[str, int] = {}
    for t, path in items:
        bgr = cv2.imread(str(path))
        if bgr is None:
            rejected += 1
            continue
        faces = finder.detect(bgr)
        metrics, reasons = _score_ok(bgr, faces, require_face=require_face)
        if reasons:
            rejected += 1
            for r in reasons:
                reject_counts[r] = reject_counts.get(r, 0) + 1
            continue
        scored.append({"t": t, "lowres": str(path), "metrics": metrics, "faces": [
            {k: v for k, v in f.items() if k != "landmarks"} for f in faces[:3]
        ]})

    print(f"scored={len(scored)} rejected={rejected} reasons={reject_counts}", flush=True)
    if not scored:
        raise SystemExit("no frames survived the filters; relax thresholds or pass --allow-no-face")

    winners = greedy_diverse(scored, args.top_k, args.min_gap)
    print("re-extracting full-res winners …", flush=True)
    for i, row in enumerate(winners, 1):
        dest = top_dir / f"{i:02d}_{mmss(row['t']).replace(':','-')}_{row['t']:.2f}.jpg"
        extract_fullres(video, row["t"], dest, width=args.width, height=args.height)
        row["rank"] = i
        row["fullres"] = str(dest)
        # Re-score the full-res crop so face placement matches the cover canvas.
        bgr = cv2.imread(str(dest))
        if bgr is not None:
            faces = finder.detect(bgr)
            metrics, reasons = _score_ok(bgr, faces, require_face=False)
            row["fullres_metrics"] = metrics
            row["fullres_faces"] = [
                {k: v for k, v in f.items() if k != "landmarks"} for f in faces[:3]
            ]

    # After full-res rescoring, keep the original rank order (diversity already applied)
    # but name a recommended frame: highest full-res overall among winners.
    def rec_key(r: dict) -> float:
        m = r.get("fullres_metrics") or r["metrics"]
        return m["overall"]

    recommended = max(winners, key=rec_key)
    rec_copy = top_dir / "recommended.jpg"
    shutil.copy2(recommended["fullres"], rec_copy)

    sheet_items = []
    for row in winners:
        m = row.get("fullres_metrics") or row["metrics"]
        label = f"#{row['rank']}  {mmss(row['t'])}  {m['overall']:.3f}"
        sheet_items.append((Path(row["fullres"]), label))
    contact_sheet(sheet_items, out / "top_contact_sheet.jpg")

    report = {
        "video": str(video),
        "duration": duration,
        "window": [start, end],
        "every": args.every,
        "require_face": require_face,
        "sampled": len(items),
        "scored": len(scored),
        "rejected": rejected,
        "reject_counts": reject_counts,
        "recommended": {
            "t": recommended["t"],
            "timecode": mmss(recommended["t"]),
            "path": recommended["fullres"],
            "metrics": recommended.get("fullres_metrics") or recommended["metrics"],
        },
        "top": winners,
    }
    (out / "scores.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # A short human-readable ranking
    lines = [
        f"video: {video}",
        f"window: {mmss(start)} – {mmss(end)} of {mmss(duration)}",
        f"sampled={len(items)} scored={len(scored)} rejected={rejected} {reject_counts}",
        f"recommended: {mmss(recommended['t'])}  {recommended['fullres']}",
        "",
        "rank  time    overall  sharp   face   text   face_cx  face_area  path",
    ]
    for row in winners:
        m = row.get("fullres_metrics") or row["metrics"]
        p = m["parts"]
        lines.append(
            f"{row['rank']:02d}    {mmss(row['t']):7s}  {m['overall']:.3f}    "
            f"{p['sharp']:.2f}   {p['face']:.2f}  {p['text_room']:.2f}  "
            f"{str(m['face_cx']):6s}  {str(m['face_area']):7s}  {row['fullres']}"
        )
    (out / "ranking.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines), flush=True)
    print(f"\nwrote {out / 'scores.json'}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as e:
        sys.stderr.write((e.stderr or e.stdout or str(e)) + "\n")
        raise SystemExit(e.returncode)

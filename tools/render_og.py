#!/usr/bin/env python3
"""把每期封面渲染成社交分享图 site/og/{slug}.jpg（1280×720 JPEG）。

微信、X、Facebook、LinkedIn 的抓取器都不渲染 SVG，所以 og:image 只能给位图。
- 已刊封面 site/covers/*.svg 只读不改，分享图与封面一一对应、版式完全相同。
- 分享图是构建产物：.gitignore 已忽略 site/og/，每次部署由 CI 重新渲染。
- 依赖见 tools/requirements-og.txt（resvg-py、pillow），只在这一步安装；
  tools/build.py 仍只用标准库。没装依赖时 build.py 会退回站点图标，
  CI 与部署则设置 REQUIRE_OG=1，缺图即失败。
- 封面文字用系统字体渲染。CI 里安装 fonts-noto-cjk，与封面工具的烟测环境一致；
  本地预览可用 --serif-family 指定一款已安装的中文衬线字体。

用法：
  python3 tools/render_og.py
  python3 tools/render_og.py --serif-family "Source Han Serif SC"
"""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path

import resvg_py
from PIL import Image

ROOT = Path(__file__).resolve().parent
SITE = ROOT.parent / 'site'
SIZE = (1280, 720)


def render(svg: str, serif_family: str) -> Image.Image:
    try:
        raw = resvg_py.svg_to_bytes(svg_string=svg, serif_family=serif_family)
    except TypeError:
        # 旧版 resvg-py 没有 serif_family 参数时，交给 SVG 自带的字体栈
        raw = resvg_py.svg_to_bytes(svg_string=svg)
    return Image.open(io.BytesIO(bytes(raw))).convert('RGB')


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--serif-family', default='Noto Serif CJK SC',
                    help='SVG 里 serif 回退到的字体族（默认 Noto Serif CJK SC）')
    ap.add_argument('--quality', type=int, default=85, help='JPEG 质量（默认 85）')
    args = ap.parse_args()

    master = json.loads((ROOT / 'lex-master.json').read_text(encoding='utf-8'))
    out = SITE / 'og'
    out.mkdir(exist_ok=True)
    for e in master:
        rel = (e.get('cover') or '').lstrip('/')
        if not rel:
            print('skip, no cover:', e['slug'])
            continue
        im = render((SITE / rel).read_text(encoding='utf-8'), args.serif_family)
        if im.size != SIZE:
            raise SystemExit(f'cover {rel} rendered at {im.size}, expected {SIZE}')
        dest = out / f"{e['slug']}.jpg"
        im.save(dest, 'JPEG', quality=args.quality, optimize=True, progressive=True)
        print(f'og: {dest.relative_to(SITE.parent).as_posix()} {dest.stat().st_size // 1024} KB')


if __name__ == '__main__':
    main()

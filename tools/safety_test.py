#!/usr/bin/env python3
"""发布安全测试（PLATFORM.md §4.3 的三项安全测试）。只用标准库。

每一项都在仓库的临时副本里放进一样「不该公开」的东西，断言构建会失败，
最后再跑一次干净构建，断言能通过。真实仓库不会被改动。

  ① 白名单外的文件能否进入构建产物
  ② 未登记的期数能否经由正文、链接进入 RSS / 搜索数据 / 站点地图 / 页面
  ③ 本地路径、写作工坊材料能否进入公开产物

用法：python3 tools/safety_test.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build(repo: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONUTF8='1')
    env.pop('REQUIRE_OG', None)
    return subprocess.run([sys.executable, 'tools/build.py'], cwd=repo, env=env,
                          capture_output=True, text=True, encoding='utf-8')


def stray_file(repo: Path) -> None:
    p = repo / 'site' / 'notes' / 'draft.txt'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('草稿，不该公开', encoding='utf-8')


def unregistered_body(repo: Path) -> None:
    (repo / 'site' / 'zh' / '999-private-draft.html').write_text('<p>未登记的草稿正文</p>', encoding='utf-8')


def unregistered_link(repo: Path) -> None:
    t = repo / 'tools' / 'translations.json'
    data = json.loads(t.read_text(encoding='utf-8'))
    first = next(iter(data))
    data[first]['desc'] += ' 见 <a href="/shichubai-reads/ep/999-private-draft/">草稿</a>'
    t.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def private_path(repo: Path) -> None:
    t = repo / 'tools' / 'translations.json'
    data = json.loads(t.read_text(encoding='utf-8'))
    first = next(iter(data))
    data[first]['desc'] += r' 素材见 C:\Users\me\Documents\写作\写作训练\第六周.md'
    t.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


CASES = [
    ('① 白名单外的文件', stray_file, 'allowed_outputs'),
    ('② 未登记的正文片段', unregistered_body, 'allowed_outputs'),
    ('② 指向未登记期数的链接', unregistered_link, 'unregistered episode'),
    ('③ 本地路径与工坊材料', private_path, 'private material'),
]


def main() -> int:
    failed = 0
    with tempfile.TemporaryDirectory(prefix='scb-safety-') as tmp:
        base = Path(tmp) / 'clean'
        shutil.copytree(ROOT, base, ignore=shutil.ignore_patterns('.git', '__pycache__'))
        for i, (name, inject, expect) in enumerate(CASES):
            repo = Path(tmp) / f'case{i}'
            shutil.copytree(base, repo)
            inject(repo)
            r = build(repo)
            out = r.stdout + r.stderr
            ok = r.returncode != 0 and expect in out
            print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f'\n  exit={r.returncode}\n  ' + out[-600:]))
            failed += not ok
        r = build(base)
        ok = r.returncode == 0 and 'checks: ok' in r.stdout
        print(('PASS ' if ok else 'FAIL ') + '干净构建' + ('' if ok else '\n  ' + (r.stdout + r.stderr)[-600:]))
        failed += not ok
    print('safety tests:', 'ok' if not failed else f'{failed} failed')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())

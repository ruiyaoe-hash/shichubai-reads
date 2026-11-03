#!/usr/bin/env python3
"""时初白精读 · 静态站构建器。

壳层来自 https://github.com/joeseesun/lexfridman-cn （MIT，仅代码）。
只使用 Python 标准库。

输入：
  tools/lex-master.json     单集目录（最新在前）
  tools/translations.json   中文标题 / 嘉宾 / 简介
  tools/feed_audio.json     播放地址。单集 mp3 只用 GitHub Release 的 https 绝对地址
                            （标签 audio-001、audio-002……）；没有则留空，页面不放播放器。
                            这些标签只放内容文件，不要用来发布站点版本。不要把 mp3 放进 git。
  site/zh/{slug}.html       中文精读正文片段
  site/data/zh-index.json   已有精读的 slug 列表
  site/covers/              自有封面（无 YouTube 时使用）

输出（发布根目录就是 site/）：
  site/index.html           注入首页头条、卡片、页脚
  site/ep/{slug}/index.html 单集页
  site/data/episodes.json   首页数据
  site/sitemap.xml site/feed.xml site/llms.txt
  site/archive/ site/disclaimer/ site/404.html site/offline.html

项目页路径前缀来自站点 URL 的 path。默认：
  https://ruiyaoe-hash.github.io/shichubai-reads/
换自定义域名（路径为 /）时设置 SITE_DOMAIN，或用 BASE_PATH= 强制空前缀。
不用 <base>：它会把目录锚点 (#) 解析到站点根，精读侧栏会跳错页。
"""
import datetime
import email.utils
import html as H
import json
import os
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
SITE = ROOT.parent / 'site'
DOMAIN = os.environ.get('SITE_DOMAIN', 'https://ruiyaoe-hash.github.io/shichubai-reads').rstrip('/')
BASE = os.environ.get('BASE_PATH', urlparse(DOMAIN).path).rstrip('/')
TODAY = datetime.date.today().isoformat()
CSS_V, APP_V, EP_V = 2, 2, 2
SITE_NAME = '时初白精读'
TAGLINE = '在你想放弃时，把火递回来。'


def sp(path):
    """站内根路径 → 项目页路径。path 以 / 开头。"""
    if not path.startswith('/'):
        path = '/' + path
    return f'{BASE}{path}' if BASE else path


def absu(path):
    if not path.startswith('/'):
        path = '/' + path
    return f'{DOMAIN}{path}'


THEME_BTN = (
    '<button class="theme-toggle" type="button" data-theme-toggle aria-label="切换浅色 / 深色模式" title="切换浅色 / 深色模式">'
    '<svg class="i-sun" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/>'
    '<path d="M12 2.5v2M12 19.5v2M4.6 4.6l1.4 1.4M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4L6 18M18 6l1.4-1.4"/></svg>'
    '<svg class="i-moon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5a8.5 8.5 0 1 0 10.7 10.7z"/></svg>'
    '</button>'
)
ICON_SEARCH = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.6-3.6"/></svg>'
ICON_PLAY = '<svg class="i-play" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13a1 1 0 0 0 1.5.86l10.6-6.5a1 1 0 0 0 0-1.72L9.5 4.64A1 1 0 0 0 8 5.5z"/></svg>'
ICON_PAUSE = '<svg class="i-pause" viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="5" width="4.2" height="14" rx="1.2"/><rect x="13.8" y="5" width="4.2" height="14" rx="1.2"/></svg>'

THEME_SCRIPT = """<script>
(function () {
  var d = document.documentElement, g = function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } };
  var t = g('lex-theme'), f = g('lex-font'), z = g('lex-size'), lh = g('lex-lh'), w = g('lex-measure');
  var BG = { light: '#ffffff', sepia: '#f5eddc', dark: '#141414' };
  if (!BG[t]) t = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
  d.setAttribute('data-theme', t);
  var FONTS = {
    sans: 'https://fonts.googleapis.cn/css2?family=Noto+Sans+SC:wght@400;600&display=swap',
    serif: 'https://fonts.googleapis.cn/css2?family=Noto+Serif+SC:wght@400;600&display=swap',
    kai: 'https://cdn.jsdelivr.net/npm/lxgw-wenkai-screen-webfont@1.7.0/lxgwwenkaiscreen.css',
    wei: 'https://fonts.googleapis.cn/css2?family=ZCOOL+XiaoWei&display=swap',
    song: 'https://cdn.jsdelivr.net/npm/@chinese-fonts/jhlst@3.0.0/dist/%E4%BA%AC%E8%8F%AF%E8%80%81%E5%AE%8B%E4%BD%93v2_002/result.css'
  };
  window.__lexFonts = FONTS;
  window.__lexLoadFont = function (k) {
    if (!FONTS[k] || document.getElementById('lexfont-' + k)) return;
    var l = document.createElement('link'); l.rel = 'stylesheet'; l.href = FONTS[k]; l.id = 'lexfont-' + k;
    document.head.appendChild(l);
  };
  if (!f) f = 'serif';
  if (FONTS[f]) { d.setAttribute('data-font', f); window.__lexLoadFont(f); }
  if (z && /^(1[5-9]|2[0-2])$/.test(z)) d.style.setProperty('--read-size', z + 'px');
  if (lh && /^(1\\.\\d+|2(\\.\\d+)?)$/.test(lh)) d.style.setProperty('--read-lh', lh);
  if (w && /^\\d{3}$/.test(w)) d.style.setProperty('--measure', w + 'px');
  var meta = document.querySelector('meta[name="theme-color"]');
  function syncMeta() { if (meta) meta.content = BG[t]; }
  syncMeta();
  window.__lexSetTheme = function (n) {
    if (!BG[n]) return;
    t = n;
    try { localStorage.setItem('lex-theme', t); if (t !== 'dark') localStorage.setItem('lex-light', t); } catch (e) {}
    d.classList.add('theme-anim');
    d.setAttribute('data-theme', t);
    syncMeta();
    setTimeout(function () { d.classList.remove('theme-anim'); }, 320);
    document.dispatchEvent(new CustomEvent('lex-theme', { detail: t }));
  };
  window.__lexThemeToggle = function () { window.__lexSetTheme(t === 'dark' ? (g('lex-light') || 'light') : 'dark'); };
  (function () {
    var vv = window.visualViewport;
    if (!vv) return;
    var queued = false;
    function apply() {
      queued = false;
      var off = Math.round(window.innerHeight - vv.offsetTop - vv.height);
      d.style.setProperty('--vv-off', Math.max(0, off) + 'px');
    }
    function onVV() { if (!queued) { queued = true; requestAnimationFrame(apply); } }
    vv.addEventListener('resize', onVV);
    vv.addEventListener('scroll', onVV);
    window.addEventListener('orientationchange', onVV);
    apply();
  })();
  document.addEventListener('click', function (e) {
    var el = e.target.closest ? e.target : e.target.parentNode;
    if (el.closest('[data-theme-toggle]')) return window.__lexThemeToggle();
    var o = el.closest('[data-open]');
    if (o) { var m = document.getElementById(o.getAttribute('data-open')); if (m) { m.hidden = false; var c = m.querySelector('.modal-close'); if (c) c.focus(); } return; }
    var mm = el.closest('.modal');
    if (mm && (el === mm || el.closest('.modal-close'))) { mm.hidden = true; return; }
    var sh = el.closest('[data-share]');
    if (sh) {
      var data = { title: document.title, url: location.href.split('#')[0] };
      if (navigator.share) { navigator.share(data).catch(function () {}); }
      else if (navigator.clipboard) navigator.clipboard.writeText(data.title + ' ' + data.url).then(function () { var tx = sh.textContent; sh.textContent = '链接已复制'; setTimeout(function () { sh.textContent = tx; }, 1600); });
      return;
    }
    var cf = el.closest('[data-copy-feed]');
    if (cf) {
      var base = d.getAttribute('data-base') || '';
      var url = location.origin + base + '/feed.xml', label = cf.textContent;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(function () { cf.textContent = '已复制'; setTimeout(function () { cf.textContent = label; }, 1600); }, function () { location.href = url; });
      } else location.href = url;
    }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') Array.prototype.forEach.call(document.querySelectorAll('.modal'), function (m) { m.hidden = true; });
  });
  document.addEventListener('load', function (e) { var im = e.target; if (im.tagName === 'IMG') im.classList.add('ok'); }, true);
  document.addEventListener('error', function (e) { var im = e.target; if (im.tagName === 'IMG' && !im.getAttribute('onerror')) im.classList.add('ok'); }, true);
  var deferred = null;
  function showInstall() { Array.prototype.forEach.call(document.querySelectorAll('[data-install]'), function (b) { b.hidden = false; }); }
  window.addEventListener('beforeinstallprompt', function (e) { e.preventDefault(); deferred = e; showInstall(); });
  var standalone = (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) || navigator.standalone;
  if (/iphone|ipad|ipod/i.test(navigator.userAgent) && !standalone) document.addEventListener('DOMContentLoaded', showInstall);
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-install]');
    if (!b) return;
    if (deferred) { deferred.prompt(); deferred.userChoice.finally(function () { deferred = null; b.hidden = true; }); }
    else { var m = document.getElementById('installModal'); if (m) m.hidden = false; }
  });
  if ('serviceWorker' in navigator && location.protocol === 'https:') {
    window.addEventListener('load', function () {
      var base = d.getAttribute('data-base') || '';
      navigator.serviceWorker.register(base + '/sw.js').catch(function () {});
    });
  }
})();
</script>"""


def head_extra():
    return (
        '<link rel="preconnect" href="https://fonts.googleapis.cn">'
        '<link rel="preconnect" href="https://fonts.gstatic.cn" crossorigin>'
        '<link rel="preconnect" href="https://i.ytimg.com">'
        '<link rel="stylesheet" href="https://fonts.googleapis.cn/css2?family=Libre+Caslon+Text:ital,wght@0,400;0,700;1,400'
        '&family=Noto+Serif+SC:wght@500;700&display=swap">\n'
        f'<link rel="icon" href="{sp("/favicon.ico")}" sizes="32x32">'
        f'<link rel="icon" href="{sp("/icon.svg")}" type="image/svg+xml">'
        f'<link rel="apple-touch-icon" href="{sp("/apple-touch-icon.png")}">'
        f'<link rel="manifest" href="{sp("/site.webmanifest")}">\n'
        '<meta name="apple-mobile-web-app-title" content="时初白">'
        '<meta name="apple-mobile-web-app-capable" content="yes">'
        '<meta name="mobile-web-app-capable" content="yes">'
        '<meta name="apple-mobile-web-app-status-bar-style" content="default">'
        '<meta name="format-detection" content="telephone=no">'
        '<noscript><style>.thumb img,.cont-thumb img,.hero-media img{opacity:1}</style></noscript>'
    )


def feed_link():
    return (f'<link rel="alternate" type="application/rss+xml" title="{SITE_NAME}" href="{absu("/feed.xml")}">')


def site_header():
    home = sp('/')
    return (
        '<header class="site-header slim">\n  <div class="wrap header-inner">\n'
        f'    <a class="hdr-back" href="{home}">← 全部单集</a>\n'
        f'    <a class="wordmark" href="{home}" aria-label="{SITE_NAME} · 首页">时初白 <span>精读</span></a>\n'
        f'    <div class="header-actions"><a class="hdr-icon" href="{home}#search" aria-label="搜索全部单集" title="搜索">{ICON_SEARCH}</a>{THEME_BTN}</div>\n'
        '  </div>\n</header>'
    )


def site_footer():
    home = sp('/')
    return f"""<footer class="site-footer">
  <div class="wrap">
    <div class="ft-top">
      <a class="ft-mark" href="{home}">时初白 <span>精读</span></a>
      <p class="ft-tag">{TAGLINE}</p>
    </div>
    <div class="ft-cols">
      <nav class="ft-col" aria-label="浏览"><h2>浏览</h2>
        <a href="{home}">全部单集</a><a href="{home}?f=zh">中文精读</a><a href="{sp('/archive/')}">单集目录</a><a href="{home}#search">搜索</a>
        <button type="button" data-install hidden>安装为应用</button></nav>
      <nav class="ft-col" aria-label="订阅"><h2>订阅</h2>
        <a href="{sp('/feed.xml')}">RSS 全文订阅</a><button type="button" data-copy-feed>复制 RSS 地址</button></nav>
      <nav class="ft-col" aria-label="关于"><h2>关于</h2>
        <a href="{sp('/disclaimer/')}">免责声明</a>
        <a href="https://github.com/ruiyaoe-hash/shichubai-reads" target="_blank" rel="noopener">本站代码</a>
        <a href="https://github.com/joeseesun/lexfridman-cn" target="_blank" rel="noopener">壳层来源（MIT）</a>
        <a href="{sp('/llms.txt')}">llms.txt</a></nav>
      <div class="ft-col ft-support"><h2>读法</h2>
        <p>白纸、墨字、一条细线。没有话题分类，只有按时间排下去的精读。火不用很大，能递回来就好。</p></div>
    </div>
    <div class="ft-bottom">
      <span>© 2026 时初白精读 · 非官方评论站点</span>
      <span>不托管访谈视频。个别单集的音频在站内播放，不是官方播客。中文精读是依据公开访谈与报道写的评论，不是官方文稿；表述以原访谈为准。</span>
    </div>
  </div>
</footer>
<div id="installModal" class="modal" hidden role="dialog" aria-modal="true" aria-labelledby="installT">
  <div class="modal-card">
    <button type="button" class="modal-close" aria-label="关闭">×</button>
    <h3 id="installT">添加到主屏幕</h3>
    <p class="modal-sub">像读一本杂志一样打开。读过的文章可以离线再看。</p>
    <ol class="install-steps"><li>点 Safari 底部的「分享」按钮 <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v12M7.5 7.5L12 3l4.5 4.5M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/></svg></li><li>向下滑，选择「添加到主屏幕」</li><li>点右上角「添加」</li></ol>
  </div>
</div>"""


def colophon():
    return (
        '<aside class="colophon" aria-label="致读者">'
        '<div class="colo-k">致读者</div>'
        '<p>这篇是时初白的评论，不是官方整理稿。它从公开报道里先搭一段骨架，等原片的合法链接补上，再按访谈本身重写。'
        '这里没有广告。若你正想把书合上，希望这一页能把火递回来一点。</p>'
        '<div class="colo-actions">'
        '<button type="button" class="colo-link" data-share>分享这篇</button>'
        f'<a class="colo-link" href="{sp("/feed.xml")}">RSS 订阅</a>'
        f'<a class="colo-link" href="{sp("/disclaimer/")}">说明</a></div></aside>'
    )


EP_SHELL = """<!DOCTYPE html>
<html lang="zh-CN" data-base="{base}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="dark light">
<meta name="theme-color" content="#ffffff">
<title>{title_tag}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{og_img}">
<meta property="og:image:width" content="1280">
<meta property="og:image:height" content="720">
<meta property="og:image:alt" content="{og_title}">
<meta property="og:site_name" content="{site_name}">
<meta property="og:locale" content="zh_CN">
{article_meta}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{og_title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{og_img}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
{md_link}
<script type="application/ld+json">{ldjson}</script>
{theme_script}
{head_extra}
{feed_link}
<link rel="stylesheet" href="{css_href}">
</head>
<body>
<a class="skip-link" href="#main">跳到主要内容</a>
{site_header}
<main class="wrap ep-main{main_cls}" id="main">
  <article class="ep">
    <header class="ep-head">
      <div class="ep-kicker">{kicker}</div>
      <h1 class="ep-title">{h1}</h1>
      {orig_line}
      {dek}
      <div class="ep-byline">{byline}</div>
      <div class="ep-actions"><button type="button" class="fav-btn" id="favBtn" hidden aria-pressed="false"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6.5 3.5h11a1 1 0 0 1 1 1V20.5L12 17.1 5.5 20.5V4.5a1 1 0 0 1 1-1z"/></svg><span class="fav-label">收藏</span></button></div>
    </header>
    {media_html}
    <section class="content-tabs">
      {tab_buttons}
      {panel_zh}
      {panel_tr}
      {no_tr_note}
    </section>
    {resources}
    <nav class="ep-prevnext" aria-label="上一期 / 下一期">
      {prevnext}
    </nav>
  </article>
  <aside class="ep-toc" aria-label="精读目录"></aside>
</main>
{site_footer}
<script src="{ep_href}"></script>
</body>
</html>
"""

master = json.load(open(ROOT / 'lex-master.json'))
feed = json.load(open(ROOT / 'feed_audio.json'))
trans = json.load(open(ROOT / 'translations.json')) if (ROOT / 'translations.json').exists() else {}
zh_index = json.load(open(SITE / 'data' / 'zh-index.json'))
ZH = set(zh_index.get('slugs', []))


# 内容音频：每期一个 Release，标签 audio-NNN。不是站点版本发布。
RELEASE_AUDIO_RE = re.compile(
    r'^https://github\.com/[\w.-]+/[\w.-]+/releases/download/audio-\d+/[^/?#]+\.mp3$'
)
EP001_AUDIO = (
    'https://github.com/ruiyaoe-hash/shichubai-reads/releases/download/'
    'audio-001/001-jiang-chenglan.mp3'
)


def is_release_audio(raw):
    return bool(raw) and bool(RELEASE_AUDIO_RE.match(raw))


def audio_for(e):
    """feed_audio.json 的原始值。Release 用 https 绝对地址；以 / 开头的是站点根路径。"""
    by_num = feed.get('by_num') or {}
    by_slug = feed.get('by_slug') or {}
    if e.get('num') is not None and str(e['num']) in by_num:
        return by_num[str(e['num'])] or None
    return by_slug.get(e['slug']) or None


def publish_audio(raw):
    """页面里使用的地址。https 原样保留，不拼 BASE_PATH；站内路径才加项目页前缀。"""
    if not raw:
        return None
    if raw.startswith(('http://', 'https://')):
        return raw
    if not raw.startswith('/'):
        raw = '/' + raw
    return sp(raw)


def check_feed_audio():
    """单集 mp3 只能指向 audio-NNN Release，不能再指向仓库里的文件。"""
    for bucket in ('by_num', 'by_slug'):
        for key, raw in (feed.get(bucket) or {}).items():
            if not raw:
                continue
            if not is_release_audio(raw):
                raise SystemExit(
                    f'feed_audio {bucket}[{key}] must be a GitHub Release download URL '
                    f'on tag audio-NNN, not a file in the repo: {raw}'
                )
    got_num = (feed.get('by_num') or {}).get('1')
    got_slug = (feed.get('by_slug') or {}).get('001-jiang-chenglan')
    if got_num != EP001_AUDIO or got_slug != EP001_AUDIO:
        raise SystemExit('episode 001 audio must be the audio-001 Release asset')


def text_for(slug):
    """保留壳层的文稿入口。本站默认不入库文稿；有本地纯文本时才显示。"""
    p = SITE / 'transcripts' / f'{slug}.txt'
    if p.exists():
        return 'note', p.read_text()
    return None, None


def fmt_date(d):
    if not d or len(d) < 7:
        return ''
    return f'{d[:4]} 年 {int(d[5:7])} 月'


def strip_no(t):
    return re.sub(r'^#\d+\s*[–—:-]?\s*', '', t or '')


def norm_zh(zh):
    return re.sub(r'^(#\d+)\s*[–—-]\s*', r'\1 ', zh or '')


def cover_of(e):
    rel = e.get('cover') or ''
    if not rel:
        return None
    if not rel.startswith('/'):
        rel = '/' + rel
    if (SITE / rel.lstrip('/')).exists():
        return rel
    print('warning: missing cover', rel)
    return None


def build_data():
    eps = []
    for e in master:
        tag, _ = text_for(e['slug'])
        info = trans.get(e['slug'], {})
        eps.append({
            'n': e.get('num'), 't': e['title'], 's': e['slug'], 'd': e.get('date'),
            'y': e.get('ytId') or None,
            'cv': cover_of(e),
            'zh': info.get('zh'),
            'guest': info.get('guest'),
            'tr': tag, 'au': bool(audio_for(e)),
            'r': 1 if e['slug'] in ZH and (SITE / 'zh' / f"{e['slug']}.html").exists() else 0,
            'ds': info.get('desc'),
        })
    out = {'updated': TODAY, 'episodes': eps}
    (SITE / 'data').mkdir(exist_ok=True)
    (SITE / 'data' / 'episodes.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')))
    print(f"episodes.json: {len(eps)} eps, zh={sum(1 for x in eps if x['r'])}, au={sum(1 for x in eps if x['au'])}")
    return eps


def prune(o):
    if isinstance(o, dict):
        return {k: prune(v) for k, v in o.items() if v not in (None, '', [], {})}
    if isinstance(o, list):
        return [prune(v) for v in o]
    return o


def html_to_md(h):
    h = re.sub(r'\s*<h2[^>]*>(.*?)</h2>\s*', lambda m: f'\n\n## {m.group(1)}\n\n', h, flags=re.S)
    h = re.sub(r'\s*<h3[^>]*>(.*?)</h3>\s*', lambda m: f'\n\n### {m.group(1)}\n\n', h, flags=re.S)
    h = re.sub(r'\s*<blockquote>(.*?)</blockquote>\s*',
               lambda m: '\n\n' + '\n'.join('> ' + ln for ln in re.sub(r'</?p>', '\n', m.group(1)).strip().splitlines() if ln.strip()) + '\n\n',
               h, flags=re.S)
    h = re.sub(r'\s*<li>(.*?)</li>\s*', lambda m: f'\n- {m.group(1).strip()}', h, flags=re.S)
    h = re.sub(r'</?(ul|ol)>', '\n', h)
    h = re.sub(r'<(strong|b)>(.*?)</\1>', r'**\2**', h, flags=re.S)
    h = re.sub(r'<(em|i)>(.*?)</\1>', r'*\2*', h, flags=re.S)
    h = re.sub(r'<br\s*/?>', '  \n', h)
    h = re.sub(r'\s*<p>(.*?)</p>\s*', lambda m: f'\n\n{m.group(1).strip()}\n\n', h, flags=re.S)
    h = H.unescape(re.sub(r'<[^>]+>', '', h))
    return re.sub(r'\n{3,}', '\n\n', h).strip() + '\n'


def thumb_img(x, hero=False):
    if x.get('y'):
        y = x['y']
        if hero:
            return (f'<img src="https://i.ytimg.com/vi/{y}/maxresdefault.jpg" alt="" '
                    f'onerror="this.onerror=null;this.src=\'https://i.ytimg.com/vi/{y}/hqdefault.jpg\'">')
        return (f'<img loading="lazy" decoding="async" src="https://i.ytimg.com/vi/{y}/mqdefault.jpg" '
                f'alt="" width="320" height="180">')
    if x.get('cv'):
        src = H.escape(sp(x['cv']))
        if hero:
            return f'<img src="{src}" alt="">'
        return f'<img loading="lazy" decoding="async" src="{src}" alt="" width="320" height="180">'
    if hero:
        return ''
    label = f'{x["n"]:03d}' if isinstance(x.get('n'), int) else '时'
    return f'<div class="no-img">{label}</div>'


def build_page(i, eps):
    e = master[i]
    slug, num, title = e['slug'], e.get('num'), e['title']
    d = e.get('date') or ''
    y = e.get('ytId') or None
    audio_raw = audio_for(e)
    audio = publish_audio(audio_raw)
    info = trans.get(slug, {})
    zh_title = norm_zh(info.get('zh'))
    guest, lede = info.get('guest'), info.get('desc')
    zh_file = SITE / 'zh' / f'{slug}.html'
    has_zh = slug in ZH and zh_file.exists()
    tr_tag, tr_text = text_for(slug)
    x = eps[i]
    url = absu(f'/ep/{slug}/')
    plain = strip_no(zh_title) or strip_no(title) or title
    title_tag = f'{plain} | {SITE_NAME}' + (f' · 第 {num} 期' if num else '')
    desc = lede or f'{guest or SITE_NAME}：{plain}'
    og_title = plain
    og_img = absu(x['cv']) if x.get('cv') else absu('/icon-512.png')

    zh_raw = zh_file.read_text() if has_zh else ''
    zh_chars = len(re.sub(r'\s+', '', H.unescape(re.sub(r'<[^>]+>', '', zh_raw))))
    read_min = max(1, round(zh_chars / 450)) if zh_chars else 0
    zh_mtime = datetime.date.fromtimestamp(zh_file.stat().st_mtime).isoformat() if has_zh else None
    zh_sections = [H.unescape(re.sub(r'<[^>]+>', '', s)).strip() for s in re.findall(r'<h2[^>]*>(.*?)</h2>', zh_raw)]

    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "Article", "@id": f'{url}#article', "headline": plain[:110],
         "alternativeHeadline": title, "description": lede,
         "inLanguage": "zh-CN", "datePublished": d or zh_mtime, "dateModified": zh_mtime or d or None,
         "wordCount": zh_chars or None, "timeRequired": f'PT{read_min}M' if read_min else None,
         "image": og_img, "articleSection": zh_sections[:12] or None,
         "isAccessibleForFree": True, "mainEntityOfPage": url,
         "author": {"@type": "Organization", "name": SITE_NAME, "url": absu('/')},
         "publisher": {"@id": f'{DOMAIN}/#org'},
         "isBasedOn": {"@type": "Conversation", "name": e.get('sourceLabel') or plain,
                       "url": e.get('sourceUrl') or None,
                       "description": "公开访谈。本页不嵌入、不托管视频。" if e.get('sourceUrl')
                       else "公开访谈。原片外链未核到之前，本页不嵌入、不托管视频。"}},
        {"@type": "Organization", "@id": f'{DOMAIN}/#org', "name": SITE_NAME, "url": absu('/'),
         "slogan": TAGLINE},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": absu('/')},
            {"@type": "ListItem", "position": 2, "name": plain, "item": url}]},
    ]}
    ldjson = json.dumps(prune(ld), ensure_ascii=False).replace('<', '\\u003c')

    h1 = H.escape(plain)
    orig_line = f'<p class="ep-title-en" lang="en">{H.escape(strip_no(title))}</p>' if zh_title else ''
    kicker_bits = [f'第 {num} 期' if num else '特别篇']
    if has_zh:
        kicker_bits.append('<span class="k-zh">中文精读</span>')
    kicker = '<span class="k-sep">·</span>'.join(kicker_bits)
    dek = f'<p class="ep-dek">{H.escape(lede)}</p>' if lede else ''
    by = []
    if guest:
        by.append(f'<span>{H.escape(guest)}</span>')
    if d:
        by.append(f'<time datetime="{H.escape(d)}">{fmt_date(d)}</time>')
    if e.get('sourceLabel'):
        by.append(f'<span>{H.escape(e["sourceLabel"])}</span>')
    if read_min:
        wan = f'{zh_chars / 10000:.1f} 万字' if zh_chars >= 10000 else f'{zh_chars} 字'
        by.append(f'<span>精读约 {wan} · 阅读 {read_min} 分钟</span>')
    byline = '<span class="k-sep">·</span>'.join(by)

    if audio:
        audio_html = (
            f'<div class="audio-player" data-slug="{H.escape(slug)}" data-title="{H.escape(zh_title or title)}">'
            f'<audio src="{H.escape(audio)}" preload="none"></audio>'
            f'<button class="ap-play" type="button" aria-label="播放">{ICON_PLAY}{ICON_PAUSE}</button>'
            f'<div class="ap-mid"><div class="ap-line1"><span class="ap-label">音频</span>'
            f'<span class="ap-time"><span class="ap-cur">00:00</span> / <span class="ap-dur">--:--</span></span></div>'
            f'<div class="ap-bar" role="slider" aria-label="播放进度" tabindex="0"><div class="ap-buf"></div><div class="ap-fill"></div></div>'
            f'<div class="ap-line2"><button type="button" class="ap-skip" data-s="-15" aria-label="后退 15 秒">−15s</button>'
            f'<button type="button" class="ap-skip" data-s="15" aria-label="前进 15 秒">+15s</button>'
            f'<button type="button" class="ap-rate" aria-label="播放速度">1×</button>'
            f'<span class="ap-resume" hidden>已从上次位置继续 · <button type="button" class="ap-restart">从头听</button></span>'
            f'</div></div></div>')
    else:
        audio_html = ''
    video_html = ''
    if y:
        video_html = (f'<button type="button" class="video-facade" data-yt="{H.escape(y)}" aria-label="播放视频">'
                      f'<img src="https://i.ytimg.com/vi/{H.escape(y)}/mqdefault.jpg" alt="" width="320" height="180">'
                      f'<span class="vf-play">{ICON_PLAY}<span>看视频</span></span></button>')
    if audio or y:
        media_html = f'<div class="media{" has-audio" if audio else ""}">{video_html}{audio_html}</div>'
    else:
        src = e.get('sourceUrl') or ''
        if src:
            listen = f'<a href="{H.escape(src)}" target="_blank" rel="noopener">来源页收听</a>'
        else:
            listen = '来源页收听（原片外链待补，见下方资源与出处）'
        media_html = f'<div class="ep-notice">本集不在站内托管音视频。{listen}</div>'

    tabs = ['<div class="tabs" role="tablist">']
    if has_zh:
        tabs.append('<button class="tab-btn" type="button" data-tab="zh" role="tab" aria-controls="panel-zh">中文精读</button>')
    if tr_tag:
        tabs.append('<button class="tab-btn" type="button" data-tab="tr" role="tab" aria-controls="panel-tr">文字记录</button>')
    tabs.append('</div>')
    tab_buttons = ''.join(tabs) if (has_zh or tr_tag) else ''
    panel_zh = ''
    if has_zh:
        panel_zh = (
            f'<div class="tab-panel" id="panel-zh" data-panel="zh">'
            f'<div class="zh-note">中文精读是本站依据公开访谈与报道写的评论，不是官方文稿，也不是逐字翻译，可能有偏差或遗漏。'
            f'表述以原访谈为准。<a href="{sp("/disclaimer/")}">说明</a></div>'
            f'<div class="zh-article">{zh_raw}</div>{colophon()}</div>')
    panel_tr = ''
    if tr_tag:
        panel_tr = (f'<div class="tab-panel" id="panel-tr" data-panel="tr">'
                    f'<div class="tr-note">本地文字记录，仅在仓库提供纯文本时出现。</div>'
                    f'<div class="transcript-text">{H.escape(tr_text)}</div></div>')
    no_tr_note = '' if (has_zh or tr_tag) else '<div class="ep-notice">这篇还没有正文。</div>'

    res = ['<section class="ep-resources"><h2>本集资源与出处</h2><ul>']
    res.append(f'<li><span class="res-k">嘉宾</span>{H.escape(guest or "—")}</li>')
    res.append(f'<li><span class="res-k">来源</span>{H.escape(e.get("sourceLabel") or "公开访谈")}'
               f'<span class="res-sub">报道日期 {H.escape(d) or "待核"}；原片播出日以原片为准</span></li>')
    if e.get('sourceUrl'):
        res.append(f'<li><span class="res-k">原片</span><a href="{H.escape(e["sourceUrl"])}" target="_blank" rel="noopener">来源页</a>'
                   f'<span class="res-sub">外链，本站不托管视频文件</span></li>')
    else:
        res.append('<li><span class="res-k">原片</span>TODO：补上访谈原片的合法外链（抖音 / 视频号或其他公开页面）。'
                   '未核到稳定地址之前，本页不嵌入、不下载、不托管任何视频。</li>')
    if audio:
        if is_release_audio(audio_raw):
            res.append(f'<li><span class="res-k">音频</span><a href="{H.escape(audio)}" target="_blank" rel="noopener">访谈音频</a>'
                       f'<span class="res-sub">供本页收听，不是官方播客</span></li>')
        elif audio_raw.startswith(('http://', 'https://')):
            res.append(f'<li><span class="res-k">音频</span><a href="{H.escape(audio)}" target="_blank" rel="noopener">访谈音频</a></li>')
        else:
            res.append(f'<li><span class="res-k">音频</span><a href="{H.escape(audio)}">访谈音频</a>'
                       f'<span class="res-sub">供本页收听，不是官方播客</span></li>')
    else:
        res.append('<li><span class="res-k">音频</span>暂无音频，故不放置播放器。</li>')
    for rep in e.get('reports') or []:
        if rep.get('url'):
            res.append(f'<li><span class="res-k">报道</span><a href="{H.escape(rep["url"])}" target="_blank" rel="noopener">{H.escape(rep.get("label") or rep["url"])}</a>'
                       f'<span class="res-sub">转述，非原片</span></li>')
    res.append('</ul></section>')
    resources = ''.join(res)

    def pn_link(ne, label):
        if not ne:
            return '<span></span>'
        t = ne['zh'] or ne['t']
        txt = f'#{ne["n"]} {strip_no(t)}' if ne.get('n') else strip_no(t)
        rel = 'prev' if label.startswith('←') else 'next'
        return (f'<a href="{sp("/ep/" + ne["s"] + "/")}" rel="{rel}">'
                f'<span class="pn-k">{label}</span><span class="pn-t">{H.escape(txt)}</span></a>')

    prev_e = eps[i - 1] if i > 0 else None
    next_e = eps[i + 1] if i < len(eps) - 1 else None
    prevnext = f'{pn_link(prev_e, "← 上一期")}{pn_link(next_e, "下一期 →")}'

    page = EP_SHELL.format(
        base=BASE, title_tag=H.escape(title_tag), desc=H.escape(desc), url=url,
        og_title=H.escape(og_title), og_img=og_img, site_name=SITE_NAME,
        ldjson=ldjson, css_href=f'{sp("/style.css")}?v={CSS_V}', ep_href=f'{sp("/ep.js")}?v={EP_V}',
        theme_script=THEME_SCRIPT, feed_link=feed_link(), site_footer=site_footer(),
        h1=h1, orig_line=orig_line, kicker=kicker, dek=dek, byline=byline,
        main_cls=' has-toc' if has_zh else '',
        article_meta=(f'<meta property="article:published_time" content="{d}">' if d else '') +
                     (f'<meta property="article:modified_time" content="{zh_mtime}">' if zh_mtime else ''),
        md_link=(f'<link rel="alternate" type="text/markdown" title="中文精读 Markdown" href="{sp("/ep/" + slug + "/index.md")}">' if has_zh else ''),
        head_extra=head_extra(), site_header=site_header(),
        media_html=media_html, tab_buttons=tab_buttons,
        panel_zh=panel_zh, panel_tr=panel_tr, no_tr_note=no_tr_note,
        resources=resources, prevnext=prevnext,
    )
    dest = SITE / 'ep' / slug / 'index.html'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(page)
    md = dest.parent / 'index.md'
    if has_zh:
        head = [f'# {plain}', '', f'> {lede or ""}', '',
                f'- 英文题：{title}', f'- 期数：第 {num} 期' if num else '- 期数：特别篇',
                f'- 日期：{d}' if d else '', f'- 嘉宾：{guest}' if guest else '',
                f'- 来源：{e.get("sourceLabel") or ""}', f'- 网页：{url}',
                f'- 约 {zh_chars} 字（阅读约 {read_min} 分钟）', '',
                '> 时初白精读的评论骨架，依据公开报道，非官方文稿。引用请链到网页版，并以上面的出处为准。', '']
        md.write_text('\n'.join(head) + '\n' + html_to_md(zh_raw))
    elif md.exists():
        md.unlink()


def ssr_card(x):
    zh, en = strip_no(x['zh']) or strip_no(x['t']), strip_no(x['t'])
    num = f'第 {x["n"]} 期' if x['n'] is not None else '特别篇'
    dt = (x['d'] or '')[:7].replace('-', '.')
    tag = '<span class="zh-tag">中文精读</span>' if x.get('r') else ''
    en_html = f'<div class="card-title-en" lang="en">{H.escape(en)}</div>' if x.get('zh') else ''
    return (f'<a class="card" href="{sp("/ep/" + x["s"] + "/")}"><div class="thumb">{thumb_img(x)}</div><div class="card-body">'
            f'<div class="card-kicker"><span class="ep-n">{num}</span><span>{dt}</span>{tag}</div>'
            f'<div class="card-title">{H.escape(zh)}</div>{en_html}</div></a>')


def ssr_hero(x):
    zh, en = strip_no(x['zh']) or strip_no(x['t']), strip_no(x['t'])
    d = x['d'] or ''
    when = fmt_date(d)
    by = ' · '.join(H.escape(v) for v in [x.get('guest'), when, f'第 {x["n"]} 期' if x['n'] is not None else ''] if v)
    desc = f'<p class="hero-desc">{H.escape(x["ds"])}</p>' if x.get('ds') else ''
    href = sp(f'/ep/{x["s"]}/')
    return (f'<a class="hero-media" href="{href}" tabindex="-1" aria-hidden="true">{thumb_img(x, hero=True)}</a>'
            f'<div class="hero-text"><div class="hero-kicker">最新精读</div>'
            f'<h2 class="hero-title"><a href="{href}">{H.escape(zh)}</a></h2>'
            f'<p class="hero-en" lang="en">{H.escape(en)}</p>{desc}<p class="hero-by">{by}</p>'
            f'<a class="hero-cta" href="{href}">阅读全文<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg></a></div>')


def sync_index(eps):
    f = SITE / 'index.html'
    html = f.read_text()
    n_zh = sum(1 for x in eps if x.get('r'))
    since = min((x['d'] for x in eps if x.get('d')), default='')[:4]
    latest = next((x for x in eps if x.get('r')), None)
    sub = f'{len(eps)} 期深度阅读 · {n_zh} 篇中文精读' + (f' · {since} 年至今' if since else '')
    title = f'{SITE_NAME} · 按时间读下去'
    desc = f'{SITE_NAME}：{sub}。{TAGLINE} 不设话题分类。'
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "@id": f'{DOMAIN}/#website', "name": SITE_NAME, "url": absu('/'),
         "description": desc, "inLanguage": "zh-CN", "publisher": {"@id": f'{DOMAIN}/#org'},
         "potentialAction": {"@type": "SearchAction", "target": f'{absu("/")}?q={{search_term_string}}',
                             "query-input": "required name=search_term_string"}},
        {"@type": "Organization", "@id": f'{DOMAIN}/#org', "name": SITE_NAME, "url": absu('/'), "slogan": TAGLINE},
        {"@type": "ItemList", "name": "单集", "itemListOrder": "https://schema.org/ItemListOrderDescending",
         "numberOfItems": len(eps),
         "itemListElement": [{"@type": "ListItem", "position": k + 1, "url": absu(f'/ep/{x["s"]}/'),
                              "name": strip_no(x['zh']) or x['t']} for k, x in enumerate(eps[:30])]},
    ]}
    blocks = {
        'head': f'{THEME_SCRIPT}\n{head_extra()}',
        'ld': '<script type="application/ld+json">' + json.dumps(prune(ld), ensure_ascii=False).replace('<', '\\u003c') + '</script>',
        'sub': sub,
        'hero': ssr_hero(latest) if latest else '',
        'grid': ''.join(ssr_card(x) for x in eps[:30]),
        'footer': site_footer(),
    }
    for k, v in blocks.items():
        html, n = re.subn(
            rf'<!--lex:{k}-->.*?<!--/lex:{k}-->',
            lambda m, v=v, k=k: f'<!--lex:{k}-->{v}<!--/lex:{k}-->',
            html, count=1, flags=re.S)
        if n != 1:
            raise SystemExit(f'index.html missing marker lex:{k}')
    if latest:
        html = re.sub(r'<section class="hero" id="hero"[^>]*>',
                      f'<section class="hero" id="hero" data-s="{latest["s"]}" aria-label="最新精读">', html, count=1)
    html = re.sub(r'(<html\b[^>]*\bdata-base=")[^"]*"', rf'\1{BASE}"', html, count=1)
    html = re.sub(r'<title>[^<]*</title>', f'<title>{H.escape(title)}</title>', html, count=1)
    html = re.sub(r'(<meta name="description" content=")[^"]*"', rf'\1{H.escape(desc)}"', html, count=1)
    html = re.sub(r'(<meta property="og:description" content=")[^"]*"', rf'\1{H.escape(desc)}"', html, count=1)
    html = re.sub(r'(style\.css\?v=)\d+', rf'\g<1>{CSS_V}', html)
    html = re.sub(r'(app\.js\?v=)\d+', rf'\g<1>{APP_V}', html)
    f.write_text(html)
    print('index.html synced')


def page_shell(title, desc, body, path='/', robots='index, follow'):
    url_path = path
    return f"""<!DOCTYPE html>
<html lang="zh-CN" data-base="{BASE}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#ffffff">
<title>{H.escape(title)}</title>
<meta name="description" content="{H.escape(desc)}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{absu(url_path)}">
<meta property="og:title" content="{H.escape(title)}">
<meta property="og:description" content="{H.escape(desc)}">
<meta property="og:site_name" content="{SITE_NAME}">
{THEME_SCRIPT}
{head_extra()}
{feed_link()}
<link rel="stylesheet" href="{sp('/style.css')}?v={CSS_V}">
</head>
<body>
<a class="skip-link" href="#main">跳到主要内容</a>
{site_header()}
{body}
{site_footer()}
<script src="{sp('/app.js')}?v={APP_V}"></script>
</body>
</html>
"""


def build_disclaimer():
    body = f"""
<main class="wrap ep-main" id="main">
  <article class="ep">
    <header class="ep-head"><div class="ep-kicker">关于本站</div><h1 class="ep-title">免责声明与内容说明</h1></header>
    <div class="zh-article disclaimer-body">
      <p>{SITE_NAME}是一个按时间排列的中文精读站。它与访谈嘉宾、主持人、播出平台都没有隶属或合作关系。站点上的话不代表他们的立场。</p>
      <h2>视频与音频</h2>
      <p>本站不保存、不分发访谈视频。个别单集把音频放在站点里，只供这一页收听，不是官方播客，也不代替原片。原片以页面上的来源链接为准。没有音频时不放播放器。</p>
      <h2>中文精读</h2>
      <p>「中文精读」是本站写的评论，依据已经公开的访谈与报道，不是官方文稿，也不是逐字翻译，未经嘉宾或制作方审阅。可能有理解偏差、压缩和遗漏。人名、数字和原话以原访谈为准。稿件若仍标着「骨架」或「待原片核对」，就不要把它当成记录。</p>
      <h2>代码与正文</h2>
      <p>页面壳层的代码来自 <a href="https://github.com/joeseesun/lexfridman-cn" target="_blank" rel="noopener">joeseesun/lexfridman-cn</a>，以 MIT 许可使用，许可只覆盖代码。本站的中文正文不适用该 MIT 许可。转载正文请署名「时初白精读」，并链接到对应页面。</p>
      <h2>联系</h2>
      <p>纠错或权利人要求撤下某页，请在 <a href="https://github.com/ruiyaoe-hash/shichubai-reads" target="_blank" rel="noopener">仓库</a> 开 Issue。确认后会改或撤。</p>
    </div>
  </article>
  <nav class="ep-prevnext"><span></span><a href="{sp('/')}">← 返回全部单集</a></nav>
</main>"""
    out = SITE / 'disclaimer' / 'index.html'
    out.parent.mkdir(exist_ok=True)
    out.write_text(page_shell('免责声明与内容说明 · 时初白精读', '本站不托管访谈视频。个别单集可在页内收听音频，不是官方播客。中文精读是评论，不是官方文稿。', body, path='/disclaimer/'))
    print('disclaimer: ok')


def build_archive(eps):
    years = {}
    for x in eps:
        years.setdefault((x['d'] or '0000')[:4], []).append(x)
    nav = ''.join(f'<a href="#y{y}">{y}</a>' for y in sorted(years, reverse=True) if y != '0000')
    sec = []
    for y in sorted(years, reverse=True):
        rows = []
        for x in years[y]:
            zh = strip_no(x['zh']) or strip_no(x['t'])
            md = (x['d'] or '')[5:10].replace('-', '.')
            tag = '<span class="ar-zh">精读</span>' if x.get('r') else ''
            rows.append(
                f'<li><a href="{sp("/ep/" + x["s"] + "/")}"><span class="ar-n">{x["n"] if x["n"] is not None else "—"}</span>'
                f'<span class="ar-t"><b>{H.escape(zh)}</b><i lang="en">{H.escape(strip_no(x["t"]))}</i></span>'
                f'<span class="ar-d">{md}{tag}</span></a></li>')
        label = '年份未知' if y == '0000' else y
        sec.append(f'<section class="ar-year" id="y{y}"><h2>{label}<small>{len(years[y])} 期</small></h2><ol>{"".join(rows)}</ol></section>')
    title = f'单集目录 · {SITE_NAME}'
    body = f"""<main class="wrap ar-main" id="main">
  <header class="ep-head"><div class="ep-kicker">单集目录</div><h1 class="ep-title">全部 {len(eps)} 期</h1>
    <p class="ep-dek">按时间排列。没有话题分类。标了「精读」的有中文长文。</p></header>
  <nav class="ar-nav" aria-label="按年份跳转">{nav}</nav>
  {''.join(sec)}
</main>"""
    html = page_shell(title, f'{SITE_NAME}全部 {len(eps)} 期，按年份排列。', body, path='/archive/')
    out = SITE / 'archive' / 'index.html'
    out.parent.mkdir(exist_ok=True)
    out.write_text(html)
    print(f'archive: {len(eps)}')


def build_sitemap(eps):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
             f'<url><loc>{absu("/")}</loc><lastmod>{TODAY}</lastmod><priority>1.0</priority></url>',
             f'<url><loc>{absu("/archive/")}</loc><lastmod>{TODAY}</lastmod><priority>0.5</priority></url>',
             f'<url><loc>{absu("/disclaimer/")}</loc><lastmod>{TODAY}</lastmod><priority>0.3</priority></url>']
    for x in eps:
        lines.append(f'<url><loc>{absu("/ep/" + x["s"] + "/")}</loc><lastmod>{x["d"] or TODAY}</lastmod><priority>0.8</priority></url>')
    lines.append('</urlset>')
    (SITE / 'sitemap.xml').write_text('\n'.join(lines) + '\n')
    print(f'sitemap: {len(eps) + 3}')


def build_llms(eps):
    lines = [f'# {SITE_NAME}', '', f'> {TAGLINE}', '',
             '中文精读是评论，不是官方文稿。本站不放访谈视频。个别单集可在网页里收听音频，不是官方播客。',
             f'目录：{absu("/archive/")}', f'RSS：{absu("/feed.xml")}', '']
    for x in eps:
        if x['s'] in ZH:
            t = strip_no(x['zh']) or x['t']
            lines.append(f'- [{t}]({absu("/ep/" + x["s"] + "/index.md")})：{(trans.get(x["s"]) or {}).get("desc", "")}')
    (SITE / 'llms.txt').write_text('\n'.join(lines) + '\n')
    print('llms.txt: ok')


def rfc822(d):
    try:
        dt = datetime.datetime.fromisoformat(d).replace(tzinfo=datetime.timezone.utc)
    except (ValueError, TypeError):
        dt = datetime.datetime.now(datetime.timezone.utc)
    return email.utils.format_datetime(dt)


def build_feed(eps):
    items = []
    ordered = sorted((e for e in eps if e.get('n') is not None), key=lambda e: -e['n'])
    for x in ordered[:20]:
        slug, num = x['s'], x['n']
        title = norm_zh(x['zh'] or x['t'])
        if not str(title).startswith('#'):
            title = f'#{num} {strip_no(title)}'
        url = absu(f'/ep/{slug}/')
        desc = (trans.get(slug) or {}).get('desc') or title
        zh_file = SITE / 'zh' / f'{slug}.html'
        body = ''
        if zh_file.exists():
            body = zh_file.read_text() + f'<hr><p>评论骨架，非官方文稿。网页：<a href="{url}">{url}</a></p>'
        au = audio_for(next(e for e in master if e['slug'] == slug))
        # 页面播放用的访谈音频（含 audio-NNN Release）不写进 RSS enclosure，避免被当成官方播客。
        enc = (f'<enclosure url="{H.escape(au)}" type="audio/mpeg" length="0"/>'
               if au and au.startswith(('http://', 'https://')) and not is_release_audio(au) else '')
        content = f'<content:encoded><![CDATA[{body.replace("]]>", "]]]]><![CDATA[>")}]]></content:encoded>' if body else ''
        items.append(
            f'<item><title>{H.escape(title)}</title><link>{url}</link>'
            f'<guid isPermaLink="true">{url}</guid><pubDate>{rfc822(x["d"])}</pubDate>'
            f'<description><![CDATA[{H.escape(desc)}]]></description>{content}{enc}</item>')
    now = email.utils.format_datetime(datetime.datetime.now(datetime.timezone.utc))
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        f'<channel><title>{SITE_NAME}</title><link>{absu("/")}</link>'
        f'<atom:link href="{absu("/feed.xml")}" rel="self" type="application/rss+xml"/>'
        f'<description>{H.escape(TAGLINE)} 中文精读全文。个别单集可在网页里收听访谈音频，这不是官方播客。</description>'
        f'<language>zh-CN</language><lastBuildDate>{now}</lastBuildDate>'
        '<generator>shichubai-reads build.py</generator>\n'
        + '\n'.join(items) + '\n</channel></rss>\n')
    (SITE / 'feed.xml').write_text(xml)
    print(f'feed: {len(items)}')


def build_special(eps):
    picks = [x for x in eps if x.get('r')][:4]
    links = ''.join(
        f'<li><a href="{sp("/ep/" + x["s"] + "/")}"><b>{H.escape(strip_no(x["zh"]) or x["t"])}</b><i>第 {x["n"]} 期</i></a></li>'
        for x in picks)
    pages = {
        '404.html': ('页面不存在', '这一页没有找到', '链接可能写错了。回到首页，或从最新的精读读起。', True),
        'offline.html': ('离线', '现在没有网络', '读过的文章若已缓存，可以返回继续。联网后会再更新。', False),
    }
    for fn, (kicker, h1, dek, show) in pages.items():
        body = f"""<main class="wrap ep-main special" id="main">
  <header class="ep-head"><div class="ep-kicker">{kicker}</div><h1 class="ep-title">{h1}</h1><p class="ep-dek">{dek}</p>
  <p class="special-actions"><a class="more-btn" href="{sp('/')}">回到首页</a><a class="more-btn ghost" href="{sp('/')}#search">搜索</a></p></header>
  {f'<section class="special-list"><h2>最新精读</h2><ol>{links}</ol></section>' if show else ''}
</main>"""
        html = page_shell(f'{kicker} · {SITE_NAME}', dek, body, path='/', robots='noindex')
        (SITE / fn).write_text(html)
    print('404 / offline: ok')


def build_meta_files():
    (SITE / 'robots.txt').write_text(
        'User-agent: *\nAllow: /\n\n'
        f'Sitemap: {absu("/sitemap.xml")}\n')
    icons = []
    for name, size in (('icon-192.png', '192x192'), ('icon-512.png', '512x512'), ('apple-touch-icon.png', '180x180')):
        if (SITE / name).exists() or name == 'apple-touch-icon.png' and (SITE / 'apple-touch-icon.png').exists():
            icons.append({"src": sp(f'/{name}'), "sizes": size, "type": "image/png"})
    if (SITE / 'icon-512.png').exists():
        icons.append({"src": sp('/icon-512.png'), "sizes": "512x512", "type": "image/png", "purpose": "maskable"})
    manifest = {
        "name": SITE_NAME,
        "short_name": "时初白",
        "description": TAGLINE,
        "lang": "zh-CN",
        "start_url": sp('/') if sp('/') != '' else '/',
        "scope": sp('/') if sp('/').endswith('/') else sp('/') + '/',
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#ffffff",
        "icons": icons or [{"src": sp('/icon.svg'), "sizes": "any", "type": "image/svg+xml"}],
    }
    if manifest['start_url'] == '/shichubai-reads':
        manifest['start_url'] = '/shichubai-reads/'
    (SITE / 'site.webmanifest').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    (SITE / '.nojekyll').write_text('')
    print('robots / manifest: ok')


def clean_stale(eps):
    live = {x['s'] for x in eps}
    epdir = SITE / 'ep'
    if not epdir.exists():
        return
    for d in epdir.iterdir():
        if d.is_dir() and d.name not in live:
            shutil.rmtree(d)
            print('removed stale', d.name)


def assert_site():
    css = (SITE / 'style.css').read_text()
    for needle in (
        'filter: grayscale(1) contrast(1.05)',
        '.card:hover .thumb img, .cont-item:hover .cont-thumb img, .hero:hover .hero-media img { filter: none; }',
        'transform: scale(1.025)',
        'filter .45s ease',
        'filter .5s ease',
    ):
        if needle not in css:
            raise SystemExit('thumbnail hover CSS missing: ' + needle)
    bad = ('umami.qiaomu.ai', 'qiaomu_reward', 'qiaomu_wechat', 'lex.qiaomu.ai', 'vista8', '向阳乔木')
    blobs = []
    for p in SITE.rglob('*'):
        if p.is_file() and p.suffix in {'.html', '.js', '.css', '.xml', '.txt', '.json', '.webmanifest', '.svg'}:
            blobs.append(p.read_text(errors='ignore'))
    blob = '\n'.join(blobs)
    for n in bad:
        if n in blob:
            raise SystemExit('leftover brand string: ' + n)
    if re.search(r'(?:href|src)="/(?:ep/|style\.css|app\.js|ep\.js|feed\.xml|archive/|disclaimer/|data/|sw\.js|audio/|covers/)', blob):
        raise SystemExit('found a site link that is not prefixed for project pages')
    check_feed_audio()
    ep = SITE / 'ep' / '001-jiang-chenglan' / 'index.html'
    text = ep.read_text()
    if 'audio-player' not in text or f'src="{EP001_AUDIO}"' not in text:
        raise SystemExit('episode 001 should play the audio-001 Release asset')
    if '/audio/001-jiang-chenglan.mp3' in text or f'{BASE}/audio/' in text:
        raise SystemExit('episode 001 must not point at a Pages audio path')
    if '访谈音频' not in text or '供本页收听，不是官方播客' not in text:
        raise SystemExit('episode 001 audio note should stay visitor-facing')
    if '合法音频直链' in text:
        raise SystemExit('episode page should not use editor jargon for the audio link')
    if '陈鲁豫的电影沙发' not in text or '创作阶梯计划' not in text:
        raise SystemExit('episode 001 should keep the interview attribution')
    if 'youtube.com/watch?v=NPOOl6g9z6s' not in text:
        raise SystemExit('episode 001 should link to the source interview')
    if 'covers/001-jiang-chenglan.jpg' not in text:
        raise SystemExit('episode 001 cover is not the release still')
    mp3s = [p for p in SITE.rglob('*.mp3') if p.is_file()]
    if mp3s:
        raise SystemExit('mp3 must not live in the site tree: ' + ', '.join(str(p.relative_to(SITE)) for p in mp3s))
    feed_xml = (SITE / 'feed.xml').read_text()
    if '001-jiang-chenglan.mp3' in feed_xml or '<enclosure' in feed_xml:
        raise SystemExit('Release audio must not be an RSS enclosure')
    if 'id="favBtn"' not in text:
        raise SystemExit('episode page is missing the favorite button')
    idx = (SITE / 'index.html').read_text()
    if 'data-f="fav"' not in idx or 'data-f="hist"' not in idx:
        raise SystemExit('home filters are missing history or favorites')
    for name in ('app.js', 'ep.js'):
        src = (SITE / name).read_text()
        if 'scb-fav' not in src:
            raise SystemExit(name + ' is missing the favorites store')
        if 'lex-hist' not in src:
            raise SystemExit(name + ' lost the reading history store')
    print('checks: ok')


def main():
    print(f'DOMAIN={DOMAIN} BASE={BASE or "/"}')
    eps = build_data()
    sync_index(eps)
    for i, _ in enumerate(eps):
        build_page(i, eps)
    build_archive(eps)
    build_disclaimer()
    build_sitemap(eps)
    build_llms(eps)
    build_feed(eps)
    build_special(eps)
    build_meta_files()
    clean_stale(eps)
    assert_site()
    print(f'ep pages: {len(list((SITE / "ep").glob("*/index.html")))}')


if __name__ == '__main__':
    main()

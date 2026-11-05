#!/usr/bin/env python3
"""初白de小岛 · 静态站构建器。

壳层来自 https://github.com/joeseesun/lexfridman-cn （MIT，仅代码）。
只使用 Python 标准库。

输入：
  tools/lex-master.json     单集目录（最新在前）。每期的 officialLinks 是权利人自行
                            发布的官方页面外链；本站不保存、不嵌入任何音视频文件。
  tools/translations.json   中文标题 / 嘉宾 / 简介
  tools/index.template.html 首页模板（site/index.html 由此生成，不要直接改产物）
  site/zh/{slug}.html       中文精读正文片段
  site/data/zh-index.json   已有精读的 slug 列表
  site/covers/              本站自制的文字封面（不得使用节目画面或人物肖像）

输出（发布根目录就是 site/）：
  site/index.html           由模板注入头条、卡片、页脚及站点绝对路径
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

class U8Path(type(Path())):
    """全站文件读写固定 UTF-8，不依赖运行主机的 locale。

    中文 Windows 默认编码是 cp936；直接用 Path.read_text/write_text 读带中文的
    JSON 会抛 UnicodeDecodeError。派生路径（/ 、parent、rglob）保持本子类，
    因此一处定义即全站生效。
    """
    def read_text(self, *a, **kw):
        kw.setdefault('encoding', 'utf-8')
        return super().read_text(*a, **kw)

    def write_text(self, *a, **kw):
        kw.setdefault('encoding', 'utf-8')
        return super().write_text(*a, **kw)


ROOT = U8Path(__file__).resolve().parent
SITE = ROOT.parent / 'site'
DOMAIN = os.environ.get('SITE_DOMAIN', 'https://ruiyaoe-hash.github.io/shichubai-reads').rstrip('/')
BASE = os.environ.get('BASE_PATH', urlparse(DOMAIN).path).rstrip('/')
TODAY = datetime.date.today().isoformat()
CSS_V, APP_V, EP_V = 3, 3, 3
SITE_NAME = '初白de小岛'
SITE_SUB = '中文精读 · 按时间往下读'
IP_NAME = '时初白'
TAGLINE = '在你想放弃时，把火递回来。'

CN_DIGITS = '零壹贰叁肆伍陆柒捌玖'


def cn_num(n):
    """全站统一的期号字形：1→壹、2→贰…99→玖拾玖。"""
    if not isinstance(n, int) or not 1 <= n <= 99:
        return str(n) if n is not None else ''
    if n < 10:
        return CN_DIGITS[n]
    tens, ones = divmod(n, 10)
    head = (CN_DIGITS[tens] + '拾') if tens > 1 else '拾'
    return head + (CN_DIGITS[ones] if ones else '')


def ep_label(n):
    """展示用期号：第壹期 / 第贰期；无编号时为特别篇。"""
    return f'第{cn_num(n)}期' if isinstance(n, int) and n > 0 else '特别篇'


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
    '<button class="theme-toggle" type="button" data-theme-toggle aria-label="切换日读 / 夜读" title="切换日读 / 夜读">'
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
  var BG = { light: '#FBF7F0', sepia: '#FBF7F0', dark: '#24201B' };
  // 暖纸白是默认外观；夜读由读者主动选择，不跟随系统深色偏好。
  if (t !== 'light' && t !== 'dark') t = 'light';
  d.setAttribute('data-theme', t);
  // 只保留两款字体，思源宋体已在 head 加载，这里按需补黑体。
  var FONTS = { sans: 'https://fonts.googleapis.cn/css2?family=Noto+Sans+SC:wght@400;600&display=swap' };
  window.__lexFonts = FONTS;
  window.__lexLoadFont = function (k) {
    if (!FONTS[k] || document.getElementById('lexfont-' + k)) return;
    var l = document.createElement('link'); l.rel = 'stylesheet'; l.href = FONTS[k]; l.id = 'lexfont-' + k;
    document.head.appendChild(l);
  };
  if (f !== 'serif' && f !== 'sans' && f !== 'sys') f = 'serif';
  d.setAttribute('data-font', f);
  if (FONTS[f]) window.__lexLoadFont(f);
  if (z && /^(1[5-9]|2[0-2])$/.test(z)) d.style.setProperty('--read-size', z + 'px');
  if (lh && /^(1\\.\\d+|2(\\.\\d+)?)$/.test(lh)) d.style.setProperty('--read-lh', lh);
  if (w && /^\\d{3}$/.test(w)) d.style.setProperty('--measure', w + 'px');
  var meta = document.querySelector('meta[name="theme-color"]');
  function syncMeta() { if (meta) meta.content = BG[t]; }
  syncMeta();
  window.__lexSetTheme = function (n) {
    if (n !== 'light' && n !== 'dark') return;
    t = n;
    try { localStorage.setItem('lex-theme', t); } catch (e) {}
    d.classList.add('theme-anim');
    d.setAttribute('data-theme', t);
    syncMeta();
    setTimeout(function () { d.classList.remove('theme-anim'); }, 320);
    document.dispatchEvent(new CustomEvent('lex-theme', { detail: t }));
  };
  window.__lexThemeToggle = function () { window.__lexSetTheme(t === 'dark' ? 'light' : 'dark'); };
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
        '<link rel="stylesheet" href="https://fonts.googleapis.cn/css2?family=Noto+Serif+SC:wght@400;600;700&display=swap">\n'
        f'<link rel="icon" href="{sp("/favicon.ico")}" sizes="32x32">'
        f'<link rel="icon" href="{sp("/icon.svg")}" type="image/svg+xml">'
        f'<link rel="apple-touch-icon" href="{sp("/apple-touch-icon.png")}">'
        f'<link rel="manifest" href="{sp("/site.webmanifest")}">\n'
        f'<meta name="apple-mobile-web-app-title" content="{SITE_NAME}">'
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
        f'    <a class="wordmark" href="{home}" aria-label="{SITE_NAME} · 首页">初白<span class="brand-de">de</span>小岛</a>\n'
        f'    <div class="header-actions">{THEME_BTN}</div>\n'
        '  </div>\n</header>'
    )


def site_footer():
    home = sp('/')
    return f"""<footer class="site-footer">
  <div class="wrap">
    <div class="ft-top">
      <a class="ft-mark" href="{home}">初白<span class="brand-de">de</span>小岛</a>
      <p class="ft-tag">{TAGLINE}</p>
    </div>
    <div class="ft-cols">
      <nav class="ft-col" aria-label="浏览"><div class="ft-h">浏览</div>
        <a href="{home}">全部单集</a><a href="{sp('/archive/')}">单集目录</a></nav>
      <nav class="ft-col" aria-label="订阅"><div class="ft-h">订阅</div>
        <a href="{sp('/feed.xml')}">RSS 订阅</a></nav>
      <nav class="ft-col" aria-label="关于"><div class="ft-h">关于</div>
        <a href="{sp('/disclaimer/')}">版权与说明</a></nav>
    </div>
    <div class="ft-bottom">
      <span>© 2026 {SITE_NAME} · {IP_NAME}</span>
      <span>本站不托管访谈音视频；中文内容依据已公开材料整理与评述，完整内容请以各期官方渠道为准。</span>
    </div>
  </div>
</footer>"""


def colophon():
    """改版后不再在正文末尾放抒情块，动作入口统一收进页脚。"""
    return ''


EP_SHELL = """<!DOCTYPE html>
<html lang="zh-CN" data-base="{base}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#FBF7F0">
<title>{title_tag}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{og_img}">
<meta property="og:image:type" content="{og_type}">
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

def load_json(name):
    return json.loads((ROOT / name).read_text())


master = load_json('lex-master.json')
trans = load_json('translations.json') if (ROOT / 'translations.json').exists() else {}
zh_index = json.loads((SITE / 'data' / 'zh-index.json').read_text())
ZH = set(zh_index.get('slugs', []))


def official_links(e):
    """权利人自行发布的官方页面外链。本站永不托管音视频文件。"""
    out = []
    for lk in e.get('officialLinks') or []:
        url = (lk.get('url') or '').strip()
        if not url.startswith('https://'):
            raise SystemExit(f'officialLinks must use https absolute URLs: {url!r}')
        out.append({
            'label': lk.get('label') or url,
            'url': url,
            'kind': lk.get('kind') or 'official',
            'note': lk.get('note') or '',
        })
    return out


def absolutize(html):
    """RSS 全文里的站内相对链接改成绝对地址，避免聚合器解析到自己的域名。"""
    return (html.replace('href="/', f'href="{DOMAIN}/')
                .replace('src="/', f'src="{DOMAIN}/'))


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
            'tr': tag, 'ln': len(official_links(e)),
            'r': 1 if e['slug'] in ZH and (SITE / 'zh' / f"{e['slug']}.html").exists() else 0,
            'ds': info.get('desc'),
        })
    out = {'updated': TODAY, 'episodes': eps}
    (SITE / 'data').mkdir(exist_ok=True)
    (SITE / 'data' / 'episodes.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')))
    print(f"episodes.json: {len(eps)} eps, zh={sum(1 for x in eps if x['r'])}, links={sum(x['ln'] for x in eps)}")
    return eps


def prune(o):
    if isinstance(o, dict):
        return {k: prune(v) for k, v in o.items() if v not in (None, '', [], {})}
    if isinstance(o, list):
        return [prune(v) for v in o]
    return o


def table_to_md(m):
    # 正文里的术语表转成 Markdown 表格，供 index.md 与 llms 使用。
    rows = re.findall(r'<tr>(.*?)</tr>', m.group(1), flags=re.S)
    out = []
    for i, row in enumerate(rows):
        cells = [re.sub(r'<[^>]+>', '', c).strip().replace('|', r'\|')
                 for c in re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row, flags=re.S)]
        out.append('| ' + ' | '.join(cells) + ' |')
        if i == 0:
            out.append('|' + '---|' * len(cells))
    return '\n\n' + '\n'.join(out) + '\n\n'


def html_to_md(h):
    h = re.sub(r'\s*<h2[^>]*>(.*?)</h2>\s*', lambda m: f'\n\n## {m.group(1)}\n\n', h, flags=re.S)
    h = re.sub(r'\s*<h3[^>]*>(.*?)</h3>\s*', lambda m: f'\n\n### {m.group(1)}\n\n', h, flags=re.S)
    h = re.sub(r'\s*<h4[^>]*>(.*?)</h4>\s*', lambda m: f'\n\n#### {m.group(1)}\n\n', h, flags=re.S)
    h = re.sub(r'\s*<h5[^>]*>(.*?)</h5>\s*', lambda m: f'\n\n##### {m.group(1)}\n\n', h, flags=re.S)
    h = re.sub(r'\s*<blockquote>(.*?)</blockquote>\s*',
               lambda m: '\n\n' + '\n'.join('> ' + ln for ln in re.sub(r'</?p>', '\n', m.group(1)).strip().splitlines() if ln.strip()) + '\n\n',
               h, flags=re.S)
    h = re.sub(r'\s*<li>(.*?)</li>\s*', lambda m: f'\n- {m.group(1).strip()}', h, flags=re.S)
    h = re.sub(r'</?(ul|ol)>', '\n', h)
    h = re.sub(r'<(strong|b)>(.*?)</\1>', r'**\2**', h, flags=re.S)
    h = re.sub(r'<(em|i)>(.*?)</\1>', r'*\2*', h, flags=re.S)
    h = re.sub(r'<div class="tbl-wrap"><table>(.*?)</table></div>', table_to_md, h, flags=re.S)
    h = re.sub(r'<code>(.*?)</code>', r'`\1`', h, flags=re.S)
    h = re.sub(r'<hr\s*/?>', '\n\n---\n\n', h)
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
        light = H.escape(sp(x['cv']))
        dark_path = x['cv'].replace('.svg', '-dark.svg')
        # 没有夜读版时退回日读版，至少不会缺图。
        dark_src = dark_path if (SITE / dark_path.lstrip('/')).exists() else x['cv']
        dark = H.escape(sp(dark_src))
        lazy = '' if hero else ' loading="lazy" decoding="async"'
        dims = '' if hero else ' width="320" height="180"'
        return (f'<img class="cv-light"{lazy} src="{light}" alt=""{dims}>'
                f'<img class="cv-dark"{lazy} src="{dark}" alt=""{dims}>')
    if hero:
        return ''
    label = f'{x["n"]:03d}' if isinstance(x.get('n'), int) else '时'
    return f'<div class="no-img">{label}</div>'


def build_page(i, eps):
    e = master[i]
    slug, num, title = e['slug'], e.get('num'), e['title']
    d = e.get('date') or ''
    y = e.get('ytId') or None
    links = official_links(e)
    info = trans.get(slug, {})
    zh_title = norm_zh(info.get('zh'))
    guest, lede = info.get('guest'), info.get('desc')
    zh_file = SITE / 'zh' / f'{slug}.html'
    has_zh = slug in ZH and zh_file.exists()
    tr_tag, tr_text = text_for(slug)
    x = eps[i]
    url = absu(f'/ep/{slug}/')
    plain = strip_no(zh_title) or strip_no(title) or title
    title_tag = f'{plain} | {SITE_NAME}' + (f' · {ep_label(num)}' if num else '')
    desc = lede or f'{guest or SITE_NAME}：{plain}'
    og_title = plain
    og_img = absu(x['cv']) if x.get('cv') else absu('/icon-512.png')

    zh_raw = zh_file.read_text() if has_zh else ''
    zh_chars = len(re.sub(r'\s+', '', H.unescape(re.sub(r'<[^>]+>', '', zh_raw))))
    read_min = max(1, round(zh_chars / 450)) if zh_chars else 0
    # 修改时间来自数据，不取文件 mtime：CI 每次 checkout 都会把它重置成构建当天。
    updated = e.get('updated') or d or None
    zh_sections = [H.unescape(re.sub(r'<[^>]+>', '', s)).strip() for s in re.findall(r'<h2[^>]*>(.*?)</h2>', zh_raw)]

    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "Article", "@id": f'{url}#article', "headline": plain[:110],
         "alternativeHeadline": title, "description": lede,
         "inLanguage": "zh-CN", "datePublished": d or None, "dateModified": updated,
         "wordCount": zh_chars or None, "timeRequired": f'PT{read_min}M' if read_min else None,
         "image": og_img, "articleSection": zh_sections[:12] or None,
         "isAccessibleForFree": True, "mainEntityOfPage": url,
         "author": {"@type": "Organization", "name": SITE_NAME, "url": absu('/')},
         "publisher": {"@id": f'{DOMAIN}/#org'},
         "isBasedOn": {"@type": "Conversation", "name": e.get('sourceLabel') or plain,
                       "url": e.get('sourceUrl') or None,
                       "creator": {"@type": "Organization", "name": e.get('rightsHolder') or '未标注'},
                       "description": "已公开的内容。本页只做中文整理与外链，不复制、不嵌入、不托管音视频。"}},
        {"@type": "Organization", "@id": f'{DOMAIN}/#org', "name": SITE_NAME, "url": absu('/'),
         "slogan": TAGLINE},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": absu('/')},
            {"@type": "ListItem", "position": 2, "name": plain, "item": url}]},
    ]}
    ldjson = json.dumps(prune(ld), ensure_ascii=False).replace('<', '\\u003c')

    h1 = H.escape(plain)
    orig_line = f'<p class="ep-title-en" lang="en">{H.escape(strip_no(title))}</p>' if zh_title else ''
    kicker_bits = [ep_label(num)]
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

    primary = next((lk for lk in links if lk['kind'] == 'primary'), links[0] if links else None)
    if primary:
        media_html = (
            '<p class="ep-source"><a href="' + H.escape(primary['url']) + '" '
            'target="_blank" rel="noopener noreferrer">去官方看完整内容 <span aria-hidden="true">↗</span></a>'
            '<span class="ep-source-note">原片在发布方平台，本站不托管</span></p>')
    else:
        media_html = ''

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
            f'<div class="zh-article">{zh_raw}</div></div>')
    panel_tr = ''
    if tr_tag:
        panel_tr = (f'<div class="tab-panel" id="panel-tr" data-panel="tr">'
                    f'<div class="tr-note">本地文字记录，仅在仓库提供纯文本时出现。</div>'
                    f'<div class="transcript-text">{H.escape(tr_text)}</div></div>')
    no_tr_note = '' if (has_zh or tr_tag) else '<div class="ep-notice">这篇还没有正文。</div>'

    res = ['<section class="ep-resources"><div class="res-h">本集资源与出处</div><ul>']
    res.append(f'<li><span class="res-k">嘉宾</span>{H.escape(guest or "—")}</li>')
    res.append(f'<li><span class="res-k">来源</span>{H.escape(e.get("sourceLabel") or "公开访谈")}'
               f'<span class="res-sub">发布日 {H.escape(d) or "待核"}</span></li>')
    if e.get('sourceUrl'):
        res.append(f'<li><span class="res-k">原片</span><a href="{H.escape(e["sourceUrl"])}" target="_blank" rel="noopener noreferrer">官方发布渠道</a></li>')
    for lk in links:
        if lk['kind'] != 'primary':
            res.append(f'<li><span class="res-k">官方</span><a href="{H.escape(lk["url"])}" target="_blank" rel="noopener noreferrer">{H.escape(lk["label"])}</a></li>')
    for rep_ in e.get('reports') or []:
        if rep_.get('url'):
            res.append(f'<li><span class="res-k">报道</span><a href="{H.escape(rep_["url"])}" target="_blank" rel="noopener noreferrer">{H.escape(rep_.get("label") or rep_["url"])}</a></li>')
    res.append('</ul><p class="res-note">本站内容依据已公开材料整理与评述，不是官方文稿、不是逐字稿，也未经讲者或发布方审阅。'
               f'<a href="{sp("/disclaimer/")}">版权与说明</a></p></section>')
    resources = ''.join(res)

    def pn_link(ne, label):
        if not ne:
            return '<span></span>'
        t = ne['zh'] or ne['t']
        txt = f'{cn_num(ne["n"])} · {strip_no(t)}' if ne.get('n') else strip_no(t)
        rel = 'prev' if label.startswith('←') else 'next'
        return (f'<a href="{sp("/ep/" + ne["s"] + "/")}" rel="{rel}">'
                f'<span class="pn-k">{label}</span><span class="pn-t">{H.escape(txt)}</span></a>')

    prev_e = eps[i - 1] if i > 0 else None
    next_e = eps[i + 1] if i < len(eps) - 1 else None
    prevnext = f'{pn_link(prev_e, "← 上一期")}{pn_link(next_e, "下一期 →")}'

    page = EP_SHELL.format(
        base=BASE, title_tag=H.escape(title_tag), desc=H.escape(desc), url=url,
        og_title=H.escape(og_title), og_img=og_img,
        og_type='image/svg+xml' if str(og_img).endswith('.svg') else 'image/png', site_name=SITE_NAME,
        ldjson=ldjson, css_href=f'{sp("/style.css")}?v={CSS_V}', ep_href=f'{sp("/ep.js")}?v={EP_V}',
        theme_script=THEME_SCRIPT, feed_link=feed_link(), site_footer=site_footer(),
        h1=h1, orig_line=orig_line, kicker=kicker, dek=dek, byline=byline,
        main_cls=' has-toc' if has_zh else '',
        article_meta=(f'<meta property="article:published_time" content="{d}">' if d else '') +
                     (f'<meta property="article:modified_time" content="{updated}">' if updated else ''),
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
                f'- 英文题：{title}', f'- 期数：{ep_label(num)}',
                f'- 日期：{d}' if d else '', f'- 嘉宾：{guest}' if guest else '',
                f'- 来源：{e.get("sourceLabel") or ""}', f'- 网页：{url}',
                f'- 约 {zh_chars} 字（阅读约 {read_min} 分钟）', '',
                f'> {SITE_NAME} 的中文整理与评述，依据已公开材料写成，非官方授权文稿；原话与完整语境以官方渠道为准。引用请链到网页版。', '']
        md.write_text('\n'.join(head) + '\n' + html_to_md(zh_raw))
    elif md.exists():
        md.unlink()


def ssr_card(x):
    zh, en = strip_no(x['zh']) or strip_no(x['t']), strip_no(x['t'])
    num = ep_label(x['n'])
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
    by = ' · '.join(H.escape(v) for v in [x.get('guest'), when, ep_label(x['n']) if x['n'] is not None else ''] if v)
    desc = f'<p class="hero-desc">{H.escape(x["ds"])}</p>' if x.get('ds') else ''
    href = sp(f'/ep/{x["s"]}/')
    return (f'<a class="hero-media" href="{href}" tabindex="-1" aria-hidden="true">{thumb_img(x, hero=True)}</a>'
            f'<div class="hero-text"><div class="hero-kicker">最新精读</div>'
            f'<h2 class="hero-title"><a href="{href}">{H.escape(zh)}</a></h2>'
            f'<p class="hero-en" lang="en">{H.escape(en)}</p>{desc}<p class="hero-by">{by}</p>'
            f'<a class="hero-cta" href="{href}">阅读全文<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg></a></div>')


def sync_index(eps):
    # 源模板与产物分离：每次都从模板读，产物只写不读。
    # 切换 BASE / DOMAIN 后仍可幂等重建，也不会让 index.html 越改越脏。
    tpl = ROOT / 'index.template.html'
    f = SITE / 'index.html'
    html = tpl.read_text() if tpl.exists() else f.read_text()
    latest = next((x for x in eps if x.get('r')), None)
    sub = SITE_SUB
    title = f'{SITE_NAME} · 按时间读下去'
    desc = f'{SITE_NAME} · {SITE_SUB}。按时间排列的中文精读。'
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
    # 方案 B：hero 是「最新精读」门面，网格从第二期开始排，消除上下重复。
    # 单期时网格本就隐藏，这里保持同样条件以免 SSR 与运行时不一致。
    grid_eps = [x for x in eps[:30]
                if not (len(eps) > 1 and latest and x['s'] == latest['s'])]
    blocks = {
        'head': f'{THEME_SCRIPT}\n{head_extra()}',
        'ld': '<script type="application/ld+json">' + json.dumps(prune(ld), ensure_ascii=False).replace('<', '\\u003c') + '</script>',
        'sub': sub,
        'hero': ssr_hero(latest) if latest else '',
        'grid': ''.join(ssr_card(x) for x in grid_eps),
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
    og = absu(latest['cv']) if latest and latest.get('cv') else absu('/icon-512.png')
    html = re.sub(r'(<meta property="og:image" content=")[^"]*"', rf'\1{H.escape(og)}"', html, count=1)
    html = re.sub(r'(<meta property="og:image:type" content=")[^"]*"',
                  rf'\1{"image/svg+xml" if og.endswith(".svg") else "image/png"}"', html, count=1)
    html = re.sub(r'(style\.css\?v=)\d+', rf'\g<1>{CSS_V}', html)
    html = re.sub(r'(app\.js\?v=)\d+', rf'\g<1>{APP_V}', html)
    # 只有 1 期时，检索工具与重复卡片列表都不出现，首屏只留一篇精读。
    if len(eps) <= 1:
        html = html.replace('<div class="toolbar">', '<div class="toolbar" hidden>', 1)
        html = html.replace('<div id="grid" class="grid">', '<div id="grid" class="grid" hidden>', 1)
        html = html.replace('<div class="result-line" id="resultLine" aria-live="polite">',
                            '<div class="result-line" id="resultLine" aria-live="polite" hidden>', 1)
        html = html.replace('<div id="sentinel" class="sentinel">',
                            '<div id="sentinel" class="sentinel" hidden>', 1)
    html = html.replace('{{DOMAIN}}', DOMAIN).replace('{{BASE}}', BASE)
    if '{{' in html:
        raise SystemExit('index template still has unresolved placeholders')
    f.write_text(html)
    print('index.html synced')


def page_shell(title, desc, body, path='/', robots='index, follow', canonical=True):
    canonical_tag = f'<link rel="canonical" href="{absu(path)}">' if canonical else ''
    return f"""<!DOCTYPE html>
<html lang="zh-CN" data-base="{BASE}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#FBF7F0">
<title>{H.escape(title)}</title>
<meta name="description" content="{H.escape(desc)}">
<meta name="robots" content="{robots}">
{canonical_tag}
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
    <header class="ep-head"><div class="ep-kicker">关于本站</div><h1 class="ep-title">版权、来源与内容说明</h1></header>
    <div class="zh-article disclaimer-body">
      <p>{SITE_NAME}是一个按时间排列的中文精读站，与访谈嘉宾、主持人、制作方、播出平台均无隶属、授权或合作关系。本站不是官方站点，也不代表他们的立场。</p>

      <h2>一、不托管音视频</h2>
      <p>本站不保存、不复制、不上传、不内嵌、不分发任何访谈视频或音频文件：仓库、Pages 站点与 RSS 中都没有原片文件，也没有指向原片文件的直链。各期只提供<strong>指向权利人自行发布页面</strong>的普通外链（平台内的官方入口、主办方公开发布的图文）。内容的访问、播放与数据都发生在原平台。</p>
      <p>第壹期的权利人是抖音精选「创作阶梯计划」、@陈鲁豫 与 @姜乘澜。嘉宾官方主页明确标注「全网同名，只此一号，没有小号。暂未授权切片。」在权利人未开放音频直链或官方嵌入、且已明确表示未授权切片的情形下，本站不提供站内播放器，也不以任何形式转载原片。早期版本曾把整段访谈音频上传到 Release 并在页内播放，该做法已撤销。</p>
      <p>第贰期的原视频由 Lauren（X：@poteto）本人于 X 公开发布，约 38 分钟。本站只提供指向该公开帖文的普通外链，不保存、不转存视频文件。该期正文末尾附注提到的英文 ASR 原文另存文件<strong>不在本仓库、也不随站点发布</strong>，站内没有任何逐字稿文件。</p>

      <h2>二、外链的边界</h2>
      <p>外链只是索引，不等于获得授权，也不把第三方内容变成本站内容。本站不绕过平台的登录、付费或地域限制，不抓取、不缓存、不改写被链页面，不使用对方的名称、标识或节目包装来暗示合作。被链页面若下线或变更，本站不承担其内容可用性，也不对其中的广告、评论或信息收集负责。</p>

      <h2>三、中文内容的性质</h2>
      <p>「中文精读」是本站在已公开内容基础上做的中文整理与评述，不是官方文稿，不是逐字稿，也未经讲者、嘉宾或制作方审阅。各期写法并不相同：第壹期依据公开访谈及主办方、媒体的公开报道写成，以介绍与评述为主；第贰期是通读公开视频分享后重新组织结构的中文整理译文，尽量保留讲者实际说出的内容、案例、工具名称、技术细节与关键数据，并附术语表。</p>
      <p>第贰期的篇幅与还原度都高于评论体，接近整场分享的中文呈现，本站<strong>未取得复制、翻译、改编或传播授权</strong>。这是站点所有者在知悉上述边界后作出的选择，并如实记录于此：读者若需要原话、语气与完整语境，请以官方渠道的原视频为准；本站不以任何形态替代原作，也不把转述补写成当事人原话。人名、数字、时间一律以原发布内容为准，可能存在理解偏差、压缩与遗漏。</p>

      <h2>四、封面、姓名与商标</h2>
      <p>封面为本站自制的文字与几何排版，不使用节目画面、视频帧、剧照、嘉宾肖像或平台标识。两期共用同一版式骨架，期号以汉字数字「壹 / 贰」呈现，与站内「第壹期 / 第贰期」一致。文中出现的姓名、账号名、节目与计划名称仅用于指明整理对象与出处，属描述性使用，不构成商业背书，也不主张任何权利。相关商标、肖像、录音录像制品与节目包装的权利归各自权利人所有。</p>

      <h2>五、代码与正文的许可</h2>
      <p>页面壳层代码来自 <a href="https://github.com/joeseesun/lexfridman-cn" target="_blank" rel="noopener noreferrer">joeseesun/lexfridman-cn</a>，以 MIT 许可使用，许可只覆盖代码；LICENSE 中的版权声明按 MIT 要求原样保留。本站中文正文不适用该 MIT 许可，除依法属于合理使用的情形外保留所有权利。转载或引用请署名「{SITE_NAME}」并链接到对应页面，且不得删改本说明。</p>

      <h2>六、更正与下架</h2>
      <p>权利人、嘉宾或其代理如认为某处引用、封面或链接不当，或希望撤下某一页，请在 <a href="https://github.com/ruiyaoe-hash/shichubai-reads/issues" target="_blank" rel="noopener noreferrer">仓库开 Issue</a>，说明具体页面与理由。核实后本站会更正、补充出处或删除该页及其构建产物，不要求对方先行提供争议证明。事实性错误同样欢迎指出。</p>
      <p>第贰期因采用整理译文形态、还原度高于评论体，如讲者、其代理或发布平台提出异议，本站将直接撤下该页及其构建产物（页面、Markdown、RSS 条目、站点地图与目录），不以声明替代处理。</p>

    </div>
  </article>
  <nav class="ep-prevnext"><span></span><a href="{sp('/')}">← 返回全部单集</a></nav>
</main>"""
    out = SITE / 'disclaimer' / 'index.html'
    out.parent.mkdir(exist_ok=True)
    out.write_text(page_shell(
        f'版权、来源与内容说明 · {SITE_NAME}',
        '非官方中文精读站。不保存、不嵌入、不分发访谈音视频，只提供权利人自行发布页面的外链；中文内容不是官方文稿或逐字稿。',
        body, path='/disclaimer/'))
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
                f'<li><a href="{sp("/ep/" + x["s"] + "/")}"><span class="ar-n">{cn_num(x["n"]) if x["n"] is not None else "—"}</span>'
                f'<span class="ar-t"><b>{H.escape(zh)}</b><i lang="en">{H.escape(strip_no(x["t"]))}</i></span>'
                f'<span class="ar-d">{md}{tag}</span></a></li>')
        label = '年份未知' if y == '0000' else y
        sec.append(f'<section class="ar-year" id="y{y}"><h2>{label}<small>{len(years[y])} 期</small></h2><ol>{"".join(rows)}</ol></section>')
    title = f'单集目录 · {SITE_NAME}'
    body = f"""<main class="wrap ar-main" id="main">
  <header class="ep-head"><div class="ep-kicker">单集目录</div><h1 class="ep-title">全部 {len(eps)} 期</h1>
    <p class="ep-dek">按时间从新到旧排列。</p></header>
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
             '中文内容依据已公开材料整理与评述，不是官方文稿或逐字稿。本站不托管音视频，只提供官方页面外链。',
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
        return None
    return email.utils.format_datetime(dt)


def cdata(text):
    return (text or '').replace(']]>', ']]]]><![CDATA[>')


def build_feed(eps):
    items = []
    ordered = sorted((e for e in eps if e.get('n') is not None), key=lambda e: -e['n'])
    for x in ordered[:20]:
        slug, num = x['s'], x['n']
        title = norm_zh(x['zh'] or x['t'])
        if not str(title).startswith('#'):
            title = f'#{cn_num(num)} {strip_no(title)}'
        url = absu(f'/ep/{slug}/')
        desc = (trans.get(slug) or {}).get('desc') or title
        zh_file = SITE / 'zh' / f'{slug}.html'
        body = ''
        if zh_file.exists():
            body = absolutize(zh_file.read_text()) + (
                f'<hr><p>本文由{SITE_NAME}依据已公开材料整理，不是官方文稿或逐字稿，也未经讲者或发布方审阅。'
                f'完整内容请到<a href="{url}">原文所列官方渠道</a>观看；本站不托管音视频。</p>')
        pub = rfc822(x['d'])
        pub_tag = f'<pubDate>{pub}</pubDate>' if pub else ''
        content = f'<content:encoded><![CDATA[{cdata(body)}]]></content:encoded>' if body else ''
        items.append(
            f'<item><title>{H.escape(title)}</title><link>{H.escape(url)}</link>'
            f'<guid isPermaLink="true">{H.escape(url)}</guid>{pub_tag}'
            f'<description><![CDATA[{cdata(desc)}]]></description>{content}</item>')
    # 用最新一期的发布时间，而不是构建时刻：内容没变时 RSS 字节级不变，
    # 聚合器也不会把每次部署误判成内容更新。
    latest_date = max((x['d'] for x in eps if x.get('d')), default=TODAY)
    last_build = rfc822(latest_date) or email.utils.format_datetime(
        datetime.datetime.fromisoformat(TODAY).replace(tzinfo=datetime.timezone.utc))
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        f'<channel><title>{SITE_NAME}</title><link>{absu("/")}</link>'
        f'<atom:link href="{absu("/feed.xml")}" rel="self" type="application/rss+xml"/>'
        f'<description>{H.escape(SITE_NAME)} · 中文精读全文。本站不托管访谈音视频。</description>'
        f'<language>zh-CN</language><lastBuildDate>{last_build}</lastBuildDate>'
        '<generator>shichubai-reads build.py</generator>\n'
        + '\n'.join(items) + '\n</channel></rss>\n')
    (SITE / 'feed.xml').write_text(xml)
    print(f'feed: {len(items)}')


def build_special(eps):
    picks = [x for x in eps if x.get('r')][:4]
    links = ''.join(
        f'<li><a href="{sp("/ep/" + x["s"] + "/")}"><b>{H.escape(strip_no(x["zh"]) or x["t"])}</b><i>{ep_label(x["n"])}</i></a></li>'
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
        html = page_shell(f'{kicker} · {SITE_NAME}', dek, body, path='/', robots='noindex, noarchive', canonical=False)
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
        "short_name": "初白岛",
        "description": SITE_SUB,
        "lang": "zh-CN",
        "start_url": sp('/') if sp('/') != '' else '/',
        "scope": sp('/') if sp('/').endswith('/') else sp('/') + '/',
        "display": "standalone",
        "background_color": "#FBF7F0",
        "theme_color": "#FBF7F0",
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
    """只校验结构不变量。

    内容级检查属于审阅流程，不能放进构建器：否则改一处来源说法、换一张封面，
    整站就发不出去。旧的 assert 把第 001 期的音频 URL、来源措辞、封面名和
    上游品牌黑名单写死在构建里，已移除。
    """
    css = (SITE / 'style.css').read_text()
    for needle in (
        '--bg: #FBF7F0',
        '--clay: #A9684B',
        '.ip-seal',
        '@keyframes breathe',
    ):
        if needle not in css:
            raise SystemExit('thumbnail hover CSS missing: ' + needle)

    blobs = []
    for q in SITE.rglob('*'):
        if q.is_file() and q.suffix in {'.html', '.js', '.css', '.xml', '.txt', '.json', '.webmanifest', '.svg'}:
            blobs.append(q.read_text(errors='ignore'))
    blob = '\n'.join(blobs)

    # 项目页构建必须带前缀；域名根构建则不能残留旧前缀。
    if BASE:
        if re.search(r'(?:href|src)="/(?:ep/|style\.css|app\.js|ep\.js|feed\.xml|archive/|disclaimer/|data/|sw\.js|covers/)', blob):
            raise SystemExit('found a site link that is not prefixed for project pages')
    elif re.search(r'(?:href|src|content)="/shichubai-reads/', blob):
        # 只查站内属性路径。仓库外链 URL 和代码注释里出现这个字符串是正常的。
        raise SystemExit('custom-domain build still contains the project-page prefix')

    for token in ('releases/download/audio-', '<audio', '<enclosure', '.mp3', 'audio-001'):
        if token in blob:
            raise SystemExit('site must not host or link interview media files: ' + token)
    if [q for q in SITE.rglob('*.mp3') if q.is_file()]:
        raise SystemExit('mp3 must not live in the site tree')

    for e in master:
        ep = SITE / 'ep' / e['slug'] / 'index.html'
        if not ep.exists():
            raise SystemExit('missing episode page: ' + e['slug'])
        text = ep.read_text()
        lks = official_links(e)
        if lks and 'ep-source' not in text:
            raise SystemExit('official source link missing: ' + e['slug'])
        for lk in lks:
            # 页面里对 & 做了 HTML 转义，两种形式都算命中。
            if lk['url'] not in text and H.escape(lk['url']) not in text:
                raise SystemExit('official link missing from episode page: ' + lk['url'])
    for name in ('app.js', 'ep.js'):
        if 'scb-fav' not in (SITE / name).read_text():
            raise SystemExit(name + ' is missing the favorites store')
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

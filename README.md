# 时初白精读

按时间往下排的中文精读。白纸、墨字、一条细线。唯一的红色留给「中文精读」。

> 在你想放弃时，把火递回来。

不设话题分类，也不做情绪入口。首页就是检索、按时间排列的全部单集，以及中文精读。看过和收藏只在这台浏览器里有记录时才出现。一期一张卡片。

计划中的地址：[https://ruiyaoe-hash.github.io/shichubai-reads/](https://ruiyaoe-hash.github.io/shichubai-reads/)

## 这一期

| 期 | 嘉宾 | 题目 | 页面 |
|---|---|---|---|
| 001 | 姜乘澜 | 乘风破浪，心在桃源 | `/ep/001-jiang-chenglan/` |

来源是陈鲁豫的电影沙发、创作阶梯计划里的公开访谈：[YouTube 上的这一期](https://www.youtube.com/watch?v=NPOOl6g9z6s)。正文是评论骨架，不是官方文稿，也不是逐字稿。

第 001 期的音频不在仓库里。单集页播放的是 [Release `audio-001`](https://github.com/ruiyaoe-hash/shichubai-reads/releases/tag/audio-001) 上的文件：

`https://github.com/ruiyaoe-hash/shichubai-reads/releases/download/audio-001/001-jiang-chenglan.mp3`

构建时这个 https 地址原样写进播放器，不会再加 `/shichubai-reads/`。浏览器按范围请求收听，GitHub Pages 不托管这份 mp3。这不是官方播客的 enclosure。站点不放视频文件。封面仍在 `site/covers/`，默认黑白，悬停回到彩色。

## 这台浏览器里的记录

阅读进度和收藏都写在这台浏览器的 localStorage 里。没有账号。

阅读和收听进度用键 `lex-hist`。首页的「继续」和「看过」读它。收藏用键 `scb-fav`，每一项是 `{at: 时间戳}`。单集页标题下有「收藏 / 已收藏」。有收藏时，首页会出现「收藏」筛选，地址是 `?f=fav`。这个链接可以分享，但另一台设备上的收藏是空的。

清除这台浏览器里本站的网站数据后，进度和收藏会一起消失，也不会跟着你到另一台设备。

## 本地构建

只需要 Python 3，没有第三方依赖。

```bash
python3 tools/build.py
```

发布根目录是构建后的 `site/`。链接带项目页前缀 `/shichubai-reads/`，这样在 GitHub Pages 的项目站点上能直接打开，不必先绑域名。没有使用 `<base>`：它会把文内目录的 `#` 锚点解析到站点根，侧栏会跳错页。以 `https://` 开头的音频地址不会再拼 `BASE_PATH`；页面、封面、样式和脚本仍走项目页前缀。本地预览时，播放会向 GitHub 请求 Release 上的 mp3，需要能访问外网。

本地要按将来的网址预览：

```bash
python3 tools/build.py
rm -rf /tmp/gh-preview && mkdir -p /tmp/gh-preview/shichubai-reads
cp -a site/. /tmp/gh-preview/shichubai-reads/
python3 -m http.server 8123 -d /tmp/gh-preview
```

打开 [http://127.0.0.1:8123/shichubai-reads/](http://127.0.0.1:8123/shichubai-reads/)。

封面默认黑白。鼠标移上去，大约半秒内回到彩色，并轻轻放大到 1.025。这是壳层里原有的 `filter` 与 `transition`，不要拿掉。

以后如果绑了自定义域名、站点挂在域名根上，构建前设置：

```bash
SITE_DOMAIN=https://example.com BASE_PATH= python3 tools/build.py
```

同时把 `site/index.html` 里写死的 `/shichubai-reads/` 改成 `/`（报头、样式和脚本这几处不在构建标记内部）。

## 加上第 002 期

目录按**最新在前**排，和首页默认顺序一致。

1. 在 `tools/lex-master.json` 数组**最前面**加一条：`num`、`title`（英文或原文题）、`date`（`YYYY-MM-DD`）、`slug`、`sourceUrl`（合法外链，没有就 `""`）、`sourceLabel`、`ytId`（没有就 `null`）、`cover`（站内封面路径，如 `/covers/002-xxx.png`）、`reports`（公开报道，可空数组）。
2. 在 `tools/translations.json` 加上同一个 `slug`：`zh`（中文标题）、`guest`、`desc`（一两句简介）。
3. 若这一期要在页内播放音频，为它单独发一个 GitHub Release，标签必须是 `audio-002`（第 003 期则是 `audio-003`，以此类推）。把 mp3 作为该 Release 的附件上传。不要把文件提交进 git，也不要放进 `site/audio/`。这些 `audio-NNN` 标签只放这一期的内容文件，不要用来发布站点版本。然后在 `tools/feed_audio.json` 的 `by_num` 和 `by_slug` 写上附件的绝对地址，形如 `https://github.com/ruiyaoe-hash/shichubai-reads/releases/download/audio-002/002-….mp3`。`https://` 开头的地址会原样进入播放器。没有音频就留空，页面不放播放器。
4. 把精读正文片段放到 `site/zh/{slug}.html`（只要段落和 `h2`，不要整页 HTML）。把 `slug` 加进 `site/data/zh-index.json` 的 `slugs`。
5. 封面放到 `site/covers/`。有 YouTube id 时可以不放封面，卡片会用那张图，悬停仍会从黑白回到彩色。
6. `python3 tools/build.py`。

不要把抖音或别的平台的视频文件放进仓库。

## GitHub Pages

工作流在 `.github/workflows/pages.yml`：推到 `main` 后执行 `python3 tools/build.py`，用 `actions/upload-pages-artifact` 上传 `site/`，再 `actions/deploy-pages`。

仓库设置里需要打开一次：

1. **Settings → Pages → Build and deployment → Source** 选 **GitHub Actions**。
2. 把本分支合并进 `main`（工作流文件必须在默认分支上，Actions 才会按推送部署）。
3. 打开 **Actions**，确认 “Deploy GitHub Pages” 成功。
4. 站点地址是 [https://ruiyaoe-hash.github.io/shichubai-reads/](https://ruiyaoe-hash.github.io/shichubai-reads/)。单集在 `/shichubai-reads/ep/001-jiang-chenglan/`。

如果 Pages 还写着 “GitHub Actions” 不可选，先把带有 `pages.yml` 的提交推进 `main`，刷新设置页再选一次。

## 代码从哪里来

页面壳层——`site/style.css`、`site/app.js`、`site/ep.js`、首页和单集页的结构、`tools/build.py` 的构建方式——来自 [joeseesun/lexfridman-cn](https://github.com/joeseesun/lexfridman-cn)。那些代码以 [MIT](LICENSE) 许可使用，**许可只覆盖代码**。版权声明保留在 `LICENSE`。

本仓库没有保留 Lex 的节目数据、追新脚本或统计。新的一期是手工加进 `lex-master.json` 的，文件名沿用壳层，避免把构建入口改散。

## 内容与版权

- `site/zh/` 里的中文不是 MIT 许可的一部分。
- 精读是评论，依据公开访谈和报道，不是官方文稿，可能有偏差。原话以原访谈为准。
- 单集音频只放在 GitHub Release，一期一个标签：`audio-001`、`audio-002`……。仓库和 GitHub Pages 不托管这些 mp3。播放器使用 `releases/download/audio-NNN/…` 的绝对地址，供对照阅读，不是官方播客的 enclosure。没有音频就不放播放器。封面可以留在 `site/covers/`。视频文件不进仓库。不要用 `audio-NNN` 发布站点版本。
- 转载正文请署名「时初白精读」，并链接到对应页面。

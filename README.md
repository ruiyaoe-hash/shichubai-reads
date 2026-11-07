# 初白de小岛

按时间往下排的中文精读。暖纸白底、暖褐墨字、一道细线；陶土色是唯一强调色，只留给品牌小字、传播语与关键入口。

> 让阅读产生思想，让思想成为作品。

这是「初白de小岛」的固定传播语，唯一来源是 `tools/build.py` 的 `TAGLINE`：首页报头、全站页脚、JSON-LD 与 `llms.txt` 都由它注入，模板只留占位符。不要在模板或生成物里另写一份，也不要随手改写措辞。

首页顶部是最新一期的「最新精读」门面，下面按时间列出往期；搜索与排序在收录多期后出现。采用方案 B：门面那期不会在列表里重复出现，一旦搜索或切换为「由旧到新」，门面收起、列表恢复全部期数。首页只保留搜索与排序两件套：已收录的每一期都有中文精读，因此不再提供「全部 / 中文精读」这类没有第二取值的筛选。看过和收藏只记在这台浏览器里。

站点：[https://ruiyaoe-hash.github.io/shichubai-reads/](https://ruiyaoe-hash.github.io/shichubai-reads/)

> **版权立场**：本站是**非官方中文精读站**，不保存、不嵌入、不分发任何访谈音视频。完整内容只在权利人自行发布的官方渠道观看，各期页面只提供指向这些渠道的普通外链。完整的核查记录、法律依据说明与内容准入规则见 [COMPLIANCE.md](COMPLIANCE.md)，对外说明见站内「[版权与说明](/shichubai-reads/disclaimer/)」。

## 这一期

| 期 | 嘉宾 | 题目 | 页面 | 官方发布渠道 |
|---|---|---|---|---|
| 第叁期 | 待核 | 关于爱情，我终于想明白了几件事 | `/ep/003-about-love/` | 抖音精选（精读撰写中） |
| 第贰期 | Lauren（@poteto） | 我如何在一个月内把 2,500 个 PR 合进生产环境 | `/ep/002-poteto-2500-prs/` | X · 讲者本人发布 |
| 第壹期 | 姜乘澜 | 三个名字，三幕人生 | `/ep/001-jiang-chenglan/` | 抖音精选「创作阶梯计划」 |

两期写法不同：第壹期依据公开访谈与主办方、媒体的公开报道写成，以介绍与评述为主；第贰期是通读讲者本人公开发布的视频分享后、重新组织结构的中文整理译文，附术语表与附录。两者都不是官方文稿、不是逐字稿；完整内容以各期官方渠道为准。第贰期的授权边界、风险与下架承诺见 [COMPLIANCE.md](COMPLIANCE.md) §五之一。

**为什么页内没有播放器**：权利人未开放音频直链或官方嵌入，嘉宾官方主页明确标注「全网同名，只此一号，没有小号。暂未授权切片」。因此本站不上传、不转存、不播放原片，只链接到官方页面。早期版本曾把整段访谈音频上传到 Release 并在页内播放，该做法已撤销；Release 上的文件也请一并删除。

## 第叁期的官方外链（精读撰写中）

| 类型 | 页面 | 说明 |
|---|---|---|
| 节目官方视频页 | [抖音 · 第叁期节目视频页](https://www.douyin.com/video/7697926023714737408) | 2026-11-07 核验 GET 200；页面标题「关于爱情，我终于想明白了几件事」；发布账号与出镜人物待核 |

本期是**先登记节目入口、正文后补**：中文精读由岛主自行撰写，写好前不列入 `site/data/zh-index.json`、不建 `site/zh/003-about-love.html`，单集页明确标注「精读正在撰写中」。正文交付后转成 HTML 片段、补进 `zh-index.json` 并重建即可。第 003 期的来源核查与待核项见 [COMPLIANCE.md](COMPLIANCE.md)。

## 第壹期的官方外链

以下地址已核验可访问（GET 200）：抖音节目视频页于 2026-11-07 核验，主办方两个页面于 2026-11-04 核验。均由 `tools/lex-master.json` 的 `officialLinks` 驱动，自动出现在单集页顶部：

| 类型 | 页面 | 说明 |
|---|---|---|
| 节目官方视频页 | [抖音 · 第壹期节目视频页](https://www.douyin.com/video/7702304629450607887) | 第壹期节目本身的官方页面，2026-11-07 核验 GET 200；网页端受限时请在抖音 App 内观看（抖音号 `JCLjiangchenglan`） |
| 主办方预告 | [创作阶梯计划 · 对谈预告与观看指引](https://mp.weixin.qq.com/s?__biz=MzUxNTk5NjY4MQ==&mid=2247568636&idx=1&sn=861a6f7d6c446af0772a39ea8c1e1588) | 主办方自行发布的公开页面，写明发布渠道与上线时间 |
| 主办方通稿 | [创作阶梯计划 · 对谈内容官方通稿](https://mp.weixin.qq.com/s?__biz=MzUxNTk5NjY4MQ==&mid=2247568927&idx=1&sn=40ecdfb883333504f822240f13425c35) | 主办方发布的公开图文，含官方引语 |

第三方媒体报道（新浪新闻、网易新闻等）只放在 `reports` 里用于核对事实，不冒充原片入口。原 README 里那条 YouTube 链接无法核实为权利人授权发布，且与官方公告的发布渠道不符，已移除。

## 第贰期的官方外链

| 类型 | 页面 | 说明 |
|---|---|---|
| 讲者本人发布 | [X · @poteto 原视频分享](https://x.com/poteto/status/2102050467505430555) | 约 38 分钟，由讲者本人在 X 公开发布；本站不保存、不转存视频文件 |

该期正文末尾附注提到的英文 ASR 原文另存文件不在本仓库、不随站点发布；站内没有任何逐字稿文件。

## 这台浏览器里的记录

阅读进度和收藏都写在这台浏览器的 localStorage 里，没有账号。

阅读进度用键 `lex-hist`（沿用上游壳层的键名，改动会让老读者丢记录，暂不迁移）；收藏用 `scb-fav`，每项 `{at: 时间戳}`。单集页标题下有「收藏 / 已收藏」，首页卡片显示收藏标记与阅读进度。首页不提供收藏筛选；旧链接里的 `?f=` 参数会被忽略并自动从地址栏清除。清除本站网站数据后两者一起消失。

## 本地构建

只需要 Python 3，无第三方依赖。所有文件读写固定 UTF-8，中文 Windows 的默认 cp936 环境也能直接跑。

```bash
python3 tools/build.py
```

发布根目录是构建后的 `site/`。链接带项目页前缀 `/shichubai-reads/`，这样在 GitHub Pages 项目站点上能直接打开。没有用 `<base>`：它会把文内目录的 `#` 锚点解析到站点根，侧栏会跳错页。

**`site/index.html` 是生成物。** 要改版式请改 `tools/index.template.html`：里面的 `{{DOMAIN}}` / `{{BASE}}` 由构建时注入，因此切换项目页与域名根路径都不会残留旧地址。`site/robots.txt`、`site/site.webmanifest` 同样由 `build.py` 生成，不要手改。

本地按将来的网址预览（Git Bash / macOS / Linux）：

```bash
python3 tools/build.py
rm -rf /tmp/gh-preview && mkdir -p /tmp/gh-preview/shichubai-reads
cp -a site/. /tmp/gh-preview/shichubai-reads/
python3 -m http.server 8123 -d /tmp/gh-preview
```

打开 [http://127.0.0.1:8123/shichubai-reads/](http://127.0.0.1:8123/shichubai-reads/)。Windows PowerShell 可用 `python -m http.server 8123 -d <目录>`，或直接在 `site/` 下起服务（此时相对链接按项目页前缀会失效，仅适合看样式）。

三期封面**成套**：左侧固定标题网格，右侧是该期节目视频帧经本地像素运算转成的铅笔素描主人物图（灰度反相除法、45° 排线、轮廓梯度增强、四边羽化），右上角只留 `NO. 001 / 002 / 003` 小编号，不再出现汉字期号。素描以 WebP data URI 内嵌在 1280×720 SVG 里，不需要外部资源。日读是整张暖纸、墨线直接长在纸里；夜读是深褐左页 + 浅纸右页的对开版式，两版共用同一张素描图，按 `data-theme` 切换，不做灰度与放大。站内正文的「第壹期 / 第贰期」汉字期号仍由 `build.py` 的 `cn_num()` / `ep_label()` 与 `app.js` 的 `cnNum()` / `epLabel()` 两处同步生成，与封面编号互不影响。报头有一层极淡暖光，22 秒一次低幅度呼吸，`prefers-reduced-motion` 下静止。

### 自定义域名

站点挂到域名根时，只需构建前设置环境变量，**不要再手工改 `index.html`**：

```bash
SITE_DOMAIN=https://example.com BASE_PATH= python3 tools/build.py
```

模板方案保证这次构建与之后切回项目页都幂等。

## 加上新的一期

目录按**最新在前**排，和首页默认顺序一致。

1. 在 `tools/lex-master.json` 数组**最前面**加一条：`num`、`title`、`date`（`YYYY-MM-DD`）、`updated`（本次修订日）、`slug`、`sourceLabel`、`sourceUrl`、`rightsHolder`、`rightsNotice`、`officialLinks`、`cover`、`reports`。`ytId` 只有官方频道且确认允许嵌入时才填，否则 `null`。
2. **`officialLinks` 是合规红线**：每一项必须是 `https://` 开头、指向**权利人自行发布**的页面。第三方转载、搬运视频、音频/视频文件直链一律不填。没有核实的官方渠道就不填，页面会自动显示「暂无核实过的来源」。
3. 在 `tools/translations.json` 加同一 `slug`：`zh`、`guest`、`desc`。
4. 精读正文片段放 `site/zh/{slug}.html`（只要段落和 `h2`，不要整页 HTML），把 `slug` 加进 `site/data/zh-index.json` 的 `slugs`。
5. 封面放 `site/covers/`，沿用三期成套版式：左侧标题、右侧该期视频帧的铅笔素描、右上 `NO. 00X` 小编号，日读 / 夜读各一张。素材使用由站点所有者决定，记录见 [COMPLIANCE.md](COMPLIANCE.md) §五之二。
6. `python3 tools/build.py`。构建末尾的 `assert_site()` 会拦截：媒体文件、Release 直链、RSS enclosure、缺失的官方外链、路径前缀错误。
7. 更新 [COMPLIANCE.md](COMPLIANCE.md) 的核查记录与外链清单。

**禁止**：任何 mp3/mp4/视频文件进仓库或 Pages；任何逐字稿；`audio-NNN` 形式的 Release 音频附件；RSS enclosure；把访谈原片做成 iframe 嵌入。

**内容形态**：评论体与整理译文都属于中文精读。若某期采用覆盖整场分享的整理译文，须在 `COMPLIANCE.md`、本文件与站内《版权、来源与内容说明》中如实写明形态差异、授权状态与下架承诺；第贰期的决定记录不自动适用于后续期数。

## 校验与部署

- `.github/workflows/ci.yml`：PR 与非 main 分支推送时，分别在「项目页前缀」和「域名根」两种模式下构建，检查每期页面存在、输出无托管媒体、构建幂等。
- `.github/workflows/pages.yml`：推到 `main` 后构建并部署 Pages。
- `tools/build.py` 的 `assert_site()` **只校验结构不变量**。它不检查任何一期的标题、来源措辞或封面文件名——内容级审阅属于人工流程，放进构建器会让改一句话就发不出站。

仓库设置里需要打开一次：

1. **Settings → Pages → Build and deployment → Source** 选 **GitHub Actions**。
2. 把带 `pages.yml` 的提交推进 `main`。
3. 打开 **Actions**，确认 "Deploy GitHub Pages" 成功。
4. 单集地址：`/shichubai-reads/ep/001-jiang-chenglan/`、`/shichubai-reads/ep/002-poteto-2500-prs/`。

## 代码从哪里来

页面壳层——`site/style.css`、`site/app.js`、`site/ep.js`、首页和单集页结构、`tools/build.py` 的构建方式——来自 [joeseesun/lexfridman-cn](https://github.com/joeseesun/lexfridman-cn)，以 [MIT](LICENSE) 许可使用，**许可只覆盖代码**。`LICENSE` 里的原作者版权声明按 MIT 要求原样保留，它不是「品牌残留」。

本仓库没有保留 Lex 的节目数据、追新脚本或统计。`lex-master.json`、`lex-hist` 等命名是壳层遗留，为避免打断老读者的本地记录暂未重命名。

## 内容与版权

- 中文正文不是 MIT 许可的一部分，除依法属于合理使用的情形外保留所有权利。
- 中文内容依据已公开材料整理与评述，不是官方文稿、不是逐字稿，可能有偏差；原话与事实以原访谈及权利人发布的内容为准。
- 本站不保存、不嵌入、不分发任何访谈音视频；仓库、Pages、Release、RSS 都不含原片文件或文件直链。
- 封面为本站自制版式：标题、细线网格与编号由本站排版，右侧主人物图由该期公开视频帧做铅笔素描化处理；三期成套，日读 / 夜读各一张。
- 转载正文请署名「初白de小岛」并链接到对应页面，且不得删改版权说明。
- 权利人、嘉宾或其代理要求更正或下架：在[仓库开 Issue](https://github.com/ruiyaoe-hash/shichubai-reads/issues) 说明页面与理由，核实后更正、补出处或删页重建。

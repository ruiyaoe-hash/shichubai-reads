# 视频高光帧封面管线

这是给「初白de小岛」**以后新期**用的封面管线。默认不回填、不替换已上线各期封面。

站点所有者 2026-11-24 拍板的顺序，不能少、不能调换：

1. **先抽帧**（机器打分，给出候选）
2. **人来选**（从候选里定一帧）
3. **铅笔素描加暖纸**，再上标题排版

第 3 步是风格，不可改成「字直接贴在未处理的照片上」。没有成片的原创作品（如第叁期）走同一套：岛主提供静帧 → 铅笔素描 + 暖纸 → 标题网格。

仓库里的路径：

- `docs/highlight-cover-pipeline.md`  本说明
- `tools/extract_highlight_frames.py`  输入视频 → 候选帧 + 排序 + 推荐帧
- `tools/compose_cover.py`            选定静帧 → 素描 + 暖纸 + 日读 / 夜读 SVG（及 PNG 预览）
- `tools/models/face_detection_yunet_2023mar.onnx`  OpenCV YuNet 人脸模型（用于把人物放到右侧）
- `tools/models/README.md`            该模型的 MIT 许可全文与 OpenCV Zoo 出处
- `tools/requirements-highlight-cover.txt`  抽帧 / 合成的可选依赖；不要装进站点构建
- `tools/build.py` **保持标准库**，不把 opencv / pillow / numpy 拉进构建器，构建脚本也不导入上面两个封面工具

系统依赖：`ffmpeg`、`ffprobe`，以及 Noto Serif CJK SC 与 Liberation Serif（合成 PNG 预览用）。Python 依赖见 requirements 文件。YuNet 模型文件是 [OpenCV Zoo `models/face_detection_yunet`](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) 的 `face_detection_yunet_2023mar.onnx`（232589 字节，约 232 KB），MIT，Copyright (c) 2020 Shiqi Yu。许可全文在 `tools/models/README.md`。

## 新期怎么用

1. 准备该期官方视频的本地副本（**不要把成片提交进 git**）。
2. 抽帧并打分：

```bash
python tools/extract_highlight_frames.py /path/to/episode.mp4 \
  --out /tmp/epXXX-frames \
  --scenes --scan-caption-gaps
```

硬字幕成片请务必加 `--scan-caption-gaps`：脚本会先以 1fps 扫描字幕空隙，再把无字幕帧纳入打分。能拿到无烧录字幕的母版时，优先用母版。

3. 打开 `top_contact_sheet.jpg` 和 `top/` 里的 12 张全分辨率候选，**由人选定**一帧；必要时改选。说话中途张嘴、眨眼、虚焦、被字幕或台标挡住的帧在这一步剔除。
4. 把选定帧交给合成脚本。它会先做铅笔素描、再铺暖纸，然后叠标题：

```bash
python tools/compose_cover.py /path/to/chosen-frame.jpg \
  --out-prefix site/covers/00X-slug \
  --title '上句／下句' \
  --en-title 'English Title' \
  --figure '姓名' \
  --number 005 \
  --date 2026.11 \
  --kicker '中文精读'
```

`--number` 只接受数字（例如 `5` 或 `005`），会原样写成封面上的 `NO. 5` / `NO. 005`。不要传汉字期号，也不要传 `00X` 这类占位。

5. 照旧跑 `python tools/build.py`。`assert_site()` 仍只校验日读 / 夜读 SVG 里有与 `enTitle` / `figure` 一字不差的字符串。封面工具的产物不要在未获明确授权时写进已刊 `site/covers/001`–`004`。
6. 没有成片的原创作品：不要走抽帧；由岛主提供静帧后，只跑 `compose_cover.py`（同样会素描 + 暖纸，不另开一套）。

## 选帧标准（已写进 extract 脚本）

硬过滤：过糊（Laplacian 方差过低）、过暗 / 过亮、对比过平、明显上下黑边、过曝死黑、画面下方烧录字幕（黄白字幕条启发式），以及默认「必须检出人脸」（可用 `--allow-no-face` 关闭）。

打分（加权后取高，再按时间间隔做多样性，默认间隔 45 秒）：

- 锐度
- 曝光与反差
- 人脸大小适中、位置偏右
- 画面尽量干净

**不**把 CLIP / LAION-Aesthetic / NIMA 做成硬依赖：它们适合作为后续可选项，但封面最终以人工从 top-K 里确认一帧为准。

## 合成：素描 + 暖纸（已写进 compose 脚本）

对齐已刊第壹、叁期，以及 README / COMPLIANCE.md §五之二 写过的做法。当时的生成脚本是本地临时工具、没有进仓库，这里按文档描述和已刊像素复原：

- 灰度 → 反相模糊除法（color dodge）→ 轮廓梯度增强，得到铅笔素描
- 铺满幅暖纸：日读 `#F6EFE4`，夜读压暗一档 `#E6D8C5`；两版按各自纸色重渲染素描，不是给照片加一层滤镜
- 人物在右侧，左侧约 x&lt;640 为精确纸色，供标题网格使用
- 四边 smoothstep 软遮罩渐隐，源图裁切边落在 alpha=0 区，不设外框、分栏线或光晕
- 字体仍是 Noto Serif CJK SC；栏目标签、中文短对句、英文题、人物署名、右上 `NO. 00X` 的网格坐标与已刊各期一致
- 细线用与已刊相同的线性渐变，在 x≈662 前淡尽，不压到人物
- 画布 1280×720，与现有 `og:image` 声明一致

## 不要做的事

- 不要把选定帧直接当照片铺满封面，再把字贴在照片上。
- 不要跳过铅笔素描或暖纸。
- 不要把这段管线接到「自动上新期」或选题库。
- 不要在未获明确授权时替换 001–004 的已刊封面。
- 不要把视频文件或大图缓存提交进仓库。
- 不要把抽帧 / 素描依赖写进 `tools/build.py`。

## 验证

- `python tools/extract_highlight_frames.py --help`
- `python tools/compose_cover.py --help`
- 用任意一张静帧跑一遍合成，确认写出 `PREFIX.svg` 与 `PREFIX-dark.svg`，且文件中含 `--en-title` 与 `--figure` 原文；预览必须是素描人物 + 暖纸，而不是未处理的照片。
- 将这两张 SVG 按新期 `cover` 字段放好后，跑项目现有的 `python tools/build.py`（或 CI 里的双模式构建）。
- CI 的 `build` job 仍然只跑标准库构建，不安装 `requirements-highlight-cover.txt`。另有独立的 `highlight-cover` job：安装该依赖后跑两个 `--help`，再用合成短片做一次抽帧与 `--number 5` 的合成烟测。烟测写在临时目录，不进入 `site/`。

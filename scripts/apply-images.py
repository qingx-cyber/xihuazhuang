#!/usr/bin/env python3
"""把 index.html 里的 12 处图片占位换成 images/ 里的真实文件。

用法：
    python3 scripts/apply-images.py            # 预览会改哪些地方，不写文件
    python3 scripts/apply-images.py --write    # 真正写回 index.html

规则：
- 占位图按出现顺序编号 1..12，第 N 个占位对应 images/NN-*.webp
  （例如第 7 个占位 → images/07-清晨进棚.webp）；
- 第 12 个占位是 Vlog 区，会换成 <video>，用 images/vlog.mp4 和 images/vlog-poster.jpg；
- 找不到对应照片的占位（例如第 11 个）原样保留，方便以后补图；
- 顺带补上 width/height（防止加载时页面跳动）、loading/decoding、并把说明里的
  “（占位图）”字样清理掉。
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HTML = ROOT / "index.html"
IMAGES = ROOT / "images"

PLACEHOLDER_IMG = re.compile(r'<img\s+src="data:image/svg\+xml;base64,[^"]*"[^>]*>')
ALT = re.compile(r'alt="([^"]*)"')
PLACEHOLDER_COMMENT = re.compile(r"<!--\s*【图片占位 (\d+)】(.*?)-->", re.S)
VIDEO_COMMENT = re.compile(r"[ \t]*<!--\s*\n?\s*⬇️.*?-->\n", re.S)
VIDEO_OVERLAY = re.compile(r'\s*<div class="play"><span class="tri"></span></div>')
VIDEO_JS = re.compile(
    r"\n/\* =+ Vlog 播放（占位交互，接入真实视频后移除） =+ \*/\n"
    r"document\.getElementById\('videoBox'\)\.addEventListener\('click', function \(\) \{\n"
    r".*?\n\}\);\n",
    re.S,
)

# 照片接入后，把说明文字里的“占位”备注清掉（用不到的直接跳过）
CAPTION_CLEANUPS = [
    ("🌱 我们在西槐庄科技小院门口的合影（此处为占位图，请替换为真实照片）", "🌱 我们在西槐庄科技小院门口的合影"),
    ("曾经的西槐庄村（占位图，可替换为村史馆老照片）", "曾经的西槐庄村"),
    ("2020年11月11日 · 西槐庄科技小院揭牌（占位图）", "2020年11月11日 · 西槐庄科技小院揭牌"),
    ("今日西槐庄村（占位图）", "今日西槐庄村"),
    ("大棚里的绿色科技（占位图：可替换为水肥一体化 / 黄板 / 熊蜂箱等实拍）", "大棚里的绿色科技：水肥一体化 / 黄板 / 熊蜂箱"),
    ("招牌“冰淇淋萝卜”（占位图）", "招牌“冰淇淋萝卜”"),
    ("清晨进棚指导（占位图）", "清晨进棚指导"),
    ("入户回访（占位图）", "入户回访"),
    ("与村民的交流（占位图）", "与村民的交流"),
    ("我们小队在田野里的合影（占位图）", "我们小队在田野里的合影"),
    ("🎬 实践 Vlog：走进西槐庄科技小院（此处为占位封面，请替换为你们拍摄的视频）", "🎬 实践 Vlog：走进西槐庄科技小院"),
]


def webp_size(path: pathlib.Path) -> tuple[int, int]:
    """从 webp 文件头读出宽高（VP8X / VP8 / VP8L 三种情况）。"""
    data = path.read_bytes()[:64]
    chunk = data[12:16]
    if chunk == b"VP8X":
        w = int.from_bytes(data[24:27], "little") + 1
        h = int.from_bytes(data[27:30], "little") + 1
        return w, h
    if chunk == b"VP8L":
        bits = int.from_bytes(data[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if chunk == b"VP8 ":
        return (
            int.from_bytes(data[26:28], "little") & 0x3FFF,
            int.from_bytes(data[28:30], "little") & 0x3FFF,
        )
    raise ValueError(f"认不出 {path.name} 的尺寸")


def main() -> int:
    write = "--write" in sys.argv
    html = HTML.read_text(encoding="utf-8")
    original = html

    photos = {}
    for path in sorted(IMAGES.glob("[0-9][0-9]-*.webp")):
        photos[int(path.name[:2])] = path

    counter = {"n": 0}
    filled: dict[int, str] = {}

    def replace_img(match: re.Match) -> str:
        counter["n"] += 1
        index = counter["n"]
        tag = match.group(0)
        alt = ALT.search(tag)
        alt_text = alt.group(1) if alt else ""

        # 第 12 个占位是 Vlog 封面 → 换成真正的 <video>
        if index == 12:
            filled[12] = "images/vlog.mp4"
            return (
                '<video id="vlogPlayer" controls preload="metadata" '
                'poster="images/vlog-poster.jpg" width="960" height="544">\n'
                '            <source src="images/vlog.mp4" type="video/mp4">\n'
                '            您的浏览器不支持 video 标签，可<a href="images/vlog.mp4">点此下载观看</a>。\n'
                "          </video>"
            )

        photo = photos.get(index)
        if photo is None:
            print(f"  第 {index} 个占位：images/ 里没有对应照片，保持占位图不变")
            return tag

        width, height = webp_size(photo)
        attrs = [
            f'src="images/{photo.name}"',
            f'alt="{alt_text}"',
            f'width="{width}"',
            f'height="{height}"',
        ]
        if index == 1:  # 首屏大图要立刻显示，不懒加载
            attrs += ['loading="eager"', 'fetchpriority="high"']
        else:
            attrs += ['loading="lazy"', 'decoding="async"']
        filled[index] = f"images/{photo.name}"
        print(f"  第 {index} 个占位 → images/{photo.name}（{width}×{height}）")
        return f"<img {' '.join(attrs)}>"

    html = PLACEHOLDER_IMG.sub(replace_img, html)

    # 已接入照片的占位注释改写成一句简短说明
    def replace_comment(match: re.Match) -> str:
        index = int(match.group(1))
        target = filled.get(index)
        if not target:
            return match.group(0)
        return f"<!-- 图片 {index} 已接入：{target} -->"

    html = PLACEHOLDER_COMMENT.sub(replace_comment, html)
    html, n_comment = VIDEO_COMMENT.subn("", html)
    html, n_overlay = VIDEO_OVERLAY.subn("", html)
    html, n_js = VIDEO_JS.subn("\n", html)

    n_caps = 0
    for old, new in CAPTION_CLEANUPS:
        if old in html:
            html = html.replace(old, new)
            n_caps += 1

    print(
        f"\n占位替换：{len(filled)} 处；清理 Vlog 注释 {n_comment} 处、"
        f"播放遮罩 {n_overlay} 处、占位 JS {n_js} 处、说明文字 {n_caps} 处"
    )

    if html == original:
        print("文件没有变化。")
        return 0
    if not write:
        print("这是预览模式，没有写文件；确认无误后加 --write 再跑一次。")
        return 0

    HTML.write_text(html, encoding="utf-8")
    print(f"已写回 {HTML}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

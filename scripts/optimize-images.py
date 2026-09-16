#!/usr/bin/env python3
"""把 原图/ 里的照片压成网页用的 webp，输出到 images/。

用法：
    python3 scripts/optimize-images.py

规则：
- 文件名以两位数字开头（如 01-门口合影.jpg），数字作为网页里的图片位编号；
- 最长边缩到 1600px（原图更小的不放大），webp 质量 82；
- 输出同名但扩展名为 .webp 的文件到 images/。
"""

import pathlib
import sys

from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "原图"
OUT = ROOT / "images"
SOURCE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tif", ".tiff"}
MAX_SIDE = 1600
QUALITY = 82


def main() -> int:
    if not SRC.is_dir():
        print(f"找不到原图目录：{SRC}", file=sys.stderr)
        return 1
    OUT.mkdir(exist_ok=True)

    sources = sorted(
        p for p in SRC.iterdir()
        if p.is_file() and p.suffix.lower() in SOURCE_EXT and not p.name.startswith(".")
    )
    if not sources:
        print(f"{SRC} 里没有找到图片", file=sys.stderr)
        return 1

    total_before = total_after = 0
    print(f"{'文件':<26}{'原图':>18}  →  {'输出':>18}   体积变化")
    print("-" * 88)

    for src in sources:
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)
            before_wh = im.size
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            longest = max(im.size)
            if longest > MAX_SIDE:
                scale = MAX_SIDE / longest
                im = im.resize(
                    (max(1, round(im.width * scale)), max(1, round(im.height * scale))),
                    Image.LANCZOS,
                )
            dst = OUT / (src.stem + ".webp")
            im.save(dst, "WEBP", quality=QUALITY, method=6)
            after_wh = im.size

        before_kb = src.stat().st_size / 1024
        after_kb = dst.stat().st_size / 1024
        total_before += before_kb
        total_after += after_kb
        print(
            f"{src.name:<26}{before_wh[0]}×{before_wh[1]:<11}"
            f"  →  {after_wh[0]}×{after_wh[1]:<11}"
            f"  {before_kb:>8.0f}KB → {after_kb:>7.0f}KB"
        )

    saved = (1 - total_after / total_before) * 100 if total_before else 0
    print("-" * 88)
    print(f"合计：{total_before/1024:.1f}MB → {total_after/1024:.1f}MB（省了 {saved:.0f}%）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

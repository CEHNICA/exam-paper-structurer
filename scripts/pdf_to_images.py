#!/usr/bin/env python3
"""
把 PDF 每一页渲染成 jpg，用于 Claude 直接读图核对（Read 工具内置的 PDF 渲染在这台机器上
依赖 pdftoppm，如果报"pdftoppm is not installed"就用这个脚本代替）。

用法:
    python pdf_to_images.py <PDF路径> <输出文件夹> [--dpi 200]
"""
import argparse
from pathlib import Path

import fitz  # PyMuPDF


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf_path")
    ap.add_argument("out_dir")
    ap.add_argument("--dpi", type=int, default=200)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(args.pdf_path)
    print(f"total pages: {len(doc)}")
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=args.dpi)
        out_path = out_dir / f"page_{i + 1:02d}.jpg"
        pix.save(out_path)
        print(f"saved {out_path} ({pix.width}x{pix.height})")


if __name__ == "__main__":
    main()

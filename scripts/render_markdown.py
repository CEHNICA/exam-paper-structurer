#!/usr/bin/env python3
"""
将 questions.json（见本工具生成的结构）渲染成一份易读的 Markdown 试题文档。

用法: python render_markdown.py <questions.json> [输出路径 questions.md]
"""
import json
import sys
from pathlib import Path

SECTION_ORDER = []


def render(data):
    lines = []
    src = data.get("source", {})
    if src.get("title"):
        lines.append(f"# {src['title']}")
    meta_bits = [v for v in (src.get("school"), src.get("author") and f"命题教师：{src['author']}") if v]
    if meta_bits:
        lines.append("　".join(meta_bits))
    lines.append("")

    last_section = None
    for q in data["questions"]:
        if q.get("section") != last_section:
            last_section = q.get("section")
            if last_section:
                lines.append(f"## {last_section}")
                lines.append("")

        points = f"（{q['points']}分）" if q.get("points") else ""
        stem = q["stem"].replace("\n", "  \n")
        lines.append(f"**{q['id']}. {points}** {stem}")
        lines.append("")

        if q.get("options"):
            # 每个选项独立一段，前后留空行，选项字母与内容之间多一个全角空格做左右留白
            for k, v in q["options"].items():
                lines.append("")
                lines.append(f"{k}.　{v}")
            lines.append("")

        images = q.get("images") or ([q["image"]] if q.get("image") else [])
        labels = q.get("image_labels") or [None] * len(images)
        for img, label in zip(images, labels):
            alt = label or f"第{q['id']}题图"
            lines.append(f"![{alt}]({img})")
        if images:
            lines.append("")

        if q.get("answer"):
            lines.append(f"> 答案：{q['answer']}")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        sys.exit("用法: python render_markdown.py <questions.json> [输出 md 路径]")
    json_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else json_path.with_suffix(".md")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    out_path.write_text(render(data), encoding="utf-8")
    print(f"已生成: {out_path}")


if __name__ == "__main__":
    main()

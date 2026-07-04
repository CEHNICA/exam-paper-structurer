#!/usr/bin/env python3
"""
用 MinerU content_list.json 里的阅读顺序，把每张裁剪插图分配给"离它最近的上一道题"，
取代（或者说，先于）"拼联系表凭形状肉眼认"的做法。

原理：content_list.json 是按阅读顺序排列的一份列表（text/image/equation/footer...），
一道题的插图在物理排版上几乎总是紧跟在这道题的题干文字之后、下一道题题干之前。
所以只要能从文字里认出"第几题开始了"，题号文字和下一个题号文字之间出现的所有
image 类型条目，就是这道题的候选插图。

这解决不了的问题：MinerU 会把红笔解题过程、纸张背面透字的"鬼影"也当成 image 裁出来，
这些噪声往往也紧跟在对应题目后面，位置信息没法把它们剔除——所以这里只负责把"候选范围"
从一整页几十张图收窄到某道题名下的一两张，最终选哪张/要不要用，仍然需要看一眼图内容
（Claude 或人工），而不是完全自动定论。

用法:
    python match_images_by_position.py <content_list.json路径1> [<content_list.json路径2> ...]
    多个路径按试卷页面顺序传入，会当成一份连续文档拼接处理——这样即使某道题的插图
    因为排版被挤到下一张照片/下一页，只要传入顺序对，窗口一样能跨文件延伸过去。

输出: 一份 JSON，{"1": [], "2": ["<content_list所在目录>/images/xxx.jpg"], ...}
"""
import json
import re
import sys
from pathlib import Path

# 题号形如 "12." "12、" "12．"，但要排除 "(1)" "(2)" 这种小问编号、选项 "A." "B."，
# 以及 "3.5" 这种小数（要求标记前是行首/空白，标记后不是数字）。
# 不能只在文本开头找：OCR 有时会把题号粘在上一题最后一个选项的同一行末尾
# （比如 "D. 3 10. 如图..."），题号出现在字符串中间，必须整段搜索。
QUESTION_MARKER = re.compile(r"(?:^|\s)(\d{1,3})[\.\、．](?!\d)")


def load_items(content_list_paths):
    """把多个 content_list.json 按给定顺序拼成一条连续的 (item, images_dir) 列表。"""
    combined = []
    for p in content_list_paths:
        p = Path(p)
        items = json.loads(p.read_text(encoding="utf-8"))
        images_dir = p.parent  # img_path 是相对这个目录的相对路径，如 "images/xxx.jpg"
        for item in items:
            combined.append((item, images_dir))
    return combined


LOOKAHEAD = 5   # 允许往后找几个题号（应付连续几题的标记被OCR读花的情况）
SCAN_WINDOW = 20  # 每次往后扫多少个 content_list 条目去找下一个题号


def find_question_markers(combined):
    """
    按"接下来应该是第几题"逐个往后找，而不是见到任何递增的数字就收——
    见过一次真实案例：某道解答题的手写批改文字被 OCR 读花，
    里面偶然拼出了一个"24."，如果只判断"比上一个大就收"，
    会导致中间 19-23 这几道真正的题号全部被这个假阳性挡住、误判成"没找到"。
    改成"在期望题号附近一个小范围窗口里找最小的候选"，就不会被文档后面
    远处一个偶然凑巧、数值又比较大的假阳性抢先劫持。
    """
    markers = []
    expected = 1
    pos = 0
    n = len(combined)

    while pos < n:
        found = None  # (idx, num)
        scan_end = min(pos + SCAN_WINDOW, n)
        for idx in range(pos, scan_end):
            item, _ = combined[idx]
            if item.get("type") != "text":
                continue
            text = (item.get("text") or "").strip()
            for m in QUESTION_MARKER.finditer(text):
                num = int(m.group(1))
                if expected <= num <= expected + LOOKAHEAD:
                    if found is None or num < found[1]:
                        found = (idx, num)
        if found is None:
            break  # 这个窗口范围内彻底找不到接下来该有的题号了，到此为止
        markers.append(found)
        expected = found[1] + 1
        pos = found[0] + 1

    return markers


def assign_images(combined, markers):
    """
    题号标记之间的 image 条目，归给前一个题号。
    第一个题号标记之前出现的 image（比如版面顺序把某道题的插图排到了最前面，
    这次陈毅中学卷子里第7题的图就发生了这种情况），不能悄悄丢掉，单独列进
    "unassigned" 让人/AI 去核对该塞给哪道题。
    """
    result = {}
    unassigned = []

    first_marker_idx = markers[0][0] if markers else len(combined)
    for j in range(0, first_marker_idx):
        item, images_dir = combined[j]
        if item.get("type") == "image" and item.get("img_path"):
            unassigned.append(str(images_dir / item["img_path"]))

    for i, (idx, num) in enumerate(markers):
        end_idx = markers[i + 1][0] if i + 1 < len(markers) else len(combined)
        images = []
        for j in range(idx, end_idx):
            item, images_dir = combined[j]
            if item.get("type") == "image" and item.get("img_path"):
                images.append(str(images_dir / item["img_path"]))
        result[str(num)] = images

    return result, unassigned


def main():
    if len(sys.argv) < 2:
        sys.exit("用法: python match_images_by_position.py <content_list.json路径...>（按页面顺序传入）")

    combined = load_items(sys.argv[1:])
    markers = find_question_markers(combined)
    nums = [n for _, n in markers]
    print(f"\n识别出 {len(markers)} 个题号标记: {nums}")

    expected = set(range(1, (max(nums) if nums else 0) + 1))
    missing = sorted(expected - set(nums))
    if missing:
        print(f"警告：{missing} 这些题号没有识别到标记（多半是OCR把题号读花了），"
              f"它们的内容会被并入前一题的窗口——检查前一题候选数是不是多得反常。")
    print()

    result, unassigned = assign_images(combined, markers)
    for num, images in result.items():
        note = ""
        if not images:
            note = "（无候选图，可能确实没配图，也可能候选图落进了上面提到的缺失题号窗口，需要人工确认）"
        elif len(images) >= 3:
            note = "（候选数偏多，可能吞并了一道没识别到标记的相邻题，需要人工确认）"
        print(f"第{num}题: {len(images)}张候选 {note}")
        for img in images:
            print(f"    - {img}")

    if unassigned:
        print(f"\n未分配的图片（出现在第一个题号标记之前，不能瞎猜属于哪题，人工核对）：")
        for img in unassigned:
            print(f"    - {img}")

    out_path = Path("image_candidates.json")
    out_path.write_text(
        json.dumps({"questions": result, "unassigned": unassigned}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n已写入 {out_path.resolve()}")


if __name__ == "__main__":
    main()

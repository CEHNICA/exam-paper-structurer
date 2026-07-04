#!/usr/bin/env python3
"""
用 MiniMax-M3（文本模式）把 questions.json 里的数学记号转成行内 LaTeX（$...$），
生成 questions.json 的就地更新（更新前自动备份为 questions.json.bak）。

用法:
    python latexify_questions.py <questions.json路径>
    python latexify_questions.py <questions.json路径> --validate-only

如果第3步整理 questions.json 时已经自己手写好 LaTeX（对着原图看数学符号有把握，
不需要假手 M3），加 --validate-only 跳过 API 调用，只做换行伪影修复和 $ 配对校验——
不需要 config.json/API key，也不用等一次网络请求。只有对符号没把握、想让 M3 帮忙
转换时，才不加这个参数走完整流程。
"""
import argparse
import copy
import json
import re
import shutil
import sys
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
API_URL = "https://api.minimaxi.com/v1/text/chatcompletion_v2"
MODEL = "MiniMax-M3"

PROMPT = """你是一个数学试题排版助手。下面是一个 JSON 数组，每个元素是一道数学题的文字字段。
请把其中所有数学记号转换为行内 LaTeX（用 $...$ 包裹），规则：
- 线段/边/角等字母组合：AB=CD → $AB=CD$，∠ABC → $\\angle ABC$，△ABC → $\\triangle ABC$，▱ABCD → $\\square ABCD$（菱形、矩形等字样保留中文）
- 根号：√3 → $\\sqrt{3}$，2√3 → $2\\sqrt{3}$
- 分数：½AC → $\\frac{1}{2}AC$，S/2 → $\\frac{S}{2}$
- 度数：90° → $90^\\circ$，45° → $45^\\circ$
- 平行/垂直：AD∥BC → $AD\\parallel BC$，AE⊥BC → $AE\\perp BC$
- 带下标：S▱ABCD=9 → $S_{\\square ABCD}=9$，S菱形ABCD=4 → $S_{\\text{菱形}ABCD}=4$
- 单位保留中文/正体：12米、60cm 里的数字可以不套 $，但如果和公式连在一起（如 AB=16cm）写成 $AB=16\\,\\text{cm}$
- 相邻的数学片段合并到同一对 $ 里，不要把中文包进 $
- 中文叙述、标点、题号一律不动；换行符 \\n 保留

只输出转换后的 JSON 数组，结构、字段名、元素顺序必须和输入完全一致，不要加任何解释或代码围栏。

输入：
"""


def call_m3(payload_json, api_key, retries=2):
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT + payload_json}],
        "max_tokens": 12000,
        "temperature": 0.1,
    }
    last_err = None
    for attempt in range(retries + 1):
        resp = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body,
            timeout=300,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("base_resp", {}).get("status_code"):
            raise RuntimeError(data["base_resp"])
        choice = data["choices"][0]
        content = (choice["message"].get("content") or "").strip()
        # 剥掉可能出现的 ```json 围栏，再兜底提取第一个 [...] 数组
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content)
        m = re.search(r"\[.*\]", content, re.DOTALL)
        try:
            return json.loads(m.group(0) if m else content)
        except json.JSONDecodeError as e:
            last_err = e
            print(f"    第{attempt + 1}次解析失败 (finish_reason={choice.get('finish_reason')}, "
                  f"content前120字={content[:120]!r})，重试 ...")
    raise RuntimeError(f"M3 返回始终无法解析为 JSON: {last_err}")


# M3 偶尔会把 JSON 字符串里的换行符双重转义，写成字面的反斜杠+n（2个字符）而不是真正的
# 换行符。天真地把所有 "反斜杠+n" 都替换成真换行会连带破坏 \neq、\notin、\nabla 这些本来就以
# "\n" 开头的合法 LaTeX 命令（这个坑真的发生过：\neq 被切成"\"+换行+"eq"）。
# 区分方法：真正的换行符伪影后面通常紧跟"("（下一问的编号）、中文字符或字符串结尾；
# 合法的 LaTeX 命令后面紧跟小写英文字母（continues the macro name）。
# 只在"n"后面不是小写字母时才当作换行伪影处理。
_FAKE_NEWLINE = re.compile(r"\\+n(?![a-z])")


def fix_fake_newlines(value):
    if not isinstance(value, str):
        return value
    return _FAKE_NEWLINE.sub("\n", value)


def fix_and_validate(data):
    """就地修复字面反斜杠+n，并检查 $ 是否配对；返回发现的问题列表（不抛异常，只报告）。"""
    problems = []
    for q in data["questions"]:
        for f in ("stem", "answer"):
            if isinstance(q.get(f), str):
                q[f] = fix_fake_newlines(q[f])
        if q.get("options"):
            q["options"] = {k: fix_fake_newlines(v) for k, v in q["options"].items()}

        texts = [q.get("stem") or ""]
        texts += list((q.get("options") or {}).values())
        if q.get("answer"):
            texts.append(q["answer"])
        for t in texts:
            if _FAKE_NEWLINE.search(t):
                problems.append((q["id"], "仍有疑似字面反斜杠+n未处理", t[:60]))
            if t.count("$") % 2:
                problems.append((q["id"], "$ 数量不是偶数", t[:60]))
    return problems


def load_config():
    cfg_path = SCRIPT_DIR / "config.json"
    if not cfg_path.exists():
        sys.exit(
            f"未找到 {cfg_path}——先执行 `cp scripts/config.example.json scripts/config.json`，"
            "并填入你自己的 MiniMax API key（申请步骤见 SETUP.md）。"
        )
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json_path", help="questions.json 路径")
    ap.add_argument(
        "--validate-only", action="store_true",
        help="跳过 M3 转换，只做换行伪影修复 + $ 配对校验（适用于已经手写好 LaTeX 的情况，不需要 API key）",
    )
    args = ap.parse_args()

    json_path = Path(args.json_path)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    questions = data["questions"]

    if not args.validate_only:
        cfg = load_config()
        api_key = cfg["minimax_api_key"]

        # 按 8 题一批送给 M3，避免单次输出过长
        fields = ("stem", "options", "answer")
        for start in range(0, len(questions), 8):
            batch = questions[start:start + 8]
            slim = []
            for q in batch:
                item = {"id": q["id"], "stem": q["stem"]}
                if q.get("options"):
                    item["options"] = q["options"]
                if q.get("answer"):
                    item["answer"] = q["answer"]
                slim.append(item)
            payload = json.dumps(slim, ensure_ascii=False, indent=1)
            print(f"  转换第 {batch[0]['id']}-{batch[-1]['id']} 题 ...")
            converted = call_m3(payload, api_key)
            if len(converted) != len(batch):
                raise RuntimeError(f"返回题数不符: {len(converted)} != {len(batch)}")
            for q, c in zip(batch, converted):
                if q["id"] != c.get("id"):
                    raise RuntimeError(f"题号错位: {q['id']} != {c.get('id')}")
                for f in fields:
                    if f in c and c[f]:
                        q[f] = c[f]
    else:
        print("  --validate-only：跳过 M3 转换，只做换行伪影修复和 $ 配对校验。")

    problems = fix_and_validate(data)

    backup = json_path.with_suffix(".json.bak")
    shutil.copy(json_path, backup)
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"完成。已备份原文件到 {backup.name}，并更新 {json_path}")

    if problems:
        print(f"\n警告：修复后仍发现 {len(problems)} 处疑似问题，需要人工核对：")
        for qid, kind, preview in problems:
            print(f"  第{qid}题 - {kind}: {preview!r}")
    else:
        print("校验通过：没有残留的字面反斜杠+n，$ 全部配对。")


if __name__ == "__main__":
    main()

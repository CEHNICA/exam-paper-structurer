#!/usr/bin/env python3
"""
用 MiniMax-M3（大陆 Token Plan 账号，api.minimaxi.com）看图问答，
主要用来核对试卷照片里手写标注/圈出的答案，跟 Claude 自己读图的结果交叉验证。

用法:
    python minimax_vision.py <图片路径> "<问题>"
"""
import base64
import json
import mimetypes
import sys
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
API_URL = "https://api.minimaxi.com/v1/text/chatcompletion_v2"
MODEL = "MiniMax-M3"


def load_config():
    cfg_path = SCRIPT_DIR / "config.json"
    if not cfg_path.exists():
        sys.exit(
            f"未找到 {cfg_path}——先执行 `cp scripts/config.example.json scripts/config.json`，"
            "并填入你自己的 MiniMax API key（申请步骤见 SETUP.md）。"
        )
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def ask(image_path, prompt, api_key):
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    mime = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
    body = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            }
        ],
        "max_tokens": 800,
    }
    resp = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=body,
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("base_resp", {}).get("status_code"):
        raise RuntimeError(data["base_resp"])
    return data["choices"][0]["message"]["content"]


def main():
    if len(sys.argv) < 3:
        sys.exit('用法: python minimax_vision.py <图片路径> "<问题>"')
    cfg = load_config()
    answer = ask(sys.argv[1], sys.argv[2], cfg["minimax_api_key"])
    print(answer)


if __name__ == "__main__":
    main()

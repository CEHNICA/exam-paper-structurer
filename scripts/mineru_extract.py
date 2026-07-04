#!/usr/bin/env python3
"""
将一个文件夹里的试题照片/PDF 提交给 MinerU 云端解析，下载解析结果
（Markdown + content_list.json + 版面图片）到 <输入文件夹>/mineru_output/。

用法:
    python mineru_extract.py "<图片所在文件夹>" [--token TOKEN] [--model pipeline|vlm]

MinerU token 优先级: --token 参数 > MINERU_TOKEN 环境变量 > config.json 里的 mineru_token
"""
import argparse
import json
import os
import sys
import time
import zipfile
from pathlib import Path

import requests

API = "https://mineru.net/api/v4"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif", ".jp2"}
SCRIPT_DIR = Path(__file__).resolve().parent


def load_token(cli_token):
    if cli_token:
        return cli_token
    if os.environ.get("MINERU_TOKEN"):
        return os.environ["MINERU_TOKEN"]
    cfg_path = SCRIPT_DIR / "config.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        if cfg.get("mineru_token"):
            return cfg["mineru_token"]
    sys.exit("未找到 MinerU token，请用 --token 传入，或设置 MINERU_TOKEN 环境变量，或写入 config.json")


def submit_batch(files, token, model_version):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {
        "files": [
            {"name": f.name, "is_ocr": True, "data_id": f"page_{i + 1:02d}"}
            for i, f in enumerate(files)
        ],
        "model_version": model_version,
        "language": "ch",
        "enable_formula": True,
        "enable_table": True,
    }
    resp = requests.post(f"{API}/file-urls/batch", headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        sys.exit(f"提交任务失败: {data}")
    batch_id = data["data"]["batch_id"]
    upload_urls = data["data"]["file_urls"]

    for f, url in zip(files, upload_urls):
        with open(f, "rb") as fh:
            put_resp = requests.put(url, data=fh, timeout=120)
            put_resp.raise_for_status()
        print(f"  已上传: {f.name}")

    return batch_id


def poll_batch(batch_id, token, interval=5, timeout=900):
    headers = {"Authorization": f"Bearer {token}"}
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(f"{API}/extract-results/batch/{batch_id}", headers=headers, timeout=60)
        resp.raise_for_status()
        results = resp.json()["data"]["extract_result"]
        states = [r["state"] for r in results]
        print(f"  状态: {states}")
        if all(s in ("done", "failed") for s in states):
            return results
        time.sleep(interval)
    sys.exit("轮询超时，任务未在规定时间内完成")


def download_and_unzip(results, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    unpacked = []
    for r in results:
        if r["state"] != "done":
            print(f"  警告: {r.get('file_name')} 解析失败: {r.get('err_msg')}")
            continue
        zip_url = r["full_zip_url"]
        page_dir = out_dir / Path(r["file_name"]).stem
        page_dir.mkdir(parents=True, exist_ok=True)
        zip_path = page_dir / "result.zip"
        with requests.get(zip_url, stream=True, timeout=300) as resp:
            resp.raise_for_status()
            with open(zip_path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=1 << 16):
                    fh.write(chunk)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(page_dir)
        zip_path.unlink()
        unpacked.append(page_dir)
        print(f"  已下载并解压: {page_dir}")
    return unpacked


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input_dir", help="包含试题图片/PDF 的文件夹")
    ap.add_argument("--token", default=None, help="MinerU API token（JWT）")
    ap.add_argument("--model", default="pipeline", choices=["pipeline", "vlm"], help="解析模型，默认 pipeline")
    ap.add_argument("--out", default=None, help="输出目录，默认 <input_dir>/mineru_output")
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        sys.exit(f"找不到目录: {input_dir}")

    files = sorted(
        [p for p in input_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS or p.suffix.lower() == ".pdf"]
    )
    if not files:
        sys.exit("目录下没有找到图片或 PDF 文件")

    print(f"共找到 {len(files)} 个文件，按文件名顺序（应为页面顺序）:")
    for f in files:
        print(f"  - {f.name}")

    token = load_token(args.token)
    out_dir = Path(args.out) if args.out else input_dir / "mineru_output"

    print("正在提交并上传到 MinerU ...")
    batch_id = submit_batch(files, token, args.model)
    print(f"批次 ID: {batch_id}，等待解析完成 ...")
    results = poll_batch(batch_id, token)
    print("正在下载解析结果 ...")
    unpacked = download_and_unzip(results, out_dir)

    print(f"\n完成。解析结果已保存到: {out_dir}")
    for p in unpacked:
        print(f"  - {p}")


if __name__ == "__main__":
    main()

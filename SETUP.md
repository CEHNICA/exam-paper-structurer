# 安装 & 环境搭建指南（给 AI agent 看的，照着一步步做）

这是一个 Claude Code skill 的分发包：把手机拍的数学试卷照片/PDF 转成结构化题目（JSON + Markdown，插图自动配到对应题目）。收到这份包的人应该让自己的 Claude Code（或其他支持 skill 机制的 agent）读这份文件，按顺序把环境搭好，然后就可以正常使用了。

## 第0步：确认这是不是你要的东西

打开 `SKILL.md` 看一眼开头的 description 和正文，确认这确实是"把试卷照片处理成结构化题目"这个功能，不是别的。

## 第1步：把这个文件夹放到 skill 目录下

把这整个文件夹（包含 `SKILL.md`、`scripts/`、`references/`）复制到用户的 Claude Code skills 目录下，文件夹名就用 `exam-paper-structurer`：

- Windows: `C:\Users\<用户名>\.claude\skills\exam-paper-structurer\`
- macOS/Linux: `~/.claude/skills/exam-paper-structurer/`

如果目标位置已经有同名文件夹，先问用户要不要覆盖，不要直接覆盖别人的东西。

## 第2步：装 Python 依赖

需要 Python 3.9 及以上。在这个文件夹里跑：
```
pip install -r requirements.txt
```
装的是 `requests`（调用 MinerU/MiniMax 的 HTTP API）、`Pillow`（拼联系表用的图像处理）、`PyMuPDF`（渲染 PDF 页面，import 名是 `fitz`）。

装完用这条确认一下都能正常 import：
```
python -c "import requests, PIL, fitz; print('依赖OK')"
```

## 第3步：申请两个第三方服务的凭证

这个 skill 依赖两个外部服务，都需要用户自己注册账号申请凭证——**不要帮用户填入任何凭证，也不要使用这份包里可能出现的任何示例值**，这些必须是用户自己的账号：

1. **MinerU**（负责试卷版面解析、OCR、插图裁剪）
   - 去 https://mineru.net 注册账号（已注册可直接登录）
   - 打开 **https://mineru.net/apiManage/token** ——登录后会跳到 token 管理页面，点"创建 token"或类似按钮拿一个（一串很长的 JWT 字符串，形如 `eyJ...`）
   - 免费账号每天有一定的解析页数额度

2. **MiniMax**（负责视觉核对和 LaTeX 转换，用的是 `MiniMax-M3` 模型）
   - 去 https://platform.minimaxi.com 注册**中国大陆账号**（注意不是国际站 platform.minimax.io，这个 skill 依赖大陆站的 API 地址 `api.minimaxi.com`，国际站地址会认证失败）
   - 开通 Token Plan 订阅，拿到一个 `sk-cp-` 开头的 API key

如果用户不方便自己申请、需要你帮忙走注册流程，参照你自己的安全准则处理（通常涉及创建账号/填写个人信息，应该由用户自己动手，你可以在旁边指路）。

## 第4步：配置凭证

在 `scripts/` 目录下：
```
cp config.example.json config.json
```
然后打开 `scripts/config.json`，把 `mineru_token` 和 `minimax_api_key` 换成用户第3步申请到的真实值，其余字段（`minimax_base_url`、`minimax_text_model`、`minimax_vision_model`）保持原样不用改。

**`config.json` 不要分享给别人、不要提交到公开代码仓库或截图发出去**——它包含用户的私人凭证。

## 第5步：验证凭证能用

跑一个轻量级的连通性检查（不需要真的处理试卷）：
```
python -c "
import json, requests
cfg = json.load(open('scripts/config.json', encoding='utf-8'))
r = requests.post('https://api.minimaxi.com/v1/text/chatcompletion_v2',
    headers={'Authorization': f'Bearer {cfg[\"minimax_api_key\"]}', 'Content-Type': 'application/json'},
    json={'model': cfg['minimax_text_model'], 'messages':[{'role':'user','content':'回复两个字：测试'}], 'max_tokens': 10})
print('MiniMax:', r.status_code, r.json().get('base_resp'))
"
```
返回 `status_code: 200` 且 `base_resp` 里 `status_code: 0` 就说明 MiniMax 这边配置对了。MinerU 的 token 会在第一次真正解析试卷时验证，不需要单独测。

## 第6步：告诉用户可以用了

跟用户确认：以后只要给一份试卷照片/PDF，说"帮我把这份试卷处理成结构化题目"之类的话，就会自动触发这个 skill。可以先看一眼 `references/history/INDEX.md` 了解已经积累的经验（这是原作者处理过的几份卷子留下的记录，跟这次的具体使用场景无关，可以参考但不用管里面提到的具体文件路径）。

正式使用流程见 `SKILL.md` 正文，不用再重复讲一遍。

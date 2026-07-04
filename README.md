# exam-paper-structurer

> 一份 Claude Code skill：把手机拍的中国数学试卷照片 / PDF 转成结构化题目（JSON + Markdown，题干/选项配 LaTeX 公式，插图自动配到对应题目）。

## 是什么

传统的"拍照存卷"最后都变成相册里的一张没人看的图，这份 skill 想把这件事做扎实——不是再 OCR 一遍字，而是真的把一份试卷还原成**题库**：

- 把每道题的题干、选项、印刷体插图干净地转写出来
- 手写的答案、批改、解题过程**默认不识别**（那是答卷，不是题库——除非你明确要求）
- 输出 `questions.json` + `questions.md` + `images/`，可直接喂给 Anki / 题库 App / 复盘材料

## 怎么装

按 [`SETUP.md`](./SETUP.md) 一步步走，主要是：

1. 把这份仓库 clone 到 `~/.claude/skills/exam-paper-structurer/`
2. `pip install -r requirements.txt`
3. 申请 MinerU token 和 MiniMax API key（中国大陆 Token Plan，`sk-cp-` 开头）
4. `cp scripts/config.example.json scripts/config.json` 填凭证

10-15 分钟搞定。

## 怎么用

把 skill 文件夹就位、凭证填好之后，对 Claude Code 说类似下面的话就能触发：

> "帮我把这张照片里的卷子处理成结构化题目"
> 
> "把这份 PDF 试卷整理成题库"

处理流程见 [`SKILL.md`](./SKILL.md)，6 步：

1. `mineru_extract.py` — 版面解析 + OCR + 插图裁剪
2. `match_images_by_position.py` — 按阅读顺序位置把插图配到题号（**不要凭形状肉眼比对**——曾经的真实踩坑）
3. Claude 自己读题 + 校对插图
4. `latexify_questions.py` — 数学记号转 LaTeX（带 JSON 双重转义自动修复）
5. `render_markdown.py` — 生成最终 `questions.md`
6. 在 `references/history/` 写处理记录

## 数据结构

`questions.json` 的字段定义见 [`references/questions_schema.md`](./references/questions_schema.md)。

## 处理历史

`references/history/` 里记录了过去几份实战踩过的坑（陈毅初三几何卷、凤城高一数学卷、胜利初四数学卷）。处理新卷子前先扫一眼，能提前避开常见问题。

## 第三方依赖 & 声明

- **MinerU**（[mineru.net](https://mineru.net)）— 试卷版面解析、OCR、插图裁剪，需要免费的 API token
- **MiniMax**（[platform.minimaxi.com](https://platform.minimaxi.com)，中国大陆 Token Plan）— 数学记号 → LaTeX 转换 + 视觉核对，需要 `sk-cp-` 开头的 API key
- 跑出来的产物（`mineru_output/`、`structured/`、`*.bak`）已在 `.gitignore` 里，不会被 git 追踪

两个服务都有免费 / 低成本额度，个人整理自家孩子的卷子绰绰有余。**这份 skill 不包含任何人的私人凭证**——`scripts/config.example.json` 只有占位符，每个人自己填自己的。

## License

[MIT](./LICENSE)

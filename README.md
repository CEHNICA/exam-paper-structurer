# exam-paper-structurer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](#装起来)
[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-6b5fc7.svg)](https://github.com/anthropics/claude-code)

> 一份 Claude Code skill：把手机拍的中国数学试卷照片 / PDF，变成结构化题目——`questions.json` + `questions.md`，题干选项配好 LaTeX，插图自动配对到对应题号。

## 拍完照片之后呢？

试卷拍完照，通常的下场是躺在相册里吃灰——除了"证明处理过"，没有别的用处。想找某一道题要翻半天照片，更别提喂给 Anki、题库工具或者下学期的复习资料。

这个项目要做的不是再 OCR 一遍文字，而是把一份卷子真正拆解成可复用的**题目条目**：题干、选项、插图各自落位，数学符号转成 LaTeX，手写的答案和批改默认不管——你要的是题库，不是一份带批改痕迹的答卷复印件。

跟 Claude Code 说一句"帮我把这份试卷处理成结构化题目"，剩下的都自动跑：

```
照片 / PDF
   │  mineru_extract.py —— 版面解析 + OCR + 插图裁剪
   ▼
候选插图 + 印刷体文字
   │  match_images_by_position.py —— 按位置把插图配到题号
   │  Claude 亲自读原图 —— 校对题干、核对配图
   ▼
questions.json（数学符号还是原始记号）
   │  latexify_questions.py —— 转成行内 LaTeX
   ▼
questions.json + questions.md —— 图文并茂、可直接用的题库
```

## 出来的东西长什么样

一道解答题在 `questions.json` 里大概是这样：

```json
{
  "id": 17,
  "type": "solving",
  "section": "四、解答题",
  "points": 15,
  "stem": "某网店销售一批新款削笔器，进价为10元/个.经统计，该削笔器的日销售量$y$（单位：个）与售价$x$（单位：元）满足如图所示的函数关系.\n(1) 为了使这批削笔器的日利润最大，应怎样定制这批削笔器的销售价格？\n(2) 为了使这批削笔器的日利润不低于售价为15元时的日利润，求售价$x$的取值范围.",
  "image": "images/q17.jpg"
}
```

`render_markdown.py` 把它渲染成带图、选项分行显示的 `questions.md`，直接拿去做题库、喂给 Anki，或者当复盘材料。完整字段说明见 [`references/questions_schema.md`](./references/questions_schema.md)。

## 只做这一件事，划清边界

**支持**：中国初一到高三的数学试卷——月考、期中期末、真题、模拟卷；选择/填空/解答题混排；函数、几何、代数、概率统计、数列等常见板块；手机拍照或扫描 PDF 都行。

**默认不做**：识别手写内容。批改红笔、学生的解题过程、圈出的答案字母——这些是"这份答卷"的信息，不是"这道题"的信息，默认不提取，`answer` 字段直接省略。只有你明确要求"把答案也记下来"才会做，而且这一步比听起来贵得多（连笔字、涂改、多选题都容易认错），所以不是默认行为。

**不在范围内，也不打算扩**：其它学科、大学 / 竞赛数学、中国大陆以外的试卷版式。底层的版面解析和位置配图逻辑也许凑巧能用在别的场景，但没测试过，用出问题欢迎反馈，不算 bug。

## 装起来

```bash
git clone https://github.com/CEHNICA/exam-paper-structurer.git ~/.claude/skills/exam-paper-structurer
cd ~/.claude/skills/exam-paper-structurer
pip install -r requirements.txt
cp scripts/config.example.json scripts/config.json   # 填入你自己的凭证
```

还需要申请两个第三方凭证：**MinerU**（版面解析）和 **MiniMax 中国大陆 Token Plan**（LaTeX 转换 + 视觉核对，模型用 `MiniMax-M3`，注意不是国际站）。完整申请步骤、验证方法和常见报错排查见 [`SETUP.md`](./SETUP.md)，跟着走 10-15 分钟能搞定。

装好之后不用记命令，直接跟 Claude Code 说话：

> 帮我把这张试卷照片处理成结构化题目
>
> 把这份月考 PDF 整理成题库

完整六步流程和每一步的已知坑，见 [`SKILL.md`](./SKILL.md)。

## 处理过的卷子留下的经验

`references/history/` 记录了几份真实卷子处理时的发现——比如几何卷几乎每题都配图，而代数 / 函数卷的候选插图里大部分其实是学生手绘的验算草稿，真正的印刷插图反而很少，这种反直觉的差异不看历史记录很容易踩坑。处理新卷子前先扫一眼 `INDEX.md`，能省不少事。

## 关于凭证和隐私

`scripts/config.example.json` 里只有占位符，不含任何真实凭证；仓库里也不会出现任何人的私人 token 或 API key。运行产生的 `config.json`、`mineru_output/`、`structured/`、`*.bak` 都在 `.gitignore` 里，不会被提交。MinerU 和 MiniMax 都有免费 / 低成本额度，个人处理自家孩子的卷子完全够用。

## 反馈 / 贡献

Issue、PR 都欢迎，仓库是 MIT 协议，clone 下来改完 `git push` 就行——无论你是真人用户，还是正在替你跑这份 skill 的 AI agent。

最有价值的反馈来自实战：卷子的基本情况（年级 / 题型概况，能脱敏就脱敏）、卡在哪一步、怎么绕过去的。如果能整理成一份 `references/history/<卷子名>.md`（照抄现有几份的格式），那是最好的贡献方式——下一个处理卷子的人能直接受益，少踩一半坑。

## License

[MIT](./LICENSE)

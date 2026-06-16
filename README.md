# bank-flow-report

> 银行流水财务分析报告生成器 —— 一个 [Claude Code](https://claude.com/claude-code) skill。
> 输入一份银行流水（Excel/CSV，列名格式不限），一键产出一套专业的财务分析文件。

## 这是什么

把一份杂乱的银行账户流水，自动变成：

- **`index.html`** —— 整合分析网站（顶部导航 + 首屏 + 约 10 个交互图表 + 解读 + 建议，主成品）
- **`charts.html`** —— 图表速览版
- **`report.html`** —— 完整文字版（适合打印 / 正式存档）
- **`pic/`** —— 预留的配图位（放了图显示图，没放自动用品牌渐变兜底，不破版）

核心设计：**脚本只负责算数和排版，解读文字由 Claude 读完真实数据后现写**，不套死模板，因此每份报告都贴合那份流水的实际情况。

## 特性

- **列名自适应**：不管列叫"对方户名"还是"交易对手"、方向是"借/贷"还是"收/付"或正负金额，都能识别
- **多维指标**：年/季/月趋势、对手方画像、属性构成、用途分类、集中度（HHI / CRn）、波动性、季节性、金额分布、Benford 检验、异常筛查
- **主体视角自动切换**：非营利/社团看储备线与政府依赖、企业看回款与盈利、个人看储蓄率
- **隐私脱敏**：对外的网站与图表版自动给自然人姓名打码（保留姓氏、名字转 `*`，如 `张伟明 → 张**`），完整文字版可留真名作内部存档
- **可独立运行**：两个 Python 脚本也可脱离 Claude 单独使用

## 架构

```
SKILL.md          # 工作流程（Claude 按此执行）
flow_analyze.py   # 分析引擎：流水 + config.json → analysis/data.json
flow_build.py     # 渲染引擎：data.json + narrative.json → 三件套 HTML
```

数据流：`流水文件 → [flow_analyze] → data.json → [Claude 写 narrative.json] → [flow_build] → 三件套`

## 安装

```bash
git clone https://github.com/<你的用户名>/bank-flow-report.git
cd bank-flow-report
bash install.sh          # 复制到 ~/.claude/commands 与 ~/.claude/skills-assets
pip3 install pandas openpyxl
```

安装后在 Claude Code 里发一份流水说"生成流水报告"，或输入 `/bank-flow-report`。

## 手动使用（不经 Claude）

```bash
# 1. 按 examples/config.example.json 写一份 config.json（指向你的流水、映射列名）
python3 flow_analyze.py config.json        # → analysis/data.json

# 2. 参照 examples/narrative.example.json 写 analysis/narrative.json（解读文字）

# 3. 生成三件套
python3 flow_build.py config.json          # → index.html / charts.html / report.html + pic/
```

## 隐私

- **不修改**你的原始流水文件
- 对外网站与图表版自动脱敏自然人姓名（`mask_site: true`）
- 全程本地处理，不上传任何数据

## License

MIT

#!/usr/bin/env bash
# 把 bank-flow-report skill 安装到 Claude Code
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p ~/.claude/commands ~/.claude/skills-assets/bank-flow-report
cp "$DIR/SKILL.md" ~/.claude/commands/bank-flow-report.md
cp "$DIR/flow_analyze.py" "$DIR/flow_build.py" ~/.claude/skills-assets/bank-flow-report/

# 缓存 ECharts，使生成的报告自包含、可离线/微信直接打开（下载失败不阻断安装，报告会回退 CDN）
ECH=~/.claude/skills-assets/bank-flow-report/echarts.min.js
if [ ! -f "$ECH" ]; then
  echo "下载 ECharts（约 1MB，用于内联到报告）..."
  curl -fsSL https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js -o "$ECH" \
    && echo "✓ ECharts 已缓存" || { echo "⚠ ECharts 下载失败，报告将回退 CDN（联网仍可正常显示）"; rm -f "$ECH"; }
fi

echo "✓ 已安装 bank-flow-report skill"
echo "  - ~/.claude/commands/bank-flow-report.md"
echo "  - ~/.claude/skills-assets/bank-flow-report/{flow_analyze,flow_build}.py"
echo ""
echo "请确认依赖已安装：pip3 install pandas openpyxl"
echo "然后在 Claude Code 中发送流水文件并说「生成流水报告」，或输入 /bank-flow-report"

#!/usr/bin/env bash
# 把 bank-flow-report skill 安装到 Claude Code
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p ~/.claude/commands ~/.claude/skills-assets/bank-flow-report
cp "$DIR/SKILL.md" ~/.claude/commands/bank-flow-report.md
cp "$DIR/flow_analyze.py" "$DIR/flow_build.py" ~/.claude/skills-assets/bank-flow-report/

echo "✓ 已安装 bank-flow-report skill"
echo "  - ~/.claude/commands/bank-flow-report.md"
echo "  - ~/.claude/skills-assets/bank-flow-report/{flow_analyze,flow_build}.py"
echo ""
echo "请确认依赖已安装：pip3 install pandas openpyxl"
echo "然后在 Claude Code 中发送流水文件并说「生成流水报告」，或输入 /bank-flow-report"

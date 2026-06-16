# -*- coding: utf-8 -*-
"""
通用渲染引擎：data.json(指标) + narrative.json(Claude写的解读) + config.json(主体) → 三件套 HTML。
产出：index.html(整合网站) / charts.html(图表版) / report.html(完整文字版) + pic/ 配图位。
脱敏：config.mask_site=True 时，网站与图表版的自然人姓氏→*，文字版(存档)默认留真名。
用法：python3 flow_build.py [config.json]
"""
import sys, os, json, re

CFG = sys.argv[1] if len(sys.argv) > 1 else 'config.json'
cfg = json.load(open(CFG, encoding='utf-8'))
BASE = os.path.dirname(os.path.abspath(CFG)) or '.'
OUT = cfg.get('outdir', BASE)
D = json.load(open(os.path.join(OUT, 'analysis', 'data.json'), encoding='utf-8'))
NARR = os.path.join(OUT, 'analysis', 'narrative.json')
N = json.load(open(NARR, encoding='utf-8')) if os.path.exists(NARR) else {}
MASK_SITE = cfg.get('mask_site', True)
M = D['meta']; OV = D['overview']

# ---------- 姓名脱敏 ----------
ORG_KW = ['市','县','区','省','局','委','办','会','厅','政府','街道','财政','专户','银行','公司','中心',
 '研究院','学院','大学','协会','商会','工作室','事务所','合伙','传媒','传播','科技','广告','网络','文化',
 '管理','咨询','实业','集团','基地','款项','国税','地税','税务','发展','服务','投资','工程','建设','贸易',
 '电子','信息','产业','装饰','塑胶','管委','开发区','委员会','有限','部','站','队','院','校','行','社','厂','场']
def mask(s):
    if not s: return s
    t = s.strip()
    if any(k in t for k in ORG_KW): return s
    if re.fullmatch(r'[一-龥·]{2,4}', t): return '*' + t[1:]
    return s
def mask_data(d):
    import copy; x = copy.deepcopy(d)
    for r in x['top_in']+x['top_out']: r['name'] = mask(r['name'])
    for r in x['anomaly']['big_top']+x['anomaly']['freq_groups']: r['cp'] = mask(r.get('cp'))
    return x
D_SITE = mask_data(D) if MASK_SITE else D

# ---------- 工具 ----------
def w(v):           # 元 → 万元字符串
    return f'{v/1e4:,.1f}'
def yi_or_w(v):
    return f'{v/1e8:.2f}亿' if abs(v) >= 1e8 else f'{v/1e4:,.1f}万'
def g(key, default=''):   # narrative 取值
    return N.get(key, default)
def nl2(s): return (s or '').replace('\n', '<br>')

# narrative 片段 → HTML
def findings_html():
    out = []
    for f in N.get('findings', []):
        out.append(f'<div class="finding"><b>{f.get("t","")}</b>{f.get("d","")}</div>')
    return '\n'.join(out) or '<div class="finding">（待填写核心发现）</div>'
def alert_html():
    a = N.get('alert')
    if not a: return ''
    return f'''<div class="alert"><div class="ico">⚠️</div><div>
      <h4>{a.get("title","")}</h4><p>{a.get("body","")}</p></div></div>'''
def trend_html():
    out = []
    for t in N.get('trend', []):
        out.append(f'<div class="conclusion"><p><b>{t.get("t","")}</b>　{t.get("d","")}</p></div>')
    return '\n'.join(out)
def advice_html():
    cmap = {'紧急':'urgent','重要':'important','战略':'strategy','机制':'important'}
    out = []
    for i, a in enumerate(N.get('advice', []), 1):
        lv = a.get('level') or cmap.get(a.get('tag',''), 'normal')
        out.append(f'''<div class="advice"><span class="no">{i}</span>
        <span class="tag {lv}">{a.get("tag","建议")}</span>
        <h4>{a.get("h","")}</h4><p>{a.get("p","")}</p></div>''')
    return '\n'.join(out)

REPL = {
    '__DATA__': json.dumps(D_SITE, ensure_ascii=False),
    '__NAME__': M.get('name', '账户'),
    '__SUBTITLE__': cfg.get('subtitle', '银行账户流水财务分析报告'),
    '__ACCOUNT__': M.get('account', ''),
    '__RANGE__': f"{M['date_start']} 至 {M['date_end']}",
    '__SPAN__': f"{M.get('span_years','')} 年 · {M.get('span_days','')} 天",
    '__COUNT__': f"{M['total_count']:,}",
    '__REPORTDATE__': cfg.get('report_date', M['date_end']),
    '__TURNOVER__': yi_or_w(OV['turnover']),
    '__NET__': ('+' if OV['net'] >= 0 else '') + yi_or_w(OV['net']),
    '__ENDBAL__': yi_or_w(OV['end_bal']),
    '__TOTALIN__': w(OV['total_in']), '__TOTALOUT__': w(OV['total_out']),
    '__INCNT__': f"{M.get('in_count',0):,}", '__OUTCNT__': f"{M.get('out_count',0):,}",
    '__EXEC__': nl2(g('exec_summary', '（执行摘要待填写）')),
    '__ALERT__': alert_html(),
    '__FINDINGS__': findings_html(),
    '__OVERVIEW_NOTE__': nl2(g('overview_note')),
    '__INCOME_NOTE__': nl2(g('income_note')),
    '__EXPENSE_NOTE__': nl2(g('expense_note')),
    '__TREND__': trend_html(),
    '__TREND_NOTE__': nl2(g('trend_note')),
    '__RISK_NOTE__': nl2(g('risk_note')),
    '__CONCLUSION__': nl2(g('conclusion')),
    '__ADVICE__': advice_html(),
    '__SUBJECT_TYPE__': M.get('subject_type', ''),
}
def render(tpl):
    for k, v in REPL.items():
        tpl = tpl.replace(k, str(v))
    return tpl

# ============================================================= 网站模板
TPL_INDEX = r'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__NAME__ · 财务分析报告</title><link rel="icon" href="pic/favicon.png">
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
:root{--navy:#1e3a5f;--navy-d:#14293f;--gold:#c5a572;--gold-d:#a8884f;--green:#10b981;--green-d:#047857;
--red:#ef4444;--red-d:#b91c1c;--blue:#3b82f6;--ink:#1f2937;--gray:#6b7280;--line:#e5e7eb;--bg:#f4f6f9;}
*{box-sizing:border-box;margin:0;padding:0}html{scroll-behavior:smooth}
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",Arial,sans-serif;background:var(--bg);color:var(--ink);line-height:1.7;font-size:15px}
.serif{font-family:"Songti SC","STSong","SimSun",serif}
nav{position:fixed;top:0;left:0;right:0;z-index:100;background:rgba(20,41,63,.92);backdrop-filter:blur(8px);border-bottom:1px solid rgba(197,165,114,.25)}
nav .nav-in{max-width:1200px;margin:0 auto;padding:0 24px;height:58px;display:flex;align-items:center;gap:14px}
nav .brand{display:flex;align-items:center;gap:10px;color:#fff;font-weight:600;font-size:15px}
nav .brand img{height:26px}
nav .logo-fb{width:28px;height:28px;border-radius:6px;background:linear-gradient(135deg,var(--gold),var(--gold-d));display:flex;align-items:center;justify-content:center;font-family:"Songti SC",serif;font-weight:700;color:#14293f;font-size:16px}
nav .links{margin-left:auto;display:flex;gap:4px;flex-wrap:wrap}
nav .links a{color:#cdd6e0;text-decoration:none;font-size:13px;padding:7px 12px;border-radius:6px;transition:.18s}
nav .links a:hover{color:#fff;background:rgba(255,255,255,.08)}nav .links a.active{color:var(--gold);background:rgba(197,165,114,.12)}
.nav-toggle{display:none}
.hero{position:relative;color:#fff;padding:150px 24px 90px;text-align:center;background:linear-gradient(135deg,rgba(15,32,51,.93),rgba(30,58,95,.82) 55%,rgba(30,58,95,.74)),url('pic/hero.jpg') center/cover no-repeat;background-color:var(--navy-d)}
.hero::after{content:'';position:absolute;left:0;right:0;bottom:0;height:90px;background:linear-gradient(to bottom,rgba(244,246,249,0),var(--bg))}
.hero .badge{display:inline-block;font-size:12px;letter-spacing:5px;color:var(--gold);border:1px solid rgba(197,165,114,.55);padding:5px 18px;margin-bottom:26px}
.hero h1{font-size:40px;font-weight:700;letter-spacing:3px;margin-bottom:14px;line-height:1.25}
.hero .subtitle{font-size:18px;color:#c8d3df;letter-spacing:2px;margin-bottom:8px}
.hero .account{font-size:13px;color:#8ea2b8;font-family:"SF Mono",Menlo,monospace;margin-bottom:40px}
.hero-stats{display:flex;justify-content:center;flex-wrap:wrap;max-width:880px;margin:0 auto;position:relative;z-index:2}
.hero-stats>div{padding:0 34px;border-right:1px solid rgba(255,255,255,.15)}.hero-stats>div:last-child{border-right:none}
.hero-stats .v{font-size:30px;font-weight:700;font-family:"Songti SC",serif}.hero-stats .v small{font-size:14px;font-weight:400;margin-left:3px;color:#c8d3df}
.hero-stats .l{font-size:12px;color:#9fb1c4;margin-top:6px}
.hero .meta-line{margin-top:34px;font-size:12.5px;color:#8ea2b8;position:relative;z-index:2}
.wrap{max-width:1200px;margin:0 auto;padding:0 24px}
section{padding:54px 0 10px;scroll-margin-top:70px}
.sec-head{margin-bottom:26px}.sec-head .kicker{font-size:12px;letter-spacing:3px;color:var(--gold-d);font-weight:600}
.sec-head h2{font-family:"Songti SC",serif;font-size:27px;color:var(--navy);margin-top:6px;display:flex;align-items:center;gap:14px}
.sec-head h2 .no{font-size:18px;color:#fff;background:var(--navy);width:38px;height:38px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center}
.sec-head p.lead{color:var(--gray);font-size:14.5px;margin-top:10px;max-width:860px}
.banner{height:170px;border-radius:14px;margin-bottom:30px;overflow:hidden;position:relative;display:flex;align-items:center;padding:0 40px;color:#fff;background-color:var(--navy);background-size:cover;background-position:center}
.banner .bc{position:relative;z-index:2}.banner .bc .t{font-family:"Songti SC",serif;font-size:24px;letter-spacing:2px}.banner .bc .s{font-size:13.5px;color:rgba(255,255,255,.82);margin-top:6px;max-width:680px}
.b-fund{background-image:linear-gradient(100deg,rgba(20,41,63,.88) 30%,rgba(30,58,95,.55)),url('pic/fund.jpg')}
.b-income{background-image:linear-gradient(100deg,rgba(4,71,55,.88) 30%,rgba(16,120,90,.5)),url('pic/income.jpg')}
.b-expense{background-image:linear-gradient(100deg,rgba(91,30,30,.88) 30%,rgba(150,50,50,.5)),url('pic/expense.jpg')}
.b-trend{background-image:linear-gradient(100deg,rgba(20,41,63,.88) 30%,rgba(58,86,120,.5)),url('pic/trend.jpg')}
.b-risk{background-image:linear-gradient(100deg,rgba(74,58,35,.9) 30%,rgba(168,136,79,.5)),url('pic/risk.jpg')}
.b-advice{background-image:linear-gradient(100deg,rgba(20,41,63,.88) 30%,rgba(197,165,114,.5)),url('pic/advice.jpg')}
.card{background:#fff;border-radius:12px;padding:24px 26px;box-shadow:0 1px 3px rgba(0,0,0,.05);margin-bottom:20px}
.card .ct{font-size:15px;font-weight:600;color:var(--navy);margin-bottom:16px;padding-bottom:12px;border-bottom:2px solid var(--line);display:flex;align-items:center;gap:10px}
.card .ct::before{content:'';width:3px;height:15px;background:var(--gold)}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:20px}.grid-2 .card{margin-bottom:0}
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:8px}
.kpi{background:#fff;border-radius:12px;padding:20px 22px;box-shadow:0 1px 3px rgba(0,0,0,.05);border-top:3px solid var(--navy)}
.kpi.green{border-top-color:var(--green)}.kpi.red{border-top-color:var(--red)}.kpi.gold{border-top-color:var(--gold)}
.kpi .l{color:var(--gray);font-size:12.5px;margin-bottom:8px}.kpi .v{font-size:25px;font-weight:700;font-family:"SF Mono",Menlo,monospace}.kpi .f{color:#9ca3af;font-size:11.5px;margin-top:6px}
.alert{background:linear-gradient(100deg,#fff7ed,#fff);border:1px solid #f3d9b8;border-left:5px solid var(--gold-d);border-radius:10px;padding:22px 26px;margin:8px 0 24px;display:flex;gap:18px}
.alert .ico{font-size:30px;flex:0 0 auto}.alert h4{color:#9a3412;font-size:15px;margin-bottom:6px}.alert p{color:#7c2d12;font-size:13.5px}.alert b{color:var(--red-d)}
.findings{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.finding{background:#fff;border-radius:10px;padding:16px 18px;box-shadow:0 1px 3px rgba(0,0,0,.04);border-left:3px solid var(--navy);font-size:13.5px}
.finding b{color:var(--navy);display:block;margin-bottom:3px;font-size:14px}
.finding .red{color:var(--red-d);font-weight:600}.finding .green{color:var(--green-d);font-weight:600}.finding .num{font-family:"SF Mono",Menlo,monospace;font-weight:600}
.chart{width:100%;height:380px}.chart-tall{height:440px}.chart-sm{height:320px}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:10px 12px;text-align:left;border-bottom:1px solid #f1f3f5}
th{background:#f9fafb;color:#4b5563;font-weight:600;font-size:11.5px}td.num{font-family:"SF Mono",Menlo,monospace;text-align:right}
td.in,td.pos{color:var(--green-d);font-weight:600}td.out,td.neg{color:var(--red-d);font-weight:600}tbody tr:hover{background:#fafafa}
.astat-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px}
.astat{background:#fef9f3;border:1px solid #f3e8d4;border-radius:10px;padding:18px 16px;text-align:center}
.astat .n{font-size:24px;font-weight:700;color:var(--gold-d);font-family:"SF Mono",Menlo,monospace}.astat .d{font-size:12px;color:var(--gray);margin-top:5px;line-height:1.45}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);border-top:2px solid var(--navy);border-bottom:2px solid var(--navy);padding:16px 0;margin:6px 0 20px}
.metrics>div{text-align:center;border-right:1px solid var(--line);padding:0 10px}.metrics>div:last-child{border-right:none}
.metrics .l{font-size:11.5px;color:var(--gray);margin-bottom:6px}.metrics .v{font-family:"Songti SC",serif;font-size:21px;font-weight:700;color:var(--navy)}.metrics .v small{font-size:12px;font-weight:400;color:var(--gray)}
.conclusion{background:linear-gradient(180deg,#fafaf7,#fff);border:1px solid var(--line);border-radius:12px;padding:24px 28px;margin-bottom:18px}
.conclusion p{color:#374151;margin-bottom:10px;font-size:14px}.conclusion p b{color:var(--navy)}
.advice-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.advice{background:#fff;border-radius:12px;padding:22px 24px;box-shadow:0 1px 3px rgba(0,0,0,.05);border-top:3px solid var(--gold);position:relative}
.advice .tag{display:inline-block;font-size:11px;font-weight:600;padding:2px 9px;border-radius:20px;margin-bottom:10px}
.advice .tag.urgent{background:#fee2e2;color:var(--red-d)}.advice .tag.important{background:#fef3c7;color:#92400e}.advice .tag.strategy{background:#dbeafe;color:#1e40af}.advice .tag.normal{background:#f3f4f6;color:var(--gray)}
.advice h4{font-family:"Songti SC",serif;font-size:17px;color:var(--navy);margin-bottom:8px}.advice p{font-size:13.5px;color:#4b5563}
.advice .no{position:absolute;right:20px;top:16px;font-family:"Songti SC",serif;font-size:34px;color:#eef1f5;font-weight:700}
.note{font-size:12px;color:#8b7355;padding-left:12px;border-left:2px solid #e8dcc4;margin:10px 0 4px;font-style:italic}
.lead-note{font-size:14px;color:#374151;margin-top:4px}.lead-note+.lead-note{margin-top:8px}
footer{background:var(--navy-d);color:#9fb1c4;margin-top:60px;padding:46px 24px 36px;text-align:center}
footer .org{font-family:"Songti SC",serif;font-size:18px;color:#fff}
footer .links2{margin:20px 0 18px;display:flex;gap:14px;justify-content:center;flex-wrap:wrap}
footer .links2 a{color:#cdd6e0;text-decoration:none;font-size:13px;border:1px solid rgba(255,255,255,.2);padding:8px 18px;border-radius:6px}
footer .links2 a:hover{background:rgba(197,165,114,.15);border-color:var(--gold);color:#fff}
footer .fine{font-size:11.5px;color:#67788c;margin-top:8px}
@media(max-width:980px){.grid-2,.findings,.advice-grid{grid-template-columns:1fr}.kpi-grid,.astat-grid{grid-template-columns:repeat(2,1fr)}.metrics{grid-template-columns:repeat(2,1fr);gap:14px 0}.metrics>div:nth-child(2){border-right:none}}
@media(max-width:680px){.hero{padding:120px 18px 70px}.hero h1{font-size:28px}.hero-stats>div{padding:12px 18px;border-right:none}.sec-head h2{font-size:22px}.banner{padding:0 22px;height:140px}nav .links{display:none;position:absolute;top:58px;left:0;right:0;flex-direction:column;background:var(--navy-d);padding:8px}nav .links.open{display:flex}.nav-toggle{display:block;margin-left:auto;background:none;border:1px solid rgba(255,255,255,.3);color:#fff;border-radius:6px;padding:6px 12px;cursor:pointer}}
</style></head><body>
<nav><div class="nav-in"><div class="brand">
<img src="pic/logo.png" alt="" onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
<span class="logo-fb" style="display:none">__LOGOCH__</span><span>__NAME__</span></div>
<button class="nav-toggle" onclick="document.getElementById('nl').classList.toggle('open')">☰</button>
<div class="links" id="nl">
<a href="#summary">执行摘要</a><a href="#overview">资金总览</a><a href="#income">收入结构</a>
<a href="#expense">支出结构</a><a href="#trend">趋势拐点</a><a href="#risk">风险审视</a><a href="#advice">结论建议</a></div>
</div></nav>
<header class="hero"><div class="badge">FINANCIAL ANALYSIS REPORT</div>
<h1 class="serif">__NAME__</h1><div class="subtitle">__SUBTITLE__</div>
<div class="account">账户 __ACCOUNT__ · __RANGE__</div>
<div class="hero-stats">
<div><div class="v">__TURNOVER__</div><div class="l">累计资金流转</div></div>
<div><div class="v">__NET__</div><div class="l">累计净流入</div></div>
<div><div class="v">__ENDBAL__</div><div class="l">期末账户余额</div></div>
<div><div class="v">__COUNT__<small>笔</small></div><div class="l">有效交易记录</div></div></div>
<div class="meta-line">统计区间 __RANGE__（__SPAN__）　|　报告日期 __REPORTDATE__　|　数据经合并去重处理</div></header>
<main class="wrap">
<section id="summary"><div class="sec-head"><div class="kicker">EXECUTIVE SUMMARY</div>
<h2 class="serif"><span class="no">〇</span>执行摘要</h2><p class="lead">__EXEC__</p></div>
__ALERT__
<div class="kpi-grid">
<div class="kpi green"><div class="l">累计收入（贷方）</div><div class="v">¥__TOTALIN__万</div><div class="f">__INCNT__ 笔进账</div></div>
<div class="kpi red"><div class="l">累计支出（借方）</div><div class="v">¥__TOTALOUT__万</div><div class="f">__OUTCNT__ 笔出账</div></div>
<div class="kpi"><div class="l">累计净流入</div><div class="v">__NET__</div><div class="f">__SUBJECT_TYPE__</div></div>
<div class="kpi gold"><div class="l">期末账户余额</div><div class="v">¥__ENDBAL__</div><div class="f">截至 __RANGE__</div></div></div>
<div class="card" style="margin-top:20px"><div class="ct">核心发现</div><div class="findings">__FINDINGS__</div></div></section>
<section id="overview"><div class="banner b-fund"><div class="bc"><div class="t serif">资金规模与流动性总览</div><div class="s">收支结构、年度与月度走势、账户余额水位。</div></div></div>
<div class="sec-head"><div class="kicker">PART 01 · OVERVIEW</div><h2 class="serif"><span class="no">壹</span>资金规模与流动性</h2></div>
<div class="metrics" id="m-ov"></div>
<div class="card"><div class="ct">年度收支与净额趋势</div><div id="c-year" class="chart chart-tall"></div></div>
<div class="card"><div class="ct">月度收支走势与账户余额（可拖动缩放）</div><div id="c-month" class="chart chart-tall"></div></div>
<div class="card" id="ov-note-box" style="display:none"><div class="ct">解读</div><p class="lead-note">__OVERVIEW_NOTE__</p></div></section>
<section id="income"><div class="banner b-income"><div class="bc"><div class="t serif">收入结构分析</div><div class="s">资金来源的属性构成、用途分布与主要来源。</div></div></div>
<div class="sec-head"><div class="kicker">PART 02 · INCOME</div><h2 class="serif"><span class="no">贰</span>收入结构分析</h2></div>
<div class="grid-2" style="margin-bottom:20px"><div class="card"><div class="ct">收入对手方属性分布</div><div id="c-prop-in" class="chart chart-sm"></div></div>
<div class="card"><div class="ct">收入资金用途分布</div><div id="c-cat-in" class="chart chart-sm"></div></div></div>
<div class="card"><div class="ct">主要资金来源 Top 15</div><div id="c-top-in" class="chart chart-tall"></div></div>
<div class="card" id="in-note-box" style="display:none"><div class="ct">解读</div><p class="lead-note">__INCOME_NOTE__</p></div></section>
<section id="expense"><div class="banner b-expense"><div class="bc"><div class="t serif">支出结构分析</div><div class="s">资金去向的属性构成、用途分布与主要去向。</div></div></div>
<div class="sec-head"><div class="kicker">PART 03 · EXPENSE</div><h2 class="serif"><span class="no">叁</span>支出结构分析</h2></div>
<div class="grid-2" style="margin-bottom:20px"><div class="card"><div class="ct">支出对手方属性分布</div><div id="c-prop-out" class="chart chart-sm"></div></div>
<div class="card"><div class="ct">支出资金用途分布</div><div id="c-cat-out" class="chart chart-sm"></div></div></div>
<div class="card"><div class="ct">主要支出去向 Top 15</div><div id="c-top-out" class="chart chart-tall"></div></div>
<div class="card" id="out-note-box" style="display:none"><div class="ct">解读</div><p class="lead-note">__EXPENSE_NOTE__</p></div></section>
<section id="trend"><div class="banner b-trend"><div class="bc"><div class="t serif">年度趋势与季节性</div><div class="s">阶段演变、拐点识别与资金的季节性节奏。</div></div></div>
<div class="sec-head"><div class="kicker">PART 04 · TREND</div><h2 class="serif"><span class="no">肆</span>趋势、拐点与季节性</h2></div>
<div class="grid-2" style="margin-bottom:20px"><div class="card"><div class="ct">季度收支与净额</div><div id="c-quarter" class="chart"></div></div>
<div class="card"><div class="ct">月度季节性（各月历史均值）</div><div id="c-season" class="chart"></div></div></div>
<div class="advice-grid">__TREND__</div>
<p class="note" style="margin-top:14px">__TREND_NOTE__</p></section>
<section id="risk"><div class="banner b-risk"><div class="bc"><div class="t serif">风险与异常审视</div><div class="s">大额、整数额、周末、Benford 等多视角扫描。</div></div></div>
<div class="sec-head"><div class="kicker">PART 05 · RISK & AUDIT</div><h2 class="serif"><span class="no">伍</span>风险与异常审视</h2></div>
<div class="astat-grid" id="astat"></div>
<div class="grid-2" style="margin-bottom:20px">
<div class="card"><div class="ct">Benford 首位数字检验</div><div id="c-benford" class="chart chart-sm"></div></div>
<div class="card"><div class="ct">单笔金额区间分布</div><div id="c-dist" class="chart chart-sm"></div></div></div>
<div class="card"><div class="ct">大额交易明细 Top 15</div><table><thead><tr><th>日期</th><th>方向</th><th>对手方</th><th>摘要/备注</th><th style="text-align:right">金额（元）</th></tr></thead><tbody id="t-big"></tbody></table></div>
<div class="card" id="risk-note-box" style="display:none"><div class="ct">结论</div><p class="lead-note">__RISK_NOTE__</p></div></section>
<section id="advice"><div class="banner b-advice"><div class="bc"><div class="t serif">结论与改进建议</div><div class="s">综合判断与可执行的改进建议。</div></div></div>
<div class="sec-head"><div class="kicker">PART 06 · CONCLUSION</div><h2 class="serif"><span class="no">陆</span>结论与改进建议</h2></div>
<div class="conclusion" style="margin-bottom:24px"><p>__CONCLUSION__</p></div>
<div class="advice-grid">__ADVICE__</div></section>
</main>
<footer><div class="org">__NAME__</div><div style="font-size:13px;margin-top:4px">__SUBTITLE__ · 报告日期 __REPORTDATE__</div>
<div class="links2"><a href="charts.html">📊 图表分析版</a><a href="report.html">📄 完整文字版</a></div>
<div class="fine">数据来源：账户流水，经合并去重处理 · 本报告基于银行流水单一信息源，不构成正式审计意见</div></footer>
<script>
const D=__DATA__;
const C={navy:'#1e3a5f',gold:'#c5a572',green:'#10b981',red:'#ef4444',blue:'#3b82f6',gray:'#9ca3af'};
const ts={fontFamily:'-apple-system,"PingFang SC","Microsoft YaHei",Arial',fontSize:12};
const insts=[];function chart(id){const el=document.getElementById(id);if(!el)return null;const c=echarts.init(el);insts.push(c);return c;}
function money(v){if(v==null)return '-';const a=Math.abs(v);if(a>=1e8)return (v/1e8).toFixed(2)+'亿';if(a>=1e4)return (v/1e4).toFixed(1)+'万';return Math.round(v).toLocaleString();}
// 解读框：有内容才显示
[['ov-note-box','__OVERVIEW_NOTE__'],['in-note-box','__INCOME_NOTE__'],['out-note-box','__EXPENSE_NOTE__'],['risk-note-box','__RISK_NOTE__']].forEach(([id,v])=>{if(v&&v.trim()){const b=document.getElementById(id);if(b)b.style.display='';}});
// 总览指标
const ov=D.overview,m=D.meta;
document.getElementById('m-ov').innerHTML=[
 ['累计资金流转量',money(ov.turnover)],['账户活跃天数',(m.span_days||'-')+' 天'],
 ['单笔收入均值',money(ov.avg_in_amt)],['单笔支出均值',money(ov.avg_out_amt)]
].map(([l,v])=>`<div><div class="l">${l}</div><div class="v">${v}</div></div>`).join('');
// 异常统计
const an=D.anomaly;
document.getElementById('astat').innerHTML=[
 [an.big_count,'大额交易<br>≥'+money(an.big_threshold)],[an.round_count,'整万元交易<br>疑似定期划款'],
 [an.weekend_count,'周末发生交易'],[an.freq_groups.length>=10?'10+':an.freq_groups.length,'同日同对手 ≥3 笔<br>（展示前 10 组）']
].map(([n,d])=>`<div class="astat"><div class="n">${n}</div><div class="d">${d}</div></div>`).join('');
// 年度
chart('c-year').setOption({textStyle:ts,tooltip:{trigger:'axis',axisPointer:{type:'shadow'},formatter:p=>{let s=p[0].name+'<br>';p.forEach(it=>{if(it.value!=null)s+=`<span style="color:${it.color}">●</span> ${it.seriesName}: <b>¥${money(it.value)}</b><br>`;});return s;}},legend:{data:['收入','支出','净流入'],top:0},grid:{left:62,right:62,top:46,bottom:28},xAxis:{type:'category',data:D.years},yAxis:[{type:'value',axisLabel:{formatter:v=>money(v)},splitLine:{lineStyle:{color:'#f1f3f5'}}},{type:'value',axisLabel:{formatter:v=>money(v)},splitLine:{show:false}}],series:[{name:'收入',type:'bar',data:D.year_in,itemStyle:{color:C.green,borderRadius:[4,4,0,0]},barWidth:24},{name:'支出',type:'bar',data:D.year_out,itemStyle:{color:C.red,borderRadius:[4,4,0,0]},barWidth:24},{name:'净流入',type:'line',yAxisIndex:1,data:D.year_net,symbol:'circle',symbolSize:9,lineStyle:{color:C.gold,width:3},itemStyle:{color:C.gold},markLine:{silent:true,data:[{yAxis:0}],lineStyle:{color:'#cbd5e1',type:'dashed'}}}]});
// 月度
chart('c-month').setOption({textStyle:ts,tooltip:{trigger:'axis',formatter:p=>{let s=p[0].axisValue+'<br>';p.forEach(it=>{if(it.value!=null)s+=`<span style="color:${it.color}">●</span> ${it.seriesName}: <b>¥${money(it.value)}</b><br>`;});return s;}},legend:{data:['月收入','月支出','账户余额'],top:0},grid:{left:62,right:62,top:46,bottom:64},dataZoom:[{type:'inside'},{type:'slider',height:18,bottom:10}],xAxis:{type:'category',data:D.months,boundaryGap:false},yAxis:[{type:'value',axisLabel:{formatter:v=>money(v)},splitLine:{lineStyle:{color:'#f1f3f5'}}},{type:'value',axisLabel:{formatter:v=>money(v)},splitLine:{show:false}}],series:[{name:'月收入',type:'line',data:D.month_in,smooth:true,symbol:'none',areaStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(16,185,129,.5)'},{offset:1,color:'rgba(16,185,129,.05)'}])},lineStyle:{color:C.green,width:2},itemStyle:{color:C.green}},{name:'月支出',type:'line',data:D.month_out,smooth:true,symbol:'none',areaStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(239,68,68,.5)'},{offset:1,color:'rgba(239,68,68,.05)'}])},lineStyle:{color:C.red,width:2},itemStyle:{color:C.red}},{name:'账户余额',type:'line',yAxisIndex:1,data:D.month_bal,connectNulls:true,smooth:true,symbol:'none',lineStyle:{color:C.navy,width:2,type:'dashed'}}]});
function propPie(id,arr){if(!arr||!arr.length)return;chart(id).setOption({textStyle:ts,tooltip:{trigger:'item',formatter:p=>`${p.name}<br>金额: <b>¥${money(p.value)}</b><br>笔数: ${p.data.cnt} · 单位: ${p.data.np}<br>占比: ${p.percent}%`},legend:{orient:'vertical',right:8,top:'middle',textStyle:{fontSize:12}},series:[{type:'pie',radius:['46%','72%'],center:['36%','52%'],padAngle:2,itemStyle:{borderRadius:5},label:{formatter:'{d}%',fontSize:11},data:arr.map(x=>({name:x.cls,value:x.sum,cnt:x.cnt,np:x.n_parties})),color:[C.navy,C.gold,C.green,C.blue,'#8b5cf6']}]});}
propPie('c-prop-in',D.prop_in);propPie('c-prop-out',D.prop_out);
function catPie(id,arr){if(!arr||!arr.length)return;chart(id).setOption({textStyle:ts,tooltip:{trigger:'item',formatter:p=>`${p.name}<br>金额: <b>¥${money(p.value)}</b><br>笔数: ${p.data.cnt}<br>占比: ${p.percent}%`},legend:{type:'scroll',orient:'vertical',right:6,top:'middle',textStyle:{fontSize:11}},series:[{type:'pie',radius:['42%','68%'],center:['34%','52%'],padAngle:2,itemStyle:{borderRadius:4},label:{formatter:'{d}%',fontSize:10},data:arr.map(x=>({name:x.name,value:x.sum,cnt:x.cnt})),color:['#1e3a5f','#c5a572','#10b981','#3b82f6','#8b5cf6','#ec4899','#f59e0b','#06b6d4','#84cc16','#64748b']}]});}
catPie('c-cat-in',D.cat_in);catPie('c-cat-out',D.cat_out);
function topBar(id,arr,color){if(!arr||!arr.length)return;const s=[...arr].sort((a,b)=>a.sum-b.sum);chart(id).setOption({textStyle:ts,tooltip:{trigger:'axis',axisPointer:{type:'shadow'},formatter:p=>`${p[0].name}<br>金额: <b>¥${money(p[0].value)}</b><br>笔数: ${p[0].data.cnt}`},grid:{left:185,right:90,top:20,bottom:20},xAxis:{type:'value',axisLabel:{formatter:v=>money(v)},splitLine:{lineStyle:{color:'#f1f3f5'}}},yAxis:{type:'category',data:s.map(x=>x.name.length>16?x.name.slice(0,15)+'…':x.name),axisLabel:{fontSize:11,color:'#4b5563'}},series:[{type:'bar',data:s.map(x=>({value:x.sum,cnt:x.cnt})),itemStyle:{color:color,borderRadius:[0,3,3,0]},label:{show:true,position:'right',formatter:p=>'¥'+money(p.value),color:'#4b5563',fontSize:11}}]});}
topBar('c-top-in',D.top_in,C.green);topBar('c-top-out',D.top_out,C.red);
if(D.quarter&&D.quarter.length)chart('c-quarter').setOption({textStyle:ts,tooltip:{trigger:'axis',axisPointer:{type:'shadow'},formatter:p=>{let s=p[0].axisValue+'<br>';p.forEach(it=>{if(it.value!=null)s+=`<span style="color:${it.color}">●</span> ${it.seriesName}: <b>¥${money(it.value)}</b><br>`;});return s;}},legend:{data:['收入','支出','净额'],top:0},grid:{left:55,right:20,top:42,bottom:60},dataZoom:[{type:'inside'},{type:'slider',height:16,bottom:8}],xAxis:{type:'category',data:D.quarter.map(q=>q.q),axisLabel:{rotate:45,fontSize:10}},yAxis:{type:'value',axisLabel:{formatter:v=>money(v)},splitLine:{lineStyle:{color:'#f1f3f5'}}},series:[{name:'收入',type:'bar',data:D.quarter.map(q=>q.in),itemStyle:{color:C.green},barMaxWidth:14},{name:'支出',type:'bar',data:D.quarter.map(q=>q.out),itemStyle:{color:C.red},barMaxWidth:14},{name:'净额',type:'line',data:D.quarter.map(q=>+(q.in-q.out).toFixed(2)),symbol:'circle',symbolSize:6,lineStyle:{color:C.gold,width:2},itemStyle:{color:C.gold}}]});
if(D.season&&D.season.length)chart('c-season').setOption({textStyle:ts,tooltip:{trigger:'axis',formatter:p=>{let s=p[0].axisValue+' 月<br>';p.forEach(it=>{s+=`<span style="color:${it.color}">●</span> ${it.seriesName}: <b>¥${money(it.value)}</b><br>`;});return s;}},legend:{data:['平均收入','平均支出','平均净额'],top:0},grid:{left:55,right:20,top:42,bottom:30},xAxis:{type:'category',data:D.season.map(s=>s.month)},yAxis:{type:'value',axisLabel:{formatter:v=>money(v)},splitLine:{lineStyle:{color:'#f1f3f5'}}},series:[{name:'平均收入',type:'bar',data:D.season.map(s=>+s.in_avg.toFixed(0)),itemStyle:{color:'rgba(16,185,129,.85)',borderRadius:[3,3,0,0]},barMaxWidth:16},{name:'平均支出',type:'bar',data:D.season.map(s=>+s.out_avg.toFixed(0)),itemStyle:{color:'rgba(239,68,68,.85)',borderRadius:[3,3,0,0]},barMaxWidth:16},{name:'平均净额',type:'line',data:D.season.map(s=>+(s.in_avg-s.out_avg).toFixed(0)),smooth:true,symbol:'circle',symbolSize:6,lineStyle:{color:C.gold,width:2},itemStyle:{color:C.gold},markLine:{silent:true,data:[{yAxis:0}],lineStyle:{color:'#cbd5e1',type:'dashed'}}}]});
if(D.benford){const bf=Object.keys(D.benford.actual);chart('c-benford').setOption({textStyle:ts,tooltip:{trigger:'axis',axisPointer:{type:'shadow'},valueFormatter:v=>v.toFixed(1)+'%'},legend:{data:['实际比例','Benford 预期'],top:0},grid:{left:44,right:16,top:42,bottom:28},xAxis:{type:'category',data:bf},yAxis:{type:'value',axisLabel:{formatter:'{value}%'},splitLine:{lineStyle:{color:'#f1f3f5'}}},series:[{name:'实际比例',type:'bar',data:bf.map(k=>+D.benford.actual[k].toFixed(2)),itemStyle:{color:C.navy,borderRadius:[3,3,0,0]},barMaxWidth:18},{name:'Benford 预期',type:'line',data:bf.map(k=>+D.benford.expected[k].toFixed(2)),symbol:'circle',symbolSize:6,lineStyle:{color:C.gold,width:2},itemStyle:{color:C.gold}}]});}
if(D.dist){const dl=['<1k','1k-1w','1w-5w','5w-20w','20w-100w','>100w'];chart('c-dist').setOption({textStyle:ts,tooltip:{trigger:'axis',axisPointer:{type:'shadow'},formatter:p=>{let s=p[0].axisValue+'<br>';p.forEach(it=>{s+=`<span style="color:${it.color}">●</span> ${it.seriesName}: <b>${Math.abs(it.value)} 笔</b><br>`;});return s;}},legend:{data:['收入笔数','支出笔数'],top:0},grid:{left:70,right:30,top:42,bottom:24},xAxis:{type:'value',axisLabel:{formatter:v=>Math.abs(v)},splitLine:{lineStyle:{color:'#f1f3f5'}}},yAxis:{type:'category',data:dl},series:[{name:'收入笔数',type:'bar',stack:'t',data:dl.map(k=>D.dist.in_buck[k]),itemStyle:{color:C.green},label:{show:true,position:'right',fontSize:10,formatter:p=>p.value||''}},{name:'支出笔数',type:'bar',stack:'t',data:dl.map(k=>-D.dist.out_buck[k]),itemStyle:{color:C.red},label:{show:true,position:'left',fontSize:10,formatter:p=>Math.abs(p.value)||''}}]});}
const tb=document.getElementById('t-big');const DCIN=D.meta.dc_in||'贷';an.big_top.slice(0,15).forEach(r=>{const cls=r.sign==DCIN?'in':'out',arrow=r.sign==DCIN?'← 收':'→ 付';tb.insertAdjacentHTML('beforeend',`<tr><td>${r.date}</td><td class="${cls}">${arrow}</td><td>${r.cp||''}</td><td style="color:#6b7280">${r.memo||''}</td><td class="num ${cls}">¥${r.amt.toLocaleString('zh-CN',{minimumFractionDigits:2})}</td></tr>`);});
window.addEventListener('resize',()=>insts.forEach(c=>c.resize()));
const secs=[...document.querySelectorAll('section[id]')],navas=[...document.querySelectorAll('#nl a')];
function onScroll(){let cur='';secs.forEach(s=>{if(window.scrollY>=s.offsetTop-90)cur=s.id;});navas.forEach(a=>a.classList.toggle('active',a.getAttribute('href')==='#'+cur));}
window.addEventListener('scroll',onScroll);onScroll();
navas.forEach(a=>a.addEventListener('click',()=>document.getElementById('nl').classList.remove('open')));
</script></body></html>'''

# ============================================================= 图表版（简版，复用网站图表区）
TPL_CHARTS = r'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>__NAME__ · 银行流水分析（图表版）</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script><style>
*{box-sizing:border-box;margin:0;padding:0}body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",Arial,sans-serif;background:#f4f6f9;color:#1f2937;line-height:1.6}
.container{max-width:1280px;margin:0 auto;padding:32px 24px 64px}
.header{background:linear-gradient(135deg,#1e3a5f,#2d5078);color:#fff;padding:36px 40px;border-radius:12px;margin-bottom:24px}
.header h1{font-size:26px;font-weight:600;margin-bottom:6px}.header .sub{font-size:13px;opacity:.8}
.header .meta-row{display:flex;gap:32px;margin-top:20px;padding-top:20px;border-top:1px solid rgba(255,255,255,.15);font-size:13px;flex-wrap:wrap}.header .meta-row b{color:#c5a572;margin-right:6px}
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}
.kpi-card{background:#fff;border-radius:10px;padding:20px 22px;box-shadow:0 1px 3px rgba(0,0,0,.04);border-left:4px solid #1e3a5f}
.kpi-card.green{border-left-color:#10b981}.kpi-card.red{border-left-color:#ef4444}.kpi-card.amber{border-left-color:#c5a572}.kpi-card.blue{border-left-color:#3b82f6}
.kpi-card .label{color:#6b7280;font-size:12px;margin-bottom:8px}.kpi-card .value{font-size:24px;font-weight:700;font-family:"SF Mono",Menlo,monospace}.kpi-card .footnote{color:#9ca3af;font-size:11px;margin-top:6px}
.section{background:#fff;border-radius:10px;padding:24px 28px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,.04)}
.section-title{font-size:15px;font-weight:600;color:#1e3a5f;padding-bottom:12px;margin-bottom:18px;border-bottom:2px solid #e5e7eb;display:flex;align-items:center;gap:10px}
.section-title::before{content:'';width:3px;height:16px;background:#c5a572;display:inline-block}
.chart{width:100%;height:380px}.chart-tall{height:440px}.chart-sm{height:320px}.chart-row{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.summary{background:linear-gradient(135deg,#fafafa,#fff);border-left:4px solid #c5a572;padding:28px 32px;border-radius:8px}
.summary h2{font-size:16px;color:#1e3a5f;margin-bottom:16px}.summary p{color:#374151;margin-bottom:12px;font-size:14px;line-height:1.8}
.footer{text-align:center;color:#9ca3af;font-size:12px;margin-top:30px}
@media(max-width:900px){.kpi-grid{grid-template-columns:repeat(2,1fr)}.chart-row{grid-template-columns:1fr}}
</style></head><body><div class="container">
<div class="header"><h1>__NAME__ · 银行流水分析报告</h1><div class="sub">账户 __ACCOUNT__ · 图表分析版</div>
<div class="meta-row"><span><b>统计区间</b>__RANGE__</span><span><b>跨度</b>__SPAN__</span><span><b>有效记录</b>__COUNT__ 笔</span><span><b>报告日期</b>__REPORTDATE__</span></div></div>
<div class="kpi-grid">
<div class="kpi-card green"><div class="label">累计收入</div><div class="value">¥ __TOTALIN__ 万</div><div class="footnote">__INCNT__ 笔进账</div></div>
<div class="kpi-card red"><div class="label">累计支出</div><div class="value">¥ __TOTALOUT__ 万</div><div class="footnote">__OUTCNT__ 笔出账</div></div>
<div class="kpi-card blue"><div class="label">净流入/流出</div><div class="value">__NET__</div><div class="footnote">__SPAN__ 累计</div></div>
<div class="kpi-card amber"><div class="label">期末账户余额</div><div class="value">¥ __ENDBAL__</div><div class="footnote">截至期末</div></div></div>
<div class="section"><div class="section-title">一、年度收支趋势</div><div id="c-year" class="chart chart-tall"></div></div>
<div class="section"><div class="section-title">二、月度收支与账户余额走势</div><div id="c-month" class="chart chart-tall"></div></div>
<div class="section"><div class="section-title">三、对手方画像 · 收入与支出 Top 15</div><div class="chart-row"><div id="c-top-in" class="chart chart-tall"></div><div id="c-top-out" class="chart chart-tall"></div></div></div>
<div class="section"><div class="section-title">四、资金用途分类</div><div class="chart-row"><div id="c-cat-in" class="chart"></div><div id="c-cat-out" class="chart"></div></div></div>
<div class="section"><div class="section-title">五、审计视角 · 异常交易识别</div><div id="c-dist" class="chart chart-sm"></div></div>
<div class="summary"><h2>📌 总结与建议</h2><p>__EXEC__</p>__SUMMARY_FINDINGS__</div>
<div class="footer">数据来源：__NAME__ 账户流水 · 经合并去重处理 · 报告自动生成</div></div>
<script>
const D=__DATA__;const C={navy:'#1e3a5f',gold:'#c5a572',green:'#10b981',red:'#ef4444',blue:'#3b82f6',gray:'#9ca3af'};
const ts={fontFamily:'-apple-system,"PingFang SC","Microsoft YaHei",Arial',fontSize:12};const insts=[];
function chart(id){const el=document.getElementById(id);if(!el)return null;const c=echarts.init(el);insts.push(c);return c;}
function money(v){if(v==null)return '-';const a=Math.abs(v);if(a>=1e8)return (v/1e8).toFixed(2)+'亿';if(a>=1e4)return (v/1e4).toFixed(1)+'万';return Math.round(v).toLocaleString();}
chart('c-year').setOption({textStyle:ts,tooltip:{trigger:'axis',axisPointer:{type:'shadow'}},legend:{data:['收入','支出','净流入'],top:0},grid:{left:62,right:62,top:46,bottom:28},xAxis:{type:'category',data:D.years},yAxis:[{type:'value',axisLabel:{formatter:v=>money(v)}},{type:'value',axisLabel:{formatter:v=>money(v)},splitLine:{show:false}}],series:[{name:'收入',type:'bar',data:D.year_in,itemStyle:{color:C.green,borderRadius:[4,4,0,0]},barWidth:24},{name:'支出',type:'bar',data:D.year_out,itemStyle:{color:C.red,borderRadius:[4,4,0,0]},barWidth:24},{name:'净流入',type:'line',yAxisIndex:1,data:D.year_net,symbol:'circle',symbolSize:9,lineStyle:{color:C.gold,width:3},itemStyle:{color:C.gold}}]});
chart('c-month').setOption({textStyle:ts,tooltip:{trigger:'axis'},legend:{data:['月收入','月支出','账户余额'],top:0},grid:{left:62,right:62,top:46,bottom:64},dataZoom:[{type:'inside'},{type:'slider',height:18,bottom:10}],xAxis:{type:'category',data:D.months,boundaryGap:false},yAxis:[{type:'value',axisLabel:{formatter:v=>money(v)}},{type:'value',axisLabel:{formatter:v=>money(v)},splitLine:{show:false}}],series:[{name:'月收入',type:'line',data:D.month_in,smooth:true,symbol:'none',areaStyle:{color:'rgba(16,185,129,.25)'},lineStyle:{color:C.green,width:2}},{name:'月支出',type:'line',data:D.month_out,smooth:true,symbol:'none',areaStyle:{color:'rgba(239,68,68,.25)'},lineStyle:{color:C.red,width:2}},{name:'账户余额',type:'line',yAxisIndex:1,data:D.month_bal,connectNulls:true,smooth:true,symbol:'none',lineStyle:{color:C.navy,width:2,type:'dashed'}}]});
function topBar(id,arr,color){if(!arr||!arr.length)return;const s=[...arr].sort((a,b)=>a.sum-b.sum);chart(id).setOption({textStyle:ts,title:{text:id.includes('in')?'收入来源 Top 15':'支出去向 Top 15',left:'center',textStyle:{fontSize:14,color:C.navy}},tooltip:{trigger:'axis',axisPointer:{type:'shadow'},formatter:p=>`${p[0].name}<br>¥${money(p[0].value)} · ${p[0].data.cnt}笔`},grid:{left:175,right:80,top:46,bottom:20},xAxis:{type:'value',axisLabel:{formatter:v=>money(v)}},yAxis:{type:'category',data:s.map(x=>x.name.length>15?x.name.slice(0,14)+'…':x.name),axisLabel:{fontSize:11}},series:[{type:'bar',data:s.map(x=>({value:x.sum,cnt:x.cnt})),itemStyle:{color:color,borderRadius:[0,3,3,0]},label:{show:true,position:'right',formatter:p=>'¥'+money(p.value),fontSize:11}}]});}
topBar('c-top-in',D.top_in,C.green);topBar('c-top-out',D.top_out,C.red);
function catPie(id,arr,title){if(!arr||!arr.length)return;chart(id).setOption({textStyle:ts,title:{text:title,left:'center',textStyle:{fontSize:14,color:C.navy}},tooltip:{trigger:'item',formatter:p=>`${p.name}<br>¥${money(p.value)} · ${p.percent}%`},legend:{type:'scroll',orient:'vertical',right:6,top:'middle',textStyle:{fontSize:11}},series:[{type:'pie',radius:['42%','68%'],center:['36%','55%'],padAngle:2,itemStyle:{borderRadius:4},label:{formatter:'{d}%',fontSize:10},data:arr.map(x=>({name:x.name,value:x.sum})),color:['#1e3a5f','#c5a572','#10b981','#3b82f6','#8b5cf6','#ec4899','#f59e0b','#06b6d4','#84cc16','#64748b']}]});}
catPie('c-cat-in',D.cat_in,'收入用途分布');catPie('c-cat-out',D.cat_out,'支出用途分布');
if(D.dist){const dl=['<1k','1k-1w','1w-5w','5w-20w','20w-100w','>100w'];chart('c-dist').setOption({textStyle:ts,tooltip:{trigger:'axis',axisPointer:{type:'shadow'},formatter:p=>{let s=p[0].axisValue+'<br>';p.forEach(it=>{s+=`${it.seriesName}: ${Math.abs(it.value)} 笔<br>`;});return s;}},legend:{data:['收入笔数','支出笔数'],top:0},grid:{left:70,right:30,top:42,bottom:24},xAxis:{type:'value',axisLabel:{formatter:v=>Math.abs(v)}},yAxis:{type:'category',data:dl},series:[{name:'收入笔数',type:'bar',stack:'t',data:dl.map(k=>D.dist.in_buck[k]),itemStyle:{color:C.green}},{name:'支出笔数',type:'bar',stack:'t',data:dl.map(k=>-D.dist.out_buck[k]),itemStyle:{color:C.red}}]});}
window.addEventListener('resize',()=>insts.forEach(c=>c.resize()));
</script></body></html>'''

# ============================================================= 文字版（数据表格 + narrative）
def table(headers, rows, foot=None):
    h = ''.join(f'<th class="num">{x}</th>' if i else f'<th>{x}</th>' for i, x in enumerate(headers))
    body = ''
    for r in rows:
        body += '<tr>' + ''.join(f'<td class="num">{c}</td>' if i else f'<td>{c}</td>' for i, c in enumerate(r)) + '</tr>'
    f = f'<tr class="total">{"".join(f"<td class=num>{c}</td>" if i else f"<td>{c}</td>" for i,c in enumerate(foot))}</tr>' if foot else ''
    return f'<table><thead><tr>{h}</tr></thead><tbody>{body}{f}</tbody></table>'

def fmt(v): return f'{v:,.2f}'
def report_tables():
    OVr = D['overview']
    t_year = table(['年度','收入','支出','净额','笔数'],
        [[y, fmt(D['year_in'][i]), fmt(D['year_out'][i]), fmt(D['year_net'][i]), D['year_cnt'][i]] for i, y in enumerate(D['years'])],
        ['合计', fmt(OVr['total_in']), fmt(OVr['total_out']), fmt(OVr['net']), D['meta']['total_count']])
    t_pin = table(['对手方类型','金额','占比','笔数','单位数'],
        [[p['cls'], fmt(p['sum']), f"{p['sum']/OVr['total_in']*100:.1f}%", p['cnt'], p['n_parties']] for p in D['prop_in']])
    t_pout = table(['对手方类型','金额','占比','笔数','单位数'],
        [[p['cls'], fmt(p['sum']), f"{p['sum']/OVr['total_out']*100:.1f}%", p['cnt'], p['n_parties']] for p in D['prop_out']])
    t_tin = table(['#','资金来源','累计金额','笔数'],
        [[i+1, r['name'], fmt(r['sum']), r['cnt']] for i, r in enumerate(D['top_in'])])
    t_tout = table(['#','支出去向','累计金额','笔数'],
        [[i+1, r['name'], fmt(r['sum']), r['cnt']] for i, r in enumerate(D['top_out'])])
    cc = D['conc']
    t_conc = table(['指标','收入端','支出端'],
        [['HHI 指数', cc['hhi_in'], cc['hhi_out']],['CR3', f"{cc['cr3_in']}%", f"{cc['cr3_out']}%"],
         ['CR5', f"{cc['cr5_in']}%", f"{cc['cr5_out']}%"],['CR10', f"{cc['cr10_in']}%", f"{cc['cr10_out']}%"],
         ['对手方总数', cc['n_in_parties'], cc['n_out_parties']]])
    bf = D['benford']
    t_bf = table(['首位','实际比例','Benford 预期','偏差(pp)'],
        [[d, f"{bf['actual'][str(d)]:.1f}%", f"{bf['expected'][str(d)]:.1f}%", f"{bf['actual'][str(d)]-bf['expected'][str(d)]:+.1f}"] for d in range(1, 10)])
    an = D['anomaly']
    t_big = table(['#','日期','方向','对手方','摘要','金额'],
        [[i+1, r['date'], '收' if r['sign'] in ('贷', D['meta'].get('dc_in','贷')) else '付', r['cp'], r['memo'] or '', fmt(r['amt'])] for i, r in enumerate(an['big_top'][:15])])
    return dict(year=t_year, pin=t_pin, pout=t_pout, tin=t_tin, tout=t_tout, conc=t_conc, bf=t_bf, big=t_big,
                chi2=bf['chi2'], hhi_in=cc['hhi_in'], hhi_out=cc['hhi_out'],
                big_count=an['big_count'], round_count=an['round_count'], weekend_count=an['weekend_count'])

def report_advice():
    out = ''
    for i, a in enumerate(N.get('advice', []), 1):
        out += f'<div class="conclusion"><h3>建议{["一","二","三","四","五","六","七","八"][i-1] if i<=8 else i}：{a.get("h","")}（{a.get("tag","")}）</h3><p>{a.get("p","")}</p></div>'
    return out
def report_trend():
    return ''.join(f'<p><b>{t.get("t","")}</b>{t.get("d","")}</p>' for t in N.get('trend', []))
def report_findings():
    return '<ul>' + ''.join(f'<li><b>{f.get("t","")}</b>：{f.get("d","")}</li>' for f in N.get('findings', [])) + '</ul>'

TPL_REPORT = r'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>__NAME__ · 财务分析报告（完整文字版）</title><style>
*{box-sizing:border-box;margin:0;padding:0}body{font-family:"Songti SC","STSong",-apple-system,"PingFang SC",serif;background:#f5f3ee;color:#1a1a1a;line-height:1.85;font-size:15px}
.report{max-width:880px;margin:0 auto;background:#fefcf7;padding:60px 70px 80px;box-shadow:0 2px 20px rgba(0,0,0,.06)}
.cover{text-align:center;padding:50px 0 60px;border-bottom:3px double #5a4a3a;margin-bottom:44px}
.cover .badge{display:inline-block;font-size:11px;letter-spacing:4px;color:#8b7355;padding:4px 16px;border:1px solid #c5a572;margin-bottom:24px}
.cover h1{font-size:32px;font-weight:700;color:#2c1810;letter-spacing:4px;margin-bottom:16px}
.cover .subtitle{font-size:18px;color:#5a4a3a;letter-spacing:2px;margin-bottom:36px}
.cover .meta{display:inline-block;text-align:left;font-size:14px;color:#4a3a2a;line-height:2.2;padding:18px 30px;border-top:1px solid #d4c4a8;border-bottom:1px solid #d4c4a8}
.cover .meta b{color:#2c1810;display:inline-block;min-width:90px}
h2{font-size:22px;color:#2c1810;border-bottom:2px solid #2c1810;padding-bottom:10px;margin:40px 0 22px;letter-spacing:1px}
h2 .num{color:#8b7355;font-size:18px;margin-right:12px}
h3{font-size:17px;color:#2c1810;margin:26px 0 12px;padding-left:12px;border-left:4px solid #c5a572}
p{margin-bottom:14px;text-align:justify;text-indent:2em;color:#2a2a2a}p.ni{text-indent:0}
.summary-box{background:#f9f5ec;border-left:5px solid #8b7355;padding:20px 26px;margin:18px 0;border-radius:0 4px 4px 0}
.summary-box ul{padding-left:20px}.summary-box li{margin-bottom:6px;list-style:disc}
table{width:100%;border-collapse:collapse;margin:16px 0 22px;font-size:13px;font-family:-apple-system,"PingFang SC",sans-serif}
th,td{padding:8px 11px;border-bottom:1px solid #e5dcc8;text-align:left}
th{background:#f0e9d8;color:#2c1810;border-top:2px solid #2c1810;border-bottom:1.5px solid #5a4a3a;font-weight:600}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}tr.total td{background:#f9f5ec;font-weight:700;border-top:1.5px solid #5a4a3a;border-bottom:2px solid #2c1810}
.conclusion{background:linear-gradient(180deg,#faf6ec,#f5ede0);border:1px solid #c5a572;padding:20px 26px;margin:16px 0;border-radius:4px}
.conclusion h3{border:none;padding:0;margin:0 0 8px}.conclusion p{text-indent:0;margin:0}
.signature{margin-top:50px;padding-top:24px;border-top:1px solid #d4c4a8;text-align:right;color:#5a4a3a;font-size:13px;line-height:2}
.signature .org{font-size:15px;color:#2c1810;font-weight:600}
@media print{body{background:#fff}.report{box-shadow:none;max-width:100%;padding:0}h2,table{page-break-inside:avoid}}
</style></head><body><div class="report">
<div class="cover"><div class="badge">FINANCIAL ANALYSIS REPORT</div><h1>__NAME__</h1><div class="subtitle">__SUBTITLE__</div>
<div class="meta"><div><b>报告主体</b>__NAME__</div><div><b>分析账户</b>__ACCOUNT__</div>
<div><b>统计区间</b>__RANGE__（__SPAN__）</div><div><b>有效记录</b>__COUNT__ 笔（已合并去重）</div>
<div><b>报告日期</b>__REPORTDATE__</div></div></div>
<h2><span class="num">〇</span>执行摘要</h2><p>__EXEC__</p>
<div class="summary-box"><b>核心发现</b>__FINDINGS_LIST__</div>
<h2><span class="num">一</span>资金规模与流动性总览</h2>__OVERVIEW_NOTE_P____T_YEAR__
<h2><span class="num">二</span>收入结构分析</h2>__INCOME_NOTE_P__
<h3>2.1 收入对手方属性分布</h3>__T_PIN__<h3>2.2 主要资金来源 Top 15</h3>__T_TIN__
<h2><span class="num">三</span>支出结构分析</h2>__EXPENSE_NOTE_P__
<h3>3.1 支出对手方属性分布</h3>__T_POUT__<h3>3.2 主要支出去向 Top 15</h3>__T_TOUT__
<h2><span class="num">四</span>年度趋势与拐点</h2>__TREND_P__
<h2><span class="num">五</span>对手方集中度</h2><p>采用 HHI 指数与 CRn 衡量收支两端的依赖程度。HHI 越低代表越分散（&lt;1500 为分散市场）。</p>__T_CONC__
<h2><span class="num">六</span>异常识别与内控观察</h2>
<p>金额 ≥ 大额阈值的交易共 __BIG_COUNT__ 笔；整万元交易 __ROUND_COUNT__ 笔；周末交易 __WEEKEND_COUNT__ 笔。__RISK_NOTE_P2__</p>
<h3>6.1 大额交易明细 Top 15</h3>__T_BIG__
<h3>6.2 Benford 首位数字检验（χ² = __CHI2__）</h3>__T_BF__
<h2><span class="num">七</span>结论与改进建议</h2><p>__CONCLUSION__</p>__ADVICE_BLOCKS__
<div class="signature"><div class="org">__NAME__</div><div>__SUBTITLE__</div><div>编制日期：__REPORTDATE__</div>
<div style="margin-top:10px;font-size:11px;color:#8b7355">— 本报告基于银行账户流水数据生成，不构成正式审计意见 —</div></div>
</div></body></html>'''

# ---------- 渲染输出 ----------
os.makedirs(os.path.join(OUT, 'pic'), exist_ok=True)
logo_ch = (M.get('name') or '账')[0]

# 网站
idx = render(TPL_INDEX).replace('__LOGOCH__', logo_ch)
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(idx)

# 图表版（脱敏数据；总结=exec+findings）
sf = '<p>' + '</p><p>'.join(f"<b>{f.get('t','')}</b> {f.get('d','')}" for f in N.get('findings', [])) + '</p>' if N.get('findings') else ''
ch = render(TPL_CHARTS).replace('__SUMMARY_FINDINGS__', sf)
open(os.path.join(OUT, 'charts.html'), 'w', encoding='utf-8').write(ch)

# 文字版（按 config：默认留真名）—— 用未脱敏 D 渲染表格
T = report_tables()
rep = TPL_REPORT
reps = {'__FINDINGS_LIST__': report_findings(),
        '__OVERVIEW_NOTE_P__': f'<p>{nl2(g("overview_note"))}</p>' if g('overview_note') else '',
        '__INCOME_NOTE_P__': f'<p>{nl2(g("income_note"))}</p>' if g('income_note') else '',
        '__EXPENSE_NOTE_P__': f'<p>{nl2(g("expense_note"))}</p>' if g('expense_note') else '',
        '__TREND_P__': report_trend() or '<p>（趋势解读待填写）</p>',
        '__RISK_NOTE_P2__': nl2(g('risk_note')),
        '__ADVICE_BLOCKS__': report_advice(),
        '__T_YEAR__': T['year'], '__T_PIN__': T['pin'], '__T_POUT__': T['pout'],
        '__T_TIN__': T['tin'], '__T_TOUT__': T['tout'], '__T_CONC__': T['conc'],
        '__T_BF__': T['bf'], '__T_BIG__': T['big'], '__CHI2__': str(T['chi2']),
        '__BIG_COUNT__': str(T['big_count']), '__ROUND_COUNT__': str(T['round_count']), '__WEEKEND_COUNT__': str(T['weekend_count'])}
for k, v in reps.items(): rep = rep.replace(k, v)
rep = render(rep)
open(os.path.join(OUT, 'report.html'), 'w', encoding='utf-8').write(rep)

print('✓ 三件套已生成：')
for f in ['index.html', 'charts.html', 'report.html']:
    p = os.path.join(OUT, f); print(f'  {f}  ({os.path.getsize(p)/1024:.0f} KB)')
print(f'  脱敏：网站/图表版={"是" if MASK_SITE else "否"}，文字版=否（存档留真名）')
print(f'  配图位：{os.path.join(OUT, "pic")}/  （hero/fund/income/expense/trend/risk/advice/logo）')

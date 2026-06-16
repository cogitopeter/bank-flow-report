# -*- coding: utf-8 -*-
"""
通用银行流水分析引擎。读 config.json（列映射 + 主体信息），输出 data.json（全维度指标）。
支持 .xlsx / .csv；多 sheet 自动按 dedup_priority 去重。
不含任何机构硬编码——一切来自 config。解读文字由 Claude 另写进 narrative.json。
用法：python3 flow_analyze.py [config.json]   默认读同目录 config.json
"""
import sys, os, json, re, math
from datetime import datetime
from collections import defaultdict
import pandas as pd

CFG = sys.argv[1] if len(sys.argv) > 1 else 'config.json'
cfg = json.load(open(CFG, encoding='utf-8'))
COL = cfg['cols']                         # {date,amount,dc,counterparty,summary,memo,balance}
DC_IN, DC_OUT = cfg.get('dc_in', '贷'), cfg.get('dc_out', '借')
BIG = cfg.get('big_threshold', 200000)
OUT = cfg.get('outdir', '.')
PRIORITY = cfg.get('dedup_priority', [])  # sheet 名优先级（靠前者优先保留）

# 资金用途关键词分类（可在 config.categories 覆盖）
CATEGORIES = cfg.get('categories') or [
    ['政府专项/财政拨款', ['财政', '专项', '拨款', '政府', '管委', '办事处', '人才', '经信', '经济和信息化', '科技局']],
    ['咨询/服务费',       ['咨询', '服务费', '技术服务']],
    ['活动/会议/赛事',     ['活动', '会议', '赛', '论坛', '对接', '路演', '峰会', '沙龙', '考察', '培训']],
    ['工资/人员费用',     ['工资', '薪', '劳务', '社保', '公积金', '奖金', '津贴', '报酬']],
    ['办公/差旅/招待',     ['办公', '差旅', '招待', '餐', '住宿', '交通', '机票', '租', '物业', '水电']],
    ['税费/手续费',       ['税', '手续费', '管理费', '年费']],
    ['利息/结息',         ['利息', '结息']],
    ['退款/转账往来',     ['退', '往来', '备用金', '报销', '转账']],
]

def parse_dt(v):
    if v is None or (isinstance(v, float) and math.isnan(v)): return None
    if hasattr(v, 'year') and not isinstance(v, str): return datetime(v.year, v.month, v.day,
        getattr(v, 'hour', 0), getattr(v, 'minute', 0), getattr(v, 'second', 0))
    s = str(v).strip()
    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d', '%Y/%m/%d %H:%M:%S', '%Y/%m/%d', '%Y%m%d']:
        try: return datetime.strptime(s[:19], fmt)
        except: pass
    return None

def num(v):
    if v is None or (isinstance(v, float) and math.isnan(v)): return 0.0
    s = re.sub(r'[,，¥\s]', '', str(v))
    try: return float(s)
    except: return 0.0

# ---------- 读取 + 合并去重 ----------
src = os.path.join(os.path.dirname(CFG) or '.', cfg['src'])
if src.lower().endswith('.csv'):
    df_csv = None
    for enc in [cfg.get('encoding'), 'utf-8-sig', 'gbk', 'gb18030']:   # 银行 CSV 多为 GBK，自动探测
        if not enc: continue
        try:
            df_csv = pd.read_csv(src, dtype=str, encoding=enc); break
        except (UnicodeDecodeError, LookupError): continue
    if df_csv is None:
        print('！CSV 编码无法识别，请在 config.encoding 指定（如 gbk）'); sys.exit(1)
    sheets = {'_': df_csv}
else:
    sheets = pd.read_excel(src, sheet_name=None, dtype=object)

def prio(sheet):
    return PRIORITY.index(sheet) if sheet in PRIORITY else len(PRIORITY)

rows = []
for sn, df in sheets.items():
    for _, row in df.iterrows():
        d = {c: row.get(c) for c in df.columns}
        dt = parse_dt(d.get(COL['date']))
        if dt is None: continue
        rows.append({
            'dt': dt, 'sheet': sn,
            'amt': num(d.get(COL['amount'])),
            'dc': str(d.get(COL['dc']) or '').strip(),
            'cp': (str(d.get(COL['counterparty'])).strip() if d.get(COL['counterparty']) is not None else ''),
            'summary': str(d.get(COL.get('summary', '')) or '').strip() if COL.get('summary') else '',
            'memo': str(d.get(COL.get('memo', '')) or '').strip() if COL.get('memo') else '',
            'bal': num(d.get(COL['balance'])) if COL.get('balance') and d.get(COL['balance']) is not None else None,
        })

DEDUP = str(cfg.get('dedup', 'auto')).lower()   # 'auto'=仅多 sheet 去重 / 'true' 强制 / 'false' 不去重
do_dedup = DEDUP == 'true' or (DEDUP == 'auto' and len(sheets) > 1)
if do_dedup:
    seen = {}
    for r in rows:
        key = (r['dt'].strftime('%Y-%m-%d %H:%M'), r['amt'], r['dc'], r['cp'], r['summary'])
        if key not in seen or prio(r['sheet']) < prio(seen[key]['sheet']):
            seen[key] = r
    data = sorted(seen.values(), key=lambda x: x['dt'])
    print(f'  去重：{len(rows)} → {len(data)} 笔（{len(sheets)} 个 sheet 按优先级合并）')
else:
    data = sorted(rows, key=lambda x: x['dt'])
    print(f'  未去重：保留全部 {len(data)} 笔（单 sheet 默认不去重，避免误删同日同额交易）')
if not data:
    print('！未解析到任何记录，请检查 config.cols 列名映射'); sys.exit(1)

is_in = lambda r: r['dc'] == DC_IN
is_out = lambda r: r['dc'] == DC_OUT

# ---------- 总览 ----------
total_in = sum(r['amt'] for r in data if is_in(r))
total_out = sum(r['amt'] for r in data if is_out(r))
in_cnt = sum(1 for r in data if is_in(r))
out_cnt = sum(1 for r in data if is_out(r))
end_bal = next((r['bal'] for r in reversed(data) if r['bal'] is not None), 0)
ins = sorted(r['amt'] for r in data if is_in(r))
outs = sorted(r['amt'] for r in data if is_out(r))
def pct(a, p):
    if not a: return 0
    return round(a[min(len(a)-1, int(len(a)*p))], 2)
span_days = (data[-1]['dt'] - data[0]['dt']).days or 1
n_months = len({r['dt'].strftime('%Y-%m') for r in data}) or 1

# ---------- 年/月/季 ----------
ys = defaultdict(lambda: {'in': 0, 'out': 0, 'cnt': 0, 'ic': 0, 'oc': 0})
ms = defaultdict(lambda: {'in': 0, 'out': 0})
qs = defaultdict(lambda: {'in': 0, 'out': 0})
for r in data:
    y, m = r['dt'].year, r['dt'].strftime('%Y-%m')
    q = f"{y}Q{(r['dt'].month-1)//3+1}"
    ys[y]['cnt'] += 1
    if is_in(r): ys[y]['in'] += r['amt']; ys[y]['ic'] += 1; ms[m]['in'] += r['amt']; qs[q]['in'] += r['amt']
    if is_out(r): ys[y]['out'] += r['amt']; ys[y]['oc'] += 1; ms[m]['out'] += r['amt']; qs[q]['out'] += r['amt']
years = sorted(ys)
months = sorted(ms)
def yoy(cur, prev): return round((cur-prev)/prev*100, 2) if prev else None
year_in = [round(ys[y]['in'], 2) for y in years]
year_out = [round(ys[y]['out'], 2) for y in years]

# 月末余额（对齐 months）
bal_by_month = {}
for r in data:
    if r['bal'] is not None: bal_by_month[r['dt'].strftime('%Y-%m')] = r['bal']
month_bal = [bal_by_month.get(m) for m in months]
daily = {}
for r in data:
    if r['bal'] is not None: daily[r['dt'].strftime('%Y-%m-%d')] = r['bal']
daily_bal = sorted(daily.items())

# ---------- 对手方 + 属性分类 ----------
FIN = ['银行', '支行', '分行', '信用社', '证券', '保险', '基金']
GOV = ['财政', '政府', '管委', '街道', '办事处', '人民政府', '团委', '机关', '事业', '专户', '国库']
GOV_SUF = ['局', '委员会', '管理委员会']
ORG = ['公司', '中心', '有限', '研究院', '学院', '大学', '工作室', '事务所', '厂', '商行', '合作社', '集团', '协会', '商会', '基金会', '院', '校', '部', '站']
def classify(name):
    n = name or ''
    if any(k in n for k in FIN) or ('利息' in n): return '金融机构'
    if any(k in n for k in GOV) or any(n.endswith(s) or s in n for s in GOV_SUF): return '政府/事业'
    if any(k in n for k in ORG): return '企业'
    if re.fullmatch(r'[一-龥·]{2,4}', n): return '个人'
    return '企业'

cp_in = defaultdict(lambda: {'sum': 0, 'cnt': 0})
cp_out = defaultdict(lambda: {'sum': 0, 'cnt': 0})
prop_in = defaultdict(lambda: {'sum': 0, 'cnt': 0, 'parties': set()})
prop_out = defaultdict(lambda: {'sum': 0, 'cnt': 0, 'parties': set()})
for r in data:
    cp = r['cp'] or '(未知)'
    cls = classify(cp)
    tgt, ptgt = (cp_in, prop_in) if is_in(r) else (cp_out, prop_out) if is_out(r) else (None, None)
    if tgt is None: continue
    tgt[cp]['sum'] += r['amt']; tgt[cp]['cnt'] += 1
    ptgt[cls]['sum'] += r['amt']; ptgt[cls]['cnt'] += 1; ptgt[cls]['parties'].add(cp)

def top(cpd, n=15):
    return [{'name': k, 'sum': round(v['sum'], 2), 'cnt': v['cnt']}
            for k, v in sorted(cpd.items(), key=lambda x: -x[1]['sum'])[:n]]
def proplist(pd_):
    return [{'cls': k, 'sum': round(v['sum'], 2), 'cnt': v['cnt'], 'n_parties': len(v['parties'])}
            for k, v in sorted(pd_.items(), key=lambda x: -x[1]['sum'])]

# HHI / CRn
def conc(cpd):
    tot = sum(v['sum'] for v in cpd.values()) or 1
    shares = sorted((v['sum']/tot*100 for v in cpd.values()), reverse=True)
    hhi = round(sum(s*s for s in shares), 1)
    crn = lambda k: round(sum(shares[:k]), 1)
    return {'hhi': hhi, 'cr3': crn(3), 'cr5': crn(5), 'cr10': crn(10), 'n': len(cpd)}

# ---------- 用途分类 ----------
def categorize(r):
    full = (r['summary'] + ' ' + r['memo'] + ' ' + r['cp']).lower()
    for cat, kws in CATEGORIES:
        if any(kw.lower() in full for kw in kws): return cat
    return '其他'
cat_in = defaultdict(lambda: {'sum': 0, 'cnt': 0})
cat_out = defaultdict(lambda: {'sum': 0, 'cnt': 0})
for r in data:
    c = categorize(r)
    if is_in(r): cat_in[c]['sum'] += r['amt']; cat_in[c]['cnt'] += 1
    if is_out(r): cat_out[c]['sum'] += r['amt']; cat_out[c]['cnt'] += 1
def catlist(cd):
    return [{'name': k, 'sum': round(v['sum'], 2), 'cnt': v['cnt']}
            for k, v in sorted(cd.items(), key=lambda x: -x[1]['sum'])]

# ---------- 季节性 ----------
mser = defaultdict(lambda: {'in': 0, 'out': 0})
for r in data:
    k = r['dt'].strftime('%Y-%m')
    if is_in(r): mser[k]['in'] += r['amt']
    if is_out(r): mser[k]['out'] += r['amt']
season_raw = defaultdict(lambda: {'in': [], 'out': []})
for k, v in mser.items():
    season_raw[int(k[5:7])]['in'].append(v['in']); season_raw[int(k[5:7])]['out'].append(v['out'])
season = [{'month': mo, 'in_avg': round(sum(d['in'])/len(d['in']), 1) if d['in'] else 0,
           'out_avg': round(sum(d['out'])/len(d['out']), 1) if d['out'] else 0, 'n': len(d['in'])}
          for mo, d in sorted(season_raw.items())]

# 波动性 CV
mi = [mser[k]['in'] for k in sorted(mser)]
mo = [mser[k]['out'] for k in sorted(mser)]
def cv(a):
    if not a: return 0
    mu = sum(a)/len(a)
    if mu == 0: return 0
    sd = (sum((x-mu)**2 for x in a)/len(a))**0.5
    return round(sd/mu*100, 1)

# ---------- 金额区间 ----------
BUCKETS = [('<1k', 0, 1000), ('1k-1w', 1000, 10000), ('1w-5w', 10000, 50000),
           ('5w-20w', 50000, 200000), ('20w-100w', 200000, 1000000), ('>100w', 1000000, 9e18)]
def buckets(vals):
    cnt = {b[0]: 0 for b in BUCKETS}; summ = {b[0]: 0 for b in BUCKETS}
    for v in vals:
        for name, lo, hi in BUCKETS:
            if lo <= v < hi: cnt[name] += 1; summ[name] += v; break
    return cnt, {k: round(x, 2) for k, x in summ.items()}
in_buck, in_buck_sum = buckets([r['amt'] for r in data if is_in(r)])
out_buck, out_buck_sum = buckets([r['amt'] for r in data if is_out(r)])

# ---------- Benford ----------
firsts = [int(str(int(r['amt']))[0]) for r in data if r['amt'] >= 1]
n_bf = len(firsts) or 1
actual = {str(d): round(firsts.count(d)/n_bf*100, 4) for d in range(1, 10)}
expected = {str(d): round(math.log10(1+1/d)*100, 4) for d in range(1, 10)}
chi2 = round(sum((actual[str(d)]-expected[str(d)])**2 / expected[str(d)] for d in range(1, 10)) * n_bf/100, 2)

# ---------- 异常 ----------
big = sorted([r for r in data if r['amt'] >= BIG], key=lambda x: -x['amt'])
round_amt = [r for r in data if r['amt'] >= 10000 and r['amt'] % 10000 == 0]
weekend = [r for r in data if r['dt'].weekday() >= 5]
night = [r for r in data if 0 < r['dt'].hour < 6]
day_cp = defaultdict(list)
for r in data:
    if r['cp']: day_cp[(r['dt'].date(), r['cp'])].append(r)
freq = [(k, v) for k, v in day_cp.items() if len(v) >= 3]

conc_in, conc_out = conc(cp_in), conc(cp_out)

result = {
    'meta': {**cfg.get('meta', {}), 'dc_in': DC_IN, 'dc_out': DC_OUT,
             'date_start': data[0]['dt'].strftime('%Y-%m-%d'),
             'date_end': data[-1]['dt'].strftime('%Y-%m-%d'), 'total_count': len(data),
             'span_days': span_days, 'span_years': round(span_days/365, 1),
             'in_count': in_cnt, 'out_count': out_cnt},
    'overview': {'total_in': round(total_in, 2), 'total_out': round(total_out, 2),
                 'net': round(total_in-total_out, 2), 'turnover': round(total_in+total_out, 2),
                 'end_bal': round(end_bal, 2), 'avg_monthly_in': round(total_in/n_months, 2),
                 'avg_monthly_out': round(total_out/n_months, 2), 'avg_monthly_cnt': round(len(data)/n_months),
                 'avg_in_amt': round(total_in/in_cnt, 2) if in_cnt else 0,
                 'avg_out_amt': round(total_out/out_cnt, 2) if out_cnt else 0,
                 'median_in': pct(ins, .5), 'median_out': pct(outs, .5)},
    'years': years, 'year_in': year_in, 'year_out': year_out,
    'year_net': [round(ys[y]['in']-ys[y]['out'], 2) for y in years],
    'year_cnt': [ys[y]['cnt'] for y in years],
    'yoy_in': [None]+[yoy(year_in[i], year_in[i-1]) for i in range(1, len(years))],
    'yoy_out': [None]+[yoy(year_out[i], year_out[i-1]) for i in range(1, len(years))],
    'months': months, 'month_in': [round(ms[m]['in'], 2) for m in months],
    'month_out': [round(ms[m]['out'], 2) for m in months], 'month_bal': month_bal,
    'daily_bal': daily_bal,
    'quarter': [{'q': q, 'in': round(qs[q]['in'], 2), 'out': round(qs[q]['out'], 2)} for q in sorted(qs)],
    'top_in': top(cp_in), 'top_out': top(cp_out),
    'prop_in': proplist(prop_in), 'prop_out': proplist(prop_out),
    'cat_in': catlist(cat_in), 'cat_out': catlist(cat_out),
    'conc': {'hhi_in': conc_in['hhi'], 'hhi_out': conc_out['hhi'],
             'cr3_in': conc_in['cr3'], 'cr3_out': conc_out['cr3'],
             'cr5_in': conc_in['cr5'], 'cr5_out': conc_out['cr5'],
             'cr10_in': conc_in['cr10'], 'cr10_out': conc_out['cr10'],
             'n_in_parties': conc_in['n'], 'n_out_parties': conc_out['n']},
    'volatility': {'cv_in': cv(mi), 'cv_out': cv(mo),
                   'max_in': round(max(mi), 2) if mi else 0, 'max_out': round(max(mo), 2) if mo else 0},
    'season': season,
    'dist': {'in_pct': {str(int(p*100)): pct(ins, p) for p in [.1, .25, .5, .75, .9, .95, .99]},
             'out_pct': {str(int(p*100)): pct(outs, p) for p in [.1, .25, .5, .75, .9, .95, .99]},
             'in_buck': in_buck, 'out_buck': out_buck, 'in_buck_sum': in_buck_sum, 'out_buck_sum': out_buck_sum},
    'benford': {'actual': actual, 'expected': expected, 'chi2': chi2, 'n': n_bf},
    'anomaly': {'big_threshold': BIG, 'big_count': len(big), 'big_sum': round(sum(r['amt'] for r in big), 2),
                'big_top': [{'date': r['dt'].strftime('%Y-%m-%d'), 'amt': r['amt'], 'sign': r['dc'],
                             'cp': r['cp'], 'memo': r['summary'] or r['memo']} for r in big[:20]],
                'round_count': len(round_amt), 'weekend_count': len(weekend), 'night_count': len(night),
                'freq_groups': [{'date': str(k[0]), 'cp': k[1], 'count': len(v), 'sum': round(sum(x['amt'] for x in v), 2)}
                                for k, v in sorted(freq, key=lambda x: -len(x[1]))[:10]]},
}

os.makedirs(os.path.join(OUT, 'analysis'), exist_ok=True)
outpath = os.path.join(OUT, 'analysis', 'data.json')
json.dump(result, open(outpath, 'w', encoding='utf-8'), ensure_ascii=False, indent=2, default=str)
print(f'✓ 分析完成 → {outpath}')
print(f'  记录 {len(data)} 笔 | {result["meta"]["date_start"]} ~ {result["meta"]["date_end"]}')
print(f'  收入 ¥{total_in:,.0f} | 支出 ¥{total_out:,.0f} | 净 ¥{total_in-total_out:,.0f} | 期末 ¥{end_bal:,.0f}')
print(f'  属性收入: ' + ' '.join(f'{p["cls"]}{p["sum"]/total_in*100:.0f}%' for p in proplist(prop_in)))

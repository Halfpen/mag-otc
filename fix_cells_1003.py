#!/usr/bin/env python3
"""fix_cells_1003.py — 2026-10-03 把 6 格舊標籤改成與現行關鍵日邏輯一致
（「代替 D1」也算關鍵日參照；mag_admin 2026-10-03 已修，這裡補回歷史格）。

只動 kd class、title 的【止盈】後綴、jl 標籤；mag／brk／period／price 一律不碰。
可重複執行：已改好的格會跳過。任何一格內容與預期不符就整個中止、不寫檔。
用法：cd ~/mag-otc && python3 fix_cells_1003.py
"""
import re, sys

# (ck, 日期, kd, title 後綴, jl 文字, jl class)
CELLS = [
    ('coins|SOL',      '2026-01-08', 'jin-tp', '【做多止盈】', '止盈多', 'lie'),
    ('coins|SUI',      '2026-07-27', 'tui-tp', '【做空止盈】', '止盈空', 'lie'),
    ('coins|HYPE',     '2026-06-18', 'jin',    '',            '續抱多', 'yu'),
    ('coins|PUMP',     '2026-09-16', 'tui',    '',            '續抱空', 'yu'),
    ('coins|ZEC',      '2026-08-01', 'tui',    '',            '續抱空', 'yu'),
    ('macro|BTC_VEGA', '2026-09-11', 'tui',    '',            '優退',   'yu'),
]
JL_RE = re.compile(r'\s*<div class="jl [a-z]+">[^<]*</div>')


def fix_html(h):
    log = []
    for ck, d, kd, suf, jl, cls in CELLS:
        tk = ck.split('|')[1]
        key = f'title="{d} {tk}: '
        if h.count(key) != 1:
            sys.exit(f'index.html：{d} {tk} 找到 {h.count(key)} 格（預期 1），未修改')
        i = h.index(key)
        a, b = h.rfind('<td', 0, i), h.index('</td>', i) + 5
        old = h[a:b]
        m = re.match(r'<td class="([^"]*)"((?: data-ck="[^"]*")?) title="([^"【]*)(【[^】]*】)?">', old)
        if not m or len(JL_RE.findall(old)) > 1 or old.count('<div class="pr">') != 1:
            sys.exit(f'index.html：{d} {tk} 格式與預期不符，未修改：{old!r}')
        base = 'jin' if kd.startswith('jin') else 'tui-pos'
        head = f'<td class="{base} kd-{kd}"{m.group(2)} title="{m.group(3)}{suf}">'
        body = JL_RE.sub('', old[m.end():-5])
        multi = '\n' in body
        tail = body.rstrip()
        jl_div = f'<div class="jl {cls}">{jl}</div>'
        new = head + (tail + '\n          ' + jl_div + '\n        ' if multi else tail + jl_div) + '</td>'
        if new == old:
            log.append(f'  {d} {tk}：已正確，跳過'); continue
        # 保險：數據欄不可變
        keep = lambda s: re.findall(r'<div class="(?:cp|cv[^"]*|cb[^"]*|pr)">[^<]*</div>', s)
        assert keep(old) == keep(new) and m.group(3) in new
        h = h[:a] + new + h[b:]
        log.append(f'  {d} {tk} → kd-{kd}、{jl}')
    return h, log


def fix_json(raw):
    log = []
    for ck, d, kd, suf, jl, cls in CELLS:
        tk = ck.split('|')[1]
        i = raw.find(f'"{ck}": {{')
        a = raw.find(f'"{d}": {{', i) if i >= 0 else -1
        if a < 0:
            sys.exit(f'data.json：找不到 {ck} {d}，未修改')
        b = raw.index('}', a) + 1
        old = raw[a:b]
        m = re.search(r'\n(\s*)"kd": "[^"]*"', old)
        if not m:
            sys.exit(f'data.json：{ck} {d} 沒有 kd 欄，未修改：{old}')
        ind = m.group(1)
        new = re.sub(r',?\n\s*"jl": "[^"]*"', '', old)
        new = re.sub(r'\n\s*"kd": "[^"]*"', f'\n{ind}"kd": "{kd}",\n{ind}"jl": "{jl}"', new, count=1)
        if new == old:
            log.append(f'  {d} {tk}：已正確，跳過'); continue
        num = lambda s: re.findall(r'"(?:mag|brk|period|price)": [^,\n]*', s)
        assert num(old) == num(new)
        raw = raw[:a] + new + raw[b:]
        log.append(f'  {d} {tk} → kd={kd}、jl={jl}')
    return raw, log


def main():
    import json
    h = open('index.html', encoding='utf-8').read()
    j = open('data.json', encoding='utf-8').read()
    h2, l1 = fix_html(h)
    j2, l2 = fix_json(j)
    json.loads(j2)                                   # 仍是合法 JSON
    assert len(h2.split('<td')) == len(h.split('<td'))
    if h2 != h: open('index.html', 'w', encoding='utf-8').write(h2)
    if j2 != j: open('data.json', 'w', encoding='utf-8').write(j2)
    print('index.html：'); print('\n'.join(l1))
    print('data.json：'); print('\n'.join(l2))


if __name__ == '__main__':
    main()

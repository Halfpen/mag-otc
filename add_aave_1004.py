#!/usr/bin/env python3
"""add_aave_1004.py — 2026-10-04 新增 AAVE（魔方 2026-10-02 起在每日貼文加入 AAVE）

 1) mag_admin.html：ASSETS、NAME_TO_CK 加 AAVE（Binance AAVEUSDT）。
 2) mag_admin.html：當日沒有數據的標的補一個空格佔位；新格一律加在該行最尾。
    以前沒有數據就甚麼都不加，之後的格會向左錯位（BTC_VEGA 2026-07 起就是這樣移了 2 欄）。
 3) index.html：新增 row_coins_AAVE（全部空格，欄數跟 thead）＋資產勾選框。
 4) index.html：BTC_VEGA 整行對返欄位。該行由第一格（2026-04-27）起就放早了 1 欄，2026-09-03 缺數據後再早多 1 欄；
    今次只搬位置（按格內日期對返表頭的 M/D），每一格的內容原封不動。

不改任何已有的 mag／brk／period／價格。可重複執行；內容與預期不符就中止、不寫檔。
用法：cd ~/mag-otc && python3 add_aave_1004.py
"""
import re, sys

def die(m): sys.exit('✗ ' + m + '（未修改任何檔案）')

def one(s, old, what):
    if s.count(old) != 1: die('%s：預期 1 處，找到 %d 處' % (what, s.count(old)))

# ── mag_admin.html ──────────────────────────────────────────────────────────
A_ASSET_OLD = "  ['coins|UNI',    'UNI',         'UNI',       'UNIUSDT',   'BINANCE'],\n"
A_ASSET_NEW = A_ASSET_OLD + "  ['coins|AAVE',   'AAVE',        'AAVE',      'AAVEUSDT',  'BINANCE'],\n"
A_NAME_OLD  = "'ZEC':'coins|ZEC','UNI':'coins|UNI',\n"
A_NAME_NEW  = "'ZEC':'coins|ZEC','UNI':'coins|UNI','AAVE':'coins|AAVE',\n"
S1_OLD = """  // Step 2: 清除 thead 中今天日期的 th（含重複）
"""
S1_NEW = """  // Step 1b（2026-10-04）: 清除今天日期的空格佔位（重跑同一日時不會重複）
  {
    const ph = `<td class="mt" data-d="${date}"></td>`;
    while (h.includes('\\n        ' + ph)) h = h.replace('\\n        ' + ph, '');
    while (h.includes(ph)) h = h.replace(ph, '');
  }

  // Step 2: 清除 thead 中今天日期的 th（含重複）
"""
S4_OLD = """  for (const row of rows) {
    if (row.mag === '') continue;
    const anchor = `data-ck="${row.ck}"`;
    const last   = h.lastIndexOf(anchor);
    let pos;
    if (last === -1) {
      // 全新標（尚無歷史數據）：定位到對應 tr 的結尾
      const rowId  = `id="row_${row.ck.replace('|', '_')}"`;
      const rowIdx = h.indexOf(rowId);
      if (rowIdx === -1) throw new Error('找不到 anchor: ' + row.ck);
      pos = h.indexOf('</tr>', rowIdx);
    } else {
      pos = h.indexOf('</td>', last) + 5;
    }
    h = h.slice(0, pos) + '\\n' + makeCell(row) + h.slice(pos);
  }
"""
S4_NEW = """  // 2026-10-04：新格一律加在該行最尾（最後一個 </td> 之後）；當日沒有數據的標的補一個空格佔位。
  //   以前沒有數據就不加格，之後的格會向左錯位（BTC_VEGA 2026-07 起移了 2 欄）。
  for (const row of rows) {
    const rowId  = `id="row_${row.ck.replace('|', '_')}"`;
    const rowIdx = h.indexOf(rowId);
    if (rowIdx === -1) {
      if (row.mag === '') continue;
      throw new Error('找不到 row: ' + row.ck + '（index.html 未有這一行）');
    }
    const nextTr = h.indexOf('<tr', rowIdx);
    const rowEnd = nextTr !== -1 ? nextTr : h.indexOf('</tbody>', rowIdx);
    const lastTd = h.lastIndexOf('</td>', rowEnd);
    if (lastTd < rowIdx) throw new Error('row 結構異常: ' + row.ck);
    const pos  = lastTd + 5;
    const cell = row.mag === '' ? `        <td class="mt" data-d="${date}"></td>` : makeCell(row);
    h = h.slice(0, pos) + '\\n' + cell + h.slice(pos);
  }
"""

def patch_admin(a):
    log = []
    if "'coins|AAVE'" in a.split('const NAME_TO_CK')[0]: log.append('  ASSETS 已有 AAVE，跳過')
    else: one(a, A_ASSET_OLD, 'mag_admin ASSETS 的 UNI 行'); a = a.replace(A_ASSET_OLD, A_ASSET_NEW); log.append('  ASSETS ＋AAVE（AAVEUSDT／Binance）')
    if "'AAVE':'coins|AAVE'" in a: log.append('  NAME_TO_CK 已有 AAVE，跳過')
    else: one(a, A_NAME_OLD, 'mag_admin NAME_TO_CK 的 UNI 行'); a = a.replace(A_NAME_OLD, A_NAME_NEW); log.append('  NAME_TO_CK ＋AAVE')
    if 'Step 1b（2026-10-04）' in a: log.append('  空格佔位邏輯已在，跳過')
    else:
        one(a, S1_OLD, 'mag_admin Step 2 註解'); one(a, S4_OLD, 'mag_admin Step 4 插入新格')
        a = a.replace(S1_OLD, S1_NEW).replace(S4_OLD, S4_NEW); log.append('  buildNewHtml：無數據補空格、新格加在行尾')
    return a, log

# ── index.html ─────────────────────────────────────────────────────────────
CB_OLD = """<div class="ac" id="ac_row_coins_UNI"><input type="checkbox" id="cb_row_coins_UNI" checked onchange="togA('row_coins_UNI',this.checked)"><label for="cb_row_coins_UNI">UNI</label></div>"""
CB_NEW = CB_OLD + """\n  <div class="ac" id="ac_row_coins_AAVE"><input type="checkbox" id="cb_row_coins_AAVE" checked onchange="togA('row_coins_AAVE',this.checked)"><label for="cb_row_coins_AAVE">AAVE</label></div>"""

def patch_index(h):
    log = []
    if 'id="row_coins_AAVE"' in h:
        log.append('  row_coins_AAVE 已在，跳過')
    else:
        t = h[h.index('<thead'):h.index('</thead>')]
        ncol = len(re.findall(r'<th[ >]', t)) - 1       # 日期欄數（不含「資產」；<thead 本身不計）
        if ncol < 1000: die('index.html thead 欄數異常：%d' % ncol)
        one(h, '<tr id="row_coins_UNI"', 'index.html UNI 行')
        i = h.index('<tr id="row_coins_UNI"'); j = h.index('<tr', i + 10)
        if h[i:j].rstrip()[-5:] != '</tr>': die('index.html UNI 行結尾不是 </tr>')
        row = '<tr id="row_coins_AAVE" data-g="主要幣種"><td class="nm">AAVE</td>' + '<td class="mt"></td>' * ncol + '\n</tr>'
        ntd = len(re.findall(r'<td', h))
        h = h[:j] + row + h[j:]
        assert len(re.findall(r'<td', h)) == ntd + ncol + 1
        log.append('  ＋row_coins_AAVE（%d 個空格，放在 UNI 之後）' % ncol)
    if 'id="cb_row_coins_AAVE"' in h: log.append('  資產勾選框已在，跳過')
    else: one(h, CB_OLD, 'index.html UNI 勾選框'); h = h.replace(CB_OLD, CB_NEW); log.append('  ＋資產勾選框 AAVE')
    return h, log

def _labels(h):
    t = h[h.index('<thead'):h.index('</thead>')]
    return [l for _, l in re.findall(r'<th(?=[ >])([^>]*)>([^<]*)</th>', t)][1:]

def _row(h, rid):
    i = h.index('<tr id="%s"' % rid); j = h.find('<tr', i + 5)
    if j == -1: j = h.index('</tbody>', i)
    return i, j, h[i:j]

def _cells(r):
    """回傳 [(起, 止)]：每個 <td ...>…</td>（格內沒有巢狀 td）。"""
    out = []
    for m in re.finditer(r'<td', r):
        e = r.find('</td>', m.start())
        if e == -1: die('row 內有未關閉的 td')
        out.append((m.start(), e + 5))
    return out

def misaligned(h, rid, lab):
    _, _, r = _row(h, rid); n = 0
    for k, (a, b) in enumerate(_cells(r)[1:]):
        m = re.search(r'title="\d{4}-(\d{2})-(\d{2}) ', r[a:b])
        if m and (k >= len(lab) or lab[k] != '%d/%d' % (int(m.group(1)), int(m.group(2)))): n += 1
    return n

def fix_vega(h, rid='row_macro_BTC_VEGA'):
    lab = _labels(h)
    if misaligned(h, rid, lab) == 0: return h, ['  BTC_VEGA 已對齊，跳過']
    i, j, r = _row(h, rid); cs = _cells(r)
    head = r[:cs[0][0]]; nm = r[cs[0][0]:cs[0][1]]
    if 'class="nm"' not in nm: die('BTC_VEGA 第一格不是名稱格')
    data = [r[a:b] for a, b in cs[1:] if 'title="20' in r[a:b]]
    others = [r[a:b] for a, b in cs[1:] if 'title="20' not in r[a:b]]
    if any('class="mt"' not in c or len(c) > 60 for c in others): die('BTC_VEGA 有不是空格、又沒有日期的格')
    last = {}                                         # M/D → 最後一次出現的欄（VEGA 只有 2026-04 之後的數據）
    for k, l in enumerate(lab): last[l] = k
    slot = {}; prev = -1
    for c in data:
        m = re.search(r'title="(\d{4})-(\d{2})-(\d{2}) ', c); key = '%d/%d' % (int(m.group(2)), int(m.group(3)))
        if key not in last: die('BTC_VEGA %s 在表頭找不到對應欄' % m.group(0))
        k = last[key]
        if k <= prev: die('BTC_VEGA 欄位次序異常：%s' % m.group(0))
        slot[k] = c; prev = k
    # 交叉核對：同一欄 BTC 那格的日期要一樣
    _, _, rb = _row(h, 'row_coins_BTC'); cb = _cells(rb)[1:]
    for k, c in slot.items():
        if k < len(cb):
            mb = re.search(r'title="(\d{4}-\d{2}-\d{2}) ', rb[cb[k][0]:cb[k][1]]); mv = re.search(r'title="(\d{4}-\d{2}-\d{2}) ', c)
            if mb and mb.group(1) != mv.group(1): die('BTC_VEGA %s 對到的欄是 BTC %s' % (mv.group(1), mb.group(1)))
    body = ''.join(slot.get(k, '<td class="mt"></td>') if k not in slot else '\n        ' + slot[k] for k in range(len(lab)))
    new = head + nm + body + ('\n</tr>' if '</tr>' in r[cs[-1][1]:] else '\n')
    h2 = h[:i] + new + h[j:]
    if misaligned(h2, rid, lab) != 0: die('BTC_VEGA 對齊後仍有錯位')
    _, _, r2 = _row(h2, rid); c2 = _cells(r2)
    if [r2[a:b] for a, b in c2[1:] if 'title="20' in r2[a:b]] != data: die('BTC_VEGA 數據格內容有變')
    return h2, ['  BTC_VEGA：%d 格數據對返欄位（之前錯位 %d 格），全行 %d 欄' % (len(data), misaligned(h, rid, lab), len(c2) - 1)]

def main():
    a = open('mag_admin.html', encoding='utf-8').read(); h = open('index.html', encoding='utf-8').read()
    a2, l1 = patch_admin(a); h2, l2 = patch_index(h); h2, l3 = fix_vega(h2); l2 += l3
    # 已有數據格一格都不能變
    cells = lambda s: re.findall(r'title="\d{4}-\d{2}-\d{2} [^"]*"', s)
    assert cells(h) == cells(h2), '數據格有變動'
    if a2 != a: open('mag_admin.html', 'w', encoding='utf-8').write(a2)
    if h2 != h: open('index.html', 'w', encoding='utf-8').write(h2)
    print('mag_admin.html：'); print('\n'.join(l1)); print('index.html：'); print('\n'.join(l2))
    lab = _labels(h2); bad = {}
    for rid in re.findall(r'<tr id="(row_[^"]+)"', h2):
        n = misaligned(h2, rid, lab)
        if n: bad[rid] = n
    print('對齊檢查：' + ('全部行的數據格都在正確日期欄 ✅' if not bad else '仍有錯位 ' + str(bad)))

if __name__ == '__main__':
    main()

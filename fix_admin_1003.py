#!/usr/bin/env python3
"""fix_admin_1003.py — 2026-10-03 修 mag_admin 兩個問題＋補 data.json
 1) 「代替 D1」（期間第一格不是 D1，例 PUMP 2026-09-28 進D2）以前不算關鍵日參照，
    令之後的 Dn 關鍵日只標 kd、沒有續抱／止盈標籤（PUMP 2026-10-03 應為止盈多）。
 2) 手工修改一格只寫 index.html，沒有同步 data.json。
 3) data.json：PUMP 2026-10-03 補回 kd=jin-tp、jl=止盈多。
可重複執行。用法：cd ~/mag-otc && python3 fix_admin_1003.py
"""
import os, sys, json
os.chdir(os.path.dirname(os.path.abspath(__file__)))
def patch_admin():
    h = open('mag_admin.html', encoding='utf-8').read()
    if 'subD1' in h: print('mag_admin.html：已修過，跳過'); return
    reps = [
      # getD1RefMag：代替 D1 也算一次 KD
      ("""  let lastJinKd=null, lastTuiKd=null, lastTuiDrop200=null, lastJinNegPos=null, prevB=null;
  for (const c of cells) {
    const cJin = c.period.startsWith('進場期'), day = getDN(c.period);
    if (day === 1) {""",
       """  let lastJinKd=null, lastTuiKd=null, lastTuiDrop200=null, lastJinNegPos=null, prevB=null, pJ=null;
  for (const c of cells) {
    const cJin = c.period.startsWith('進場期'), day = getDN(c.period);
    // 代替 D1：期間第一格不是 D1（網站缺了 D1 那一欄），而且本身不是 Dn 關鍵日 → 當 D1 用
    const subD1 = day !== 1 && pJ !== null && pJ !== cJin &&
      !((cJin && prevB>200 && c.brk<=200) || (!cJin && prevB<0 && c.brk>=0));
    pJ = cJin;
    if (day === 1 || subD1) {"""),
      # getLastKdInCurrentPeriod
      ("""    if (curJin !== cJin) { curJin = cJin; if (cJin !== isJin) lastMag = null; }
    if (cJin === isJin) {
      if (day === 1) lastMag = c.mag;""",
       """    const sw = curJin !== null && curJin !== cJin;      // 期間剛切換的第一格
    const subD1 = day !== 1 && sw &&
      !((cJin && prevB>200 && c.brk<=200) || (!cJin && prevB<0 && c.brk>=0));
    if (curJin !== cJin) { curJin = cJin; if (cJin !== isJin) lastMag = null; }
    if (cJin === isJin) {
      if (day === 1 || subD1) lastMag = c.mag;"""),
      # saveEditCell：同步 data.json
      ("""    html = h;
    document.getElementById('prog-edit').textContent = '';
    showMsg('msg-edit','ok',`✓ 已更新 ${dt} ${ck.split('|')[1]}`);""",
       """    html = h;
    document.getElementById('prog-edit').textContent = '';
    showMsg('msg-edit','ok',`✓ 已更新 ${dt} ${ck.split('|')[1]}`);
    // 2026-10-03：手工修改同步 data.json（以前只改 index.html，data.json 會留舊標籤）
    try {
      const data = await ghReadDataJson();
      if (!data.rows[ck]) data.rows[ck] = {};
      const e = { ...(data.rows[ck][dt] || {}), mag, brk, period };
      if (kd) e.kd = kd; else delete e.kd;
      if (jl) e.jl = jl; else delete e.jl;
      const pv = price.replace(/[^\\d.k]/gi, '');
      const pn = /k$/i.test(pv) ? parseFloat(pv) * 1000 : parseFloat(pv);
      if (!isNaN(pn) && pn > 0) e.price = pn;
      data.rows[ck][dt] = e;
      if (!data.cols.includes(dt)) { data.cols.push(dt); data.cols.sort(); }
      await ghWrite('data.json', JSON.stringify(data, null, 2),
        `Mag data.json manual edit: ${dt} ${ck.split('|')[1]}`,
        msg => document.getElementById('prog-edit').textContent = msg);
      document.getElementById('prog-edit').textContent = '';
      showMsg('msg-edit','ok',`✓ 已更新 ${dt} ${ck.split('|')[1]}（index.html＋data.json）`);
    } catch(e2) {
      document.getElementById('prog-edit').textContent = '';
      showMsg('msg-edit','warn',`✓ index.html 已更新，但 data.json 同步失敗：${e2.message}`);
    }"""),
    ]
    for a, b in reps:
        if h.count(a) != 1: sys.exit('mag_admin.html 結構不符，未修改：' + a[:50])
    for a, b in reps: h = h.replace(a, b)
    open('mag_admin.html', 'w', encoding='utf-8').write(h)
    print('mag_admin.html：已修（代替 D1 參照＋手工修改同步 data.json）')
def patch_data():
    raw = open('data.json', encoding='utf-8').read()
    i = raw.find('"coins|PUMP"')
    j = raw.find('"2026-10-03"', i) if i >= 0 else -1
    if j < 0: print('data.json：找不到 PUMP 2026-10-03，跳過'); return
    k = raw.index('}', j); blk = raw[j:k]
    if '"jin-tp"' in blk and '止盈多' in blk: print('data.json：PUMP 2026-10-03 已正確，跳過'); return
    old = '"kd": "jin",'
    if blk.count(old) != 1: sys.exit('data.json：PUMP 2026-10-03 的內容與預期不符，未修改：' + blk)
    ind = blk[blk.rfind('\n', 0, blk.index(old)) + 1:blk.index(old)]          # 沿用原縮排，只改這兩行
    new = blk.replace(old, '"kd": "jin-tp",\n' + ind + '"jl": "止盈多",')
    open('data.json', 'w', encoding='utf-8').write(raw[:j] + new + raw[k:])
    json.loads(raw[:j] + new + raw[k:])
    print('data.json：PUMP 2026-10-03 → kd=jin-tp、jl=止盈多')
patch_admin(); patch_data()

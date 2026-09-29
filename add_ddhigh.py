#!/usr/bin/env python3
"""add_ddhigh.py — 為 mag-otc 加「進場期距高點」顯示（2026-09-29）
  index.html    : 在 </body> 前加 <script id="ddhigh">（純顯示，不改任何 mag/brk/period/價格數據）
  mag_admin.html: 價格表加「距高點」預覽欄
可重複執行（已加過會跳過）。用法：cd ~/mag-otc && python3 add_ddhigh.py
"""
import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
SNIP = '<script id="ddhigh">\n/* 進場期「距高點」顯示（純顯示，不改任何數據）\n   - 只計 2026-09-29 當日仍在進行、或之後開始的進場期（DDH_FROM）\n   - 高點 = 該進場期內網站價（.pr）的最高收錄價；D1 價為起點\n   - 天數 = 距高點的日曆日（與網站 Dn 同口徑）；創新高 → 歸零，顯示「▲新高」 */\n(function(){\n  var DDH_FROM=\'2026-09-29\';\n  var css=document.createElement(\'style\');\n  css.textContent=\'.ddh{font-size:8px;line-height:1.2;font-weight:700;letter-spacing:0.1px;white-space:nowrap}\'+\n    \'.ddh.nh{color:#34d399}.ddh.d1{color:#a3a3a3}.ddh.d2{color:#fbbf24}.ddh.d3{color:#f87171}\';\n  document.head.appendChild(css);\n  function px(t){\n    t=(t||\'\').trim(); if(!t||t.indexOf(\'---\')>=0) return NaN;\n    var k=/k$/i.test(t)?1e3:(/m$/i.test(t)?1e6:1);\n    var v=parseFloat(t.replace(/[^\\d.\\-]/g,\'\'));\n    return isNaN(v)||v<=0?NaN:v*k;\n  }\n  var RE=/^(\\d{4}-\\d{2}-\\d{2}) [^:]+: [^,]*,[^,]*, (進|退)場期D(\\d+)/;\n  function dayMs(s){return Date.UTC(+s.slice(0,4),+s.slice(5,7)-1,+s.slice(8,10));}\n  function run(){\n    document.querySelectorAll(\'.ddh\').forEach(function(e){e.remove();});\n    document.querySelectorAll(\'#T tbody tr[id^="row_"]\').forEach(function(tr){\n      // 1) 收集有數據的格，按進／退與 Dn 切分期\n      var cells=[],prevPh=null,prevD=0,seg=-1;\n      [].forEach.call(tr.cells,function(td){\n        var m=RE.exec(td.getAttribute(\'title\')||\'\'); if(!m) return;\n        var ph=m[2],d=+m[3];\n        if(ph!==prevPh||d<=prevD) seg++;\n        prevPh=ph; prevD=d;\n        cells.push({td:td,date:m[1],ph:ph,seg:seg});\n      });\n      // 2) 每個進場期：最後一格日期 >= DDH_FROM 才顯示\n      var last={}; cells.forEach(function(c){last[c.seg]=c.date;});\n      var hi=null,hiDate=null,curSeg=-1;\n      cells.forEach(function(c){\n        if(c.ph!==\'進\'||last[c.seg]<DDH_FROM) return;\n        if(c.seg!==curSeg){curSeg=c.seg;hi=null;hiDate=null;}\n        var prDiv=c.td.querySelector(\'.pr\'); if(!prDiv) return;\n        var p=px(prDiv.textContent); if(isNaN(p)) return;\n        var el=document.createElement(\'div\'); el.className=\'ddh\';\n        if(hi===null||p>hi){\n          hi=p; hiDate=c.date; el.className+=\' nh\'; el.textContent=\'▲新高\';\n        }else{\n          var n=Math.round((dayMs(c.date)-dayMs(hiDate))/864e5);\n          var dd=(p/hi-1)*100;\n          el.className+=dd>-5?\' d1\':(dd>-10?\' d2\':\' d3\');\n          el.textContent=\'↓\'+n+\'日 \'+dd.toFixed(1)+\'%\';\n          el.title=\'高點 \'+hiDate+\'（\'+prDiv.textContent.trim()+\' vs 高 \'+hi+\'）\';\n        }\n        prDiv.insertAdjacentElement(\'afterend\',el);\n      });\n    });\n  }\n  run();\n  window.ddhRun=run;\n})();\n</script>\n'
FN = '\n// ── 距高點預覽（與 index.html #ddhigh 同口徑：進場期內網站價最高點、日曆日、創新高歸零）──\nfunction ddPx(t) {\n  t = (t || \'\').trim(); if (!t || t.includes(\'---\')) return NaN;\n  const k = /k$/i.test(t) ? 1e3 : (/m$/i.test(t) ? 1e6 : 1);\n  const v = parseFloat(t.replace(/[^\\d.\\-]/g, \'\'));\n  return isNaN(v) || v <= 0 ? NaN : v * k;\n}\nfunction ddPreview(ck) {\n  const id = ck.replace(\'|\', \'_\'), out = document.getElementById(\'dd-\' + id);\n  if (!out) return;\n  const set = (txt, col) => { out.textContent = txt; out.style.color = col; };\n  const tk = ck.split(\'|\')[1].replace(/[.*+?^${}()|[\\]\\\\]/g, \'\\\\$&\');\n  // 今日期間：先用②解析結果，否則讀 html 內今日格\n  let period = (rows.find(r => r.ck === ck) || {}).period || \'\';\n  if (!period) {\n    const m = new RegExp(`title="${date} ${tk}: [^"]*?((?:進|退)場期D\\\\d+)`).exec(html);\n    if (m) period = m[1];\n  }\n  if (!period.startsWith(\'進場期\')) return set(\'—\', \'#475569\');\n  const dT = getDN(period);\n  // 只掃該行\n  let src = html;\n  const a = html.indexOf(`<tr id="row_${id}"`);\n  if (a >= 0) src = html.slice(a, html.indexOf(\'</tr>\', a));\n  const re = new RegExp(`title="(\\\\d{4}-\\\\d{2}-\\\\d{2}) ${tk}: [^"]*?(進|退)場期D(\\\\d+)[^"]*"[^>]*>[\\\\s\\\\S]*?<div class="pr">([^<]*)</div>`, \'g\');\n  const cells = []; let m, seg = -1, pPh = null, pD = 0;\n  while ((m = re.exec(src)) !== null) {\n    if (m[1] >= date) break;\n    const ph = m[2], d = +m[3];\n    if (ph !== pPh || d <= pD) seg++;\n    pPh = ph; pD = d;\n    cells.push({ date: m[1], ph, d, seg, p: ddPx(m[4]) });\n  }\n  const last = cells[cells.length - 1];\n  const cont = last && last.ph === \'進\' && dT > last.d;   // 今日延續同一進場期\n  let hi = null, hiDate = null;\n  if (cont) cells.filter(c => c.seg === last.seg && !isNaN(c.p)).forEach(c => { if (hi === null || c.p > hi) { hi = c.p; hiDate = c.date; } });\n  const p = ddPx(document.getElementById(\'pr-\' + id)?.value);\n  if (isNaN(p)) return set(hi === null ? \'（新進場期）\' : `高 ${hi}（${hiDate.slice(5)}）`, \'#64748b\');\n  if (hi === null || p > hi) return set(\'▲新高\', \'#34d399\');\n  const n = Math.round((Date.parse(date) - Date.parse(hiDate)) / 864e5);\n  const dd = (p / hi - 1) * 100;\n  set(`↓${n}日 ${dd.toFixed(1)}%（高 ${hi}）`, dd > -5 ? \'#a3a3a3\' : (dd > -10 ? \'#fbbf24\' : \'#f87171\'));\n}\n'
def patch_index():
    h = open('index.html', encoding='utf-8').read()
    if 'id="ddhigh"' in h: print('index.html：已有 ddhigh，跳過'); return
    assert h.count('</body>') == 1, '找不到唯一的 </body>'
    open('index.html', 'w', encoding='utf-8').write(h.replace('</body>', SNIP + '</body>'))
    print('index.html：已加入 ddhigh 顯示腳本')
def patch_admin():
    h = open('mag_admin.html', encoding='utf-8').read()
    if 'function ddPreview' in h: print('mag_admin.html：已有 ddPreview，跳過'); return
    reps = [
      ('<th style="width:140px">價格</th><th>狀態</th></tr>',
       '<th style="width:140px">價格</th><th>狀態</th><th>距高點</th></tr>'),
      ("""      `<td id="ps-${id}" style="font-size:11px;color:#475569">—</td>`;
    tb.appendChild(tr);""",
       """      `<td id="ps-${id}" style="font-size:11px;color:#475569">—</td>` +
      `<td id="dd-${id}" style="font-size:11px;color:#475569;white-space:nowrap">—</td>`;
    tb.appendChild(tr);
    tr.querySelector('input').addEventListener('input', () => ddPreview(ck));
    ddPreview(ck);"""),
      ("document.getElementById('pr-'+id).value = fmt || '';",
       "document.getElementById('pr-'+id).value = fmt || '';\n      ddPreview(ck);"),
      ('// ── 時間選擇器', FN.strip('\n') + '\n\n// ── 時間選擇器'),
    ]
    for a, b in reps:
        if h.count(a) != 1: sys.exit('mag_admin.html 結構不符，未修改：' + a[:60])
    for a, b in reps: h = h.replace(a, b)
    open('mag_admin.html', 'w', encoding='utf-8').write(h)
    print('mag_admin.html：價格表已加「距高點」欄')
patch_index(); patch_admin()

#!/usr/bin/env python3
"""admin_unknown_1004.py — 2026-10-04 mag_admin：未識別標的偵測 ＋ 一鍵新增 ＋ 外置資產名單

 1) 偵測：貼文裡有「場外指數」但對不上任何已知標的的行，用紅框列出；未處理不能寫入（可按「略過」）。
    同一標的出現多於一次也會警告。未識別那一行不再被接到上一個標的後面。
 2) 一鍵新增：在紅框填代號／分組／價格來源／交易對 → 自動開行、加勾選框、加入名單，並重新解析。
 3) 名單外置：新增的標的存入 repo 的 assets_extra.json，admin 每次連線時讀取；index.html 缺行會自動補回。

只改 mag_admin.html。要先行過 add_aave_1004.py（需要它的「空格佔位」邏輯）。可重複執行。
用法：cd ~/mag-otc && python3 admin_unknown_1004.py
"""
import sys

def die(m): sys.exit('✗ ' + m + '（未修改任何檔案）')

REPS = []
def R(old, new, what): REPS.append((old, new, what))

# ── ② 卡片：紅框位置 ─────────────────────────────────────────────────────────
R('''    <span id="parse-hint" style="font-size:11px;color:#475569"></span>
  </div>
''', '''    <span id="parse-hint" style="font-size:11px;color:#475569"></span>
  </div>
  <div id="unk-box" style="display:none;margin-top:10px"></div>
''', '② 卡片 parse-hint')

# ── 狀態＋外置名單 ─────────────────────────────────────────────────────────
R('''// ── GitHub API ─''', r'''// ── 2026-10-04：外置資產名單（assets_extra.json）＋未識別標的 ─────────────────
const EXTRA_PATH = 'assets_extra.json';
// [分組名稱（index.html 的 data-g）, ck 前綴, 預設價格來源]
const GROUPS  = [['主要幣種','coins','BINANCE'], ['美股','stocks','BYBIT_LINEAR'], ['宏觀','macro','EMPTY'],
                 ['A股/ETF','macro','CN'], ['大宗商品','commodities','YAHOO']];
const SOURCES = ['BINANCE','BYBIT','BYBIT_LINEAR','KUCOIN','YAHOO','YAHOO_KRW','CN','EMPTY'];
let EXTRA  = { assets: [] };   // assets_extra.json 的內容
let UNK    = [];               // 本次貼文裡未識別的標的 [{name,text,mag,brk,period}]
let DUP    = [];               // 同一標的出現多於一次 [{ck,text}]
let unkAck = false;            // 已按「略過未識別」

async function ghReadExtra() {
  const r = await ghReq(`/repos/${REPO}/contents/${EXTRA_PATH}?ref=${BRANCH}`, { cache: 'no-store' });
  if (r.status === 404) return { assets: [] };
  if (!r.ok) throw new Error('讀取 ' + EXTRA_PATH + ' 失敗 ' + r.status);
  const { content } = await r.json();
  const bytes = Uint8Array.from(atob((content || '').replace(/\n/g, '')), c => c.charCodeAt(0));
  const j = JSON.parse(new TextDecoder('utf-8').decode(bytes));
  return (j && Array.isArray(j.assets)) ? j : { assets: [] };
}

// 把一個外置標的加入記憶體中的名單（ASSETS、NAME_TO_CK）
function registerAsset(a) {
  if (!ASSETS.some(x => x[0] === a.ck)) ASSETS.push([a.ck, a.name, a.display, a.symbol || null, a.source]);
  for (const n of (a.aliases || [])) if (n) NAME_TO_CK[n] = a.ck;
}

// index.html 沒有這個標的的行 → 補一行（全部空格）＋資產勾選框；已有就原樣返回
function ensureAssetRow(h, a) {
  const rid = 'row_' + a.ck.replace('|', '_');
  if (h.includes(`<tr id="${rid}"`)) return h;
  const thead = h.slice(h.indexOf('<thead'), h.indexOf('</thead>'));
  const ncol  = (thead.match(/<th[ >]/g) || []).length - 1;          // 日期欄數（不含「資產」）
  if (ncol < 1) throw new Error('thead 結構異常');
  const dts   = thead.match(/title="\d{4}-\d{2}-\d{2}"/g) || [];
  const lastD = dts.length ? dts[dts.length - 1].slice(7, 17) : '';
  // 最後一欄用帶日期的佔位格：之後同一日重跑②③時會被清走再補，不會多出一格
  const cells = '<td class="mt"></td>'.repeat(ncol - 1) +
                (lastD ? `<td class="mt" data-d="${lastD}"></td>` : '<td class="mt"></td>');
  const g  = a.group || (GROUPS.find(x => x[1] === a.ck.split('|')[0]) || GROUPS[0])[0];
  const re = new RegExp('<tr id="(row_[^"]+)" data-g="' + g.replace(/[.*+?^${}()|[\]\\\/]/g, '\\$&') + '"', 'g');
  let m, last = null;
  while ((m = re.exec(h)) !== null) last = m;
  if (!last) throw new Error('index.html 找不到分組：' + g);
  const nextTr = h.indexOf('<tr', last.index + 5);
  const pos    = nextTr !== -1 ? nextTr : h.indexOf('</tbody>', last.index);
  const row    = `<tr id="${rid}" data-g="${g}"><td class="nm">${a.display}</td>${cells}\n</tr>`;
  h = h.slice(0, pos) + row + h.slice(pos);
  const acId = `<div class="ac" id="ac_${last[1]}">`;
  const ai   = h.indexOf(acId);
  if (ai !== -1) {
    const ae = h.indexOf('</div>', ai) + 6;
    h = h.slice(0, ae) + `\n  <div class="ac" id="ac_${rid}"><input type="checkbox" id="cb_${rid}" checked onchange="togA('${rid}',this.checked)"><label for="cb_${rid}">${a.display}</label></div>` + h.slice(ae);
  }
  return h;
}

// 把貼文逐行分組。回傳 { groups:[{ck,text}], unknown:[{name,text}] }
//   已知標的名稱的行 → 開新組；有「場外指數」但沒有已知名稱、而當前組已經有場外指數 → 未識別標的（另開一組，不接到上一個標的）
function groupLines(rawLines) {
  const MAG = /[场場]外指[数數]?\s*\d+/;
  const groups = [], unknown = [];
  let cur = null, pending = '';
  for (const line of rawLines) {
    const ck = findCk(line), isMag = MAG.test(line);
    if (ck) { cur = { ck, text: line, hasMag: isMag }; groups.push(cur); pending = ''; continue; }
    if (isMag && (!cur || cur.hasMag)) {
      const u = { name: (line.split(/[场場]外/)[0].trim() || pending).replace(/[：:，,\s]+$/, ''), text: line };
      unknown.push(u); cur = { ck: null, text: line, hasMag: true, unk: u }; groups.push(cur); pending = ''; continue;
    }
    if (cur) { cur.text += ' ' + line; if (isMag) cur.hasMag = true; if (cur.unk) cur.unk.text = cur.text; }
    if (!isMag) pending = line;
  }
  return { groups, unknown };
}

function parseFields(text) {
  const mm = text.match(/场外指数\s*(\d+)/) || text.match(/場外指數\s*(\d+)/)
          || text.match(/场外指\s*(\d+)/)   || text.match(/場外指\s*(\d+)/);
  const bm = text.match(/爆破指数\s*(-?\d+)/) || text.match(/爆破指數\s*(-?\d+)/);
  return { mag: mm ? +mm[1] : null, brk: bm ? +bm[1] : null, period: extractPeriod(text) };
}

function escH(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c])); }

function renderUnknown() {
  const box = document.getElementById('unk-box');
  if (!box) return;
  if (!UNK.length && !DUP.length) { box.style.display = 'none'; box.innerHTML = ''; return; }
  const inp = 'background:#0f1117;border:1px solid #374151;border-radius:5px;color:#e2e8f0;padding:5px 8px;font-size:12px;width:100%';
  let out = '';
  UNK.forEach((u, i) => {
    const code = ((u.name || '').match(/[A-Za-z0-9_]+/) || [''])[0].toUpperCase();
    out += `<div class="ev" style="border:1px solid #7f1d1d;padding:10px">
      <div style="color:#fca5a5">⚠️ 未識別標的：<b>${escH(u.name || '（無名稱）')}</b>　場外 ${u.mag ?? '?'}／爆破 ${u.brk ?? '?'}／${escH(u.period || '期別?')}</div>
      <div style="font-size:11px;color:#64748b;margin:4px 0 8px;word-break:break-all">原文：${escH(u.text)}</div>
      <div class="row-g">
        <div style="min-width:90px"><label>代號（英數大寫）</label><input type="text" id="unk-code-${i}" value="${escH(code)}" style="${inp}" oninput="unkSync(${i})"></div>
        <div style="min-width:110px"><label>貼文裡的名稱</label><input type="text" id="unk-alias-${i}" value="${escH(u.name)}" style="${inp}"></div>
        <div style="min-width:100px"><label>分組</label><select id="unk-grp-${i}" style="${inp}" onchange="unkSync(${i},true)">${GROUPS.map((g, k) => `<option value="${k}">${g[0]}</option>`).join('')}</select></div>
        <div style="min-width:120px"><label>價格來源</label><select id="unk-src-${i}" style="${inp}" onchange="unkSync(${i})">${SOURCES.map(s => `<option value="${s}">${s === 'EMPTY' ? 'EMPTY（無價）' : s === 'CN' ? 'CN（---）' : s}</option>`).join('')}</select></div>
        <div style="min-width:110px"><label>交易對／代碼</label><input type="text" id="unk-sym-${i}" value="${escH(code ? code + 'USDT' : '')}" style="${inp}"></div>
        <div style="flex:0"><button class="btn-g" onclick="addUnknown(${i})" id="unk-btn-${i}">＋ 新增此標的</button></div>
      </div>
      <div id="unk-msg-${i}" class="prog"></div>
    </div>`;
  });
  DUP.forEach(d => {
    const nm = (ASSETS.find(x => x[0] === d.ck) || [,, d.ck])[2];
    out += `<div class="ev" style="border:1px solid #92400e;padding:10px;color:#fcd34d">⚠️ <b>${escH(nm)}</b> 在貼文裡出現多於一次，只採用第一次。可能是新標的名稱包含了「${escH(nm)}」，請核對③表格裡 ${escH(nm)} 的數字，有錯就直接在表格改。
      <div style="font-size:11px;color:#64748b;margin-top:4px;word-break:break-all">第二次的原文：${escH(d.text)}</div></div>`;
  });
  out += `<div style="margin-top:6px;display:flex;gap:8px;align-items:center">
      <button class="btn-o" onclick="unkAck=true;this.disabled=true;document.getElementById('unk-ack').textContent='已略過：未識別的標的今次不會寫入；重複的只用第一次'">略過，照樣寫入</button>
      <span id="unk-ack" style="font-size:11px;color:#fcd34d">${unkAck ? '已略過' : '未處理之前不能寫入 GitHub'}</span></div>`;
  box.innerHTML = out; box.style.display = '';
}

// 代號或分組改了 → 帶出預設的價格來源與交易對
function unkSync(i, grpChanged) {
  const code = document.getElementById('unk-code-' + i).value.trim().toUpperCase();
  const src  = document.getElementById('unk-src-' + i);
  if (grpChanged) src.value = GROUPS[+document.getElementById('unk-grp-' + i).value][2];
  const sym  = document.getElementById('unk-sym-' + i);
  const usdt = ['BINANCE','BYBIT','BYBIT_LINEAR'].includes(src.value);
  if (src.value === 'CN' || src.value === 'EMPTY') sym.value = '';
  else if (usdt) sym.value = code ? code + 'USDT' : '';
  else if (/USDT$/.test(sym.value)) sym.value = '';
}

function refreshEditAssets() {
  const sel = document.getElementById('edit-asset');
  if (!sel) return;
  const cur = sel.value;
  sel.innerHTML = ASSETS.map(([ck,,d]) => `<option value="${ck}">${d}</option>`).join('');
  if (cur) sel.value = cur;
}

async function addUnknown(i) {
  const msg  = t => { const e = document.getElementById('unk-msg-' + i); if (e) { e.textContent = t; e.style.color = '#fca5a5'; } };
  const code  = document.getElementById('unk-code-' + i).value.trim().toUpperCase();
  const alias = document.getElementById('unk-alias-' + i).value.trim();
  const [gname, cat] = GROUPS[+document.getElementById('unk-grp-' + i).value];
  const src   = document.getElementById('unk-src-' + i).value;
  const sym   = document.getElementById('unk-sym-' + i).value.trim();
  if (!/^[A-Z0-9_]{1,16}$/.test(code)) return msg('代號只可以用英文字母、數字、底線（最多 16 字）');
  if (!alias) return msg('請填貼文裡的名稱（用來識別這個標的）');
  if (src !== 'CN' && src !== 'EMPTY' && !sym) return msg('這個價格來源需要交易對／代碼');
  const ck = cat + '|' + code;
  if (ASSETS.some(x => x[0] === ck) || html.includes(`<tr id="row_${cat}_${code}"`)) return msg(code + ' 已經存在');
  const clash = Object.keys(NAME_TO_CK).find(n => n.toUpperCase() === alias.toUpperCase());
  if (clash) return msg('名稱「' + alias + '」已經屬於另一個標的（' + NAME_TO_CK[clash] + '）');
  const a = { ck, name: code, display: code, symbol: sym || null, source: src,
              aliases: [...new Set([alias, code])], group: gname, added: date };
  const btn = document.getElementById('unk-btn-' + i); if (btn) btn.disabled = true;
  try {
    const newHtml = ensureAssetRow(html, a);                  // 先確認開得到行，再寫名單
    const latest  = await ghReadExtra();                      // 以 GitHub 上最新的名單為準
    if (latest.assets.some(x => x.ck === ck)) throw new Error(code + ' 已在 ' + EXTRA_PATH);
    const next = { assets: [...latest.assets, a] };
    await ghWrite(EXTRA_PATH, JSON.stringify(next, null, 2) + '\n', `Mag admin: add asset ${code}`,
      t => { const e = document.getElementById('unk-msg-' + i); if (e) { e.textContent = t; e.style.color = '#64748b'; } });
    EXTRA = next; next.assets.forEach(registerAsset); html = newHtml;
    refreshEditAssets();
    parseData();                                              // 重新解析：新標的會出現在③
    const hint = document.getElementById('parse-hint');
    if (hint) hint.textContent += `｜✓ 已新增 ${code}（行已加入，寫入 GitHub 時一併儲存）`;
  } catch (e) {
    if (btn) btn.disabled = false;
    msg('❌ ' + e.message);
  }
}

// ── GitHub API ─''', 'GitHub API 註解（插入新函數）')

# ── connect：讀外置名單 ─────────────────────────────────────────────────────
R('''    html = await ghReadHtml();
    localStorage.setItem('mag_pat', PAT);
''', '''    html = await ghReadHtml();
    let extraNote = '';
    try {
      EXTRA = await ghReadExtra();
      for (const a of EXTRA.assets) { registerAsset(a); html = ensureAssetRow(html, a); }
      if (EXTRA.assets.length) extraNote = ` ｜ 外置名單 ${EXTRA.assets.length} 個`;
    } catch (e) { extraNote = ' ｜ ⚠️ 外置名單讀取失敗：' + e.message; }
    localStorage.setItem('mag_pat', PAT);
''', 'connect 讀 index.html')
R('''      showMsg('msg1', 'ok', `✓ 連線成功 (${login})，${sz} KB ｜ ⚠️ ${today} 已有數據 → 可直接執行④，或重新跑②③覆蓋`);''',
  '''      showMsg('msg1', 'ok', `✓ 連線成功 (${login})，${sz} KB${extraNote} ｜ ⚠️ ${today} 已有數據 → 可直接執行④，或重新跑②③覆蓋`);''', 'connect 訊息 1')
R('''      showMsg('msg1', 'ok', `✓ 連線成功 (${login})，index.html ${sz} KB`);''',
  '''      showMsg('msg1', 'ok', `✓ 連線成功 (${login})，index.html ${sz} KB${extraNote}`);''', 'connect 訊息 2')

# ── parseData：分組＋未識別 ─────────────────────────────────────────────────
R('''  const groups = [];   // [{ck, text}]
  let cur = null;
  for (const line of rawLines) {
    const ck = findCk(line);
    if (ck) {
      cur = { ck, text: line };
      groups.push(cur);
    } else if (cur) {
      cur.text += ' ' + line;
    }
  }

  const found = new Map();
  for (const { ck, text } of groups) {
    if (found.has(ck)) continue;
''', '''  // 2026-10-04：未識別的標的另開一組（不再接到上一個標的後面），並列出來
  const { groups, unknown } = groupLines(rawLines);
  UNK = unknown.map(u => ({ ...u, ...parseFields(u.text) }));
  DUP = []; unkAck = false;

  const found = new Map();
  for (const { ck, text } of groups) {
    if (!ck) continue;
    if (found.has(ck)) { const f = parseFields(text); if (f.mag !== null && f.brk !== null && f.period) DUP.push({ ck, text }); continue; }
''', 'parseData 分組')
R('''  document.getElementById('parse-hint').textContent = `識別 ${rows.filter(r=>r.mag!=='').length}/${ASSETS.length}`;
''', '''  document.getElementById('parse-hint').textContent = `識別 ${rows.filter(r=>r.mag!=='').length}/${ASSETS.length}` +
    (UNK.length ? `｜⚠️ 未識別 ${UNK.length} 個（見下方紅框）` : '') + (DUP.length ? `｜⚠️ 重複 ${DUP.length} 個` : '');
  renderUnknown();
''', 'parse-hint')

# ── commitData：未處理不能寫入 ───────────────────────────────────────────────
R('''  if (!n) { showMsg('msg3','err','沒有有效數據'); return; }
''', '''  if (!n) { showMsg('msg3','err','沒有有效數據'); return; }
  if ((UNK.length || DUP.length) && !unkAck) {
    showMsg('msg3','err',`貼文裡有 ${UNK.length} 個未識別標的、${DUP.length} 個重複（見②下方紅框）。請先處理，或按「略過，照樣寫入」。`);
    return;
  }
''', 'commitData 開頭')


def main():
    a = open('mag_admin.html', encoding='utf-8').read()
    if "const EXTRA_PATH = 'assets_extra.json';" in a:
        print('mag_admin.html：已是新版，跳過'); return
    if 'Step 1b（2026-10-04）' not in a:
        die('mag_admin.html 未有「空格佔位」邏輯，請先行 add_aave_1004.py')
    for old, new, what in REPS:
        if a.count(old) != 1: die('%s：預期 1 處，找到 %d 處' % (what, a.count(old)))
    for old, new, what in REPS: a = a.replace(old, new)
    open('mag_admin.html', 'w', encoding='utf-8').write(a)
    print('mag_admin.html：已加入 未識別標的偵測／一鍵新增／外置名單（assets_extra.json）')

if __name__ == '__main__':
    main()

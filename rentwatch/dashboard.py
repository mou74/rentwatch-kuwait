"""Generates a static, RTL Arabic dashboard (single HTML file) from the database."""
import json
from datetime import datetime

SOURCE_LABELS = {"4sale": "4Sale", "opensooq": "OpenSooq", "boshamlan": "بوشملان"}

TEMPLATE = r"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="600">
<title>مراقب الشقق</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#f4f5f7;--card:#fff;--text:#1a1d21;--muted:#6b7280;--line:#e5e7eb;--accent:#0f6fb5;--accent-ink:#fff;--star:#f59e0b;--star-bg:#fff7e6;--chip:#eef2f6}
:root:not([data-theme="light"]){color-scheme:light dark}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f1115;--card:#171a21;--text:#e7e9ee;--muted:#9aa3b2;--line:#262b35;--accent:#4ea3e8;--accent-ink:#0b1320;--star:#fbbf24;--star-bg:#2a2210;--chip:#222733}}
:root[data-theme="dark"]{--bg:#0f1115;--card:#171a21;--text:#e7e9ee;--muted:#9aa3b2;--line:#262b35;--accent:#4ea3e8;--accent-ink:#0b1320;--star:#fbbf24;--star-bg:#2a2210;--chip:#222733}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:"IBM Plex Sans Arabic",-apple-system,"Segoe UI",Tahoma,Arial,sans-serif;line-height:1.6}
header{position:sticky;top:0;z-index:5;background:var(--card);border-bottom:1px solid var(--line);padding:12px 16px}
.wrap{max-width:1180px;margin:0 auto;padding:0 16px}
h1{font-size:20px;margin:0 0 4px}
.sub{color:var(--muted);font-size:13px}
.stats{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0 2px}
.stat{background:var(--chip);border-radius:10px;padding:6px 12px;font-size:13px}
.stat b{font-size:16px;margin-inline-start:4px}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}
.tab{border:1px solid var(--line);background:var(--card);color:var(--text);padding:8px 14px;border-radius:999px;cursor:pointer;font:inherit;font-size:14px}
.tab.active{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}
select,input{font:inherit;font-size:14px;padding:7px 10px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--text)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;padding-bottom:40px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column}
.card.strong{border-color:var(--star);box-shadow:0 0 0 2px var(--star-bg)}
.img{aspect-ratio:4/3;background:var(--chip);display:block;width:100%;object-fit:cover}
.noimg{aspect-ratio:4/3;background:var(--chip);display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:40px}
.body{padding:12px 14px;display:flex;flex-direction:column;gap:8px;flex:1}
.title{font-weight:600;font-size:15px;line-height:1.5}
.meta{display:flex;gap:6px;flex-wrap:wrap;font-size:13px;color:var(--muted)}
.chip{background:var(--chip);border-radius:8px;padding:2px 8px}
.price{font-weight:700;color:var(--accent);font-size:16px}
.badge{display:inline-block;background:var(--star-bg);color:var(--star);border:1px solid var(--star);border-radius:999px;padding:2px 10px;font-size:12px;font-weight:600}
.desc{font-size:13px;color:var(--text);opacity:.85;white-space:pre-wrap;max-height:7.5em;overflow:hidden}
.actions{display:flex;gap:8px;margin-top:auto;padding-top:6px}
.btn{flex:1;text-align:center;text-decoration:none;padding:9px 10px;border-radius:10px;font-weight:600;font-size:14px;background:var(--accent);color:var(--accent-ink)}
.btn.ghost{background:var(--chip);color:var(--text)}
.time{font-size:12px;color:var(--muted)}
.empty{padding:40px;text-align:center;color:var(--muted)}
.new{position:absolute;inset-inline-start:10px;top:10px;background:#16a34a;color:#fff;font-size:11px;padding:2px 8px;border-radius:999px}
.rel{position:relative}
footer{color:var(--muted);font-size:12px;text-align:center;padding:20px}
</style>
</head>
<body>
<header><div class="wrap">
<h1>🏠 مراقب شقق الإيجار – الكويت</h1>
<div class="sub">__CRITERIA__</div>
<div class="stats">
<span class="stat">⭐ تشطيب جديد / أول ساكن <b id="s-strong"></b></span>
<span class="stat">✅ كل المطابقات <b id="s-matched"></b></span>
<span class="stat">📥 إعلانات مفحوصة <b id="s-total"></b></span>
<span class="stat">🕒 آخر فحص <b id="s-last"></b></span>
</div>
</div></header>
<main class="wrap">
<div class="tabs">
<button class="tab active" data-tab="strong">⭐ تشطيب جديد / أول ساكن</button>
<button class="tab" data-tab="matched">✅ كل المطابقات</button>
<button class="tab" data-tab="all">📥 آخر الإعلانات (بدون فلترة)</button>
</div>
<div class="filters">
<select id="f-source"><option value="">كل المصادر</option></select>
<select id="f-area"><option value="">كل المناطق</option></select>
<input id="f-q" placeholder="بحث في النص…">
</div>
<div id="grid" class="grid"></div>
<div id="empty" class="empty" hidden>لا توجد إعلانات هنا بعد. الفحص التالي خلال __INTERVAL__ دقائق.</div>
</main>
<footer>يتم الفحص تلقائياً كل __INTERVAL__ دقائق من 4Sale و OpenSooq و بوشملان · آخر توليد للصفحة: __GENERATED__</footer>
<script>
const DATA = __DATA__;
const LABELS = __LABELS__;
let tab = 'strong';
const $ = s => document.querySelector(s);
function rel(iso){ if(!iso) return ''; const d=new Date(iso); if(isNaN(d)) return iso; const m=Math.round((Date.now()-d)/60000);
  if(m<1) return 'الآن'; if(m<60) return `قبل ${m} دقيقة`; const h=Math.round(m/60); if(h<24) return `قبل ${h} ساعة`; const dd=Math.round(h/24); return dd===1?'أمس':`قبل ${dd} يوم`; }
function esc(s){ return (s||'').replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function isNew(l){ return (Date.now()-new Date(l.first_seen))<6*3600*1000; }
function render(){
  const src=$('#f-source').value, area=$('#f-area').value, q=$('#f-q').value.trim();
  let rows = DATA.filter(l => tab==='all' ? true : tab==='matched' ? l.matched : l.strong);
  if(src) rows=rows.filter(l=>l.source===src); if(area) rows=rows.filter(l=>l.area===area);
  if(q) rows=rows.filter(l=>((l.title||'')+' '+(l.description||'')+' '+(l.district||'')).includes(q));
  $('#grid').innerHTML = rows.map(l=>`
   <article class="card ${l.strong?'strong':''}">
    <div class="rel">${l.image?`<img class="img" loading="lazy" src="${esc(l.image)}" alt="">`:`<div class="noimg">🏢</div>`}${isNew(l)?'<span class="new">جديد</span>':''}</div>
    <div class="body">
      <div class="title">${esc(l.title)}</div>
      ${l.is_new_finish?'<div><span class="badge">⭐ تشطيب جديد / أول ساكن</span></div>':''}
      <div class="meta"><span class="price">${l.price?l.price+' د.ك':'السعر غير مذكور'}</span><span class="chip">📍 ${esc(l.district||l.area||'')}</span><span class="chip">🛏 ${l.rooms??'?'} غرف</span><span class="chip">${LABELS[l.source]||l.source}</span></div>
      <div class="desc">${esc(l.description)}</div>
      <div class="time">نُشر ${rel(l.posted_at)||'—'} · رُصد ${rel(l.first_seen)}${l.matched?'':' · '+esc(l.reasons||'')}</div>
      <div class="actions"><a class="btn" target="_blank" rel="noopener" href="${esc(l.url)}">افتح الإعلان</a>${l.phone?`<a class="btn ghost" href="tel:${esc(String(l.phone))}">📞 اتصال</a>`:''}</div>
    </div></article>`).join('');
  $('#empty').hidden = rows.length>0;
}
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));b.classList.add('active');tab=b.dataset.tab;render();});
['#f-source','#f-area','#f-q'].forEach(s=>$(s).addEventListener('input',render));
[...new Set(DATA.map(l=>l.source))].forEach(s=>$('#f-source').insertAdjacentHTML('beforeend',`<option value="${s}">${LABELS[s]||s}</option>`));
[...new Set(DATA.map(l=>l.area).filter(Boolean))].forEach(a=>$('#f-area').insertAdjacentHTML('beforeend',`<option value="${esc(a)}">${esc(a)}</option>`));
const STATS=__STATS__; $('#s-strong').textContent=STATS.strong; $('#s-matched').textContent=STATS.matched; $('#s-total').textContent=STATS.total;
$('#s-last').textContent = STATS.last_run ? rel(STATS.last_run.finished_at) : '—';
render();
</script>
</body></html>
"""


def build(store, cfg, out_path):
    rows = {r["id"]: r for r in store.matches(400)}
    for r in store.recent_all(300):
        rows.setdefault(r["id"], r)
    data = sorted(rows.values(), key=lambda r: (r["first_seen"] or ""), reverse=True)
    for r in data:
        r.pop("notified", None)
    areas = "، ".join(a["name"] for a in cfg["areas"])
    criteria = (f"المناطق: {areas} · الميزانية {cfg['price_min']}–{cfg['price_max']} د.ك · {cfg['rooms']} غرف"
                f" · تشطيب جديد أو أول ساكن")
    html = (TEMPLATE
            .replace("__DATA__", json.dumps(data, ensure_ascii=False))
            .replace("__LABELS__", json.dumps(SOURCE_LABELS, ensure_ascii=False))
            .replace("__STATS__", json.dumps(store.stats(), ensure_ascii=False))
            .replace("__CRITERIA__", criteria)
            .replace("__INTERVAL__", str(cfg.get("interval_minutes", 30)))
            .replace("__GENERATED__", datetime.now().strftime("%Y-%m-%d %H:%M")))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path

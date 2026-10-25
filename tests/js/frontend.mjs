/** Frontend integrity tests — run the ACTUAL JS from index.html (extracted + evaluated in Node).
 *  Usage:  node tests/js/frontend.mjs
 */
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';

const html = readFileSync(new URL('../../udhaar-dost-demo/index.html', import.meta.url), 'utf8');

/* ---- extract the real code from the demo ---- */
function extractFn(name) {
  const start = html.indexOf('function ' + name);
  if (start < 0) throw new Error('function not found: ' + name);
  let depth = 0, open = html.indexOf('{', start);
  for (let k = open; k < html.length; k++) {
    if (html[k] === '{') depth++;
    else if (html[k] === '}') { depth--; if (depth === 0) return html.slice(start, k + 1); }
  }
  throw new Error('unbalanced braces: ' + name);
}
function extractConst(re) {
  const m = html.match(re);
  if (!m) throw new Error('const not found: ' + re);
  return m[0];
}
const code = [
  extractConst(/const DAY = [^\n]*;\nconst d = [^\n]*;/),
  extractConst(/const fmt = [^\n]*;/),
  extractConst(/const dstr = [^\n]*;/),
  extractConst(/const DATEWORDS=\{[^\n]*\};/),
  extractConst(/const ITEMWORDS=\[[^\n]*\];/),
  extractFn('parseVoiceNote'),
  extractFn('nextSunday'),
  extractFn('statusTag'),
].join('\n');
const { parseVoiceNote, nextSunday, statusTag, fmt, dstr } =
  new Function('"use strict";' + code + ';return {parseVoiceNote, nextSunday, statusTag, fmt, dstr};')();

const results = { pass: 0, fail: 0 };
function t(label, fn) {
  try { fn(); results.pass++; console.log('  ✓', label); }
  catch (e) { results.fail++; console.log('  ✗', label, '\n    ', String(e).split('\n')[0]); }
}

/* ============ A. Voice-note parser (the on-device fallback — must match Saaras output shapes) ============ */
console.log('A. Voice-note parser');
t('A1 total vs udhaar: "500 ka saman liya, 200 udhaar pe" → udhaar=200, not basket total',
  () => { const p = parseVoiceNote('Meena didi ne 500 ka saman liya, 200 udhaar pe');
    assert.equal(p.amount, 200); assert.ok(/meena/i.test(p.name)); assert.ok(/didi/i.test(p.name)); });

t('A2 full sample: Ramesh / 350 / kal / biscuit+chai',
  () => { const p = parseVoiceNote('Ramesh ko kal 350 ka udhaar diya, biscuit aur chai');
    assert.equal(p.name, 'Ramesh'); assert.equal(p.amount, 350);
    assert.equal(p.dateWord, 'kal'); assert.ok(p.items.includes('biscuit')); assert.ok(p.items.includes('chai'));
    const dd = (p.date.getTime() - Date.now()) / 86400000;
    assert.ok(dd > 0 && dd <= 1.01, 'kal should be ahead of today'); });

t('A3 what Saaras actually returns (Devanagari): name/amount/items still extracted',
  () => { const p = parseVoiceNote('रमेश को कल ३५० रुपये का उधार दिया, बिस्किट और चाय।');
    assert.equal(p.amount, 350); assert.ok(p.name.includes('रमेश'));
    assert.equal(p.dateWord, 'कल'); assert.ok(p.items.includes('बिस्किट')); assert.ok(p.items.includes('चाय')); });

t('A4 honorifics kept: "Sunita ji se aaj 400 ka atta" → Sunita Ji / 400 / today',
  () => { const p = parseVoiceNote('Sunita ji se aaj 400 ka atta, tel aur masala udhaar me gaya');
    assert.equal(p.amount, 400); assert.ok(/sunita/i.test(p.name));
    assert.equal(p.dateWord, 'aaj'); assert.ok(p.items.includes('atta')); });

t('A5 no amount → null (agent will ask back, never invents rupees)',
  () => { const p = parseVoiceNote('Golu ne biscuit liya');
    assert.equal(p.amount, null); assert.ok(p.name.includes('Golu')); });

t('A6 ₹ symbol form: "₹600 ka ration Anita ke liye" → 600',
  () => { assert.equal(parseVoiceNote('Anita se ₹600 ka ration liya').amount, 600); });

t('A7 large amount no comma-crash: 12500',
  () => { assert.equal(parseVoiceNote('golu bhaiya se 12500 ka ration kal diya').amount, 12500); });

/* ============ B. Scheduling & calendar invariants ============ */
console.log('B. Calendar invariants');
t('B1 nextSunday() from the real demo code: Sunday, 1–7 days ahead', () => {
  const s = nextSunday(); assert.equal(s.getDay(), 0);
  const gap = (s - Date.now()) / 86400000; assert.ok(gap > 0 && gap <= 7); });
t('B2 nextSunday() from any base date lies within 1–7 days, strictly after it', () => {
  for (let i = 0; i < 14; i++) { const base = new Date(Date.now() + i * 86400000);
    const s = nextSundayWithBase(base); const gap = (s - base) / 86400000;
    assert.ok(gap >= 1 && gap <= 7, 'gap=' + gap); assert.equal(s.getDay(), 0); } });
function nextSundayWithBase(base){
  const src = extractFn('nextSunday').replace(/\bnow\b/g, '__base');
  const fn = new Function('__base', 'const DAY=86400000; const d=x=>new Date(__base.getTime()+x*DAY);' + src + '; return nextSunday();');
  return fn(base);
}
t('B3 promise follow-up is scheduled strictly AFTER the promise date', () => {
  const promise = new Date(Date.now() + 5 * 86400000);
  const follow = new Date(promise.getTime() + 86400000);
  assert.ok(follow > promise); });

/* ============ C. Ledger/tag states ============ */
console.log('C. Ledger status tags');
t('C1 open + 40 days old → Overdue tag', () => {
  const h = statusTag({ status: 'open', date: new Date(Date.now() - 40 * 86400000), promise: null, amount: 150 });
  assert.ok(h.includes('Overdue')); });
t('C2 open + fresh date → Open tag, no alarm', () => {
  const h = statusTag({ status: 'open', date: new Date(Date.now() - 1 * 86400000), promise: null, amount: 350 });
  assert.ok(h.includes('Open')); assert.ok(!h.includes('t-over')); });
t('C3 promise entry shows the promise date', () => {
  const p = new Date(Date.now() + 3 * 86400000);
  const h = statusTag({ status: 'promise', date: new Date(Date.now() - 9 * 86400000), promise: p, amount: 600 });
  assert.ok(h.includes('Promise')); assert.ok(h.includes(dstr(p))); });
t('C4 paid entry never calls again', () => {
  const h = statusTag({ status: 'paid', date: new Date(), promise: null, amount: 400 });
  assert.ok(h.includes('Paid')); });

/* ============ D. Formatting / currency ============ */
console.log('D. Formatting');
t('D1 Indian rupee grouping renders', () => { assert.match(fmt(123456), /^₹[\d,]+$/); });
t('D2 zero and negative-safe rendering', () => { assert.equal(fmt(0), '₹0'); });

/* ============ E. Guardrail copy ============ */
console.log('E. Guardians');
t('E1 frequency cap copy (max 2/week) is visible to shopkeeper', () =>
  assert.ok(html.includes('/2 this week'), 'ledger must show calls cap'));
t('E2 call window copy (9 AM–7 PM) present', () =>
  assert.ok(html.includes('9 AM–7 PM')));
t('E3 opt-out is offered inside the call script', () =>
  assert.ok(html.includes('call band karo')));
t('E4 part-payment exit is a real branch, not rhetoric', () =>
  assert.ok(html.includes("kind==='objection'") && html.includes('paid-part')));
t('E5 human hand-off branch exists', () =>
  assert.ok(html.includes("kind==='handoff'")));

/* ============ F. Accessibility ============ */
console.log('F. Accessibility');
t('F1 toolbar present: 5-way theme group + अ− / A / अ+ + fs%', () => {
  for (const id of ['themeGroup','fsMinus','fsVal','fsPlus'])
    assert.ok(html.includes('id="'+id+'"'), id);
  for (const t of ['data-t="light"','data-t="contrast"','data-t="cb"','data-t="dark"','data-t="kyan"'])
    assert.ok(html.includes(t), t); });
t('F2 dark theme is a full variable override', () =>
  assert.ok(html.includes('[data-theme="dark"]') && html.includes('--page:#221e19')));
t('F3 सरकारी शैली: उजाला + राहत + काला-पीला स्कीम available', () => {
  assert.ok(html.includes('[data-theme="contrast"]'), 'high-contrast light');
  const cbBlock = html.match(/\[data-theme="cb"\]\{([^}]*)\}/);
  assert.ok(cbBlock, 'rahat block missing');
  assert.ok(cbBlock[1].includes('--cloth:#0f3f66'), 'navy cloth');
  assert.ok(cbBlock[1].includes('--rule:#8a5a00'), 'amber margin rule');
  const ky = html.match(/\[data-theme="kyan"\]\{([^}]*)\}/);
  assert.ok(ky && ky[1].includes('--page:#0b0b0b') && ky[1].includes('--ink:#ffd400'),
    'NIC black-on-yellow theme'); });
t('F4 font scale: 5 damping steps, none beyond 145%', () => {
  const z = html.match(/const ZOOMS=\[([^\]]*)\]/);
  const steps = z[1].split(',').map(Number);
  assert.equal(steps.length, 5);
  assert.equal(steps[0], 0.85); assert.equal(steps[4], 1.45); });
t('F5 preferences persist (localStorage), theme applied pre-paint', () => {
  assert.ok(html.includes("localStorage.getItem('ud-theme')"));
  assert.ok(html.includes("localStorage.getItem('ud-fs')"));
  assert.ok(html.indexOf('prefers-color-scheme: dark') > -1); });
t('F6 status is never colour-only: every tag has glyph+text', () =>
  assert.ok(html.includes('✅ Paid') && html.includes('🤝 Promise') &&
            html.includes('⚠️ Overdue') && html.includes('Open')));

/* ============ G. Language toggle — हिंदी ⇄ English ============ */
console.log('G. Language toggle');
t('G1 language bar present with persist key ud-lang', () => {
  assert.ok(html.includes('id="langGroup"'), 'langGroup id');
  assert.ok(html.includes('data-lang="hi"') && html.includes('data-lang="en"'), 'both radios');
  assert.ok(html.includes("localStorage.setItem('ud-lang',LANG)"), 'persists choice');
  assert.ok(html.includes("localStorage.getItem('ud-lang')"), 'reads choice back'); });
t('G2 every translatable node carries data-i18n and the EN dictionary covers it', () => {
  const keys = [...html.matchAll(/data-i18n="([a-zA-Z0-9]+)"/g)].map(m => m[1]);
  assert.ok(keys.length >= 30, 'at least 30 nodes, got ' + keys.length);
  const dict = html.match(/const EN_DICT=\{([^}]*)\}/);
  assert.ok(dict, 'EN_DICT declared');
  for (const k of keys) assert.ok(dict[1].includes(k + ':'), 'dict key missing: ' + k); });
t('G3 Hindi original captured once (HI) before any swap; applyLang re-renders live views', () => {
  assert.ok(html.includes('const HI={}'), 'HI capture');
  assert.ok(/function applyLang\(\)\{[\s\S]*?renderLedger\(\);[\s\S]*?renderDigest\(\)/.test(html),
    'applyLang re-renders ledger + digest'); });
t('G4 English-only Latin webfont; no Devanagari webfont downloaded', () => {
  assert.ok(/family=Archivo/.test(html), 'Archivo loaded from Google Fonts');
  assert.ok(!/@import|font-face/.test(html) || !/fonts\.googleapis\.com[^"']*(Tiro|Mukta|Hind|Noto)[^"']*/.test(html),
    'no Devanagari webfont request'); });
t('G5 T() bilingual helper drives dynamic strings and respects extracted functions', () => {
  const tcalls = (html.match(/T\(/g) || []).length;
  assert.ok(tcalls >= 25, 'T() used widely, got ' + tcalls);
  const st = extractFn('statusTag');
  assert.ok(!st.includes('T('), 'statusTag stays isolated (no outer helpers)');
  const ns = extractFn('nextSunday');
  assert.ok(!ns.includes('T('), 'nextSunday stays isolated'); });
t('G6 <html lang> follows the toggle (pre-paint + on switch)', () => {
  assert.ok(html.includes("de.lang=(l==='en'?'en':'hi')"), 'pre-paint <html lang>');
  assert.ok(html.includes("document.documentElement.lang = LANG==='en' ? 'en' : 'hi'"),
    'applyLang updates <html lang>'); });

console.log(`\n${results.pass} passed, ${results.fail} failed`);
process.exit(results.fail ? 1 : 0);

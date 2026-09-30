// Inkstone widget for Scriptable (Lock Screen and Home Screen).
//
// Setup
//   1. Paste this whole script into a new Scriptable script and name it exactly: Inkstone
//   2. In Inkstone, Settings > Lock screen widget > Send to widget. Scriptable opens and imports your cards.
//      (Or run this script in Scriptable and choose "Paste deck" or "Import deck file".)
//   3. Lock Screen: long-press, Customise, tap the widget area, add Scriptable, tap it, Script: Inkstone.
//
// Optional widget parameter (long-press the widget, Edit Widget, Parameter), space separated, any order:
//   ja | zh         one language only (default: both)
//   chars | words   only characters or only words
//   quiz            hide the meaning, so you recall it before unlocking
//   20m             minutes per card (default 30; iOS decides the exact moment it refreshes)
//   #2              offset, so two widgets with the same settings show different cards (#1 to #4)
//
// Tapping the widget opens that entry in Inkstone.
// To update this script later, run it in Scriptable and choose "Update script from website".

const FILE = 'inkstone-widget.json';
const SITE = 'https://venus-beetroot.github.io/inkstone/';
const VERSION = 2;
const C = {
  bg: new Color('#12110e'), ink: new Color('#ece4d3'), ink2: new Color('#b9ad97'),
  ink3: new Color('#877c69'), brass: new Color('#d0a94f'), line: new Color('#2e2a22'),
};
// Explicit fonts keep Japanese and Chinese glyph forms apart (han unification).
const CJK = {
  ja: n => new Font('HiraMinProN-W6', n),
  zh: n => new Font('PingFangSC-Semibold', n),
};
const READ = {
  ja: n => new Font('HiraginoSans-W5', n),
  zh: n => Font.semiboldSystemFont(n),
};
const SERIF_I = n => new Font('Georgia-Italic', n);
const MONO = n => new Font('Menlo-Regular', n);
const KIND = { jk: 'Kanji', hz: 'Hanzi', jw: 'Word', zw: 'Word' };

/* ---------- storage ---------- */
function files() {
  try { return FileManager.iCloud(); } catch (e) { return FileManager.local(); }
}
async function loadDeck() {
  for (const fm of [files(), FileManager.local()]) {
    const path = fm.joinPath(fm.documentsDirectory(), FILE);
    if (!fm.fileExists(path)) continue;
    try {
      if (fm.isFileStoredIniCloud && fm.isFileStoredIniCloud(path) && !fm.isFileDownloaded(path)) {
        await fm.downloadFileFromiCloud(path);
      }
      const deck = JSON.parse(fm.readString(path));
      if (deck && deck.app === 'inkstone-widget' && Array.isArray(deck.items)) return deck;
    } catch (e) { /* fall through to the next location */ }
  }
  return null;
}
function saveDeck(text) {
  const deck = JSON.parse(text);
  if (!deck || deck.app !== 'inkstone-widget' || !Array.isArray(deck.items)) {
    throw new Error('That is not an Inkstone widget deck.');
  }
  const fm = files();
  fm.writeString(fm.joinPath(fm.documentsDirectory(), FILE), JSON.stringify(deck));
  return deck;
}

/* ---------- choosing a card ---------- */
function parseParam(p) {
  const o = { lang: null, kind: null, quiz: false, mins: 30, offset: 0 };
  for (const t of String(p || '').toLowerCase().split(/[\s,]+/).filter(Boolean)) {
    if (t === 'ja' || t === 'jp' || t === 'japanese') o.lang = 'ja';
    else if (t === 'zh' || t === 'cn' || t === 'chinese') o.lang = 'zh';
    else if (t === 'chars' || t === 'kanji' || t === 'hanzi' || t === 'characters') o.kind = 'char';
    else if (t === 'words' || t === 'vocab') o.kind = 'word';
    else if (t === 'quiz') o.quiz = true;
    else if (/^\d+m(in)?$/.test(t)) o.mins = Math.max(5, parseInt(t, 10));
    else if (/^#\d+$/.test(t)) o.offset = Math.max(0, parseInt(t.slice(1), 10) - 1);
  }
  return o;
}
function hash(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}
function rand(a) {
  a = (a + 0x6D2B79F5) | 0;
  let t = Math.imul(a ^ (a >>> 15), 1 | a);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
const isChar = it => it.k === 'jk' || it.k === 'hz';
function pick(deck, o, now) {
  if (!deck) return null;
  const items = deck.items.filter(it =>
    (!o.lang || it.l === o.lang) && (!o.kind || (o.kind === 'char') === isChar(it)));
  if (!items.length) return null;
  // A fixed shuffle per exported deck, walked one step per time slot, so every card comes round before any repeats.
  const seed = hash(String(deck.generated || ''));
  const order = items.map((it, i) => [rand(seed + i), it]).sort((a, b) => a[0] - b[0]).map(x => x[1]);
  const slot = Math.floor(now / (o.mins * 60000));
  const shift = Math.floor(order.length / 4) * o.offset + o.offset;
  return order[(slot + shift) % order.length];
}

/* ---------- drawing ---------- */
const len = s => Array.from(s).length;
function text(parent, str, font, color, opts = {}) {
  const t = parent.addText(str);
  t.font = font;
  if (color) t.textColor = color;
  t.lineLimit = opts.lines || 1;
  t.minimumScaleFactor = opts.scale || 0.6;
  if (opts.center) t.centerAlignText();
  if (opts.opacity) t.textOpacity = opts.opacity;
  return t;
}
function readingLine(it) {
  return it.ro ? `${it.r}  ${it.ro}` : it.r;
}
function build(deck, it, o, family, now) {
  const w = new ListWidget();
  const accessory = family && family.startsWith('accessory');
  if (!accessory) { w.backgroundColor = C.bg; }

  if (!it) {
    w.url = (deck && deck.url) || SITE + '#widget';
    if (family === 'accessoryInline') { w.addText('Inkstone: open Scriptable to import cards'); return w; }
    if (family === 'accessoryCircular') { w.addAccessoryWidgetBackground = true; text(w, '硯', CJK.ja(26), null, { center: true }); return w; }
    text(w, 'Inkstone', accessory ? Font.semiboldSystemFont(14) : SERIF_I(18), accessory ? null : C.ink);
    text(w, deck ? 'No cards match this widget\'s parameter.' : 'Run the Inkstone script in Scriptable to import your cards.',
      accessory ? Font.systemFont(12) : Font.systemFont(12), accessory ? null : C.ink2, { lines: 3 });
    return w;
  }

  const cjk = CJK[it.l] || CJK.ja, read = READ[it.l] || READ.ja;
  const n = len(it.h);

  if (family === 'accessoryInline') {
    w.addText(o.quiz ? `${it.h}  ${it.r}` : `${it.h} ${it.r} · ${it.m}`);
  } else if (family === 'accessoryCircular') {
    w.addAccessoryWidgetBackground = true;
    text(w, it.h, cjk(n === 1 ? 32 : n === 2 ? 20 : 14), null, { center: true, scale: 0.4 });
  } else if (family === 'accessoryRectangular') {
    const row = w.addStack();
    row.layoutHorizontally(); row.centerAlignContent(); row.spacing = 8;
    text(row, it.h, cjk(n === 1 ? 42 : n === 2 ? 30 : n === 3 ? 22 : 18), null, { scale: 0.45 });
    const col = row.addStack();
    col.layoutVertically(); col.spacing = 1;
    text(col, readingLine(it), read(14), null, { scale: 0.55 });
    if (o.quiz) text(col, `${it.lv} · ${KIND[it.k] || ''}`, Font.mediumSystemFont(11), null, { opacity: 0.7 });
    else text(col, it.m, Font.systemFont(12), null, { lines: 2, scale: 0.7 });
  } else if (family === 'medium') {
    w.setPadding(14, 16, 14, 16);
    const row = w.addStack();
    row.layoutHorizontally(); row.centerAlignContent(); row.spacing = 16;
    const left = row.addStack();
    left.size = new Size(110, 110); left.centerAlignContent();
    text(left, it.h, cjk(n === 1 ? 84 : n === 2 ? 50 : n === 3 ? 36 : 28), C.ink, { center: true, scale: 0.4 });
    const col = row.addStack();
    col.layoutVertically(); col.spacing = 4;
    text(col, `${it.lv} · ${KIND[it.k] || ''}`.toUpperCase(), MONO(9), C.ink3);
    text(col, readingLine(it), read(17), C.brass, { scale: 0.5 });
    if (!o.quiz) text(col, it.m, SERIF_I(15), C.ink, { lines: 3, scale: 0.7 });
    row.addSpacer();
  } else {
    // small, large and extraLarge share one poster layout
    const big = family === 'large' || family === 'extraLarge';
    w.setPadding(big ? 20 : 12, 14, big ? 20 : 12, 14);
    text(w, `${it.lv} · ${KIND[it.k] || ''}`.toUpperCase(), MONO(big ? 11 : 8), C.ink3);
    w.addSpacer();
    const mid = w.addStack();
    mid.layoutHorizontally(); mid.addSpacer();
    const base = big ? [150, 96, 70, 54] : [64, 44, 32, 24];
    text(mid, it.h, cjk(base[Math.min(3, n - 1)]), C.ink, { center: true, scale: 0.4 });
    mid.addSpacer();
    w.addSpacer();
    text(w, readingLine(it), read(big ? 22 : 13), C.brass, { scale: 0.5 });
    if (!o.quiz) text(w, it.m, SERIF_I(big ? 20 : 12), C.ink, { lines: 2, scale: 0.7 });
  }

  w.url = `${(deck && deck.url) || SITE}#item=${encodeURIComponent(it.id)}`;
  // Ask to refresh at the start of the next slot. iOS may wait longer to save battery.
  w.refreshAfterDate = new Date((Math.floor(now / (o.mins * 60000)) + 1) * o.mins * 60000);
  return w;
}

/* ---------- in-app menu ---------- */
function ago(iso) {
  const ms = Date.now() - new Date(iso).getTime();
  if (isNaN(ms)) return 'at an unknown time';
  const h = Math.round(Math.max(0, ms) / 3600000);
  return h < 1 ? 'just now' : h < 48 ? `${h} h ago` : `${Math.round(h / 24)} days ago`;
}
async function note(title, message) {
  const a = new Alert(); a.title = title; a.message = message; a.addAction('OK'); await a.presentAlert();
}
async function updateScript() {
  const src = await new Request(SITE + 'Inkstone.js').loadString();
  const m = src.match(/const VERSION = (\d+);/);
  if (!m || src.indexOf('Inkstone widget for Scriptable') < 0) throw new Error('The website did not return the Inkstone script. Try again in a minute.');
  const remote = parseInt(m[1], 10);
  if (remote <= VERSION) { await note('Up to date', `You have version ${VERSION}, the latest on the website.`); return; }
  try { files().writeString(module.filename, src); } catch (e) { FileManager.local().writeString(module.filename, src); }
  await note('Updated', `Now on version ${remote}. Widgets use it from their next refresh.`);
}
async function pasteDeck() {
  const s = (Pasteboard.pasteString ? Pasteboard.pasteString() : Pasteboard.paste()) || '';
  const deck = saveDeck(s);
  await note('Widget updated', `${deck.items.length} cards saved. Widgets pick them up at their next refresh, usually within half an hour.`);
  return deck;
}
async function menu(o) {
  let deck = await loadDeck();
  const a = new Alert();
  a.title = 'Inkstone widget';
  a.message = deck ? `${deck.items.length} cards, exported ${ago(deck.generated)}.` : 'No cards yet. In Inkstone, use Send to widget, or paste a copied deck here.';
  a.addAction('Paste deck from clipboard');
  a.addAction('Import deck file');
  a.addAction('Preview Lock Screen');
  a.addAction('Preview Home Screen');
  a.addAction('Open Inkstone');
  a.addAction(`Update script from website (v${VERSION})`);
  a.addCancelAction('Done');
  const i = await a.presentSheet();
  try {
    if (i === 0) deck = await pasteDeck();
    else if (i === 1) {
      const paths = await DocumentPicker.open(['public.json', 'public.text']);
      deck = saveDeck(FileManager.local().readString(paths[0]));
      await note('Widget updated', `${deck.items.length} cards saved.`);
    } else if (i === 2) {
      const now = Date.now();
      await build(deck, pick(deck, o, now), o, 'accessoryRectangular', now).presentAccessoryRectangular();
    } else if (i === 3) {
      const now = Date.now();
      await build(deck, pick(deck, o, now), o, 'medium', now).presentMedium();
    } else if (i === 4) {
      Safari.open((deck && deck.url) || SITE);
    } else if (i === 5) {
      await updateScript();
    }
  } catch (e) {
    await note('Could not finish that', String(e.message || e));
  }
}

/* ---------- entry point ---------- */
const params = parseParam(args.widgetParameter);
if (config.runsInWidget) {
  const deck = await loadDeck();
  const now = Date.now();
  Script.setWidget(build(deck, pick(deck, params, now), params, config.widgetFamily, now));
} else if (args.queryParameters && args.queryParameters.import === 'clipboard') {
  try { await pasteDeck(); } catch (e) { await note('Could not import', String(e.message || e)); }
} else {
  await menu(params);
}
Script.complete();

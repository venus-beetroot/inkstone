// Runs Inkstone.js against a minimal mock of the Scriptable runtime.
const fs = require('fs'), path = require('path'), os = require('os'), vm = require('vm');
const ROOT = path.join(__dirname, '..');
const SRC = fs.readFileSync(path.join(ROOT, 'Inkstone.js'), 'utf8');
const DECK = path.join(ROOT, 'build', 'test-deck.json');

async function run({family = null, param = '', inWidget = true, deck = true, query = {}, paste = '', choice = -1, now = Date.UTC(2026, 8, 30, 6, 0), remote = null}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'scr-'));
  const icloud = path.join(root, 'icloud'), local = path.join(root, 'local');
  fs.mkdirSync(icloud); fs.mkdirSync(local);
  if (deck) fs.copyFileSync(DECK, path.join(icloud, 'inkstone-widget.json'));
  const log = {widget: null, presented: null, alerts: [], opened: null, fetched: null};
  const scriptPath = path.join(icloud, 'Inkstone.js'); fs.writeFileSync(scriptPath, SRC);
  class Color { constructor(h) { this.hex = h; } }
  class Font {
    constructor(n, s) { this.name = n; this.size = s; }
    static systemFont(s) { return new Font('system', s); }
    static semiboldSystemFont(s) { return new Font('system-semibold', s); }
    static mediumSystemFont(s) { return new Font('system-medium', s); }
  }
  class Size { constructor(w, h) { this.w = w; this.h = h; } }
  class Text { constructor(t) { this.kind = 'text'; this.text = t; } centerAlignText() { this.center = true; } }
  class Box {
    constructor(kind) { this.kind = kind; this.children = []; }
    addText(t) { if (typeof t !== 'string') throw new Error('addText expects a string, got ' + typeof t); const n = new Text(t); this.children.push(n); return n; }
    addStack() { const s = new Box('stack'); this.children.push(s); return s; }
    addSpacer(l) { this.children.push({kind: 'spacer', l}); return {}; }
    setPadding() {} layoutHorizontally() { this.dir = 'h'; } layoutVertically() { this.dir = 'v'; } centerAlignContent() {}
  }
  class ListWidget extends Box {
    constructor() { super('widget'); }
    async presentAccessoryRectangular() { log.presented = 'accessoryRectangular'; log.widget = this; }
    async presentMedium() { log.presented = 'medium'; log.widget = this; }
  }
  const fm = dir => ({
    documentsDirectory: () => dir, joinPath: (a, b) => path.join(a, b), fileExists: p => fs.existsSync(p),
    readString: p => fs.readFileSync(p, 'utf8'), writeString: (p, s) => fs.writeFileSync(p, s),
    isFileStoredIniCloud: () => dir === icloud, isFileDownloaded: () => true, downloadFileFromiCloud: async () => {},
  });
  class FakeDate extends Date { constructor(...a) { a.length ? super(...a) : super(now); } static now() { return now; } }
  const ctx = {
    Color, Font, Size, ListWidget, Date: FakeDate, console, JSON, Math, String, Array, Error, Object, Number, parseInt,
    FileManager: {iCloud: () => fm(icloud), local: () => fm(local)},
    Pasteboard: {pasteString: () => paste},
    Alert: class { constructor() { this.actions = []; } addAction(a) { this.actions.push(a); } addCancelAction() {}
      async presentSheet() { log.alerts.push({title: this.title, message: this.message, actions: this.actions}); return choice; }
      async presentAlert() { log.alerts.push({title: this.title, message: this.message}); return 0; } },
    DocumentPicker: {open: async () => [DECK]},
    Safari: {open: u => { log.opened = u; }},
    Request: class { constructor(u) { this.url = u; } async loadString() { log.fetched = this.url; return remote; } },
    module: {filename: scriptPath},
    Script: {setWidget: w => { log.widget = w; }, complete: () => {}},
    args: {widgetParameter: param, queryParameters: query},
    config: {runsInWidget: inWidget, widgetFamily: family, runsInApp: !inWidget},
  };
  await vm.runInNewContext(`(async () => {\n${SRC}\n})()`, ctx);
  const saved = fs.existsSync(path.join(icloud, 'inkstone-widget.json')) ? JSON.parse(fs.readFileSync(path.join(icloud, 'inkstone-widget.json'), 'utf8')) : null;
  return {log, saved, script: fs.readFileSync(scriptPath, 'utf8')};
}
function texts(node, out = []) {
  for (const c of node.children || []) {
    if (c.kind === 'text') out.push(`${c.text}${c.font ? ` [${c.font.name} ${c.font.size}]` : ''}`);
    else texts(c, out);
  }
  return out;
}

(async () => {
  let fails = 0;
  const check = (ok, msg) => { if (!ok) fails++; console.log((ok ? 'PASS ' : 'FAIL ') + msg); };
  const families = ['accessoryRectangular', 'accessoryInline', 'accessoryCircular', 'small', 'medium', 'large', 'extraLarge'];

  console.log('--- no deck yet');
  for (const f of families) {
    const {log} = await run({family: f, deck: false});
    check(log.widget && texts(log.widget).length > 0, `${f}: ${texts(log.widget).join(' | ')}`);
  }
  console.log('--- with deck');
  for (const f of families) {
    const {log} = await run({family: f});
    const w = log.widget;
    check(w && w.url && w.url.includes('#item=') && w.refreshAfterDate > new Date(Date.UTC(2026, 8, 30, 6, 0)),
      `${f}: ${texts(w).join(' | ')}  url=${decodeURIComponent(w.url.split('#')[1])} refresh=${w.refreshAfterDate.toISOString()}`);
  }
  console.log('--- parameters');
  {
    const {log} = await run({family: 'accessoryRectangular', param: 'zh quiz'});
    const t = texts(log.widget).join(' | ');
    check(/PingFangSC/.test(t) && /HSK/.test(t), `zh quiz: ${t}`);
    const {log: l2} = await run({family: 'accessoryRectangular', param: 'ja words'});
    check(/HiraMin/.test(texts(l2.widget).join()) && l2.widget.url.includes('jw%3A'), `ja words: ${texts(l2.widget).join(' | ')}`);
    const {log: l3} = await run({family: 'accessoryInline', param: 'ja chars quiz'});
    check(texts(l3.widget).length === 1, `inline quiz: ${texts(l3.widget).join()}`);
    const a = (await run({family: 'accessoryRectangular', param: ''})).log.widget.url;
    const b = (await run({family: 'accessoryRectangular', param: '#2'})).log.widget.url;
    check(a !== b, 'offset #2 shows a different card than #1');
    const {log: l4} = await run({family: 'accessoryRectangular', param: 'nonsense zh chars'});
    check(l4.widget.url.includes('hz%3A'), 'unknown tokens are ignored');
  }
  console.log('--- rotation');
  {
    const deck = JSON.parse(fs.readFileSync(DECK, 'utf8'));
    const n = deck.items.length, seen = new Set();
    const start = Date.UTC(2026, 8, 30, 0, 0);
    for (let i = 0; i < n; i++) {
      const {log} = await run({family: 'accessoryRectangular', now: start + i * 30 * 60000});
      seen.add(log.widget.url);
    }
    check(seen.size === n, `${n} consecutive half-hour slots show ${seen.size} different cards`);
    const {log: l1} = await run({family: 'accessoryRectangular', param: '20m', now: start + 20 * 60000 - 1});
    const {log: l2} = await run({family: 'accessoryRectangular', param: '20m', now: start + 20 * 60000});
    check(l1.widget.url !== l2.widget.url && l2.widget.refreshAfterDate.getTime() === start + 40 * 60000, '20m interval advances on the boundary and schedules the next one');
  }
  console.log('--- importing');
  {
    const deckText = fs.readFileSync(DECK, 'utf8');
    const r1 = await run({inWidget: false, deck: false, query: {import: 'clipboard'}, paste: deckText});
    check(r1.saved && r1.saved.items.length === JSON.parse(deckText).items.length && /Widget updated/.test(r1.log.alerts[0].title), `URL import: ${r1.log.alerts[0].message}`);
    const r2 = await run({inWidget: false, deck: false, query: {import: 'clipboard'}, paste: 'hello'});
    check(!r2.saved && /Could not import/.test(r2.log.alerts[0].title), `bad clipboard: ${r2.log.alerts[0].title}`);
    const r3 = await run({inWidget: false, deck: false, choice: 1});
    check(r3.saved && r3.saved.items.length > 0, 'menu: import deck file');
    const r4 = await run({inWidget: false, choice: 2});
    check(r4.log.presented === 'accessoryRectangular', `menu: preview lock screen. Menu said: ${r4.log.alerts[0].message}`);
    const r5 = await run({inWidget: false, deck: false, choice: 0, paste: deckText});
    check(r5.saved !== null, 'menu: paste deck from clipboard');
  }
  console.log('--- routing');
  {
    const {log} = await run({family: 'accessoryRectangular', deck: false});
    check(log.widget.url === 'https://venus-beetroot.github.io/inkstone/#widget', `empty widget taps through to ${log.widget.url}`);
    const r = await run({inWidget: false, choice: 4});
    check(/^http/.test(r.log.opened), `menu: open Inkstone -> ${r.log.opened}`);
    const same = await run({inWidget: false, choice: 5, remote: SRC});
    check(/Up to date/.test(same.log.alerts[1].title) && same.log.fetched.endsWith('/inkstone/Inkstone.js'), `update, same version: ${same.log.alerts[1].message}`);
    const newer = SRC.replace(/const VERSION = (\d+);/, (m, v) => `const VERSION = ${+v + 1};`);
    const up = await run({inWidget: false, choice: 5, remote: newer});
    check(/Updated/.test(up.log.alerts[1].title) && up.script === newer, `update, newer version: ${up.log.alerts[1].message}`);
    const bad = await run({inWidget: false, choice: 5, remote: '<html>404</html>'});
    check(/Could not/.test(bad.log.alerts[1].title) && bad.script === SRC, 'update, bad response leaves the script untouched');
  }
  console.log(fails ? `${fails} FAILED` : 'ALL PASSED');
})().catch(e => { console.error('CRASH', e); process.exit(1); });

"""End-to-end check of the app in headless Chromium, plus FSRS-5 against the py-fsrs reference.
Needs: pip install playwright "fsrs>=5,<6", and a built index.html. Set CHROME to use a specific browser."""
import json, os, sys, threading, http.server, functools, urllib.parse
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(B, 'tests', 'shots'); os.makedirs(OUT, exist_ok=True)
PKG = {'hanzi-writer-data-jp@0.0.1': f'{B}/build/cache/pkg/hanzi-writer-data-jp@0.0.1', 'hanzi-writer-data@2.0.1': f'{B}/build/cache/pkg/hanzi-writer-data@2.0.1'}

# ---- serve dist ----
Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=B)
Handler.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 8765), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()

errors = []
def route_cdn(route):
    url = urllib.parse.unquote(route.request.url)
    for k, d in PKG.items():
        if k in url:
            name = url.split(k + '/')[1]
            p = os.path.join(d, name)
            if os.path.exists(p):
                return route.fulfill(status=200, body=open(p, 'rb').read(), headers={'content-type': 'application/json', 'access-control-allow-origin': '*'})
            return route.fulfill(status=404, body='nf')
    return route.abort()

# ---- FSRS reference comparison ----
from fsrs import Scheduler, Card, Rating
def ref_seq(seq):
    sch = Scheduler(enable_fuzzing=False)
    c = Card(); t = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc); out = []
    for g, dt_min in seq:
        t = t + timedelta(minutes=dt_min)
        c, _ = sch.review_card(c, Rating(g), review_datetime=t)
        out.append((round(c.stability, 4), round(c.difficulty, 4), c.state.value, round((c.due - t).total_seconds() / 86400, 3)))
    return out

SEQS = [
    [(3, 0), (3, 1), (3, 10), (3, 60 * 24 * 4), (1, 60 * 24 * 11), (3, 10), (4, 60 * 24 * 2)],
    [(1, 0), (2, 1), (3, 5), (3, 10), (2, 60 * 24 * 3), (3, 60 * 24 * 5), (3, 60 * 24 * 30)],
    [(4, 0), (3, 60 * 24 * 16), (1, 60 * 24 * 60), (1, 10), (3, 10), (3, 60 * 24 * 2)],
]

with sync_playwright() as p:
    br = p.chromium.launch(executable_path=os.environ.get('CHROME') or None)
    ctx = br.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
    ctx.route('**/cdn.jsdelivr.net/**', route_cdn)
    ctx.route('**/fonts.googleapis.com/**', lambda r: r.abort())
    ctx.route('**/fonts.gstatic.com/**', lambda r: r.abort())
    page = ctx.new_page()
    page.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
    page.on('console', lambda m: m.type == 'error' and 'fonts.g' not in m.text and 'net::ERR_FAILED' not in m.text and errors.append('console: ' + m.text))
    page.goto('http://127.0.0.1:8765/index.html')
    page.wait_for_selector('[data-ob]')
    page.screenshot(path=f'{OUT}/01-onboarding.png')

    # FSRS comparison in-page (uses the app's stepCard with fixed timestamps)
    for seq in SEQS:
        mine = page.evaluate('''(seq) => { const {stepCard} = window.__inkstone; let c = {st:0,s:0,d:0,due:0,last:0,step:0,reps:0,lapses:0}; let t = Date.UTC(2026,0,1,10,0); const out=[];
            for (const [g, m] of seq) { t += m*60000; c = stepCard(c, g, t); out.push([+c.s.toFixed(4), +c.d.toFixed(4), c.st, +((c.due - t)/86400000).toFixed(3)]); } return out; }''', seq)
        ref = ref_seq(seq)
        for a, b in zip(mine, ref):
            ok = abs(a[0] - b[0]) < 1e-3 and abs(a[1] - b[1]) < 1e-3
            stmap = {1: 1, 2: 2, 3: 3}
            print('OK ' if ok else 'BAD', 'mine', a, 'ref', b)
    # onboarding: choose N5 + HSK1 defaults, begin
    page.click('[data-ob-go]')
    page.wait_for_selector('.lang-card')
    page.screenshot(path=f'{OUT}/02-today.png', full_page=True)
    print('today counts:', page.inner_text('.section:has(.lang-card)').replace('\n', ' | ')[:300])

    # study session: both languages
    page.click('[data-act="study"][data-lang="all"]')
    page.wait_for_selector('.overlay .head-big')
    page.screenshot(path=f'{OUT}/03-front.png')
    seen = []
    for i in range(14):
        head = page.inner_text('.overlay .head-big')
        kick = page.inner_text('.overlay .study-inner .kicker')
        page.click('[data-act="reveal"] >> nth=-1')
        page.wait_for_selector('.rate'); page.wait_for_timeout(300)
        if i == 0:
            page.screenshot(path=f'{OUT}/04-back-kanji.png')
        ivls = page.inner_text('.rate').replace('\n', ' ')
        seen.append((head, kick, ivls))
        if 'WORD' in kick.upper() and 'N5' in kick and not os.path.exists(f'{OUT}/05-back-jword.png'):
            page.screenshot(path=f'{OUT}/05-back-jword.png')
        if 'HANZI' in kick.upper() and not os.path.exists(f'{OUT}/06-back-hanzi.png'):
            page.screenshot(path=f'{OUT}/06-back-hanzi.png')
        page.click(f'[data-rate="{3 if i % 4 else 1}"]')
    for s in seen: print('card', s)
    page.click('[data-act="undo"]')
    print('after undo head:', page.inner_text('.overlay .head-big'), '| revealed:', page.locator('.rate').count() > 0)
    # details from inside the session -> strokes
    page.click('.overlay [data-act="open-strokes"], .overlay .answer [data-open] >> nth=0')
    page.wait_for_selector('.sheet')
    page.wait_for_timeout(600)
    print('writer msg:', page.inner_text('.hw-msg') if page.locator('.hw-msg').count() else 'no writer')
    page.screenshot(path=f'{OUT}/07-detail.png')
    if page.locator('[data-act="hw-trace"]').count():
        page.click('[data-act="hw-trace"]'); page.wait_for_timeout(300)
        page.click('[data-act="hw-play"]'); page.wait_for_timeout(1500)
        page.screenshot(path=f'{OUT}/08-strokes.png')
    page.keyboard.press('Escape'); page.keyboard.press('Escape')
    page.wait_for_timeout(200)

    # browse searches
    page.click('[data-tab="browse"]')
    for q in ['water', 'mizu', 'shui', '水', 'たべる', 'xuexi', 'テレビ', '学习', 'to study', 'yinhang']:
        page.fill('#q', q); page.wait_for_timeout(300)
        rows = page.locator('#results .row')
        tops = [rows.nth(i).inner_text().replace('\n', ' / ') for i in range(min(3, rows.count()))]
        print(f'search {q!r}:', page.inner_text('#results .kicker') if rows.count() else 'none', tops)
    page.fill('#q', ''); page.click('[data-seg="word"]'); page.wait_for_timeout(200)
    page.screenshot(path=f'{OUT}/09-browse.png')
    page.fill('#q', '食べる'); page.wait_for_timeout(300)
    page.click('#results .row >> nth=0'); page.wait_for_selector('.sheet'); page.wait_for_timeout(500)
    page.screenshot(path=f'{OUT}/10-word-detail.png')
    page.keyboard.press('Escape')

    # fake history so the charts have something to draw
    page.evaluate('''() => { const s = window.__inkstone.S(); const now = Date.now();
      for (let i = 1; i < 120; i++) { if (Math.random() < .25) continue; const d = new Date(now - i*86400000); const k = d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
        const r = Math.round(20 + Math.random()*120); s.log[k] = {r, n:{ja:5,zh:5}, rv: r-10, p: Math.round((r-10)*.88), ms: r*9000, x:{ja:0,zh:0}}; }
      let n = 0; for (const it of window.__inkstone.ITEMS.values()) { if (n++ > 400) break; if (!s.cards[it.id]) s.cards[it.id] = {st:2, s: 5 + Math.random()*40, d: 5, due: now + Math.floor(Math.random()*16)*86400000, last: now - 5*86400000, step:0, reps:4, lapses:0}; }
    }''')
    # stats + settings
    page.click('[data-tab="stats"]'); page.wait_for_timeout(200)
    page.screenshot(path=f'{OUT}/11-stats.png', full_page=True)
    page.click('[data-tab="settings"]'); page.wait_for_timeout(200)
    page.screenshot(path=f'{OUT}/12-settings.png', full_page=True)
    page.click('[data-theme-set="light"]'); page.wait_for_timeout(100)
    page.click('[data-tab="today"]'); page.wait_for_timeout(100)
    page.screenshot(path=f'{OUT}/13-today-light.png', full_page=True)

    # persistence
    page.reload(); page.wait_for_selector('.lang-card')
    st = page.evaluate('() => { const s = window.__inkstone.S(); return {cards: Object.keys(s.cards).length, theme: s.settings.theme, onboarded: s.settings.onboarded, log: s.log}; }')
    print('after reload:', st)

    # iPad
    ctx2 = br.new_context(viewport={'width': 1024, 'height': 1366}, device_scale_factor=1)
    ctx2.route('**/cdn.jsdelivr.net/**', route_cdn); ctx2.route('**/fonts.g*/**', lambda r: r.abort())
    p2 = ctx2.new_page(); p2.on('pageerror', lambda e: errors.append('pageerror ipad: ' + str(e)))
    p2.goto('http://127.0.0.1:8765/index.html'); p2.wait_for_selector('[data-ob]')
    p2.click('[data-ob-go]'); p2.click('[data-act="study"][data-lang="ja"]'); p2.click('[data-act="reveal"] >> nth=-1'); p2.wait_for_timeout(500)
    p2.screenshot(path=f'{OUT}/14-ipad-study.png')
    p2.keyboard.press('3'); p2.keyboard.press('Space'); p2.keyboard.press('1')
    p2.keyboard.press('Escape'); p2.click('[data-tab="stats"]'); p2.wait_for_timeout(200)
    p2.screenshot(path=f'{OUT}/15-ipad-stats.png')
    br.close()

print('ERRORS:', errors or 'none')
srv.shutdown()

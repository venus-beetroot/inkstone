"""Checks the widget export, script copy, Send to widget hand-off and deep links. Writes build/test-deck.json for widget_mock_test.js."""
import os, json, threading, http.server, functools
from playwright.sync_api import sync_playwright
B=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT=os.path.join(B,'tests','shots'); os.makedirs(OUT, exist_ok=True)
H=functools.partial(http.server.SimpleHTTPRequestHandler, directory=B); H.log_message=lambda *a: None
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8766),H); threading.Thread(target=srv.serve_forever,daemon=True).start()
errors=[]
with sync_playwright() as p:
    br=p.chromium.launch(executable_path=os.environ.get('CHROME') or None)
    ctx=br.new_context(viewport={'width':390,'height':844}, device_scale_factor=2, accept_downloads=True)
    ctx.grant_permissions(['clipboard-read','clipboard-write'], origin='http://127.0.0.1:8766')
    ctx.route('**/fonts.g*/**', lambda r: r.abort()); ctx.route('**/cdn.jsdelivr.net/**', lambda r: r.abort())
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.goto('http://127.0.0.1:8766/index.html'); pg.click('[data-ob-go]')
    # study a few cards so "learning" has content
    pg.click('[data-act="study"][data-lang="all"]')
    for i in range(8):
        pg.click('[data-act="reveal"] >> nth=-1'); pg.click('[data-rate="3"]')
    pg.keyboard.press('Escape')
    pg.click('[data-tab="settings"]'); pg.wait_for_timeout(200)
    pg.locator('text=Lock screen widget').scroll_into_view_if_needed()
    panel = pg.locator('.section:has(h3:text("Lock screen widget"))')
    panel.screenshot(path=f'{OUT}/20-widget-panel.png')
    print('preview text:', panel.locator('.lockprev').inner_text().replace('\n',' | '), '|', panel.locator('.lockprev + .help').inner_text())
    for src in ['saved','levels','learning']:
        pg.click(f'[data-wsrc="{src}"]'); pg.wait_for_timeout(100)
        print(src, '->', pg.evaluate('() => window.__inkstone.widgetDeck().items.length'))
    pg.select_option('#wmax','50'); pg.wait_for_timeout(100)
    print('max 50 ->', pg.evaluate('() => window.__inkstone.widgetDeck().items.length'))
    pg.click('[data-wsrc="levels"]'); pg.select_option('#wmax','200')
    deck = pg.evaluate('() => window.__inkstone.widgetDeck()')
    os.makedirs(f'{B}/build', exist_ok=True); json.dump(deck, open(f'{B}/build/test-deck.json','w'), ensure_ascii=False)
    print('deck sample:', json.dumps(deck['items'][:3], ensure_ascii=False)[:400]); print('url:', deck['url'])
    zh=[i for i in deck['items'] if i['l']=='zh'][:3]; print('zh sample:', json.dumps(zh, ensure_ascii=False)[:400])
    # Save as file -> download fallback in desktop Chromium
    with pg.expect_download() as dl:
        pg.click('[data-act="widget-file"]')
    d=dl.value; print('download:', d.suggested_filename, os.path.getsize(d.path()))
    # Copy script
    pg.click('[data-act="widget-script"]'); pg.wait_for_timeout(200)
    clip = pg.evaluate('() => navigator.clipboard.readText()')
    print('script copied, matches file:', clip.strip()==open(f'{B}/Inkstone.js').read().strip())
    # Send to widget: clipboard gets the deck, then navigation to scriptable:// is attempted
    nav=[]
    pg.on('framenavigated', lambda f: nav.append(f.url))
    pg.on('request', lambda r: r.url.startswith('scriptable') and nav.append(r.url))
    pg.click('[data-act="widget-send"]'); pg.wait_for_timeout(800)
    clip = pg.evaluate('() => navigator.clipboard.readText()')
    print('send: clipboard deck items', len(json.loads(clip)['items']), '| nav attempts', nav)
    # deep link
    p2=ctx.new_page(); p2.on('pageerror', lambda e: errors.append(str(e)))
    p2.goto('http://127.0.0.1:8766/index.html#item=' + '%E9%A3%9F%E3%81%B9%E3%82%8B'); p2.wait_for_timeout(300)
    p2.goto('http://127.0.0.1:8766/index.html#item=jw%3A%E9%A3%9F%E3%81%B9%E3%82%8B%7C%E3%81%9F%E3%81%B9%E3%82%8B'); p2.wait_for_timeout(500)
    print('deep link sheet:', p2.locator('.sheet .d-char').inner_text() if p2.locator('.sheet .d-char').count() else 'none', '| hash cleared:', p2.evaluate('location.hash')=='' )
    p2.evaluate("location.hash = 'item=' + encodeURIComponent('hz:水')"); p2.wait_for_timeout(400)
    print('hashchange sheet:', p2.locator('.sheet .d-char').last.inner_text())
    p2.goto('http://127.0.0.1:8766/index.html#widget'); p2.wait_for_timeout(500)
    print('#widget route: tab', p2.get_attribute('[aria-current="page"]', 'data-tab'), '| panel on screen', p2.locator('#widget-panel').is_visible())
    br.close()
print('ERRORS:', errors or 'none'); srv.shutdown()

"""Assembles index.html from src/index.src.html, build/data.json, the two libraries, the icon and Inkstone.js.

Run: python3 tools/build_data.py && python3 tools/build.py
"""
import base64, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, npm_package

page = (ROOT / 'src' / 'index.src.html').read_text(encoding='utf-8')
data = (ROOT / 'build' / 'data.json').read_text(encoding='utf-8').replace('</', '<\\/').replace('<!--', '<\\!--')
wanakana = (npm_package('wanakana@5.3.1') / 'wanakana.min.js').read_text(encoding='utf-8').replace('//# sourceMappingURL=wanakana.min.js.map', '')
hanzi_writer = (npm_package('hanzi-writer@3.7.3') / 'dist' / 'hanzi-writer.min.js').read_text(encoding='utf-8').replace('//# sourceMappingURL=hanzi-writer.min.js.map', '')
icon = 'data:image/png;base64,' + base64.b64encode((ROOT / 'icon.png').read_bytes()).decode()
widget = (ROOT / 'Inkstone.js').read_text(encoding='utf-8')
for name, text in [('wanakana', wanakana), ('hanzi-writer', hanzi_writer), ('Inkstone.js', widget)]:
    assert '</script' not in text.lower(), f'{name} would break out of its script tag'

page = (page.replace('__SCRIPTABLE__', widget, 1)
            .replace('__DATA__', data, 1)
            .replace('__WANAKANA__', '/*! WanaKana 5.3.1 | MIT */\n' + wanakana, 1)
            .replace('__HANZIWRITER__', '/*! Hanzi Writer 3.7.3 | MIT | David Chanin */\n' + hanzi_writer, 1)
            .replace('__ICON__', icon))
(ROOT / 'index.html').write_text(page, encoding='utf-8')
print('index.html', len(page.encode()), 'bytes')

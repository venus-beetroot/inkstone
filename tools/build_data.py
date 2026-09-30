"""Builds build/data.json: the kanji, hanzi and vocabulary bundled into index.html.

Run from anywhere: python3 tools/build_data.py
Raw sources are downloaded into build/cache on first run.
"""
import json, csv, re, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, source, npm_package

# ---------- Make Me a Hanzi dictionary (components, pinyin, definitions, origin) ----------
mmah = {}
with open(source('dictionary.txt'), encoding='utf-8') as f:
    for line in f:
        o = json.loads(line)
        mmah[o['character']] = o

IDC = set('⿰⿱⿲⿳⿴⿵⿶⿷⿸⿹⿺⿻？')

def components(ch):
    o = mmah.get(ch)
    if not o:
        return ''
    out = []
    for c in o.get('decomposition', ''):
        if c not in IDC and c != ch and c not in out:
            out.append(c)
    return ''.join(out)

def origin(ch):
    o = mmah.get(ch)
    if not o or 'etymology' not in o:
        return ''
    e = o['etymology']
    t = e.get('type', '')
    hint = (e.get('hint') or '').strip()
    if t == 'pictophonetic':
        parts = []
        if e.get('semantic'):
            parts.append(f"{e['semantic']} gives the meaning")
        if e.get('phonetic'):
            parts.append(f"{e['phonetic']} gives the sound")
        s = '; '.join(parts)
        if hint:
            s = f"{s}. {hint}" if s else hint
        return 'Sound-meaning: ' + s
    label = {'ideographic': 'Ideograph', 'pictographic': 'Pictograph'}.get(t, t.capitalize())
    return f"{label}: {hint}" if hint else ''

# ---------- Japanese kanji ----------
kd = json.load(open(source('kanji.json'), encoding='utf-8'))
PROPER = set('''Japan Japanese China Chinese Buddha Buddhist Buddhism Korea Korean Shinto Confucius Confucian Europe European America American
England English Britain British Holland Dutch Russia Russian India Indian Spain Spanish Portugal Portuguese France French Germany German Italy
Sanskrit Zen Kyushu Shikoku Honshu Hokkaido Osaka Tokyo Kyoto Edo Nara Yamato Ainu Mongolia Mongol Manchu Taoism Taoist Tang Han Qin Zhou Wu Shu
Wei Chou Yin Mt. Mr. Mrs. Ms. Christ Christian Asia Asian I Heaven Emperor Imperial Buddhist-style Latin Greek Nippon'''.split())
def lower_meaning(m):
    out = []
    for tok in m.split(' '):
        core = re.sub(r'^[^A-Za-z]+|[^A-Za-z.]+$', '', tok)
        if not core or core in PROPER or (len(core) > 1 and core.isupper()):
            out.append(tok)
        else:
            i = tok.find(core[0])
            out.append(tok[:i] + tok[i].lower() + tok[i+1:])
    return ' '.join(out)

kanji = []
for ch, v in kd.items():
    lv = v.get('jlpt_new')
    if not lv:
        continue
    means = [m for m in v.get('meanings', []) if 'radical' not in m.lower()] or v.get('meanings', [])[:1]
    kanji.append([ch, lv, v.get('strokes') or 0, v.get('freq') or 9999,
                  '; '.join(lower_meaning(m) for m in means[:4]),
                  ' '.join(v.get('readings_on') or []),
                  ' '.join(v.get('readings_kun') or []),
                  components(ch), origin(ch)])
kanji.sort(key=lambda r: (-r[1], r[3], r[2]))

# ---------- Pitch accent ----------
pitch = {}
with open(source('accents.txt'), encoding='utf-8') as f:
    for line in f:
        p = line.rstrip('\n').split('\t')
        if len(p) < 3:
            continue
        m = re.search(r'\d+', p[2])
        if m:
            pitch.setdefault((p[0], p[1]), int(m.group()))

# ---------- Japanese vocab ----------
javocab = []
seen = set()
for lv in [5, 4, 3, 2, 1]:
    with open(source(f'n{lv}.csv'), encoding='utf-8') as f:
        for row in csv.DictReader(f):
            e, r, m = row['expression'].strip(), row['reading'].strip(), row['meaning'].strip()
            if not e or (e, r) in seen:
                continue
            seen.add((e, r))
            pa = pitch.get((e, r), pitch.get((r, r), -1))
            m = re.sub(r'\s+', ' ', m)
            if len(m) > 90:
                m = m[:90].rsplit(',', 1)[0]
            javocab.append([e, r, m, lv, pa])

rank = {k[0]: i for i, k in enumerate(kanji)}
ordered = []
for lv in [5, 4, 3, 2, 1]:
    grp = [w for w in javocab if w[3] == lv]
    ceiling = max((rank[k[0]] for k in kanji if k[1] >= lv), default=0) + 1
    def key(iw):
        i, w = iw
        ks = [c for c in w[0] if '\u4e00' <= c <= '\u9fff']
        if not ks:
            return i / max(1, len(grp)) * ceiling
        return max(rank.get(c, len(kanji)) for c in ks) + 0.5
    ordered += [w for _, w in sorted(enumerate(grp), key=key)]
javocab = ordered

# ---------- Chinese vocab (HSK 3.0) ----------
hsk = json.load(open(source('complete.min.json'), encoding='utf-8'))
zhvocab = []
single = {}
for w in hsk:
    newl = [int(l[1:]) for l in w.get('l', []) if l.startswith('n')]
    if not newl:
        continue
    lv = min(newl)
    JUNK = ('variant of', 'old variant', 'surname ', 'abbr. for', 'also pr.', 'used in ', 'see ', 'Japanese variant', 'erhua variant', 'Taiwan pr.', 'unofficial variant')
    def clean(f):
        raw = [re.sub(r'\s*\(Tw\)|\s*\[[^\]]*\]', '', m).strip() for m in f.get('m', [])]
        return [m for m in raw if m and not m.startswith(JUNK)]
    forms = [f for f in w['f'] if not f['i']['y'][:1].isupper()] or w['f']
    good = [(f, clean(f)) for f in forms]
    good = [x for x in good if x[1]] or [(forms[0], [m for m in forms[0].get('m', [])][:3])]
    f0, means = good[0]
    py = f0['i']['y']
    m = '; '.join(means[:3])
    if len(m) > 90:
        m = m[:90].rsplit(';', 1)[0]
    trad = f0.get('t', '')
    entry = [w['s'], py, m, lv, w.get('q', 99999), trad if trad != w['s'] else '']
    zhvocab.append(entry)
    if len(w['s']) == 1:
        readings = []
        for f, ms in good:
            if f['i']['y'] not in [r[0] for r in readings]:
                short = [x if len(x) <= 60 else x[:60].rsplit(' ', 1)[0] + '...' for x in ms[:2 if len(good) > 1 else 3]]
                readings.append((f['i']['y'], '; '.join(short)))
        prev = single.get(w['s'])
        if not prev or lv < prev[0]:
            single[w['s']] = (lv, w.get('q', 99999), readings, entry[5])
zhvocab.sort(key=lambda r: (r[3], r[4]))

# ---------- Chinese hanzi (derived from HSK words: level = earliest band a character appears in) ----------
hz = {}
for w in zhvocab:
    for ch in w[0]:
        if not ('一' <= ch <= '鿿'):
            continue
        lv, q = w[3], w[4]
        cur = hz.get(ch)
        if not cur or (lv, q) < cur:
            hz[ch] = (lv, q)
hanzi = []
for ch, (lv, q) in hz.items():
    s = single.get(ch)
    o = mmah.get(ch, {})
    if s:
        _, q, readings, trad = s
        py = ' '.join(r[0] for r in readings)
        mean = readings[0][1] if len(readings) == 1 else ' · '.join(f'{r[0]}: {r[1]}' for r in readings)
    else:
        py = ' '.join(o.get('pinyin') or [])
        mean = re.sub(r'\s+', ' ', (o.get('definition') or '').replace(';', '; '))[:90]
        trad = ''
    hanzi.append([ch, lv, q, py, mean, trad, components(ch), origin(ch)])
hanzi.sort(key=lambda r: (r[1], r[2]))

# ---------- Coverage report ----------
jp_stroke = set(x[:-5] for x in os.listdir(npm_package('hanzi-writer-data-jp@0.0.1')) if x.endswith('.json'))
zh_stroke = set(x[:-5] for x in os.listdir(npm_package('hanzi-writer-data@2.0.1')) if x.endswith('.json'))
miss_jp = [k[0] for k in kanji if k[0] not in jp_stroke]
miss_zh = [h[0] for h in hanzi if h[0] not in zh_stroke]
print('kanji', len(kanji), 'missing jp strokes', len(miss_jp), ''.join(miss_jp[:40]))
print('  of those, available in zh data', sum(1 for c in miss_jp if c in zh_stroke))
print('hanzi', len(hanzi), 'missing zh strokes', len(miss_zh), ''.join(miss_zh[:40]))
from collections import Counter
print('hanzi per band', sorted(Counter(h[1] for h in hanzi).items()))
print('ja vocab', len(javocab), 'with pitch', sum(1 for v in javocab if v[4] >= 0), sorted(Counter(v[3] for v in javocab).items()))
print('zh vocab', len(zhvocab), sorted(Counter(v[3] for v in zhvocab).items()))
print('no meaning hanzi', sum(1 for h in hanzi if not h[4]))

# Characters with no JP stroke file fall back to the Chinese file at runtime; record which ones do
data = {
    'kanji': kanji, 'jv': javocab, 'hanzi': hanzi,
    'zv': [v[:6] for v in zhvocab if len(v[0]) > 1],
    'jpNoStroke': ''.join(c for c in miss_jp),
}
s = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
open(ROOT / 'build' / 'data.json', 'w', encoding='utf-8').write(s)
print('bytes', len(s.encode('utf-8')))
print(kanji[:2]); print(hanzi[:2]); print(javocab[:2]); print(zhvocab[:2])

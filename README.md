# Inkstone

Japanese kanji and Chinese hanzi, one card a day at a time. Spaced repetition with FSRS-5, stroke order you can trace, pitch accent and tones, and a Lock Screen widget through Scriptable.

**Live:** https://venus-beetroot.github.io/inkstone/

Built for personal study. Everything runs in the browser; progress is stored on the device.

## What's inside

- **Characters:** 2,211 JLPT kanji (N5 to N1) and 2,970 HSK 3.0 hanzi (bands 1 to 7-9), with readings, meanings, components and origins
- **Vocabulary decks:** 8,034 JLPT words (6,495 with pitch accent) and 9,443 HSK 3.0 words
- **Scheduling:** FSRS-5 with learning and relearning steps, target retention you can set, undo, and a daily new-card goal per language
- **Stroke order:** animation and tracing with hints for every character, using Japanese forms for kanji
- **Audio:** the device's own Japanese and Chinese voices, with a voice picker
- **Dictionary:** search by character, kana, romaji, pinyin with or without tones, or English
- **Stats:** streak, a reviews heatmap, retention over 30 days and a 14-day forecast
- **Backup:** export and import your progress as a JSON file

## Lock Screen widget

iOS only lets native apps put widgets on the Lock Screen, so the widget runs in [Scriptable](https://apps.apple.com/app/id1405459188), a free app that runs JavaScript widgets. The site and Scriptable hand off to each other:

| From | To | How |
| --- | --- | --- |
| Inkstone | Scriptable | **Send to widget** copies your cards and opens `scriptable:///run/Inkstone?import=clipboard`; the script saves them |
| Widget | Inkstone | Tapping a card opens `…/inkstone/#item=<card>` with that entry |
| Empty widget | Inkstone | Tapping opens `…/inkstone/#widget`, the widget settings |
| Scriptable | This repo | **Update script from website** fetches `Inkstone.js` from the site when its version number goes up |

Setup, once:

1. Install Scriptable.
2. In Inkstone: Settings, Lock screen widget, **Copy script**. In Scriptable tap +, paste, and name the script `Inkstone` exactly.
3. Back in Inkstone, tap **Send to widget** and allow it to open Scriptable.
4. Long-press the Lock Screen, Customise, add a Scriptable widget, tap it and set Script to Inkstone.

Optional widget parameter, space separated: `ja` or `zh`, `chars` or `words`, `quiz` (hide the meaning), `20m` (rotation interval), `#2` (a second widget shows different cards).

The widget shows whatever you last sent it. Send again when you move on to new cards.

## Things worth knowing

- Progress lives in the browser that you study in. On iPhone and iPad, a Home Screen web app keeps separate storage from Safari, and widget taps open Safari. Pick one and stay with it, and export a backup now and then.
- `sw.js` makes the app work offline and keeps stroke data once it has been loaded. Settings, Save stroke data offline downloads it for your selected levels ahead of time.

## Layout

```
index.html        the app, built as one self-contained file
sw.js             service worker for offline use
Inkstone.js       the Scriptable widget script (also embedded in index.html for Copy script)
icon.png          home screen icon
src/              index.src.html, the app before data and libraries are inlined
tools/            build_data.py and build.py
tests/            browser tests, FSRS reference check, Scriptable mock test
```

## Building

Needs Python 3 and Node (for `npm pack`). Raw data downloads into `build/cache` on the first run.

```
python3 tools/build_data.py
python3 tools/build.py
```

When you change `Inkstone.js`, raise `const VERSION` at the top so installed widgets can pick up the update.

## Testing

```
pip install playwright "fsrs>=5,<6"
python3 tests/test_app.py            # app flows, and FSRS-5 checked against py-fsrs
python3 tests/test_widget_export.py  # widget export, Send to widget, deep links
node tests/widget_mock_test.js       # every widget size, parameters, rotation, imports, updates
```

Set `CHROME` to a browser path if Playwright's own Chromium is not installed.

## Data and credits

- Kanji: [kanji-data](https://github.com/davidluzgouveia/kanji-data) by David Gouveia, built on KANJIDIC2 from the [EDRDG](https://www.edrdg.org/) (CC BY-SA 4.0), with JLPT levels from Jonathan Waller's lists
- Japanese vocabulary: [open-anki-jlpt-decks](https://github.com/jamsinclair/open-anki-jlpt-decks) by Jamie Sinclair
- Pitch accent: [Kanjium](https://github.com/mifunetoshiro/kanjium) (CC BY-SA 4.0)
- Chinese vocabulary: [complete-hsk-vocabulary](https://github.com/drkameleon/complete-hsk-vocabulary) by drkameleon, definitions from CC-CEDICT (CC BY-SA 4.0)
- Components, origins and stroke data: [Make Me a Hanzi](https://github.com/skishore/makemeahanzi) and [animCJK](https://github.com/parsimonhi/animCJK) (Arphic Public License, LGPL), served through Hanzi Writer's data packages
- Libraries: [Hanzi Writer](https://github.com/chanind/hanzi-writer) (MIT), [WanaKana](https://github.com/WaniKani/WanaKana) (MIT)
- Scheduling: [FSRS](https://github.com/open-spaced-repetition) by Open Spaced Repetition (MIT)

The data bundled in `index.html` keeps its original licences.

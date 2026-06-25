# Memory Hunt

A photo-based "memory game meets scavenger hunt" for phones. Each pair of
matching QR codes is hidden somewhere physical (around a yard, a house, a
venue). Players scan codes one at a time with their phone's camera; each
scan briefly reveals the photo and name hidden behind that station. Find
both stations for the same photo to claim a pair. The app tracks how many
pairs you've found and how long it's taken, and celebrates when every pair
is found.

It's a static web app (HTML/CSS/JS, installable as a PWA) — no server or
backend required, just a folder of files served over HTTPS (or opened
locally for testing).

## Project files

| File / folder | Purpose |
|---|---|
| `index.html`, `css/style.css`, `js/app.js` | The app itself (screens, styling, game logic). |
| `game.json` | The current game's data: title, reveal timer, and the list of photo pairs with their station codes. |
| `photos/` | The actual photo files referenced by `game.json`. |
| `station_codes.json` | Persistent mapping of physical station slots → secret 8-character codes. Keeps printed QR codes valid even if you later change the photos. |
| `gen_game_from_photos.py` | Builds `game.json` (and assigns codes in `station_codes.json`) from whatever is in `photos/`. |
| `gen_qr.py` | Renders a printable PDF (`qr_sheet.pdf`) of QR codes, one per station. |
| `build_standalone.py` | Bundles everything into one self-contained `standalone.html` file (handy for sharing/testing without a server). |
| `manifest.json`, `sw.js`, `icon.svg` | PWA install support (home-screen icon, offline caching). |

## Changing the photos

You have two options depending on whether you're changing how many pairs
there are.

### Option A — same number of photos (just swapping content)

The station codes printed on your QR sheet are tied to the **physical
station slots**, not to the photos themselves, so you can swap photos
without reprinting anything:

1. Drop the new image files into `photos/`, replacing the old ones (or
   keeping the same filenames if you just want to update the picture
   behind an existing name).
2. Open `game.json` and for each pair update:
   - `"label"` — the name to show on screen.
   - `"photo"` — the path to the image, e.g. `"photos/newname.jpg"`.
   - Leave `"stations"` untouched — those codes match what's already
     printed on `qr_sheet.pdf`.

No commands need to be run for this option.

### Option B — adding, removing, or fully regenerating photos

Use `gen_game_from_photos.py` to rebuild `game.json` automatically from
whatever is currently in `photos/`:

```
python3 gen_game_from_photos.py
```

This scans `photos/`, turns each image into one pair (named after the
filename, minus its extension), and assigns each pair two station codes —
reusing existing codes for slots that already exist, and minting new
random codes only for newly added slots. It also writes/updates
`station_codes.json` so codes stay stable across future re-runs.

Parameters (all optional):

| Flag | Default | Meaning |
|---|---|---|
| `--photos-dir` | `photos` | Folder to scan for images. |
| `--title` | `Get to Know Each Other` | Game title shown on the home screen. |
| `--reveal-seconds` | `10` | How many seconds a photo stays visible after a successful scan. |
| `--game-id` | `photo1` | Internal identifier for this game (used in QR-code URLs). |
| `--out` | `game.json` | Where to write the generated game file. |
| `--codes-file` | `station_codes.json` | Where the slot → secret-code mapping is stored/read. |
| `--regen-codes` | off | Wipes all existing codes and issues brand-new random ones for every station. **This invalidates any previously printed QR sheets** — only use this if you're reprinting everything from scratch. |

Example with custom title and a 15-second reveal:

```
python3 gen_game_from_photos.py --title "Family Reunion 2026" --reveal-seconds 15
```

### Printing QR codes

Run this whenever the **number** of stations changes (new photos added
beyond what was already covered) — not needed for simple photo swaps:

```
python3 gen_qr.py --base-url https://yourapp.example.com/index.html --game game.json --out qr_sheet.pdf
```

Parameters:

| Flag | Default | Meaning |
|---|---|---|
| `--game` | `game.json` | Which game file to read station codes from. |
| `--base-url` | `index.html` | The URL players' phones will hit when they scan a code — should be wherever you've deployed the app. Each QR code encodes `<base-url>?game=<gameId>&station=<code>`. |
| `--out` | `qr_sheet.pdf` | Output PDF path. Produces a multi-page A4 PDF, 4 QR codes per page, each labeled with its station code. |

### Rebuilding the standalone file

If you maintain `standalone.html` as a single-file copy of the app (for
easy sharing without hosting), regenerate it after any change to
`index.html`, `css/style.css`, `js/app.js`, or `game.json` so it doesn't
drift out of sync:

```
python3 build_standalone.py
```

No parameters — it always reads the four source files above and writes
`standalone.html`.

## Testing without scanning real QR codes

On the home screen, use the "type a station code to simulate a scan"
box to enter a station code manually (from `station_codes.json` or the
printed sheet) instead of using the camera.

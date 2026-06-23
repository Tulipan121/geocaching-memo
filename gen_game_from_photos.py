#!/usr/bin/env python3
"""
Build game.json from the contents of the photos/ folder.

Drop one image per person into photos/ (e.g. photos/Alice.jpg,
photos/Bob.png). Each photo becomes one pair, hidden behind 2 QR
stations — scanning either station shows that same photo + the
person's name (the filename without its extension). Re-run this
script any time you add, remove, or rename photos, then re-run
gen_qr.py to print fresh QR codes for the new station list.

Station security
-----------------
What actually gets printed on the QR codes (and embedded in the scan
URL) is NOT a guessable "S01", "S02", ... sequence. Each physical
station slot is assigned a random 8-character alphanumeric secret code,
persisted in a codes file (default: station_codes.json) next to this
script. That means:

  - Swapping which photos are used, renaming photos, or re-running this
    script does NOT change the codes already printed on paper — the
    codes belong to the physical station slots, not to specific photos.
  - You only need to reprint QR codes (via gen_qr.py) when the NUMBER
    of stations grows (new photos added beyond what's already covered).
  - If you ever want to invalidate every previously printed sheet and
    issue all-new random codes, pass --regen-codes.

Usage:
    python3 gen_game_from_photos.py [--title "My Game"] [--reveal-seconds 10]
    python3 gen_game_from_photos.py --regen-codes   # wipe & reissue all codes
"""
import argparse
import json
import re
import secrets
from pathlib import Path

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

# Characters used for secret station codes. Visually-ambiguous characters
# (0/O, 1/I/L) are excluded so codes are easy to read off a printed sheet
# or type into the manual-entry box without mistakes.
CODE_ALPHABET = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
CODE_LENGTH = 8


def station_slot(n):
    """Internal slot id — never shown to players, just a stable key into
    the codes file so the same physical station keeps the same code."""
    return 'slot%02d' % n


def slugify(name):
    return re.sub(r'[^a-zA-Z0-9]+', '_', name).strip('_')


def gen_code(existing):
    while True:
        code = ''.join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        if code not in existing:
            return code


def load_codes(path):
    p = Path(path)
    if p.is_file():
        with open(p) as f:
            return json.load(f)
    return {}


def save_codes(path, codes):
    with open(path, 'w') as f:
        json.dump(codes, f, indent=2, sort_keys=True)
        f.write('\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--photos-dir', default='photos')
    ap.add_argument('--title', default='Get to Know Each Other')
    ap.add_argument('--reveal-seconds', type=int, default=10)
    ap.add_argument('--game-id', default='photo1')
    ap.add_argument('--out', default='game.json')
    ap.add_argument('--codes-file', default='station_codes.json',
                     help='Where the persistent slot -> secret-code mapping is stored.')
    ap.add_argument('--regen-codes', action='store_true',
                     help='Throw away all existing codes and issue brand new random ones '
                          'for every station. This invalidates any previously printed QR sheets.')
    args = ap.parse_args()

    photos_dir = Path(args.photos_dir)
    if not photos_dir.is_dir():
        raise SystemExit(f'No such folder: {photos_dir} (create it and add photos first)')

    files = sorted(
        p for p in photos_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    )
    if not files:
        raise SystemExit(
            f'No images found in {photos_dir}/ '
            f'(supported: {", ".join(sorted(IMAGE_EXTS))})'
        )

    codes = {} if args.regen_codes else load_codes(args.codes_file)
    used_codes = set(codes.values())

    def code_for_slot(slot_id):
        if slot_id in codes:
            return codes[slot_id]
        code = gen_code(used_codes)
        codes[slot_id] = code
        used_codes.add(code)
        return code

    pairs = []
    station_n = 1
    for i, f in enumerate(files, start=1):
        name = f.stem  # filename without extension
        slot1, slot2 = station_slot(station_n), station_slot(station_n + 1)
        station_n += 2
        st1, st2 = code_for_slot(slot1), code_for_slot(slot2)
        pairs.append({
            'pairId': 'p' + str(i),
            'label': name,
            'photo': str(photos_dir) + '/' + f.name,
            'stations': [st1, st2],
        })

    save_codes(args.codes_file, codes)

    game = {
        'gameId': args.game_id,
        'title': args.title,
        'revealSeconds': args.reveal_seconds,
        'pairs': pairs,
    }

    with open(args.out, 'w') as out:
        json.dump(game, out, indent=2)
        out.write('\n')

    print(f'Wrote {args.out} with {len(pairs)} pairs from {len(files)} photos in {photos_dir}/')
    print('Station codes in use: ' + ', '.join(s for p in pairs for s in p['stations']))
    if args.regen_codes:
        print('All station codes were regenerated — any previously printed QR sheets are now invalid.')
    print(f'Secret codes saved to {args.codes_file} — keep this file so codes stay stable '
          f'across future re-runs (even if you swap out the photos).')
    print('Next: run gen_qr.py to print QR codes for these station codes.')


if __name__ == '__main__':
    main()

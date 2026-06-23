#!/usr/bin/env python3
"""
Build game.json from the contents of the photos/ folder.

Drop one image per person into photos/ (e.g. photos/Alice.jpg,
photos/Bob.png). Each photo becomes one pair, hidden behind 2 QR
stations — scanning either station shows that same photo + the
person's name (the filename without its extension). Re-run this
script any time you add, remove, or rename photos, then re-run
gen_qr.py to print fresh QR codes for the new station list.

Usage:
    python3 gen_game_from_photos.py [--title "My Game"] [--reveal-seconds 10]
"""
import argparse
import json
import re
from pathlib import Path

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

def station_label(n):
    return 'S%02d' % n

def slugify(name):
    return re.sub(r'[^a-zA-Z0-9]+', '_', name).strip('_')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--photos-dir', default='photos')
    ap.add_argument('--title', default='Get to Know Each Other')
    ap.add_argument('--reveal-seconds', type=int, default=10)
    ap.add_argument('--game-id', default='photo1')
    ap.add_argument('--out', default='game.json')
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

    pairs = []
    station_n = 1
    for i, f in enumerate(files, start=1):
        name = f.stem  # filename without extension
        st1, st2 = station_label(station_n), station_label(station_n + 1)
        station_n += 2
        pairs.append({
            'pairId': 'p' + str(i),
            'label': name,
            'photo': str(photos_dir) + '/' + f.name,
            'stations': [st1, st2],
        })

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
    print('Stations used: ' + ', '.join(s for p in pairs for s in p['stations']))
    print('Next: run gen_qr.py to print QR codes for these station IDs.')

if __name__ == '__main__':
    main()

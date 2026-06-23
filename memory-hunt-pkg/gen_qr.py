#!/usr/bin/env python3
"""
Generate a printable sheet of QR codes for a Memory Hunt game.

Each QR code encodes a URL pointing at the deployed app, e.g.:
    https://yourapp.example.com/index.html?game=demo1&station=S01

Usage:
    python3 gen_qr.py --base-url https://yourapp.example.com/index.html --game game.json --out qr_sheet.png

For local testing without a real deployment, you can omit --base-url and it
will default to a relative form usable when testing on the same device.
"""
import argparse
import json
import math
import cv2
import numpy as np


def make_qr_image(text, box_size=8, border=4):
    enc = cv2.QRCodeEncoder.create()
    matrix = enc.encode(text)  # already 0=black module, 255=white module
    h, w = matrix.shape
    img = np.full((h + 2 * border, w + 2 * border), 255, dtype=np.uint8)
    img[border:border + h, border:border + w] = matrix
    img = cv2.resize(img, ((w + 2 * border) * box_size, (h + 2 * border) * box_size),
                      interpolation=cv2.INTER_NEAREST)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', default='game.json')
    ap.add_argument('--base-url', default='index.html')
    ap.add_argument('--out', default='qr_sheet.png')
    ap.add_argument('--cols', type=int, default=3)
    args = ap.parse_args()

    with open(args.game) as f:
        game = json.load(f)

    stations = []
    for pair in game['pairs']:
        for st in pair['stations']:
            stations.append(st)
    stations.sort()

    tiles = []
    cell_w = cell_h = 0
    label_h = 36
    for st in stations:
        url = f"{args.base_url}?game={game['gameId']}&station={st}"
        qr = make_qr_image(url)
        cell_w, cell_h = qr.shape[1], qr.shape[0]
        canvas = np.full((cell_h + label_h, cell_w), 255, dtype=np.uint8)
        canvas[0:cell_h, 0:cell_w] = qr
        cv2.putText(canvas, st, (cell_w // 2 - 18, cell_h + 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,), 2, cv2.LINE_AA)
        tiles.append(canvas)

    cols = args.cols
    rows = math.ceil(len(tiles) / cols)
    pad = 20
    tile_h, tile_w = tiles[0].shape
    sheet_w = cols * tile_w + (cols + 1) * pad
    sheet_h = rows * tile_h + (rows + 1) * pad
    sheet = np.full((sheet_h, sheet_w), 255, dtype=np.uint8)

    for i, tile in enumerate(tiles):
        r, c = divmod(i, cols)
        y = pad + r * (tile_h + pad)
        x = pad + c * (tile_w + pad)
        sheet[y:y + tile_h, x:x + tile_w] = tile

    cv2.imwrite(args.out, sheet)
    print(f"Wrote {len(stations)} QR codes to {args.out}")
    print("Stations:", ', '.join(stations))


if __name__ == '__main__':
    main()

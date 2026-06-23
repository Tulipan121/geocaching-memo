#!/usr/bin/env python3
"""
Generate a printable PDF sheet of QR codes for a Memory Hunt game.

Each QR code encodes a URL pointing at the deployed app, e.g.:
    https://yourapp.example.com/index.html?game=demo1&station=S01

The output is a multi-page PDF, with each page being a single A4 sheet
divided into a 2x2 grid (4 QR codes per page, each taking 1/4 of the page).

Usage:
    python3 gen_qr.py --base-url https://yourapp.example.com/index.html --game game.json --out qr_sheet.pdf

For local testing without a real deployment, you can omit --base-url and it
will default to a relative form usable when testing on the same device.
"""
import argparse
import json
import cv2
import numpy as np
from PIL import Image
import PIL.JpegImagePlugin  # ensure JPEG plugin is registered for PDF export

# A4 size at 300 DPI
DPI = 300
A4_W = int(8.27 * DPI)   # 2481 px
A4_H = int(11.69 * DPI)  # 3507 px


def make_qr_image(text, box_size=8, border=4):
    enc = cv2.QRCodeEncoder.create()
    matrix = enc.encode(text)  # already 0=black module, 255=white module
    h, w = matrix.shape
    img = np.full((h + 2 * border, w + 2 * border), 255, dtype=np.uint8)
    img[border:border + h, border:border + w] = matrix
    img = cv2.resize(img, ((w + 2 * border) * box_size, (h + 2 * border) * box_size),
                      interpolation=cv2.INTER_NEAREST)
    return img


def make_tile(st, url, cell_size, label_h=60):
    """Build a single QR tile (QR code + station label) sized to fit within
    a cell_size x cell_size box, including the label."""
    qr = make_qr_image(url)
    qr_target = cell_size - label_h
    qr = cv2.resize(qr, (qr_target, qr_target), interpolation=cv2.INTER_NEAREST)

    canvas = np.full((cell_size, cell_size), 255, dtype=np.uint8)
    x_off = (cell_size - qr_target) // 2
    canvas[0:qr_target, x_off:x_off + qr_target] = qr

    text_size = cv2.getTextSize(st, cv2.FONT_HERSHEY_SIMPLEX, 1.4, 3)[0]
    tx = (cell_size - text_size[0]) // 2
    ty = qr_target + (label_h + text_size[1]) // 2
    cv2.putText(canvas, st, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0,), 3, cv2.LINE_AA)
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', default='game.json')
    ap.add_argument('--base-url', default='index.html')
    ap.add_argument('--out', default='qr_sheet.pdf')
    args = ap.parse_args()

    with open(args.game) as f:
        game = json.load(f)

    stations = []
    for pair in game['pairs']:
        for st in pair['stations']:
            stations.append(st)
    stations.sort()

    half_w, half_h = A4_W // 2, A4_H // 2
    cell_size = min(half_w, half_h)
    margin_x = (half_w - cell_size) // 2
    margin_y = (half_h - cell_size) // 2

    pages = []
    for page_start in range(0, len(stations), 4):
        page_stations = stations[page_start:page_start + 4]
        sheet = np.full((A4_H, A4_W), 255, dtype=np.uint8)
        for i, st in enumerate(page_stations):
            url = f"{args.base_url}?game={game['gameId']}&station={st}"
            tile = make_tile(st, url, cell_size)
            r, c = divmod(i, 2)
            y = r * half_h + margin_y
            x = c * half_w + margin_x
            sheet[y:y + cell_size, x:x + cell_size] = tile
        pages.append(Image.fromarray(sheet).convert('RGB'))

    pages[0].save(args.out, save_all=True, append_images=pages[1:])
    print(f"Wrote {len(stations)} QR codes ({len(pages)} page(s), 4 per page) to {args.out}")
    print("Stations:", ', '.join(stations))


if __name__ == '__main__':
    main()

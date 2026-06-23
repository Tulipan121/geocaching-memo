#!/usr/bin/env python3
"""
Assemble standalone.html (one self-contained file: inline CSS + JS + game
data, no fetch, no service worker) from the canonical multi-file source
(index.html, css/style.css, js/app.js, game.json). Run this after editing
any of those source files so the two builds never drift apart.
"""
import json
import re

with open('index.html') as f:
    html = f.read()
with open('css/style.css') as f:
    css = f.read()
with open('js/app.js') as f:
    js = f.read()
with open('game.json') as f:
    game = json.load(f)

# Drop the manifest link and external stylesheet link, inline the CSS instead.
html = re.sub(r'\s*<link rel="manifest"[^>]*>\n', '\n', html)
html = re.sub(
    r'<link rel="stylesheet" href="css/style.css">',
    '<style>\n' + css + '\n</style>',
    html,
)

# Replace the external script tag with the embedded game data + app.js inline.
embedded = 'const EMBEDDED_GAME = ' + json.dumps(game, indent=2) + ';\n\n' + js
html = html.replace(
    '<script src="js/app.js"></script>',
    '<script>\n' + embedded + '\n</script>',
)

with open('standalone.html', 'w') as f:
    f.write(html)

print('Wrote standalone.html (%d bytes)' % len(html))

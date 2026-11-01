#!/usr/bin/env python3
"""ascii.png (white glyphs on black) -> ascii.svg: types in row by row, cursor on the edge, light/dark aware.

SMIL, not script, because GitHub strips <script>. The PNG is inlined since an SVG shown via <img> can't load files.
"""
import base64, io, sys
from PIL import Image

SRC = sys.argv[1] if len(sys.argv) > 1 else "ascii.png"
OUT = sys.argv[2] if len(sys.argv) > 2 else "ascii.svg"
ROW, DELAY, DUR = 17, 0.055, 0.35     # px per text row, stagger and wipe time in seconds

g = Image.open(SRC).convert("L")
w, h = g.size
rgba = Image.new("LA", g.size, 255)    # white glyphs; luminance becomes opacity so the black drops out
rgba.putalpha(g)
buf = io.BytesIO()
rgba.save(buf, "PNG", optimize=True)
b64 = base64.b64encode(buf.getvalue()).decode()

rows = -(-h // ROW)
p = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}" '
     f'viewBox="0 0 {w} {h}" role="img" aria-label="ASCII portrait of Joydeep Das">',
     '<style>.a{filter:none}.c{fill:#e6edf3}'
     '@media(prefers-color-scheme:light){.a{filter:brightness(.18)}.c{fill:#1f2328}}</style>',
     f'<defs><image id="i" width="{w}" height="{h}" xlink:href="data:image/png;base64,{b64}"/>']
for r in range(rows):
    p.append(f'<clipPath id="c{r}"><rect x="0" y="{r * ROW}" height="{ROW}" width="0">'
             f'<animate attributeName="width" from="0" to="{w}" begin="{r * DELAY:.3f}s" dur="{DUR}s" fill="freeze"/>'
             f'</rect></clipPath>')
p.append('</defs>')
for r in range(rows):
    p.append(f'<g class="a" clip-path="url(#c{r})"><use xlink:href="#i"/></g>')
    # the cursor: a block riding the wipe edge, gone once the row has landed
    t0, t1 = r * DELAY, r * DELAY + DUR
    p.append(f'<rect class="c" y="{r * ROW + 2}" width="8" height="{ROW - 4}" opacity="0">'
             f'<animate attributeName="x" from="0" to="{w}" begin="{t0:.3f}s" dur="{DUR}s" fill="freeze"/>'
             f'<set attributeName="opacity" to="0.85" begin="{t0:.3f}s"/>'
             f'<set attributeName="opacity" to="0" begin="{t1:.3f}s"/></rect>')
p.append('</svg>')
open(OUT, "w").write("".join(p))
print(f"{OUT}: {rows} rows, {len(b64) // 1024} KB image, types in over {rows * DELAY:.1f}s")

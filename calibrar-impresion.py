#!/usr/bin/env python3
"""
Calibra --print-scale y --print-height para una version de idioma.

Mide la altura real del documento con el ancho de diseno (900px) y calcula
la escala necesaria para que quepa en una sola pagina A4 con margen de 8mm,
dejando un 1% de holgura. Escribe los dos valores en el bloque <style> del
propio HTML.

Hay que ejecutarlo cada vez que cambien los textos de una version, porque la
longitud del texto cambia la altura total del documento.

Uso:  python3 calibrar-impresion.py es-MX/factura.html
"""
import pathlib, re, sys, math
from playwright.sync_api import sync_playwright

DESIGN_W = 900          # px, ancho al que esta calibrado el diseno aprobado
MARGIN_MM = 8           # coincide con @page { margin } en factura.css
SAFETY = 0.99           # 1% de holgura para no rozar el borde de la hoja
PX_PER_MM = 96 / 25.4

def calibrate(path):
    path = pathlib.Path(path).resolve()
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": DESIGN_W + 40, "height": 1400})
        pg.goto(path.as_uri())
        pg.wait_for_timeout(1500)
        h = pg.evaluate("document.querySelector('.invoice').getBoundingClientRect().height")
        b.close()

    avail_w = (210 - 2 * MARGIN_MM) * PX_PER_MM
    avail_h = (297 - 2 * MARGIN_MM) * PX_PER_MM
    scale = min(avail_w / DESIGN_W, avail_h / h) * SAFETY
    height = math.ceil(h * scale)
    limit = "ancho" if avail_w / DESIGN_W < avail_h / h else "alto"

    s = path.read_text()
    s = re.sub(r"--print-scale: [\d.]+;", f"--print-scale: {scale:.4f};", s)
    s = re.sub(r"--print-height: \d+px;", f"--print-height: {height}px;", s)
    path.write_text(s)

    print(f"{path.parent.name}/{path.name}")
    print(f"  altura del documento : {h:.1f}px")
    print(f"  limitado por el      : {limit} de la hoja")
    print(f"  --print-scale        : {scale:.4f}")
    print(f"  --print-height       : {height}px")
    print(f"  ocupa                : {height / avail_h * 100:.1f}% del alto util, "
          f"{DESIGN_W * scale / avail_w * 100:.1f}% del ancho util")

if __name__ == "__main__":
    for arg in sys.argv[1:] or ["es-MX/factura.html"]:
        calibrate(arg)

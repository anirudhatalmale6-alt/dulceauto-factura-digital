#!/usr/bin/env python3
"""
Extrae todos los textos traducibles de una version y genera:
  - textos-<idioma>.json  : pares clave/texto, para rellenar
  - textos-<idioma>.txt   : la misma lista en formato legible

Recorre el DOM real, asi que no se escapa ningun texto ni se cuela ningun
trozo de markup.

Uso:  python3 extraer-textos.py es-MX/factura.html
"""
import json, pathlib, re, sys
from playwright.sync_api import sync_playwright

JS = r"""() => {
  const SECTIONS = [
    ['.header', 'cabecera'], ['.intro', 'intro'], ['.customer-card', 'cliente'],
    ['.document-card', 'documentacion'], ['.transaction-card', 'transaccion'],
    ['.vehicle-card', 'vehiculo'], ['.operation', 'operacion'],
    ['.transfer', 'transferencia'], ['.faq', 'faq'],
    ['.protection-card', 'proteccion'], ['.protection-details', 'respaldo'],
    ['.verification-qr', 'qr'], ['.agent-card', 'representante'], ['.legal', 'legal'],
  ];
  const sectionOf = (el) => {
    for (const [sel, name] of SECTIONS) if (el.closest(sel)) return name;
    return 'otros';
  };
  const out = [];
  const seen = new Set();
  const walker = document.createTreeWalker(document.querySelector('.invoice'), NodeFilter.SHOW_TEXT);
  let n;
  while ((n = walker.nextNode())) {
    const t = n.textContent.replace(/\s+/g, ' ').trim();
    if (!t) continue;
    if (!/[a-zA-ZÀ-ÿ]/.test(t)) continue;      // numeros y separadores sueltos
    if (/^(DulceAuto|CARFAX|SPEI|REPUVE|BBVA|INE|MXN|CLABE)$/.test(t)) continue;  // marcas y siglas
    const el = n.parentElement;
    const field = el.closest('[data-field]');
    out.push({
      section: sectionOf(el),
      text: t,
      dynamic: !!field,            // valor que vendra del backend
      field: field ? field.getAttribute('data-field') : null,
    });
  }
  // atributos visibles para el usuario o para lectores de pantalla
  document.querySelectorAll('.invoice [alt], .invoice [aria-label]').forEach(e => {
    for (const a of ['alt', 'aria-label']) {
      const v = (e.getAttribute(a) || '').trim();
      if (v && !seen.has(a + v)) { seen.add(a + v);
        out.push({ section: sectionOf(e), text: v, dynamic: false, field: null, attr: a }); }
    }
  });
  return out;
}"""

def slug(s):
    s = re.sub(r'[^a-z0-9]+', '_', s.lower().strip())
    return re.sub(r'^_|_$', '', s)[:40] or 'texto'

def run(path):
    path = pathlib.Path(path).resolve()
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 940, "height": 1400})
        pg.goto(path.as_uri()); pg.wait_for_timeout(1500)
        items = pg.evaluate(JS); b.close()

    entries, used = [], {}
    for it in items:
        base = f"{it['section']}.{slug(it['text'])}"
        used[base] = used.get(base, 0) + 1
        key = base if used[base] == 1 else f"{base}_{used[base]}"
        it['key'] = key
        entries.append(it)

    lang = path.parent.name
    outdir = path.parent.parent
    static = [e for e in entries if not e['dynamic']]
    dynamic = [e for e in entries if e['dynamic']]

    (outdir / f"textos-{lang}.json").write_text(
        json.dumps({e['key']: e['text'] for e in static}, ensure_ascii=False, indent=2))

    lines = [f"TEXTOS A TRADUCIR — origen {lang}",
             f"{len(static)} textos fijos  |  {len(dynamic)} valores dinamicos (no traducir, vienen de BBDD)",
             "=" * 78, ""]
    cur = None
    for e in static:
        if e['section'] != cur:
            cur = e['section']; lines += ["", f"--- {cur.upper()} " + "-" * (70 - len(cur))]
        tag = "  [texto alternativo]" if e.get('attr') else ""
        lines.append(f"{e['key']}{tag}\n    {e['text']}")
    lines += ["", "", "=" * 78,
              "VALORES DINAMICOS — no hace falta traducirlos, los pondra el backend:",
              ""]
    for e in dynamic:
        lines.append(f"  {{{{{e['field']}}}}}   ejemplo actual: {e['text']}")
    (outdir / f"textos-{lang}.txt").write_text("\n".join(lines))

    print(f"{len(static)} textos fijos y {len(dynamic)} valores dinamicos")
    print(f"  -> textos-{lang}.json")
    print(f"  -> textos-{lang}.txt")

if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "es-MX/factura.html")

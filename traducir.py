#!/usr/bin/env python3
"""
Genera una version de idioma a partir de la plantilla es-MX aprobada.

Sustituye UNICAMENTE los textos. No toca el marcado, ni las clases, ni los
atributos data-field, ni el sprite de iconos: la estructura que sale es
exactamente la misma que entra, asi que el VIEW aprobado no se puede romper
por esta via.

Usa las mismas claves que genera extraer-textos.py, con la misma logica de
seccion y de slug, de modo que los archivos de traduccion encajan directamente.

Uso:
    python3 traducir.py DulceAuto_textos_EN.txt en/invoice.html en

Despues hay que calibrar la impresion de la version nueva:
    python3 calibrar-impresion.py en/invoice.html
"""
import json, pathlib, re, sys
from lxml import html as LH

TEMPLATE = "es-MX/factura.html"

SECTIONS = [("header", "cabecera"), ("intro", "intro"), ("customer-card", "cliente"),
            ("document-card", "documentacion"), ("transaction-card", "transaccion"),
            ("vehicle-card", "vehiculo"), ("operation", "operacion"),
            ("transfer", "transferencia"), ("faq", "faq"),
            ("protection-card", "proteccion"), ("protection-details", "respaldo"),
            ("verification-qr", "qr"), ("agent-card", "representante"), ("legal", "legal")]

SKIP = re.compile(r"^(DulceAuto|CARFAX|SPEI|REPUVE|BBVA|INE|MXN|CLABE)$")
HAS_LETTER = re.compile(r"[a-zA-ZÀ-ÿ]")


def slug(s):
    s = re.sub(r"[^a-z0-9]+", "_", s.lower().strip())
    return re.sub(r"^_|_$", "", s)[:40] or "texto"


def section_of(el):
    cur = el
    while cur is not None:
        classes = (cur.get("class") or "").split()
        for cls, name in SECTIONS:
            if cls in classes:
                return name
        cur = cur.getparent()
    return "otros"


def parse_translations(path):
    """Lee el .txt del cliente: linea de clave, luego linea(s) indentadas."""
    out, key, buf = {}, None, []
    for raw in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.startswith(("---", "===", "  {{")):
            continue
        if raw.startswith(" "):
            if key:
                buf.append(raw.strip())
        else:
            if key and buf:
                out[key] = " ".join(buf)
            m = re.match(r"^([a-z_]+\.[a-z0-9_]+)", raw.strip())
            key, buf = (m.group(1) if m else None), []
    if key and buf:
        out[key] = " ".join(buf)
    return out


# lxml serializa en HTML y pasa a minusculas los nombres de atributo. En SVG
# eso importa: "viewBox" en camelCase es obligatorio. El parser HTML de los
# navegadores lo corrige solo, asi que en pantalla no se nota, pero un parser
# XML estricto o segun que generador de PDF de servidor se lo salta y los
# iconos dejan de escalar. Se restaura al escribir el archivo.
SVG_CAMEL = ["viewBox", "preserveAspectRatio", "patternUnits", "gradientUnits",
             "gradientTransform", "clipPathUnits", "markerWidth", "markerHeight",
             "refX", "refY", "baseProfile", "textLength", "startOffset"]


def fix_svg_case(html_text):
    for attr in SVG_CAMEL:
        html_text = re.sub(rf"\b{attr.lower()}=", f"{attr}=", html_text)
    return html_text


def build(txt_path, out_path, lang):
    tr = parse_translations(txt_path)
    doc = LH.parse(TEMPLATE).getroot()
    invoice = doc.cssselect(".invoice")[0]

    used, missing, counts = set(), [], {}

    def key_for(section, text):
        base = f"{section}.{slug(text)}"
        counts[base] = counts.get(base, 0) + 1
        return base if counts[base] == 1 else f"{base}_{counts[base]}"

    # --- nodos de texto, en orden de documento ---
    for el in invoice.iter():
        if not isinstance(el.tag, str):      # comentarios y nodos de proceso
            continue
        for attr in ("text", "tail"):
            val = getattr(el, attr)
            if not val:
                continue
            stripped = val.strip()
            if not stripped or not HAS_LETTER.search(stripped) or SKIP.match(stripped):
                continue
            owner = el if attr == "text" else el.getparent()
            k = key_for(section_of(owner), re.sub(r"\s+", " ", stripped))
            if k in tr:
                lead = val[:len(val) - len(val.lstrip())]
                trail = val[len(val.rstrip()):]
                setattr(el, attr, f"{lead}{tr[k]}{trail}")
                used.add(k)
            else:
                missing.append((k, stripped[:60]))

    # --- atributos visibles / de accesibilidad ---
    seen = set()
    for el in invoice.iter():
        if not isinstance(el.tag, str):
            continue
        for attr in ("alt", "aria-label"):
            v = (el.get(attr) or "").strip()
            if not v or (attr, v) in seen:
                continue
            seen.add((attr, v))
            k = key_for(section_of(el), v)
            if k in tr:
                el.set(attr, tr[k]); used.add(k)
            else:
                missing.append((k, v[:60]))

    # --- valores de muestra de los data-field ---
    # En produccion los sirve el backend. Aqui se sustituyen para que la
    # version de muestra no ensene texto en espanol dentro de la factura en
    # ingles. Si el original estaba en mayusculas, se respeta.
    muestras_file = pathlib.Path(f"muestras-{lang}.json")
    if muestras_file.exists():
        muestras = json.loads(muestras_file.read_text(encoding="utf-8"))
        cambiados = 0
        for el in invoice.iter():
            if not isinstance(el.tag, str):
                continue
            f = el.get("data-field")
            if not f or f not in muestras or len(el):
                continue
            orig = (el.text or "").strip()
            nuevo = muestras[f]
            if orig and orig == orig.upper() and orig != orig.lower():
                nuevo = nuevo.upper()
            if orig != nuevo:
                el.text = nuevo; cambiados += 1
        print(f"  valores de muestra sustituidos: {cambiados}")

    # el <title> vive fuera de .invoice, se toma del titulo de la cabecera
    titulo = tr.get("cabecera.pre_factura_de_reserva")
    if titulo:
        for t in doc.cssselect("title"):
            t.text = f"DulceAuto — {titulo}"

    doc.set("lang", lang)
    out = pathlib.Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("<!doctype html>\n" + fix_svg_case(LH.tostring(doc, encoding="unicode")),
                   encoding="utf-8")

    unused = sorted(set(tr) - used)
    print(f"{out_path}  (lang={lang})")
    print(f"  aplicados : {len(used)} de {len(tr)} textos del archivo")
    if missing:
        print(f"  SIN TRADUCCION ({len(missing)}):")
        for k, t in missing:
            print(f"     {k}  <-  {t}")
    if unused:
        print(f"  CLAVES DEL ARCHIVO NO USADAS ({len(unused)}):")
        for k in unused:
            print(f"     {k}")
    if not missing and not unused:
        print("  todo encaja, sin claves sueltas por ningun lado")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], sys.argv[3])

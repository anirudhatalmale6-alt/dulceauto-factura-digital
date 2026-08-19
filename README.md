# DulceAuto — Pre-factura de reserva

Factura digital en HTML + CSS, preparada para verse en pantalla, imprimirse en
**A4 a una sola página** y alimentar después la generación de PDF desde
backend.

Estado actual: **las tres versiones terminadas**, cada una con su PDF A4 de una
sola página.

---

## Estructura

```
es-MX/factura.html         version español de México
en/invoice.html            version English
es-AR/factura.html         version español de Argentina

assets/css/factura.css     hoja de estilos UNICA, compartida por las 3 versiones
assets/fonts/*.woff2       Inter incrustada en local (SIL OFL 1.1)
assets/icons/*.svg         iconos sueltos, archivos fuente
assets/img/                fotos del vehiculo + QR y codigo de barras en SVG

pdf/DulceAuto-*.pdf        los tres PDF A4 ya generados
textos/textos-*.txt        textos fuente de cada version (origen de la verdad)
calibrar-impresion.py      recalcula el ajuste de impresion de cada idioma
extraer-textos.py          saca todos los textos traducibles de una version
traducir.py                genera una version de idioma desde la plantilla es-MX
muestras-<idioma>.json     valores de muestra de los data-field por idioma
```

Un solo CSS para las tres versiones: cualquier retoque se aplica a las tres a
la vez y no se desincronizan.

---

## Impresión A4

El PDF reproduce el **mismo diseño horizontal que se ve en pantalla**, no una
maqueta apilada.

Dos cosas lo hacen posible:

1. Todas las media queries responsive están limitadas con `screen and`. Sin
   eso, el ancho útil del A4 (unos 756px) activa el breakpoint de 820px y la
   impresión sale con la maquetación de tablet.
2. El documento se compone al ancho de diseño (900px) y se escala al tamaño de
   la hoja con `transform: scale()`. Se usa `transform` y no `zoom` porque
   `zoom` no es estándar y lo ignoran wkhtmltopdf, DomPDF y WeasyPrint, que son
   las librerías habituales para generar el PDF desde servidor.

Cada versión de idioma lleva sus propios valores en un bloque `<style>` corto:

```html
<style>
  :root { --print-scale: 0.8066; --print-height: 1051px; }
</style>
```

Valores calibrados actualmente:

| version | --print-scale | --print-height |
|---------|---------------|----------------|
| es-MX   | 0.8066        | 1051px         |
| en      | 0.8066        | 1051px         |
| es-AR   | 0.8066        | 1051px         |

### Al cambiar textos, recalibrar

La longitud del texto cambia la altura del documento, así que después de tocar
los textos de una versión hay que volver a calcular esos dos valores:

```bash
pip install playwright && playwright install chromium
python3 calibrar-impresion.py es-MX/factura.html
```

El script mide la altura real, calcula la escala para que quepa en una A4 con
8mm de margen y un 1% de holgura, y escribe los valores en el propio HTML.

---

## Preparación para el backend

Los valores que vendrán de base de datos están marcados con `data-field`:

```html
<strong data-field="folio">RES-87241</strong>
<b data-field="importe">$3,240.00</b>
```

Campos disponibles: `folio`, `fecha_emision`, `fecha_entrega`, `estado`,
`cliente_nombre`, `cliente_email`, `cliente_telefono`, `cliente_ciudad`,
`vigencia`, `autorizacion`, `vehiculo`, `vehiculo_ubicacion`, `vin`, `anio`,
`tipo`, `kilometraje`, `combustible`, `transmision`, `descuento`,
`precio_vehiculo`, `importe`, `moneda`, `banco`, `beneficiario`, `clabe`,
`cuenta`, `url_verificacion`, `agente_iniciales`, `agente_nombre`,
`agente_horario`, `agente_telefono`, `agente_email`.

Sustituir el contenido de esos nodos no toca el diseño.

### QR y código de barras

Ambos son SVG generados, no imágenes de mapa de bits: nítidos a cualquier
resolución y regenerables por folio desde el backend.

- `assets/img/reservation-qr.svg` → apunta a la URL de `data-field="url_verificacion"`
- `assets/img/reservation-barcode.svg` → Code 128-B del folio

Al cambiar el folio o la URL de verificación hay que regenerar los dos
archivos.

---

## Generar o regenerar una version de idioma

```bash
python3 traducir.py DulceAuto_textos_EN.txt en/invoice.html en
python3 calibrar-impresion.py en/invoice.html
```

`traducir.py` parte SIEMPRE de `es-MX/factura.html` y sustituye unicamente
textos: no toca el marcado, ni las clases, ni los `data-field`, ni el sprite.
Por esa via el VIEW aprobado no se puede romper. Al terminar avisa de cualquier
clave sin traducir y de cualquier clave del archivo que no se haya usado, asi
que no se puede colar un texto a medias.

Los ajustes propios de un idioma van en el bloque `<style>` de su HTML. Ahora
mismo solo hay uno: en ingles la columna del titulo pasa de 230px a 270px,
porque "Vehicle Reservation Proforma Invoice" no cabe en una linea a 230px.

### Cuidado al cambiar los textos de es-MX

Las claves de los archivos de `textos/` se derivan del propio texto de la
plantilla es-MX. Si se cambia la redaccion de es-MX, las claves de esa frase
cambian y los archivos de EN y es-AR dejan de encajar en esas lineas.

Al hacerlo hay que reetiquetar los otros dos archivos. La comprobacion de que
salio bien es que `traducir.py` siga diciendo 95 de 95 y que el HTML generado
no cambie respecto al anterior salvo en lo que se queria cambiar.

Para el backend del Milestone 2 conviene pasar a claves fijas por posicion en
lugar de derivadas del texto, y este problema desaparece.


## Notas de mantenimiento

- **El sprite de iconos va incrustado en cada HTML, no en un archivo aparte.**
  Un `<use href="sprite.svg#id">` externo no carga bajo `file://` en Chrome por
  CORS y rompería tanto la vista previa local como algunos generadores de PDF.
  Los iconos sueltos están en `assets/icons/` como fuente.
- **Sin dependencias externas.** El documento no hace ni una sola petición a
  internet: se abre igual sin conexión y el servidor genera exactamente lo
  mismo que el navegador.
- **Sin JavaScript.**

## Créditos

Fotografías del vehículo: ver `assets/img/ATTRIBUTION.txt` (Wikimedia Commons,
CC BY / CC BY-SA).
Tipografía Inter: Rasmus Andersson, SIL Open Font License 1.1.

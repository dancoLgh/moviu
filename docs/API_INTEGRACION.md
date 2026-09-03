# Integración de la API - Moviu Print Server

## Resumen rápido

- Servidor HTTPS local que expone una API REST para enviar trabajos de impresión.
- Autenticación mediante `X-API-Key` en cabecera.
- Endpoints principales: `POST /api/print`, `GET /api/health`, `GET /api/printers`, `GET /api/discover`.
- Soporta modos: `html`, `image`, `pdf`, `raw`, `raw_text`, `hybrid`, `zpl`.

## Requisitos

- La aplicación corre localmente (por defecto en `https://127.0.0.1:9000`).
- El servidor genera una CA local (`ca_cert.pem`) y firma con ella el certificado HTTPS del servidor; instala esa CA en tablets/clientes para confiar en la conexión.
- En entornos de desarrollo puedes usar `-k` en `curl` o `verify=False` en `requests` si aún no instalas la CA.
- La API Key se persiste en el archivo de configuración (`~/.moviu_printer/config.json`).

## Autenticación

- Todas las llamadas a la API, excepto `/api/discover`, deben incluir el header `X-API-Key: <API_KEY>`.
- El portal auxiliar `http://<host>:<puerto-api+1>/certificado` y su descarga de CA son públicos para permitir la instalación inicial. Nunca exponen claves privadas.
- Si la API key es inválida la API devuelve `401 Unauthorized`.

---

## Esquemas JSON

### PrinterSettings (objeto opcional en PrintRequest)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `host` | string | Host/IP de la impresora de red (para impresoras térmicas) |
| `port` | int | Puerto TCP de la impresora (default: 9100) |
| `name` | string | Nombre de impresora local (para modo `pdf` en impresoras del sistema) |

### PrintRequest (cuerpo para `POST /api/print`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `mode` | string | `html` \| `image` \| `pdf` \| `raw` \| `raw_text` \| `hybrid` \| `zpl`. Default: `html` |
| `content` | string u object | Payload del trabajo; `hybrid` acepta un objeto con `image` y `commands` |
| `printer` | PrinterSettings | Destino de impresión (opcional) |
| `code_page` | string | Para `raw_text`: cp437, cp850, cp858, cp1252, etc. |
| `dpi` | int | Para `pdf` con `printer.name`: resolución 72-600 (default: 150) |
| `paper_size` | string | Para `pdf` con `printer.name` y `raw_mode=false`: A4, Letter, Legal, etc. o código DMPAPER |
| `paper_width_mm` | float | Para `pdf` con `printer.name` y `raw_mode=false`: ancho personalizado en mm (requiere `paper_height_mm`) |
| `paper_height_mm` | float | Para `pdf` con `printer.name` y `raw_mode=false`: alto personalizado en mm (requiere `paper_width_mm`) |
| `raw_mode` | bool | Para `pdf` con `printer.name`: enviar PDF directo sin renderizar |
| `simulate` | bool | Forzar simulación (no enviar a impresora física) |
| `cut_margin_lines` | int | Líneas de avance antes del corte generado por Moviu, de 0 a 20 (opcional; usa la configuración global por defecto) |

`cut_margin_lines` solo se aplica a los cortes que Moviu genera al rasterizar `html`, `image` o un PDF enviado a una térmica ESC/POS. Los modos `raw`, `raw_text`, `hybrid` y `zpl` conservan íntegramente los comandos enviados por el cliente. El valor global se configura en **Impresoras > Papel y renderizado > Margen antes del corte**, se guarda como `cut_margin_lines` y por defecto es de 2 líneas; la distancia física de cada línea depende de la impresora.

### PrintResponse

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `status` | string | `sent` o `simulated` |
| `host` | string | Host de impresora (modos térmicos) |
| `port` | int | Puerto de impresora (modos térmicos) |
| `bytes` | int | Tamaño del payload |
| `printer` | string | Nombre de impresora local (modo `pdf`) |
| `pages` | int | Páginas impresas (modo `pdf` local) |
| `paper_size` | string | Tamaño de hoja aplicado (modo `pdf` renderizado) |
| `paper_width_mm` | float | Ancho personalizado aplicado en mm |
| `paper_height_mm` | float | Alto personalizado aplicado en mm |
| `message` | string | Mensaje descriptivo |
| `preview` | object | Datos de previsualización (si simulado) |

---

## Endpoints

### OPTIONS /api/print

CORS preflight o comprobación rápida.

**Respuesta:** `200 { "status": "ok" }`

### POST /api/print

Enviar un trabajo de impresión.

**Headers:** `X-API-Key`, `Content-Type: application/json`

**Respuestas:**
- `200` con `PrintResponse`
- `400` si el trabajo no es procesable
- `401` si API key inválida

### GET /api/health

Verificar estado del servidor.

**Headers:** `X-API-Key`

**Respuesta:** `200 { "status": "ok" }`

### GET /api/printers

Listar impresoras instaladas en el sistema.

**Headers:** `X-API-Key`

**Respuesta:**
```json
{
  "printers": ["HP LaserJet Pro", "POS-80C", "Microsoft Print to PDF"],
  "count": 3
}
```

### GET /api/discover

Descubrir servidores Moviu en la red local (mDNS). **No requiere autenticación.**

**Query params:** `timeout` (float, default: 3.0)

**Respuesta:**
```json
{
  "servers": [
    {
      "name": "Moviu Print Server._moviu-print._tcp.local.",
      "port": 9000,
      "addresses": ["192.168.1.156"],
      "properties": {"version": "1.4.0", "api_version": "1.0", "protocol": "https"}
    }
  ],
  "count": 1
}
```

---

## Modos de impresión

### `html` — Impresoras térmicas

HTML renderizado a imagen y convertido a ESC/POS.

```json
{
  "mode": "html",
  "content": "<h1>Ticket</h1><p>Gracias por su compra</p>",
  "printer": {"host": "192.168.1.50", "port": 9100}
}
```

### `image` — Impresoras térmicas

Imagen en base64 convertida a ESC/POS.

```json
{
  "mode": "image",
  "content": "data:image/png;base64,iVBORw0K..."
}
```

### `pdf` — Modo unificado para cualquier impresora

El modo `pdf` detecta automáticamente el destino y el tipo de envío:

**Impresora de red térmica (renderiza a ESC/POS):**
```json
{
  "mode": "pdf",
  "content": "JVBERi0xLjQN...",
  "printer": {"host": "192.168.1.50", "port": 9100}
}
```

**Impresora de red con soporte PDF nativo (envío directo):**
```json
{
  "mode": "pdf",
  "content": "JVBERi0xLjQN...",
  "printer": {"host": "192.168.1.100", "port": 9100},
  "raw_mode": true
}
```

**Impresora local del sistema (renderiza con Windows GDI):**
```json
{
  "mode": "pdf",
  "content": "JVBERi0xLjQN...",
  "printer": {"name": "HP LaserJet Pro"},
  "dpi": 300,
  "paper_size": "A4"
}
```

**Impresora local con tamaño personalizado (mm):**
```json
{
  "mode": "pdf",
  "content": "JVBERi0xLjQN...",
  "printer": {"name": "HP LaserJet Pro"},
  "dpi": 300,
  "paper_width_mm": 80,
  "paper_height_mm": 200
}
```

**Impresora local con PDF directo (envío sin renderizar):**
```json
{
  "mode": "pdf",
  "content": "JVBERi0xLjQN...",
  "printer": {"name": "Kyocera ECOSYS"},
  "raw_mode": true
}
```

| Destino | `raw_mode` | Comportamiento |
|---------|------------|----------------|
| `printer.name` | `false` | Renderiza con Windows GDI (compatible con todas) |
| `printer.name` | `true` | Envía PDF directo al spooler (requiere soporte PDF) |
| `printer.host/port` | `false` | Renderiza a ESC/POS (para térmicas) |
| `printer.host/port` | `true` | Envía PDF directo por TCP (para láser/inkjet con PDF nativo) |

| Opción | Descripción |
|--------|-------------|
| `dpi` | Resolución para renderizado: 72-600 (default: 150). Solo aplica cuando `raw_mode=false` |
| `paper_size` | Tamaño de hoja para renderizado local (`A4`, `A5`, `Letter`, `Legal`, `Tabloid`, `Executive`, `B5`, `carta`, `oficio` o código `DMPAPER`) |
| `paper_width_mm` | Ancho personalizado en mm para renderizado local |
| `paper_height_mm` | Alto personalizado en mm para renderizado local |

> Nota: usa `paper_size` o `paper_width_mm`+`paper_height_mm`, pero no ambos a la vez.

### `raw` — Bytes directos

Bytes ESC/POS en hexadecimal o base64.

```json
{
  "mode": "raw",
  "content": "1b401b6101486f6c610a1d5630"
}
```

### `raw_text` — Texto con escapes

Texto con secuencias de escape (`\n`, `\xHH`) codificado en la code page seleccionada.

```json
{
  "mode": "raw_text",
  "content": "\\x1b@Nombre: Juan\\nTotal: $10.00\\x0a\\x1dV\\x00",
  "code_page": "cp858"
}
```

**Code pages:** cp437, cp850, cp858, cp860, cp863, cp865, cp866, cp852, cp1252/latin-1

### `hybrid` — Imagen seguida de comandos ESC/POS

Combina una cabecera gráfica con comandos directos en un mismo trabajo, sin cortar el papel entre ambos bloques.

```json
{
  "mode": "hybrid",
  "content": {
    "image": "iVBORw0KGgoAAAANSUhEUg...",
    "commands": "G0BIZWxsbwoXVjA="
  },
  "printer": {"host": "192.168.1.50", "port": 9100}
}
```

`image` y `commands` aceptan Base64 o hexadecimal. `content` también puede enviarse como una cadena JSON serializada.

### `zpl` — Impresoras de etiquetas Zebra

Comandos ZPL enviados directamente.

```json
{
  "mode": "zpl",
  "content": "^XA^FO50,50^ADN,36,20^FDHello World^FS^XZ",
  "printer": {"host": "192.168.1.100", "port": 9100}
}
```

---

## Ejemplos prácticos

### cURL - HTML

```bash
curl -k -X POST "https://127.0.0.1:9000/api/print" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"mode":"html","content":"<p>Prueba</p>"}'
```

### cURL - PDF a impresora láser

```bash
curl -k -X POST "https://127.0.0.1:9000/api/print" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"mode":"pdf","content":"JVBERi0x...","printer":{"name":"HP LaserJet Pro"},"dpi":300,"paper_width_mm":80,"paper_height_mm":200}'
```

### Python - requests

```python
import requests
import base64

api_key = "YOUR_API_KEY"
url = "https://127.0.0.1:9000/api/print"

# HTML a térmica
payload = {"mode": "html", "content": "<b>Hola</b>"}
res = requests.post(url, headers={"X-API-Key": api_key}, json=payload, verify=False)
print(res.json())

# PDF a láser
with open("documento.pdf", "rb") as f:
    pdf_b64 = base64.b64encode(f.read()).decode()

payload = {
    "mode": "pdf",
    "content": pdf_b64,
    "printer": {"name": "HP LaserJet Pro"},
    "dpi": 300,
    "paper_width_mm": 80,
    "paper_height_mm": 200
}
res = requests.post(url, headers={"X-API-Key": api_key}, json=payload, verify=False)
print(res.json())
```

### JavaScript - fetch

```javascript
const apiKey = 'YOUR_API_KEY';
const url = 'https://192.168.1.100:9000/api/print';

// HTML a térmica
fetch(url, {
  method: 'POST',
  headers: {
    'X-API-Key': apiKey,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    mode: 'html',
    content: '<h1>Ticket</h1><p>Gracias!</p>'
  })
}).then(r => r.json()).then(console.log);

// PDF a láser
fetch(url, {
  method: 'POST',
  headers: {
    'X-API-Key': apiKey,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    mode: 'pdf',
    content: pdfBase64,
    printer: { name: 'HP LaserJet Pro' },
    dpi: 300,
    paper_width_mm: 80,
    paper_height_mm: 200
  })
}).then(r => r.json()).then(console.log);
```

---

## Simulación y previsualización

- Si `simulate: true` o la configuración tiene `simulate_printer = true`, no se envía a la impresora.
- La respuesta incluirá `preview` con rutas locales y datos en base64.
- Los trabajos simulados se guardan en `~/.moviu_printer/simulated_jobs/`.

---

## Puente TCP → USB

Recibe bytes crudos por TCP y los envía a una impresora USB local.

```python
import socket
payload = b"\x1b@Hola\n"  # ESC @ + Texto
with socket.create_connection(("127.0.0.1", 9100), timeout=5) as s:
    s.sendall(payload)
```

---

## Errores comunes

| Código | Causa |
|--------|-------|
| `400` | Contenido inválido (base64 mal formado, code page desconocida) |
| `401` | API Key ausente o incorrecta |
| `500` | Error interno (revisar logs en `~/.moviu_printer/app.log`) |

---

## Archivos relevantes

- API: `moviu_server/server.py`
- Procesamiento: `moviu_server/printer.py`
- Impresión sistema: `moviu_server/system_printer.py`
- mDNS: `moviu_server/mdns.py`
- Configuración: `moviu_server/config.py`
- Puente TCP→USB: `tcp_usb_bridge/printer_bridge.py`

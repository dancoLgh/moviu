# Integración de la API - Moviu Print Server

Resumen rápido
- Servidor HTTPS local que expone una API REST para enviar trabajos de impresión.
- Autenticación mediante `X-API-Key` en cabecera.
- Endpoints principales: `POST /api/print`, `GET /api/health`.
- Soporta modos: `html`, `image`, `raw`, `raw_text`.

Requisitos
- La aplicación corre localmente (por defecto en `https://127.0.0.1:9000`).
- Certificados auto-firmados se generan automáticamente; en entornos de desarrollo puedes usar `-k` en `curl` o `verify=False` en `requests`.
- La API Key se persiste en el archivo de configuración (ver [moviu_server/config.py](moviu_server/config.py#L1-L40)).

Autenticación
- Todas las llamadas deben incluir el header `X-API-Key: <API_KEY>`.
- Si la API key es inválida la API devuelve `401 Unauthorized`.

Esquemas JSON

PrintRequest (cuerpo para `POST /api/print`)
- `mode` (string): "html" | "image" | "raw" | "raw_text". Default: "html".
- `content` (string): payload del trabajo (HTML, base64 de imagen, hex/base64 para raw, o texto con escapes para raw_text).
- `printer` (opcional): objeto con `host` (string) y `port` (int) para sobrescribir destino.
- `code_page` (opcional): para `raw_text` (ej. `cp437`, `cp850`, `cp1252`, `cp858`).
- `simulate` (opcional, bool): forzar simulación (no enviar a impresora física).

PrintResponse
- `status` (string): `sent` (enviado) o `simulated` (simulado).
- `host` (string): host de impresora usado.
- `port` (int): puerto de impresora usado.
- `bytes` (int): tamaño en bytes del payload enviado.
- `preview` (opcional, object): datos de previsualización según modo (texto, hex, html, image base64, paths locales si simulado).

Endpoints
- OPTIONS /api/print
  - Uso: CORS preflight o comprobación rápida.
  - Respuesta: `200` JSON `{ "status": "ok" }`.

- POST /api/print
  - Descripción: enviar un trabajo de impresión.
  - Headers: `X-API-Key: <API_KEY>`, `Content-Type: application/json`.
  - Body: `PrintRequest`.
  - Respuestas:
    - `200` con `PrintResponse`.
    - `400` si el trabajo no es procesable (ej. imagen no base64 válida, code page desconocida).
    - `401` si API key inválida.

- GET /api/health
  - Requiere `X-API-Key`.
  - Respuesta: `200` `{ "status": "ok" }`.

Modos y formatos de `content`
- `html`: HTML (string). El servidor renderiza en imagen y lo convierte a ESC/POS.
  - Ejemplo: `{"mode":"html","content":"<h1>Hola</h1>"}`
- `image`: Base64 de imagen o `data:` URL (`data:image/png;base64,...`).
  - Ejemplo: `{"mode":"image","content":"data:image/png;base64,iVBORw0..."}`
- `raw`: Bytes ya formateados para la impresora, en hexadecimal o base64.
  - Hex: `0A1B2C...` (sin prefijo).
  - Base64: cadena base64 pura.
  - Ejemplo: `{"mode":"raw","content":"1b40"}`
- `raw_text`: Texto con escapes (`\n`, `\r`, `\xHH`) que se codifica en la code page seleccionada y puede prefijarse con el comando ESC que selecciona code page.
  - Ejemplo: `{"mode":"raw_text","content":"Hola\\nMundo\\x0A","code_page":"cp1252"}`

Ejemplos prácticos
- cURL (HTML):

```bash
curl -k -X POST "https://127.0.0.1:9000/api/print" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"mode":"html","content":"<p>Prueba</p>"}'
```
Nota: `-k` omite verificación TLS para certificados auto-firmados.

- Python `requests` (ignorar verificación en dev):

```python
import requests
api_key = "YOUR_API_KEY"
url = "https://127.0.0.1:9000/api/print"
payload = {"mode":"html","content":"<b>Hola</b>"}
res = requests.post(url, headers={"X-API-Key": api_key}, json=payload, verify=False)
print(res.status_code, res.json())
```

- Enviar imagen (data URL):
```json
{
  "mode": "image",
  "content": "data:image/png;base64,iVBORw0K..."
}
```

- Enviar raw (hex):
```json
{"mode":"raw","content":"1b40..."}
```

- Enviar raw_text con escapes:
```json
{
  "mode":"raw_text",
  "content":"Nombre: Juan\\nTotal: 10.00EUR\\x0A\\x1DVA",
  "code_page":"cp1252"
}
```

Previsualización y simulación
- Si `simulate` es `true` o la configuración del servidor tiene `simulate_printer = true`, la API no envía los bytes a la impresora.
- En modo simulado la respuesta incluirá `preview` con rutas locales (`payload_path`, `text`, `hex`, `html`) y la imagen en base64 si aplica.
- Los trabajos simulados se guardan en el directorio de configuración del usuario (ver `CONFIG_DIR` en [moviu_server/config.py](moviu_server/config.py#L1-L40)).

Errores comunes
- `400 Bad Request`: imagen no base64 válida, raw mal formado, code page desconocida.
- `401 Unauthorized`: cabecera `X-API-Key` ausente o incorrecta.
- `500` es raro; revisar logs localmente (archivo `app.log`, carpeta de certificados/registro).

Puente TCP → USB (TCP USB Bridge)
- Propósito: recibir bytes crudos por TCP y enviarlos a una impresora USB local (Windows) o guardarlos en disco en otros sistemas.
- El servicio escucha en `host:port` (por defecto la app usa la configuración `usb_bridge_port` y `usb_bridge_printer`).
- Protocolo: conexión TCP simple; servidor lee todos los bytes enviados por el cliente y, al cerrar la conexión, envía esos bytes a la impresora (o los guarda para sistemas no Windows).

Ejemplo (Python) — enviar bytes crudos al puente:
```python
import socket
payload = b"\x1b@Hola\n"  # ESC @ + Texto + newline
with socket.create_connection(("127.0.0.1", 9100), timeout=5) as s:
    s.sendall(payload)
```

Ejemplo con `nc` (Linux/macOS):
```bash
printf "\x1b@Hola\n" | nc 127.0.0.1 9100
```

Comportamiento en Windows
- Si `win32print` está disponible, el puente enviará bytes directamente a la impresora seleccionada (raw).
- En otros sistemas se guardará un archivo binario en `~/.tcp_usb_bridge/simulated_jobs/job.bin`.

Archivos relevantes
- Código API: [moviu_server/server.py](moviu_server/server.py#L1-L200)
- Procesamiento de trabajos: [moviu_server/printer.py](moviu_server/printer.py#L1-L240)
- Configuración y ubicación de `api_key`: [moviu_server/config.py](moviu_server/config.py#L1-L80)
- Puente TCP→USB: [tcp_usb_bridge/printer_bridge.py](tcp_usb_bridge/printer_bridge.py#L1-L260)

Sugerencias / próximos pasos
- Verificar la `api_key` en el archivo de configuración (`~/.moviu_printer/config.json`) o desde la UI de la aplicación.
- Para integración desde navegadores, usar el preflight `OPTIONS /api/print` y enviar `X-API-Key` en las cabeceras.
- Añadir ejemplos en el repositorio para cada modo (`examples/print_html.py`, `examples/print_raw.py`).

Archivo de documentación generado: `docs/API_INTEGRACION.md`.

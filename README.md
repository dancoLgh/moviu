# Moviu Print Server

Servidor de impresión local para convertir HTML → imagen → ESC/POS y exponer una API HTTP protegida con API key.

## Características

- Aplicación de escritorio (Tkinter) que inicia/detiene el servidor.
- API REST (`FastAPI`) accesible mediante `X-API-Key`.
- Convierte HTML plano o imágenes base64 en comandos ESC/POS listos para impresoras térmicas.
- Permite enviar comandos ESC/POS sin transformación (`mode="raw"` o `mode="raw_text"`).
- Enrutamiento a impresoras de red vía TCP configurable por petición.

## Requisitos

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

1. Ejecuta la aplicación de escritorio:
   ```bash
   python main.py
   ```
2. Configura host, puerto, datos de la impresora y guarda.
3. Inicia el servidor desde la propia interfaz. La API key se muestra en la ventana.

### Endpoint principal

`POST /api/print`

Cabecera obligatoria: `X-API-Key: <valor mostrado en la app>`

Ejemplo de payload para HTML:

```json
{
  "mode": "html",
  "content": "<h1>Ticket</h1><p>Gracias por tu compra</p>",
  "printer": {
    "host": "192.168.1.50",
    "port": 9100
  }
}
```

Ejemplo para enviar comandos ESC/POS ya preparados (hexadecimal):

```json
{
  "mode": "raw",
  "content": "1b4068656c6c6f0a1d5630"
}
```

También puedes enviar el binario en base64 (útil si generas bytes desde otra librería) usando la misma clave `content`.

Si prefieres enviar la cadena binaria tal cual (sin hex ni base64), usa el modo `raw_text`:

```json
{
  "mode": "raw_text",
  "content": "\\x1b@\\x1ba\\x01Hola\\x0a\\x1dV\\x00"
}
```

El modo `raw_text` interpreta las secuencias de escape (\n, \t, \x1b, etc.) y codifica el texto en la code page CP437 por defecto, insertando el comando `ESC t n` al inicio para forzar a la impresora a esa misma page. Si tu impresora usa otra code page (por ejemplo CP858 o CP1252), pásala en el campo opcional `code_page` y el servidor enviará el comando correspondiente antes del payload:

```json
{
  "mode": "raw_text",
  "code_page": "cp858",
  "content": "\\x1b@\\x1bt\\x09Hola Sebasti\\xA2n\\x0a\\x1dV\\x00"
}
```

Code pages soportadas para `raw_text`: `cp437` (ESC t 0), `cp850` (ESC t 2), `cp860` (ESC t 3), `cp863` (ESC t 4), `cp865` (ESC t 5), `cp1252`/`latin-1` (ESC t 6), `cp866` (ESC t 7), `cp852` (ESC t 8) y `cp858` (ESC t 9). Si pasas una no soportada, la API devuelve error de validación.

## Seguridad

- La API solo responde cuando la cabecera `X-API-Key` coincide con la clave almacenada localmente.
- Puedes regenerar la clave desde la interfaz; se guardará en `~/.moviu_printer/config.json`.

## Licencia

MIT

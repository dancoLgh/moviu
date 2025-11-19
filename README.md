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
  "content": "\u001b@\u001ba\u0001Hola\n\u001dV\u0000"
}
```

## Seguridad

- La API solo responde cuando la cabecera `X-API-Key` coincide con la clave almacenada localmente.
- Puedes regenerar la clave desde la interfaz; se guardará en `~/.moviu_printer/config.json`.

## Licencia

MIT

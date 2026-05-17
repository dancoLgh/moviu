# Moviu Print Server

Servidor de impresión local para convertir HTML → imagen → ESC/POS y exponer una API HTTP protegida con API key.

## Características

- Aplicación de escritorio (Tkinter) que inicia/detiene el servidor con visor de logs.
- API REST (`FastAPI`) accesible mediante `X-API-Key` y servido sobre HTTPS con certificado de servidor firmado por una CA local autogenerada.
- **Modos soportados:**
  - `html` / `image` — Impresoras térmicas (ESC/POS)
  - `pdf` — Modo unificado: impresoras térmicas (red) o del sistema (local)
  - `raw` / `raw_text` — Comandos ESC/POS directos
  - `hybrid` — Cabecera con imagen + comandos ESC/POS personalizados
  - `zpl` — Impresoras de etiquetas Zebra
- Enrutamiento a impresoras de red vía TCP o impresoras locales por nombre.
- Modo de simulación que guarda trabajos en disco para desarrollo.
- Puente TCP → USB para impresoras USB de Windows.
- Descubrimiento de servicios mDNS/DNS-SD (Bonjour/Avahi).

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
3. Opcional: genera/descarga el certificado CA desde los botones "Generar certificados" y "Exportar Certificado CA" para instalarlo en tablets o clientes que consumen la API por HTTPS.
4. Si quieres evitar envíos reales durante el desarrollo, activa "Simular impresora (solo desarrollo)" para que los trabajos se guarden en `~/.moviu_printer/simulated_jobs/` con una copia binaria (`.bin`) y, cuando aplique, una vista previa en texto (`.txt`/`.hex`) o imagen (`.png`). El log indica la ruta de cada trabajo simulado y el botón "Abrir simulaciones" abre la carpeta. La respuesta de la API también incluirá un bloque `preview` con texto/HTML/hex y la imagen en base64 cuando la simulación esté activa.
5. Inicia el servidor desde la propia interfaz. La API key se muestra en la ventana y el log en la parte inferior.

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

Para forzar la impresora virtual en un entorno de desarrollo sin cambiar la configuración global, añade `"simulate": true` al payload. La respuesta incluirá un bloque `preview` con copias en texto/hex/HTML y, si aplica, la imagen en base64.

También puedes enviar el binario en base64 (útil si generas bytes desde otra librería) usando la misma clave `content`.

Si prefieres enviar la cadena binaria tal cual (sin hex ni base64), usa el modo `raw_text`:

```json
{
  "mode": "raw_text",
  "content": "\\x1b@\\x1ba\\x01Hola\\x0a\\x1dV\\x00"
}
```

El modo `raw_text` interpreta las secuencias de escape (\n, \t, \x1b, etc.) sin romper los acentos y codifica el texto en la code page CP858 por defecto, insertando el comando `ESC t n` al inicio para forzar a la impresora a esa misma page. Si tu impresora usa otra code page (por ejemplo CP437 o CP1252), pásala en el campo opcional `code_page` y el servidor enviará el comando correspondiente antes del payload:

```json
{
  "mode": "raw_text",
  "code_page": "cp858",
  "content": "\\x1b@Hola Sebasti\\xA2n\\x0a\\x1dV\\x00"
}
```

Code pages soportadas para `raw_text`: `cp437` (ESC t 0), `cp850` (ESC t 2), `cp860` (ESC t 3), `cp863` (ESC t 4), `cp865` (ESC t 5), `cp1252`/`latin-1` (ESC t 6), `cp866` (ESC t 7), `cp852` (ESC t 8) y `cp858` (ESC t 9). Si pasas una no soportada, la API devuelve error de validación.

### Imprimir en modo híbrido (Imagen + RAW)

El modo `hybrid` permite enviar una imagen (cabecera) y comandos ESC/POS seguidos en un mismo trabajo, sin cortar el papel entre ellos. El `content` debe ser un objeto JSON con `image` y `commands` (ambos en base64 o hexadecimal):

```json
{
  "mode": "hybrid",
  "content": "{\"image\": \"data:image/png;base64,...\", \"commands\": \"1b4068656c6c6f0a1d5630\"}"
}
```

O enviando el JSON directamente como cadena:

```json
{
  "mode": "hybrid",
  "content": {
    "image": "iVBORw0KGgoAAAANSUhEUg...",
    "commands": "G0BIZWxsbwoXVjA="
  }
}
```

> Nota: Si el cliente envía un objeto JSON real en `content` en lugar de una cadena, el servidor lo procesará correctamente siempre que la API lo reciba como string deserializado.

### Imprimir PDFs (modo unificado)

El modo `pdf` detecta automáticamente el destino y el tipo de envío según los campos de `printer`:

**Impresora de red térmica (renderiza a ESC/POS):**
```json
{
  "mode": "pdf",
  "content": "JVBERi0xLjQN...",
  "printer": {"host": "192.168.1.50", "port": 9100}
}
```

**Impresora de red con soporte PDF (envío directo):**
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
| `printer.name` | `false` | Renderiza con Windows GDI |
| `printer.name` | `true` | Envía PDF directo al spooler |
| `printer.host/port` | `false` | Renderiza a ESC/POS (térmicas) |
| `printer.host/port` | `true` | Envía PDF directo por TCP |

`paper_size` es opcional y aplica cuando imprimes PDF con `printer.name` y `raw_mode: false`. Puedes enviar alias como `A4`, `A5`, `Letter`, `Legal`, `Tabloid`, `Executive`, `B5` (también `carta`/`oficio`) o un código numérico `DMPAPER` de Windows.

Si necesitas tamaño personalizado, usa `paper_width_mm` + `paper_height_mm` (ambos obligatorios juntos). No se puede combinar `paper_size` con `paper_width_mm`/`paper_height_mm` en la misma petición.

### Imprimir etiquetas ZPL (Zebra)

Usa el modo `zpl` para impresoras de etiquetas:

```json
{
  "mode": "zpl",
  "content": "^XA^FO50,50^ADN,36,20^FDHello World^FS^XZ",
  "printer": {"host": "192.168.1.100", "port": 9100}
}
```

### Listar impresoras disponibles

`GET /api/printers` devuelve las impresoras instaladas en el sistema:

```json
{"printers": ["HP LaserJet Pro", "POS-80C"], "count": 2}
```

### Vista previa para modo desarrollo

- Activa la casilla "Simular impresora" o envía `"simulate": true` en el cuerpo de la petición.
- La API responderá con `status="simulated"` y un objeto `preview` que incluye:
  - `text`, `hex` u `html` con el contenido recibido.
  - `image_base64` cuando el modo genera imagen (HTML o image).
  - `payload_path` con la ruta del `.bin` guardado y los puertos/host utilizados para la simulación.
- Todos los artefactos quedan en `~/.moviu_printer/simulated_jobs/` y se pueden abrir desde el botón "Abrir simulaciones" de la app.

## Generar instaladores

### Windows (ejecutable .exe)

1. Instala PyInstaller (solo para empaquetar):
   ```powershell
   pip install pyinstaller
   ```
2. Genera el ejecutable:
   ```powershell
   pyinstaller --noconfirm --noconsole --onefile --name MoviuPrintServer main.py
   ```
3. El binario queda en `dist/MoviuPrintServer.exe`. Copia todo el directorio `dist/` al equipo destino; al arrancar, la app crea `~/.moviu_printer/` con la configuración y certificados.
4. Al abrir la app podrás iniciar o detener el servidor desde la propia interfaz.

### Debian/Ubuntu (.deb)

1. Instala dependencias de build (solo una vez):
   ```bash
   sudo apt-get update && sudo apt-get install -y python3-venv python3-dev build-essential debhelper
   pip install pyinstaller
   ```
2. Crea el binario autónomo:
   ```bash
   pyinstaller --noconfirm --noconsole --onefile --name moviu-print-server main.py
   ```
3. Arma la estructura del paquete:
   ```bash
   mkdir -p dist/deb/DEBIAN dist/deb/usr/local/bin
   cp dist/moviu-print-server dist/deb/usr/local/bin/moviu-print-server
   cat > dist/deb/DEBIAN/control <<'EOF'
   Package: moviu-print-server
   Version: 1.0.0
   Section: utils
   Priority: optional
   Architecture: amd64
   Maintainer: moviu
   Description: Servidor local de impresión ESC/POS con API HTTPS y app Tkinter
   EOF
   ```
4. Genera el .deb:
   ```bash
   dpkg-deb --build dist/deb dist/moviu-print-server.deb
   ```
5. Instala en la máquina destino:
   ```bash
   sudo dpkg -i dist/moviu-print-server.deb
   ```
6. Al lanzar `/usr/local/bin/moviu-print-server` se abrirá la GUI y podrás iniciar/detener el servidor desde la aplicación.

## Seguridad

- La API solo responde cuando la cabecera `X-API-Key` coincide con la clave almacenada localmente.
- Puedes regenerar la clave desde la interfaz; se guardará en `~/.moviu_printer/config.json`.
- El servidor levanta HTTPS con `~/.moviu_printer/cert.pem` y `~/.moviu_printer/key.pem`, firmados por una CA local en `~/.moviu_printer/ca_cert.pem` (clave: `~/.moviu_printer/ca_key.pem`).
- Usa "Exportar Certificado CA" para instalar `ca_cert.pem` en tablets/PCs clientes y evitar avisos de certificado.

## Licencia

MIT

---

## Puente TCP → impresora USB

En la propia aplicación encontrarás el apartado **"Puente TCP → Impresora USB"** para activar o detener el listener. Selecciona la impresora USB instalada en Windows, el puerto TCP de escucha y marca **"Arrancar puente automáticamente"** si quieres que se levante al iniciar Moviu. En sistemas no Windows los trabajos se guardan como simulaciones en `~/.tcp_usb_bridge/` para poder probar el flujo sin hardware real.

---

## Descubrimiento de servicios (mDNS/DNS-SD)

El servidor Moviu se anuncia automáticamente en la red local usando mDNS/DNS-SD (compatible con Bonjour/Avahi). Esto permite que los clientes descubran servidores sin conocer la IP previamente.

### Endpoint de descubrimiento

`GET /api/discover` — **No requiere autenticación**

```bash
curl -X GET "https://localhost:8443/api/discover?timeout=3"
```

Respuesta:

```json
{
  "servers": [
    {
      "name": "Moviu Print Server._moviu-print._tcp.local.",
      "port": 9050,
      "addresses": ["192.168.1.156"],
      "properties": {
        "version": "1.0",
        "protocol": "https",
        "hostname": "DESKTOP-ABC123"
      }
    }
  ],
  "count": 1
}
```

### Utilidad de línea de comandos

Incluimos `discover.py` para buscar servidores desde la terminal:

```bash
# Búsqueda básica (3 segundos)
python discover.py

# Con timeout personalizado
python discover.py --timeout 5

# Salida JSON (para scripts)
python discover.py --json

# Modo detallado
python discover.py --verbose
```

### Compilar la utilidad discover.py

Para distribuir la utilidad como ejecutable independiente:

#### Windows

```powershell
pyinstaller --noconfirm --onefile --name MoviuDiscover discover.py
```

El ejecutable queda en `dist/MoviuDiscover.exe`.

#### Linux/macOS

```bash
pyinstaller --noconfirm --onefile --name moviu-discover discover.py
```

### Descubrimiento desde JavaScript (Browser/Node.js)

Dado que los navegadores no pueden hacer mDNS directamente, usa el endpoint HTTP del servidor:

```javascript
/**
 * Descubre servidores Moviu Print Server en la red local.
 * Requiere conocer al menos un servidor para hacer la consulta inicial.
 * 
 * @param {string} knownServerUrl - URL de un servidor conocido (ej: https://192.168.1.100:8443)
 * @param {number} timeout - Segundos de espera (default: 3)
 * @returns {Promise<Array>} Lista de servidores encontrados
 */
async function discoverMoviuServers(knownServerUrl, timeout = 3) {
  try {
    const response = await fetch(
      `${knownServerUrl}/api/discover?timeout=${timeout}`,
      {
        method: 'GET',
        // No requiere X-API-Key
      }
    );
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    return data.servers || [];
  } catch (error) {
    console.error('Error descubriendo servidores:', error);
    return [];
  }
}

// Ejemplo de uso
async function main() {
  // Si conoces al menos un servidor, puedes descubrir todos los demás
  const servers = await discoverMoviuServers('https://192.168.1.100:8443');
  
  console.log(`Encontrados ${servers.length} servidor(es):`);
  servers.forEach((server, i) => {
    const addr = server.addresses?.[0] || 'unknown';
    console.log(`  [${i + 1}] ${server.name}`);
    console.log(`      URL: https://${addr}:${server.port}`);
  });
}

main();
```

### Descubrimiento nativo con Node.js (usando multicast-dns)

Para hacer descubrimiento mDNS real desde Node.js sin depender de un servidor conocido:

```javascript
const mdns = require('multicast-dns')();

function discoverMoviuServersNative(timeout = 3000) {
  return new Promise((resolve) => {
    const servers = [];
    
    mdns.on('response', (response) => {
      // Buscar servicios _moviu-print._tcp.local
      const srvRecords = response.answers.filter(
        (a) => a.type === 'SRV' && a.name.includes('_moviu-print._tcp')
      );
      
      srvRecords.forEach((srv) => {
        const aRecords = response.additionals.filter(
          (a) => a.type === 'A' && a.name === srv.data.target
        );
        
        servers.push({
          name: srv.name,
          port: srv.data.port,
          host: srv.data.target,
          addresses: aRecords.map((a) => a.data),
        });
      });
    });
    
    // Enviar query mDNS
    mdns.query({
      questions: [{ name: '_moviu-print._tcp.local', type: 'PTR' }],
    });
    
    setTimeout(() => {
      mdns.destroy();
      resolve(servers);
    }, timeout);
  });
}

// Uso
discoverMoviuServersNative(3000).then((servers) => {
  console.log('Servidores encontrados:', servers);
});
```

**Dependencia npm:** `npm install multicast-dns`


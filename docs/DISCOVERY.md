# Descubrimiento de servidores Moviu

Cuando la API está configurada para recibir conexiones por LAN, Moviu se anuncia en la red local mediante mDNS/DNS-SD con el servicio `_moviu-print._tcp.local.`. Los clientes compatibles con Bonjour o Avahi pueden localizar el servidor sin conocer previamente su dirección IP.

## Modo local sin API key

Con **Conexión → Permitir impresión sin API key** activo, Moviu escucha únicamente en `127.0.0.1` y no publica anuncios mDNS. Por eso no aparece en `discover.py` ni en las búsquedas de otros dispositivos de la LAN. Desde el equipo donde está instalado, utiliza directamente `https://127.0.0.1:9000`; cambia el puerto si configuraste otro.

`GET /api/discover` sigue disponible desde ese equipo para buscar otros servidores que sí se anuncian en la LAN. El endpoint no publica ni habilita el acceso al propio servidor local.

Para volver a anunciar Moviu en la LAN, desactiva la opción sin clave, configura **Host API** como `0.0.0.0`, guarda e inicia el servidor si está detenido. Los clientes descubiertos deberán utilizar la API key. Consulta la [guía de configuración de acceso](INSTALLATION.md#volver-a-recibir-trabajos-desde-la-lan).

## Endpoint HTTP

`GET /api/discover` no requiere autenticacion.

```bash
curl -k "https://localhost:9000/api/discover?timeout=3"
```

Respuesta de ejemplo:

```json
{
  "servers": [
    {
      "name": "Moviu Print Server._moviu-print._tcp.local.",
      "port": 9000,
      "addresses": ["192.168.1.156"],
      "properties": {
        "version": "1.5.0",
        "protocol": "https",
        "hostname": "DESKTOP-ABC123"
      }
    }
  ],
  "count": 1
}
```

## Utilidad de linea de comandos

El archivo `discover.py` busca servidores desde la terminal:

```bash
python discover.py
python discover.py --timeout 5
python discover.py --json
python discover.py --verbose
```

Para distribuir la utilidad como ejecutable independiente:

```bash
pyinstaller --noconfirm --onefile --name moviu-discover discover.py
```

En Windows puedes usar `--name MoviuDiscover`; el resultado se genera dentro de `dist/`.

## JavaScript en navegador

Los navegadores no pueden consultar mDNS directamente. Si conoces al menos un servidor, utiliza su endpoint de descubrimiento:

```javascript
async function discoverMoviuServers(knownServerUrl, timeout = 3) {
  try {
    const response = await fetch(
      `${knownServerUrl}/api/discover?timeout=${timeout}`
    );
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    return data.servers || [];
  } catch (error) {
    console.error("No fue posible descubrir servidores Moviu", error);
    return [];
  }
}

const servers = await discoverMoviuServers("https://192.168.1.100:9000");
console.log(servers);
```

## Node.js con mDNS nativo

Instala `multicast-dns`:

```bash
npm install multicast-dns
```

Consulta el servicio de Moviu:

```javascript
const mdns = require("multicast-dns")();

function discoverMoviuServers(timeout = 3000) {
  return new Promise((resolve) => {
    const servers = [];

    mdns.on("response", (response) => {
      const records = [...response.answers, ...response.additionals];
      const serviceRecords = records.filter(
        (answer) => answer.type === "SRV" && answer.name.includes("_moviu-print._tcp")
      );

      for (const service of serviceRecords) {
        const addresses = response.additionals
          .filter((answer) => answer.type === "A" && answer.name === service.data.target)
          .map((answer) => answer.data);
        servers.push({
          name: service.name,
          port: service.data.port,
          host: service.data.target,
          addresses,
        });
      }
    });

    mdns.query({
      questions: [{ name: "_moviu-print._tcp.local", type: "PTR" }],
    });

    setTimeout(() => {
      mdns.destroy();
      resolve(servers);
    }, timeout);
  });
}

discoverMoviuServers().then(console.log);
```

# Descubrimiento de servidores Moviu

Moviu se anuncia en la red local mediante mDNS/DNS-SD con el servicio `_moviu-print._tcp.local.`. Los clientes compatibles con Bonjour o Avahi pueden localizar el servidor sin conocer previamente su direccion IP.

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
        "version": "1.1.0",
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

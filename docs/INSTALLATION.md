# Instalacion y distribucion

Esta guia cubre la instalacion de Moviu Print Server, la ejecucion desde codigo fuente y la generacion de binarios.

## Binarios publicados

Descarga la version mas reciente desde GitHub Releases:

- [Windows x86-64](https://github.com/dancoLgh/moviu/releases/latest/download/MoviuPrintServer-Windows-x86_64.exe)
- [Linux x86-64](https://github.com/dancoLgh/moviu/releases/latest/download/MoviuPrintServer-Linux-x86_64)
- [Historial de versiones](https://github.com/dancoLgh/moviu/releases)

## Actualizaciones automáticas

En una instalación portátil, abre **Configuración > Actualizaciones** y pulsa **Buscar e instalar actualización**. Moviu muestra el progreso mientras descarga el binario correspondiente al sistema, verifica su tamaño y SHA-256 y prueba que pueda cargar sus dependencias. Solo entonces cierra la aplicación, reemplaza el ejecutable y vuelve a abrirla.

> **Actualización desde v1.4.0 o v1.4.1:** descarga y reemplaza el ejecutable manualmente por `v1.4.2` o una versión posterior una sola vez. Esas versiones antiguas no pueden reiniciar correctamente el proceso de actualización automática. Desde `v1.4.2`, las siguientes actualizaciones sí pueden instalarse automáticamente.

La actualización automática requiere que Moviu se ejecute desde el binario empaquetado y que su carpeta permita escribir archivos. Si se ejecuta desde el código fuente, la arquitectura no es compatible o el ejecutable está en una carpeta protegida, la aplicación ofrece abrir la descarga manual.

No es obligatorio utilizar un instalador para el modo portátil. Para instalar en una carpeta protegida como `Program Files` sí es necesario un instalador o actualizador firmado que pueda solicitar permisos de administrador; también permite crear accesos directos y ofrecer un desinstalador.

### Windows

1. Descarga `MoviuPrintServer-Windows-x86_64.exe`.
2. Ejecuta la aplicacion. Windows puede solicitar confirmacion la primera vez porque el binario no esta firmado comercialmente.
3. Configura la impresora y elige el modo de acceso descrito en **Primer inicio**.
4. Instala el certificado CA en el equipo o los dispositivos que consumirán la API HTTPS y pulsa **Iniciar servidor**.

### Linux

1. Descarga `MoviuPrintServer-Linux-x86_64`.
2. Dale permiso de ejecucion:

   ```bash
   chmod +x MoviuPrintServer-Linux-x86_64
   ```

3. Inicia la aplicacion:

   ```bash
   ./MoviuPrintServer-Linux-x86_64
   ```

La interfaz requiere un entorno grafico. Algunas funciones de impresoras locales y del puente USB dependen de Windows; la impresion de red y el modo de simulacion pueden utilizarse en Linux.

## Ejecutar desde codigo fuente

Requiere Python 3.10 o posterior.

```bash
git clone https://github.com/dancoLgh/moviu.git
cd moviu
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

En PowerShell, activa el entorno con:

```powershell
.venv\Scripts\Activate.ps1
python main.py
```

La configuracion, certificados y simulaciones se guardan en `~/.moviu_printer/`.

## Primer inicio

1. Configura el host y puerto de la impresora de red o selecciona una impresora local.
2. Conserva el puerto API predeterminado `9000` o elige otro disponible.
3. Elige el modo de acceso en **Conexión** según la tabla siguiente.
4. Genera los certificados desde la interfaz e instala la CA local en los equipos cliente.
5. Activa **Simular impresora** para validar la integración sin enviar papel.
6. Inicia el servidor y utiliza la URL HTTPS mostrada. Copia la API key si el modo elegido la requiere.

| Modo de acceso | Configuración en Conexión | Dirección para el cliente | API key |
|---|---|---|---|
| Desde el mismo equipo, sin clave | Activa **Permitir impresión sin API key** | `https://127.0.0.1:9000` | Se omite |
| Desde el mismo equipo, con clave | Desactiva la opción y configura **Host API** como `127.0.0.1` | `https://127.0.0.1:9000` | Obligatoria |
| Desde otros dispositivos de la LAN | Desactiva la opción y configura **Host API** como `0.0.0.0` | `https://<IP-del-equipo-Moviu>:9000` | Obligatoria |

Los ejemplos usan el puerto predeterminado; reemplaza `9000` si configuraste otro. `0.0.0.0` es la dirección de escucha del servidor: los clientes de la LAN utilizan la IP real del equipo.

### Imprimir sin API key desde este equipo

Disponible desde **v1.5.0**.

1. En **Conexión**, activa **Permitir impresión sin API key**. El cambio se guarda inmediatamente y reinicia los servicios activos.
2. Moviu fija **Host API** en `127.0.0.1` y deshabilita **Habilitar acceso en la red local**. La API, el portal de certificados y el puente USB solo aceptan conexiones locales, y el servidor deja de anunciarse por mDNS.
3. Abre `http://127.0.0.1:9001/certificado` desde ese equipo e instala la CA siguiendo las instrucciones. HTTPS sigue siendo necesario aunque no se use clave.
4. Envía los trabajos a `https://127.0.0.1:9000/api/print` sin el header `X-API-Key`.

El programa o navegador que envía el trabajo debe ejecutarse en el equipo de Moviu. Una página web alojada en otro servidor puede imprimir si el navegador que la abre está en ese equipo. Una tablet o una PC distinta no puede enviarle trabajos en este modo. La impresora de destino puede seguir siendo USB o de red.

### Usar el puente USB sin API key

El modo sin clave permite utilizar el puente USB integrado. Para una impresora USB en Windows:

1. Abre **Puente USB**, activa **Habilitar puente** y selecciona la impresora instalada.
2. Conserva el puerto `9100` o elige otro disponible, guarda la configuración y pulsa **Iniciar**.
3. Con **Permitir impresión sin API key** activo, el puente escucha en `127.0.0.1:<puerto-del-puente>` y solo recibe comandos del mismo equipo.
4. Envía trabajos a la API HTTPS sin `X-API-Key`. Si deseas dirigirlos explícitamente al puerto del puente, utiliza `"printer": {"host": "127.0.0.1", "port": 9100}` en el JSON, cambiando el puerto si corresponde.

También puedes enviar bytes directamente al puerto TCP del puente desde un programa local; ese protocolo no utiliza API key. La API sigue en el puerto `9000` y el puente en `9100`: son servicios distintos.

```powershell
$payload = @{
    mode = "raw_text"
    content = "Prueba por puente USB`n"
    printer = @{ host = "127.0.0.1"; port = 9100 }
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://127.0.0.1:9000/api/print" `
    -Method Post -ContentType "application/json" -Body $payload
```

### Comprobar la conexión sin imprimir

Para probar desde una terminal, con **Simular impresora** activado:

```bash
curl --cacert "$HOME/.moviu_printer/ca_cert.pem" \
  -X POST "https://127.0.0.1:9000/api/print" \
  -H "Content-Type: application/json" \
  -d '{"mode":"raw_text","content":"Prueba local sin clave","simulate":true}'
```

Consulta también los [ejemplos de integración sin API key](API_INTEGRACION.md#ejemplos-sin-api-key).

### Volver a recibir trabajos desde la LAN

1. Desactiva **Permitir impresión sin API key**. Moviu vuelve a exigir la misma clave que tenía antes.
2. Cambia **Host API** de `127.0.0.1` a `0.0.0.0` y guarda la configuración. Desactivar la opción conserva el host local hasta que lo cambies.
3. Pulsa **Habilitar acceso en la red local** para configurar el firewall si hace falta.
4. Instala la CA en cada dispositivo cliente desde `http://<IP-del-equipo-Moviu>:9001/certificado` y utiliza la URL HTTPS con `X-API-Key`.

## Generar ejecutables

El archivo `MoviuPrintServer.spec` incluye los recursos visuales de la aplicacion.

```bash
pip install pyinstaller
pyinstaller --noconfirm MoviuPrintServer.spec
```

PyInstaller genera un ejecutable para el sistema operativo donde se realiza la compilacion:

- Windows: `dist/MoviuPrintServer.exe`
- Linux: `dist/MoviuPrintServer`

No es posible generar de forma nativa el ejecutable de Windows desde Linux ni el de Linux desde Windows. Al subir una etiqueta `v*`, el workflow `release-binaries.yml` ejecuta las pruebas, compila ambos sistemas y crea automaticamente la release con sus binarios. La etiqueta debe coincidir con `VERSION` en `moviu_server/config.py`.

## Paquete Debian/Ubuntu

Despues de compilar el binario en Linux:

```bash
mkdir -p dist/deb/DEBIAN dist/deb/usr/local/bin
cp dist/MoviuPrintServer dist/deb/usr/local/bin/moviu-print-server
cat > dist/deb/DEBIAN/control <<'EOF'
Package: moviu-print-server
Version: 1.5.0
Section: utils
Priority: optional
Architecture: amd64
Maintainer: moviu
Description: Servidor local de impresion con API HTTPS
EOF
dpkg-deb --build dist/deb dist/moviu-print-server.deb
sudo dpkg -i dist/moviu-print-server.deb
```

## Seguridad local

- Por defecto, la API exige `X-API-Key`, excepto el endpoint público de descubrimiento.
- Con **Permitir impresión sin API key** activo, la API acepta trabajos únicamente desde el mismo equipo por loopback. El portal HTTP y el puente USB también quedan limitados al equipo local.
- El portal HTTP de instalacion y la descarga de la CA son publicos; solo entregan el certificado publico y nunca la clave privada.
- La clave se guarda en `~/.moviu_printer/config.json` y puede regenerarse desde la interfaz.
- Moviu crea una CA local y certificados HTTPS en `~/.moviu_printer/`.
- Instala el certificado CA exportado solo en dispositivos de confianza de tu red.
- No expongas el servidor directamente a Internet.

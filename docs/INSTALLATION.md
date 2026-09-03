# Instalacion y distribucion

Esta guia cubre la instalacion de Moviu Print Server, la ejecucion desde codigo fuente y la generacion de binarios.

## Binarios publicados

Descarga la version mas reciente desde GitHub Releases:

- [Windows x86-64](https://github.com/dancoLgh/moviu/releases/latest/download/MoviuPrintServer-Windows-x86_64.exe)
- [Linux x86-64](https://github.com/dancoLgh/moviu/releases/latest/download/MoviuPrintServer-Linux-x86_64)
- [Historial de versiones](https://github.com/dancoLgh/moviu/releases)

## Actualizaciones automáticas

En una instalación portátil, abre **Configuración > Actualizaciones** y pulsa **Buscar e instalar actualización**. Moviu descarga el binario correspondiente al sistema, verifica su tamaño y SHA-256, cierra la aplicación, reemplaza el ejecutable y vuelve a abrirla.

> **Actualización a v1.4.2:** si tienes `v1.4.0` o `v1.4.1`, descarga y reemplaza el ejecutable manualmente una sola vez. Esas versiones no pueden reiniciar correctamente el proceso de actualización automática. Desde `v1.4.2`, las siguientes actualizaciones sí pueden instalarse automáticamente.

La actualización automática requiere que Moviu se ejecute desde el binario empaquetado y que su carpeta permita escribir archivos. Si se ejecuta desde el código fuente, la arquitectura no es compatible o el ejecutable está en una carpeta protegida, la aplicación ofrece abrir la descarga manual.

No es obligatorio utilizar un instalador para el modo portátil. Para instalar en una carpeta protegida como `Program Files` sí es necesario un instalador o actualizador firmado que pueda solicitar permisos de administrador; también permite crear accesos directos y ofrecer un desinstalador.

### Windows

1. Descarga `MoviuPrintServer-Windows-x86_64.exe`.
2. Ejecuta la aplicacion. Windows puede solicitar confirmacion la primera vez porque el binario no esta firmado comercialmente.
3. Configura la impresora y pulsa **Iniciar servidor**.
4. Exporta e instala el certificado CA en los equipos que consumiran la API HTTPS.

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
3. Genera los certificados desde la interfaz.
4. Exporta la CA local e instalala en los dispositivos cliente.
5. Activa **Simular impresora** para validar la integracion sin enviar papel.
6. Inicia el servidor y copia la API key mostrada por la aplicacion.

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
Version: 1.4.2
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

- La API exige `X-API-Key`, excepto el endpoint publico de descubrimiento.
- El portal HTTP de instalacion y la descarga de la CA son publicos; solo entregan el certificado publico y nunca la clave privada.
- La clave se guarda en `~/.moviu_printer/config.json` y puede regenerarse desde la interfaz.
- Moviu crea una CA local y certificados HTTPS en `~/.moviu_printer/`.
- Instala el certificado CA exportado solo en dispositivos de confianza de tu red.
- No expongas el servidor directamente a Internet.

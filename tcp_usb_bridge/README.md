# TCP → USB Printer Bridge

Pequeña utilidad de escritorio para Windows que escucha peticiones TCP en un puerto configurable y reenvía los bytes recibidos a una impresora USB instalada en el sistema operativo. Incluye una interfaz Tkinter para seleccionar la impresora, el puerto TCP y activar el arranque automático.

> Nota: el envío real a la impresora requiere Windows con `pywin32`. En otros sistemas operativos la aplicación guarda los trabajos en `~/.tcp_usb_bridge/simulated_jobs/job.bin` para facilitar el desarrollo.

## Puente integrado en Moviu

Moviu incluye este puente en su panel **Puente USB**. Sigue disponible al activar **Conexión → Permitir impresión sin API key**: habilita el puente, selecciona la impresora USB y pulsa **Iniciar**. El puente integrado queda limitado a `127.0.0.1`, por lo que únicamente los programas del equipo de Moviu pueden enviar bytes a su puerto. Un puente activo se reinicia al cambiar ese modo.

El protocolo TCP crudo no utiliza `X-API-Key`; la restricción se aplica a la dirección donde escucha. Esta opción pertenece a Moviu y no cambia la configuración de la utilidad independiente iniciada con `python -m tcp_usb_bridge`, descrita a continuación. Consulta la [guía de acceso local de Moviu](../docs/INSTALLATION.md#imprimir-sin-api-key-desde-este-equipo).

## Estructura

- `tcp_usb_bridge/printer_bridge.py`: servidor TCP y funciones de envío a impresora.
- `tcp_usb_bridge/gui.py`: interfaz Tkinter con selección de impresora y controles de inicio/detención.
- `tcp_usb_bridge/config.py`: carga y guardado de configuración en `~/.tcp_usb_bridge/config.json`.
- `tcp_usb_bridge/__main__.py`: punto de entrada (`python -m tcp_usb_bridge`).

## Entorno de desarrollo (Windows)

1. Instala Python 3.11+ desde [python.org](https://www.python.org/downloads/windows/).
2. Crea y activa un entorno virtual:
   ```powershell
   python -m venv .venv
   .venv\\Scripts\\activate
   ```
3. Instala dependencias:
   ```powershell
   pip install -r tcp_usb_bridge/requirements.txt
   ```

## Ejecución en modo desarrollo

```powershell
python -m tcp_usb_bridge
```

Pasos en la interfaz:
1. Pulsa **Actualizar** para cargar la lista de impresoras instaladas y selecciona la deseada.
2. Indica el puerto TCP donde el programa escuchará (ej. `9100`).
3. Marca **Iniciar servidor automáticamente** si quieres que arranque solo con la configuración guardada.
4. Pulsa **Iniciar**. Cualquier cliente TCP que envíe bytes a `IP_DEL_PC:PUERTO` será reenviado a la impresora USB.

Los logs y el estado se muestran en la parte inferior. La configuración se guarda automáticamente.

## Empaquetar a .exe (PyInstaller)

1. Instala PyInstaller en el mismo entorno virtual:
   ```powershell
   pip install pyinstaller
   ```
2. Genera el ejecutable de un solo archivo sin consola:
   ```powershell
   pyinstaller --noconfirm --noconsole --onefile --name TcpUsbBridge tcp_usb_bridge/__main__.py
   ```
3. El binario quedará en `dist/TcpUsbBridge.exe`. Copia ese archivo a la máquina donde se usará la utilidad.

## Ejecutar en segundo plano y al iniciar Windows

1. Asegúrate de que en la interfaz la casilla **Iniciar servidor automáticamente** esté marcada para que el servicio empiece sin interacción.
2. Crea una tarea programada que ejecute el .exe al iniciar sesión:
   - Abre **Programador de tareas → Crear tarea básica**.
   - Desencadenador: **Al iniciar sesión**.
   - Acción: **Iniciar un programa** apuntando a `C:\ruta\TcpUsbBridge.exe`.
   - Opcional: marca **Ejecutar con los privilegios más altos** si necesitas acceder a dispositivos USB restringidos.
   - Para minimizar la ventana, usa el comando: `cmd /c start "" /min "C:\ruta\TcpUsbBridge.exe"`.
3. Alternativamente, coloca un acceso directo al .exe en la carpeta **shell:startup** de Windows para que se ejecute al inicio de sesión.

Con estos pasos el puente TCP→USB quedará activo en segundo plano cada vez que arranque el equipo.

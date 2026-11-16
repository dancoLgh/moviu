# Imprimir desde otro equipo de la misma red con Moviu

[Descargar la guía ilustrada en PDF](Moviu_Impresion_en_Red_Local.pdf)

Moviu recibe los trabajos en el equipo conectado a la impresora. Desde otra PC de la misma red, una aplicación compatible envía la impresión a su API HTTPS con una API key. La PC cliente necesita confiar en el certificado de Moviu; para este flujo no necesita instalar Moviu ni el controlador de la impresora.

La guía PDF incluye capturas reales de la interfaz de Moviu 1.6.0 y del portal de certificados, con recuadros y números sobre los lugares donde hacer clic. Las capturas se realizaron en Linux con datos de ejemplo; el puente USB se utiliza en Windows.

## Equipos y direcciones del ejemplo

| Elemento | Función | Dirección de ejemplo |
|---|---|---|
| Equipo A | Ejecuta Moviu y tiene acceso a la impresora | `192.168.1.20` |
| Equipo B | Ejecuta la aplicación o el navegador que envía el trabajo | `192.168.1.30` |
| Impresora de red | Destino TCP, cuando no se usa una impresora USB | `192.168.1.50:9100` |
| API de Moviu | Recibe las solicitudes de impresión | `https://192.168.1.20:9000` |
| Portal de certificados | Permite descargar e instalar la CA | `http://192.168.1.20:9001/certificado` |

Sustituye las direcciones por las de tu instalación. Los equipos pueden usar cable o Wi-Fi, siempre que la red permita la comunicación entre ellos. Una red de invitados o el aislamiento de clientes puede impedirla aunque se use el mismo router.

`0.0.0.0` permite que Moviu escuche en las interfaces del equipo A. En el equipo B se utiliza la IP real de A. Si B usa `localhost` o `127.0.0.1` como URL de Moviu, intentará conectarse a sí mismo.

## Configurar el acceso en el equipo A

1. Instala y abre Moviu siguiendo la [guía de instalación](INSTALLATION.md).
2. Abre **Conexión**.
3. Deja desmarcada **Permitir impresión sin API key** para seguir esta guía con autenticación. Desde v1.7.0 puedes activarla también para la LAN; Moviu advierte que se recomienda solo en redes privadas, controladas y seguras. En ese caso omite `X-API-Key` en las solicitudes.
4. Configura **Host API** como `0.0.0.0` y **Puerto API** como `9000`.
5. Pulsa **Guardar cambios**. Si el servidor estaba activo, Moviu lo reinicia para aplicar la configuración.

Consulta la IP de A en **URL HTTPS**. En Windows también puedes ejecutar `ipconfig` y buscar la dirección IPv4 del adaptador conectado a la red. Si hay varias interfaces, elige la IP accesible desde B. Conviene reservar esa dirección en el DHCP del router para que no cambie.

## Configurar la impresora en el equipo A

### Impresora térmica de red

1. Abre **Impresoras**.
2. En **Host o dirección IP**, escribe la IP de la impresora, por ejemplo `192.168.1.50`.
3. En **Puerto**, escribe el puerto RAW de la impresora, normalmente `9100`.
4. Ajusta el ancho de papel y pulsa **Guardar cambios**.

La aplicación de B se conecta a `192.168.1.20:9000`; Moviu se conecta a `192.168.1.50:9100`. Son destinos distintos. Si envías `printer.host` en una solicitud, ese valor selecciona la impresora de destino y reemplaza el destino predeterminado de Moviu.

### Impresora térmica USB en Windows

1. Instala la impresora y comprueba que funcione desde Windows en A.
2. En **Impresoras**, configura **Host o dirección IP** como `127.0.0.1` y **Puerto** como `9100`.
3. Pulsa **Mostrar panel** si el panel **Configuración avanzada** está oculto.
4. En **Puente USB**, activa **Habilitar puente TCP a USB** y selecciona la impresora instalada en **Impresora USB**. Usa **Actualizar** si hace falta volver a consultar la lista.
5. Configura **Puerto TCP** como `9100`, pulsa **Guardar configuración del puente** y luego **Iniciar**. **Arrancar automáticamente** permite iniciarlo con Moviu.

El `127.0.0.1` de este destino se interpreta en A, donde Moviu accede al puente. B sigue utilizando la IP de A para conectarse a la API HTTPS. Las térmicas deben aceptar los comandos del modo elegido, por ejemplo ESC/POS para los tickets de esta guía. Para una impresora de oficina, consulta el [modo PDF y las impresoras del sistema](API_INTEGRACION.md).

## Preparar HTTPS y habilitar el firewall en A

1. Con A conectado a la red definitiva, abre **Conexión** y pulsa **Generar certificados SSL**. Si Moviu solicita detener y reiniciar el servidor, acepta para aplicar el certificado.
2. Pulsa **Habilitar acceso en la red local** y acepta la solicitud de permisos de administrador del sistema.
3. Vuelve a **Inicio**, pulsa **Iniciar servidor** si está detenido y espera el estado **Servidor activo**.
4. En **Conexión**, copia la **URL HTTPS**, la URL del **Portal de certificado (HTTP)** y la clave mediante **Copiar API key**. Utiliza la clave real de esa instalación; la del PDF es un ejemplo.
5. Pulsa **Abrir portal de instalación** y conserva la huella SHA-256 que Moviu muestra para compararla desde B.

| Puerto TCP predeterminado | Uso |
|---|---|
| `9000` | API HTTPS de impresión |
| `9001` | Portal HTTP y descarga del certificado público |
| `9100` | Puente USB, cuando está habilitado |

El puerto del portal siempre es **Puerto API + 1**. El botón configura reglas para la red local en Windows y, en Linux, mediante UFW o firewalld. Si el puente está habilitado, también incluye su puerto. El puerto de una impresora remota no requiere una regla entrante en A porque Moviu realiza una conexión saliente hacia ella.

El puente TCP recibe bytes crudos y no utiliza API key. Los ejemplos de B emplean la API HTTPS con clave. Mantén el servicio en una red de confianza y no reenvíes estos puertos desde el router a Internet.

## Instalar el certificado en el equipo B

1. Abre en el navegador de B `http://192.168.1.20:9001/certificado`, sustituyendo la IP y el puerto si corresponde.
2. Compara la huella SHA-256 del portal con la que muestra Moviu en A.
3. Pulsa **Descargar certificado CA** y guarda `moviu-ca.crt`.
4. En Windows, abre el archivo y pulsa **Instalar certificado**. Elige **Usuario actual**, o **Equipo local** si necesitas instalarlo para otros usuarios y dispones de permisos de administrador.
5. Selecciona **Colocar todos los certificados en el siguiente almacén** y luego **Entidades de certificación raíz de confianza**. Finaliza el asistente y acepta la instalación de la CA verificada.
6. Reinicia el navegador o la aplicación que enviará las impresiones.

El portal también incluye instrucciones para Linux y Android. En Debian o Ubuntu, copia el certificado al almacén y actualízalo:

```bash
sudo cp /ruta/a/moviu-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

El botón **Instalar certificado en Windows** de Moviu instala la CA en A. Para que B confíe en HTTPS, la CA debe instalarse también en B. Algunos navegadores o programas mantienen un almacén propio; importa allí la misma CA si aún no confían en ella.

## Configurar la aplicación y comprobar la conexión desde B

En la aplicación compatible con Moviu configura la URL base `https://192.168.1.20:9000` y la API key copiada de A. Si solicita la URL completa para imprimir, utiliza `https://192.168.1.20:9000/api/print`. Los nombres de estos campos dependen de la aplicación.

La página web puede estar alojada en otro servidor: el navegador o proceso que envía la solicitud debe poder alcanzar A. Esta conexión utiliza la API de Moviu; no registra automáticamente una impresora en el diálogo de impresión de Windows.

Desde PowerShell en B, prueba primero la conexión y la autenticación, sin imprimir:

```powershell
$baseUrl = "https://192.168.1.20:9000"
$apiKey = Read-Host "Pega la API key de Moviu"
$headers = @{ "X-API-Key" = $apiKey }

Invoke-RestMethod -Uri "$baseUrl/api/health" -Headers $headers
```

La respuesta esperada es `status: ok`. Si prefieres cURL, indica la ruta del certificado descargado en B:

```bash
curl --cacert ./moviu-ca.crt \
  -H "X-API-Key: CLAVE_REAL_DE_MOVIU" \
  "https://192.168.1.20:9000/api/health"
```

## Probar una impresión desde B

Mantén las variables de la prueba anterior y envía primero un trabajo simulado:

```powershell
$payload = @{
    mode = "raw_text"
    content = "Prueba desde el equipo B`n`n`n"
    simulate = $true
}

Invoke-RestMethod -Uri "$baseUrl/api/print" -Method Post `
    -Headers $headers -ContentType "application/json" `
    -Body ($payload | ConvertTo-Json)
```

La respuesta debe indicar `status: simulated`. En A, abre **Actividad** y **Abrir simulaciones** para revisar el trabajo. Esto comprueba la recepción y el procesamiento sin gastar papel.

Para imprimir el ticket en una térmica compatible con ESC/POS, desactiva **Simular impresora y guardar trabajos localmente** en A y guarda los cambios. Luego ejecuta desde B:

```powershell
$payload.simulate = $false

Invoke-RestMethod -Uri "$baseUrl/api/print" -Method Post `
    -Headers $headers -ContentType "application/json" `
    -Body ($payload | ConvertTo-Json)
```

`status: sent` indica que Moviu envió el trabajo al destino configurado. Confirma también que salga el papel. Para PDF, etiquetas ZPL u otros formatos, usa el [payload del modo correspondiente](API_INTEGRACION.md#modos-de-impresión).

## Resolver problemas

| Síntoma | Qué comprobar |
|---|---|
| El portal no abre desde B | Moviu iniciado, IP de A correcta, puerto `9001`, **Host API** en `0.0.0.0`, alcance **Red local** y firewall habilitado. Revisa también redes de invitados, aislamiento Wi-Fi o VPN. |
| El portal abre, pero la API no responde | La API usa `https://` y el puerto `9000`; el portal usa `http://` y el puerto `9001`. Comprueba el firewall de ambos puertos. |
| Aviso de certificado | Instala la CA de A en B, comprueba la fecha y hora, reinicia el navegador y usa la IP con la que se generó el certificado. Si cambió la IP de A, regenera el certificado de servidor desde Moviu y actualiza la URL. |
| `401 Unauthorized` | Falta `X-API-Key` o la clave es incorrecta. Si se regeneró, actualízala en B. |
| `403` o acceso limitado a A | Selecciona **Red local** o configura `0.0.0.0`, guarda e inicia el servidor. Normalmente el modo local impide la conexión antes de obtener una respuesta HTTP. |
| `status: simulated` y no sale papel | Quita la simulación en la solicitud y revisa la opción de simulación en A. |
| `400` o no sale papel tras el envío | Revisa el mensaje de error, la IP y el puerto de la impresora, su alimentación, papel y compatibilidad con el formato. Para USB, verifica la impresora seleccionada y el puente. |
| La terminal funciona pero la aplicación falla | Revisa en la aplicación la URL, la clave y los errores o permisos de su navegador. La confianza en el certificado debe existir en el programa que realiza la solicitud. |

En PowerShell puedes comprobar los puertos desde B con `Test-NetConnection 192.168.1.20 -Port 9000` y repetir con `-Port 9001`. Un resultado positivo comprueba el acceso TCP; la prueba `/api/health` verifica además HTTPS y la clave.

En A consulta **Actividad** o el archivo `~/.moviu_printer/app.log` (`%USERPROFILE%\.moviu_printer\app.log` en Windows). Si la IP cambió y se conserva la misma CA, regenerar el certificado de servidor no exige reinstalar la CA en B; si se reemplazó la CA, vuelve a instalar la nueva.

# Portal de certificado y acceso a la red local

## Objetivo

Permitir que cualquier dispositivo de la LAN descargue de forma sencilla el certificado CA público de Moviu y consulte instrucciones de instalación para Windows, Android y Linux. La clave privada no se expone por ningún endpoint.

## Diseño

FastAPI publica una página sin API key en `/certificado` y la descarga en `/certificado/descargar`. Un listener HTTP aislado usa automáticamente el puerto siguiente al de la API HTTPS; si la API usa 9000, el portal usa 9001. Ese listener no publica rutas de impresión, documentación ni OpenAPI. La página es autocontenida, adaptable a móviles, muestra la huella SHA-256 del certificado y evita caché, carga de recursos externos y uso dentro de frames.

La aplicación de escritorio incorpora acciones para abrir el portal y habilitar el acceso desde la LAN. La segunda acción valida los puertos, solicita confirmación y eleva privilegios mediante UAC en Windows o polkit en Linux. Solo abre el puerto HTTPS, el puerto HTTP del certificado y el puerto del puente USB cuando está habilitado; nunca abre el puerto de una impresora remota.

Las reglas de Windows usan `LocalSubnet`. En Linux se detectan las redes IPv4 conectadas y se crean reglas de origen limitado mediante UFW o firewalld. No se ejecutan comandos recibidos desde la web ni texto libre introducido por el usuario.

## Pruebas

Las pruebas verifican acceso público, descarga exclusiva de la CA, huella visible, cabeceras defensivas, validación de puertos, elevación en Windows y alcance de subred en UFW. La interfaz Tk requiere una comprobación manual en Windows y Linux porque el entorno automatizado no dispone de un servidor gráfico.

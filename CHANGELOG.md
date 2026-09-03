# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

## [1.4.3] - 2026-09-03

### Añadido
- Pantalla de progreso para mostrar la descarga, verificación SHA-256, prueba de arranque y preparación de la instalación.
- Prueba segura del ejecutable descargado antes de cerrar o reemplazar la versión instalada.

### Mejorado
- Los binarios empaquetados deben superar una prueba de carga de SSL y de las dependencias de la aplicación antes de publicarse en GitHub Releases.

## [1.4.2] - 2026-09-02

### Corregido
- El reinicio posterior a una actualización usa un entorno nuevo de PyInstaller y ya no intenta cargar archivos desde un directorio temporal `_MEI` eliminado.
- El arranque de recuperación también limpia el entorno de PyInstaller para que la versión anterior pueda abrirse correctamente después de un rollback.

### Importante
- La actualización desde `v1.4.0` o `v1.4.1` debe instalarse manualmente una sola vez debido al error de reinicio de esas versiones. Las actualizaciones automáticas posteriores funcionarán desde `v1.4.2`.

## [1.4.1] - 2026-09-02

### Corregido
- La ventana de novedades ahora muestra el historial completo incluido con la aplicación en lugar de las notas genéricas de GitHub.
- Si el historial incluido no está disponible o no puede leerse, la aplicación abre la página de releases como alternativa.

### Mejorado
- Los GitHub Releases usan el `CHANGELOG.md` completo como notas, tanto al crearlos como al reprocesarlos.

## [1.4.0] - 2026-09-02

### Añadido
- Actualización automática y verificada del ejecutable desde la propia aplicación en Windows y Linux.
- Archivo `SHA256SUMS.txt` en cada release para verificar la integridad de los binarios descargados.
- Restauración automática de la versión anterior si la aplicación actualizada no confirma su arranque.

### Mejorado
- Las configuraciones de conexión, aplicación y puente USB tienen secciones y acciones de guardado claramente agrupadas.
- La búsqueda y descarga de actualizaciones se ejecuta en segundo plano para no bloquear la interfaz.

## [1.3.0] - 2026-08-27

### Añadido
- Margen configurable de 0 a 20 líneas antes del corte ESC/POS para evitar cortar el contenido demasiado al ras.
- Opción `cut_margin_lines` en la API para ajustar el margen de corte por trabajo.

### Mejorado
- La configuración de la aplicación se valida por completo antes de modificar o guardar los valores activos.

## [1.2.0] - 2026-08-09

### Añadido
- Ayuda contextual mediante botones `?` en los principales campos técnicos de la aplicación.
- Página de ayuda integrada para configurar impresoras de red, el puente USB, la API y los certificados.
- URL visible y copiable del portal HTTP para instalar el certificado CA en los clientes.

### Mejorado
- Las configuraciones nuevas usan `127.0.0.1` como destino de impresión predeterminado para facilitar el uso del puente USB local.
- El panel de inicio identifica si el destino apunta al puente USB local o a una impresora de red.
- El aviso de actualización dirige a la sección de descargas del sitio de Moviu.
- El sitio del proyecto incorpora iconografía consistente, una historia de integración con Odoo y el flujo opcional de aportes mediante dLocal Go.

## [1.1.0] - 2026-08-07

### Añadido
- Portal local para instalar la CA de Moviu, con descarga segura, instrucciones por plataforma y huella SHA-256 verificable.
- Configuración guiada del firewall para permitir solo las conexiones necesarias desde la red local en Windows, UFW y firewalld.
- GitHub Pages con presentación del producto, descargas y documentación para usuarios y desarrolladores.
- Compilación automatizada de ejecutables de Windows y Linux desde el tag de cada release.

### Mejorado
- Rediseño completo de la aplicación de escritorio con dashboard, navegación lateral, panel avanzado y vista de actividad.
- Nuevo icono de marca para la ventana, la bandeja del sistema y los ejecutables empaquetados.
- Inicio del servidor más confiable, con publicación mDNS únicamente después de confirmar que HTTPS está disponible.
- Manejo seguro de eventos de interfaz, logs, actualizaciones y puente USB desde procesos en segundo plano.
- Los cambios de configuración reinician el servicio activo para aplicarse inmediatamente y mantener correcta la URL mostrada.

### Corregido
- Los errores de inicio y ejecución de Uvicorn ahora llegan al registro de actividad de la aplicación.
- Las reglas de firewall administradas por Moviu pueden retirarse; las reglas de apertura solo se crean cuando UFW está activo.

## [1.0.5] - 2026-07-09

### Corregido
- Se silencia el traceback benigno `WinError 10054` que Windows puede registrar al cerrar conexiones HTTPS ya terminadas por el cliente.

## [1.0.4] - 2026-07-09

### Corregido
- Mejora de estabilidad para impresión PDF con tamaños de hoja personalizados en Windows.

## [1.0.3] - 2026-06-29

### Corregido
- El puente TCP -> USB ahora valida que la impresora seleccionada exista antes de iniciar.
- Si la impresora USB desaparece mientras el puente está activo, el estado y los logs muestran un error explícito.
- Los errores al enviar RAW a una impresora local ahora se devuelven como errores controlados en vez de `500` genérico.

## [1.0.2] - 2026-01-25

### Añadido
- **Soporte para Repositorios Privados**: Opción para configurar un GitHub Token y permitir actualizaciones desde repositorios privados.
- **Formateo Markdown en Novedades**: Las notas de versión ahora se muestran con formato enriquecido (títulos, negritas, listas).
- **Instancia Única**: El programa ahora detecta si ya se está ejecutando y trae la ventana existente al primer plano en lugar de abrir una nueva.

### Mejorado
- **Interfaz Avanzada**: Nuevo campo para el GitHub Token en la pestaña de configuración avanzada.
- **Diálogo de Novedades**: Mejora en el tamaño y espaciado de la ventana de visualización de cambios.

## [1.0.1] - 2026-01-25

### Añadido
- **Sistema de Actualizaciones**: Integración con GitHub Releases para notificaciones automáticas de nuevas versiones.
- **Botón "Copiar API Key"**: Acceso rápido a las credenciales desde la pestaña de Información.
- **Botón "Buscar Actualizaciones"**: Comprobación manual de nuevas versiones.

### Mejorado
- **Interfaz de Usuario (UX)**: Rediseño completo con Dashboard de estado y organización por pestañas (Información, Configuración, Puente USB, Avanzado, Logs).
- **Indicadores de Estado**: Nuevos indicadores visuales grandes (Verde/Rojo) para saber instantáneamente si el servidor está corriendo.
- **Soporte de Transparencia**: Ahora las imágenes con fondo transparente se imprimen correctamente sobre fondo blanco, evitando bloques negros.
- **Impresión Inteligente (Chunking)**: Las imágenes grandes ahora se dividen en partes de 128px para evitar que las impresoras se cuelguen o impriman basura por saturación de memoria.
- **Robustez Híbrida**: Soporte mejorado para imágenes en formato hexadecimal en el modo `hybrid`.

---

## [1.0.0] - 2026-01-20

### Añadido
- Versión inicial de Moviu Print Server.
- Soporte para modos: HTML, Imagen, PDF, RAW, RAW_TEXT, ZPL y Hybrid.
- Descubrimiento de servicios vía mDNS (Bonjour).
- Puente TCP -> USB para impresoras locales en Windows.
- Servidor HTTPS con certificados autogenerados.
- Modo de simulación para desarrollo.

# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

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

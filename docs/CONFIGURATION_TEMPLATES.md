# Plantillas de configuración

El asistente aparece en el primer inicio de una instalación nueva. También se puede abrir desde **Configuración → Usar plantilla de configuración**.

| Plantilla | Preguntas | Acceso | API key |
|---|---|---|---|
| Odoo, local (predeterminado) | Impresora y uso local o compartido | Solo este equipo, `127.0.0.1` | Desactivada |
| Odoo, compartido | Impresora y modo de acceso | Red local, `0.0.0.0` | Obligatoria |
| Odoo, compartido sin clave | Impresora y modo de acceso | Red local, `0.0.0.0` | Desactivada |
| ChePos | Impresora | Solo este equipo, `127.0.0.1` | Desactivada |

Todas las plantillas activan el puente USB incluido, usan la impresora seleccionada y dirigen la impresión al puente local. Desactivan la simulación e inician el puente y el servidor al finalizar y cada vez que se abre Moviu. No agregan la aplicación al inicio de Windows; ese ajuste sigue siendo independiente.

El modo compartido de Odoo habilita los puertos configurados de HTTPS, del portal de certificados y del puente USB en el firewall para la red local. Los clientes HTTPS usan la IP real del equipo, no `0.0.0.0`, y envían la API key que aparece en **Conexión** solo si el modo elegido la requiere. Sin clave, se muestra una advertencia y se recomienda usar únicamente redes privadas, controladas y seguras. El protocolo TCP directo del puente no utiliza API key. En todos los modos, los clientes HTTPS deben confiar en la CA de Moviu.

Antes de finalizar se puede retroceder o salir sin aplicar la plantilla. Si la impresora desaparece o el puente no puede iniciarse, el asistente permanece abierto para reintentar. Las configuraciones anteriores al asistente se conservan y no provocan su apertura automática. **Configuración manual** permite continuar con impresoras de red y Linux.

## Vista inicial

Odoo y ChePos abren el **modo fácil**: estado del servidor, botón grande de inicio/parada, IP copiable sola o con puerto y actividad reciente. El botón **Modo avanzado** abre la interfaz completa. Cada plantilla define `default_interface_mode`; el usuario puede cambiar el valor guardado en **Configuración → Al abrir Moviu**. Cambiar de vista durante el uso no modifica por sí solo esa preferencia.

## Añadir una plantilla

El catálogo está en [`moviu_server/configuration_templates.py`](../moviu_server/configuration_templates.py). Añade una entrada a `CONFIGURATION_TEMPLATES`, con un identificador único y estable:

```python
ConfigurationTemplate(
    id="mi-pos",
    label="Mi POS",
    description="Impresión USB desde este equipo.",
    access_modes=(LOCAL_ACCESS,),
    default_interface_mode="simple",  # "advanced" abre la interfaz completa
),
```

Para ofrecer uso compartido con o sin clave, utiliza `access_modes=(LOCAL_ACCESS, SHARED_ACCESS, SHARED_WITHOUT_KEY_ACCESS)`. El primer modo es el predeterminado. El asistente obtiene las opciones del catálogo y solo muestra la pregunta de acceso si la plantilla ofrece varios modos; no hace falta añadir condiciones por nombre a la interfaz. Las plantillas de este catálogo utilizan impresoras instaladas mediante el puente USB.

Incluye pruebas en `tests/test_configuration_templates.py` para cualquier comportamiento nuevo. Ejecuta `PYSTRAY_BACKEND=dummy python -m unittest discover -s tests -v`; las pruebas gráficas de `tests/test_setup_wizard.py` requieren una pantalla o Xvfb en Linux.

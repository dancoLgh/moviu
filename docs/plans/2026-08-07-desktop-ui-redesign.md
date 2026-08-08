# Moviu Print Server Desktop UI Redesign

## Objective

Replace the tab-based desktop interface with a modern dark dashboard inspired by the approved reference while preserving every existing server, printer, USB bridge, certificate, update, and diagnostic action.

## Layout

The maximized window has three persistent regions:

- A 170-pixel navigation sidebar with the Moviu brand, five page buttons, and access to release notes.
- A flexible central page container for Inicio, Impresoras, Conexion, Actividad, and Configuracion.
- A 300-pixel advanced panel that remains available on every page and can be collapsed to give space back to the center.

Navigation raises existing page frames instead of opening new windows. The active destination uses a blue highlighted state. The advanced panel groups related controls into visible sections for Red y API, Puente USB, Seguridad y certificados, and Diagnostico.

## Pages

Inicio summarizes server readiness, the configured printer, the HTTPS endpoint, USB bridge state, and recent in-session log events. It exposes the primary start and stop actions without duplicating configuration.

Impresoras owns printer host, port, paper width, image density, and simulation settings. Conexion shows the public URL and API key, API host and port, and certificate actions. Actividad contains the complete live log. Configuracion contains automatic startup, update credentials and checks, release notes, and save actions.

## Visual System

The interface uses Segoe UI, a near-black navy window background, slate-blue surfaces, subtle borders, electric blue actions, cyan accents, and green only for healthy states. Cards use native ttk frames with spacing and borders instead of introducing a new UI dependency. The approved Moviu icon remains the window, tray, and packaged executable icon.

## Behavior And Safety

Existing Tk variables and command methods remain the source of truth. Starting and stopping the server updates all visible status labels and actions. Recent activity is derived from actual application logs and is not presented as persistent print history. Collapsing the advanced panel changes only layout. Existing validation and dialogs remain in place.

## Testing

Pure presentation metadata and recent-activity behavior are covered without requiring a display server. Existing resource tests continue to validate the icon assets. Python compilation and a clean PyInstaller build verify syntax and packaged resources. Final Windows appearance still requires a native Windows smoke test because PyInstaller cannot cross-build a Windows executable from Linux.

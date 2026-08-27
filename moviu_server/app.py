"""Tkinter desktop shell that manages the local API server."""

from __future__ import annotations

import logging
import os
from queue import Empty, Full, Queue, SimpleQueue
import re
import signal
import subprocess
import socket
import sys
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

import pystray
from PIL import Image, ImageTk

import uvicorn

from .autostart import configure_autostart
from .certs import (
    ca_certificate_path,
    certificate_sha256_fingerprint,
    certificates_folder,
    ensure_certificates,
    export_ca_certificate,
    install_certificate_in_system,
)
from .config import AppConfig, CONFIG_DIR, load_config, save_config, VERSION
from .server import certificate_http_port, create_api, create_certificate_api
from .usb_bridge import UsbBridgeController, discover_printers
from .mdns import MoviuServiceAnnouncer, get_local_ip, get_local_ips
from .network_access import (
    NetworkAccessError,
    close_local_network_ports,
    is_local_network_bind,
    open_local_network_ports,
)
from .logging_config import build_uvicorn_log_config
from .resources import APP_ICON_ICO_PATH, load_app_icon
from .ui_state import (
    ActivityFeed,
    NAV_ITEMS,
    certificate_portal_url,
    printer_route_label,
    tooltip_coordinates,
)
from .updater import check_for_updates, open_release_page


def _suppress_windows_connection_reset_noise() -> None:
    """Ignore benign WinError 10054 raised while closing HTTPS connections."""
    if not sys.platform.startswith("win"):
        return

    try:
        from asyncio import proactor_events
    except Exception:
        return

    transport_cls = proactor_events._ProactorBasePipeTransport
    if getattr(transport_cls, "_moviu_connection_reset_patch", False):
        return

    original = transport_cls._call_connection_lost

    def patched_call_connection_lost(self, exc):
        try:
            return original(self, exc)
        except ConnectionResetError as err:
            if getattr(err, "winerror", None) == 10054:
                logging.debug("Conexión HTTPS cerrada por el cliente durante cleanup: %s", err)
                return None
            raise

    transport_cls._call_connection_lost = patched_call_connection_lost
    transport_cls._moviu_connection_reset_patch = True


def _certificate_hosts(config: AppConfig) -> list[str]:
    hosts = ["localhost", "127.0.0.1", *get_local_ips()]
    if config.host not in ("0.0.0.0", "127.0.0.1", "localhost"):
        hosts.append(config.host)
    return hosts


class HelpTooltip:
    """Small contextual popover shown by a field's help button."""

    def __init__(self, widget: ttk.Button, text: str) -> None:
        self.widget = widget
        self.text = text
        self.window: tk.Toplevel | None = None
        self.pinned = False
        widget.configure(command=self.toggle)
        widget.bind("<Enter>", self._show_on_hover, add="+")
        widget.bind("<Leave>", self._hide_after_hover, add="+")

    def _show_on_hover(self, _event: tk.Event) -> None:
        self.show()

    def _hide_after_hover(self, _event: tk.Event) -> None:
        if not self.pinned:
            self.hide()

    def toggle(self) -> None:
        if self.window is not None and self.pinned:
            self.pinned = False
            self.hide()
            return
        self.pinned = True
        self.show()

    def show(self) -> None:
        if self.window is not None:
            return
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        self.window.configure(bg="#2a405b")
        label = tk.Label(
            self.window,
            text=self.text,
            justify=tk.LEFT,
            wraplength=320,
            bg="#102238",
            fg="#dce7f5",
            padx=12,
            pady=9,
            font=("Segoe UI", 9),
        )
        label.pack(padx=1, pady=1)
        self.window.update_idletasks()
        x, y = tooltip_coordinates(
            self.widget.winfo_rootx(),
            self.widget.winfo_rooty(),
            self.widget.winfo_width(),
            self.window.winfo_reqwidth(),
            self.window.winfo_reqheight(),
            self.widget.winfo_screenwidth(),
            self.widget.winfo_screenheight(),
        )
        self.window.wm_geometry(f"+{x}+{y}")

    def hide(self) -> None:
        if self.window is not None:
            self.window.destroy()
            self.window = None


class ServerController:
    """Manage the uvicorn server on a background thread."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.server: uvicorn.Server | None = None
        self.thread: threading.Thread | None = None
        self.certificate_server: uvicorn.Server | None = None
        self.certificate_thread: threading.Thread | None = None
        self.mdns_announcer: MoviuServiceAnnouncer | None = None

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        _ensure_streams()
        _suppress_windows_connection_reset_noise()
        portal_port = certificate_http_port(self.config.port)
        # Generate certificate for localhost, internal IP and configured host
        cert_hosts = _certificate_hosts(self.config)
            
        cert_path, key_path = ensure_certificates(
            Path(self.config.ssl_cert_path), Path(self.config.ssl_key_path), cert_hosts
        )
        app = create_api(self.config)
        uvicorn_config = uvicorn.Config(
            app,
            host=self.config.host,
            port=self.config.port,
            log_level="info",
            log_config=self._log_config(),
            ssl_certfile=str(cert_path),
            ssl_keyfile=str(key_path),
        )
        certificate_config = uvicorn.Config(
            create_certificate_api(self.config),
            host=self.config.host,
            port=portal_port,
            log_level="info",
            log_config=self._log_config(),
        )
        self.server = uvicorn.Server(uvicorn_config)
        self.certificate_server = uvicorn.Server(certificate_config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.certificate_thread = threading.Thread(
            target=self.certificate_server.run,
            daemon=True,
        )
        try:
            self.thread.start()
            self.certificate_thread.start()
        except Exception:
            self.stop()
            raise

    def announce_mdns(self) -> None:
        if self.mdns_announcer or not self.server or not self.server.started:
            return
        self.mdns_announcer = MoviuServiceAnnouncer(
            port=self.config.port,
            instance_name="Moviu Print Server",
            properties={
                "version": VERSION,
                "api_version": "1.0",
                "protocol": "https",
                "certificate_http_port": certificate_http_port(self.config.port),
            },
        )
        self.mdns_announcer.start()

    def stop(self) -> bool:
        # Stop mDNS announcement
        if self.mdns_announcer:
            self.mdns_announcer.stop()
            self.mdns_announcer = None

        if self.server:
            self.server.should_exit = True
        if self.certificate_server:
            self.certificate_server.should_exit = True
        server_threads = (
            (self.server, self.thread),
            (self.certificate_server, self.certificate_thread),
        )
        for _server, thread in server_threads:
            if thread and thread.is_alive():
                thread.join(timeout=2)
        for server, thread in server_threads:
            if server and thread and thread.is_alive():
                server.force_exit = True
                thread.join(timeout=3)
        if any(thread and thread.is_alive() for _server, thread in server_threads):
            logging.error("Uno de los servicios de Moviu no respondió al apagado")
            return False
        self.server = None
        self.thread = None
        self.certificate_server = None
        self.certificate_thread = None
        return True

    def _log_config(self) -> dict:
        log_file = certificates_folder() / "app.log"
        stream = sys.stdout or sys.__stdout__
        if stream is None:
            stream = open(os.devnull, "w", encoding="utf-8")
        return build_uvicorn_log_config(log_file, stream)


class DesktopApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Moviu Print Server")
        self.config = load_config()
        self.controller = ServerController(self.config)
        self.bridge_status_queue: SimpleQueue[str] = SimpleQueue()
        self.bridge_controller = UsbBridgeController(on_status=self._update_bridge_status)
        self.activity_feed = ActivityFeed()
        self.ui_callback_queue: SimpleQueue[Callable[[], None]] = SimpleQueue()
        self._closing = False
        self._server_start_token: object | None = None
        _ensure_streams()
        self._setup_logging()
        self._set_window_icon()
        self._setup_theme()
        self._build_ui()
        self._maximize_window()
        self._configure_window_hooks()
        self._register_signal_handlers()
        self.tray = SystemTray(
            on_show=lambda: self._queue_ui_callback(self._restore_from_tray),
            on_exit=lambda: self._queue_ui_callback(self._do_exit),
        )
        self._check_single_instance()
        self._apply_autostart(self.config.auto_start, notify=False)
        self._maybe_autostart_server()
        self._maybe_autostart_bridge()

    def _set_window_icon(self) -> None:
        """Apply the branded icon to the Tk window and Windows taskbar."""
        try:
            self._window_icon = ImageTk.PhotoImage(load_app_icon(256), master=self.root)
            self.root.iconphoto(True, self._window_icon)
            if sys.platform.startswith("win"):
                self.root.iconbitmap(default=str(APP_ICON_ICO_PATH))
        except (OSError, tk.TclError):
            logging.exception("No se pudo cargar el icono de Moviu Print Server")

    def _check_single_instance(self) -> None:
        """Prevent multiple instances and bring the existing one to focus."""
        self.instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.instance_port = 29170  # Dedicated port for instance signaling
        
        try:
            # Try to bind to the port
            self.instance_socket.bind(('127.0.0.1', self.instance_port))
            self.instance_socket.listen(1)
            
            # If successful, start a listener thread to handle 'show' signals
            def listen_for_other_instances():
                while True:
                    try:
                        conn, _ = self.instance_socket.accept()
                        data = conn.recv(1024).decode('utf-8')
                        if data == "SHOW":
                            self._queue_ui_callback(self._restore_from_tray)
                        conn.close()
                    except Exception:
                        break
            
            threading.Thread(target=listen_for_other_instances, daemon=True).start()
            
        except socket.error:
            # Another instance is already running
            try:
                # Signal the existing instance to show itself
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.connect(('127.0.0.1', self.instance_port))
                client.sendall(b"SHOW")
                client.close()
            except Exception:
                pass
            
            # Exit the current instance
            sys.exit(0)

    def _build_ui(self) -> None:
        self.host_var = tk.StringVar(value=self.config.host)
        self.port_var = tk.StringVar(value=str(self.config.port))
        self.printer_host_var = tk.StringVar(value=self.config.printer_host)
        self.printer_port_var = tk.StringVar(value=str(self.config.printer_port))
        self.printer_width_var = tk.StringVar(value=str(self.config.printer_width))
        self.printer_gamma_var = tk.IntVar(value=self.config.printer_gamma)
        self.cut_margin_lines_var = tk.StringVar(value=str(self.config.cut_margin_lines))
        self.printer_gamma_str = tk.StringVar(value=str(self.config.printer_gamma))
        
        def _update_gamma_str(*args):
            self.printer_gamma_str.set(str(self.printer_gamma_var.get()))
        self.printer_gamma_var.trace_add("write", _update_gamma_str)

        self.api_key_var = tk.StringVar(value=self.config.api_key)
        self.simulate_var = tk.BooleanVar(value=self.config.simulate_printer)
        self.auto_start_var = tk.BooleanVar(value=self.config.auto_start)

        self.bridge_enabled_var = tk.BooleanVar(value=self.config.usb_bridge_enabled)
        self.bridge_port_var = tk.StringVar(value=str(self.config.usb_bridge_port))
        self.bridge_printer_var = tk.StringVar(value=self.config.usb_bridge_printer)
        self.bridge_autostart_var = tk.BooleanVar(value=self.config.usb_bridge_autostart)
        self.bridge_status_var = tk.StringVar(value="Puente detenido")
        self.github_token_var = tk.StringVar(value=self.config.github_token)
        self.available_printers: list[str] = []
        self.help_tooltips: list[HelpTooltip] = []
        display_host = self.config.host if self.config.host != "0.0.0.0" else get_local_ip()
        self.full_url_var = tk.StringVar(value=f"https://{display_host}:{self.config.port}")
        self.certificate_url_var = tk.StringVar(
            value=certificate_portal_url(
                self.config.host,
                certificate_http_port(self.config.port),
                display_host,
            )
        )
        self.printer_route_var = tk.StringVar(
            value=printer_route_label(
                self.config.printer_host,
                self.config.printer_port,
                self.config.usb_bridge_enabled,
                self.config.usb_bridge_port,
            )
        )

        self.root.minsize(1050, 680)
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        shell = ttk.Frame(self.root, style="App.TFrame")
        shell.grid(row=0, column=0, sticky="nsew")
        self.layout_shell = shell
        shell.rowconfigure(0, weight=1)
        shell.columnconfigure(1, weight=1)
        shell.columnconfigure(2, minsize=310)

        sidebar = ttk.Frame(shell, style="Sidebar.TFrame", width=172, padding=(12, 18))
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        sidebar.rowconfigure(2, weight=1)

        brand = ttk.Frame(sidebar, style="Sidebar.TFrame")
        brand.grid(row=0, column=0, sticky="ew", pady=(0, 24))
        self._brand_icon = ImageTk.PhotoImage(load_app_icon(38), master=self.root)
        ttk.Label(brand, image=self._brand_icon, style="Sidebar.TLabel").pack(side=tk.LEFT)
        brand_text = ttk.Frame(brand, style="Sidebar.TFrame")
        brand_text.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(brand_text, text="moviu", style="Brand.TLabel").pack(anchor="w")
        ttk.Label(brand_text, text=f"Print Server  {VERSION}", style="BrandMeta.TLabel").pack(anchor="w")

        ttk.Label(sidebar, text="NAVEGACIÓN", style="NavSection.TLabel").grid(
            row=1, column=0, sticky="w", padx=8, pady=(0, 8)
        )
        nav_frame = ttk.Frame(sidebar, style="Sidebar.TFrame")
        nav_frame.grid(row=2, column=0, sticky="nsew")
        self.nav_buttons: dict[str, ttk.Button] = {}
        for destination, label in NAV_ITEMS:
            button = ttk.Button(
                nav_frame,
                text=label,
                style="Nav.TButton",
                command=lambda page=destination: self._show_page(page),
            )
            button.pack(fill=tk.X, pady=3)
            self.nav_buttons[destination] = button

        ttk.Separator(sidebar).grid(row=3, column=0, sticky="ew", pady=12)
        ttk.Button(
            sidebar,
            text="Novedades",
            style="Nav.TButton",
            command=self._show_changelog,
        ).grid(row=4, column=0, sticky="ew")

        center = ttk.Frame(shell, style="App.TFrame")
        center.grid(row=0, column=1, sticky="nsew")
        center.rowconfigure(1, weight=1)
        center.columnconfigure(0, weight=1)

        topbar = ttk.Frame(center, style="Topbar.TFrame", padding=(20, 12))
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.columnconfigure(1, weight=1)
        self.page_title_var = tk.StringVar(value="Inicio")
        ttk.Label(topbar, textvariable=self.page_title_var, style="PageTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.update_link_var = tk.StringVar(value="")
        self.update_label = ttk.Label(
            topbar,
            textvariable=self.update_link_var,
            cursor="hand2",
            style="Update.TLabel",
        )
        self.update_label.grid(row=0, column=1, sticky="e", padx=14)
        self.update_label.bind("<Button-1>", lambda _event: self._on_update_click())
        self.advanced_toggle_btn = ttk.Button(
            topbar,
            text="Ocultar panel",
            style="Secondary.TButton",
            command=self._toggle_advanced_panel,
        )
        self.advanced_toggle_btn.grid(row=0, column=2, sticky="e")

        page_host = ttk.Frame(center, style="Page.TFrame", padding=18)
        page_host.grid(row=1, column=0, sticky="nsew")
        page_host.rowconfigure(0, weight=1)
        page_host.columnconfigure(0, weight=1)
        self.pages: dict[str, ttk.Frame] = {}
        for destination, _label in NAV_ITEMS:
            page = ttk.Frame(page_host, style="Page.TFrame")
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[destination] = page

        self._build_home_page(self.pages["home"])
        self._build_printers_page(self.pages["printers"])
        self._build_connection_page(self.pages["connection"])
        self._build_activity_page(self.pages["activity"])
        self._build_settings_page(self.pages["settings"])
        self._build_help_page(self.pages["help"])

        self.advanced_panel = ttk.Frame(
            shell,
            style="Advanced.TFrame",
            width=310,
            padding=(14, 16),
        )
        self.advanced_panel.grid(row=0, column=2, sticky="nsew")
        self._build_advanced_panel(self.advanced_panel)
        self.advanced_panel_visible = True

        self._show_page("home")

        self.refresh_printers(initial=True)
        self._refresh_activity_summary()
        self._poll_background_events()
        self.root.after(3000, self._background_update_check)

    def _build_home_page(self, page: ttk.Frame) -> None:
        for column in (0, 1):
            page.columnconfigure(column, weight=1)
        page.rowconfigure(2, weight=1)

        hero = self._card(page, padding=(22, 18))
        hero.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        hero.columnconfigure(0, weight=1)
        self.status_title_var = tk.StringVar(value="Servidor listo para iniciar")
        self.status_desc_var = tk.StringVar(
            value="Inicia el servicio para recibir trabajos de impresión desde la red."
        )
        self.status_label = ttk.Label(hero, textvariable=self.status_title_var, style="HeroTitle.TLabel")
        self.status_label.grid(row=0, column=0, sticky="w")
        ttk.Label(hero, textvariable=self.status_desc_var, style="Muted.TLabel").grid(
            row=1, column=0, sticky="w", pady=(4, 14)
        )
        actions = ttk.Frame(hero, style="Surface.TFrame")
        actions.grid(row=2, column=0, sticky="w")
        self.main_action_btn = ttk.Button(
            actions,
            text="Iniciar servidor",
            style="Primary.TButton",
            command=self.start_server,
        )
        self.main_action_btn.pack(side=tk.LEFT)
        self.stop_btn = ttk.Button(
            actions,
            text="Detener",
            style="Secondary.TButton",
            command=self.stop_server,
            state="disabled",
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.server_badge_var = tk.StringVar(value="Servidor detenido")
        self.server_badge_label = ttk.Label(
            hero,
            textvariable=self.server_badge_var,
            style="DangerBadge.TLabel",
            padding=(10, 6),
        )
        self.server_badge_label.grid(row=0, column=1, rowspan=3, sticky="ne", padx=(18, 0))

        printer_card = self._card(page)
        printer_card.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(0, 12))
        printer_title = ttk.Frame(printer_card, style="Surface.TFrame")
        printer_title.pack(fill=tk.X)
        ttk.Label(printer_title, text="Impresora predeterminada", style="CardTitle.TLabel").pack(
            side=tk.LEFT
        )
        self._help_button(
            printer_title,
            "Es el destino de respaldo cuando un trabajo no indica otra impresora.",
        ).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(printer_card, textvariable=self.printer_host_var, style="Metric.TLabel").pack(
            anchor="w", pady=(12, 2)
        )
        ttk.Label(printer_card, textvariable=self.printer_route_var, style="InfoBadge.TLabel").pack(
            anchor="w"
        )
        printer_meta = ttk.Frame(printer_card, style="Surface.TFrame")
        printer_meta.pack(fill=tk.X, pady=(16, 10))
        ttk.Label(printer_meta, text="Puerto", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(printer_meta, textvariable=self.printer_port_var, style="BodyStrong.TLabel").grid(
            row=1, column=0, sticky="w"
        )
        ttk.Label(printer_meta, text="Ancho", style="Muted.TLabel").grid(
            row=0, column=1, sticky="w", padx=(36, 0)
        )
        ttk.Label(printer_meta, textvariable=self.printer_width_var, style="BodyStrong.TLabel").grid(
            row=1, column=1, sticky="w", padx=(36, 0)
        )
        ttk.Button(
            printer_card,
            text="Configurar impresora",
            style="Outline.TButton",
            command=lambda: self._show_page("printers"),
        ).pack(fill=tk.X, side=tk.BOTTOM)

        connection_card = self._card(page)
        connection_card.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=(0, 12))
        ttk.Label(connection_card, text="Conexión web", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(connection_card, text="HTTPS configurado", style="SuccessBadge.TLabel").pack(
            anchor="w", pady=(12, 10)
        )
        ttk.Entry(connection_card, textvariable=self.full_url_var, state="readonly").pack(fill=tk.X)
        ttk.Label(
            connection_card,
            text="Las páginas autorizadas pueden enviar trabajos con la API key.",
            style="Muted.TLabel",
            wraplength=340,
        ).pack(anchor="w", pady=(14, 10))
        ttk.Label(connection_card, textvariable=self.bridge_status_var, style="Status.TLabel").pack(
            anchor="w", side=tk.BOTTOM
        )

        activity_card = self._card(page, padding=(16, 12))
        activity_card.grid(row=2, column=0, columnspan=2, sticky="nsew")
        activity_card.columnconfigure(0, weight=1)
        ttk.Label(activity_card, text="Actividad reciente", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Button(
            activity_card,
            text="Ver toda la actividad",
            style="Link.TButton",
            command=lambda: self._show_page("activity"),
        ).grid(row=0, column=1, sticky="e")
        self.activity_message_vars: list[tk.StringVar] = []
        self.activity_time_vars: list[tk.StringVar] = []
        self.activity_dots: list[ttk.Label] = []
        for row_index in range(4):
            row = ttk.Frame(activity_card, style="ActivityRow.TFrame", padding=(10, 7))
            row.grid(row=row_index + 1, column=0, columnspan=2, sticky="ew", pady=2)
            row.columnconfigure(1, weight=1)
            dot = ttk.Label(row, text="o", style="InfoDot.TLabel")
            dot.grid(row=0, column=0, padx=(0, 9))
            message_var = tk.StringVar(value="Sin actividad reciente" if row_index == 0 else "")
            time_var = tk.StringVar(value="")
            ttk.Label(row, textvariable=message_var, style="Activity.TLabel").grid(
                row=0, column=1, sticky="w"
            )
            ttk.Label(row, textvariable=time_var, style="Muted.TLabel").grid(
                row=0, column=2, sticky="e", padx=(12, 0)
            )
            self.activity_dots.append(dot)
            self.activity_message_vars.append(message_var)
            self.activity_time_vars.append(time_var)

    def _build_printers_page(self, page: ttk.Frame) -> None:
        for column in (0, 1):
            page.columnconfigure(column, weight=1)
        network = self._card(page)
        network.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        network.columnconfigure(1, weight=1)
        ttk.Label(network, text="Impresora de red", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 14)
        )
        self._labeled_entry(
            network,
            1,
            "Host o dirección IP",
            self.printer_host_var,
            "Usa 127.0.0.1 para enviar al puente USB de este equipo. Usa la IP de la impresora para imprimir directamente por red.",
        )
        self._labeled_entry(
            network,
            2,
            "Puerto",
            self.printer_port_var,
            "Puerto TCP del destino. El valor habitual para impresión RAW es 9100 y debe coincidir con el puerto del puente USB.",
        )

        rendering = self._card(page)
        rendering.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        rendering.columnconfigure(1, weight=1)
        ttk.Label(rendering, text="Papel y renderizado", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 14)
        )
        ttk.Label(rendering, text="Ancho de papel", style="FieldLabel.TLabel").grid(
            row=1, column=0, sticky="w", pady=7
        )
        self.width_combo = ttk.Combobox(
            rendering,
            textvariable=self.printer_width_var,
            values=["576 (80mm)", "384 (58mm)"],
            state="readonly",
        )
        self.width_combo.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(14, 0), pady=7)
        ttk.Label(rendering, text="Oscuridad", style="FieldLabel.TLabel").grid(
            row=2, column=0, sticky="w", pady=7
        )
        ttk.Scale(
            rendering,
            variable=self.printer_gamma_var,
            from_=200,
            to=1000,
            orient=tk.HORIZONTAL,
        ).grid(row=2, column=1, sticky="ew", padx=(14, 8), pady=7)
        ttk.Label(rendering, textvariable=self.printer_gamma_str, width=4).grid(
            row=2, column=2, sticky="e"
        )
        ttk.Label(rendering, text="Margen antes del corte", style="FieldLabel.TLabel").grid(
            row=3, column=0, sticky="w", pady=7
        )
        ttk.Spinbox(
            rendering,
            textvariable=self.cut_margin_lines_var,
            from_=0,
            to=20,
            width=6,
        ).grid(row=3, column=1, sticky="w", padx=(14, 0), pady=7)
        ttk.Label(rendering, text="líneas", style="Muted.TLabel").grid(
            row=3, column=2, sticky="w", pady=7
        )
        ttk.Checkbutton(
            rendering,
            text="Simular impresora y guardar trabajos localmente",
            variable=self.simulate_var,
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(14, 4))

        footer = self._card(page, padding=(16, 12))
        footer.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Label(
            footer,
            text="Si el servidor está activo, se reiniciará para aplicar los cambios.",
            style="Muted.TLabel",
        ).pack(side=tk.LEFT)
        ttk.Button(
            footer,
            text="Guardar cambios",
            style="Primary.TButton",
            command=self.save_settings,
        ).pack(side=tk.RIGHT)

    def _build_connection_page(self, page: ttk.Frame) -> None:
        for column in (0, 1):
            page.columnconfigure(column, weight=1)
        api_card = self._card(page)
        api_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        ttk.Label(api_card, text="Acceso a la API", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(api_card, text="URL HTTPS", style="FieldLabel.TLabel").pack(anchor="w", pady=(16, 6))
        ttk.Entry(api_card, textvariable=self.full_url_var, state="readonly").pack(fill=tk.X)
        portal_heading = ttk.Frame(api_card, style="Surface.TFrame")
        portal_heading.pack(fill=tk.X, pady=(14, 6))
        ttk.Label(portal_heading, text="Portal de certificado (HTTP)", style="FieldLabel.TLabel").pack(
            side=tk.LEFT
        )
        self._help_button(
            portal_heading,
            "Abre esta dirección desde cada tablet o PC cliente para descargar e instalar el certificado CA antes de usar HTTPS.",
        ).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Entry(api_card, textvariable=self.certificate_url_var, state="readonly").pack(fill=tk.X)
        portal_actions = ttk.Frame(api_card, style="Surface.TFrame")
        portal_actions.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(portal_actions, text="Copiar URL", command=self._copy_certificate_url).pack(side=tk.LEFT)
        ttk.Button(
            portal_actions,
            text="Abrir portal",
            command=self.open_certificate_portal,
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(api_card, text="API key", style="FieldLabel.TLabel").pack(anchor="w", pady=(14, 6))
        ttk.Entry(api_card, textvariable=self.api_key_var, state="readonly").pack(fill=tk.X)
        api_actions = ttk.Frame(api_card, style="Surface.TFrame")
        api_actions.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(api_actions, text="Copiar API key", command=self._copy_api_key).pack(side=tk.LEFT)
        ttk.Button(api_actions, text="Regenerar", command=self.regenerate_api_key).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        cert_card = self._card(page)
        cert_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        cert_card.columnconfigure(1, weight=1)
        ttk.Label(cert_card, text="Red y certificados", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 14)
        )
        self._labeled_entry(
            cert_card,
            1,
            "Host API",
            self.host_var,
            "0.0.0.0 permite conexiones desde la red local. 127.0.0.1 limita la API a este equipo. Los clientes usan la IP local mostrada en URL HTTPS.",
        )
        self._labeled_entry(
            cert_card,
            2,
            "Puerto API",
            self.port_var,
            "Puerto HTTPS de Moviu. El portal HTTP de certificados utiliza automáticamente el puerto siguiente.",
        )
        for row_index, (label, command) in enumerate(
            [
                ("Generar certificados SSL", self.generate_certs),
                ("Instalar certificado en Windows", self.install_cert_locally),
                ("Exportar certificado CA", self.export_cert),
                ("Abrir portal de instalación", self.open_certificate_portal),
                ("Habilitar acceso en la red local", self.enable_local_network_access),
                ("Retirar acceso del firewall", self.disable_local_network_access),
            ],
            start=3,
        ):
            ttk.Button(cert_card, text=label, style="Outline.TButton", command=command).grid(
                row=row_index, column=0, columnspan=2, sticky="ew", pady=(8 if row_index == 3 else 3, 0)
            )
        ttk.Button(
            cert_card,
            text="Guardar red",
            style="Primary.TButton",
            command=self.save_settings,
        ).grid(row=8, column=0, columnspan=2, sticky="ew", pady=(14, 0))

    def _build_activity_page(self, page: ttk.Frame) -> None:
        page.rowconfigure(1, weight=1)
        page.columnconfigure(0, weight=1)
        toolbar = self._card(page, padding=(14, 10))
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(toolbar, text="Registro en tiempo real", style="CardTitle.TLabel").pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Abrir simulaciones", command=self.open_simulations).pack(side=tk.RIGHT)
        ttk.Button(toolbar, text="Limpiar vista", command=self._clear_log).pack(side=tk.RIGHT, padx=8)

        log_card = self._card(page, padding=1)
        log_card.grid(row=1, column=0, sticky="nsew")
        self.log_widget = tk.Text(
            log_card,
            state="disabled",
            bg="#081321",
            fg="#a9b8cc",
            insertbackground="#f4f7fb",
            selectbackground="#1f5eff",
            relief="flat",
            borderwidth=0,
            padx=14,
            pady=12,
            font=("Consolas", 10),
        )
        self.log_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(log_card, command=self.log_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_widget.configure(yscrollcommand=scrollbar.set)
        self.log_handler.attach(self.log_widget)

    def _build_settings_page(self, page: ttk.Frame) -> None:
        for column in (0, 1):
            page.columnconfigure(column, weight=1)
        behavior = self._card(page)
        behavior.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        ttk.Label(behavior, text="Comportamiento", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Checkbutton(
            behavior,
            text="Ejecutar Moviu al iniciar Windows",
            variable=self.auto_start_var,
        ).pack(anchor="w", pady=(18, 8))
        ttk.Checkbutton(
            behavior,
            text="Arrancar el puente USB automáticamente",
            variable=self.bridge_autostart_var,
        ).pack(anchor="w", pady=8)
        ttk.Button(
            behavior,
            text="Guardar configuración",
            style="Primary.TButton",
            command=self.save_settings,
        ).pack(anchor="w", pady=(18, 0))

        updates = self._card(page)
        updates.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        ttk.Label(updates, text="Actualizaciones y soporte", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(updates, text="GitHub token privado", style="FieldLabel.TLabel").pack(
            anchor="w", pady=(18, 6)
        )
        ttk.Entry(updates, textvariable=self.github_token_var, show="*").pack(fill=tk.X)
        ttk.Button(updates, text="Buscar actualizaciones", command=self._manual_update_check).pack(
            fill=tk.X, pady=(14, 5)
        )
        ttk.Button(updates, text="Ver novedades", command=self._show_changelog).pack(fill=tk.X, pady=5)
        ttk.Button(updates, text="Abrir simulaciones", command=self.open_simulations).pack(
            fill=tk.X, pady=5
        )

    def _build_help_page(self, page: ttk.Frame) -> None:
        for column in (0, 1):
            page.columnconfigure(column, weight=1)
        page.rowconfigure(0, weight=1)

        printer = self._card(page)
        printer.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        ttk.Label(printer, text="Destino de impresión", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            printer,
            text=(
                "La impresora predeterminada recibe los trabajos que no indican otro destino.\n\n"
                "Impresora de red: escribe su IP y puerto RAW, normalmente 9100.\n\n"
                "Impresora USB: usa 127.0.0.1, activa el puente USB, selecciona la impresora "
                "de Windows y configura el mismo puerto en ambos lugares."
            ),
            style="Muted.TLabel",
            justify=tk.LEFT,
            wraplength=360,
        ).pack(anchor="w", fill=tk.X, pady=(14, 18))
        ttk.Button(
            printer,
            text="Configurar impresora",
            style="Outline.TButton",
            command=lambda: self._show_page("printers"),
        ).pack(fill=tk.X, side=tk.BOTTOM)

        connection = self._card(page)
        connection.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        ttk.Label(connection, text="Conexión y certificados", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            connection,
            text=(
                "Host API 0.0.0.0 hace que Moviu escuche en la red local; los clientes se conectan "
                "usando la IP local mostrada por la aplicación.\n\n"
                "Para preparar un cliente: inicia el servidor, abre allí el portal HTTP, comprueba "
                "la huella, instala el certificado CA y después utiliza la URL HTTPS con la API key."
            ),
            style="Muted.TLabel",
            justify=tk.LEFT,
            wraplength=360,
        ).pack(anchor="w", fill=tk.X, pady=(14, 10))
        ttk.Label(connection, text="Portal para clientes", style="FieldLabel.TLabel").pack(
            anchor="w", pady=(4, 6)
        )
        ttk.Entry(connection, textvariable=self.certificate_url_var, state="readonly").pack(fill=tk.X)
        help_actions = ttk.Frame(connection, style="Surface.TFrame")
        help_actions.pack(fill=tk.X, pady=(10, 0), side=tk.BOTTOM)
        ttk.Button(help_actions, text="Copiar URL", command=self._copy_certificate_url).pack(
            side=tk.LEFT
        )
        ttk.Button(
            help_actions,
            text="Ir a Conexión",
            style="Outline.TButton",
            command=lambda: self._show_page("connection"),
        ).pack(side=tk.RIGHT)

    def _build_advanced_panel(self, panel: ttk.Frame) -> None:
        ttk.Label(panel, text="Configuración avanzada", style="AdvancedTitle.TLabel").pack(anchor="w")
        ttk.Label(
            panel,
            text="Opciones técnicas del servicio local.",
            style="AdvancedMuted.TLabel",
        ).pack(anchor="w", pady=(4, 14))
        self.accordions: dict[str, tuple[ttk.Button, ttk.Frame, str, bool]] = {}

        scroll_host = ttk.Frame(panel, style="Advanced.TFrame")
        scroll_host.pack(fill=tk.BOTH, expand=True)
        self.advanced_canvas = tk.Canvas(
            scroll_host,
            bg="#0a1929",
            highlightthickness=0,
            borderwidth=0,
            width=270,
        )
        advanced_scrollbar = ttk.Scrollbar(
            scroll_host,
            orient=tk.VERTICAL,
            command=self.advanced_canvas.yview,
        )
        self.advanced_canvas.configure(yscrollcommand=advanced_scrollbar.set)
        self.advanced_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        advanced_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        content = ttk.Frame(self.advanced_canvas, style="Advanced.TFrame")
        self.advanced_canvas_window = self.advanced_canvas.create_window(
            (0, 0),
            window=content,
            anchor="nw",
        )
        content.bind(
            "<Configure>",
            lambda _event: self.advanced_canvas.configure(
                scrollregion=self.advanced_canvas.bbox("all")
            ),
        )
        self.advanced_canvas.bind(
            "<Configure>",
            lambda event: self.advanced_canvas.itemconfigure(
                self.advanced_canvas_window,
                width=event.width,
            ),
        )
        self.advanced_canvas.bind("<MouseWheel>", self._scroll_advanced_panel)
        self.advanced_canvas.bind("<Button-4>", self._scroll_advanced_panel)
        self.advanced_canvas.bind("<Button-5>", self._scroll_advanced_panel)

        network = self._accordion(content, "network", "Red y API", expanded=True)
        ttk.Label(network, text="Host API", style="AdvancedLabel.TLabel").pack(anchor="w")
        ttk.Entry(network, textvariable=self.host_var).pack(fill=tk.X, pady=(4, 9))
        ttk.Label(network, text="Puerto API", style="AdvancedLabel.TLabel").pack(anchor="w")
        ttk.Entry(network, textvariable=self.port_var).pack(fill=tk.X, pady=(4, 9))
        ttk.Label(network, text="API key", style="AdvancedLabel.TLabel").pack(anchor="w")
        ttk.Entry(network, textvariable=self.api_key_var, state="readonly").pack(
            fill=tk.X, pady=(4, 8)
        )
        network_actions = ttk.Frame(network, style="AdvancedBody.TFrame")
        network_actions.pack(fill=tk.X)
        ttk.Button(network_actions, text="Copiar", command=self._copy_api_key).pack(side=tk.LEFT)
        ttk.Button(network_actions, text="Guardar", command=self.save_settings).pack(side=tk.RIGHT)
        ttk.Button(
            network,
            text="Habilitar acceso en la red local",
            command=self.enable_local_network_access,
        ).pack(fill=tk.X, pady=(8, 0))
        ttk.Button(
            network,
            text="Retirar acceso del firewall",
            command=self.disable_local_network_access,
        ).pack(fill=tk.X, pady=(4, 0))

        bridge = self._accordion(content, "bridge", "Puente USB")
        bridge_help = ttk.Frame(bridge, style="AdvancedBody.TFrame")
        bridge_help.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(bridge_help, text="Convierte TCP en impresión USB", style="AdvancedLabel.TLabel").pack(
            side=tk.LEFT
        )
        self._help_button(
            bridge_help,
            "Recibe trabajos en un puerto TCP local y los entrega a la impresora USB seleccionada. Configura 127.0.0.1 y el mismo puerto como impresora predeterminada.",
        ).pack(side=tk.RIGHT)
        ttk.Checkbutton(
            bridge,
            text="Habilitar puente TCP a USB",
            variable=self.bridge_enabled_var,
        ).pack(anchor="w", pady=(0, 8))
        ttk.Label(bridge, text="Impresora USB", style="AdvancedLabel.TLabel").pack(anchor="w")
        self.printer_combo = ttk.Combobox(bridge, textvariable=self.bridge_printer_var, state="readonly")
        self.printer_combo.pack(fill=tk.X, pady=(4, 8))
        ttk.Label(bridge, text="Puerto TCP", style="AdvancedLabel.TLabel").pack(anchor="w")
        ttk.Entry(bridge, textvariable=self.bridge_port_var).pack(fill=tk.X, pady=(4, 8))
        ttk.Checkbutton(
            bridge,
            text="Arrancar automáticamente",
            variable=self.bridge_autostart_var,
        ).pack(anchor="w", pady=(0, 8))
        ttk.Label(bridge, textvariable=self.bridge_status_var, style="AdvancedStatus.TLabel").pack(
            anchor="w", pady=(0, 8)
        )
        bridge_actions = ttk.Frame(bridge, style="AdvancedBody.TFrame")
        bridge_actions.pack(fill=tk.X)
        ttk.Button(bridge_actions, text="Actualizar", command=self.refresh_printers).pack(side=tk.LEFT)
        ttk.Button(bridge_actions, text="Iniciar", command=self.start_bridge).pack(side=tk.LEFT, padx=5)
        ttk.Button(bridge_actions, text="Detener", command=self.stop_bridge).pack(side=tk.RIGHT)

        security = self._accordion(content, "security", "Seguridad y certificados")
        for label, command in [
            ("Generar certificados SSL", self.generate_certs),
            ("Instalar en Windows", self.install_cert_locally),
            ("Exportar certificado CA", self.export_cert),
            ("Abrir portal de instalación", self.open_certificate_portal),
        ]:
            ttk.Button(security, text=label, command=command).pack(fill=tk.X, pady=3)

        diagnostics = self._accordion(content, "diagnostics", "Diagnóstico y registros")
        ttk.Button(diagnostics, text="Ver actividad", command=lambda: self._show_page("activity")).pack(
            fill=tk.X, pady=3
        )
        ttk.Button(diagnostics, text="Abrir simulaciones", command=self.open_simulations).pack(
            fill=tk.X, pady=3
        )
        ttk.Button(diagnostics, text="Buscar actualizaciones", command=self._manual_update_check).pack(
            fill=tk.X, pady=3
        )
        self._bind_advanced_scroll(content)

    def _card(self, parent: ttk.Frame, padding: tuple[int, int] = (18, 16)) -> ttk.Frame:
        return ttk.Frame(parent, style="Surface.TFrame", padding=padding)

    def _labeled_entry(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        help_text: str | None = None,
    ) -> ttk.Entry:
        label_frame = ttk.Frame(parent, style="Surface.TFrame")
        label_frame.grid(row=row, column=0, sticky="w", pady=7)
        ttk.Label(label_frame, text=label, style="FieldLabel.TLabel").pack(side=tk.LEFT)
        if help_text:
            self._help_button(label_frame, help_text).pack(side=tk.LEFT, padx=(5, 0))
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", padx=(14, 0), pady=7)
        return entry

    def _help_button(self, parent: tk.Misc, text: str) -> ttk.Button:
        button = ttk.Button(parent, text="?", style="Help.TButton", width=2, takefocus=True)
        self.help_tooltips.append(HelpTooltip(button, text))
        return button

    def _accordion(
        self,
        parent: ttk.Frame,
        key: str,
        title: str,
        expanded: bool = False,
    ) -> ttk.Frame:
        wrapper = ttk.Frame(parent, style="Advanced.TFrame")
        wrapper.pack(fill=tk.X, pady=4)
        header = ttk.Button(
            wrapper,
            text=f"{'-' if expanded else '+'}  {title}",
            style="Accordion.TButton",
            command=lambda: self._toggle_accordion(key),
        )
        header.pack(fill=tk.X)
        body = ttk.Frame(wrapper, style="AdvancedBody.TFrame", padding=(10, 10))
        if expanded:
            body.pack(fill=tk.X)
        self.accordions[key] = (header, body, title, expanded)
        return body

    def _toggle_accordion(self, key: str) -> None:
        header, body, title, expanded = self.accordions[key]
        expanded = not expanded
        header.configure(text=f"{'-' if expanded else '+'}  {title}")
        if expanded:
            body.pack(fill=tk.X)
        else:
            body.pack_forget()
        self.accordions[key] = (header, body, title, expanded)

    def _scroll_advanced_panel(self, event: tk.Event) -> None:
        if getattr(event, "num", None) == 4:
            direction = -1
        elif getattr(event, "num", None) == 5:
            direction = 1
        else:
            direction = -1 if getattr(event, "delta", 0) > 0 else 1
        self.advanced_canvas.yview_scroll(direction, "units")

    def _bind_advanced_scroll(self, widget: tk.Misc) -> None:
        widget.bind("<MouseWheel>", self._scroll_advanced_panel, add="+")
        widget.bind("<Button-4>", self._scroll_advanced_panel, add="+")
        widget.bind("<Button-5>", self._scroll_advanced_panel, add="+")
        for child in widget.winfo_children():
            self._bind_advanced_scroll(child)

    def _toggle_advanced_panel(self) -> None:
        if self.root.state() == "normal":
            self.root.geometry(f"{self.root.winfo_width()}x{self.root.winfo_height()}")
        self.advanced_panel_visible = not self.advanced_panel_visible
        if self.advanced_panel_visible:
            self.layout_shell.columnconfigure(2, minsize=310)
            self.advanced_panel.grid()
            self.advanced_toggle_btn.configure(text="Ocultar panel")
        else:
            self.advanced_panel.grid_remove()
            self.layout_shell.columnconfigure(2, minsize=0)
            self.advanced_toggle_btn.configure(text="Mostrar panel")

    def _show_page(self, destination: str) -> None:
        for tooltip in self.help_tooltips:
            tooltip.pinned = False
            tooltip.hide()
        page = self.pages[destination]
        page.tkraise()
        titles = dict(NAV_ITEMS)
        self.page_title_var.set(titles[destination])
        for key, button in self.nav_buttons.items():
            button.configure(style="NavActive.TButton" if key == destination else "Nav.TButton")

    def _refresh_activity_summary(self) -> None:
        if self._closing:
            return
        events = self.activity_feed.recent(len(self.activity_message_vars))
        for index, message_var in enumerate(self.activity_message_vars):
            if index < len(events):
                event = events[index]
                message = event.message.replace("\n", " ")
                message_var.set(message if len(message) <= 82 else f"{message[:79]}...")
                self.activity_time_vars[index].set(event.time_label)
                style = "DangerDot.TLabel" if event.level in {"ERROR", "CRITICAL"} else "InfoDot.TLabel"
                self.activity_dots[index].configure(style=style)
            else:
                message_var.set("Sin actividad reciente" if index == 0 else "")
                self.activity_time_vars[index].set("")
                self.activity_dots[index].configure(style="InfoDot.TLabel")
        self.root.after(1200, self._refresh_activity_summary)

    def _queue_ui_callback(self, callback: Callable[[], None]) -> None:
        if not self._closing:
            self.ui_callback_queue.put(callback)

    def _poll_background_events(self) -> None:
        if self._closing:
            return

        for message in self.log_handler.drain_pending():
            self.log_handler.append(message)

        while True:
            try:
                bridge_status = self.bridge_status_queue.get_nowait()
            except Empty:
                break
            self.bridge_status_var.set(bridge_status)

        while True:
            try:
                callback = self.ui_callback_queue.get_nowait()
            except Empty:
                break
            callback()
            if self._closing:
                return

        if not self._closing:
            self.root.after(200, self._poll_background_events)

    def _clear_log(self) -> None:
        self.log_widget.configure(state="normal")
        self.log_widget.delete("1.0", tk.END)
        self.log_widget.configure(state="disabled")

    def _background_update_check(self) -> None:
        """Check for updates in a background thread."""
        def _target():
            available, version, url = check_for_updates(self.config.github_token)
            if available and url:
                self.latest_update_url = url
                self._queue_ui_callback(
                    lambda: self.update_link_var.set(f"¡Nueva versión disponible: {version}!")
                )
        
        threading.Thread(target=_target, daemon=True).start()

    def _manual_update_check(self) -> None:
        """Manually trigger an update check with a popup."""
        available, version, url = check_for_updates(self.config.github_token)
        if available and url:
            if messagebox.askyesno("Actualización disponible", f"Hay una nueva versión disponible: {version}\n¿Deseas descargarla ahora?"):
                open_release_page(url)
        else:
            messagebox.showinfo("Actualización", "Ya tienes la última versión instalada.")

    def _on_update_click(self) -> None:
        if hasattr(self, 'latest_update_url'):
            open_release_page(self.latest_update_url)

    def _show_changelog(self) -> None:
        """Fetch latest notes from GitHub or fall back to local CHANGELOG.md."""
        def _fetch():
            from .updater import get_latest_release_info
            info = get_latest_release_info(self.config.github_token)
            
            if info and info.get("body"):
                content = info["body"]
                title = f"Novedades - {info.get('tag_name', 'Última Versión')}"
                self._queue_ui_callback(lambda: ReleaseNotesDialog(self.root, title, content))
            else:
                # Fallback to local file
                changelog_path = Path(__file__).parent.parent / "CHANGELOG.md"
                if changelog_path.exists():
                    try:
                        content = changelog_path.read_text(encoding="utf-8")
                        self._queue_ui_callback(
                            lambda: ReleaseNotesDialog(self.root, "Novedades (Local)", content)
                        )
                    except Exception:
                        self._queue_ui_callback(
                            lambda: open_release_page("https://github.com/dancoLgh/moviu/releases")
                        )
                else:
                    self._queue_ui_callback(
                        lambda: open_release_page("https://github.com/dancoLgh/moviu/releases")
                    )
        
        threading.Thread(target=_fetch, daemon=True).start()

    def _create_card(self, parent: ttk.Frame, title: str) -> ttk.Labelframe:
        card = ttk.Labelframe(parent, text=title, style="Card.TLabelframe")
        card.columnconfigure(0, weight=1)
        return card

    def save_settings(self, notify: bool = True, restart_running: bool = True) -> bool:
        server_was_running = bool(self.controller.thread and self.controller.thread.is_alive())
        try:
            host = self.host_var.get()
            port = int(self.port_var.get())
            portal_port = certificate_http_port(port)
            printer_host = self.printer_host_var.get()
            printer_port = int(self.printer_port_var.get())
            
            # Parse printer width
            width_str = self.printer_width_var.get()
            # Extract number if it contains text (e.g. "576 (80mm)")
            match = re.search(r"^\d+", width_str)
            if match:
                printer_width = int(match.group(0))
            else:
                printer_width = int(width_str)

            printer_gamma = int(self.printer_gamma_var.get())
            cut_margin_lines = int(self.cut_margin_lines_var.get())
            if not 0 <= cut_margin_lines <= 20:
                raise ValueError("El margen antes del corte debe estar entre 0 y 20 líneas")
            simulate_printer = self.simulate_var.get()
            auto_start = self.auto_start_var.get()
            usb_bridge_enabled = self.bridge_enabled_var.get()
            usb_bridge_port = int(self.bridge_port_var.get())
            instance_port = getattr(self, "instance_port", 29170)
            if port == instance_port or portal_port == instance_port:
                raise ValueError("El puerto está reservado para el control interno de Moviu")
            if usb_bridge_enabled and usb_bridge_port in {
                port,
                portal_port,
            }:
                raise ValueError("El puerto del puente coincide con un puerto del servidor")
            usb_bridge_printer = self.bridge_printer_var.get()
            usb_bridge_autostart = self.bridge_autostart_var.get()
            github_token = self.github_token_var.get()

            self.config.host = host
            self.config.port = port
            self.config.printer_host = printer_host
            self.config.printer_port = printer_port
            self.config.printer_width = printer_width
            self.config.printer_gamma = printer_gamma
            self.config.cut_margin_lines = cut_margin_lines
            self.config.simulate_printer = simulate_printer
            self.config.auto_start = auto_start
            self.config.usb_bridge_enabled = usb_bridge_enabled
            self.config.usb_bridge_port = usb_bridge_port
            self.config.usb_bridge_printer = usb_bridge_printer
            self.config.usb_bridge_autostart = usb_bridge_autostart
            self.config.github_token = github_token
            save_config(self.config)
            self._apply_autostart(self.config.auto_start, notify=notify)
            if restart_running and server_was_running:
                if not self.stop_server():
                    messagebox.showerror(
                        "Configuración",
                        "La configuración se guardó, pero el servidor anterior no pudo detenerse. "
                        "Cierra Moviu y vuelve a iniciarlo para aplicar los cambios.",
                    )
                    return False
                self.start_server()
            else:
                self._update_endpoint_url()
            if notify:
                detail = (
                    "Configuración guardada. El servidor se está reiniciando."
                    if restart_running and server_was_running
                    else "Configuración guardada"
                )
                messagebox.showinfo("Configuración", detail)
            logging.info("Configuración guardada")
            return True
        except ValueError as exc:
            messagebox.showerror("Error", f"Configuración inválida: {exc}")
            return False

    def regenerate_api_key(self) -> None:
        from secrets import token_hex

        self.config.api_key = token_hex(16)
        self.api_key_var.set(self.config.api_key)
        save_config(self.config)
        messagebox.showinfo("API Key", "Se generó una nueva API key")
        logging.info("Se regeneró la API key")

    def refresh_printers(self, initial: bool = False) -> None:
        self.available_printers = discover_printers()
        self.printer_combo["values"] = self.available_printers

        if not self.bridge_printer_var.get() and self.available_printers:
            self.bridge_printer_var.set(self.available_printers[0])

        if not initial and not self.available_printers:
            messagebox.showwarning(
                "Impresoras",
                "No se encontraron impresoras USB. Este listado solo está disponible en Windows.",
            )
        self.save_settings(notify=False, restart_running=False)

    def start_bridge(self) -> None:
        if not self.bridge_enabled_var.get():
            messagebox.showinfo(
                "Puente TCP → USB",
                "Activa el interruptor 'Habilitar puente' para poder iniciarlo.",
            )
            return

        try:
            port = int(self.bridge_port_var.get())
        except ValueError:
            messagebox.showerror("Puerto inválido", "Introduce un puerto numérico para el puente.")
            return

        printer = self.bridge_printer_var.get()
        if not printer:
            messagebox.showerror(
                "Impresora requerida", "Selecciona la impresora USB que recibirá los trabajos."
            )
            return

        try:
            self.bridge_controller.start(printer, port)
            self._update_bridge_status(f"Escuchando en 0.0.0.0:{port} → {printer}")
            self.save_settings(notify=False, restart_running=False)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Puente", f"No se pudo iniciar el puente: {exc}")
            logging.exception("Error al iniciar el puente TCP → USB")

    def stop_bridge(self) -> None:
        self.bridge_controller.stop()

    def _update_bridge_status(self, text: str) -> None:
        self.bridge_status_queue.put(text)
        logging.info(text)

    def _maybe_autostart_bridge(self) -> None:
        if self.config.usb_bridge_enabled and (
            self.config.usb_bridge_autostart or self.config.auto_start
        ):
            self.root.after(200, self.start_bridge)

    def _maybe_autostart_server(self) -> None:
        if self.config.auto_start:
            self.root.after(200, self.start_server)

    def start_server(self) -> None:
        if not self.save_settings(notify=False, restart_running=False):
            return
        try:
            self.controller.start()
        except Exception as exc:  # noqa: BLE001
            logging.exception("No se pudo preparar el servidor")
            messagebox.showerror("Servidor", f"No se pudo iniciar el servidor:\n{exc}")
            return

        display_host = self.config.host if self.config.host != "0.0.0.0" else get_local_ip()
        self.status_title_var.set("Iniciando servidor")
        self.status_desc_var.set(f"Preparando HTTPS en https://{display_host}:{self.config.port}")
        self.server_badge_var.set("Iniciando")
        self.server_badge_label.configure(style="InfoBadge.TLabel")
        self.main_action_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.full_url_var.set(f"https://{display_host}:{self.config.port}")
        token = object()
        self._server_start_token = token
        deadline = time.monotonic() + 10
        self.root.after(100, lambda: self._check_server_started(token, deadline, display_host))

    def _check_server_started(self, token: object, deadline: float, display_host: str) -> None:
        if self._closing or token is not self._server_start_token:
            return
        if (
            self.controller.server
            and self.controller.server.started
            and self.controller.certificate_server
            and self.controller.certificate_server.started
        ):
            self._server_start_token = None
            self.controller.announce_mdns()
            self.status_title_var.set("Todo listo para imprimir")
            self.status_desc_var.set(
                f"Moviu está conectado en https://{display_host}:{self.config.port}"
            )
            self.server_badge_var.set("Servidor activo")
            self.server_badge_label.configure(style="SuccessBadge.TLabel")
            logging.info("Servidor iniciado con SSL en %s", display_host)
            return

        threads_alive = bool(
            self.controller.thread
            and self.controller.thread.is_alive()
            and self.controller.certificate_thread
            and self.controller.certificate_thread.is_alive()
        )
        if not threads_alive or time.monotonic() >= deadline:
            self._server_start_token = None
            self.controller.stop()
            self._set_server_stopped_state("No se pudo iniciar el servicio HTTPS.")
            logging.error("El servidor no pudo iniciar en %s:%s", self.config.host, self.config.port)
            messagebox.showerror(
                "Servidor",
                "No se pudo iniciar el servidor HTTPS o el portal HTTP. "
                "Revisa ambos puertos y el registro de actividad.",
            )
            return

        self.root.after(100, lambda: self._check_server_started(token, deadline, display_host))

    def stop_server(self) -> bool:
        self._server_start_token = None
        if not self.controller.stop():
            self.status_title_var.set("No se pudo detener el servidor")
            self.status_desc_var.set("Cierra Moviu para finalizar los servicios en ejecución.")
            self.server_badge_var.set("Error al detener")
            self.server_badge_label.configure(style="DangerBadge.TLabel")
            logging.error("El servidor no respondió al apagado")
            return False
        self._set_server_stopped_state(
            "Inicia el servicio para volver a recibir trabajos de impresión."
        )
        logging.info("Servidor detenido")
        return True

    def _set_server_stopped_state(self, description: str) -> None:
        self.status_title_var.set("Servidor detenido")
        self.status_desc_var.set(description)
        self.server_badge_var.set("Servidor detenido")
        self.server_badge_label.configure(style="DangerBadge.TLabel")
        self.main_action_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def _update_endpoint_url(self) -> None:
        display_host = self.config.host if self.config.host != "0.0.0.0" else get_local_ip()
        self.full_url_var.set(f"https://{display_host}:{self.config.port}")
        self.certificate_url_var.set(
            certificate_portal_url(
                self.config.host,
                certificate_http_port(self.config.port),
                display_host,
            )
        )
        self.printer_route_var.set(
            printer_route_label(
                self.config.printer_host,
                self.config.printer_port,
                self.config.usb_bridge_enabled,
                self.config.usb_bridge_port,
            )
        )

    def _active_api_endpoint(self) -> tuple[str, int]:
        server = self.controller.server
        if server:
            return server.config.host, int(server.config.port)
        return self.config.host, self.config.port

    def _copy_api_key(self) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(self.api_key_var.get())
        messagebox.showinfo("Copiado", "API Key copiada al portapapeles")

    def _copy_certificate_url(self) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(self.certificate_url_var.get())
        messagebox.showinfo("Copiado", "URL del portal copiada al portapapeles")

    def _do_exit(self) -> None:
        if self._closing:
            return
        self._closing = True
        self.stop_server()
        self.stop_bridge()
        self.tray.stop()
        self.root.destroy()

    def _minimize_to_background(self) -> None:
        """Send the window to the system tray instead of closing it."""

        try:
            self.root.withdraw()
        except Exception:
            try:
                self.root.iconify()
            except Exception:
                logging.debug("No se pudo ocultar la ventana; se mantendrá visible")
                return

        self.tray.start()
        logging.info("Ventana enviada a la bandeja del sistema; el servidor sigue activo")

    def _restore_from_tray(self) -> None:
        self.tray.stop()
        try:
            self.root.deiconify()
            self.root.state("normal")
            self.root.lift()
            self.root.focus_force()
        except Exception:
            logging.debug("No se pudo restaurar la ventana desde la bandeja")

    def generate_certs(self) -> None:
        restart_server = bool(self.controller.server and self.controller.server.started)
        server_busy = bool(self.controller.thread and self.controller.thread.is_alive())
        if server_busy:
            if not messagebox.askyesno(
                "Reiniciar servidor",
                "Para regenerar los certificados es necesario detener el servidor. ¿Continuar?",
            ):
                return
            self.stop_server()

        cert_hosts = _certificate_hosts(self.config)

        cert_path, key_path = ensure_certificates(
            Path(self.config.ssl_cert_path), 
            Path(self.config.ssl_key_path), 
            cert_hosts,
            force=True
        )
        ca_path = ca_certificate_path(Path(self.config.ssl_cert_path))
        messagebox.showinfo(
            "Certificados",
            f"Certificado de servidor generado en:\n{cert_path}\n\n"
            f"Clave privada del servidor:\n{key_path}\n\n"
            f"Certificado CA (para instalar en tablets/clientes):\n{ca_path}",
        )
        logging.info("Certificados SSL regenerados (CA + servidor)")
        if restart_server:
            self.start_server()

    def export_cert(self) -> None:
        cert_hosts = _certificate_hosts(self.config)

        cert_path, _ = ensure_certificates(
            Path(self.config.ssl_cert_path), Path(self.config.ssl_key_path), cert_hosts
        )
        dest = filedialog.asksaveasfilename(
            defaultextension=".crt",
            filetypes=[("Certificado", "*.crt"), ("PEM", "*.pem"), ("Todos", "*.*")],
            initialfile="moviu_ca.crt",
            initialdir=certificates_folder(),
            title="Exportar certificado CA",
        )
        if dest:
            export_ca_certificate(Path(dest), cert_path)
            messagebox.showinfo(
                "Exportar certificado",
                f"Certificado CA copiado a\n{dest}\n\n"
                "Instálalo en la tablet/cliente para confiar en HTTPS.",
            )
            logging.info("Certificado CA exportado a %s", dest)

    def install_cert_locally(self) -> None:
        cert_hosts = _certificate_hosts(self.config)

        cert_path, _ = ensure_certificates(
            Path(self.config.ssl_cert_path),
            Path(self.config.ssl_key_path),
            cert_hosts,
        )
        ca_path = ca_certificate_path(cert_path)

        if install_certificate_in_system(ca_path):
            messagebox.showinfo(
                "Instalar Certificado",
                "Certificado CA instalado correctamente en el almacén de confianza de Windows.\n\n"
                "Ahora los navegadores de esta PC deberían confiar en la conexión HTTPS."
            )
            logging.info("Certificado CA instalado en el sistema local")
        else:
            messagebox.showerror(
                "Error",
                "No se pudo instalar el certificado CA automáticamente.\n"
                "Intenta ejecutar la aplicación como administrador o exportarlo para instalarlo manualmente."
            )

    def open_certificate_portal(self) -> None:
        if not self.controller.certificate_server or not self.controller.certificate_server.started:
            messagebox.showwarning(
                "Portal de certificado",
                "Inicia el servidor antes de abrir el portal de instalación.",
            )
            return

        ca_path = ca_certificate_path(Path(self.config.ssl_cert_path))
        fingerprint = certificate_sha256_fingerprint(ca_path)
        host, port = self._active_api_endpoint()
        display_host = host if host != "0.0.0.0" else get_local_ip()
        portal_url = certificate_portal_url(host, certificate_http_port(port), display_host)
        logging.info("Abriendo portal público de certificado: %s", portal_url)
        messagebox.showinfo(
            "Huella del certificado Moviu",
            "Comprueba que el portal muestre esta misma huella SHA-256:\n\n"
            f"{fingerprint}",
        )
        webbrowser.open(portal_url)

    def enable_local_network_access(self) -> None:
        running_bridge = self.bridge_controller.server
        running_bridge_port = int(running_bridge.port) if running_bridge else None
        if not self.save_settings(notify=False):
            return

        api_port = self.config.port
        portal_port = certificate_http_port(api_port)
        api_host = self.config.host
        if not is_local_network_bind(api_host):
            messagebox.showerror(
                "Acceso en red local",
                "El servidor está limitado a este equipo. Configura Host API como 0.0.0.0 "
                "y reinicia el servidor antes de habilitar el acceso desde otros dispositivos.",
            )
            return
        bridge_port = running_bridge_port
        if bridge_port is None and self.config.usb_bridge_enabled:
            bridge_port = self.config.usb_bridge_port
        ports = [api_port, portal_port]
        if bridge_port and bridge_port not in ports:
            ports.append(bridge_port)
        port_list = ", ".join(str(port) for port in ports)
        if not messagebox.askyesno(
            "Habilitar acceso en red local",
            "Moviu solicitará permisos de administrador para abrir solo conexiones TCP "
            f"desde la red local hacia los puertos: {port_list}.\n\n¿Deseas continuar?",
        ):
            return

        try:
            result = open_local_network_ports(
                api_port,
                bridge_port,
                certificate_port=portal_port,
            )
        except (NetworkAccessError, ValueError) as exc:
            logging.error("No se pudo habilitar el acceso en la red local: %s", exc)
            messagebox.showerror("Acceso en red local", str(exc))
            return

        if not result.rules_changed:
            logging.info("No hay un firewall activo; no fue necesario crear reglas")
            messagebox.showinfo(
                "Acceso en red local",
                "No hay un firewall activo en el sistema. Moviu ya puede recibir conexiones "
                f"en los puertos TCP {port_list}.",
            )
            return

        logging.info(
            "Acceso local habilitado mediante %s para puertos %s",
            result.firewall,
            port_list,
        )
        messagebox.showinfo(
            "Acceso en red local",
            f"Reglas aplicadas correctamente mediante {result.firewall}.\n\n"
            f"Puertos TCP disponibles para la red local: {port_list}",
        )

    def disable_local_network_access(self) -> None:
        if not messagebox.askyesno(
            "Retirar acceso del firewall",
            "Moviu solicitará permisos de administrador para retirar todas las reglas de "
            "firewall que administra. ¿Deseas continuar?",
        ):
            return
        try:
            result = close_local_network_ports()
        except NetworkAccessError as exc:
            logging.error("No se pudo retirar el acceso del firewall: %s", exc)
            messagebox.showerror("Acceso en red local", str(exc))
            return
        if not result.rules_changed:
            messagebox.showinfo(
                "Acceso en red local",
                "Moviu no tiene reglas de firewall administradas en este equipo.",
            )
            return
        logging.info("Se retiraron las reglas de firewall administradas por Moviu")
        messagebox.showinfo(
            "Acceso en red local",
            "Se retiraron correctamente las reglas de firewall administradas por Moviu.",
        )

    def open_simulations(self) -> None:
        sims = CONFIG_DIR / "simulated_jobs"
        sims.mkdir(parents=True, exist_ok=True)
        logging.info("Abriendo carpeta de simulaciones: %s", sims)
        try:
            if os.name == "nt":
                os.startfile(sims)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", str(sims)], check=False)
            else:
                subprocess.run(["xdg-open", str(sims)], check=False)
        except Exception as exc:  # noqa: BLE001
            logging.error("No se pudo abrir la carpeta de simulaciones: %s", exc)
            messagebox.showerror(
                "Simulaciones",
                f"No se pudo abrir la carpeta de simulaciones:\n{sims}\n\n{exc}",
            )

    def run(self) -> None:
        self.root.mainloop()

    def _setup_logging(self) -> None:
        log_file = certificates_folder() / "app.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )
        self.log_handler = _TextHandler(None, self.activity_feed)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        self.log_handler.setFormatter(formatter)
        logging.getLogger().addHandler(self.log_handler)

    def _setup_theme(self) -> None:
        background = "#07111f"
        sidebar = "#081827"
        topbar = "#091625"
        surface = "#102238"
        advanced = "#0a1929"
        text = "#f4f7fb"
        muted = "#94a4b8"
        blue = "#2d6cdf"
        green = "#32c36c"
        red = "#f25f68"

        self.root.configure(bg=background)
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TFrame", background=background)
        style.configure("App.TFrame", background=background)
        style.configure("Page.TFrame", background=background)
        style.configure("Sidebar.TFrame", background=sidebar)
        style.configure("Topbar.TFrame", background=topbar)
        style.configure("Surface.TFrame", background=surface, relief="flat")
        style.configure("ActivityRow.TFrame", background="#0d1d30")
        style.configure("Advanced.TFrame", background=advanced)
        style.configure("AdvancedBody.TFrame", background=surface)

        style.configure("TLabel", background=background, foreground=text, font=("Segoe UI", 10))
        style.configure("Sidebar.TLabel", background=sidebar, foreground=text)
        style.configure("Brand.TLabel", background=sidebar, foreground=text, font=("Segoe UI Semibold", 18))
        style.configure("BrandMeta.TLabel", background=sidebar, foreground=muted, font=("Segoe UI", 8))
        style.configure("NavSection.TLabel", background=sidebar, foreground="#5f7895", font=("Segoe UI Semibold", 8))
        style.configure("PageTitle.TLabel", background=topbar, foreground=text, font=("Segoe UI Semibold", 16))
        style.configure("Update.TLabel", background=topbar, foreground="#58a6ff", font=("Segoe UI Semibold", 9))
        style.configure("HeroTitle.TLabel", background=surface, foreground=text, font=("Segoe UI Semibold", 20))
        style.configure("CardTitle.TLabel", background=surface, foreground=text, font=("Segoe UI Semibold", 11))
        style.configure("Metric.TLabel", background=surface, foreground=text, font=("Segoe UI Semibold", 19))
        style.configure("BodyStrong.TLabel", background=surface, foreground="#d9e3ef", font=("Segoe UI Semibold", 10))
        style.configure("FieldLabel.TLabel", background=surface, foreground="#c4d0df", font=("Segoe UI", 9))
        style.configure("Muted.TLabel", background=surface, foreground=muted, font=("Segoe UI", 9))
        style.configure("Activity.TLabel", background="#0d1d30", foreground="#d9e3ef", font=("Segoe UI", 9))
        style.configure("Status.TLabel", background=surface, foreground="#58a6ff", font=("Segoe UI", 9))
        style.configure("InfoDot.TLabel", background="#0d1d30", foreground="#58a6ff", font=("Segoe UI Bold", 10))
        style.configure("DangerDot.TLabel", background="#0d1d30", foreground=red, font=("Segoe UI Bold", 10))
        style.configure("InfoBadge.TLabel", background="#12345d", foreground="#82b8ff", font=("Segoe UI Semibold", 9), padding=(8, 4))
        style.configure("SuccessBadge.TLabel", background="#123d2d", foreground="#5cdd8b", font=("Segoe UI Semibold", 9), padding=(8, 4))
        style.configure("DangerBadge.TLabel", background="#44242d", foreground="#ff8992", font=("Segoe UI Semibold", 9), padding=(8, 4))
        style.configure("AdvancedTitle.TLabel", background=advanced, foreground=text, font=("Segoe UI Semibold", 15))
        style.configure("AdvancedMuted.TLabel", background=advanced, foreground=muted, font=("Segoe UI", 8))
        style.configure("AdvancedLabel.TLabel", background=surface, foreground="#c4d0df", font=("Segoe UI", 8))
        style.configure("AdvancedStatus.TLabel", background=surface, foreground="#58a6ff", font=("Segoe UI", 8))

        style.configure(
            "TButton",
            background="#163052",
            foreground="#dce7f5",
            padding=(10, 7),
            borderwidth=0,
            font=("Segoe UI Semibold", 9),
        )
        style.map(
            "TButton",
            background=[("active", "#204674"), ("disabled", "#17263a")],
            foreground=[("disabled", "#60748a")],
        )
        style.configure("Primary.TButton", background=blue, foreground="#ffffff", padding=(14, 9))
        style.map("Primary.TButton", background=[("active", "#3f7ef2"), ("disabled", "#1b3355")])
        style.configure("Secondary.TButton", background="#10233a", foreground="#c9d6e5")
        style.configure("Outline.TButton", background=surface, foreground="#72a8ff", borderwidth=1, relief="solid")
        style.map("Outline.TButton", background=[("active", "#173453")])
        style.configure("Link.TButton", background=surface, foreground="#72a8ff", padding=(6, 3))
        style.map("Link.TButton", background=[("active", surface)], foreground=[("active", "#a4c8ff")])
        style.configure(
            "Help.TButton",
            background="#173453",
            foreground="#a4c8ff",
            padding=(2, 0),
            font=("Segoe UI Semibold", 8),
        )
        style.map("Help.TButton", background=[("active", "#204674")])
        style.configure("Nav.TButton", background=sidebar, foreground="#a6b6c9", anchor="w", padding=(12, 10))
        style.map("Nav.TButton", background=[("active", "#102a46")], foreground=[("active", text)])
        style.configure("NavActive.TButton", background="#173a69", foreground="#ffffff", anchor="w", padding=(12, 10))
        style.map("NavActive.TButton", background=[("active", "#1d4b86")])
        style.configure("Accordion.TButton", background="#10233a", foreground="#dce7f5", anchor="w", padding=(10, 10))
        style.map("Accordion.TButton", background=[("active", "#173553")])

        style.configure(
            "TEntry",
            fieldbackground="#0a1727",
            foreground="#dce7f5",
            insertcolor="#ffffff",
            bordercolor="#2a405b",
            lightcolor="#2a405b",
            darkcolor="#2a405b",
            padding=7,
        )
        style.map("TEntry", fieldbackground=[("readonly", "#0a1727")], foreground=[("readonly", "#aebdd0")])
        style.configure("TCombobox", fieldbackground="#0a1727", background="#163052", foreground="#dce7f5", padding=6)
        style.map("TCombobox", fieldbackground=[("readonly", "#0a1727")], foreground=[("readonly", "#dce7f5")])
        style.configure("TCheckbutton", background=surface, foreground="#c4d0df", font=("Segoe UI", 9))
        style.map("TCheckbutton", background=[("active", surface)], foreground=[("active", text)])
        style.configure("Horizontal.TScale", background=surface, troughcolor="#0a1727")
        style.configure("TSeparator", background="#1d3149")

    def _configure_window_hooks(self) -> None:
        self.root.protocol("WM_DELETE_WINDOW", self._minimize_to_background)

    def _maximize_window(self) -> None:
        """Try platform-specific ways to show the window maximized."""

        try:
            self.root.state("zoomed")  # Windows and many X11 window managers
            return
        except Exception:
            pass

        try:
            self.root.attributes("-zoomed", True)  # Some Linux environments
            return
        except Exception:
            pass

        try:
            width = self.root.winfo_screenwidth()
            height = self.root.winfo_screenheight()
            self.root.geometry(f"{width}x{height}+0+0")
        except Exception:
            logging.debug("No se pudo maximizar la ventana automáticamente")

    def _register_signal_handlers(self) -> None:
        """Allow Ctrl+C/SIGINT to close the app cleanly."""

        def _sigint_handler(_sig: int, _frame: object) -> None:
            self.root.after(0, self._do_exit)

        try:
            signal.signal(signal.SIGINT, _sigint_handler)
        except Exception:
            # Not all platforms allow overriding SIGINT in GUI apps
            logging.debug("SIGINT handler no disponible en esta plataforma")

    def _apply_autostart(self, enabled: bool, notify: bool = True) -> None:
        try:
            configure_autostart(enabled)
        except Exception as exc:  # noqa: BLE001
            logging.error("No se pudo actualizar el autoinicio: %s", exc)
            if notify:
                messagebox.showerror(
                    "Autoinicio",
                    "No se pudo configurar el inicio automático:\n" f"{exc}",
                )
            self.auto_start_var.set(False)
            self.config.auto_start = False
            save_config(self.config)
        else:
            if notify:
                estado = "activado" if enabled else "desactivado"
                logging.info("Autoinicio %s", estado)


class ReleaseNotesDialog(tk.Toplevel):
    """A dialog to display release notes with formatted Markdown support."""
    def __init__(self, parent, title, content):
        super().__init__(parent)
        self.title(title)
        self.geometry("700x600")
        self.configure(bg="#0f172a")
        
        self.transient(parent)
        self.grab_set()
        
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text=title, font=("Segoe UI Bold", 16)).pack(pady=(0, 20))
        
        text_area = tk.Text(
            frame, 
            wrap=tk.WORD, 
            bg="#0f172a", 
            fg="#cbd5e1", 
            font=("Segoe UI", 11),
            relief="flat",
            padx=15,
            pady=15,
            borderwidth=0,
            highlightthickness=0
        )
        
        # Configure tags for Markdown-like formatting
        text_area.tag_configure("h1", font=("Segoe UI Bold", 20), foreground="#f8fafc", spacing1=15, spacing3=10)
        text_area.tag_configure("h2", font=("Segoe UI Bold", 16), foreground="#f8fafc", spacing1=12, spacing3=8)
        text_area.tag_configure("h3", font=("Segoe UI Bold", 13), foreground="#f8fafc", spacing1=10, spacing3=5)
        text_area.tag_configure("bold", font=("Segoe UI Bold", 11), foreground="#f1f5f9")
        text_area.tag_configure("bullet", lmargin1=20, lmargin2=40, spacing1=5)
        
        # Parse and insert content
        for line in content.split('\n'):
            stripped = line.strip()
            if not stripped:
                text_area.insert(tk.END, "\n")
                continue
                
            if line.startswith('# '):
                text_area.insert(tk.END, line[2:] + "\n", "h1")
            elif line.startswith('## '):
                text_area.insert(tk.END, line[3:] + "\n", "h2")
            elif line.startswith('### '):
                text_area.insert(tk.END, line[4:] + "\n", "h3")
            elif stripped.startswith('- ') or stripped.startswith('* '):
                self._insert_formatted(text_area, "  • " + stripped[2:] + "\n", "bullet")
            else:
                self._insert_formatted(text_area, line + "\n")
        
        text_area.configure(state="disabled")
        text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(frame, command=text_area.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_area.configure(yscrollcommand=scrollbar.set)
        
        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Cerrar", command=self.destroy).pack(side=tk.RIGHT, padx=10)

    def _insert_formatted(self, widget, text, extra_tag=None):
        """Helper to insert text and handle inline bold markers (**text**)."""
        import re
        parts = re.split(r'(\*\*.*?\*\*)', text)
        for part in parts:
            if not part: continue
            tags = [extra_tag] if extra_tag else []
            if part.startswith('**') and part.endswith('**'):
                tags.append("bold")
                widget.insert(tk.END, part[2:-2], tuple(tags))
            else:
                widget.insert(tk.END, part, tuple(tags))

class _TextHandler(logging.Handler):
    """Send log records to a Tkinter Text widget."""

    def __init__(self, widget: tk.Text | None, activity_feed: ActivityFeed) -> None:
        super().__init__()
        self.widget = widget
        self.activity_feed = activity_feed
        self.pending: Queue[str] = Queue(maxsize=1000)

    def attach(self, widget: tk.Text) -> None:
        self.widget = widget
        existing = reversed(self.activity_feed.recent(100))
        for event in existing:
            self.append(f"{event.time_label} [{event.level}] {event.message}")
        self.drain_pending()

    def emit(self, record: logging.LogRecord) -> None:
        self.activity_feed.add(record.levelname, record.getMessage(), record.created)
        try:
            self.pending.put_nowait(self.format(record))
        except Full:
            pass

    def drain_pending(self, limit: int = 200) -> list[str]:
        messages: list[str] = []
        for _index in range(limit):
            try:
                messages.append(self.pending.get_nowait())
            except Empty:
                break
        return messages

    def append(self, msg: str) -> None:
        if not self.widget:
            return
        self.widget.configure(state="normal")
        self.widget.insert(tk.END, msg + "\n")
        self.widget.see(tk.END)
        self.widget.configure(state="disabled")


class SystemTray:
    """Lightweight system tray controller to restore or exit the app."""

    def __init__(self, on_show: Callable[[], None], on_exit: Callable[[], None]) -> None:
        self.on_show = on_show
        self.on_exit = on_exit
        self.icon: pystray.Icon | None = None

    def start(self) -> None:
        if self.icon and self.icon.visible:
            return

        image = self._create_image()
        menu = pystray.Menu(
            pystray.MenuItem("Mostrar", self._handle_show),
            pystray.MenuItem("Salir", self._handle_exit),
        )
        self.icon = pystray.Icon("moviu_print_server", image, "Moviu Print Server", menu)
        self.icon.run_detached()

    def stop(self) -> None:
        if self.icon:
            self.icon.stop()
            self.icon = None

    def _handle_show(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self.on_show()

    def _handle_exit(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self.stop()
        self.on_exit()

    def _create_image(self) -> Image.Image:
        return load_app_icon(64)


def _ensure_streams() -> None:
    """Guarantee stdout/stderr exist for uvicorn log setup (e.g., frozen builds)."""

    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")  # type: ignore[assignment]
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")  # type: ignore[assignment]


def main() -> None:
    app = DesktopApp()
    app.run()


if __name__ == "__main__":
    main()

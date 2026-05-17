"""Tkinter desktop shell that manages the local API server."""

from __future__ import annotations

import logging
import os
import re
import signal
import subprocess
import socket
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

import pystray
from PIL import Image, ImageDraw, ImageFont

import uvicorn

from .autostart import configure_autostart
from .certs import (
    ca_certificate_path,
    certificates_folder,
    ensure_certificates,
    export_ca_certificate,
    install_certificate_in_system,
)
from .config import AppConfig, CONFIG_DIR, load_config, save_config, VERSION
from .server import create_api
from .usb_bridge import UsbBridgeController, discover_printers
from .mdns import MoviuServiceAnnouncer, get_local_ip
from .updater import check_for_updates, open_release_page


class ServerController:
    """Manage the uvicorn server on a background thread."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.server: uvicorn.Server | None = None
        self.thread: threading.Thread | None = None
        self.mdns_announcer: MoviuServiceAnnouncer | None = None

    def start(self) -> None:
        if self.server and self.server.started:
            return
        _ensure_streams()
        # Generate certificate for localhost, internal IP and configured host
        cert_hosts = ["localhost", "127.0.0.1", get_local_ip()]
        if self.config.host not in ("0.0.0.0", "127.0.0.1", "localhost"):
            cert_hosts.append(self.config.host)
            
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
        self.server = uvicorn.Server(uvicorn_config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()

        # Start mDNS announcement
        self.mdns_announcer = MoviuServiceAnnouncer(
            port=self.config.port,
            instance_name="Moviu Print Server",
            properties={"api_version": "1.0", "protocol": "https"},
        )
        self.mdns_announcer.start()

    def stop(self) -> None:
        # Stop mDNS announcement
        if self.mdns_announcer:
            self.mdns_announcer.stop()
            self.mdns_announcer = None

        if self.server:
            self.server.should_exit = True
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        self.server = None
        self.thread = None

    def _log_config(self) -> dict:
        log_file = certificates_folder() / "app.log"
        stream = sys.stdout or sys.__stdout__
        if stream is None:
            stream = open(os.devnull, "w", encoding="utf-8")

        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": "logging.Formatter",
                    "fmt": "%(asctime)s [%(levelname)s] %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
                "access": {
                    "()": "logging.Formatter",
                    "fmt": "%(asctime)s [%(levelname)s] %(client_addr)s - \"%(request_line)s\" %(status_code)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": stream,
                },
                "file": {
                    "formatter": "default",
                    "class": "logging.FileHandler",
                    "filename": str(log_file),
                    "mode": "a",
                    "encoding": "utf-8",
                },
                "access": {
                    "formatter": "access",
                    "class": "logging.StreamHandler",
                    "stream": stream,
                },
            },
            "loggers": {
                "uvicorn": {"handlers": ["default", "file"], "level": "INFO", "propagate": False},
                "uvicorn.error": {
                    "handlers": ["default", "file"],
                    "level": "INFO",
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["access", "file"],
                    "level": "INFO",
                    "propagate": False,
                },
            },
        }


class DesktopApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Moviu Print Server")
        self.config = load_config()
        self.controller = ServerController(self.config)
        self.bridge_controller = UsbBridgeController(on_status=self._update_bridge_status)
        _ensure_streams()
        self._setup_logging()
        self._setup_theme()
        self._build_ui()
        self._maximize_window()
        self._configure_window_hooks()
        self._register_signal_handlers()
        self.tray = SystemTray(
            on_show=self._restore_from_tray,
            on_exit=lambda: self.root.after(0, self._do_exit),
        )
        self._check_single_instance()
        self._apply_autostart(self.config.auto_start, notify=False)
        self._maybe_autostart_server()
        self._maybe_autostart_bridge()

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
                            self._restore_from_tray()
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

        # Main Scrollable Container (for smaller screens)
        main_container = ttk.Frame(self.root, style="Card.TFrame")
        main_container.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(main_container, padding=(20, 20, 20, 10), style="Card.TFrame")
        header.pack(fill=tk.X)
        ttk.Label(header, text="Moviu Print Server", style="Headline.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, text=VERSION, style="Subhead.TLabel").pack(side=tk.LEFT, padx=10, pady=(5, 0))

        self.update_link_var = tk.StringVar(value="")
        self.update_label = ttk.Label(header, textvariable=self.update_link_var, cursor="hand2", foreground="#38bdf8", font=("Segoe UI Bold", 9))
        self.update_label.pack(side=tk.LEFT, padx=5, pady=(5, 0))
        self.update_label.bind("<Button-1>", lambda e: self._on_update_click())

        # Dashboard (Aesthetic Status)
        dashboard = ttk.Frame(main_container, padding=20, style="Card.TFrame")
        dashboard.pack(fill=tk.X)
        
        status_card = ttk.Frame(dashboard, padding=30, style="CardInner.TFrame", relief="flat")
        status_card.pack(fill=tk.X)
        
        self.status_title_var = tk.StringVar(value="SERVIDOR APAGADO")
        self.status_desc_var = tk.StringVar(value="La impresora no recibirá trabajos hasta que inicies el servidor.")
        self.status_label = ttk.Label(status_card, textvariable=self.status_title_var, style="StatusStopped.TLabel")
        self.status_label.pack()
        
        ttk.Label(status_card, textvariable=self.status_desc_var, style="Subhead.TLabel").pack(pady=(5, 15))
        
        btn_center = ttk.Frame(status_card, style="CardInner.TFrame")
        btn_center.pack()
        self.main_action_btn = ttk.Button(btn_center, text="INICIAR SERVIDOR", style="Big.TButton", command=self.start_server)
        self.main_action_btn.pack(side=tk.LEFT, padx=10)
        self.stop_btn = ttk.Button(btn_center, text="DETENER", style="Big.TButton", command=self.stop_server, state="disabled")
        self.stop_btn.pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_center, text="NOVEDADES", style="Big.TButton", command=self._show_changelog).pack(side=tk.LEFT, padx=10)

        # Tabs for Advanced Settings
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Tab 1: Info & API
        info_tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(info_tab, text=" Información ")
        
        info_grid = ttk.Frame(info_tab, style="CardInner.TFrame")
        info_grid.pack(fill=tk.X)
        info_grid.columnconfigure(1, weight=1)

        display_host = self.config.host if self.config.host != "0.0.0.0" else get_local_ip()
        self.full_url_var = tk.StringVar(value=f"https://{display_host}:{self.config.port}")
        ttk.Label(info_grid, text="URL del Servidor:", font=("Segoe UI Bold", 10)).grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(info_grid, textvariable=self.full_url_var, state="readonly").grid(row=0, column=1, sticky="ew", padx=10)
        
        ttk.Label(info_grid, text="API Key:", font=("Segoe UI Bold", 10)).grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(info_grid, textvariable=self.api_key_var, state="readonly").grid(row=1, column=1, sticky="ew", padx=10)
        
        api_btns = ttk.Frame(info_tab, style="CardInner.TFrame")
        api_btns.pack(fill=tk.X, pady=10)
        ttk.Button(api_btns, text="Copiar API Key", command=self._copy_api_key).pack(side=tk.LEFT, padx=5)
        ttk.Button(api_btns, text="Regenerar API Key", command=self.regenerate_api_key).pack(side=tk.LEFT, padx=5)
        ttk.Button(api_btns, text="Buscar Actualizaciones", command=self._manual_update_check).pack(side=tk.LEFT, padx=5)

        # Tab 2: Configuración de Impresora
        config_tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(config_tab, text=" Configuración ")
        
        conf_grid = ttk.Frame(config_tab, style="CardInner.TFrame")
        conf_grid.pack(fill=tk.X)
        conf_grid.columnconfigure(1, weight=1)

        ttk.Label(conf_grid, text="Host Impresora").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(conf_grid, textvariable=self.printer_host_var).grid(row=0, column=1, sticky="ew", padx=10)
        
        ttk.Label(conf_grid, text="Puerto Impresora").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(conf_grid, textvariable=self.printer_port_var).grid(row=1, column=1, sticky="ew", padx=10)

        ttk.Label(conf_grid, text="Ancho de Papel").grid(row=2, column=0, sticky="w", pady=5)
        self.width_combo = ttk.Combobox(conf_grid, textvariable=self.printer_width_var, values=["576 (80mm)", "384 (58mm)"], state="readonly")
        self.width_combo.grid(row=2, column=1, sticky="ew", padx=10)

        ttk.Label(conf_grid, text="Oscuridad (Densidad)").grid(row=3, column=0, sticky="w", pady=5)
        ttk.Scale(conf_grid, variable=self.printer_gamma_var, from_=200, to=1000, orient=tk.HORIZONTAL).grid(row=3, column=1, sticky="ew", padx=10)
        ttk.Label(conf_grid, textvariable=self.printer_gamma_str, width=4).grid(row=3, column=2, sticky="w")

        config_check_frame = ttk.Frame(config_tab, style="CardInner.TFrame")
        config_check_frame.pack(fill=tk.X, pady=10)
        ttk.Checkbutton(config_check_frame, text="Simular impresora (modo prueba)", variable=self.simulate_var).pack(anchor="w")
        ttk.Checkbutton(config_check_frame, text="Ejecutar al iniciar Windows", variable=self.auto_start_var).pack(anchor="w")

        ttk.Button(config_tab, text="Guardar Cambios", style="Action.TButton", command=self.save_settings).pack(pady=10)

        # Tab 3: Puente USB
        bridge_tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(bridge_tab, text=" Puente USB ")
        
        ttk.Checkbutton(bridge_tab, text="Habilitar puente TCP → USB", variable=self.bridge_enabled_var).pack(anchor="w", pady=5)
        
        bridge_grid = ttk.Frame(bridge_tab, style="CardInner.TFrame")
        bridge_grid.pack(fill=tk.X, pady=10)
        bridge_grid.columnconfigure(1, weight=1)

        ttk.Label(bridge_grid, text="Impresora USB").grid(row=0, column=0, sticky="w", pady=5)
        self.printer_combo = ttk.Combobox(bridge_grid, textvariable=self.bridge_printer_var, state="readonly")
        self.printer_combo.grid(row=0, column=1, sticky="ew", padx=10)
        ttk.Button(bridge_grid, text="Actualizar", command=self.refresh_printers).grid(row=0, column=2)

        ttk.Label(bridge_grid, text="Puerto TCP").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(bridge_grid, textvariable=self.bridge_port_var).grid(row=1, column=1, sticky="ew", padx=10)

        ttk.Checkbutton(bridge_tab, text="Arrancar puente automáticamente", variable=self.bridge_autostart_var).pack(anchor="w")

        b_btns = ttk.Frame(bridge_tab, style="CardInner.TFrame")
        b_btns.pack(pady=15)
        ttk.Button(b_btns, text="Iniciar Puente", command=self.start_bridge).pack(side=tk.LEFT, padx=5)
        ttk.Button(b_btns, text="Detener Puente", command=self.stop_bridge).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(bridge_tab, textvariable=self.bridge_status_var, style="Status.TLabel").pack()

        # Tab 4: Avanzado (SSL & Tools)
        advanced_tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(advanced_tab, text=" Avanzado ")
        
        adv_grid = ttk.Frame(advanced_tab, style="CardInner.TFrame")
        adv_grid.pack(fill=tk.X)
        adv_grid.columnconfigure(1, weight=1)

        ttk.Label(adv_grid, text="Host API").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(adv_grid, textvariable=self.host_var).grid(row=0, column=1, sticky="ew", padx=10)
        
        ttk.Label(adv_grid, text="Puerto API").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(adv_grid, textvariable=self.port_var).grid(row=1, column=1, sticky="ew", padx=10)

        ttk.Label(adv_grid, text="GitHub Token (Private)").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(adv_grid, textvariable=self.github_token_var, show="*").grid(row=2, column=1, sticky="ew", padx=10)

        tools_frame = ttk.LabelFrame(advanced_tab, text="Herramientas", padding=10)
        tools_frame.pack(fill=tk.X, pady=20)
        
        for text, cmd in [
            ("Generar Certificados SSL", self.generate_certs),
            ("Instalar Certificado en Windows (esta PC)", self.install_cert_locally),
            ("Exportar Certificado CA (.crt)", self.export_cert),
            ("Abrir Carpeta de Simulaciones", self.open_simulations),
        ]:
            ttk.Button(tools_frame, text=text, command=cmd).pack(fill=tk.X, pady=2)

        # Tab 5: Logs
        log_tab = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(log_tab, text=" Logs ")
        
        self.log_widget = tk.Text(
            log_tab,
            height=15,
            state="disabled",
            bg="#0b1220",
            fg="#94a3b8",
            insertbackground="#e2e8f0",
            relief="flat",
            font=("Consolas", 10),
        )
        self.log_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(log_tab, command=self.log_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_widget.configure(yscrollcommand=scrollbar.set)
        self.log_handler.attach(self.log_widget)

        self.refresh_printers(initial=True)
        self.root.after(3000, self._background_update_check)

    def _background_update_check(self) -> None:
        """Check for updates in a background thread."""
        def _target():
            available, version, url = check_for_updates(self.config.github_token)
            if available and url:
                self.latest_update_url = url
                self.root.after(0, lambda: self.update_link_var.set(f"¡Nueva versión disponible: {version}!"))
        
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
                self.root.after(0, lambda: ReleaseNotesDialog(self.root, title, content))
            else:
                # Fallback to local file
                changelog_path = Path(__file__).parent.parent / "CHANGELOG.md"
                if changelog_path.exists():
                    try:
                        content = changelog_path.read_text(encoding="utf-8")
                        self.root.after(0, lambda: ReleaseNotesDialog(self.root, "Novedades (Local)", content))
                    except Exception:
                        self.root.after(0, lambda: open_release_page("https://github.com/dancoLgh/moviu/releases"))
                else:
                    self.root.after(0, lambda: open_release_page("https://github.com/dancoLgh/moviu/releases"))
        
        threading.Thread(target=_fetch, daemon=True).start()

    def _create_card(self, parent: ttk.Frame, title: str) -> ttk.Labelframe:
        card = ttk.Labelframe(parent, text=title, style="Card.TLabelframe")
        card.columnconfigure(0, weight=1)
        return card

    def save_settings(self, notify: bool = True) -> None:
        try:
            self.config.host = self.host_var.get()
            self.config.port = int(self.port_var.get())
            self.config.printer_host = self.printer_host_var.get()
            self.config.printer_port = int(self.printer_port_var.get())
            
            # Parse printer width
            width_str = self.printer_width_var.get()
            # Extract number if it contains text (e.g. "576 (80mm)")
            match = re.search(r"^\d+", width_str)
            if match:
                self.config.printer_width = int(match.group(0))
            else:
                self.config.printer_width = int(width_str)

            self.config.printer_gamma = int(self.printer_gamma_var.get())
            self.config.simulate_printer = self.simulate_var.get()
            self.config.auto_start = self.auto_start_var.get()
            self.config.usb_bridge_enabled = self.bridge_enabled_var.get()
            self.config.usb_bridge_port = int(self.bridge_port_var.get())
            self.config.usb_bridge_printer = self.bridge_printer_var.get()
            self.config.usb_bridge_autostart = self.bridge_autostart_var.get()
            self.config.github_token = self.github_token_var.get()
            save_config(self.config)
            self._apply_autostart(self.config.auto_start, notify=notify)
            if notify:
                messagebox.showinfo("Configuración", "Configuración guardada")
            logging.info("Configuración guardada")
        except ValueError:
            messagebox.showerror("Error", "Puerto inválido")

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
        self.save_settings(notify=False)

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
            self.save_settings(notify=False)
        except OSError as exc:
            messagebox.showerror("Puente", f"No se pudo iniciar el puente: {exc}")
            logging.exception("Error al iniciar el puente TCP → USB")

    def stop_bridge(self) -> None:
        self.bridge_controller.stop()

    def _update_bridge_status(self, text: str) -> None:
        self.bridge_status_var.set(text)
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
        self.save_settings(notify=False)
        self.controller.start()
        display_host = self.config.host if self.config.host != "0.0.0.0" else get_local_ip()
        self.status_title_var.set("SERVIDOR ACTIVO")
        self.status_desc_var.set(f"Recibiendo trabajos en https://{display_host}:{self.config.port}")
        self.status_label.configure(style="StatusRunning.TLabel")
        self.main_action_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.full_url_var.set(f"https://{display_host}:{self.config.port}")
        logging.info("Servidor iniciado con SSL en %s", display_host)

    def stop_server(self) -> None:
        self.controller.stop()
        self.status_title_var.set("SERVIDOR APAGADO")
        self.status_desc_var.set("La impresora no recibirá trabajos hasta que inicies el servidor.")
        self.status_label.configure(style="StatusStopped.TLabel")
        self.main_action_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        logging.info("Servidor detenido")

    def _copy_api_key(self) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(self.api_key_var.get())
        messagebox.showinfo("Copiado", "API Key copiada al portapapeles")

    def _do_exit(self) -> None:
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
        def _show() -> None:
            self.tray.stop()
            try:
                self.root.deiconify()
                self.root.state("normal")
                self.root.lift()
                self.root.focus_force()
            except Exception:
                logging.debug("No se pudo restaurar la ventana desde la bandeja")

        self.root.after(0, _show)

    def generate_certs(self) -> None:
        cert_hosts = ["localhost", "127.0.0.1", get_local_ip()]
        if self.config.host not in ("0.0.0.0", "127.0.0.1", "localhost"):
            cert_hosts.append(self.config.host)

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

    def export_cert(self) -> None:
        cert_hosts = ["localhost", "127.0.0.1", get_local_ip()]
        if self.config.host not in ("0.0.0.0", "127.0.0.1", "localhost"):
            cert_hosts.append(self.config.host)

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
        cert_hosts = ["localhost", "127.0.0.1", get_local_ip()]
        if self.config.host not in ("0.0.0.0", "127.0.0.1", "localhost"):
            cert_hosts.append(self.config.host)

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
        self.log_handler = _TextHandler(None)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        self.log_handler.setFormatter(formatter)
        logging.getLogger().addHandler(self.log_handler)

    def _setup_theme(self) -> None:
        self.root.configure(bg="#0f172a")
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TFrame", background="#0f172a")
        style.configure("Card.TFrame", background="#0f172a")
        style.configure("CardInner.TFrame", background="#0f172a")
        style.configure("TLabel", background="#0f172a", foreground="#e2e8f0")
        style.configure("Headline.TLabel", font=("Segoe UI Semibold", 18), foreground="#f8fafc")
        style.configure("Subhead.TLabel", font=("Segoe UI", 11), foreground="#94a3b8")
        style.configure("Status.TLabel", foreground="#38bdf8", font=("Segoe UI", 11))
        style.configure("StatusRunning.TLabel", foreground="#22c55e", font=("Segoe UI Bold", 24))
        style.configure("StatusStopped.TLabel", foreground="#ef4444", font=("Segoe UI Bold", 24))
        
        style.configure(
            "TButton",
            background="#1d4ed8",
            foreground="#e2e8f0",
            padding=6,
        )
        style.map(
            "TButton",
            background=[("active", "#2563eb")],
            relief=[("pressed", "groove")],
        )
        
        style.configure("Action.TButton", font=("Segoe UI Semibold", 10), padding=10)
        style.configure("Big.TButton", font=("Segoe UI Bold", 12), padding=12)

        style.configure("Card.TLabelframe", background="#0f172a", foreground="#cbd5e1")
        style.configure(
            "Card.TLabelframe.Label",
            background="#0f172a",
            foreground="#cbd5e1",
            font=("Segoe UI Semibold", 11),
        )
        
        # Notebook styling
        style.configure("TNotebook", background="#0f172a", borderwidth=0)
        style.configure("TNotebook.Tab", background="#1e293b", foreground="#94a3b8", padding=[12, 4])
        style.map("TNotebook.Tab", 
                  background=[("selected", "#0f172a")],
                  foreground=[("selected", "#38bdf8")])

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

    def __init__(self, widget: tk.Text | None) -> None:
        super().__init__()
        self.widget = widget

    def attach(self, widget: tk.Text) -> None:
        self.widget = widget

    def emit(self, record: logging.LogRecord) -> None:
        if not self.widget:
            return
        msg = self.format(record)
        self.widget.after(0, self._append, msg)

    def _append(self, msg: str) -> None:
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
        size = 64
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((6, 6, size - 6, size - 6), radius=12, fill=(24, 79, 254, 255))
        font = ImageFont.load_default()
        text = "M"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        draw.text(((size - text_w) / 2, (size - text_h) / 2), text, font=font, fill="white")
        return image


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

"""Tkinter desktop shell that manages the local API server."""

from __future__ import annotations

import logging
import os
import re
import signal
import subprocess
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
from .certs import certificates_folder, ensure_certificates, export_certificate
from .config import AppConfig, CONFIG_DIR, load_config, save_config
from .server import create_api
from .usb_bridge import UsbBridgeController, discover_printers


class ServerController:
    """Manage the uvicorn server on a background thread."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.server: uvicorn.Server | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.server and self.server.started:
            return
        _ensure_streams()
        app = create_api(self.config)
        cert_path, key_path = ensure_certificates(
            Path(self.config.ssl_cert_path), Path(self.config.ssl_key_path), self.config.host
        )
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

    def stop(self) -> None:
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
        self._apply_autostart(self.config.auto_start, notify=False)
        self._maybe_autostart_bridge()

    def _build_ui(self) -> None:
        self.host_var = tk.StringVar(value=self.config.host)
        self.port_var = tk.StringVar(value=str(self.config.port))
        self.printer_host_var = tk.StringVar(value=self.config.printer_host)
        self.printer_port_var = tk.StringVar(value=str(self.config.printer_port))
        self.printer_width_var = tk.StringVar(value=str(self.config.printer_width))
        self.api_key_var = tk.StringVar(value=self.config.api_key)
        self.simulate_var = tk.BooleanVar(value=self.config.simulate_printer)
        self.auto_start_var = tk.BooleanVar(value=self.config.auto_start)

        self.bridge_enabled_var = tk.BooleanVar(value=self.config.usb_bridge_enabled)
        self.bridge_port_var = tk.StringVar(value=str(self.config.usb_bridge_port))
        self.bridge_printer_var = tk.StringVar(value=self.config.usb_bridge_printer)
        self.bridge_autostart_var = tk.BooleanVar(value=self.config.usb_bridge_autostart)
        self.bridge_status_var = tk.StringVar(value="Puente detenido")
        self.available_printers: list[str] = []

        wrapper = ttk.Frame(self.root, padding=16, style="Card.TFrame")
        wrapper.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(wrapper, style="Card.TFrame")
        header.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(header, text="Moviu Print Server", style="Headline.TLabel").pack(
            side=tk.LEFT
        )
        ttk.Label(
            header,
            text="API segura + Puente TCP → USB en un solo lugar",
            style="Subhead.TLabel",
        ).pack(side=tk.LEFT, padx=10)

        content = ttk.Frame(wrapper, style="Card.TFrame")
        content.pack(fill=tk.BOTH, expand=True)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)

        server_card = self._create_card(content, "Servidor HTTPS / API")
        server_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        bridge_card = self._create_card(content, "Puente TCP → Impresora USB")
        bridge_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # Server form
        form = ttk.Frame(server_card, style="CardInner.TFrame")
        form.grid(row=0, column=0, sticky="nsew")
        form.columnconfigure(1, weight=1)

        for idx, (label, var) in enumerate(
            (
                ("Host servidor", self.host_var),
                ("Puerto servidor", self.port_var),
                ("Host impresora", self.printer_host_var),
                ("Puerto impresora", self.printer_port_var),
            )
        ):
            ttk.Label(form, text=label).grid(row=idx, column=0, sticky="w", pady=2)
            ttk.Entry(form, textvariable=var).grid(
                row=idx, column=1, sticky="ew", pady=2
            )

        ttk.Label(form, text="Ancho (dots)").grid(row=4, column=0, sticky="w", pady=2)
        self.width_combo = ttk.Combobox(
            form,
            textvariable=self.printer_width_var,
            values=["576 (80mm)", "384 (58mm)"],
        )
        self.width_combo.grid(row=4, column=1, sticky="ew", pady=2)

        ttk.Label(form, text="API Key").grid(row=5, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.api_key_var, state="readonly").grid(
            row=5, column=1, sticky="ew", pady=2
        )

        ttk.Checkbutton(
            form,
            text="Simular impresora (solo desarrollo)",
            variable=self.simulate_var,
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 2))

        ttk.Checkbutton(
            form,
            text="Ejecutar al iniciar el sistema",
            variable=self.auto_start_var,
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=2)

        btn_frame = ttk.Frame(form, style="CardInner.TFrame")
        btn_frame.grid(row=8, column=0, columnspan=2, pady=(10, 4))
        for text, command in (
            ("Guardar", self.save_settings),
            ("Regenerar API Key", self.regenerate_api_key),
            ("Iniciar", self.start_server),
            ("Detener", self.stop_server),
            ("Generar certificados", self.generate_certs),
            ("Exportar certificado", self.export_cert),
            ("Abrir simulaciones", self.open_simulations),
        ):
            ttk.Button(btn_frame, text=text, command=command).pack(
                side=tk.LEFT, padx=4
            )

        self.status_var = tk.StringVar(value="Servidor detenido")
        ttk.Label(form, textvariable=self.status_var, style="Status.TLabel").grid(
            row=9, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )

        # Bridge form
        bridge_form = ttk.Frame(bridge_card, style="CardInner.TFrame")
        bridge_form.grid(row=0, column=0, sticky="nsew")
        bridge_form.columnconfigure(1, weight=1)

        ttk.Checkbutton(
            bridge_form,
            text="Habilitar puente TCP → USB",
            variable=self.bridge_enabled_var,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=2)

        ttk.Label(bridge_form, text="Impresora USB").grid(
            row=1, column=0, sticky="w", pady=2
        )
        self.printer_combo = ttk.Combobox(
            bridge_form,
            textvariable=self.bridge_printer_var,
            values=self.available_printers,
            state="readonly",
        )
        self.printer_combo.grid(row=1, column=1, sticky="ew", pady=2)
        ttk.Button(bridge_form, text="Actualizar", command=self.refresh_printers).grid(
            row=1, column=2, sticky="ew", padx=(6, 0)
        )

        ttk.Label(bridge_form, text="Puerto TCP").grid(
            row=2, column=0, sticky="w", pady=2
        )
        ttk.Entry(bridge_form, textvariable=self.bridge_port_var).grid(
            row=2, column=1, sticky="ew", pady=2
        )

        ttk.Checkbutton(
            bridge_form,
            text="Arrancar puente automáticamente",
            variable=self.bridge_autostart_var,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=2)

        bridge_buttons = ttk.Frame(bridge_form, style="CardInner.TFrame")
        bridge_buttons.grid(row=4, column=0, columnspan=3, pady=(8, 4))
        ttk.Button(bridge_buttons, text="Iniciar puente", command=self.start_bridge).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(bridge_buttons, text="Detener puente", command=self.stop_bridge).pack(
            side=tk.LEFT, padx=4
        )

        ttk.Label(
            bridge_form, textvariable=self.bridge_status_var, style="Status.TLabel"
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(4, 0))

        # Log section
        log_frame = ttk.LabelFrame(wrapper, text="Logs", style="Card.TLabelframe")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log_widget = tk.Text(
            log_frame,
            height=12,
            state="disabled",
            bg="#0b1220",
            fg="#e2e8f0",
            insertbackground="#e2e8f0",
            relief="flat",
            font=("Segoe UI", 10),
        )
        self.log_widget.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_widget.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_widget.configure(yscrollcommand=scrollbar.set)
        self.log_handler.attach(self.log_widget)
        self.refresh_printers(initial=True)

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

            self.config.simulate_printer = self.simulate_var.get()
            self.config.auto_start = self.auto_start_var.get()
            self.config.usb_bridge_enabled = self.bridge_enabled_var.get()
            self.config.usb_bridge_port = int(self.bridge_port_var.get())
            self.config.usb_bridge_printer = self.bridge_printer_var.get()
            self.config.usb_bridge_autostart = self.bridge_autostart_var.get()
            save_config(self.config)
            self._apply_autostart(self.config.auto_start)
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
        if self.config.usb_bridge_enabled and self.config.usb_bridge_autostart:
            self.root.after(200, self.start_bridge)

    def start_server(self) -> None:
        self.save_settings()
        self.controller.start()
        protocol = "https"
        self.status_var.set(
            f"Servidor escuchando en {protocol}://{self.config.host}:{self.config.port}"
        )
        logging.info("Servidor iniciado con SSL")

    def stop_server(self) -> None:
        self.controller.stop()
        self.status_var.set("Servidor detenido")
        logging.info("Servidor detenido")

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
        cert_path, key_path = ensure_certificates(
            Path(self.config.ssl_cert_path), Path(self.config.ssl_key_path), self.config.host
        )
        messagebox.showinfo(
            "Certificados",
            f"Certificado generado en:\n{cert_path}\n\nClave privada:\n{key_path}",
        )
        logging.info("Certificados SSL generados")

    def export_cert(self) -> None:
        cert_path, _ = ensure_certificates(
            Path(self.config.ssl_cert_path), Path(self.config.ssl_key_path), self.config.host
        )
        dest = filedialog.asksaveasfilename(
            defaultextension=".crt",
            filetypes=[("Certificado", "*.crt"), ("PEM", "*.pem"), ("Todos", "*.*")],
            initialfile="moviu_cert.crt",
            initialdir=certificates_folder(),
            title="Exportar certificado público",
        )
        if dest:
            export_certificate(Path(dest), cert_path)
            messagebox.showinfo("Exportar certificado", f"Certificado copiado a\n{dest}")
            logging.info("Certificado exportado a %s", dest)

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
        style.configure("Status.TLabel", foreground="#38bdf8")
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
        style.configure("Card.TLabelframe", background="#0f172a", foreground="#cbd5e1")
        style.configure(
            "Card.TLabelframe.Label",
            background="#0f172a",
            foreground="#cbd5e1",
            font=("Segoe UI Semibold", 11),
        )

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

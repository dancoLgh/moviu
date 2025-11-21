"""Tkinter desktop shell that manages the local API server."""

from __future__ import annotations

import logging
import os
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
from .tcp_usb_bridge import BridgeConfig, TcpUsbBridge


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
        self.bridge = TcpUsbBridge(
            BridgeConfig(
                host=self.config.host,
                port=self.config.usb_bridge_port,
                device_path=Path(self.config.usb_device_path),
            )
        )
        _ensure_streams()
        self._setup_logging()
        self._build_ui()
        self._maximize_window()
        self._configure_window_hooks()
        self._register_signal_handlers()
        self.tray = SystemTray(
            on_show=self._restore_from_tray,
            on_exit=lambda: self.root.after(0, self._do_exit),
        )
        self._apply_autostart(self.config.auto_start, notify=False)

    def _build_ui(self) -> None:
        self._apply_style()
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        self.host_var = tk.StringVar(value=self.config.host)
        self.port_var = tk.StringVar(value=str(self.config.port))
        self.printer_host_var = tk.StringVar(value=self.config.printer_host)
        self.printer_port_var = tk.StringVar(value=str(self.config.printer_port))
        self.api_key_var = tk.StringVar(value=self.config.api_key)
        self.simulate_var = tk.BooleanVar(value=self.config.simulate_printer)
        self.auto_start_var = tk.BooleanVar(value=self.config.auto_start)
        self.usb_bridge_enabled_var = tk.BooleanVar(value=self.config.usb_bridge_enabled)
        self.usb_bridge_port_var = tk.StringVar(value=str(self.config.usb_bridge_port))
        self.usb_device_path_var = tk.StringVar(value=self.config.usb_device_path)

        header = ttk.Frame(frame)
        header.pack(fill=tk.X, pady=(0, 12))
        title = ttk.Label(
            header,
            text="Moviu Print Server",
            style="Title.TLabel",
        )
        title.pack(side=tk.LEFT)
        subtitle = ttk.Label(
            header,
            text="API segura + Bridge TCP→USB en una sola app",
            style="SubTitle.TLabel",
        )
        subtitle.pack(side=tk.LEFT, padx=(10, 0))

        sections = ttk.Frame(frame)
        sections.pack(fill=tk.BOTH, expand=True)
        sections.columnconfigure(0, weight=1)
        sections.columnconfigure(1, weight=1)

        api_frame = self._build_section(sections, "Servidor HTTPS")
        api_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._add_labeled_entry(api_frame, "Host servidor", self.host_var, 0)
        self._add_labeled_entry(api_frame, "Puerto servidor", self.port_var, 1)
        self._add_labeled_entry(api_frame, "API Key", self.api_key_var, 2, readonly=True)
        ttk.Button(api_frame, text="Regenerar API Key", command=self.regenerate_api_key).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0)
        )
        ttk.Checkbutton(
            api_frame,
            text="Simular impresora (solo desarrollo)",
            variable=self.simulate_var,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Checkbutton(
            api_frame,
            text="Ejecutar al iniciar el sistema",
            variable=self.auto_start_var,
        ).grid(row=5, column=0, columnspan=2, sticky="w")

        printer_frame = self._build_section(sections, "Impresora TCP")
        printer_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self._add_labeled_entry(printer_frame, "Host impresora", self.printer_host_var, 0)
        self._add_labeled_entry(printer_frame, "Puerto impresora", self.printer_port_var, 1)
        ttk.Label(
            printer_frame,
            text="Estos valores son el destino por defecto; cada petición puede enviar sus propios host/puerto.",
            style="Hint.TLabel",
            wraplength=280,
            justify="left",
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))

        bridge_frame = self._build_section(frame, "Bridge TCP → USB")
        bridge_frame.pack(fill=tk.X, pady=(12, 0))
        ttk.Checkbutton(
            bridge_frame,
            text="Activar bridge TCP→USB integrado",
            variable=self.usb_bridge_enabled_var,
            command=self._sync_bridge,
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        self._add_labeled_entry(bridge_frame, "Puerto bridge", self.usb_bridge_port_var, 1)
        self._add_labeled_entry(bridge_frame, "Ruta dispositivo USB", self.usb_device_path_var, 2)
        ttk.Label(
            bridge_frame,
            text="Ejemplo: /dev/usb/lp0 en Linux o LPT1 en Windows con drivers instalados.",
            style="Hint.TLabel",
            wraplength=500,
            justify="left",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))

        actions = ttk.Frame(frame)
        actions.pack(fill=tk.X, pady=12)
        ttk.Button(actions, text="Guardar", command=self.save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions, text="Iniciar", command=self.start_server).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions, text="Detener", command=self.stop_server).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions, text="Generar certificados", command=self.generate_certs).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(actions, text="Exportar certificado", command=self.export_cert).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(actions, text="Abrir simulaciones", command=self.open_simulations).pack(
            side=tk.LEFT, padx=5
        )

        status_frame = ttk.Frame(frame)
        status_frame.pack(fill=tk.X)
        self.status_var = tk.StringVar(value="Servidor detenido")
        self.bridge_status_var = tk.StringVar(value="Bridge desactivado")
        ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel").pack(
            anchor="w"
        )
        ttk.Label(status_frame, textvariable=self.bridge_status_var, style="Status.TLabel").pack(
            anchor="w"
        )

        log_frame = self._build_section(frame, "Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_widget = tk.Text(log_frame, height=10, state="disabled", bg="#0f172a", fg="#e2e8f0")
        self.log_widget.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_widget.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_widget.configure(yscrollcommand=scrollbar.set)
        self.log_handler.attach(self.log_widget)

    def _apply_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background="#0b1220")
        style.configure("TLabel", background="#0b1220", foreground="#e2e8f0")
        style.configure("Hint.TLabel", foreground="#94a3b8", background="#0b1220")
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), foreground="#38bdf8")
        style.configure("SubTitle.TLabel", font=("Segoe UI", 10), foreground="#cbd5e1")
        style.configure("Status.TLabel", foreground="#38bdf8", background="#0b1220")
        style.configure("TButton", padding=6)
        style.configure("Section.TLabelframe", background="#111827", borderwidth=1)
        style.configure("Section.TLabelframe.Label", background="#111827", foreground="#a5b4fc")
        style.configure("TCheckbutton", background="#0b1220", foreground="#e2e8f0")
        self.root.configure(bg="#0b1220")

    def _build_section(self, parent: ttk.Frame, title: str) -> ttk.LabelFrame:
        section = ttk.LabelFrame(parent, text=title, padding=12, style="Section.TLabelframe")
        section.columnconfigure(1, weight=1)
        return section

    def _add_labeled_entry(
        self, parent: ttk.Frame, label: str, var: tk.Variable, row: int, readonly: bool = False
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        entry_state = "readonly" if readonly else "normal"
        entry = ttk.Entry(parent, textvariable=var, state=entry_state)
        entry.grid(row=row, column=1, sticky="ew", pady=2)
        if readonly:
            entry.configure(cursor="arrow")

    def save_settings(self, notify: bool = True) -> None:
        try:
            self.config.host = self.host_var.get()
            self.config.port = int(self.port_var.get())
            self.config.printer_host = self.printer_host_var.get()
            self.config.printer_port = int(self.printer_port_var.get())
            self.config.simulate_printer = self.simulate_var.get()
            self.config.auto_start = self.auto_start_var.get()
            self.config.usb_bridge_enabled = self.usb_bridge_enabled_var.get()
            self.config.usb_bridge_port = int(self.usb_bridge_port_var.get())
            self.config.usb_device_path = self.usb_device_path_var.get()
            save_config(self.config)
            self._apply_autostart(self.config.auto_start)
            self._sync_bridge()
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
        self.bridge.stop()
        self.bridge_status_var.set("Bridge desactivado")

    def _do_exit(self) -> None:
        self.stop_server()
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

    def _sync_bridge(self) -> None:
        try:
            bridge_port = int(self.usb_bridge_port_var.get())
        except ValueError:
            self.bridge_status_var.set("Bridge: puerto inválido")
            return

        self.bridge.update_config(
            self.host_var.get(), bridge_port, self.usb_device_path_var.get()
        )
        if self.usb_bridge_enabled_var.get():
            self.bridge.restart(enabled=True)
            self.bridge_status_var.set(
                f"Bridge TCP→USB activo en tcp://{self.host_var.get()}:{bridge_port} → {self.usb_device_path_var.get()}"
            )
        else:
            self.bridge.stop()
            self.bridge_status_var.set("Bridge desactivado")


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

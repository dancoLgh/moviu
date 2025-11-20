"""Tkinter desktop shell that manages the local API server."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import uvicorn

from .certs import certificates_folder, ensure_certificates, export_certificate
from .config import AppConfig, CONFIG_DIR, load_config, save_config
from .server import create_api


class ServerController:
    """Manage the uvicorn server on a background thread."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.server: uvicorn.Server | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.server and self.server.started:
            return
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


class DesktopApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Moviu Print Server")
        self.config = load_config()
        self.controller = ServerController(self.config)
        self._setup_logging()
        self._build_ui()
        if self.config.auto_start:
            self.start_server(auto=True)

    def _build_ui(self) -> None:
        frame = tk.Frame(self.root, padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        self.host_var = tk.StringVar(value=self.config.host)
        self.port_var = tk.StringVar(value=str(self.config.port))
        self.printer_host_var = tk.StringVar(value=self.config.printer_host)
        self.printer_port_var = tk.StringVar(value=str(self.config.printer_port))
        self.api_key_var = tk.StringVar(value=self.config.api_key)
        self.simulate_var = tk.BooleanVar(value=self.config.simulate_printer)
        self.auto_start_var = tk.BooleanVar(value=self.config.auto_start)

        row = 0
        for label, var in (
            ("Host servidor", self.host_var),
            ("Puerto servidor", self.port_var),
            ("Printer host", self.printer_host_var),
            ("Printer puerto", self.printer_port_var),
        ):
            tk.Label(frame, text=label).grid(row=row, column=0, sticky="w")
            tk.Entry(frame, textvariable=var).grid(row=row, column=1, sticky="ew")
            row += 1

        frame.columnconfigure(1, weight=1)

        tk.Label(frame, text="API Key").grid(row=row, column=0, sticky="w")
        tk.Entry(frame, textvariable=self.api_key_var, state="readonly").grid(
            row=row, column=1, sticky="ew"
        )
        row += 1

        tk.Checkbutton(
            frame,
            text="Simular impresora (solo desarrollo)",
            variable=self.simulate_var,
            onvalue=True,
            offvalue=False,
        ).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        tk.Checkbutton(
            frame,
            text="Iniciar servidor automáticamente", 
            variable=self.auto_start_var,
            onvalue=True,
            offvalue=False,
        ).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        btn_frame = tk.Frame(frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="Guardar", command=self.save_settings).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Regenerar API Key", command=self.regenerate_api_key).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(btn_frame, text="Iniciar", command=self.start_server).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Detener", command=self.stop_server).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Generar certificados", command=self.generate_certs).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(btn_frame, text="Exportar certificado", command=self.export_cert).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(btn_frame, text="Abrir simulaciones", command=self.open_simulations).pack(
            side=tk.LEFT, padx=5
        )

        self.status_var = tk.StringVar(value="Servidor detenido")
        tk.Label(frame, textvariable=self.status_var, fg="blue").grid(
            row=row + 1, column=0, columnspan=2, sticky="w"
        )

        log_frame = tk.LabelFrame(frame, text="Log")
        log_frame.grid(row=row + 2, column=0, columnspan=2, sticky="nsew", pady=10)
        frame.rowconfigure(row + 2, weight=1)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log_widget = tk.Text(log_frame, height=10, state="disabled")
        self.log_widget.grid(row=0, column=0, sticky="nsew")
        scrollbar = tk.Scrollbar(log_frame, command=self.log_widget.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_widget.configure(yscrollcommand=scrollbar.set)
        self.log_handler.attach(self.log_widget)

    def save_settings(self, notify: bool = True) -> None:
        try:
            self.config.host = self.host_var.get()
            self.config.port = int(self.port_var.get())
            self.config.printer_host = self.printer_host_var.get()
            self.config.printer_port = int(self.printer_port_var.get())
            self.config.simulate_printer = self.simulate_var.get()
            self.config.auto_start = self.auto_start_var.get()
            save_config(self.config)
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

    def start_server(self, auto: bool = False) -> None:
        self.save_settings(notify=not auto)
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


def main() -> None:
    app = DesktopApp()
    app.run()


if __name__ == "__main__":
    main()

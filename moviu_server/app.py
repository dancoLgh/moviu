"""Tkinter desktop shell that manages the local API server."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox

import uvicorn

from .config import AppConfig, load_config, save_config
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
        uvicorn_config = uvicorn.Config(
            app,
            host=self.config.host,
            port=self.config.port,
            log_level="info",
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
        self._build_ui()

    def _build_ui(self) -> None:
        frame = tk.Frame(self.root, padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        self.host_var = tk.StringVar(value=self.config.host)
        self.port_var = tk.StringVar(value=str(self.config.port))
        self.printer_host_var = tk.StringVar(value=self.config.printer_host)
        self.printer_port_var = tk.StringVar(value=str(self.config.printer_port))
        self.api_key_var = tk.StringVar(value=self.config.api_key)

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

        btn_frame = tk.Frame(frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="Guardar", command=self.save_settings).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Regenerar API Key", command=self.regenerate_api_key).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(btn_frame, text="Iniciar", command=self.start_server).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Detener", command=self.stop_server).pack(side=tk.LEFT, padx=5)

        self.status_var = tk.StringVar(value="Servidor detenido")
        tk.Label(frame, textvariable=self.status_var, fg="blue").grid(
            row=row + 1, column=0, columnspan=2, sticky="w"
        )

    def save_settings(self) -> None:
        try:
            self.config.host = self.host_var.get()
            self.config.port = int(self.port_var.get())
            self.config.printer_host = self.printer_host_var.get()
            self.config.printer_port = int(self.printer_port_var.get())
            save_config(self.config)
            messagebox.showinfo("Configuración", "Configuración guardada")
        except ValueError:
            messagebox.showerror("Error", "Puerto inválido")

    def regenerate_api_key(self) -> None:
        from secrets import token_hex

        self.config.api_key = token_hex(16)
        self.api_key_var.set(self.config.api_key)
        save_config(self.config)
        messagebox.showinfo("API Key", "Se generó una nueva API key")

    def start_server(self) -> None:
        self.save_settings()
        self.controller.start()
        self.status_var.set(
            f"Servidor escuchando en http://{self.config.host}:{self.config.port}"
        )

    def stop_server(self) -> None:
        self.controller.stop()
        self.status_var.set("Servidor detenido")

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = DesktopApp()
    app.run()


if __name__ == "__main__":
    main()

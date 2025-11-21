import logging
import tkinter as tk
from tkinter import messagebox

from .config import AppConfig
from .printer_bridge import PrinterServer, list_printers

logger = logging.getLogger(__name__)


class PrinterBridgeApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("TCP → USB Printer")
        self.root.geometry("520x260")
        self.config = AppConfig.load()

        self._server: PrinterServer | None = None
        self._status_var = tk.StringVar(value="Servidor detenido")
        self._port_var = tk.StringVar(value=str(self.config.port))
        self._autostart_var = tk.BooleanVar(value=self.config.autostart)

        self._printer_var = tk.StringVar(value=self.config.printer_name)
        self._printer_options = list_printers()
        if self._printer_options and not self._printer_var.get():
            self._printer_var.set(self._printer_options[0])

        self._build_ui()

        if self.config.autostart and self._printer_var.get():
            self.start_server(auto=True)
            self.root.after(500, self.root.iconify)

    def _build_ui(self) -> None:
        padding = {"padx": 10, "pady": 5}

        tk.Label(self.root, text="Impresora USB").grid(row=0, column=0, sticky="w", **padding)
        self.printer_menu = tk.OptionMenu(self.root, self._printer_var, *self._printer_options)
        self.printer_menu.grid(row=0, column=1, sticky="ew", **padding)
        tk.Button(self.root, text="Actualizar", command=self.refresh_printers).grid(row=0, column=2, **padding)

        tk.Label(self.root, text="Puerto TCP").grid(row=1, column=0, sticky="w", **padding)
        tk.Entry(self.root, textvariable=self._port_var).grid(row=1, column=1, sticky="ew", **padding)

        self.autostart_check = tk.Checkbutton(
            self.root,
            text="Iniciar servidor automáticamente",
            variable=self._autostart_var,
            command=self._save_config,
        )
        self.autostart_check.grid(row=2, column=0, columnspan=2, sticky="w", **padding)

        tk.Button(self.root, text="Iniciar", command=self.start_server).grid(row=3, column=0, sticky="ew", **padding)
        tk.Button(self.root, text="Detener", command=self.stop_server).grid(row=3, column=1, sticky="ew", **padding)

        tk.Label(self.root, textvariable=self._status_var, fg="blue").grid(row=4, column=0, columnspan=3, sticky="w", **padding)

        self.log_box = tk.Text(self.root, height=8, state="disabled", wrap="word")
        self.log_box.grid(row=5, column=0, columnspan=3, sticky="nsew", **padding)

        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(5, weight=1)

    def refresh_printers(self) -> None:
        self._printer_options = list_printers()
        menu = self.printer_menu["menu"]
        menu.delete(0, "end")
        for printer in self._printer_options:
            menu.add_command(label=printer, command=lambda value=printer: self._printer_var.set(value))
        if self._printer_options and not self._printer_var.get():
            self._printer_var.set(self._printer_options[0])
        self._save_config()

    def start_server(self, auto: bool = False) -> None:
        if self._server:
            return

        printer = self._printer_var.get()
        if not printer:
            messagebox.showerror("Configurar impresora", "Selecciona una impresora antes de iniciar.")
            return

        try:
            port = int(self._port_var.get())
        except ValueError:
            messagebox.showerror("Puerto inválido", "Introduce un puerto numérico.")
            return

        try:
            self._server = PrinterServer(printer, "0.0.0.0", port, self._set_status)
            self._server.start()
            self._set_status(f"Escuchando en 0.0.0.0:{port}")
            self._append_log(f"Servidor iniciado en el puerto {port} → {printer}")
            self._save_config()
        except OSError as exc:
            self._server = None
            messagebox.showerror("Error al iniciar", str(exc))
            logger.exception("No se pudo iniciar el servidor")
            if not auto:
                return

    def stop_server(self) -> None:
        if self._server:
            self._server.stop()
            self._server = None
            self._append_log("Servidor detenido")

    def _save_config(self) -> None:
        try:
            port_value = int(self._port_var.get())
        except ValueError:
            port_value = self.config.port

        self.config = AppConfig(
            printer_name=self._printer_var.get(),
            port=port_value,
            autostart=self._autostart_var.get(),
        )
        self.config.save()

    def _set_status(self, text: str) -> None:
        self._status_var.set(text)
        self._append_log(text)

    def _append_log(self, text: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{text}\n")
        self.log_box.configure(state="disabled")
        self.log_box.see("end")

    def run(self) -> None:
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self) -> None:
        self.stop_server()
        self.root.destroy()


def launch_app() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app = PrinterBridgeApp()
    app.run()


if __name__ == "__main__":
    launch_app()

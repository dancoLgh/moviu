"""Guided first-run configuration using the shared template catalog."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk
from typing import Callable

from .config import AppConfig
from .configuration_templates import CONFIGURATION_TEMPLATES, get_template
from .network_access import is_local_network_bind
from .usb_bridge import discover_printers


class SetupWizard(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        config: AppConfig,
        on_apply: Callable[[str, str, str], bool],
        on_cancel: Callable[[], None] | None = None,
        on_manual: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__(parent)
        self.title("Configurar Moviu")
        self.geometry("720x600")
        self.minsize(650, 560)
        self.transient(parent)
        self.on_apply = on_apply
        self.on_cancel = on_cancel
        self.on_manual = on_manual
        self.step = "template"
        template_id = config.configuration_template
        if template_id not in {item.id for item in CONFIGURATION_TEMPLATES}:
            template_id = CONFIGURATION_TEMPLATES[0].id
        self.template_var = tk.StringVar(self, value=template_id)
        self.printer_var = tk.StringVar(
            self, value=config.usb_bridge_printer if config.setup_completed else ""
        )
        mode_id = "local"
        if config.setup_completed and is_local_network_bind(config.bind_host):
            mode_id = "shared_without_key" if config.allow_without_api_key else "shared"
        modes = get_template(template_id).access_modes
        if mode_id not in {mode.id for mode in modes}:
            mode_id = modes[0].id
        self.access_var = tk.StringVar(self, value=mode_id)
        self.error_var = tk.StringVar(self)
        self.printers: list[str] = []

        shell = ttk.Frame(self, style="App.TFrame", padding=24)
        shell.pack(fill=tk.BOTH, expand=True)
        self.progress_label = ttk.Label(shell, style="TLabel")
        self.progress_label.pack(anchor="w", pady=(0, 12))
        self.body = ttk.Frame(shell, style="Surface.TFrame", padding=20)
        self.body.pack(fill=tk.BOTH, expand=True)
        ttk.Label(
            shell, textvariable=self.error_var, style="TLabel", wraplength=650
        ).pack(anchor="w", pady=(10, 0))
        footer = ttk.Frame(shell, style="App.TFrame")
        footer.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(footer, text="Cancelar" if config.setup_completed else "Salir", command=self.cancel).pack(
            side=tk.LEFT
        )
        if on_manual is not None:
            ttk.Button(footer, text="Configuración manual", command=self.manual).pack(side=tk.LEFT, padx=8)
        self.next_button = ttk.Button(
            footer, text="Siguiente", style="Primary.TButton", command=self.next
        )
        self.next_button.pack(side=tk.RIGHT)
        self.back_button = ttk.Button(footer, text="Atrás", command=self.back)
        self.back_button.pack(side=tk.RIGHT, padx=8)
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.bind("<Map>", self._activate_modal, add="+")
        self.render()

    def _activate_modal(self, event: tk.Event) -> None:
        # On first launch the parent may still be mapping. Waiting for visibility
        # inside its idle callback can block both windows from ever appearing.
        if event.widget is self:
            self.grab_set()
            self.focus_set()

    @property
    def steps(self) -> tuple[str, ...]:
        modes = get_template(self.template_var.get()).access_modes
        return ("template", "printer", *(("access",) if len(modes) > 1 else ()), "review")

    def _heading(self, title: str, description: str) -> None:
        ttk.Label(self.body, text=title, style="HeroTitle.TLabel", wraplength=620).pack(anchor="w")
        ttk.Label(
            self.body, text=description, style="Muted.TLabel", wraplength=600
        ).pack(anchor="w", pady=(8, 20))

    def _choice(self, variable: tk.StringVar, value: str, label: str, description: str, command=None) -> None:
        ttk.Radiobutton(
            self.body, text=label, variable=variable, value=value,
            style="Wizard.TRadiobutton", command=command,
        ).pack(anchor="w", pady=(10, 4))
        ttk.Label(
            self.body, text=description, style="Muted.TLabel", wraplength=560
        ).pack(anchor="w", padx=(26, 0), pady=(0, 12))

    def _template_changed(self) -> None:
        self.access_var.set(get_template(self.template_var.get()).access_modes[0].id)

    def render(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()
        self.error_var.set("")
        self.progress_label.configure(text=f"CONFIGURACIÓN INICIAL  ·  Paso {self.steps.index(self.step) + 1} de {len(self.steps)}")
        self.back_button.configure(state="disabled" if self.step == "template" else "normal")
        self.next_button.configure(text="Finalizar" if self.step == "review" else "Siguiente", state="normal")
        template = get_template(self.template_var.get())

        if self.step == "template":
            self._heading("¿Qué deseas usar?", "Elige una plantilla de configuración para empezar.")
            for item in CONFIGURATION_TEMPLATES:
                self._choice(self.template_var, item.id, item.label, item.description, self._template_changed)
        elif self.step == "printer":
            self._heading("Elige tu impresora", f"Selecciona la impresora instalada que usarás con {template.label}.")
            self.printer_combo = ttk.Combobox(
                self.body, textvariable=self.printer_var, state="readonly"
            )
            self.printer_combo.pack(fill=tk.X, pady=(0, 12))
            self.printer_combo.bind("<<ComboboxSelected>>", lambda _event: self._validate_printer())
            ttk.Button(self.body, text="Actualizar impresoras", command=self.refresh_printers).pack(anchor="w")
            self.printer_hint = ttk.Label(self.body, style="Muted.TLabel", wraplength=600)
            self.printer_hint.pack(anchor="w", pady=14)
            self.refresh_printers()
        elif self.step == "access":
            self._heading("¿Uso local o compartido?", "Elige desde dónde se enviarán los trabajos de impresión.")
            for mode in template.access_modes:
                self._choice(self.access_var, mode.id, mode.label, mode.description)
        else:
            self._heading("Todo listo para configurar", "Al finalizar se guardarán los cambios y se iniciará la impresión.")
            mode = next(mode for mode in template.access_modes if mode.id == self.access_var.get())
            rows = (
                ("Plantilla", template.label),
                ("Impresora", self.printer_var.get()),
                ("Acceso", mode.label),
                ("API key", "Activada" if mode.requires_api_key else "Desactivada"),
                ("Puente USB", "Activado; se iniciará al abrir Moviu"),
                ("Servidor", "Se iniciará al abrir Moviu"),
                ("Vista inicial", "Modo fácil" if template.default_interface_mode == "simple" else "Modo avanzado"),
            )
            for label, value in rows:
                ttk.Label(
                    self.body, text=f"{label}:  {value}", style="BodyStrong.TLabel", wraplength=600
                ).pack(anchor="w", pady=7)

    def refresh_printers(self) -> None:
        try:
            self.printers = discover_printers()
            hint = (
                "El puente USB se activará automáticamente con esta impresora."
                if self.printers else
                "No se encontraron impresoras. Instala la impresora en Windows y pulsa Actualizar impresoras."
            )
        except Exception as exc:
            logging.exception("No se pudieron listar las impresoras del asistente")
            self.printers = []
            hint = f"No se pudieron listar las impresoras: {exc}. Vuelve a intentarlo."
        self.printer_combo.configure(values=self.printers)
        if self.printer_var.get() not in self.printers:
            self.printer_var.set("")
        self.printer_hint.configure(text=hint)
        self._validate_printer()

    def _validate_printer(self) -> None:
        self.error_var.set("")
        self.next_button.configure(state="normal" if self.printer_var.get() in self.printers else "disabled")

    def next(self) -> None:
        if self.step == "review":
            self.next_button.configure(state="disabled")
            try:
                applied = self.on_apply(self.template_var.get(), self.printer_var.get(), self.access_var.get())
            finally:
                if self.winfo_exists():
                    self.next_button.configure(state="normal")
            if applied:
                self.grab_release()
                self.destroy()
            else:
                self.error_var.set("No se pudo aplicar la configuración. Revisa el mensaje y vuelve a intentarlo.")
            return
        if self.step == "printer" and self.printer_var.get() not in self.printers:
            self.error_var.set("Selecciona una impresora disponible para continuar.")
            return
        self.step = self.steps[self.steps.index(self.step) + 1]
        self.render()

    def back(self) -> None:
        if self.step != "template":
            self.step = self.steps[self.steps.index(self.step) - 1]
            self.render()

    def cancel(self) -> None:
        self.grab_release()
        self.destroy()
        if self.on_cancel is not None:
            self.on_cancel()

    def manual(self) -> None:
        if self.on_manual is not None and self.on_manual():
            self.grab_release()
            self.destroy()

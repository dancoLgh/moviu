"""FastAPI app that exposes the local printing API."""

from __future__ import annotations

import base64
import logging
from typing import Optional, Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import AppConfig
from .printer import PrintJob, PrintProcessor, PrinterError
from .usb_bridge import discover_printers
from .system_printer import (
    print_pdf_to_system_printer,
    print_pdf_raw_to_printer,
    SystemPrinterError,
)
from .mdns import discover_moviu_servers

LOGGER = logging.getLogger(__name__)


class PrinterSettings(BaseModel):
    host: Optional[str] = Field(None, description="Host/IP del printer (para impresoras de red)")
    port: Optional[int] = Field(None, description="Puerto TCP del printer (para impresoras de red)")
    name: Optional[str] = Field(None, description="Nombre de impresora local (para pdf_system)")


class PrintRequest(BaseModel):
    mode: str = Field("html", description="html | image | pdf | raw | raw_text | zpl | hybrid")
    content: Any = Field(..., description="Payload del trabajo (string, base64, o dict para hybrid)")
    printer: Optional[PrinterSettings] = None
    code_page: Optional[str] = Field(
        None,
        description="Code page a usar para raw_text (p.ej. cp437, cp850, cp858, cp1252)",
    )
    dpi: int = Field(
        150,
        ge=72,
        le=600,
        description="DPI para renderizado de PDF en impresora local (72-600). Mayor = mejor calidad."
    )
    paper_size: Optional[str] = Field(
        None,
        description="Tamaño de hoja para PDF local (A4, Letter, Legal, A5, etc. o código DMPAPER numérico)"
    )
    paper_width_mm: Optional[float] = Field(
        None,
        gt=0,
        le=2000,
        description="Ancho de hoja personalizado en mm para PDF local (requiere paper_height_mm)",
    )
    paper_height_mm: Optional[float] = Field(
        None,
        gt=0,
        le=2000,
        description="Alto de hoja personalizado en mm para PDF local (requiere paper_width_mm)",
    )
    raw_mode: bool = Field(
        False,
        description="Para PDF en impresora local: enviar PDF directamente sin renderizar (requiere soporte PDF nativo)"
    )
    simulate: Optional[bool] = Field(
        None, description="Forzar simulación/impresora virtual (solo desarrollo)"
    )
    gamma: Optional[int] = Field(
        None, description="Ajuste de oscuridad 200 (claro) a 1000 (muy oscuro). Default: 500"
    )


class PrintResponse(BaseModel):
    status: str
    job_id: Optional[str] = Field(None, description="Identificador del trabajo para trazabilidad")
    host: Optional[str] = None
    port: Optional[int] = None
    bytes: Optional[int] = None
    printer: Optional[str] = Field(None, description="Nombre de impresora local (para pdf_system)")
    pages: Optional[int] = Field(None, description="Paginas impresas (para pdf_system)")
    paper_size: Optional[str] = Field(None, description="Tamano de hoja aplicado (para pdf_system)")
    paper_width_mm: Optional[float] = Field(None, description="Ancho de hoja aplicado en mm (para pdf_system)")
    paper_height_mm: Optional[float] = Field(None, description="Alto de hoja aplicado en mm (para pdf_system)")
    message: Optional[str] = Field(None, description="Mensaje descriptivo")
    preview: Optional[dict] = Field(None, description="Vista previa del trabajo si aplica")


def create_api(config: AppConfig) -> FastAPI:
    processor = PrintProcessor(
        config.printer_host,
        config.printer_port,
        width=config.printer_width,
        gamma=config.printer_gamma,
        simulate=config.simulate_printer,
    )

    app = FastAPI(title="Moviu Print Server", version="1.0.0")

    # ------------------------------------------------------------------
    # CORS: permitir cualquier origen (no usamos cookies, solo X-API-Key)
    # ------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],      # permitir todos los orígenes
        allow_credentials=False,  # obligatorio si usamos "*"
        allow_methods=["*"],      # permite OPTIONS, GET, POST, etc.
        allow_headers=["*"],      # permite X-API-Key y demás headers
    )

    def require_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> None:
        if x_api_key != config.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key inválida",
            )

    # Preflight explícito (opcional pero ayuda a que el navegador esté feliz)
    @app.options("/api/print")
    def options_print() -> dict:
        return {"status": "ok"}

    @app.post("/api/print", response_model=PrintResponse)
    def print_endpoint(
        request: PrintRequest,
        _: None = Depends(require_api_key),
    ) -> PrintResponse:
        printer_name = request.printer.name if request.printer else None
        printer_host = request.printer.host if request.printer else None
        printer_port = request.printer.port if request.printer else None
        has_explicit_network_target = bool(request.printer and (printer_host or printer_port))
        default_local_printer = (
            config.usb_bridge_printer
            if config.usb_bridge_enabled and config.usb_bridge_printer
            else None
        )

        # Handle PDF mode with intelligent routing
        if request.mode == "pdf":
            # Decode PDF content once
            try:
                content = request.content
                if content.startswith("data:application/pdf"):
                    _, b64_data = content.split(",", 1)
                    pdf_data = base64.b64decode(b64_data)
                else:
                    pdf_data = base64.b64decode(content)
            except Exception as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"El PDF debe estar codificado en base64: {exc}"
                ) from exc

            # Route 1: Print to local system printer by name
            if printer_name:
                try:
                    if request.raw_mode:
                        result = print_pdf_raw_to_printer(pdf_data, printer_name)
                    else:
                        result = print_pdf_to_system_printer(
                            pdf_data,
                            printer_name,
                            dpi=request.dpi,
                            paper_size=request.paper_size,
                            paper_width_mm=request.paper_width_mm,
                            paper_height_mm=request.paper_height_mm,
                        )
                except SystemPrinterError as exc:
                    LOGGER.exception("System print job failed")
                    raise HTTPException(status_code=400, detail=str(exc)) from exc
                return PrintResponse(**result)

            # Route 2: Print to network printer by host/port
            if has_explicit_network_target or (not default_local_printer and config.printer_host):
                target_host = printer_host or config.printer_host
                target_port = printer_port or config.printer_port or 9100

                if request.raw_mode:
                    # Send PDF directly via TCP (for printers with native PDF support)
                    import socket
                    try:
                        with socket.create_connection((target_host, target_port), timeout=30) as sock:
                            sock.sendall(pdf_data)
                        LOGGER.info("PDF RAW enviado a %s:%d (%d bytes)", target_host, target_port, len(pdf_data))
                        return PrintResponse(
                            status="sent",
                            host=target_host,
                            port=target_port,
                            bytes=len(pdf_data),
                            printer=None,
                            pages=None,
                            paper_size=None,
                            paper_width_mm=None,
                            paper_height_mm=None,
                            message=f"PDF enviado directamente a {target_host}:{target_port}",
                            preview=None,
                        )
                    except Exception as exc:
                        LOGGER.exception("Failed to send PDF to network printer")
                        raise HTTPException(status_code=400, detail=f"Error al enviar PDF: {exc}") from exc
                else:
                    # Render PDF to ESC/POS and send (for thermal printers)
                    # Falls through to standard processing below
                    pass

        # Handle other modes (thermal printers via TCP)
        resolved_local_printer = printer_name
        if resolved_local_printer is None and not has_explicit_network_target:
            resolved_local_printer = default_local_printer

        resolved_printer_host = None if resolved_local_printer else (printer_host or config.printer_host)
        resolved_printer_port = None if resolved_local_printer else (printer_port or config.printer_port)
        simulate = (
            request.simulate
            if request.simulate is not None
            else config.simulate_printer
        )
        # Ensure content is passed as string to PrintJob
        content = request.content
        if isinstance(content, (dict, list)):
            import json
            content = json.dumps(content)

        job = PrintJob(
            mode=request.mode, # type: ignore
            content=content,
            printer_host=resolved_printer_host or "",
            printer_port=resolved_printer_port or 0,
            printer_name=resolved_local_printer,
            code_page=request.code_page,
            gamma=request.gamma,
        )
        try:
            result = processor.process(job, simulate_override=simulate)
        except PrinterError as exc:
            LOGGER.exception("Print job failed")
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return PrintResponse(**result)

    @app.get("/api/health")
    def health(_: None = Depends(require_api_key)) -> dict:
        return {"status": "ok"}

    @app.get("/api/printers")
    def list_printers(_: None = Depends(require_api_key)) -> dict:
        """Lista las impresoras instaladas en el sistema local."""
        printers = discover_printers()
        return {"printers": printers, "count": len(printers)}

    @app.get("/api/discover")
    def discover_services(
        timeout: float = 3.0,
    ) -> dict:
        """Descubre servidores Moviu Print Server en la red local via mDNS.

        Este endpoint no requiere autenticación para permitir el descubrimiento
        de servicios antes de conocer la API key.

        Args:
            timeout: Segundos a esperar para el descubrimiento (default: 3.0)
        """
        servers = discover_moviu_servers(timeout=timeout)
        return {"servers": servers, "count": len(servers)}

    return app

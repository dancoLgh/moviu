"""FastAPI app that exposes the local printing API."""

from __future__ import annotations

import base64
import logging
from typing import Optional

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

LOGGER = logging.getLogger(__name__)


class PrinterSettings(BaseModel):
    host: Optional[str] = Field(None, description="Host/IP del printer")
    port: Optional[int] = Field(None, description="Puerto TCP del printer")


class PrintRequest(BaseModel):
    mode: str = Field("html", description="html | image | pdf | raw | raw_text")
    content: str = Field(..., description="Payload del trabajo")
    printer: Optional[PrinterSettings] = None
    code_page: Optional[str] = Field(
        None,
        description="Code page a usar para raw_text (p.ej. cp437, cp850, cp858, cp1252)",
    )
    simulate: Optional[bool] = Field(
        None, description="Forzar simulación/impresora virtual (solo desarrollo)"
    )


class PrintResponse(BaseModel):
    status: str
    host: str
    port: int
    bytes: int
    preview: Optional[dict] = Field(None, description="Vista previa del trabajo si aplica")


class SystemPrintRequest(BaseModel):
    """Request para imprimir en impresoras del sistema (láser, inyección, etc.)."""
    content: str = Field(..., description="PDF en base64 o data URI")
    printer_name: Optional[str] = Field(
        None,
        description="Nombre de la impresora. Si no se especifica, usa la predeterminada."
    )
    raw_mode: bool = Field(
        False,
        description="Si es True, envía el PDF directamente a la impresora (requiere soporte nativo de PDF)"
    )
    dpi: int = Field(
        150,
        ge=72,
        le=600,
        description="Resolución de renderizado (72-600). Solo aplica cuando raw_mode=false. Mayor DPI = mejor calidad pero más lento."
    )


class SystemPrintResponse(BaseModel):
    status: str
    message: str
    printer: str
    bytes: Optional[int] = None
    pages: Optional[int] = None


def create_api(config: AppConfig) -> FastAPI:
    processor = PrintProcessor(
        config.printer_host,
        config.printer_port,
        width=config.printer_width,
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
        printer_host = request.printer.host if request.printer else config.printer_host
        printer_port = request.printer.port if request.printer else config.printer_port
        simulate = (
            request.simulate
            if request.simulate is not None
            else config.simulate_printer
        )
        job = PrintJob(
            mode=request.mode,
            content=request.content,
            printer_host=printer_host or config.printer_host,
            printer_port=printer_port or config.printer_port,
            code_page=request.code_page,
        )
        try:
            result = processor.process(job, simulate_override=simulate)
        except PrinterError as exc:
            LOGGER.exception("Print job failed")
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return PrintResponse(**result)

    @app.post("/api/print/system", response_model=SystemPrintResponse)
    def print_system_endpoint(
        request: SystemPrintRequest,
        _: None = Depends(require_api_key),
    ) -> SystemPrintResponse:
        """Imprimir PDF en impresoras del sistema (láser, inyección, A4, A3, etc.)."""
        try:
            # Decode base64 content
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

        try:
            if request.raw_mode:
                if not request.printer_name:
                    raise HTTPException(
                        status_code=400,
                        detail="raw_mode requiere especificar printer_name"
                    )
                result = print_pdf_raw_to_printer(pdf_data, request.printer_name)
            else:
                result = print_pdf_to_system_printer(pdf_data, request.printer_name, dpi=request.dpi)
        except SystemPrinterError as exc:
            LOGGER.exception("System print job failed")
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return SystemPrintResponse(**result)

    @app.get("/api/health")
    def health(_: None = Depends(require_api_key)) -> dict:
        return {"status": "ok"}

    @app.get("/api/printers")
    def list_printers(_: None = Depends(require_api_key)) -> dict:
        """Lista las impresoras instaladas en el sistema local."""
        printers = discover_printers()
        return {"printers": printers, "count": len(printers)}

    return app


"""FastAPI app that exposes the local printing API."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import AppConfig
from .printer import PrintJob, PrintProcessor, PrinterError

LOGGER = logging.getLogger(__name__)


class PrinterSettings(BaseModel):
    host: Optional[str] = Field(None, description="Host/IP del printer")
    port: Optional[int] = Field(None, description="Puerto TCP del printer")


class PrintRequest(BaseModel):
    mode: str = Field("html", description="html | image | raw | raw_text")
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


def create_api(config: AppConfig) -> FastAPI:
    processor = PrintProcessor(
        config.printer_host, config.printer_port, simulate=config.simulate_printer
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

    @app.get("/api/health")
    def health(_: None = Depends(require_api_key)) -> dict:
        return {"status": "ok"}

    return app

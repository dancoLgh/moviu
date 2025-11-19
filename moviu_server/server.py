"""FastAPI app that exposes the local printing API."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
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


class PrintResponse(BaseModel):
    status: str
    host: str
    port: int
    bytes: int


def create_api(config: AppConfig) -> FastAPI:
    processor = PrintProcessor(config.printer_host, config.printer_port)
    app = FastAPI(title="Moviu Print Server", version="1.0.0")

    def require_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> None:
        if x_api_key != config.api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key inválida")

    @app.post("/api/print", response_model=PrintResponse)
    def print_endpoint(request: PrintRequest, _: None = Depends(require_api_key)) -> PrintResponse:
        printer_host = request.printer.host if request.printer else config.printer_host
        printer_port = request.printer.port if request.printer else config.printer_port
        job = PrintJob(
            mode=request.mode,
            content=request.content,
            printer_host=printer_host or config.printer_host,
            printer_port=printer_port or config.printer_port,
        )
        try:
            result = processor.process(job)
        except PrinterError as exc:
            LOGGER.exception("Print job failed")
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return PrintResponse(**result)

    @app.get("/api/health")
    def health(_: None = Depends(require_api_key)) -> dict:
        return {"status": "ok"}

    return app

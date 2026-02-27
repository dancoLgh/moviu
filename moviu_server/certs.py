"""Utilities to generate and export self-signed SSL certificates."""

from __future__ import annotations

import datetime
import ipaddress
import os
import subprocess
from pathlib import Path
from typing import Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from .config import CONFIG_DIR


def ensure_certificates(
    cert_path: Path, key_path: Path, hosts: str | list[str], force: bool = False
) -> Tuple[Path, Path]:
    """Create a self-signed certificate if it does not exist or if forced."""

    cert_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)

    if cert_path.exists() and key_path.exists() and not force:
        return cert_path, key_path

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "Moviu Local API"),
        ]
    )

    alt_names = [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
    
    if isinstance(hosts, str):
        hosts = [hosts]
        
    for host in hosts:
        if not host or host == "0.0.0.0":
            continue
        try:
            alt_names.append(x509.IPAddress(ipaddress.ip_address(host)))
        except ValueError:
            alt_names.append(x509.DNSName(host))
            
    # Remove duplicates
    seen = set()
    unique_alt_names = []
    for name in alt_names:
        if name not in seen:
            unique_alt_names.append(name)
            seen.add(name)
    alt_names = unique_alt_names

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow() - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365 * 5))
        .add_extension(x509.SubjectAlternativeName(alt_names), critical=False)
        .sign(key, hashes.SHA256())
    )

    with key_path.open("wb") as fh:
        fh.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    with cert_path.open("wb") as fh:
        fh.write(cert.public_bytes(serialization.Encoding.PEM))

    return cert_path, key_path


def export_certificate(destination: Path, cert_path: Path) -> Path:
    """Copy the public certificate so it can be shared with clients."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    data = cert_path.read_bytes()
    destination.write_bytes(data)
    return destination


def certificates_folder() -> Path:
    """Return the folder that holds the generated keys/certs."""

    return CONFIG_DIR


def install_certificate_in_system(cert_path: Path) -> bool:
    """Instala el certificado en el almacén de Entidades de Certificación de Raíz de Confianza de Windows.
    
    Esto hace que Chrome, Edge y otros navegadores confíen en el certificado localmente.
    Requiere que certutil esté disponible (estándar en Windows).
    """
    if os.name != "nt":
        return False

    try:
        # Probamos primero con el almacén del usuario (no requiere admin usualmente)
        # Si queremos global sería sin "-user", pero dispararía UAC.
        cmd = ["certutil", "-addstore", "-user", "-f", "Root", str(cert_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.returncode == 0
    except Exception:
        return False


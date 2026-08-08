"""Utilities to generate and export SSL certificates (CA + server cert)."""

from __future__ import annotations

import datetime
import ipaddress
import os
import subprocess
from pathlib import Path
from typing import Iterable, Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from .config import CONFIG_DIR

_CA_CERT_FILENAME = "ca_cert.pem"
_CA_KEY_FILENAME = "ca_key.pem"


def _normalize_hosts(hosts: str | Iterable[str]) -> list[str]:
    normalized = ["localhost", "127.0.0.1"]

    if isinstance(hosts, str):
        host_values = [hosts]
    else:
        host_values = list(hosts)

    for host in host_values:
        value = host.strip() if host else ""
        if not value or value == "0.0.0.0":
            continue
        normalized.append(value)

    unique: list[str] = []
    seen: set[str] = set()
    for value in normalized:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(value)
    return unique


def ca_certificate_path(cert_path: Path) -> Path:
    """Return CA certificate path used to sign the server certificate."""

    return cert_path.with_name(_CA_CERT_FILENAME)


def _ca_private_key_path(cert_path: Path) -> Path:
    return cert_path.with_name(_CA_KEY_FILENAME)


def _load_certificate(path: Path) -> x509.Certificate:
    return x509.load_pem_x509_certificate(path.read_bytes())


def _load_private_key(path: Path) -> RSAPrivateKey:
    private_key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise RuntimeError("La clave privada no es RSA")
    return private_key


def _build_subject_alt_names(hosts: Iterable[str]) -> x509.SubjectAlternativeName:
    alt_names: list[x509.GeneralName] = []
    for host in hosts:
        try:
            alt_names.append(x509.IPAddress(ipaddress.ip_address(host)))
        except ValueError:
            alt_names.append(x509.DNSName(host))
    return x509.SubjectAlternativeName(alt_names)


def _ensure_ca(ca_cert_path: Path, ca_key_path: Path) -> tuple[x509.Certificate, RSAPrivateKey]:
    if ca_cert_path.exists() and ca_key_path.exists():
        return _load_certificate(ca_cert_path), _load_private_key(ca_key_path)

    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Moviu Local Root CA")])

    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_subject)
        .issuer_name(ca_subject)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow() - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365 * 10))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256())
    )

    ca_key_path.write_bytes(
        ca_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    ca_cert_path.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
    return ca_cert, ca_key


def _certificate_matches_ca_and_hosts(
    cert_path: Path,
    ca_cert: x509.Certificate,
    hosts: list[str],
) -> bool:
    try:
        cert = _load_certificate(cert_path)
    except Exception:
        return False

    if cert.issuer != ca_cert.subject:
        return False

    if cert.not_valid_after <= datetime.datetime.utcnow() + datetime.timedelta(days=1):
        return False

    try:
        san_ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
    except x509.ExtensionNotFound:
        return False

    existing_dns: set[str] = set()
    existing_ips: set[str] = set()
    for entry in san_ext.value:
        if isinstance(entry, x509.DNSName):
            existing_dns.add(entry.value.lower())
        elif isinstance(entry, x509.IPAddress):
            existing_ips.add(str(entry.value))

    for host in hosts:
        try:
            ip_value = ipaddress.ip_address(host)
            if str(ip_value) not in existing_ips:
                return False
        except ValueError:
            if host.lower() not in existing_dns:
                return False

    return True


def _write_server_certificate(
    cert_path: Path,
    key_path: Path,
    hosts: list[str],
    ca_cert: x509.Certificate,
    ca_key: RSAPrivateKey,
) -> None:
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    common_name = "Moviu Local API"
    for host in hosts:
        try:
            ipaddress.ip_address(host)
        except ValueError:
            common_name = host
            break

    server_subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])

    server_cert = (
        x509.CertificateBuilder()
        .subject_name(server_subject)
        .issuer_name(ca_cert.subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow() - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365 * 5))
        .add_extension(_build_subject_alt_names(hosts), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )

    key_path.write_bytes(
        server_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(server_cert.public_bytes(serialization.Encoding.PEM))


def ensure_certificates(
    cert_path: Path,
    key_path: Path,
    hosts: str | Iterable[str],
    force: bool = False,
) -> Tuple[Path, Path]:
    """Ensure CA and server certificates exist and are valid for requested hosts."""

    cert_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)

    normalized_hosts = _normalize_hosts(hosts)
    ca_cert_path = ca_certificate_path(cert_path)
    ca_key_path = _ca_private_key_path(cert_path)
    ca_cert_path.parent.mkdir(parents=True, exist_ok=True)
    ca_key_path.parent.mkdir(parents=True, exist_ok=True)

    ca_cert, ca_key = _ensure_ca(ca_cert_path, ca_key_path)

    needs_new_server_cert = force
    if not cert_path.exists() or not key_path.exists():
        needs_new_server_cert = True
    elif not _certificate_matches_ca_and_hosts(cert_path, ca_cert, normalized_hosts):
        needs_new_server_cert = True

    if needs_new_server_cert:
        _write_server_certificate(cert_path, key_path, normalized_hosts, ca_cert, ca_key)

    return cert_path, key_path


def export_certificate(destination: Path, cert_path: Path) -> Path:
    """Copy the selected public certificate so it can be shared with clients."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(cert_path.read_bytes())
    return destination


def export_ca_certificate(destination: Path, server_cert_path: Path) -> Path:
    """Export the CA cert used to sign the local HTTPS server certificate."""

    return export_certificate(destination, ca_certificate_path(server_cert_path))


def certificate_sha256_fingerprint(cert_path: Path) -> str:
    """Return the conventional colon-separated SHA-256 certificate fingerprint."""

    digest = _load_certificate(cert_path).fingerprint(hashes.SHA256()).hex().upper()
    return ":".join(digest[index : index + 2] for index in range(0, len(digest), 2))


def certificates_folder() -> Path:
    """Return the folder that holds the generated keys/certs."""

    return CONFIG_DIR


def install_certificate_in_system(cert_path: Path) -> bool:
    """Install certificate in current user's trusted root store on Windows."""

    if os.name != "nt":
        return False

    try:
        cmd = ["certutil", "-addstore", "-user", "-f", "Root", str(cert_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.returncode == 0
    except Exception:
        return False

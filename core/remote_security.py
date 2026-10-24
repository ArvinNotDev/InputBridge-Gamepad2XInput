"""Per-installation TLS identity and SHA-256 certificate pin helpers."""
from __future__ import annotations
import hashlib
import ipaddress
import os
import socket
import ssl
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from core.utils.paths import data_path


def normalize_fingerprint(value: str) -> str:
    if not isinstance(value, str):
        return ""
    normalized = "".join(char for char in value.lower() if char in "0123456789abcdef")
    return normalized if len(normalized) == 64 else ""


def format_fingerprint(value: str) -> str:
    normalized = normalize_fingerprint(value)
    return ":".join(normalized[i:i + 2].upper() for i in range(0, 64, 2)) if normalized else ""


def fingerprint_der_certificate(certificate_der: bytes) -> str:
    return hashlib.sha256(certificate_der).hexdigest()


def _atomic_write(path: Path, data: bytes, *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            if private and hasattr(os, "fchmod"):
                try:
                    os.fchmod(stream.fileno(), 0o600)
                except OSError:
                    pass
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def ensure_server_identity(certificate_path: str | Path | None = None, private_key_path: str | Path | None = None) -> tuple[Path, Path]:
    """Create a persistent self-signed server certificate once; never rotate silently."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    certificate = Path(certificate_path or data_path("remote_security", "server.crt"))
    private_key = Path(private_key_path or data_path("remote_security", "server.key"))
    if certificate.exists() and private_key.exists():
        return certificate, private_key
    if certificate.exists() != private_key.exists():
        raise RuntimeError("Only one TLS identity file exists. Restore both files or remove the incomplete identity pair and restart.")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    hostname = socket.gethostname() or "InputBridge-PC"
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname[:64])])
    now = datetime.now(timezone.utc)
    sans = [x509.DNSName(hostname), x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
    cert = (
        x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.SubjectAlternativeName(sans), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    key_bytes = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    cert_bytes = cert.public_bytes(serialization.Encoding.PEM)
    _atomic_write(private_key, key_bytes, private=True)
    try:
        _atomic_write(certificate, cert_bytes)
    except Exception:
        try:
            private_key.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return certificate, private_key


def create_server_ssl_context(certificate_path: str | Path | None = None, private_key_path: str | Path | None = None) -> tuple[ssl.SSLContext, str]:
    """Return a TLS 1.2+ context and the pin the desktop must display."""
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization

    cert_path, key_path = ensure_server_identity(certificate_path, private_key_path)
    try:
        cert_pem = cert_path.read_bytes()
        serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        certificate = x509.load_pem_x509_certificate(cert_pem)
    except Exception as exc:
        raise RuntimeError("The saved TLS identity is invalid. Stop the server and repair or remove its identity files.") from exc
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.options |= getattr(ssl, "OP_NO_COMPRESSION", 0)
    context.load_cert_chain(str(cert_path), str(key_path))
    fingerprint = fingerprint_der_certificate(certificate.public_bytes(serialization.Encoding.DER))
    return context, format_fingerprint(fingerprint)

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



def ensure_web_server_identity(
    hosts: list[str] | tuple[str, ...] = (),
    certificate_path: str | Path | None = None,
    private_key_path: str | Path | None = None,
) -> tuple[Path, Path]:
    """Create a web-only identity whose SANs include the host/IP used in the QR URL.

    The native phone server keeps its existing pinned certificate. A LAN IP change
    may rotate this separate browser identity, but never silently rotates the
    certificate pinned by the native mobile client.
    """
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    certificate_path = Path(certificate_path or data_path("remote_security", "web_server.crt"))
    private_key_path = Path(private_key_path or data_path("remote_security", "web_server.key"))
    hostname = socket.gethostname() or "InputBridge-PC"
    dns_names = {hostname[:253], "localhost"}
    ip_names = {"127.0.0.1", "::1"}
    for host in hosts:
        if not isinstance(host, str) or not host:
            continue
        try:
            ip_names.add(str(ipaddress.ip_address(host)))
        except ValueError:
            dns_names.add(host.rstrip(".")[:253])

    # Reuse a web certificate only when it is still valid and contains every
    # SAN required by this launch. This file pair is deliberately separate from
    # the certificate used by the native TCP/TLS client.
    if certificate_path.is_file() and private_key_path.is_file():
        try:
            previous = x509.load_pem_x509_certificate(certificate_path.read_bytes())
            san = previous.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
            previous_dns = set(san.get_values_for_type(x509.DNSName))
            previous_ips = {str(item) for item in san.get_values_for_type(x509.IPAddress)}
            now = datetime.now(timezone.utc)
            not_before = previous.not_valid_before.replace(tzinfo=timezone.utc)
            not_after = previous.not_valid_after.replace(tzinfo=timezone.utc)
            if (dns_names.issubset(previous_dns) and ip_names.issubset(previous_ips)
                    and not_before <= now < not_after):
                # Let SSLContext validate that the stored private key matches.
                serialization.load_pem_private_key(private_key_path.read_bytes(), password=None)
                return certificate_path, private_key_path
        except Exception:
            # A corrupt or out-of-date web identity can be recreated. The native
            # identity is never read or modified by this function.
            pass

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname[:64])])
    now = datetime.now(timezone.utc)
    san_values = [x509.DNSName(name) for name in sorted(dns_names)]
    san_values.extend(x509.IPAddress(ipaddress.ip_address(value)) for value in sorted(ip_names))
    certificate = (
        x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.SubjectAlternativeName(san_values), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    private_key_path.parent.mkdir(parents=True, exist_ok=True)
    certificate_path.parent.mkdir(parents=True, exist_ok=True)
    key_bytes = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    certificate_bytes = certificate.public_bytes(serialization.Encoding.PEM)
    _atomic_write(private_key_path, key_bytes, private=True)
    try:
        _atomic_write(certificate_path, certificate_bytes)
    except Exception:
        try:
            private_key_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return certificate_path, private_key_path


def create_web_server_ssl_context(
    hosts: list[str] | tuple[str, ...] = (),
    certificate_path: str | Path | None = None,
    private_key_path: str | Path | None = None,
) -> tuple[ssl.SSLContext, str]:
    """Create a TLS 1.2+ context with a web-specific cert matching LAN QR hostnames."""
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization

    cert_path, key_path = ensure_web_server_identity(hosts, certificate_path, private_key_path)
    try:
        cert_bytes = cert_path.read_bytes()
        serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        certificate = x509.load_pem_x509_certificate(cert_bytes)
    except Exception as exc:
        raise RuntimeError("The saved Web Companion TLS identity is invalid.") from exc
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.options |= getattr(ssl, "OP_NO_COMPRESSION", 0)
    context.load_cert_chain(str(cert_path), str(key_path))
    fingerprint = fingerprint_der_certificate(certificate.public_bytes(serialization.Encoding.DER))
    return context, format_fingerprint(fingerprint)

import hashlib
import ssl
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from core.remote_security import create_server_ssl_context, ensure_server_identity, fingerprint_der_certificate, format_fingerprint, normalize_fingerprint


def test_fingerprint_normalization_and_formatting():
    raw = hashlib.sha256(b"certificate").hexdigest()
    formatted = format_fingerprint(raw)
    assert normalize_fingerprint(formatted) == raw
    assert len(formatted.split(":")) == 32
    assert normalize_fingerprint("not a fingerprint") == ""


def test_server_tls_identity_is_persistent_and_tls12_or_newer(tmp_path):
    cert_path, key_path = tmp_path / "server.crt", tmp_path / "server.key"
    ensure_server_identity(cert_path, key_path)
    before = cert_path.read_bytes()
    context, fingerprint = create_server_ssl_context(cert_path, key_path)
    assert isinstance(context, ssl.SSLContext)
    assert context.minimum_version >= ssl.TLSVersion.TLSv1_2
    assert len(normalize_fingerprint(fingerprint)) == 64
    assert ensure_server_identity(cert_path, key_path) == (cert_path, key_path)
    assert cert_path.read_bytes() == before


def test_fingerprint_is_sha256_of_der_certificate(tmp_path):
    cert_path, key_path = tmp_path / "server.crt", tmp_path / "server.key"
    ensure_server_identity(cert_path, key_path)
    certificate = x509.load_pem_x509_certificate(cert_path.read_bytes())
    der = certificate.public_bytes(serialization.Encoding.DER)
    assert fingerprint_der_certificate(der) == hashlib.sha256(der).hexdigest()

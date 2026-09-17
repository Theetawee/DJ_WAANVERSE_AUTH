from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_rsa_keypair_files(directory: Path) -> tuple[str, str]:
    """
    Generates a throwaway RSA keypair and writes it to PEM files in
    `directory`, for JWT tests. Never use real production keys in
    tests — this keeps every test run isolated with its own pair.
    """

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_path = directory / "test_private.pem"
    public_path = directory / "test_public.pem"
    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)

    return str(private_path), str(public_path)


def tamper_jwt_signature(token: str) -> str:
    """
    Flips a character in the middle of a JWT's signature segment.
    Deliberately avoids the first/last character of the signature —
    base64's trailing characters can encode unused padding bits that
    don't survive round-tripping, so tampering there sometimes
    decodes to the same underlying bytes and silently fails to
    actually corrupt the signature.
    """

    header, payload, signature = token.split(".")
    mid = len(signature) // 2
    tampered_char = "A" if signature[mid] != "A" else "B"
    tampered_signature = signature[:mid] + tampered_char + signature[mid + 1:]
    return f"{header}.{payload}.{tampered_signature}"

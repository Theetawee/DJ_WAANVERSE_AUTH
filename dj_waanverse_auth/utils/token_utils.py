import logging
from functools import lru_cache
from typing import Any, Dict

import jwt
from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives import serialization
from rest_framework import exceptions

from dj_waanverse_auth import settings

logger = logging.getLogger(__name__)


class KeyLoadError(Exception):
    pass


@lru_cache(maxsize=2)
def get_key(key_type):
    """
    Load and cache cryptographic keys with LRU caching
    """
    key_paths = {
        "public": settings.public_key_path,
        "private": settings.private_key_path,
    }

    if key_type not in key_paths:
        raise KeyLoadError(f"Invalid key type: {key_type}")

    try:
        with open(key_paths[key_type], "rb") as key_file:
            key_data = key_file.read()

        if key_type == "public":
            return serialization.load_pem_public_key(key_data)
        else:
            return serialization.load_pem_private_key(key_data, password=None)

    except FileNotFoundError:
        logger.critical(f"Could not find {key_type} key file at {key_paths[key_type]}")
        raise KeyLoadError(f"Could not find {key_type} key file")
    except InvalidKey as e:
        logger.critical(f"Invalid {key_type} key format: {str(e)}")
        raise KeyLoadError(f"Invalid {key_type} key format")
    except Exception as e:
        logger.critical(f"Unexpected error loading {key_type} key: {str(e)}")
        raise KeyLoadError(f"Failed to load {key_type} key")


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token with comprehensive error handling and logging.

    This function performs thorough validation of JWT tokens including:
    - Signature verification using RS256 algorithm
    - Expiration time validation
    - Not Before Time (NBF) validation
    - Issued At Time (IAT) validation
    - Required claims verification

    Args:
        token (str): The JWT token string to decode and validate

    Returns:
        Dict[str, Any]: The decoded token payload containing claims

    Raises:
        exceptions.AuthenticationFailed: Raised in the following cases:
            - No token provided
            - Token has expired
            - Invalid token structure
            - Invalid token signature
            - Invalid token issuer
            - Missing required claims
            - Other unexpected validation errors

    Example:
        >>> try:
        ...     payload = decode_token("eyJ0eXAiOiJKV1QiLC...")
        ...     user_id = payload["id"]
        ... except exceptions.AuthenticationFailed as e:
        ...     print(f"Authentication failed: {str(e)}")
    """

    if not token:
        raise exceptions.AuthenticationFailed("No token provided")

    try:
        public_key = get_key("public")
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "require": [
                    "exp",
                    "iat",
                    "iss",
                    "id",
                    "sid",
                ],
            },
        )
        return payload

    except jwt.ExpiredSignatureError:
        logger.info("Token expired")
        raise exceptions.AuthenticationFailed("Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token structure: {str(e)}")
        raise exceptions.AuthenticationFailed("Invalid token structure")
    except jwt.InvalidSignatureError:
        logger.warning("Invalid token signature")
        raise exceptions.AuthenticationFailed("Invalid token signature")
    except jwt.InvalidIssuerError:
        logger.warning("Invalid token issuer")
        raise exceptions.AuthenticationFailed("Invalid token issuer")
    except jwt.MissingRequiredClaimError as e:
        logger.warning(f"Missing required claim: {str(e)}")
        raise exceptions.AuthenticationFailed("Missing required claim in token")
    except Exception as e:
        logger.error(f"Unexpected error decoding token: {str(e)}")
        raise exceptions.AuthenticationFailed("Token validation failed")


def encode_token(payload) -> str:
    """
    Encode payload into JWT token with error handling and logging
    """

    if not isinstance(payload, dict):
        raise ValueError("Payload must be a dictionary")

    required_claims = {"id", "exp", "iat", "iss"}
    missing_claims = required_claims - set(payload.keys())
    if missing_claims:
        raise ValueError(f"Missing required claims: {missing_claims}")
    try:
        private_key = get_key("private")
        token = jwt.encode(payload, private_key, algorithm="RS256")
        return token

    except Exception as e:
        logger.error(f"Token encoding failed: {str(e)}")
        raise exceptions.AuthenticationFailed("Could not generate token")

import logging
from functools import lru_cache

import jwt
from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives import serialization
from django.utils.module_loading import import_string
from rest_framework import exceptions

from dj_waanverse_auth.settings.settings import auth_config

logger = logging.getLogger(__name__)


class KeyLoadError(Exception):
    pass


@lru_cache(maxsize=2)
def get_key(key_type):
    """
    Load and cache cryptographic keys with LRU caching
    """
    key_paths = {
        "public": auth_config.public_key_path,
        "private": auth_config.private_key_path,
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


def decode_token(token):
    """
    Decode and validate JWT token with comprehensive error handling and logging
    """
    user_claim = auth_config.user_id_claim
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
                    user_claim,
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
    user_claim = auth_config.user_id_claim

    if not isinstance(payload, dict):
        raise ValueError("Payload must be a dictionary")

    required_claims = {user_claim, "exp", "iat", "iss"}
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


def get_serializer_class(class_path: str):
    """
    Retrieve a serializer class given its string path.

    Args:
        class_path (str): Full dotted path to the serializer class.
                          Example: 'dj_waanverse_auth.serializers.Basic_Serializer'

    Returns:
        class: The serializer class.

    Raises:
        ImportError: If the class cannot be imported.
    """
    try:
        return import_string(class_path)
    except ImportError as e:
        raise ImportError(f"Could not import serializer class '{class_path}': {e}")

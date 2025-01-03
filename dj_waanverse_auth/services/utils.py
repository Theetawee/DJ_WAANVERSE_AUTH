import logging

import jwt
from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives import serialization
from jwt.exceptions import InvalidTokenError
from rest_framework import exceptions

from dj_waanverse_auth.settings import auth_config

logger = logging.getLogger(__name__)


def get_key(type):
    """
    Load and cache public key with lazy loading pattern.
    """
    print(auth_config.public_key_path, auth_config.private_key_path)
    if type == "public":

        try:
            with open(auth_config.public_key_path, "rb") as key_file:
                key_data = key_file.read()
            public_key = serialization.load_pem_public_key(key_data)
        except (IOError, InvalidKey) as e:
            logger.error(f"Failed to load public key: {str(e)}")
            raise exceptions.AuthenticationFailed("Authentication system misconfigured")

        return public_key
    elif type == "private":
        try:
            with open(auth_config.private_key_path, "rb") as key_file:
                key_data = key_file.read()
            private_key = serialization.load_pem_private_key(key_data, password=None)
        except (IOError, InvalidKey) as e:
            logger.error(f"Failed to load private key: {str(e)}")
            raise exceptions.AuthenticationFailed("Authentication system misconfigured")

        return private_key


def decode_token(token):
    """
    Decode and validate JWT token with comprehensive error handling.
    """
    try:
        public_key = get_key(type="public")
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
            },
        )
        return payload

    except jwt.ExpiredSignatureError:
        logger.info("Token expired")
        raise exceptions.AuthenticationFailed("Token has expired")
    except InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise exceptions.AuthenticationFailed("Invalid token")
    except Exception as e:
        logger.error(f"Token decode error: {str(e)}")
        raise exceptions.AuthenticationFailed(
            f"Token decoding failed with error: {str(e)}"
        )


def encode_token(payload):
    """
    Encode the payload into a JWT token using RS256 algorithm.

    Args:
        payload (dict): The payload to encode.

    Returns:
        str: The encoded JWT token.
    """
    try:
        private_key = get_key(type="private")
        return jwt.encode(payload, private_key, algorithm="RS256")
    except Exception as e:
        logger.error(f"Token encode error: {str(e)}")
        raise exceptions.AuthenticationFailed(
            f"Token Encoding failed with error: {str(e)}"
        )

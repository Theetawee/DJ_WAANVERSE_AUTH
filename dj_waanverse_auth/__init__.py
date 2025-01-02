# flake8: noqa
# Copyright 2024 Waanverse Labs Inc. All rights reserved.

"""
Dj Waanverse Auth
~~~~~~~~~~~~~~~~

A comprehensive authentication package for Django REST Framework APIs by Waanverse Labs Inc.
Provides secure, scalable, and customizable authentication solutions.

Basic usage:
    >>> from dj_waanverse_auth import WaanverseAuthentication
    >>> from dj_waanverse_auth.models import WaanverseUser
    >>> from dj_waanverse_auth.permissions import WaanversePermission

Key Features:
    - Custom user model with enhanced security
    - JWT-based authentication
    - Role-based access control
    - Session management
    - Audit logging
    - Rate limiting

For more information, visit:
https://github.com/waanverse/dj-waanverse-auth
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import Final

from .version import __version__

# Package metadata
__title__: Final = "dj_waanverse_auth"
__author__: Final = "Waanverse Labs Inc."
__copyright__: Final = f"Copyright 2024 {__author__}"
__email__: Final = "software@waanverse.com"
__license__: Final = "Proprietary and Confidential"
__description__: Final = (
    "A comprehensive Waanverse Labs Inc. internal package for managing user accounts and authentication"
)
__maintainer__: Final = "Khaotungkulmethee Pattawee Drake"
__maintainer_email__: Final = "tawee@waanverse.com"
__url__: Final = "https://github.com/waanverse/dj-waanverse-auth"
__status__: Final = "Production"

# ASCII art logo
__logo__: Final = r"""
| |  | |                                          | |         | |        
| |  | | __ _  __ _ _ ____   _____ _ __ ___  ___  | |     __ _| |__  ___ 
| |/\| |/ _` |/ _` | '_ \ \ / / _ \ '__/ __|/ _ \ | |    / _` | '_ \/ __|
\  /\  / (_| | (_| | | | \ V /  __/ |  \__ \  __/ | |___| (_| | |_) \__ \
 \/  \/ \__,_|\__,_|_| |_|\_/ \___|_|  |___/\___| \_____/\__,_|_.__/|___/
"""

# Package version
__version__ = __version__

# Public API exports

__all__ = []


# Configure logging
def setup_logging():
    """Configure package-level logging with rotation and formatting."""
    logger = logging.getLogger(__name__)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        try:
            # File handler with rotation
            file_handler = RotatingFileHandler(
                "waanverse_auth.log", maxBytes=10485760, backupCount=5  # 10MB
            )
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except (IOError, PermissionError):
            logger.warning(
                "Could not set up file logging. Continuing with console logging only."
            )

    return logger


# Initialize logger
logger = setup_logging()

# Package initialization log
logger.info(f"Dj Waanverse Auth v{__version__} initialized")
if __debug__:
    logger.debug("Running in debug mode")


# Runtime checks
def check_dependencies():
    """Verify required dependencies are installed with compatible versions."""
    try:
        import django
        import rest_framework

        logger.debug(f"Django version: {django.get_version()}")
        logger.debug(f"DRF version: {rest_framework.VERSION}")
    except ImportError as e:
        logger.error(f"Missing required dependency: {e}")
        raise ImportError(f"Required dependency not found: {e}")


check_dependencies()

# Package banner
if sys.stdout.isatty():
    print(__logo__)
    print(f"Dj Waanverse Auth v{__version__}")
    print(f"Copyright © 2024 {__author__}. All rights reserved.\n")

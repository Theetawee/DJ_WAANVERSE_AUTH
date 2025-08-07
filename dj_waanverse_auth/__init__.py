# flake8: noqa
"""
For more information, visit:
https://github.com/waanverse/dj_waanverse_auth
"""
import logging
import sys
from datetime import datetime
from typing import Final

from dj_waanverse_auth.config.settings import auth_config as settings

logger = logging.getLogger(__name__)
from .version import __version__

default_app_config = "dj_waanverse_auth.apps.WaanverseAuthConfig"

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
__url__: Final = "https://github.com/waanverse/dj_waanverse_auth"
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

__all__ = [
    "settings",
]


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


def check_settings():
    """
    Check the required settings for the package.
    """
    try:
        from django.conf import settings

        if not hasattr(settings, "WAANVERSE_AUTH_CONFIG"):
            logger.error("WAANVERSE_AUTH_CONFIG is not set.")
            raise AttributeError("WAANVERSE_AUTH_CONFIG is not set.")
        logger.debug("WAANVERSE_AUTH_CONFIG is set.")
        waanverse_config = getattr(settings, "WAANVERSE_AUTH_CONFIG", None)
        required_keys = [
            "PUBLIC_KEY_PATH",
            "PRIVATE_KEY_PATH",
        ]
        for key in required_keys:
            if key not in waanverse_config:
                logger.error(f"{key} is missing in WAANVERSE_AUTH_CONFIG")
                raise AttributeError(f"{key} is missing in WAANVERSE_AUTH_CONFIG")
    except AttributeError as e:
        logger.error(f"Missing required setting: {e}")
        raise AttributeError(f"Required setting not found: {e}")


check_dependencies()
check_settings()

# Package banner
if sys.stdout.isatty():
    print(f"Powered by Dj Waanverse Auth v{__version__}")
    print(f"Copyright © {datetime.now().year} {__author__} All rights reserved.\n")

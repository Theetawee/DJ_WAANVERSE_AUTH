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
from .version import __version__

logger = logging.getLogger(__name__)

# Optional for older Django versions
default_app_config = "dj_waanverse_auth.apps.WaanverseAuthConfig"

# Package metadata
__title__: Final = "dj_waanverse_auth"
__author__: Final = "Waanverse Labs Inc."
__copyright__: Final = f"Copyright 2024 {__author__}"
__email__: Final = "support@waanverse.com"
__license__: Final = "Proprietary and Confidential"
__description__: Final = (
    "A comprehensive Waanverse Labs Inc. internal package for managing user accounts and authentication"
)
__maintainer__: Final = "Khaotungkulmethee Pattawee Drake"
__maintainer_email__: Final = "tawee@waanverse.com"
__url__: Final = "https://github.com/waanverse/dj_waanverse_auth"
__status__: Final = "Production"
__logo__: Final = r"""
| |  | |                                          | |         | |        
| |  | | __ _  __ _ _ ____   _____ _ __ ___  ___  | |     __ _| |__  ___ 
| |/\| |/ _` |/ _` | '_ \ \ / / _ \ '__/ __|/ _ \ | |    / _` | '_ \/ __|
\  /\  / (_| | (_| | | | \ V /  __/ |  \__ \  __/ | |___| (_| | |_) \__ \
 \/  \/ \__,_|\__,_|_| |_|\_/ \___|_|  |___/\___| \_____/\__,_|_.__/|___/
"""

# Public API exports
__all__ = [
    "settings",
]

# Logging
logger.info(f"Dj Waanverse Auth v{__version__} initialized")

if __debug__:
    logger.debug("Running in debug mode")

# Package banner on terminal
if sys.stdout.isatty():
    print(f"Powered by Dj Waanverse Auth v{__version__}")
    print(f"Copyright © {datetime.now().year} {__author__}. All rights reserved.\n")

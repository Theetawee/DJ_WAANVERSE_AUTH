import json
from dataclasses import dataclass
from typing import Dict, Optional, TypedDict

from django.http import HttpRequest, HttpResponse


class BrowserInfo(TypedDict, total=False):
    """Type definition for browser-related client hints."""

    Sec_Ch_Ua: Optional[str]
    Sec_Ch_Ua_Full_Version: Optional[str]
    Sec_Ch_Ua_Full_Version_List: Optional[str]
    Sec_Ch_Ua_Wow64: Optional[str]
    Sec_Ch_Ua_Form_Factor: Optional[str]


class DeviceInfo(TypedDict, total=False):
    """Type definition for device-related client hints."""

    Sec_Ch_Ua_Platform: Optional[str]
    Sec_Ch_Ua_Platform_Version: Optional[str]
    Sec_Ch_Ua_Arch: Optional[str]
    Sec_Ch_Ua_Model: Optional[str]
    Sec_Ch_Ua_Mobile: Optional[str]
    Device_Memory: Optional[float]
    Sec_Ch_Device_Memory: Optional[str]
    Dpr: Optional[float]
    Sec_Ch_Dpr: Optional[str]
    Sec_Ch_Width: Optional[str]
    Sec_Ch_Viewport_Width: Optional[str]
    Sec_Ch_Viewport_Height: Optional[str]
    Sec_Ch_Device_Type: Optional[str]
    Sec_Ch_Ua_Platform_Arch: Optional[str]
    Sec_Ch_Bitness: Optional[str]


class NetworkInfo(TypedDict, total=False):
    """Type definition for network-related client hints."""

    Downlink: Optional[float]
    Ect: Optional[str]
    Rtt: Optional[float]
    Save_Data: Optional[str]
    Sec_Ch_Downlink: Optional[str]
    Sec_Ch_Downlink_Max: Optional[str]
    Sec_Ch_Connection_Type: Optional[str]


class PreferencesInfo(TypedDict, total=False):
    """Type definition for user preference-related client hints."""

    Sec_Ch_Prefers_Color_Scheme: Optional[str]
    Sec_Ch_Prefers_Reduced_Motion: Optional[str]
    Sec_Ch_Prefers_Contrast: Optional[str]
    Sec_Ch_Prefers_Reduced_Data: Optional[str]
    Sec_Ch_Forced_Colors: Optional[str]


@dataclass
class ClientInfo:
    """
    Structured container for all client hint information.

    Attributes:
        browser (BrowserInfo): Browser-specific information including user agent, versions
        device (DeviceInfo): Device characteristics including platform, memory, display
        network (NetworkInfo): Network conditions including speed, type
        preferences (PreferencesInfo): User preferences including color scheme, motion
    """

    browser: BrowserInfo
    device: DeviceInfo
    network: NetworkInfo
    preferences: PreferencesInfo


class ExtendedHttpRequest(HttpRequest):
    client_info: ClientInfo


class ClientHintsMiddleware:
    """
    Middleware that processes and stores Client Hints headers.

    This middleware:
    1. Processes incoming Client Hints headers from the request
    2. Structures them into easily accessible categories
    3. Stores them in request.client_info
    4. Adds necessary headers to the response for future requests

    Usage:
        ```python
        def my_view(request: ExtendedHttpRequest):
            # Access client information with full type hints
            platform = request.client_info.device.get('Sec_Ch_Ua_Platform', 'unknown')
            is_mobile = request.client_info.device.get('Sec_Ch_Ua_Mobile', 'unknown')
            color_scheme = request.client_info.preferences.get('Sec_Ch_Prefers_Color_Scheme', 'unknown')
        ```
    """

    # Define all possible client hints grouped by category
    CLIENT_HINTS: Dict[str, list[str]] = {
        "browser": [
            "Sec-Ch-Ua",
            "Sec-Ch-Ua-Full-Version",
            "Sec-Ch-Ua-Full-Version-List",
            "Sec-Ch-Ua-Wow64",
            "Sec-Ch-Ua-Form-Factor",
        ],
        "device": [
            "Sec-Ch-Ua-Platform",
            "Sec-Ch-Ua-Platform-Version",
            "Sec-Ch-Ua-Arch",
            "Sec-Ch-Ua-Model",
            "Sec-Ch-Ua-Mobile",
            "Device-Memory",
            "Sec-Ch-Device-Memory",
            "Dpr",
            "Sec-Ch-Dpr",
            "Sec-Ch-Width",
            "Sec-Ch-Viewport-Width",
            "Sec-Ch-Viewport-Height",
            "Sec-Ch-Device-Type",
            "Sec-Ch-Ua-Platform-Arch",
            "Sec-Ch-Bitness",
        ],
        "network": [
            "Downlink",
            "Ect",
            "Rtt",
            "Save-Data",
            "Sec-Ch-Downlink",
            "Sec-Ch-Downlink-Max",
            "Sec-Ch-Connection-Type",
        ],
        "preferences": [
            "Sec-Ch-Prefers-Color-Scheme",
            "Sec-Ch-Prefers-Reduced-Motion",
            "Sec-Ch-Prefers-Contrast",
            "Sec-Ch-Prefers-Reduced-Data",
            "Sec-Ch-Forced-Colors",
        ],
    }

    def __init__(self, get_response):
        """Initialize the middleware with the get_response callable."""
        self.get_response = get_response

    def __call__(self, request: ExtendedHttpRequest) -> HttpResponse:
        """
        Process the request, add client hints, and return the response.

        Args:
            request: The incoming HTTP request

        Returns:
            HttpResponse: The processed response with appropriate headers
        """
        # Process incoming client hints
        client_info = self.process_client_hints(request)

        # Store processed client info in request for use in views
        request.client_info = client_info

        # Get response
        response = self.get_response(request)

        # Add headers for future requests
        return self.process_response(request, response)

    @staticmethod
    def _get_header(request: HttpRequest, name: str) -> str:
        """Get header value with proper casing and strip quotes."""
        value = request.headers.get(name) or request.headers.get(name.lower())
        if not value:
            return "unknown"

        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        elif '","' in value:
            parts = value.split(",")
            cleaned_parts = []
            for part in parts:
                part = part.strip()
                if part.startswith('"') and part.endswith('"'):
                    part = part[1:-1]
                cleaned_parts.append(part)
            return ", ".join(cleaned_parts)
        return value

    @staticmethod
    def _normalize_key(key: str) -> str:
        """Convert header name to valid Python identifier."""
        return key.replace("-", "_")

    def process_client_hints(self, request: HttpRequest) -> ClientInfo:
        """
        Process incoming client hints and return structured data.

        Args:
            request: The incoming HTTP request

        Returns:
            ClientInfo: Structured client information object
        """
        # Process hints by category
        browser_info = {
            self._normalize_key(hint): self._get_header(request, hint)
            for hint in self.CLIENT_HINTS["browser"]
        }

        device_info = {
            self._normalize_key(hint): self._get_header(request, hint)
            for hint in self.CLIENT_HINTS["device"]
        }

        network_info = {
            self._normalize_key(hint): self._get_header(request, hint)
            for hint in self.CLIENT_HINTS["network"]
        }

        preferences_info = {
            self._normalize_key(hint): self._get_header(request, hint)
            for hint in self.CLIENT_HINTS["preferences"]
        }

        # Convert numeric values
        numeric_fields = ["Device_Memory", "Dpr", "Downlink", "Rtt"]
        for key in numeric_fields:
            try:
                if (
                    key in device_info
                    and device_info[key]
                    and device_info[key] != "unknown"
                ):
                    device_info[key] = float(device_info[key])
            except (ValueError, TypeError):
                device_info[key] = "unknown"

        return ClientInfo(
            browser=browser_info,
            device=device_info,
            network=network_info,
            preferences=preferences_info,
        )

    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        """
        Add Client Hints headers to response.

        Args:
            request: The original HTTP request
            response: The response to be modified

        Returns:
            HttpResponse: The modified response with appropriate headers
        """
        # Combine all hints into a single string
        all_hints = ", ".join(
            hint for category in self.CLIENT_HINTS.values() for hint in category
        )

        # Add headers to request future client hints
        response["Accept-CH"] = all_hints
        response["Critical-CH"] = all_hints

        # Add Permissions-Policy header to delegate client hints
        response["Permissions-Policy"] = (
            "ch-ua=*, "
            "ch-ua-arch=*, "
            "ch-ua-bitness=*, "
            "ch-ua-full-version=*, "
            "ch-ua-full-version-list=*, "
            "ch-ua-mobile=*, "
            "ch-ua-model=*, "
            "ch-ua-platform=*, "
            "ch-ua-platform-version=*"
        )

        return response

    @staticmethod
    def get_client_info_json(request: ExtendedHttpRequest) -> str:
        """
        Convert client info to JSON string.

        Args:
            request: The HTTP request containing client info

        Returns:
            str: JSON string representation of client info
        """
        if hasattr(request, "client_info"):
            return json.dumps(
                {
                    "browser": request.client_info.browser,
                    "device": request.client_info.device,
                    "network": request.client_info.network,
                    "preferences": request.client_info.preferences,
                },
                indent=2,
            )
        return "{}"

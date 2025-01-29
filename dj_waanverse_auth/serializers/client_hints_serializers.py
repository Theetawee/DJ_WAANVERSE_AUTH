from typing import Any, Dict

from rest_framework import serializers


class BrowserInfoSerializer(serializers.Serializer):
    """Serializer for browser-related client hints."""

    Sec_Ch_Ua = serializers.CharField(default="Unknown")
    Sec_Ch_Ua_Full_Version = serializers.CharField(default="Unknown")
    Sec_Ch_Ua_Full_Version_List = serializers.CharField(default="Unknown")
    Sec_Ch_Ua_Wow64 = serializers.BooleanField(default=None, allow_null=True)
    Sec_Ch_Ua_Form_Factor = serializers.CharField(default="Unknown")

    def to_representation(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Handle missing values in the input dictionary."""
        data = {}
        for field_name, field in self.fields.items():
            value = instance.get(field_name)
            if isinstance(field, serializers.BooleanField):
                if value is None or value == "unknown":
                    data[field_name] = None
                else:
                    data[field_name] = str(value).lower() == "true"
            else:
                data[field_name] = value if value is not None else field.default
        return data


class DeviceInfoSerializer(serializers.Serializer):
    """Serializer for device-related client hints."""

    Sec_Ch_Ua_Platform = serializers.CharField(default="Unknown")
    Sec_Ch_Ua_Platform_Version = serializers.CharField(default="Unknown")
    Sec_Ch_Ua_Arch = serializers.CharField(default="Unknown")
    Sec_Ch_Ua_Model = serializers.CharField(default="Unknown")
    Sec_Ch_Ua_Mobile = serializers.BooleanField(default=None, allow_null=True)
    Device_Memory = serializers.FloatField(default=-1)
    Sec_Ch_Device_Memory = serializers.CharField(default="Unknown")
    Dpr = serializers.FloatField(default=-1)
    Sec_Ch_Dpr = serializers.CharField(default="Unknown")
    Sec_Ch_Width = serializers.CharField(default="Unknown")
    Sec_Ch_Viewport_Width = serializers.CharField(default="Unknown")
    Sec_Ch_Viewport_Height = serializers.CharField(default="Unknown")
    Sec_Ch_Device_Type = serializers.CharField(default="Unknown")
    Sec_Ch_Ua_Platform_Arch = serializers.CharField(default="Unknown")
    Sec_Ch_Bitness = serializers.CharField(default="Unknown")

    def to_representation(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Handle missing values in the input dictionary."""
        data = {}
        for field_name, field in self.fields.items():
            value = instance.get(field_name)
            if isinstance(field, serializers.BooleanField):
                if value is None or value == "unknown":
                    data[field_name] = None
                else:
                    data[field_name] = str(value).lower() == "true"
            elif isinstance(field, serializers.FloatField):
                try:
                    if value is None or value == "unknown":
                        data[field_name] = field.default
                    else:
                        data[field_name] = float(value)
                except (ValueError, TypeError):
                    data[field_name] = field.default
            else:
                data[field_name] = value if value is not None else field.default
        return data


class NetworkInfoSerializer(serializers.Serializer):
    """Serializer for network-related client hints."""

    Downlink = serializers.FloatField(default=-1)
    Ect = serializers.CharField(default="Unknown")
    Rtt = serializers.FloatField(default=-1)
    Save_Data = serializers.BooleanField(default=None, allow_null=True)
    Sec_Ch_Downlink = serializers.CharField(default="Unknown")
    Sec_Ch_Downlink_Max = serializers.CharField(default="Unknown")
    Sec_Ch_Connection_Type = serializers.CharField(default="Unknown")

    def to_representation(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Handle missing values in the input dictionary."""
        data = {}
        for field_name, field in self.fields.items():
            value = instance.get(field_name)
            if isinstance(field, serializers.BooleanField):
                if value is None or value == "unknown":
                    data[field_name] = None
                else:
                    data[field_name] = str(value).lower() == "true"
            elif isinstance(field, serializers.FloatField):
                try:
                    if value is None or value == "unknown":
                        data[field_name] = field.default
                    else:
                        data[field_name] = float(value)
                except (ValueError, TypeError):
                    data[field_name] = field.default
            else:
                data[field_name] = value if value is not None else field.default
        return data


class PreferencesInfoSerializer(serializers.Serializer):
    """Serializer for user preference-related client hints."""

    Sec_Ch_Prefers_Color_Scheme = serializers.CharField(default="Unknown")
    Sec_Ch_Prefers_Reduced_Motion = serializers.BooleanField(
        default=None, allow_null=True
    )
    Sec_Ch_Prefers_Contrast = serializers.CharField(default="Unknown")
    Sec_Ch_Prefers_Reduced_Data = serializers.BooleanField(
        default=None, allow_null=True
    )
    Sec_Ch_Forced_Colors = serializers.BooleanField(default=None, allow_null=True)

    def to_representation(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Handle missing values in the input dictionary."""
        data = {}
        for field_name, field in self.fields.items():
            value = instance.get(field_name)
            if isinstance(field, serializers.BooleanField):
                if value is None or value == "unknown":
                    data[field_name] = None
                else:
                    data[field_name] = str(value).lower() == "true"
            else:
                data[field_name] = value if value is not None else field.default
        return data


class ClientInfoSerializer(serializers.Serializer):
    """
    Serializer for the complete client information structure.

    This serializer handles all client hints data including browser,
    device, network, and user preferences information.

    Usage:
        ```python
        def my_view(request: ExtendedHttpRequest):
            serializer = ClientInfoSerializer(request.client_info)
            return Response(serializer.data)
        ```
    """

    browser = BrowserInfoSerializer()
    device = DeviceInfoSerializer()
    network = NetworkInfoSerializer()
    preferences = PreferencesInfoSerializer()

    class Meta:
        """Metadata for ClientInfoSerializer."""

        fields = ("browser", "device", "network", "preferences")

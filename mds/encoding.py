"""
Encoding and decoding MDS Provider data.
"""

import json
from datetime import datetime
from pathlib import Path
from uuid import UUID

import dateutil.parser
from shapely.geometry import Point, Polygon

from mds import geometry
from .versions import UnsupportedVersionError, Version


class JsonEncoder(json.JSONEncoder):
    """
    Version-aware encoder for MDS json types:

    * datetime to date_format or str
    * Path to str
    * Point/Polygon to GeoJSON Feature dict
    * tuple to list
    * UUID to str
    * Version to str
    """

    def __init__(self, *args, **kwargs):
        """
        Parameters:
            date_format: str
                Configure how dates are formatted using one of:
                * unix: format dates as a numeric offset from Unix epoch (default, Version-aware)
                * iso8601: format dates as ISO 8601 strings
                * python format string: custom format

            version: str, Version, optional
                The MDS version to target.
        """
        self.date_format = kwargs.pop("date_format", "unix")
        self.version = Version(kwargs.pop("version", Version.mds_lower()))
        self.timestamp_encoder = TimestampEncoder(version=self.version)
        json.JSONEncoder.__init__(self, *args, **kwargs)

    def __repr__(self):
        return f"<mds.encoding.JsonEncoder ('{self.version}', '{self.date_format}')>"

    def default(self, obj):
        """
        Implement serialization for some special types.
        """
        if isinstance(obj, datetime):
            return self.timestamp_encoder.encode(obj)

        if isinstance(obj, Path):
            return str(obj)

        if isinstance(obj, Point) or isinstance(obj, Polygon):
            return geometry.to_feature(obj)

        if isinstance(obj, tuple):
            return list(obj)

        if isinstance(obj, UUID):
            return str(obj)

        if isinstance(obj, Version):
            return str(obj)

        return json.JSONEncoder.default(self, obj)


class TimestampEncoder:
    """
    Version-aware encoder for MDS timestamps.
    """

    def __init__(self, **kwargs):
        """
        Parameters:
            date_format: str
                Configure how dates are formatted using one of:
                * unix: format dates as a numeric offset from Unix epoch (default, Version-aware)
                * iso8601: format dates as ISO 8601 strings
                * python format string: custom format

            version: str, Version, optional
                The MDS version to target.
        """
        self.date_format = kwargs.get("date_format", "unix")

        self.version = Version(kwargs.get("version", Version.mds_lower()))
        if self.version.unsupported:
            raise UnsupportedVersionError(self.version)

    def __repr__(self):
        return f"<mds.encoding.TimestampEncoder ('{self.version}', '{self.date_format}')>"

    def encode(self, data):
        """
        Encode MDS timestamps for transport.

        Parameters:
            data: datetime
                Datetime to encode.

        Return:
            datetime
        """
        if self.date_format == "unix":
            if self.version < Version("0.3.0"):
                return str(obj.timestamp())
            else:
                return str(int(round(obj.timestamp() * 1000)))
        elif self.date_format == "iso8601":
            return obj.isoformat()
        elif self.date_format is not None:
            return obj.strftime(self.date_format)
        else:
            return str(obj)


class TimestampDecoder:
    """
    Version-aware decoder for MDS timestamps.
    """

    def __init__(self, **kwargs):
        """
        Parameters:
            version: str, Version, optional
                The MDS version to target.
        """
        self.version = Version(kwargs.get("version", Version.mds_lower()))

    def __repr__(self):
        return f"<mds.encoding.TimestampDecoder ('{self.version}')>"

    def decode(self, data):
        """
        Decode a MDS timestamp representation into a datetime.

        Parameters:
            data: str, int, float
                Data representing a datetime as text or UNIX timestamp.

        Return:
            datetime
        """
        try:
            if self.version < Version("0.3.0"):
                return datetime.utcfromtimestamp(int(data))
            else:
                return datetime.utcfromtimestamp(int(data / 1000.0))
        except:
            return dateutil.parser.parse(data)

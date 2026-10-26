from datetime import datetime, timezone
from typing import Annotated

from pydantic import PlainSerializer


def utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        aware = value.replace(tzinfo=timezone.utc)
    else:
        aware = value.astimezone(timezone.utc)
    return aware.replace(microsecond=0).isoformat().replace("+00:00", "Z")


UtcDateTime = Annotated[
    datetime,
    PlainSerializer(utc_iso, return_type=str, when_used="json"),
]
